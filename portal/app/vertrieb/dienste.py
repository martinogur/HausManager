"""Akquise-Dienste: Lead prüfen und bewerten, Bestand importieren, Kontakt dokumentieren, Lead → Kunde.

Diese Funktionen sind die einzigen Schreibwege für Leads – Oberfläche, Agenten und
Management-Befehle nutzen sie gemeinsam (keine doppelte Logik).
"""

import csv
import re
from datetime import date, timedelta
from pathlib import Path

from django.db import transaction
from django.db.models.functions import Now
from django.utils import timezone

from agenten.models import Firmenparameter
from stammdaten.models import Kunde

from . import region, scoring
from .models import Lead, LeadKontakt, Leadstatus

# leads.csv „typ“ → Zielgruppe
TYP_ZUORDNUNG = {
    "hausverwaltung": "hausverwaltung", "weg": "hausverwaltung", "wohnungsbau": "wohnungsunternehmen",
    "gewerbe": "gewerbeimmobilie", "privat": "eigentuemer", "partner": "partnernetz",
}
WIEDERKEHREND = {"hausverwaltung", "wohnungsunternehmen"}
KUNDENTYP = {
    "hausverwaltung": "hausverwaltung", "wohnungsunternehmen": "wohnungsunternehmen", "eigentuemer": "privat",
    "privat": "privat", "partnernetz": "partner",
}


def _parameter(schluessel: str, standard):
    try:
        return Firmenparameter.objects.get(schluessel=schluessel).wert
    except Firmenparameter.DoesNotExist:
        return standard


def pruefen_und_bewerten(lead: Lead, speichern: bool = True) -> scoring.Bewertung:
    """Schritte 4 und 5 der Pipeline: Region prüfen, Potenzial bewerten (A/B/C)."""
    zentrum = _parameter("einsatzgebiet_zentrum", {"lat": 51.9069, "lon": 8.3786})
    radius = float(_parameter("einsatzgebiet_radius_km", 30))
    gebiet = region.pruefe_gebiet(lead.ort, (zentrum["lat"], zentrum["lon"]), radius)
    if lead.entfernung_km is None and gebiet.entfernung_km is not None:
        lead.entfernung_km = gebiet.entfernung_km
    lead.im_einsatzgebiet = gebiet.im_einsatzgebiet if gebiet.ort_erkannt else (
        float(lead.entfernung_km) <= radius if lead.entfernung_km is not None else None)
    bewertung = scoring.bewerte(scoring.LeadMerkmale(
        zielgruppe=lead.zielgruppe,
        regelmaessiger_bedarf=lead.regelmaessiger_bedarf,
        geschaetzter_monatsumsatz_cent=lead.geschaetzter_monatsumsatz_cent,
        entfernung_km=float(lead.entfernung_km) if lead.entfernung_km is not None else None,
        im_einsatzgebiet=lead.im_einsatzgebiet,
        hat_postanschrift=bool(lead.strasse and lead.plz),
        hat_telefon=bool(lead.telefon),
        widerspruch=lead.widerspruch_am is not None,
        vorbewertung=(lead.score_begruendung or {}).get("vorbewertung"),
    ))
    lead.score, lead.prioritaet = bewertung.score, bewertung.prioritaet
    lead.score_begruendung = {**bewertung.als_json(), "gebiet": gebiet.hinweis,
                              "vorbewertung": (lead.score_begruendung or {}).get("vorbewertung")}
    if lead.status == Leadstatus.NEU and lead.im_einsatzgebiet is not False:
        lead.status = Leadstatus.QUALIFIZIERT
    if speichern:
        lead.save()
    return bewertung


def kontaktwege(lead: Lead) -> list[tuple[str, str]]:
    return scoring.zulaessige_kontaktwege(
        lead.zielgruppe, hat_postanschrift=bool(lead.strasse and lead.plz), hat_telefon=bool(lead.telefon),
        hat_email=bool(lead.email), email_einwilligung=lead.email_einwilligung is not None,
        einladung_beleg=bool(lead.einladung_beleg), widerspruch=lead.widerspruch_am is not None,
    )


@transaction.atomic
def kontakt_dokumentieren(lead: Lead, *, kanal: str, zusammenfassung: str, durch: str, richtung: str = "ausgehend",
                          ergebnis: str | None = None, wiedervorlage_tage: int | None = 7, freigabe=None) -> LeadKontakt:
    """Schritte 10 und 11: Kontakt protokollieren, Status und Wiedervorlage setzen.
    Rechtsregeln (Widerspruch, E-Mail-Einwilligung, Agenten-Freigabe) prüft die Datenbank."""
    kontakt = LeadKontakt.objects.create(lead=lead, kanal=kanal, richtung=richtung, zusammenfassung=zusammenfassung,
                                         ergebnis=ergebnis, durch=durch, freigabe=freigabe)
    if richtung == "ausgehend" and lead.status in (Leadstatus.NEU, Leadstatus.QUALIFIZIERT, Leadstatus.KONTAKT_GEPLANT):
        lead.status = Leadstatus.KONTAKTIERT
    elif richtung == "eingehend" and lead.status in (Leadstatus.KONTAKTIERT, Leadstatus.KONTAKT_GEPLANT):
        lead.status = Leadstatus.IM_GESPRAECH
    if wiedervorlage_tage:
        lead.wiedervorlage_am = timezone.localdate() + timedelta(days=wiedervorlage_tage)
    lead.save()
    return kontakt


