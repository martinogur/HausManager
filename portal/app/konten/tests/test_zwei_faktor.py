"""Zwei-Faktor (TOTP): Pflicht für admin/buero, Einrichtung, Code-Abfrage, Sperre."""

import pytest
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

from conftest import TEST_PASSWORT, totp_code

EINRICHTEN = reverse("konten:zwei_faktor_einrichten")
PRUEFEN = reverse("konten:zwei_faktor_pruefen")


def _anmelden(client, benutzer):
    return client.post(reverse("konten:anmelden"), {"username": benutzer.email, "password": TEST_PASSWORT})


@pytest.mark.django_db
@pytest.mark.parametrize("rolle", ["admin", "buero"])
def test_admin_und_buero_ohne_2fa_werden_zur_einrichtung_umgeleitet(client, benutzer_anlegen, rolle):
    benutzer = benutzer_anlegen(rolle)
    _anmelden(client, benutzer)
    antwort = client.get("/")
    assert antwort.status_code == 302
    assert antwort["Location"].startswith(EINRICHTEN)
    # Auch die Verwaltung ist ohne 2FA gesperrt
    antwort = client.get("/admin/")
    assert antwort["Location"].startswith(EINRICHTEN)


@pytest.mark.django_db
def test_mitarbeiter_ohne_2fa_hat_zugang(client, mitarbeiter_benutzer):
    _anmelden(client, mitarbeiter_benutzer)
    assert client.get("/").status_code == 200


@pytest.mark.django_db
def test_einrichtung_mit_gueltigem_code(client, admin_benutzer):
    _anmelden(client, admin_benutzer)
    antwort = client.get(EINRICHTEN)
    assert antwort.status_code == 200
    inhalt = antwort.content.decode()
    assert "<svg" in inhalt and "QR-Code" in inhalt

    geraet = TOTPDevice.objects.get(user=admin_benutzer, confirmed=False)
    # QR-Code bleibt beim Neuladen gleich (kein neues Gerät)
    client.get(EINRICHTEN)
    assert TOTPDevice.objects.filter(user=admin_benutzer).count() == 1

    antwort = client.post(EINRICHTEN, {"code": totp_code(geraet), "next": "/"})
    assert antwort.status_code == 302
    assert antwort["Location"] == "/"
    geraet.refresh_from_db()
    admin_benutzer.refresh_from_db()
    assert geraet.confirmed
    assert admin_benutzer.zwei_faktor
    antwort = client.get("/")
    assert antwort.status_code == 200
    assert "Kennzahlen" in antwort.content.decode()


@pytest.mark.django_db
def test_einrichtung_mit_falschem_code(client, buero_benutzer):
    _anmelden(client, buero_benutzer)
    client.get(EINRICHTEN)
    antwort = client.post(EINRICHTEN, {"code": "000000"})
    assert antwort.status_code == 200
    assert "Der Code stimmt nicht" in antwort.content.decode()
    assert 'aria-invalid="true"' in antwort.content.decode()
    assert client.get("/").status_code == 302


@pytest.mark.django_db
def test_mit_gueltigem_totp_zugriff_aufs_dashboard(client, buero_benutzer, totp_geraet):
    geraet = totp_geraet(buero_benutzer)
    _anmelden(client, buero_benutzer)
    antwort = client.get("/")
    assert antwort["Location"].startswith(PRUEFEN)

    antwort = client.post(PRUEFEN, {"code": totp_code(geraet), "next": "/"})
    assert antwort.status_code == 302
    antwort = client.get("/")
    assert antwort.status_code == 200
    assert "Kennzahlen" in antwort.content.decode()


@pytest.mark.django_db
def test_falscher_code_fuenfmal_sperrt_und_meldet_ab(client, buero_benutzer, totp_geraet):
    totp_geraet(buero_benutzer)
    _anmelden(client, buero_benutzer)
    for _ in range(4):
        antwort = client.post(PRUEFEN, {"code": "000000"})
        assert antwort.status_code == 200
    antwort = client.post(PRUEFEN, {"code": "000000"})
    assert antwort.status_code == 302
    assert antwort["Location"] == reverse("konten:anmelden")
    # abgemeldet und Passwort-Anmeldung gesperrt
    assert client.get("/").status_code == 302
    antwort = _anmelden(client, buero_benutzer)
    assert "gesperrt" in antwort.content.decode()


@pytest.mark.django_db
def test_mitarbeiter_mit_geraet_muss_code_eingeben(client, mitarbeiter_benutzer, totp_geraet):
    totp_geraet(mitarbeiter_benutzer)
    _anmelden(client, mitarbeiter_benutzer)
    assert client.get("/")["Location"].startswith(PRUEFEN)


@pytest.mark.django_db
def test_htmx_anfrage_ohne_2fa_bekommt_hx_redirect(client, buero_benutzer):
    _anmelden(client, buero_benutzer)
    antwort = client.get(reverse("berichte:kennzahlen"), headers={"HX-Request": "true"})
    assert antwort.status_code == 200
    assert antwort["HX-Redirect"].startswith(EINRICHTEN)
