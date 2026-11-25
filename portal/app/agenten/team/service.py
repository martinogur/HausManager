"""Aufgaben von Kundenservice- und HR-Agent: E-Mails einordnen, Anfragen bearbeiten, Bewerbungen aufnehmen."""

import re

from django.utils import timezone

from agenten.freigaben import folgeaktion
from agenten.laufzeit import aufgabe
from auftraege.models import Anfrage
from kommunikation.models import EmailProtokoll
from personal.models import Bewerbung
from stammdaten.models import Ansprechpartner, Kunde

from .vertrieb import FIRMA, TON

POSTFACH = "info@haus-meister-helden.de"

LEISTUNGEN = {
    "Treppenhausreinigung": r"treppenhaus|hausflur|flurreinigung",
    "Gebäudereinigung": r"gebäudereinigung|unterhaltsreinigung|büroreinigung|reinigung",
    "Winterdienst": r"winterdienst|schnee|streu|glätte",
    "Gartenpflege": r"garten|rasen|mähen|beet|grünfläche|grünpflege",
    "Heckenschnitt": r"hecke",
    "Hausmeisterservice": r"hausmeister|objektbetreuung|hauswart",
    "Kleinreparaturen": r"reparatur|defekt|kaputt",
    "Mülltonnen-Service": r"mülltonne|müllplatz|tonnen",
    "Außenanlagen": r"außenanlage|parkplatz|hof|pflaster",
}
KATEGORIEN = ["anfrage", "bewerbung", "kunde_bestand", "rechnung_zahlung", "werbung_spam", "sonstiges"]

