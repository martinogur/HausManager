import re
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.utils import timezone

from auftraege.models import (
    Anfrage,
    Angebot,
    Angebotsposition,
    Auftrag,
    Einsatz,
    EinsatzMitarbeiter,
    Rechnung,
)
from stammdaten import testhilfen as th

pytestmark = pytest.mark.django_db

JAHR = timezone.now().year


@pytest.mark.parametrize(
    "modell",
    [Anfrage, Angebot, Angebotsposition, Auftrag, Einsatz, EinsatzMitarbeiter, Rechnung],
    ids=lambda m: m.__name__,
)
def test_schema_abgleich(modell):
    th.pruefe_schema(modell)


def test_anfrage_mit_nummer_und_arrays():
    a = Anfrage.objects.create(kanal="webseite", betreff="Pytest", gewuenschte_leistungen=["Winterdienst", "Garten"])
    assert re.fullmatch(rf"AN-{JAHR}-\d{{4}}", a.anfragenummer)
    a.refresh_from_db()
    assert a.gewuenschte_leistungen == ["Winterdienst", "Garten"] and a.status == "neu"
    assert Anfrage.objects.filter(gewuenschte_leistungen__contains=["Garten"]).exists()


def test_angebot_summe_per_trigger_und_wird_beim_speichern_nicht_ueberschrieben():
    k = th.kunde()
    o = th.objekt(k)
    g = Angebot.objects.create(kunde=k, objekt=o)
    assert re.fullmatch(rf"AG-{JAHR}-\d{{4}}", g.angebotsnummer)
    assert g.summe_netto_cent == 0
    Angebotsposition.objects.create(angebot=g, pos=1, beschreibung="Grundpauschale", menge=Decimal("1"), einheit="Saison", einzelpreis_netto_cent=22000)
    Angebotsposition.objects.create(angebot=g, pos=2, beschreibung="lfd. Meter", menge=Decimal("2.5"), einheit="lfm", einzelpreis_netto_cent=950)
    g.gueltig_bis = timezone.localdate() + timedelta(days=30)
    g.save()  # darf die vom Trigger berechnete Summe nicht mit 0 überschreiben
    assert g.summe_netto_cent == 22000 + 2375
    g.refresh_from_db()
    assert g.summe_netto_cent == 24375
    with pytest.raises(IntegrityError), transaction.atomic():
        Angebotsposition.objects.create(angebot=g, pos=1, beschreibung="doppelt", menge=1, einheit="x", einzelpreis_netto_cent=1)


def test_angebot_versand_nur_mit_freigabe():
    k = th.kunde()
    g = Angebot.objects.create(kunde=k, objekt=th.objekt(k))
    g.status = "versendet"
    with pytest.raises(IntegrityError), transaction.atomic():
        g.save()
    g.status = "versendet"
    g.freigegeben_am = timezone.now()
    g.freigegeben_von = th.benutzer("admin")
    g.save()


def test_auftrag_crud_und_offen():
    a = th.auftrag()
    assert re.fullmatch(rf"AU-{JAHR}-\d{{4}}", a.auftragsnummer)
    assert a.status == "bestaetigt"
    erledigt = th.auftrag(kunde_obj=a.kunde, objekt_obj=a.objekt, status="erledigt")
    storniert = th.auftrag(kunde_obj=a.kunde, objekt_obj=a.objekt, status="storniert")
    offen = set(Auftrag.objects.offen())
    assert a in offen and erledigt not in offen and storniert not in offen
    a.titel = "Geändert"
    a.save()
    assert Auftrag.objects.get(pk=a.pk).titel == "Geändert"


def test_auftrag_mit_fremdem_objekt_wird_abgelehnt():
    k1 = th.kunde(name="Pytest Kunde Eins")
    k2 = th.kunde(name="Pytest Kunde Zwei")
    fremdes_objekt = th.objekt(k2)
    with pytest.raises(IntegrityError), transaction.atomic():
        Auftrag.objects.create(kunde=k1, objekt=fremdes_objekt, titel="Falsch zugeordnet")


