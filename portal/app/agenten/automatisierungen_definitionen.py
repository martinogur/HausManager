"""Automatisierungskarte (siehe AUTOMATION_MAP.md): Auslöser → Agent/Aktion.

Ereignis-Automatisierungen legen Agentenaufträge idempotent an (Schlüssel aus Ereignis-ID),
Zeitplan-Automatisierungen je Zeitfenster genau einmal.
"""

from agenten.automatisierung import automatisierung, fenster_schluessel
from agenten.laufzeit import beauftragen
from auftraege import status as auftragsstatus
from auftraege.models import Angebot, Auftrag, Einsatz


def _auftrag(ereignis, agent, aufgabe_name, feld, prioritaet=5):
    a = beauftragen(agent, aufgabe_name, {feld: str(ereignis.bezug_id)}, ausgeloest_von=f"ereignis:{ereignis.id}",
                    idempotenz=f"ereignis:{ereignis.id}:{agent}:{aufgabe_name}", prioritaet=prioritaet)
    return {"agentenauftrag": str(a.id)}


def _neu_ist(status):
    return lambda e: e.daten.get("neu") == status


# ----------------------------------------------------------------------------- Ereignisse
@automatisierung("email_einordnen", "Neue E-Mail → Anfrage erkennen", "Kundenservice ordnet jede eingehende E-Mail ein.",
                 "ereignis:email.eingang")
def _email(e):
    return _auftrag(e, "kundenservice", "email_einordnen", "email_id", 2)


@automatisierung("anfrage_bearbeiten", "Neue Anfrage → Kundenservice", "Zusammenfassung, fehlende Angaben, Antwortentwurf zur Freigabe.",
                 "ereignis:anfrage.neu")
def _anfrage(e):
    return _auftrag(e, "kundenservice", "anfrage_bearbeiten", "anfrage_id", 2)


@automatisierung("anfrage_crm", "Anfrage → CRM-Eintrag (HubSpot)", "Überträgt neue Anfragen als Deal an HubSpot, sobald ein Token hinterlegt ist.",
                 "ereignis:anfrage.neu")
def _anfrage_crm(e):
    from integrationen import hubspot

    return hubspot.anfrage_exportieren(e.bezug_id)


@automatisierung("lead_bewerten", "Lead → Bewertung", "Sales prüft Region, bewertet A/B/C und schlägt einen zulässigen Kontakt vor.",
                 "ereignis:lead.neu")
def _lead(e):
    return _auftrag(e, "sales", "lead_bewerten", "lead_id")


@automatisierung("angebot_angenommen", "Angebot angenommen → Auftrag", "Legt zum angenommenen Angebot den Auftrag an (Status Freigegeben).",
                 "ereignis:angebot.status", bedingung=_neu_ist("angenommen"))
def _angebot_angenommen(e):
    angebot = Angebot.objects.get(pk=e.bezug_id)
    auftrag = Auftrag.objects.filter(angebot=angebot).first() or Auftrag.objects.create(
        kunde_id=angebot.kunde_id, objekt_id=angebot.objekt_id, angebot=angebot, status="bestaetigt",
        titel=f"Auftrag aus Angebot {angebot.angebotsnummer}", verkaufspreis_netto_cent=angebot.summe_netto_cent)
    return {"auftrag": auftrag.auftragsnummer}


@automatisierung("auftrag_disposition", "Auftrag freigegeben → Mitarbeiterzuweisung", "Dispositions-Agent plant Einsatz und schlägt Personal vor.",
                 "ereignis:auftrag.status", bedingung=_neu_ist("bestaetigt"))
def _disposition(e):
    auftrag = Auftrag.objects.get(pk=e.bezug_id)
    if auftrag.leistungsvereinbarung_id:
        return {"hinweis": "Dauerauftrag – Einsätze erzeugt die tägliche Planung"}
    return _auftrag(e, "dispatch", "einsatz_planen", "auftrag_id", 3)


@automatisierung("einsatz_erledigt", "Einsatz erledigt → Auftragsstatus", "Sind alle Einsätze erledigt, wird der Auftrag „erledigt“.",
                 "ereignis:einsatz.erledigt")
def _einsatz(e):
    einsatz = Einsatz.objects.select_related("auftrag").get(pk=e.bezug_id)
    auftrag = einsatz.auftrag
    if auftrag.leistungsvereinbarung_id:
        return {"hinweis": "Dauerauftrag bleibt offen"}
    offen = auftrag.einsaetze.exclude(status__in=["erledigt", "ausgefallen"]).exists()
    if not offen and auftrag.status in ("geplant", "in_arbeit"):
        auftragsstatus.status_wechseln(auftrag, "erledigt")
        return {"auftrag_erledigt": auftrag.auftragsnummer}
    return {"offen": offen}


