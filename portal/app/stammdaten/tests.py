import re
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from django.apps import apps
from django.contrib import admin
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import RequestFactory

from stammdaten import testhilfen as th
from stammdaten.models import Ansprechpartner, Kunde, Leistung, Leistungsvereinbarung, Objekt

pytestmark = pytest.mark.django_db

FACH_APPS = ("stammdaten", "auftraege", "personal", "dokumente", "kommunikation", "integrationen", "ki")


@pytest.mark.parametrize("modell", [Kunde, Ansprechpartner, Objekt, Leistung, Leistungsvereinbarung], ids=lambda m: m.__name__)
def test_schema_abgleich(modell):
    th.pruefe_schema(modell)


def test_alle_fachmodelle_sind_unmanaged_und_jede_tabelle_ist_abgebildet():
    modelle = [m for a in FACH_APPS for m in apps.get_app_config(a).get_models()]
    assert all(not m._meta.managed for m in modelle)
    abgebildet = {m._meta.db_table for m in modelle}
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'hh'")
        tabellen = {zeile[0] for zeile in cursor.fetchall()}
    # Nicht in den Fach-Apps: benutzer (konten), nummernkreise (nur intern), Django-eigene Tabellen
    erwartet = {t for t in tabellen if not t.startswith(("django_", "auth_", "otp_")) and t not in {"benutzer", "nummernkreise"}}
    assert erwartet - abgebildet == set()


def test_kunde_crud_mit_kundennummer():
    k = th.kunde(email="Kontakt@Pytest.example.org")
    assert re.fullmatch(r"K-\d{5}", k.kundennummer)
    assert k.erstellt_am is not None and k.geaendert_am is not None
    k2 = th.kunde(name="Pytest Zweitkunde GmbH")
    assert k2.kundennummer > k.kundennummer

    k.status = "aktiv"
    k.geaendert_am = k.erstellt_am = datetime(2000, 1, 1, tzinfo=timezone.utc)  # wird nie gesendet
    k.save()
    assert k.geaendert_am.year > 2000  # vom Trigger gesetzt und nachgeladen
    k.refresh_from_db()
    assert k.status == "aktiv" and k.erstellt_am.year > 2000
    # citext: E-Mail ohne Rücksicht auf Groß-/Kleinschreibung
    assert Kunde.objects.filter(email="kontakt@pytest.example.org").exists()

    k2.delete()
    assert not Kunde.objects.filter(pk=k2.pk).exists()


def test_kunden_dublette_wird_verhindert():
    th.kunde(name="Pytest  Dublette GmbH")
    with pytest.raises(IntegrityError), transaction.atomic():
        th.kunde(name="pytest dublette gmbh")