def test_einsatz_zuweisung_zeitraum_und_doppelbelegung():
    m = th.mitarbeiter()
    e1 = th.einsatz(von=th.morgen_um(8), bis=th.morgen_um(10))
    z = EinsatzMitarbeiter.objects.create(einsatz=e1, mitarbeiter=m)
    assert z.zeitraum.lower == e1.geplant_von and z.zeitraum.upper == e1.geplant_bis  # vom Trigger
    assert EinsatzMitarbeiter.objects.get(pk=(e1.pk, m.pk)) == z

    ueberschneidend = th.einsatz(auftrag_obj=e1.auftrag, von=th.morgen_um(9), bis=th.morgen_um(11))
    with pytest.raises(IntegrityError), transaction.atomic():
        EinsatzMitarbeiter.objects.create(einsatz=ueberschneidend, mitarbeiter=m)
    danach = th.einsatz(auftrag_obj=e1.auftrag, von=th.morgen_um(10), bis=th.morgen_um(12))
    EinsatzMitarbeiter.objects.create(einsatz=danach, mitarbeiter=m)  # direkt im Anschluss ist erlaubt

    # Verschieben des Einsatzes wird an die Zuweisung weitergegeben
    e1.geplant_von = th.morgen_um(6)
    e1.geplant_bis = th.morgen_um(7)
    e1.save()
    z.refresh_from_db()
    assert z.zeitraum.lower == th.morgen_um(6)

    e1.delete()
    assert not EinsatzMitarbeiter.objects.filter(einsatz_id=e1.pk).exists()


def test_einsatz_ende_vor_beginn_wird_abgelehnt():
    with pytest.raises(IntegrityError), transaction.atomic():
        th.einsatz(von=th.morgen_um(10), bis=th.morgen_um(9))


def test_fuer_benutzer():
    admin = th.benutzer("admin")
    buero = th.benutzer("buero")
    konto_eigen = th.benutzer("mitarbeiter", email="eigen.pytest@example.org")
    konto_fremd = th.benutzer("mitarbeiter", email="fremd.pytest@example.org")
    konto_ohne = th.benutzer("mitarbeiter", email="ohne.pytest@example.org")
    eigen = th.mitarbeiter(vorname="Eigen", konto=konto_eigen)
    fremd = th.mitarbeiter(vorname="Fremd", konto=konto_fremd)

    a = th.auftrag()
    e_eigen = th.einsatz(a, von=th.morgen_um(8))
    e_beide = th.einsatz(a, von=th.morgen_um(12))
    e_fremd = th.einsatz(a, von=th.morgen_um(15))
    e_offen = th.einsatz(a, von=th.morgen_um(18))
    for e, leute in ((e_eigen, [eigen]), (e_beide, [eigen, fremd]), (e_fremd, [fremd])):
        for m in leute:
            EinsatzMitarbeiter.objects.create(einsatz=e, mitarbeiter=m)

    alle = {e_eigen, e_beide, e_fremd, e_offen}
    assert set(Einsatz.objects.fuer_benutzer(admin)) == alle
    assert set(Einsatz.objects.fuer_benutzer(buero)) == alle
    eigene = list(Einsatz.objects.fuer_benutzer(konto_eigen))
    assert set(eigene) == {e_eigen, e_beide} and len(eigene) == 2  # keine Dubletten
    assert set(Einsatz.objects.fuer_benutzer(konto_fremd)) == {e_beide, e_fremd}
    assert not Einsatz.objects.fuer_benutzer(konto_ohne).exists()
    assert not Einsatz.objects.fuer_benutzer(AnonymousUser()).exists()
    assert not Einsatz.objects.fuer_benutzer(None).exists()
    konto_eigen.aktiv = False
    konto_eigen.save()
    assert not Einsatz.objects.fuer_benutzer(konto_eigen).exists()
    # verkettbar
    assert set(Einsatz.objects.filter(geplant_von__hour__gte=0).fuer_benutzer(konto_fremd)) == {e_beide, e_fremd}


def test_rechnung_crud_und_nur_einmal_je_auftrag():
    a = th.auftrag(status="erledigt")
    r = Rechnung.objects.create(kunde=a.kunde, auftrag=a, summe_netto_cent=10000, summe_brutto_cent=11900)
    assert r.status == "entwurf" and r.rechnungsnummer is None
    with pytest.raises(IntegrityError), transaction.atomic():
        Rechnung.objects.create(kunde=a.kunde, auftrag=a, summe_netto_cent=1, summe_brutto_cent=1)
    r.status = "storniert"
    r.save()
    Rechnung.objects.create(kunde=a.kunde, auftrag=a, summe_netto_cent=1, summe_brutto_cent=1)  # nach Storno erlaubt
    with pytest.raises(IntegrityError), transaction.atomic():
        Rechnung.objects.create(kunde=a.kunde, summe_netto_cent=100, summe_brutto_cent=99)