SCHEMA_EMAIL = {
    "type": "object",
    "properties": {
        "kategorie": {"type": "string", "enum": KATEGORIEN},
        "zusammenfassung": {"type": "string"},
        "leistungen": {"type": "array", "items": {"type": "string"}},
        "ort": {"type": "string"},
        "fehlende_angaben": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["kategorie", "zusammenfassung", "leistungen", "ort", "fehlende_angaben"],
    "additionalProperties": False,
}
SCHEMA_ANTWORT = {
    "type": "object",
    "properties": {"betreff": {"type": "string"}, "text": {"type": "string"}},
    "required": ["betreff", "text"],
    "additionalProperties": False,
}


def regel_einordnung(betreff: str, text: str) -> dict:
    """Regelbasierte Einordnung (ohne KI) – auch Grundlage, wenn die KI aus ist."""
    t = f"{betreff}\n{text}".lower()
    if re.search(r"newsletter|unsubscribe|abmelden|gewinnspiel|seo-agentur|backlinks|kryptowährung", t):
        kategorie = "werbung_spam"
    elif re.search(r"bewerb|lebenslauf|minijob|aushilfe gesucht|stelle als|initiativbewerbung", t):
        kategorie = "bewerbung"
    elif re.search(r"rechnung|zahlung|mahnung|überweis", t):
        kategorie = "rechnung_zahlung"
    elif any(re.search(m, t) for m in LEISTUNGEN.values()) or re.search(r"angebot|anfrage|preis|kosten|besichtigung", t):
        kategorie = "anfrage"
    else:
        kategorie = "sonstiges"
    leistungen = [name for name, muster in LEISTUNGEN.items() if re.search(muster, t)]
    if "Treppenhausreinigung" in leistungen and "Gebäudereinigung" in leistungen:
        leistungen.remove("Gebäudereinigung")
    plz = re.search(r"\b(3\d{4}|4\d{4}|5\d{4})\b", t)
    fehlend = []
    if kategorie == "anfrage":
        if not plz and not re.search(r"straße|str\.|weg\b|platz\b", t):
            fehlend.append("Objektadresse")
        if "Treppenhausreinigung" in leistungen and not re.search(r"etage|stock|geschoss", t):
            fehlend.append("Anzahl Etagen/Treppenhäuser")
        if not re.search(r"wöchentlich|monatlich|14-tägig|einmalig|regelmäßig|intervall", t):
            fehlend.append("Gewünschter Rhythmus")
        if not re.search(r"\b0\d{3,4}[\s/-]?\d+|\+49", t):
            fehlend.append("Telefonnummer für Rückfragen")
    return {"kategorie": kategorie, "zusammenfassung": (betreff or text[:120] or "").strip(),
            "leistungen": leistungen, "ort": plz.group(1) if plz else "", "fehlende_angaben": fehlend}


def _kunde_zu(absender: str) -> tuple[Kunde | None, Ansprechpartner | None]:
    ap = Ansprechpartner.objects.filter(email__iexact=absender).select_related("kunde").first()
    if ap:
        return ap.kunde, ap
    return Kunde.objects.filter(email__iexact=absender).first(), None


@aufgabe("kundenservice", "email_einordnen")
def email_einordnen(ctx):
    mail = EmailProtokoll.objects.get(pk=ctx.eingabe["email_id"])
    if mail.status != "neu" or mail.richtung != "eingang":
        return {"uebersprungen": mail.status}
    regel = regel_einordnung(mail.betreff or "", mail.text_auszug or "")
    daten, quelle = ctx.ki_oder_regel(
        lambda: regel, zweck="email_einordnen", schema=SCHEMA_EMAIL, effort="low", bezug=("email_protokolle", mail.id),
        system=("Du ordnest eingehende E-Mails eines Hausmeisterdienstes in Gütersloh ein. Fasse sachlich in 1–2 Sätzen "
                "zusammen, nenne gewünschte Leistungen, Ort/PLZ falls genannt, und welche Angaben für ein Angebot fehlen "
                "(Adresse, Etagen, Flächen, Rhythmus, Telefon). Gesundheits- oder Bankdaten nicht wiedergeben."),
        eingabe=f"Von: {mail.von}\nBetreff: {mail.betreff}\n\n{(mail.text_auszug or '')[:6000]}",
    )
    kunde, ap = _kunde_zu(mail.von)
    mail.ki_zusammenfassung, mail.kunde, mail.ansprechpartner = daten["zusammenfassung"], kunde, ap
    ergebnis = {"kategorie": daten["kategorie"], "quelle": quelle}
    if daten["kategorie"] == "anfrage":
        anfrage = Anfrage.objects.create(
            kunde=kunde, ansprechpartner=ap, kanal="email", betreff=mail.betreff,
            gewuenschte_leistungen=daten["leistungen"] or None, ki_zusammenfassung=daten["zusammenfassung"],
            fehlende_angaben=daten["fehlende_angaben"] or None,
        )  # Ereignis anfrage.neu → anfrage_bearbeiten
        mail.anfrage, mail.status = anfrage, "zugeordnet"
        ergebnis["anfrage"] = anfrage.anfragenummer
    elif daten["kategorie"] == "werbung_spam" and regel["kategorie"] == "werbung_spam":
        mail.status = "verworfen"   # nur wenn Regel und KI übereinstimmen; im Postfach bleibt die Mail erhalten
    else:
        mail.status = "zugeordnet"
        if daten["kategorie"] == "bewerbung":
            ctx.freigabe_anfordern(art="sonstiges", titel=f"Bewerbung per E-Mail von {mail.von}",
                                   begruendung="Bitte als Bewerbung übernehmen (Datenschutzhinweis senden).",
                                   vorschlag={"email_id": str(mail.id), "zusammenfassung": daten["zusammenfassung"]},
                                   bezug=("email_protokolle", mail.id))
    mail.save()
    return ergebnis


def _regelantwort(anfrage: Anfrage) -> dict:
    fehlend = anfrage.fehlende_angaben or []
    leistungen = ", ".join(anfrage.gewuenschte_leistungen or []) or "Ihr Objekt"
    teile = [
        "Guten Tag,", "",
        f"vielen Dank für Ihre Anfrage zu {leistungen}. Gern erstellen wir Ihnen ein Festpreisangebot – "
        "am besten nach einer kostenlosen Objektbesichtigung.",
    ]
    if fehlend:
        teile += ["", "Damit wir schnell kalkulieren können, fehlen uns noch:", *[f"– {f}" for f in fehlend]]
    teile += ["", "Nennen Sie uns gern zwei Terminvorschläge für die Besichtigung.", "",
              "Mit freundlichen Grüßen", "Martin Ogur", FIRMA]
    return {"betreff": f"Ihre Anfrage {anfrage.anfragenummer} – Hausmeister Helden", "text": "\n".join(teile)}


@aufgabe("kundenservice", "anfrage_bearbeiten")
def anfrage_bearbeiten(ctx):
    anfrage = Anfrage.objects.get(pk=ctx.eingabe["anfrage_id"])
    eingang = EmailProtokoll.objects.filter(anfrage=anfrage, richtung="eingang").order_by("erstellt_am").first()
    daten, quelle = ctx.ki_oder_regel(
        lambda: _regelantwort(anfrage), zweck="antwort_entwurf", schema=SCHEMA_ANTWORT, effort="low",
        bezug=("anfragen", anfrage.id),
        system=(f"Du schreibst Antwortentwürfe für {FIRMA}. {TON} Biete eine kostenlose Besichtigung an, frage gezielt "
                "nach fehlenden Angaben, nenne keine Preise ohne Kalkulation. Maximal 140 Wörter. Signatur: Martin Ogur."),
        eingabe=(f"Anfrage {anfrage.anfragenummer}\nZusammenfassung: {anfrage.ki_zusammenfassung or anfrage.betreff}\n"
                 f"Leistungen: {anfrage.gewuenschte_leistungen}\nFehlende Angaben: {anfrage.fehlende_angaben}"),
    )
    if anfrage.status == "neu":
        anfrage.status = "in_bearbeitung"
        anfrage.save()
    if eingang is None:
        f = ctx.freigabe_anfordern(art="sonstiges", titel=f"Anfrage {anfrage.anfragenummer} ({anfrage.kanal}) beantworten",
                                   begruendung="Keine E-Mail-Adresse – telefonisch bzw. über den Eingangskanal antworten.",
                                   vorschlag={"text": daten["text"]}, bezug=("anfragen", anfrage.id))
        return {"freigabe": f.freigabenummer, "quelle": quelle}
    entwurf = EmailProtokoll.objects.create(
        richtung="ausgang", postfach=POSTFACH, von=POSTFACH, an=[eingang.von], betreff=daten["betreff"],
        in_reply_to=eingang.message_id, antwort_auf=eingang, anfrage=anfrage, kunde=anfrage.kunde,
        status="entwurf", entwurf_text=daten["text"],
    )
    f = ctx.freigabe_anfordern(art="email_versand", titel=f"Antwort an {eingang.von}: {daten['betreff']}",
                               begruendung=f"Antwortentwurf ({quelle}) zu {anfrage.anfragenummer}.",
                               vorschlag={"email_id": str(entwurf.id), "text": daten["text"]},
                               bezug=("email_protokolle", entwurf.id), prioritaet="hoch")
    return {"entwurf": str(entwurf.id), "freigabe": f.freigabenummer, "quelle": quelle}


@folgeaktion("email_versand")
def _email_freigegeben(freigabe, benutzer):
    """Freigabe → E-Mail-Status „freigegeben“. Den Versand übernimmt der SMTP-Job (nur freigegebene Mails)."""
    mail = EmailProtokoll.objects.get(pk=freigabe.vorschlag["email_id"])
    mail.entwurf_text = freigabe.vorschlag.get("text", mail.entwurf_text)
    mail.status, mail.freigegeben_von, mail.freigegeben_am = "freigegeben", benutzer, timezone.now()
    mail.save()


@folgeaktion("email_versand", bei="abgelehnt")
def _email_abgelehnt(freigabe, benutzer):
    EmailProtokoll.objects.filter(pk=freigabe.vorschlag["email_id"], status="entwurf").update(status="verworfen")


# ============================================================================= HR
SCHEMA_BEWERBUNG = {
    "type": "object",
    "properties": {"zusammenfassung": {"type": "string"}, "offene_fragen": {"type": "array", "items": {"type": "string"}}},
    "required": ["zusammenfassung", "offene_fragen"],
    "additionalProperties": False,
}


@aufgabe("hr", "bewerbung_aufnehmen")
def bewerbung_aufnehmen(ctx):
    b = Bewerbung.objects.select_related("stelle").get(pk=ctx.eingabe["bewerbung_id"])
    fakten = (f"Stelle: {b.stelle.titel}\nWohnort: {b.wohnort or '-'}\nVerfügbar ab: {b.verfuegbar_ab or '-'}\n"
              f"Stunden/Woche: {b.stunden_pro_woche or '-'}\nFührerschein: {b.fuehrerschein}\n"
              f"Erfahrung: {b.erfahrung or '-'}\nNachricht: {b.nachricht or '-'}")

    def regel():
        fragen = [f for f, fehlt in (("Verfügbar ab?", not b.verfuegbar_ab), ("Stunden pro Woche?", not b.stunden_pro_woche),
                                      ("Führerschein?", b.fuehrerschein is None)) if fehlt]
        return {"zusammenfassung": f"{b.stelle.titel}; {b.wohnort or 'Wohnort offen'}; "
                                   f"{b.stunden_pro_woche or '?'} h/Woche; ab {b.verfuegbar_ab or '?'}",
                "offene_fragen": fragen}

    daten, quelle = ctx.ki_oder_regel(
        regel, zweck="bewerbung_zusammenfassen", schema=SCHEMA_BEWERBUNG, effort="low", bezug=("bewerbungen", b.id),
        system=("Fasse eine Bewerbung neutral in 2–3 Sätzen zusammen (Fakten: Verfügbarkeit, Stunden, Erfahrung, "
                "Führerschein) und nenne offene Fragen. KEINE Bewertung, KEINE Empfehlung, keine Merkmale nach AGG "
                "(Alter, Herkunft, Geschlecht, Religion, Gesundheit)."),
        eingabe=fakten,
    )
    b.ki_zusammenfassung = daten["zusammenfassung"] + (
        f"\nOffene Fragen: {', '.join(daten['offene_fragen'])}" if daten["offene_fragen"] else "")
    b.save()
    text = (f"Guten Tag {b.vorname} {b.nachname},\n\nvielen Dank für Ihre Bewerbung als {b.stelle.titel}. "
            "Wir melden uns innerhalb von 5 Werktagen bei Ihnen.\n\nMit freundlichen Grüßen\nMartin Ogur\n" + FIRMA)
    entwurf = EmailProtokoll.objects.create(richtung="ausgang", postfach=POSTFACH, von=POSTFACH, an=[b.email],
                                            betreff="Ihre Bewerbung bei Hausmeister Helden", bewerbung=b,
                                            status="entwurf", entwurf_text=text)
    f = ctx.freigabe_anfordern(art="email_versand", titel=f"Eingangsbestätigung an {b.vorname} {b.nachname}",
                               vorschlag={"email_id": str(entwurf.id), "text": text}, bezug=("email_protokolle", entwurf.id))
    return {"bewerbung": b.bewerbungsnummer, "quelle": quelle, "freigabe": f.freigabenummer}

