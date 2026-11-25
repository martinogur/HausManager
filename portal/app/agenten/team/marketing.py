"""Aufgaben von Marketing-, Social-Media- und SEO-Agent: Saisonplan, Wochenplan, Google-Beiträge."""

from datetime import date, datetime, time, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from agenten.freigaben import folgeaktion
from agenten.laufzeit import aufgabe
from marketing.models import SocialBeitrag

HASHTAGS_REGION = ["#gütersloh", "#kreisgütersloh", "#rhedawiedenbrück", "#verl", "#harsewinkel", "#owl", "#ostwestfalen"]
HASHTAGS_FACH = {
    "Winterdienst": ["#winterdienst", "#räumpflicht", "#streudienst"],
    "Treppenhausreinigung": ["#treppenhausreinigung", "#sauberkeit", "#hausverwaltung"],
    "Gartenpflege": ["#gartenpflege", "#rasenpflege", "#grünflächenpflege"],
    "Heckenschnitt": ["#heckenschnitt", "#gartenpflege"],
    "Laub": ["#laubentfernung", "#herbstputz"],
    "Objektbetreuung": ["#hausmeisterservice", "#objektbetreuung", "#hausmeister"],
    "Außenanlagen": ["#außenanlagen", "#grünflächen", "#gewerbeobjekt"],
}


def saisonthemen(monat: int) -> list[str]:
    """Saisonale Schwerpunkte (Heckenschnitt nur als Form-/Pflegeschnitt März–Sept., § 39 BNatSchG)."""
    if monat in (11, 12, 1, 2):
        return ["Winterdienst", "Objektbetreuung", "Treppenhausreinigung"]
    if monat == 3:
        return ["Winterdienst", "Außenanlagen", "Gartenpflege"]
    if monat in (4, 5, 6, 7, 8, 9):
        return ["Gartenpflege", "Heckenschnitt", "Außenanlagen", "Treppenhausreinigung"]
    return ["Laub", "Objektbetreuung", "Winterdienst"]   # Oktober


@aufgabe("marketing", "monatsplan")
def monatsplan(ctx):
    monat = int(ctx.eingabe.get("monat") or timezone.localdate().month)
    themen = saisonthemen(monat)
    return {"monat": monat, "schwerpunkte": themen,
            "massnahmen": [f"Instagram/Facebook: Schwerpunkt {themen[0]} (Vorher/Nachher aus echten Einsätzen)",
                           "Google-Profil: 1 Beitrag je Woche, Fotos aktueller Objekte (mit Erlaubnis)",
                           "Bewertungsbitte nach jedem erledigten Auftrag (ohne Gegenleistung)",
                           f"Akquise-Brief an A-Leads mit Bezug {themen[0]}"]}


SCHEMA_WOCHENPLAN = {
    "type": "object",
    "properties": {"beitraege": {"type": "array", "items": {
        "type": "object",
        "properties": {"index": {"type": "integer"}, "text": {"type": "string"}, "bildidee": {"type": "string"}},
        "required": ["index", "text", "bildidee"], "additionalProperties": False}}},
    "required": ["beitraege"],
    "additionalProperties": False,
}

# (Wochentag 0=Mo, Uhrzeit, Format) – 5 Posts, 3 Reels, 5 Stories
WOCHENRASTER = [
    (0, time(18, 0), "post"), (1, time(18, 0), "reel"), (2, time(18, 0), "post"), (3, time(18, 0), "reel"),
    (4, time(17, 0), "post"), (5, time(10, 0), "reel"), (5, time(12, 0), "post"), (6, time(11, 0), "post"),
    *[(t, time(8, 30), "story") for t in range(5)],
]
IDEEN = {
    "post": "Vorher/Nachher-Foto aus einem echten Einsatz ({thema}), Objekt nicht erkennbar (keine Hausnummern, Personen)",
    "reel": "15-Sek.-Reel: Arbeitsschritte {thema} im Zeitraffer, Untertitel, ohne Musik mit Rechten Dritter",
    "story": "Story mit Umfrage/Quiz zu {thema} und Link-Sticker zur Webseite",
}


def _regeltext(thema: str, fmt: str) -> str:
    texte = {
        "Winterdienst": "Schnee und Glätte? Wir räumen und streuen für Hausverwaltungen und Eigentümer in Gütersloh – mit Einsatzprotokoll.",
        "Treppenhausreinigung": "Ein sauberes Treppenhaus ist die Visitenkarte jedes Hauses. Wir reinigen zuverlässig, wöchentlich oder 14-täglich.",
        "Gartenpflege": "Rasen, Beete, Hecken: Wir halten Grünflächen gepflegt – fester Ansprechpartner, faire Festpreise.",
        "Heckenschnitt": "Form- und Pflegeschnitt für Hecken – sauber, mit Abtransport des Schnittguts.",
        "Laub": "Laub auf Wegen ist rutschig. Wir sorgen für sichere Zuwege rund um Ihr Objekt.",
        "Objektbetreuung": "Objektkontrolle mit Fotoprotokoll: Licht, Türen, Müllplätze – wir sehen nach, bevor etwas passiert.",
        "Außenanlagen": "Parkplatz, Pflaster, Grünstreifen: Außenanlagen von Gewerbeobjekten gepflegt und sicher.",
    }
    return (f"{texte[thema]} 📍 Gütersloh & 30 km Umkreis. Kostenlose Besichtigung: haus-meister-helden.de"
            + (" – Was meinst du?" if fmt == "story" else ""))


