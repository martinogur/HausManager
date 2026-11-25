import re
from datetime import timedelta

import pytest
from django.contrib import admin
from django.db import IntegrityError, transaction
from django.test import RequestFactory
from django.utils import timezone

from personal.models import (
    Abwesenheit,
    Arbeitszeit,
    Bewerbung,
    Mitarbeiter,
    MitarbeiterQualifikation,
    Qualifikation,
    Stelle,
    Verfuegbarkeit,
)
from stammdaten import testhilfen as th

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "modell",
    [Mitarbeiter, Qualifikation, MitarbeiterQualifikation, Verfuegbarkeit, Abwesenheit, Stelle, Bewerbung, Arbeitszeit],
    ids=lambda m: m.__name__,
)
def test_schema_abgleich(modell):
    th.pruefe_schema(modell)


def test_mitarbeiter_crud_und_personalnummer():
    konto = th.benutzer()
    m = th.mitarbeiter(konto=konto, email="pia.pytest@example.org", stundenlohn_cent=1500)
    assert re.fullmatch(r"MA-\d{5}", m.personalnummer)
    assert konto.mitarbeiter == m
    m.telefon = "05241 000000"
    m.save()
    assert Mitarbeiter.objects.get(pk=m.pk).telefon == "05241 000000"
    konto.delete()  # ON DELETE SET NULL
    m.refresh_from_db()
    assert m.benutzer_id is None


def test_qualifikation_mit_zusammengesetztem_schluessel():
    m = th.mitarbeiter()
    q = Qualifikation.objects.create(name="Pytest-Qualifikation")
    mq = MitarbeiterQualifikation.objects.create(mitarbeiter=m, qualifikation=q)
    assert mq.pk == (m.pk, q.pk)
    assert MitarbeiterQualifikation.objects.get(pk=(m.pk, q.pk)).qualifikation == q
    with pytest.raises(IntegrityError), transaction.atomic():
        MitarbeiterQualifikation.objects.create(mitarbeiter=m, qualifikation=q)


def test_bewerbung_nummer_loeschfrist_und_loeschfaellig():
    stelle = Stelle.objects.create(titel="Pytest-Stelle", beschaeftigung="minijob")
    b = Bewerbung.objects.create(
        stelle=stelle, vorname="Lea", nachname="Pytest", email="lea.pytest@example.org", datenschutz_ok_am=timezone.now()
    )
    assert re.fullmatch(rf"BW-{timezone.now().year}-\d{{4}}", b.bewerbungsnummer)
    assert b.loeschen_ab == timezone.localdate() + timedelta(days=180)
    assert b.status == "eingegangen"
    assert not Bewerbung.objects.loeschfaellig().exists()
    assert list(Bewerbung.objects.loeschfaellig(stichtag=b.loeschen_ab)) == [b]
    Bewerbung.objects.filter(pk=b.pk).update(loeschen_ab=timezone.localdate() - timedelta(days=1))
    assert list(Bewerbung.objects.loeschfaellig()) == [b]
    with pytest.raises(IntegrityError), transaction.atomic():
        Bewerbung.objects.create(
            stelle=stelle, vorname="Lea", nachname="Pytest", email="LEA.pytest@example.org", datenschutz_ok_am=timezone.now()
        )


def test_arbeitszeit_ueberschneidung_wird_abgelehnt():
    m = th.mitarbeiter()
    e = th.einsatz()
    a = Arbeitszeit.objects.create(mitarbeiter=m, einsatz=e, beginn=th.morgen_um(8), ende=th.morgen_um(10), pause_minuten=15)
    assert a.stunden == 1.75
    with pytest.raises(IntegrityError), transaction.atomic():
        Arbeitszeit.objects.create(mitarbeiter=m, beginn=th.morgen_um(9), ende=th.morgen_um(11))
    with pytest.raises(IntegrityError), transaction.atomic():
        Arbeitszeit.objects.create(mitarbeiter=m, beginn=th.morgen_um(12), ende=th.morgen_um(13), pause_minuten=60)
    Arbeitszeit.objects.create(mitarbeiter=m, beginn=th.morgen_um(10), ende=th.morgen_um(12))


def test_verfuegbarkeit_und_abwesenheit():
    m = th.mitarbeiter()
    Verfuegbarkeit.objects.create(mitarbeiter=m, wochentag=1, von="08:00", bis="12:00")
    Abwesenheit.objects.create(mitarbeiter=m, von="2026-12-01", bis="2026-12-05", grund="Urlaub")
    with pytest.raises(IntegrityError), transaction.atomic():
        Verfuegbarkeit.objects.create(mitarbeiter=m, wochentag=8, von="08:00", bis="12:00")
    assert m.verfuegbarkeiten.count() == 1 and m.abwesenheiten.count() == 1


@pytest.mark.parametrize("rolle,sichtbar", [("admin", True), ("buero", False)])
def test_stundenlohn_nur_fuer_admin(rolle, sichtbar):
    m = th.mitarbeiter(stundenlohn_cent=1777)
    request = RequestFactory().get("/")
    request.user = th.benutzer(rolle)
    request.user.is_verified = lambda: True  # sonst setzt das die OTP-Middleware
    modeladmin = admin.site._registry[Mitarbeiter]
    assert ("stundenlohn_cent" in modeladmin.get_fields(request, m)) is sichtbar
    assert ("stundenlohn_cent" in modeladmin.get_form(request, m).base_fields) is sichtbar
    antwort = modeladmin.change_view(request, str(m.pk))
    antwort.render()
    assert ("1777" in antwort.content.decode()) is sichtbar
