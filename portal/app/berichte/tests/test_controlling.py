"""Controlling-Kennzahlen aus echten Datensätzen."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from auftraege.models import Angebot, Rechnung
from berichte import controlling as c
from personal.models import Arbeitszeit
from stammdaten import testhilfen as th
from stammdaten.models import Leistung, Leistungsvereinbarung

pytestmark = pytest.mark.django_db
B = ZoneInfo("Europe/Berlin")


def test_kennzahlen_umsatz_kosten_rohertrag_quote():
    heute = timezone.localdate()
    a = th.auftrag(status="erledigt", verkaufspreis_netto_cent=50000, materialkosten_cent=2000)
    Rechnung.objects.create(kunde=a.kunde, auftrag=a, summe_netto_cent=50000, summe_brutto_cent=59500,
                            rechnungsdatum=heute, status="offen")
    m = th.mitarbeiter(stundenlohn_cent=1500)
    e = th.einsatz(a)
    beginn = datetime.combine(heute, datetime.min.time(), B).replace(hour=8)
    Arbeitszeit.objects.create(mitarbeiter=m, einsatz=e, beginn=beginn, ende=beginn.replace(hour=10))
    Angebot.objects.create(kunde=a.kunde, objekt=a.objekt, status="angenommen", freigegeben_am=timezone.now())
    Angebot.objects.create(kunde=a.kunde, objekt=a.objekt, status="abgelehnt", freigegeben_am=timezone.now())
    l = Leistung.objects.create(code="PT-TH", name="TH", einheit="je Reinigung", preis_netto_cent=3600)
    Leistungsvereinbarung.objects.create(objekt=a.objekt, leistung=l, intervall="woechentlich", wochentag=2,
                                         preis_netto_cent=3600, gueltig_von=date(2026, 1, 1))

    k = c.kennzahlen(c.Zeitraum.monat(heute))
    assert k["umsatz_cent"] == 50000 and k["offene_rechnungen_cent"] == 50000
    assert k["personalkosten_cent"] == 3984          # 2 h × 15 € × 1,328
    assert k["rohertrag_cent"] == 50000 - 3984 - 2000
    assert k["angebotsquote_prozent"] == 50.0
    assert k["wiederkehrend_monat_cent"] == 15600 and k["wiederkehrende_vertraege"] == 1
    assert c.kennzahlen(c.Zeitraum.jahr(heute))["umsatz_cent"] == 50000
    zeile = c.auftragsrentabilitaet()[0]
    assert zeile["deckungsbeitrag_cent"] == 50000 - 2000 - 3984
    assert len(c.umsatz_je_monat(heute.year)) == 12


def test_zeitraum_monat_dezember():
    z = c.Zeitraum.monat(date(2026, 12, 15))
    assert (z.von, z.bis) == (date(2026, 12, 1), date(2027, 1, 1))
