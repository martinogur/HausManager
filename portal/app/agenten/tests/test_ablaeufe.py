"""Durchgehende Abläufe: Ereignis (DB-Trigger) → Automatisierung → Agent → Freigabe → Folgeaktion."""

from datetime import date, time, timedelta
from email.message import EmailMessage

import pytest
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from agenten import freigaben, laufzeit
from agenten.models import AgentenAuftrag, Freigabe
from agenten.team.betrieb import termine, verfuegbare_mitarbeiter
from agenten.team.service import regel_einordnung
from auftraege import status as st
from auftraege.models import Anfrage, Angebot, Auftrag, Einsatz, Rechnung
from integrationen import ionos
from kommunikation.models import EmailProtokoll
from marketing.models import SocialBeitrag
from personal.models import Arbeitszeit, Verfuegbarkeit
from stammdaten import testhilfen as th
from stammdaten.models import Leistung, Leistungsvereinbarung
from vertrieb.models import Lead

from .conftest import alles_abarbeiten

pytestmark = pytest.mark.django_db


def _eingang(betreff, text, von="kunde@example.org"):
    return EmailProtokoll.objects.create(richtung="eingang", postfach="info@example.org", von=von, an=["info@example.org"], betreff=betreff, text_auszug=text,
                                         message_id=f"<{betreff}@example.org>")


def test_regel_einordnung():
    a = regel_einordnung("Anfrage Treppenhausreinigung", "Wir suchen wöchentliche Reinigung, 3 Etagen, Teststraße 4, 33330")
    assert a["kategorie"] == "anfrage" and a["leistungen"] == ["Treppenhausreinigung"] and a["ort"] == "33330"
    assert "Telefonnummer für Rückfragen" in a["fehlende_angaben"]
    assert regel_einordnung("Bewerbung als Aushilfe", "Lebenslauf anbei")["kategorie"] == "bewerbung"
    assert regel_einordnung("Newsletter", "Zum Abmelden hier klicken")["kategorie"] == "werbung_spam"


def test_email_wird_anfrage_mit_antwortentwurf_und_freigabe(system, buero):
    mail = _eingang("Angebot Winterdienst", "Bitte Angebot für Winterdienst, 25 m Gehweg, Musterweg 3, 33330 Gütersloh")
    alles_abarbeiten()
    mail.refresh_from_db()
    assert mail.status == "zugeordnet" and mail.anfrage is not None
    anfrage = mail.anfrage
    assert anfrage.gewuenschte_leistungen == ["Winterdienst"] and anfrage.status == "in_bearbeitung"
    entwurf = EmailProtokoll.objects.get(richtung="ausgang", anfrage=anfrage)
    assert entwurf.status == "entwurf" and entwurf.an == ["kunde@example.org"] and "Besichtigung" in entwurf.entwurf_text
    f = Freigabe.objects.get(art="email_versand", bezug_id=entwurf.id)
    # Mitarbeiter dürfen nicht freigeben
    with pytest.raises(PermissionDenied):
        freigaben.entscheiden(f, th.benutzer("mitarbeiter", "ma.agenten@example.org"), freigeben=True)
    freigaben.entscheiden(f, buero, freigeben=True, vorschlag={"text": "Geänderter Text"})
    entwurf.refresh_from_db()
    assert entwurf.status == "freigegeben" and entwurf.entwurf_text == "Geänderter Text" and entwurf.freigegeben_von == buero
    with pytest.raises(ValueError):
        freigaben.entscheiden(f, buero, freigeben=False)


