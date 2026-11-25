"""Aufgaben von Sales-, Lead-Research- und Angebots-Agent."""

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from agenten.freigaben import folgeaktion
from agenten.laufzeit import Eskalation, aufgabe
from auftraege.models import Angebot, Angebotsposition, Anfrage
from stammdaten.models import Objekt
from vertrieb import dienste, kalkulation
from vertrieb.models import Lead, Leadstatus, OFFENE_STATUS

FIRMA = "Hausmeister Helden, Inhaber Martin Ogur, Auf der Benkert 68, 33330 Gütersloh, Tel. 05241 3389748"
TON = ("Schreibe auf Deutsch, per „Sie“, freundlich, bodenständig, konkret, ohne Übertreibungen. "
       "Erfinde keine Referenzen, Zahlen, Zertifikate oder Preise. Kein Werbedruck, keine Fristen-Tricks.")


# ============================================================================= Lead-Research
@aufgabe("lead_research", "lead_aufnehmen")
def lead_aufnehmen(ctx):
    """Eingabe: Lead-Felder inkl. ``quelle`` (Pflicht). Dubletten werden erkannt, nicht doppelt angelegt."""
    d = dict(ctx.eingabe)
    if not (d.get("firma") and d.get("quelle") and d.get("zielgruppe")):
        raise ValueError("firma, zielgruppe und quelle sind Pflicht (DSGVO: Herkunft dokumentieren)")
    erlaubt = {f.name for f in Lead._meta.concrete_fields} - {"id", "leadnummer", "status", "score", "prioritaet",
                                                               "kunde", "erstellt_am", "geaendert_am", "widerspruch_am"}
    vorhanden = Lead.objects.filter(firma__iexact=d["firma"].strip(), plz=d.get("plz")).first()
    if vorhanden:
        return {"dublette": vorhanden.leadnummer}
    lead = Lead.objects.create(**{k: v for k, v in d.items() if k in erlaubt})
    return {"lead": lead.leadnummer}   # Ereignis lead.neu → Sales bewertet


@aufgabe("lead_research", "bestand_importieren")
def bestand_importieren(ctx):
    ordner = Path(ctx.eingabe.get("ordner") or Path(settings.BASE_DIR).parents[1] / "leads")
    return dienste.bestand_importieren(ordner)


# ============================================================================= Sales
@aufgabe("sales", "lead_bewerten")
def lead_bewerten(ctx):
    lead = Lead.objects.get(pk=ctx.eingabe["lead_id"])
    ctx.schritt("Region und Potenzial prüfen")
    b = dienste.pruefen_und_bewerten(lead)
    ergebnis = {"lead": lead.leadnummer, "score": b.score, "prioritaet": b.prioritaet, "status": lead.status}
    if lead.status == Leadstatus.QUALIFIZIERT and b.prioritaet in ("A", "B"):
        ergebnis["kontaktvorschlag"] = _kontaktvorschlag(ctx, lead, nachfassen=False)
    return ergebnis


def _vorhandener_entwurf(lead: Lead) -> str | None:
    """Liegt im Repository schon ein Brief-/E-Mail-Entwurf (akquise/briefe/<ref>-*.md)?"""
    if not lead.externe_ref:
        return None
    basis = Path(settings.BASE_DIR).parents[1] / "akquise"
    for ordner in ("briefe", "emails", "einladungen"):
        treffer = sorted((basis / ordner).glob(f"{lead.externe_ref}-*.md"))
        if treffer:
            return str(treffer[0].relative_to(basis.parent))
    return None


def _regeltext(lead: Lead, kanal: str, nachfassen: bool) -> str:
    anrede = f"Guten Tag {lead.ansprechpartner}," if lead.ansprechpartner and "," not in lead.ansprechpartner else "Guten Tag,"
    if kanal == "telefon":
        return (f"Telefonleitfaden {lead.firma}: Vorstellen (Hausmeister Helden, Gütersloh) → Anlass "
                f"{'Nachfrage zu unserem Schreiben' if nachfassen else 'regionaler Hausmeisterservice'} → Bedarf erfragen "
                "(Treppenhaus, Winterdienst, Grünpflege, Objektkontrolle) → kostenlose Objektbesichtigung anbieten → "
                "bei „kein Interesse“ höflich beenden und Widerspruch notieren.")
    return (f"{anrede}\n\nwir sind Hausmeister Helden aus Gütersloh und betreuen Wohn- und Gewerbeobjekte im Kreis "
            "Gütersloh: Treppenhausreinigung, Winterdienst mit Einsatzprotokoll, Grünflächen- und Heckenpflege sowie "
            "Objektkontrollen mit Fotoprotokoll – mit festem Ansprechpartner und Reaktion innerhalb von 24 Stunden.\n\n"
            f"{'Gern greifen wir unser Schreiben von neulich auf: ' if nachfassen else ''}"
            "Eine Objektbesichtigung und ein unverbindliches Festpreisangebot sind kostenlos.\n\n"
            f"Mit freundlichen Grüßen\nMartin Ogur\n{FIRMA}\n\n"
            "Sie möchten keine weiteren Informationen von uns? Ein kurzer Hinweis genügt.")