@aufgabe("social", "wochenplan")
def wochenplan(ctx):
    """Plan für die Woche ab ``woche_ab`` (Montag; Standard: nächste Woche) als Entwürfe + je Beitrag eine Freigabe."""
    if ctx.eingabe.get("woche_ab"):
        montag = date.fromisoformat(ctx.eingabe["woche_ab"])
    else:
        heute = timezone.localdate()
        montag = heute + timedelta(days=7 - heute.weekday())
    themen = saisonthemen(montag.month)
    slots = []
    for i, (tag, uhr, fmt) in enumerate(WOCHENRASTER):
        thema = themen[i % len(themen)]
        slots.append({"index": i, "format": fmt, "thema": thema,
                      "zeit": timezone.make_aware(datetime.combine(montag + timedelta(days=tag), uhr))})
    daten, quelle = ctx.ki_oder_regel(
        lambda: {"beitraege": [{"index": s["index"], "text": _regeltext(s["thema"], s["format"]),
                                "bildidee": IDEEN[s["format"]].format(thema=s["thema"])} for s in slots]},
        zweck="social_wochenplan", schema=SCHEMA_WOCHENPLAN, effort="low", max_tokens=6000,
        system=("Du schreibst Instagram-Texte für Hausmeister Helden (Gütersloh). Ton: per du, freundlich, bodenständig, "
                "Marke: Zuverlässig. Sauber. Professionell. Keine erfundenen Kunden, Zahlen oder Bewertungen, keine "
                "Preisversprechen ohne Preisliste. Max. 300 Zeichen je Text, 1–2 Emojis, Aufruf zur kostenlosen Besichtigung. "
                "Gib für jeden Index Text und Bildidee (echte Einsatzfotos, ohne erkennbare Personen/Adressen)."),
        eingabe="\n".join(f"{s['index']}: {s['format']} am {timezone.localtime(s['zeit']):%a %d.%m. %H:%M}, Thema {s['thema']}" for s in slots),
    )
    texte = {b["index"]: b for b in daten["beitraege"]}
    angelegt = []
    for s in slots:
        if s["index"] not in texte:
            continue
        try:
            with transaction.atomic():
                beitrag = SocialBeitrag.objects.create(
                    plattform="instagram", format=s["format"], geplant_fuer=s["zeit"], thema=s["thema"],
                    text=texte[s["index"]]["text"], bildidee=texte[s["index"]]["bildidee"],
                    hashtags=HASHTAGS_REGION[:4] + HASHTAGS_FACH[s["thema"]], status="zur_freigabe",
                    erstellt_von="agent:social")
        except IntegrityError:
            continue   # Slot schon belegt
        f = ctx.freigabe_anfordern(art="social_beitrag", titel=f"Instagram {s['format']} {timezone.localtime(s['zeit']):%a %d.%m.}: {s['thema']}",
                                   vorschlag={"beitrag_id": str(beitrag.id), "text": beitrag.text},
                                   bezug=("social_beitraege", beitrag.id))
        beitrag.freigabe = f
        beitrag.save()
        angelegt.append(str(beitrag.id))
    return {"woche_ab": montag.isoformat(), "beitraege": len(angelegt), "quelle": quelle}


@folgeaktion("social_beitrag")
def _beitrag_freigegeben(freigabe, benutzer):
    b = SocialBeitrag.objects.get(pk=freigabe.vorschlag["beitrag_id"])
    b.text = freigabe.vorschlag.get("text", b.text)
    b.status, b.freigegeben_von, b.freigegeben_am = "freigegeben", benutzer, timezone.now()
    b.save()


@folgeaktion("social_beitrag", bei="abgelehnt")
def _beitrag_abgelehnt(freigabe, benutzer):
    SocialBeitrag.objects.filter(pk=freigabe.vorschlag["beitrag_id"]).update(status="verworfen")


@aufgabe("seo", "google_beitraege")
def google_beitraege(ctx):
    """Ein Beitrag je Woche fürs Google-Unternehmensprofil (lokales SEO), als Entwurf mit Freigabe."""
    heute = timezone.localdate()
    montag = heute + timedelta(days=7 - heute.weekday())
    thema = saisonthemen(montag.month)[0]
    zeit = timezone.make_aware(datetime.combine(montag + timedelta(days=1), time(9, 0)))
    try:
        with transaction.atomic():
            b = SocialBeitrag.objects.create(plattform="google", format="post", geplant_fuer=zeit, thema=thema,
                                             text=_regeltext(thema, "post").replace("Was meinst du?", ""),
                                             status="zur_freigabe", erstellt_von="agent:seo")
    except IntegrityError:
        return {"hinweis": "Beitrag für diese Woche existiert bereits"}
    f = ctx.freigabe_anfordern(art="social_beitrag", titel=f"Google-Beitrag {zeit:%d.%m.}: {thema}",
                               vorschlag={"beitrag_id": str(b.id), "text": b.text}, bezug=("social_beitraege", b.id))
    b.freigabe = f
    b.save()
    return {"beitrag": str(b.id), "thema": thema}