def test_ionos_abruf_und_versand_nur_freigegeben(system, buero, monkeypatch):
    monkeypatch.setenv("IONOS_MAIL_BENUTZER", "info@example.org")
    monkeypatch.setenv("IONOS_MAIL_PASSWORT", "test-nicht-echt")
    m = EmailMessage()
    m["From"], m["To"], m["Subject"], m["Message-ID"] = "Kunde <k@example.org>", "info@example.org", "Hecke schneiden", "<m1@example.org>"
    m.set_content("Bitte Heckenschnitt, 20 m.")
    roh = m.as_bytes()

    class FakeImap:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def login(self, *a): pass
        def select(self, *a, **k): pass
        def uid(self, befehl, *args):
            return ("OK", [b"1"]) if befehl == "search" else ("OK", [(b"1 (BODY[] {1})", roh), b")"])

    assert ionos.abrufen(FakeImap) == {"neu": 1}
    assert ionos.abrufen(FakeImap) == {"neu": 0}   # Message-ID verhindert Doppelimport
    eingang = EmailProtokoll.objects.get(message_id="<m1@example.org>")
    assert eingang.von == "k@example.org" and "Heckenschnitt" in eingang.text_auszug

    gesendet = []

    class FakeSmtp(FakeImap):
        def send_message(self, nachricht): gesendet.append(nachricht)

    entwurf = EmailProtokoll.objects.create(richtung="ausgang", postfach="info@example.org", von="info@example.org",
                                            an=["k@example.org"], betreff="Antwort", status="entwurf", entwurf_text="Hallo")
    assert ionos.freigegebene_senden(FakeSmtp) == {"gesendet": 0}
    entwurf.status, entwurf.freigegeben_von, entwurf.freigegeben_am = "freigegeben", buero, timezone.now()
    entwurf.save()
    assert ionos.freigegebene_senden(FakeSmtp) == {"gesendet": 1}
    entwurf.refresh_from_db()
    assert entwurf.status == "gesendet" and gesendet[0]["To"] == "k@example.org"