SCHEMA_KONTAKT = {
    "type": "object",
    "properties": {"betreff": {"type": "string"}, "text": {"type": "string"}, "begruendung": {"type": "string"}},
    "required": ["betreff", "text", "begruendung"],
    "additionalProperties": False,
}


def _kontaktvorschlag(ctx, lead: Lead, nachfassen: bool) -> str | None:
    wege = dienste.kontaktwege(lead)
    if not wege:
        return None
    kanal, rechtsgrund = wege[0]
    entwurf = _vorhandener_entwurf(lead)
    if entwurf and not nachfassen:
        text, quelle = f"Vorhandener, geprüfter Entwurf: {entwurf}", "repository"
    else:
        daten, quelle = ctx.ki_oder_regel(
            lambda: {"betreff": f"Hausmeisterservice für {lead.firma}", "text": _regeltext(lead, kanal, nachfassen),
                     "begruendung": "Vorlage (regelbasiert)"},
            zweck="lead_kontaktvorschlag", schema=SCHEMA_KONTAKT, effort="low", bezug=("leads", lead.id),
            system=f"Du schreibst Akquise-Texte für {FIRMA}. {TON} Kanal: {kanal}. Halte dich an § 7 UWG; "
                   "füge bei Briefen einen Hinweis zum Widerspruch an. Maximal 150 Wörter.",
            eingabe=(f"Firma: {lead.firma}\nZielgruppe: {lead.get_zielgruppe_display()}\nOrt: {lead.ort}\n"
                     f"Bekannt: {lead.notizen or '-'}\nObjekte: {lead.objekte_geschaetzt or '-'}\n"
                     f"{'Nachfass-Kontakt nach erstem Schreiben.' if nachfassen else 'Erstkontakt.'}"),
        )
        text = daten["text"]
    f = ctx.freigabe_anfordern(
        art="lead_kontakt", titel=f"{'Nachfassen' if nachfassen else 'Erstkontakt'} {lead.firma} per {kanal}",
        begruendung=f"Priorität {lead.prioritaet} (Score {lead.score}). Rechtsgrundlage: {rechtsgrund}.",
        vorschlag={"lead_id": str(lead.id), "kanal": kanal, "text": text, "quelle": quelle, "nachfassen": nachfassen},
        bezug=("leads", lead.id), prioritaet="hoch" if lead.prioritaet == "A" else "normal",
    )
    lead.status = Leadstatus.KONTAKT_GEPLANT if lead.status in (Leadstatus.NEU, Leadstatus.QUALIFIZIERT) else lead.status
    lead.naechste_aktion = f"Freigabe {f.freigabenummer}: {kanal}"
    lead.save()
    return f.freigabenummer


@aufgabe("sales", "wiedervorlagen")
def wiedervorlagen(ctx):
    """Täglich: fällige Wiedervorlagen → Nachfassvorschlag (max. 10 je Tag, A vor B vor C)."""
    heute = timezone.localdate()
    faellig = (Lead.objects.filter(status__in=OFFENE_STATUS, wiedervorlage_am__lte=heute, widerspruch_am__isnull=True)
               .order_by("prioritaet", "wiedervorlage_am")[:10])
    erstellt = []
    for lead in faellig:
        nr = _kontaktvorschlag(ctx, lead, nachfassen=True)
        if nr:
            erstellt.append(nr)
        lead.wiedervorlage_am = heute + timezone.timedelta(days=14)
        lead.save(update_fields=["wiedervorlage_am"])
    return {"faellig": len(faellig), "vorschlaege": erstellt}


@folgeaktion("lead_kontakt")
def _lead_kontakt_freigegeben(freigabe, benutzer):
    lead = Lead.objects.get(pk=freigabe.vorschlag["lead_id"])
    lead.naechste_aktion = (f"Freigegeben ({freigabe.freigabenummer}): {freigabe.vorschlag['kanal']} durchführen und "
                            "danach als Kontakt dokumentieren.")
    lead.save()