@transaction.atomic
def widerspruch_erfassen(lead: Lead, quelle: str) -> None:
    """Werbewiderspruch: sofort sperren (DSGVO Art. 21, UWG) – keine weiteren Werbekontakte."""
    # Datenbank-Uhr (wie bei lead_kontakte.zeitpunkt), damit auch in derselben Transaktion nichts durchrutscht
    lead.widerspruch_am = Now()
    lead.status = Leadstatus.GESPERRT
    lead.wiedervorlage_am = None
    lead.notizen = ((lead.notizen or "") + f"\nWiderspruch {timezone.localdate():%d.%m.%Y}: {quelle}").strip()
    lead.save()
    lead.refresh_from_db(fields=["widerspruch_am"])


@transaction.atomic
def in_kunden_umwandeln(lead: Lead) -> Kunde:
    """Schritt 13: Abschluss – Lead wird Kunde (Dubletten verhindert die DB über Name + PLZ)."""
    kunde = Kunde.objects.filter(name__iexact=lead.firma, plz=lead.plz).first() or Kunde.objects.create(
        name=lead.firma, typ=KUNDENTYP.get(lead.zielgruppe, "gewerbe"), status="aktiv", strasse=lead.strasse,
        plz=lead.plz, ort=lead.ort, telefon=lead.telefon, email=lead.email, webseite=lead.webseite,
        quelle=f"Lead {lead.leadnummer}",
    )
    lead.kunde, lead.status, lead.wiedervorlage_am = kunde, Leadstatus.GEWONNEN, None
    lead.save()
    return kunde


# ----------------------------------------------------------------------------- Import des Bestands
def _einladungen(pfad: Path) -> dict[str, str]:
    """E-Nummer → Beleg-URL aus leads/email-erlaubt.md (Spalte „Beleg-URL“)."""
    belege = {}
    if not pfad.exists():
        return belege
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        if not zeile.startswith("| E0"):
            continue
        spalten = [s.strip() for s in re.split(r"(?<!\\)\|", zeile)[1:-1]]
        if len(spalten) > 5 and spalten[5].startswith("http"):
            belege[spalten[0]] = spalten[5]
    return belege


def _adressen(pfad: Path) -> dict[str, dict]:
    if not pfad.exists():
        return {}
    with pfad.open(encoding="utf-8") as f:
        return {z["id"]: z for z in csv.DictReader(f, delimiter=";")}


def bestand_importieren(ordner: Path) -> dict:
    """Importiert leads/leads.csv (+ adressen.csv, email-erlaubt.md) idempotent über ``externe_ref``.

    Vorhandene Leads werden nicht überschrieben (das Portal ist ab dem Import führend)."""
    adressen = _adressen(ordner / "adressen.csv")
    belege = _einladungen(ordner / "email-erlaubt.md")
    neu = vorhanden = 0
    with (ordner / "leads.csv").open(encoding="utf-8") as f:
        zeilen = list(csv.DictReader(f, delimiter=";"))
    for z in zeilen:
        if Lead.objects.filter(externe_ref=z["id"]).exists():
            vorhanden += 1
            continue
        zielgruppe = "partnernetz" if z["id"].startswith("E") else TYP_ZUORDNUNG.get(z["typ"].strip().lower(), "sonstige")
        adr = adressen.get(z["id"], {})
        plz = adr.get("plz") or (re.search(r"\b(\d{5})\b", z["ort"]) or [None, None])[1]
        lead = Lead(
            externe_ref=z["id"], firma=z["firma"].strip(), zielgruppe=zielgruppe,
            strasse=adr.get("strasse") or None, plz=plz, ort=adr.get("ort") or z["ort"].strip() or None,
            webseite=z["webseite"] or None, telefon=z["telefon"] or None, email=z["email"] or None,
            ansprechpartner=z["ansprechpartner"] or None, position=z["position"] or None,
            quelle=z["quelle"].strip() or f"leads/leads.csv {z['id']}",
            objekte_geschaetzt=z["anzahl_objekte_geschaetzt"] or None,
            regelmaessiger_bedarf=True if zielgruppe in WIEDERKEHREND else None,
            status=Leadstatus.NEU, naechste_aktion=z["naechster_schritt"] or None,
            einladung_beleg=belege.get(z["id"]),
            notizen=z["grund"] or None,
            score_begruendung={"vorbewertung": z["prioritaet"] or None},
        )
        pruefen_und_bewerten(lead, speichern=False)
        if z["status"] == "entwurf_fertig" and lead.status == Leadstatus.QUALIFIZIERT:
            lead.status = Leadstatus.KONTAKT_GEPLANT   # Anschreiben liegt als Entwurf vor, noch nicht versendet
        lead.save()
        neu += 1
    return {"neu": neu, "vorhanden": vorhanden, "gesamt": len(zeilen)}


def fressnapf_vormerken() -> Lead:
    """Vom Inhaber genannte Verkaufschance (Projektauftrag 25.11.2026). Rückmeldung des Inhabers am 25.11.2026:
    Auftrag nicht erhalten → Status „verloren“ (bleibt für Auswertung und spätere Wiedervorlage erhalten)."""
    lead, _ = Lead.objects.get_or_create(
        externe_ref="INH-001",
        defaults=dict(
            firma="Fressnapf-Filiale Gütersloh", zielgruppe="einzelhandel", ort="Gütersloh",
            quelle="Angabe des Inhabers im Projektauftrag vom 25.11.2026",
            regelmaessiger_bedarf=True, geschaetzter_monatsumsatz_cent=89500, status=Leadstatus.VERLOREN,
            naechste_aktion="Auftrag nicht erhalten (Angebot 895 € netto/Monat). In 12 Monaten erneut anfragen.",
            notizen="Verloren: Auftrag nicht erhalten (Rückmeldung Inhaber 25.11.2026).",
        ),
    )
    if lead.score is None:
        pruefen_und_bewerten(lead)
    return lead