@automatisierung("auftrag_qualitaet", "Auftrag erledigt → Qualitätsprüfung", "Fotos, Bericht, Zeiten und Deckungsbeitrag prüfen.",
                 "ereignis:auftrag.status", bedingung=_neu_ist("erledigt"))
def _qualitaet(e):
    return _auftrag(e, "quality", "auftrag_pruefen", "auftrag_id")


@automatisierung("auftrag_abrechnung", "Auftrag erledigt → Abrechnung vorbereiten", "Rechnungsentwurf zur Freigabe (Lexware führend).",
                 "ereignis:auftrag.status", bedingung=_neu_ist("erledigt"))
def _abrechnung(e):
    return _auftrag(e, "finance", "abrechnung_vorbereiten", "auftrag_id")


@automatisierung("bewerbung_hr", "Bewerbung → HR-Prozess", "Neutrale Zusammenfassung und Eingangsbestätigung zur Freigabe.",
                 "ereignis:bewerbung.neu")
def _bewerbung(e):
    return _auftrag(e, "hr", "bewerbung_aufnehmen", "bewerbung_id", 3)


# ----------------------------------------------------------------------------- Zeitpläne
def _zeitplan(code, agent, aufgabe_name, fenster, prioritaet=5, eingabe=None):
    a = beauftragen(agent, aufgabe_name, eingabe or {}, ausgeloest_von=f"zeitplan:{code}",
                    idempotenz=fenster_schluessel(code, fenster), prioritaet=prioritaet)
    return {"agentenauftrag": str(a.id)}


@automatisierung("tagesstart", "Tagesstart (CEO verteilt Routinearbeit)", "Wiederkehrende Einsätze, Wiedervorlagen, Zahlungen; Lagebild.",
                 "zeitplan:taeglich 06:30")
def _tagesstart(_, fenster):
    return _zeitplan("tagesstart", "ceo", "tagesstart", fenster, 3)


@automatisierung("wochenbericht", "Wöchentlicher Unternehmensbericht → Geschäftsführer", "Kennzahlen, Pipeline, Agenten, Entscheidungen.",
                 "zeitplan:woechentlich mo 07:00")
def _wochenbericht(_, fenster):
    return _zeitplan("wochenbericht", "ceo", "wochenbericht", fenster, 3)


@automatisierung("redaktionsplan", "Instagram-Content → Redaktionskalender", "Social-Wochenplan und Google-Beitrag für die nächste Woche.",
                 "zeitplan:woechentlich do 09:00")
def _redaktionsplan(_, fenster):
    a = _zeitplan("redaktionsplan", "social", "wochenplan", fenster)
    beauftragen("seo", "google_beitraege", {}, ausgeloest_von="zeitplan:redaktionsplan",
                idempotenz=fenster_schluessel("redaktionsplan_seo", fenster))
    return a


@automatisierung("ueberwachung", "Fehler in Workflows → Alarm", "Automations-Agent prüft stündlich Fehler, Staus und KI-Budget.",
                 "zeitplan:stuendlich :05")
def _ueberwachung(_, fenster):
    return _zeitplan("ueberwachung", "automation", "ueberwachung", fenster, 2)


@automatisierung("email_abruf", "IONOS-Postfach abrufen", "Holt neue E-Mails per IMAP (nur wenn Zugangsdaten hinterlegt sind).",
                 "zeitplan:alle 3 min")
def _email_abruf(_, fenster):
    from integrationen import ionos

    return ionos.abrufen()


@automatisierung("email_versand", "Freigegebene E-Mails versenden", "Versendet ausschließlich freigegebene E-Mails per SMTP.",
                 "zeitplan:alle 3 min")
def _email_versand(_, fenster):
    from integrationen import ionos

    return ionos.freigegebene_senden()


@automatisierung("rechnung_lexware", "Rechnung freigegeben → Lexware-Entwurf", "Überträgt freigegebene Rechnungsentwürfe als Entwurf an Lexware Office (nie festgeschrieben).",
                 "ereignis:freigabe.entschieden",
                 bedingung=lambda e: e.daten.get("art") == "rechnung_entwurf" and e.daten.get("status") == "freigegeben")
def _rechnung_lexware(e):
    from agenten.models import Freigabe
    from integrationen import lexware

    return lexware.entwurf_anlegen(Freigabe.objects.get(pk=e.bezug_id).vorschlag["rechnung_id"])


@automatisierung("zahlungsstatus", "Rechnung → Zahlungsstatus überwachen (Lexware)", "Gleicht den Status übertragener Rechnungen täglich mit Lexware ab.",
                 "zeitplan:taeglich 06:00")
def _zahlungsstatus(_, fenster):
    from integrationen import lexware

    return lexware.status_abgleichen()