def test_objekt_und_ansprechpartner():
    k = th.kunde()
    o = th.objekt(k, gehweg_meter=Decimal("12.5"))
    assert re.fullmatch(r"OB-\d{5}", o.objektnummer)
    assert o.adresse == "Musterstraße 99, 33330 Gütersloh"
    a = Ansprechpartner.objects.create(kunde=k, nachname="Muster", ist_hauptkontakt=True)
    assert list(k.ansprechpartner.all()) == [a]
    with pytest.raises(IntegrityError), transaction.atomic():
        Ansprechpartner.objects.create(kunde=k, nachname="Zweiter", ist_hauptkontakt=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        Ansprechpartner.objects.create(kunde=k, nachname="Ohne Nachweis", email_einwilligung="2026-11-01T10:00Z")


def test_leistung_und_vereinbarung():
    lst = Leistung.objects.create(code="PYTEST", name="Pytest-Leistung", einheit="Std.", preis_netto_cent=5350)
    assert lst.ust_satz == Decimal("19.00")
    o = th.objekt(th.kunde())
    v = Leistungsvereinbarung.objects.create(
        objekt=o, leistung=lst, intervall="woechentlich", wochentag=2, preis_netto_cent=5350, gueltig_von="2026-01-01"
    )
    v.refresh_from_db()
    assert v.menge == Decimal("1")
    with pytest.raises(IntegrityError), transaction.atomic():
        Leistungsvereinbarung.objects.create(
            objekt=o, leistung=lst, intervall="woechentlich", preis_netto_cent=1, gueltig_von="2026-01-01"
        )


# ---------------------------------------------------------------- Testdaten-Befehl
def _anzahlen():
    from auftraege.models import Angebot, Auftrag, Einsatz, EinsatzMitarbeiter, Rechnung
    from kommunikation.models import EmailProtokoll
    from personal.models import Arbeitszeit, Bewerbung, Mitarbeiter, Stelle

    return {
        m.__name__: m.objects.count()
        for m in (Kunde, Objekt, Ansprechpartner, Leistung, Leistungsvereinbarung, Mitarbeiter, Stelle, Bewerbung,
                  Auftrag, Einsatz, EinsatzMitarbeiter, Arbeitszeit, Angebot, Rechnung, EmailProtokoll)
    }


def test_testdaten_befehl_idempotent_und_loeschbar():
    from auftraege.models import Angebot, Einsatz
    from kommunikation.models import EmailProtokoll

    call_command("testdaten", stdout=open("/dev/null", "w"))
    erste = _anzahlen()
    call_command("testdaten", stdout=open("/dev/null", "w"))
    assert _anzahlen() == erste

    assert erste["Kunde"] >= 3 and erste["Objekt"] >= 3 and erste["Mitarbeiter"] == 2 and erste["Bewerbung"] == 2
    assert erste["Rechnung"] == 1 and erste["EmailProtokoll"] == 2
    assert Leistung.objects.get(code="STD").preis_netto_cent == 5350
    assert Leistung.objects.get(code="WD-GRUND").preis_netto_cent == 22000
    assert EmailProtokoll.objects.filter(status="neu").count() == 1
    angebot = Angebot.objects.get(status="entwurf")
    assert angebot.summe_netto_cent == 22000 + 40 * 950  # per Trigger aus den Positionen
    from django.utils import timezone

    assert Einsatz.objects.filter(geplant_von__date=timezone.localdate()).count() >= 2
    # Nur fiktive Daten
    assert all(e.endswith("example.org") for e in Kunde.objects.exclude(email=None).values_list("email", flat=True))
    assert all(33330 <= int(p) <= 33378 for p in Objekt.objects.values_list("plz", flat=True))

    call_command("testdaten", "--loeschen", stdout=open("/dev/null", "w"))
    nachher = _anzahlen()
    assert nachher["Leistung"] == erste["Leistung"]  # Katalog bleibt
    assert {k: v for k, v in nachher.items() if k != "Leistung"} == {k: 0 for k in nachher if k != "Leistung"}
    # und wieder anlegbar
    call_command("testdaten", stdout=open("/dev/null", "w"))
    assert _anzahlen() == erste


def test_loeschen_laesst_echte_daten_stehen():
    echt = th.kunde(name="Pytest Echtkunde GmbH")
    call_command("testdaten", stdout=open("/dev/null", "w"))
    call_command("testdaten", "--loeschen", stdout=open("/dev/null", "w"))
    assert Kunde.objects.filter(pk=echt.pk).exists()


# ---------------------------------------------------------------- Verwaltungsoberfläche (Smoke-Test)
@pytest.mark.parametrize("rolle", ["admin", "buero"])
def test_admin_listen_und_formulare_laden(rolle):
    call_command("testdaten", stdout=open("/dev/null", "w"))
    user = th.benutzer(rolle)
    user.is_verified = lambda: True  # sonst setzt das die OTP-Middleware
    rf = RequestFactory()
    geprueft = 0
    for modell, modeladmin in admin.site._registry.items():
        if modell._meta.app_label not in FACH_APPS:
            continue
        request = rf.get("/")
        request.user = user
        antwort = modeladmin.changelist_view(request)
        antwort.render()
        assert antwort.status_code == 200, modell
        obj = modell.objects.first()
        if obj is not None:
            request = rf.get("/")
            request.user = user
            antwort = modeladmin.change_view(request, str(obj.pk))
            antwort.render()
            assert antwort.status_code == 200, modell
        request = rf.get("/")
        request.user = user
        if modeladmin.has_add_permission(request):
            antwort = modeladmin.add_view(request)
            antwort.render()
            assert antwort.status_code == 200, modell
        geprueft += 1
    assert geprueft >= 20
