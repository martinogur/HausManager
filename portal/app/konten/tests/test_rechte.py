"""Rollen und Rechte: Verwaltungszugang, Decorator, Mixin."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory
from django.views import View

from konten.rechte import RolleErforderlichMixin, ist_admin, ist_buero, ist_mitarbeiter, rolle_erforderlich


@pytest.mark.django_db
def test_mitarbeiter_hat_keinen_admin_zugang(client, mitarbeiter_benutzer, angemeldet):
    angemeldet(client, mitarbeiter_benutzer)  # sogar mit bestätigtem 2FA
    assert not mitarbeiter_benutzer.is_staff
    antwort = client.get("/admin/", follow=True)
    assert antwort.status_code == 403
    assert client.get("/admin/konten/benutzer/", follow=True).status_code == 403


@pytest.mark.django_db
def test_admin_sieht_benutzerverwaltung(client, admin_benutzer, angemeldet):
    angemeldet(client, admin_benutzer)
    antwort = client.get("/admin/")
    assert antwort.status_code == 200
    assert "/admin/konten/benutzer/" in antwort.content.decode()
    assert client.get("/admin/konten/benutzer/").status_code == 200
    assert client.get("/admin/konten/benutzer/add/").status_code == 200


@pytest.mark.django_db
def test_buero_hat_verwaltung_aber_keine_benutzerverwaltung(client, buero_benutzer, angemeldet):
    angemeldet(client, buero_benutzer)
    antwort = client.get("/admin/")
    assert antwort.status_code == 200
    assert "/admin/konten/benutzer/" not in antwort.content.decode()
    assert client.get("/admin/konten/benutzer/").status_code == 403
    assert client.get("/admin/otp_totp/totpdevice/").status_code == 403


@pytest.mark.django_db
def test_admin_legt_benutzer_an(client, admin_benutzer, angemeldet):
    from konten.models import Benutzer

    angemeldet(client, admin_benutzer)
    antwort = client.post(
        "/admin/konten/benutzer/add/",
        {"email": "neu@example.org", "anzeigename": "Neu", "rolle": "buero", "aktiv": "on",
         "passwort1": "Ein-sicheres-Passwort-77", "passwort2": "Ein-sicheres-Passwort-77"},
    )
    assert antwort.status_code == 302, antwort.content.decode()[:2000]
    neu = Benutzer.objects.get(email="neu@example.org")
    assert neu.rolle == "buero" and neu.check_password("Ein-sicheres-Passwort-77")


@pytest.mark.django_db
def test_rechte_hilfen(admin_benutzer, buero_benutzer, mitarbeiter_benutzer):
    assert ist_admin(admin_benutzer) and ist_buero(admin_benutzer)
    assert not ist_admin(buero_benutzer) and ist_buero(buero_benutzer)
    assert not ist_buero(mitarbeiter_benutzer) and ist_mitarbeiter(mitarbeiter_benutzer)
    assert not ist_admin(AnonymousUser()) and not ist_buero(AnonymousUser())
    assert buero_benutzer.has_perm("stammdaten.change_kunde")
    assert not buero_benutzer.has_perm("konten.change_benutzer")
    assert not mitarbeiter_benutzer.has_perm("stammdaten.view_kunde")
    assert admin_benutzer.is_superuser and not buero_benutzer.is_superuser


@pytest.mark.django_db
def test_decorator_und_mixin(admin_benutzer, buero_benutzer, mitarbeiter_benutzer):
    fabrik = RequestFactory()

    @rolle_erforderlich("buero")
    def nur_buero(request):
        return HttpResponse("ok")

    class NurAdmin(RolleErforderlichMixin, View):
        erlaubte_rollen = ("admin",)

        def get(self, request):
            return HttpResponse("ok")

    def anfrage(user):
        request = fabrik.get("/test/")
        request.user = user
        return request

    assert nur_buero(anfrage(buero_benutzer)).status_code == 200
    assert nur_buero(anfrage(admin_benutzer)).status_code == 200
    with pytest.raises(PermissionDenied):
        nur_buero(anfrage(mitarbeiter_benutzer))
    assert nur_buero(anfrage(AnonymousUser())).status_code == 302

    assert NurAdmin.as_view()(anfrage(admin_benutzer)).status_code == 200
    with pytest.raises(PermissionDenied):
        NurAdmin.as_view()(anfrage(buero_benutzer))