def test_integrationen_ohne_zugang_melden_nur(system, monkeypatch):
    for name in ("IONOS_MAIL_BENUTZER", "HUBSPOT_TOKEN", "LEXWARE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    from integrationen import hubspot, lexware

    assert "nicht eingerichtet" in ionos.abrufen()["hinweis"]
    assert "nicht eingerichtet" in hubspot.anfrage_exportieren(Anfrage.objects.create(kanal="webseite").id)["hinweis"]
    assert "nicht eingerichtet" in lexware.status_abgleichen()["hinweis"]


def test_lexware_rechnungsdaten_pflichtfelder(system):
    from integrationen import lexware

    a = th.auftrag(status="erledigt")
    r = Rechnung.objects.create(kunde=a.kunde, auftrag=a, summe_netto_cent=10000, summe_brutto_cent=11900)
    d = lexware.rechnungsdaten(r)
    assert {"voucherDate", "address", "lineItems", "totalPrice", "taxConditions", "shippingConditions"} <= set(d)
    pos = d["lineItems"][0]
    assert pos["type"] == "custom" and pos["unitPrice"] == {"currency": "EUR", "netAmount": 100.0, "taxRatePercentage": 19}
    assert d["address"]["countryCode"] == "DE" and d["shippingConditions"]["shippingType"] == "service"


def test_lead_neu_wird_bewertet_und_kontaktvorschlag(system, buero):
    lead = Lead.objects.create(firma="Pytest Wohnbau eG", zielgruppe="wohnungsunternehmen", ort="Gütersloh", plz="33330",
                               strasse="Testweg 1", telefon="05241 1", quelle="Impressum (Test)", regelmaessiger_bedarf=True,
                               geschaetzter_monatsumsatz_cent=120000)
    alles_abarbeiten()
    lead.refresh_from_db()
    assert lead.prioritaet == "A" and lead.status == "kontakt_geplant"
    f = Freigabe.objects.get(art="lead_kontakt", bezug_id=lead.id)
    assert f.vorschlag["kanal"] == "brief"
    assert "keine weiteren Informationen" in f.vorschlag["text"]   # Widerspruchshinweis im Brief
    freigaben.entscheiden(f, buero, freigeben=True)
    lead.refresh_from_db()
    assert "Freigegeben" in lead.naechste_aktion


def _verfuegbar(m):
    for tag in range(1, 8):
        Verfuegbarkeit.objects.create(mitarbeiter=m, wochentag=tag, von=time(6), bis=time(20))


def test_auftrag_bis_rechnung(system, buero):
    m = th.mitarbeiter(stundenlohn_cent=1500)
    _verfuegbar(m)
    a = th.auftrag(status="angebot", verkaufspreis_netto_cent=30000, geschaetzte_minuten=90,
                   faellig_am=timezone.localdate() + timedelta(days=3))
    st.status_wechseln(a, "bestaetigt")
    alles_abarbeiten()
    einsatz = Einsatz.objects.get(auftrag=a)
    f = Freigabe.objects.get(art="einsatz_zuweisung")
    assert f.vorschlag["mitarbeiter_id"] == str(m.id)
    freigaben.entscheiden(f, buero, freigeben=True)
    a.refresh_from_db()
    einsatz.refresh_from_db()
    assert a.status == "geplant" and einsatz.status == "zugewiesen"
    # Einsatz erledigt (ohne Fotos) → Auftrag erledigt → Qualität meldet Mängel, Finanzen bereiten Rechnung vor
    Arbeitszeit.objects.create(mitarbeiter=m, einsatz=einsatz, beginn=einsatz.geplant_von, ende=einsatz.geplant_bis)
    einsatz.status = "erledigt"
    einsatz.save()
    alles_abarbeiten()
    a.refresh_from_db()
    assert a.status == "erledigt"
    qualitaet = AgentenAuftrag.objects.get(agent="quality", aufgabe="auftrag_pruefen")
    assert not qualitaet.ergebnis["ok"] and any("Vorher-Foto" in x for x in qualitaet.ergebnis["maengel"])
    rechnung = Rechnung.objects.get(auftrag=a)
    assert rechnung.status == "entwurf" and rechnung.summe_brutto_cent == 35700
    freigaben.entscheiden(Freigabe.objects.get(art="rechnung_entwurf"), buero, freigeben=True)
    a.refresh_from_db()
    assert a.status == "abgerechnet"


def test_keine_verfuegbarkeit_eskaliert(system):
    a = th.auftrag(status="angebot")
    st.status_wechseln(a, "bestaetigt")
    alles_abarbeiten()
    auftrag = AgentenAuftrag.objects.get(agent="dispatch", aufgabe="einsatz_planen")
    assert auftrag.status == "eskaliert"
    assert Freigabe.objects.filter(art="eskalation", bezug_id=auftrag.id).exists()


def test_verfuegbarkeit_beachtet_ueberschneidung_und_abwesenheit(system):
    from personal.models import Abwesenheit

    m1, m2 = th.mitarbeiter("Ana", "Eins"), th.mitarbeiter("Ben", "Zwei", email="ben@example.org")
    _verfuegbar(m1), _verfuegbar(m2)
    von = th.morgen_um(9)
    assert {x.id for x in verfuegbare_mitarbeiter(von, von + timedelta(hours=1))} == {m1.id, m2.id}
    Abwesenheit.objects.create(mitarbeiter=m1, von=timezone.localdate(), bis=timezone.localdate() + timedelta(days=5), grund="Urlaub")
    assert [x.id for x in verfuegbare_mitarbeiter(von, von + timedelta(hours=1))] == [m2.id]


def test_angebot_angenommen_wird_auftrag(system, buero):
    k = th.kunde()
    o = th.objekt(k, treppenhaeuser=1, etagen=3)
    a = laufzeit.sofort_ausfuehren(laufzeit.beauftragen(
        "angebot", "angebot_berechnen", {"objekt_id": str(o.id), "leistungen": {"reinigung": "woechentlich", "kontrollen_monat": 1}},
        ausgeloest_von="test"))
    assert a.status == "erledigt" and a.ergebnis["netto_cent"] == 15600 + 2700
    angebot = Angebot.objects.get(objekt=o)
    assert angebot.summe_netto_cent == 18300 and angebot.status == "entwurf" and angebot.freigegeben_am is None
    freigaben.entscheiden(Freigabe.objects.get(art="angebot_versand"), buero, freigeben=True)
    angebot.refresh_from_db()
    assert angebot.freigegeben_von == buero
    angebot.status = "angenommen"
    angebot.save()
    alles_abarbeiten()
    auftrag = Auftrag.objects.get(angebot=angebot)
    assert auftrag.verkaufspreis_netto_cent == 18300


def test_wiederkehrende_einsaetze(system):
    o = th.objekt(th.kunde())
    l = Leistung.objects.create(code="PT-W", name="Treppenhaus", einheit="je Reinigung", preis_netto_cent=3600)
    m = th.mitarbeiter()
    v = Leistungsvereinbarung.objects.create(objekt=o, leistung=l, intervall="woechentlich", wochentag=2, preis_netto_cent=3600,
                                             gueltig_von=date(2026, 1, 1), standard_mitarbeiter=m)
    assert termine(v, date(2026, 11, 23), date(2026, 12, 6)) == [date(2026, 11, 24), date(2026, 12, 1)]
    zw = Leistungsvereinbarung(intervall="zweiwoechentlich", wochentag=1, gueltig_von=date(2026, 11, 2))
    assert termine(zw, date(2026, 11, 1), date(2026, 11, 30)) == [date(2026, 11, 2), date(2026, 11, 16), date(2026, 11, 30)]
    erst = laufzeit.sofort_ausfuehren(laufzeit.beauftragen("dispatch", "wiederkehrende_einsaetze", ausgeloest_von="t1"))
    assert erst.ergebnis["neue_einsaetze"] == 2
    zweit = laufzeit.sofort_ausfuehren(laufzeit.beauftragen("dispatch", "wiederkehrende_einsaetze", ausgeloest_von="t2"))
    assert zweit.ergebnis["neue_einsaetze"] == 0
    assert set(Einsatz.objects.values_list("status", flat=True)) == {"zugewiesen"}


def test_social_wochenplan_13_beitraege_mit_freigabe(system, buero):
    a = laufzeit.sofort_ausfuehren(laufzeit.beauftragen("social", "wochenplan", {"woche_ab": "2026-11-30"}, ausgeloest_von="t"))
    assert a.status == "erledigt" and a.ergebnis["beitraege"] == 13
    formate = list(SocialBeitrag.objects.values_list("format", flat=True))
    assert formate.count("post") == 5 and formate.count("reel") == 3 and formate.count("story") == 5
    b = SocialBeitrag.objects.filter(format="reel").first()
    assert "#gütersloh" in b.hashtags and b.status == "zur_freigabe"
    assert {x.thema for x in SocialBeitrag.objects.all()} == {"Winterdienst", "Objektbetreuung", "Treppenhausreinigung"}
    freigaben.entscheiden(b.freigabe, buero, freigeben=True)
    b.refresh_from_db()
    assert b.status == "freigegeben" and b.freigegeben_von == buero
    nochmal = laufzeit.sofort_ausfuehren(laufzeit.beauftragen("social", "wochenplan", {"woche_ab": "2026-11-30"}, ausgeloest_von="t2"))
    assert nochmal.ergebnis["beitraege"] == 0   # Slots schon belegt


def test_ueberwachung_meldet_fehlerhafte_automatisierung(system):
    from agenten.models import Automatisierung

    Automatisierung.objects.filter(code="anfrage_crm").update(fehler_in_folge=4, letzter_fehler="HTTP 401")
    a = laufzeit.sofort_ausfuehren(laufzeit.beauftragen("automation", "ueberwachung", ausgeloest_von="t"))
    assert not a.ergebnis["ok"] and "HTTP 401" in a.ergebnis["probleme"][0]
    assert Freigabe.objects.filter(art="eskalation", prioritaet="hoch").exists()


def test_tagesstart_verteilt_und_berichtet(system):
    a = laufzeit.sofort_ausfuehren(laufzeit.beauftragen("ceo", "tagesstart", ausgeloest_von="t"))
    assert a.status == "erledigt" and len(a.ergebnis["verteilt"]) == 3
    kinder = AgentenAuftrag.objects.filter(eltern=a)
    assert {k.agent_id for k in kinder} == {"dispatch", "sales", "finance"} and all(k.tiefe == 1 for k in kinder)
    alles_abarbeiten()
    assert set(AgentenAuftrag.objects.filter(eltern=a).values_list("status", flat=True)) == {"erledigt"}
