"""Lead-Dienste mit Datenbank: Bewertung, Import des echten Bestands, Rechtsregeln, Umwandlung in Kunde."""

from pathlib import Path

import pytest
from django.db import IntegrityError, transaction

from vertrieb import dienste
from vertrieb.models import Lead, LeadKontakt

pytestmark = pytest.mark.django_db
LEADS_ORDNER = Path(__file__).resolve().parents[4] / "leads"


def _lead(**kw):
    basis = dict(firma="Pytest Verwaltung GmbH", zielgruppe="hausverwaltung", ort="Gütersloh", plz="33330",
                 strasse="Teststraße 1", telefon="05241 0", quelle="Test", regelmaessiger_bedarf=True)
    return Lead.objects.create(**{**basis, **kw})


def test_pruefen_und_bewerten_setzt_region_score_status():
    lead = _lead(geschaetzter_monatsumsatz_cent=90000)
    b = dienste.pruefen_und_bewerten(lead)
    lead.refresh_from_db()
    assert lead.im_einsatzgebiet is True and float(lead.entfernung_km) == 0.0
    assert (lead.score, lead.prioritaet) == (b.score, "A")
    assert lead.status == "qualifiziert" and lead.score_begruendung["gruende"]


def test_bestand_importieren_ist_idempotent():
    erst = dienste.bestand_importieren(LEADS_ORDNER)
    assert erst["neu"] == erst["gesamt"] >= 50
    zweit = dienste.bestand_importieren(LEADS_ORDNER)
    assert zweit == {"neu": 0, "vorhanden": erst["gesamt"], "gesamt": erst["gesamt"]}
    l001 = Lead.objects.get(externe_ref="L001")
    assert l001.zielgruppe == "wohnungsunternehmen" and l001.plz == "33330" and l001.strasse
    assert l001.status == "kontakt_geplant" and l001.prioritaet in {"A", "B", "C"}
    assert l001.score_begruendung["vorbewertung"] == "A"
    e001 = Lead.objects.get(externe_ref="E001")
    assert e001.zielgruppe == "partnernetz" and e001.einladung_beleg.startswith("https://")
    # Werbe-E-Mail nur, wo eine Einladung belegt ist
    assert e001.email_werbung_erlaubt and not l001.email_werbung_erlaubt
    assert all(l.quelle for l in Lead.objects.all())


def test_fressnapf_wird_nicht_als_gewonnen_gefuehrt():
    lead = dienste.fressnapf_vormerken()
    assert lead.status == "angebot" and lead.kunde is None
    assert lead.geschaetzter_monatsumsatz_cent == 89500 and "klären" in lead.naechste_aktion
    assert dienste.fressnapf_vormerken().pk == lead.pk


def test_kontakt_dokumentieren_und_uwg_regeln():
    lead = _lead(email="info@example.org")
    dienste.kontakt_dokumentieren(lead, kanal="brief", zusammenfassung="Vorstellungsbrief", durch="chef@example.org")
    lead.refresh_from_db()
    assert lead.status == "kontaktiert" and lead.wiedervorlage_am
    assert [w for w, _ in dienste.kontaktwege(lead)] == ["brief", "telefon"]
    with pytest.raises(IntegrityError), transaction.atomic():
        dienste.kontakt_dokumentieren(lead, kanal="email", zusammenfassung="Werbung", durch="chef@example.org")
    dienste.widerspruch_erfassen(lead, "Anruf: bitte keine Werbung")
    assert dienste.kontaktwege(lead) == []
    with pytest.raises(IntegrityError), transaction.atomic():
        dienste.kontakt_dokumentieren(lead, kanal="brief", zusammenfassung="Brief", durch="chef@example.org")
    assert LeadKontakt.objects.filter(lead=lead).count() == 1


def test_in_kunden_umwandeln():
    lead = _lead()
    kunde = dienste.in_kunden_umwandeln(lead)
    lead.refresh_from_db()
    assert lead.status == "gewonnen" and lead.kunde == kunde and kunde.typ == "hausverwaltung"
    assert dienste.in_kunden_umwandeln(_lead(firma="Pytest Verwaltung GmbH", plz="33332")).pk != kunde.pk