@folgeaktion("lead_kontakt", bei="abgelehnt")
def _lead_kontakt_abgelehnt(freigabe, benutzer):
    lead = Lead.objects.get(pk=freigabe.vorschlag["lead_id"])
    lead.naechste_aktion = f"Kontaktvorschlag abgelehnt ({freigabe.kommentar or 'ohne Kommentar'})"
    if lead.status == Leadstatus.KONTAKT_GEPLANT:
        lead.status = Leadstatus.QUALIFIZIERT
    lead.save()


# ============================================================================= Angebot
def _objektdaten(eingabe: dict, objekt: Objekt | None) -> kalkulation.Objektdaten:
    """Werte aus der Eingabe, fehlende aus dem Objekt (Treppenhäuser, Etagen, Aufzug, Gehweg, Grünfläche)."""
    e = eingabe.get("leistungen", {})
    o = kalkulation.Objektdaten(
        treppenhaeuser=e.get("treppenhaeuser", objekt.treppenhaeuser if objekt else 0) or 0,
        etagen=e.get("etagen", objekt.etagen if objekt else 0) or 0,
        aufzug=e.get("aufzug", objekt.aufzug if objekt else False),
        reinigung=e.get("reinigung"),
        winterdienst_lfm=Decimal(str(e["winterdienst_lfm"])) if e.get("winterdienst_lfm") else (
            objekt.gehweg_meter if objekt and e.get("winterdienst") else None),
        rasen_qm=Decimal(str(e.get("rasen_qm", 0))), beet_qm=Decimal(str(e.get("beet_qm", 0))),
        hecke_lfm=Decimal(str(e.get("hecke_lfm", 0))), garten=e.get("garten", {}),
        muell_termine_monat=e.get("muell_termine_monat", 0), muell_leerungen_monat=e.get("muell_leerungen_monat", 0),
        muellplatz=e.get("muellplatz", False), kontrollen_monat=e.get("kontrollen_monat", 0),
    )
    return o


@aufgabe("angebot", "angebot_berechnen")
def angebot_berechnen(ctx):
    """Eingabe: objekt_id, leistungen{…}, optional anfrage_id, ausfuehrung ('inhaber'|'minijob'), laufzeit_monate."""
    objekt = Objekt.objects.select_related("kunde").get(pk=ctx.eingabe["objekt_id"])
    ctx.schritt("Kalkulation")
    k = kalkulation.kalkuliere(_objektdaten(ctx.eingabe, objekt), ctx.eingabe.get("ausfuehrung", "inhaber"))
    if not k.positionen:
        raise Eskalation("Keine kalkulierbaren Leistungen angegeben – bitte Leistungsumfang festlegen.")
    anfrage = Anfrage.objects.filter(pk=ctx.eingabe.get("anfrage_id")).first() if ctx.eingabe.get("anfrage_id") else None
    angebot = Angebot.objects.create(kunde=objekt.kunde, objekt=objekt, anfrage=anfrage,
                                     laufzeit_monate=ctx.eingabe.get("laufzeit_monate", 12),
                                     gueltig_bis=timezone.localdate() + timezone.timedelta(days=30))
    for nr, p in enumerate(k.positionen, start=1):
        Angebotsposition.objects.create(angebot=angebot, pos=nr, beschreibung=p.bezeichnung, menge=1,
                                        einheit=f"Monat ({p.kostenart})", einzelpreis_netto_cent=p.monat_netto_cent,
                                        intervall="monatlich")
    angebot.refresh_from_db()
    f = ctx.freigabe_anfordern(
        art="angebot_versand", titel=f"Angebot {angebot.angebotsnummer} {objekt.kunde.name}: {k.monat_netto_cent / 100:.2f} € netto/Monat",
        begruendung=(f"Arbeitszeit {k.minuten_monat} Min./Monat, Selbstkosten {k.selbstkosten_monat_cent / 100:.2f} €, "
                     f"Marge {k.marge_prozent} %. " + " ".join(k.warnungen)).strip(),
        vorschlag={"angebot_id": str(angebot.id), "positionen": [p.bezeichnung for p in k.positionen],
                   "monat_netto_cent": k.monat_netto_cent, "warnungen": k.warnungen},
        bezug=("angebote", angebot.id), prioritaet="hoch" if k.warnungen else "normal",
    )
    return {"angebot": angebot.angebotsnummer, "netto_cent": k.monat_netto_cent, "marge_prozent": str(k.marge_prozent),
            "freigabe": f.freigabenummer}


@folgeaktion("angebot_versand")
def _angebot_freigegeben(freigabe, benutzer):
    angebot = Angebot.objects.get(pk=freigabe.vorschlag["angebot_id"])
    angebot.freigegeben_von, angebot.freigegeben_am = benutzer, timezone.now()
    angebot.save()
