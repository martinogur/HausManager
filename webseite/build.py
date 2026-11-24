#!/usr/bin/env python3
"""Baut die Webseite von Hausmeister Helden nach webseite/public/.

Alle Inhalte stehen in diesem Skript (FIRMA, LEISTUNGEN, FAQ, ORTE) und in
inhalte/ratgeber/*.md. Ändern -> `python3 webseite/build.py` -> public/ hochladen.
Keine Abhängigkeiten außer Python 3.
"""
import datetime as dt
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "public"
HEUTE = dt.date.today()

# ---------------------------------------------------------------- Stammdaten
FIRMA = {
    "name": "Hausmeister Helden",
    "inhaber": "Martin Ogur",
    "strasse": "Auf der Benkert 68",
    "plz": "33330",
    "ort": "Gütersloh",
    "tel": "05241 3389748",
    "tel_link": "+4952413389748",
    "wa": "4952413389748",
    "mail": "info@haus-meister-helden.de",
    "url": "https://www.haus-meister-helden.de",
    "zeiten": "Mo–Sa, 7:00–20:00 Uhr",
    "slogan": "Ihr Haus. Unsere Pflicht.",
    "geo": (51.9069, 8.3786),  # ungefähr Gütersloh – für Google
}
ORTE = ["Gütersloh", "Rheda-Wiedenbrück", "Verl", "Harsewinkel", "Herzebrock-Clarholz",
        "Steinhagen", "Halle (Westf.)", "Schloß Holte-Stukenbrock", "Bielefeld-Süd", "Rietberg"]

ICON = {
    "reinigung": '<path d="M3 21h18M6 21V10l6-5 6 5v11"/><path d="M10 21v-5h4v5"/><path d="M17 3l1 2 2 1-2 1-1 2-1-2-2-1 2-1z"/>',
    "winter": '<path d="M12 2v20M4.9 6l14.2 12M19.1 6L4.9 18"/><path d="M9 3.5l3 2 3-2M9 20.5l3-2 3 2M3 10l3.3.8L5.5 14M21 10l-3.3.8.8 3.2"/>',
    "garten": '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10z"/><path d="M2 21c0-3 1.9-5.4 5.2-6.1C9.5 14.5 12 13 13 12"/>',
    "reparatur": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9l-3.8 3.8z"/>',
    "muell": '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6M10 11v6M14 11v6"/>',
    "kontrolle": '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M9 14l2 2 4-4"/>',
    "phone": '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
    "mail": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 7l-10 6L2 7"/>',
    "pin": '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "check": '<path d="M5 12l5 5 9-10"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "bolt": '<path d="M13 2L3 14h9l-1 8 10-12h-9z"/>',
    "euro": '<path d="M18 7a7 7 0 1 0 0 10M4 10h10M4 14h10"/>',
}
WA_SVG = ('<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="M16 3C8.8 3 3 8.7 3 15.8c0 2.3.6 4.5 1.8 6.4L3 29l7-1.8a13 13 0 0 0 6 1.5c7.2 0 13-5.7 13-12.8S23.2 3 16 3zm0 23.4c-1.9 0-3.8-.5-5.4-1.5l-.4-.2-4.1 1.1 1.1-4-.3-.4a10.5 10.5 0 0 1-1.6-5.6C5.3 10 10.1 5.3 16 5.3s10.7 4.7 10.7 10.5S21.9 26.4 16 26.4zm5.9-7.9c-.3-.2-1.9-.9-2.2-1s-.5-.2-.7.2-.8 1-1 1.2-.4.2-.7.1a8.7 8.7 0 0 1-4.3-3.7c-.3-.6.3-.5.9-1.6.1-.2 0-.4 0-.5l-1-2.4c-.3-.6-.5-.5-.7-.5h-.6c-.2 0-.6.1-.9.4s-1.1 1.1-1.1 2.7 1.2 3.1 1.3 3.3c.2.2 2.3 3.5 5.5 4.9 2 .9 2.8.9 3.8.8.6-.1 1.9-.8 2.2-1.5s.3-1.3.2-1.5c-.1-.1-.3-.2-.7-.4z"/></svg>')


def icon(name, cls=""):
    return f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICON[name]}</svg>'


LOGO = ('<svg viewBox="0 0 240 56" role="img" aria-label="Hausmeister Helden">'
        '<g fill="none" stroke="#7ccc13" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M5 31L29 9l10 9v-8h7v14l11 10"/></g>'
        '<g fill="#7ccc13"><rect x="21" y="25" width="5" height="5" rx="1"/><rect x="28" y="25" width="5" height="5" rx="1"/>'
        '<rect x="21" y="32" width="5" height="5" rx="1"/><rect x="28" y="32" width="5" height="5" rx="1"/></g>'
        '<text x="68" y="31" font-family="Archivo,system-ui,sans-serif" font-weight="850" font-stretch="82%" font-size="27" fill="currentColor" textLength="164" lengthAdjust="spacingAndGlyphs">HAUSMEISTER</text>'
        '<text x="69" y="50" font-family="Archivo,system-ui,sans-serif" font-weight="500" font-size="12.5" fill="currentColor" textLength="160" lengthAdjust="spacing">HELDEN</text>'
        '</svg>')

# ---------------------------------------------------------------- Leistungen
LEISTUNGEN = [
    {
        "slug": "treppenhausreinigung-guetersloh", "icon": "reinigung", "name": "Treppenhausreinigung",
        "kurz": "Regelmäßige Reinigung von Treppenhäusern, Fluren und Gemeinschaftsbereichen – sauber, zuverlässig, termingerecht.",
        "preis": "ab 8 €", "einheit": "pro Einheit / Woche",
        "titel": "Treppenhausreinigung in Gütersloh",
        "intro": "Ein sauberes Treppenhaus ist die Visitenkarte jedes Mehrfamilienhauses. Wir reinigen Treppen, Flure, Handläufe, Eingangsbereiche und Kellergänge nach festem Plan – damit Mieter zufrieden sind und Sie keine Beschwerden mehr bearbeiten müssen.",
        "umfang": ["Treppenstufen und Podeste kehren und feucht wischen", "Handläufe, Geländer, Lichtschalter und Türgriffe reinigen",
                   "Eingangsbereich, Briefkastenanlage und Haustür säubern", "Kellerflure und Gemeinschaftsräume nach Absprache",
                   "Spinnweben entfernen, Fensterbänke abwischen", "Kurze Gebäudekontrolle bei jedem Einsatz – inklusive"],
        "fuer": "Hausverwaltungen, WEG-Verwaltungen, Vermieter und Eigentümergemeinschaften in Gütersloh und Umgebung.",
        "faq": [("Wie oft wird gereinigt?", "Wöchentlich, 14-täglich oder monatlich – ganz nach Bedarf. Bei wöchentlicher Reinigung (4× im Monat) erhalten Sie 10 % Treuerabatt."),
                ("Bringen Sie Reinigungsmittel mit?", "Ja, Material und Reinigungsmittel bringen wir mit."),
                ("Was passiert, wenn etwas kaputt ist?", "Wir melden Schäden sofort mit Foto und beheben Kleinigkeiten auf Wunsch direkt mit.")],
    },
    {
        "slug": "winterdienst-guetersloh", "icon": "winter", "name": "Winterdienst",
        "kurz": "Schneeräumung, Eisentfernung und Streudienst für sichere Zugänge. Saisonal von Oktober bis März.",
        "preis": "ab 8 €", "einheit": "pro Einheit / Woche (Okt–März)",
        "titel": "Winterdienst in Gütersloh",
        "intro": "Als Eigentümer oder Verwalter tragen Sie die Verkehrssicherungspflicht – rutscht jemand vor Ihrem Haus aus, kann das teuer werden. Wir übernehmen das Räumen und Streuen zuverlässig und dokumentieren jeden Einsatz, damit Sie im Ernstfall einen Nachweis haben.",
        "umfang": ["Räumen von Gehwegen, Hauszugängen, Treppen und Mülltonnenplätzen", "Streuen mit abstumpfenden bzw. zulässigen Streumitteln",
                   "Einsatz zu den in Gütersloh geltenden Räumzeiten", "Kontrollfahrten bei Glätte- und Schneewarnung",
                   "Einsatzdokumentation mit Datum und Uhrzeit", "Saisonvertrag von Oktober bis März"],
        "fuer": "Hausverwaltungen, Vermieter, Gewerbeobjekte, Praxen und Privathäuser in Gütersloh und Umgebung.",
        "faq": [("Ab wann muss geräumt werden?", "Die genauen Zeiten regelt die Straßenreinigungssatzung der jeweiligen Stadt. Wir richten unsere Einsätze danach aus – sprechen Sie uns an."),
                ("Übernehmen Sie die Haftung?", "Wir übernehmen die Durchführung des Winterdienstes vertraglich und dokumentieren jeden Einsatz. Details regelt der Winterdienstvertrag."),
                ("Kann ich noch mitten in der Saison einsteigen?", "Ja, solange Kapazitäten frei sind. Fragen Sie am besten frühzeitig an.")],
    },
    {
        "slug": "gartenpflege-guetersloh", "icon": "garten", "name": "Gartenarbeit",
        "kurz": "Rasenmähen, Heckenpflege, Laub entfernen – Ihre Grünanlagen gepflegt das ganze Jahr über.",
        "preis": "30 €", "einheit": "pro Einheit / Monat",
        "titel": "Gartenpflege in Gütersloh",
        "intro": "Gepflegte Außenanlagen steigern den Wert einer Immobilie und sorgen für zufriedene Mieter. Wir kümmern uns um Rasen, Hecken, Beete und Laub – regelmäßig und ohne dass Sie daran denken müssen.",
        "umfang": ["Rasen mähen und Kanten schneiden", "Hecken- und Strauchschnitt", "Laub entfernen im Herbst",
                   "Beete von Unkraut befreien", "Wege und Plätze sauber halten", "Grünschnitt-Entsorgung nach Absprache"],
        "fuer": "Wohnanlagen, Mehrfamilienhäuser, Gewerbeflächen und Privatgärten in Gütersloh und Umgebung.",
        "faq": [("Machen Sie auch einmalige Einsätze?", "Ja – zum Beispiel einen Frühjahrs- oder Herbstschnitt. Für Wohnanlagen empfehlen wir die laufende Pflege."),
                ("Wer entsorgt den Grünschnitt?", "Auf Wunsch übernehmen wir die Entsorgung – das klären wir im Angebot.")],
    },
    {
        "slug": "kleinreparaturen-guetersloh", "icon": "reparatur", "name": "Kleinreparaturen",
        "kurz": "Türen, Beleuchtung, kleine Defekte – wir beheben Schäden schnell und fachgerecht, bevor sie größer werden.",
        "preis": "35 €", "einheit": "pro Stunde",
        "titel": "Kleinreparaturen & Hausmeister-Arbeiten in Gütersloh",
        "intro": "Eine klemmende Tür, ein defektes Licht im Flur, eine lose Leiste – kleine Schäden werden schnell zu großen Ärgernissen. Wir erledigen Kleinreparaturen zügig und melden Ihnen, was gemacht wurde.",
        "umfang": ["Leuchtmittel tauschen, Bewegungsmelder prüfen", "Türen, Türschließer und Schlösser einstellen",
                   "Kleine Montagen und Ausbesserungen", "Silikonfugen, Leisten, Griffe", "Meldung größerer Schäden mit Foto an die Verwaltung"],
        "fuer": "Hausverwaltungen, Vermieter und Gewerbekunden – auch als Ergänzung zur laufenden Objektbetreuung.",
        "faq": [("Wie schnell sind Sie vor Ort?", "Wir reagieren innerhalb von 24 Stunden und vereinbaren kurzfristig einen Termin."),
                ("Machen Sie auch Elektro- oder Sanitärarbeiten?", "Arbeiten, die einen Meisterbetrieb erfordern, übernehmen wir nicht – wir melden sie Ihnen und koordinieren auf Wunsch mit einem Fachbetrieb.")],
    },
    {
        "slug": "muelltonnen-service-guetersloh", "icon": "muell", "name": "Mülltonnen-Service",
        "kurz": "Bereitstellen, zurückstellen und Sauberhalten der Müllbereiche – ohne dass Sie daran denken müssen.",
        "preis": "5 €", "einheit": "pro Einheit / Monat",
        "titel": "Mülltonnen-Service in Gütersloh",
        "intro": "Volle Tonnen, die nicht rausgestellt wurden, und unordentliche Müllplätze sind ein Dauerthema in Mehrfamilienhäusern. Wir stellen die Tonnen zu den Abfuhrterminen bereit, holen sie zurück und halten den Müllplatz sauber.",
        "umfang": ["Bereitstellen der Tonnen zu den Abfuhrterminen", "Zurückstellen nach der Leerung", "Müllplatz sauber halten",
                   "Fehlbefüllungen melden", "Sperrmüll-Ablagerungen dokumentieren und melden"],
        "fuer": "Mehrfamilienhäuser, Wohnanlagen und Gewerbeobjekte in Gütersloh und Umgebung.",
        "faq": [("Kennen Sie die Abfuhrtermine?", "Ja, wir richten uns nach dem Abfuhrkalender Ihrer Stadt.")],
    },
    {
        "slug": None, "icon": "kontrolle", "name": "Gebäudekontrolle", "feature": True,
        "kurz": "Regelmäßige Begehungen und Protokollierung des Gebäudezustands. Bei jeder beauftragten Leistung inklusive.",
        "preis": "0 €", "einheit": "kostenlos inklusive",
    },
]

FAQ = [
    ("Was kostet ein Hausmeisterservice in Gütersloh?", "Das hängt von Größe und Leistungen ab. Treppenhausreinigung gibt es ab 8 € pro Einheit und Woche, den Mülltonnen-Service für 5 € pro Einheit und Monat. Mit unserem Preisrechner sehen Sie sofort einen Richtwert – das konkrete Angebot erhalten Sie nach einer kostenlosen Besichtigung."),
    ("Wie schnell bekomme ich ein Angebot?", "Sie erhalten innerhalb von 24 Stunden eine Rückmeldung. Nach der kostenlosen Objektbesichtigung erstellen wir Ihnen zügig ein schriftliches Angebot."),
    ("In welchen Orten sind Sie im Einsatz?", "In Gütersloh und Umgebung – unter anderem in " + ", ".join(ORTE[1:6]) + ". Fragen Sie gern auch für andere Orte im Kreis Gütersloh an."),
    ("Arbeiten Sie auch für Hausverwaltungen mit mehreren Objekten?", "Ja, genau darauf sind wir ausgerichtet: ein fester Ansprechpartner für alle Objekte, regelmäßige Kontrollen und Protokolle, die Sie direkt an Eigentümer weitergeben können."),
    ("Wie erreiche ich Sie am schnellsten?", f"Per Telefon oder WhatsApp unter {FIRMA['tel']} – {FIRMA['zeiten']}. Sie können uns auch über das Anfrageformular schreiben."),
    ("Gibt es eine Mindestlaufzeit?", "Die Laufzeit vereinbaren wir individuell im Angebot. Für einmalige Einsätze wie Gartenarbeit oder Reparaturen gibt es keine Laufzeit."),
]


# ---------------------------------------------------------------- Hilfen
def e(s):
    return html.escape(s, quote=True)


def wa(text="Hallo Hausmeister Helden, ich hätte gern ein Angebot."):
    from urllib.parse import quote
    return f"https://wa.me/{FIRMA['wa']}?text={quote(text)}"


def saison():
    m = HEUTE.month
    if m in (10, 11, 12, 1, 2):
        return ("❄️ Winterdienst-Saison läuft – jetzt noch Plätze für diesen Winter sichern.", "winterdienst-guetersloh.html")
    if m in (3, 4, 5):
        return ("🌱 Frühjahr: Jetzt Gartenpflege und Frühjahrsputz für Ihre Wohnanlage planen.", "gartenpflege-guetersloh.html")
    if m in (6, 7, 8):
        return ("🌿 Sommer: Rasen, Hecken und Außenanlagen – wir halten alles in Schuss.", "gartenpflege-guetersloh.html")
    return ("🍂 Herbst: Laubentfernung jetzt buchen – und den Winterdienst gleich mit.", "winterdienst-guetersloh.html")


def schema_business():
    return {
        "@context": "https://schema.org", "@type": "HomeAndConstructionBusiness",
        "@id": FIRMA["url"] + "/#firma", "name": FIRMA["name"], "url": FIRMA["url"] + "/",
        "image": FIRMA["url"] + "/img/logo.jpg", "logo": FIRMA["url"] + "/img/logo.jpg",
        "telephone": FIRMA["tel_link"], "email": FIRMA["mail"], "founder": FIRMA["inhaber"],
        "slogan": FIRMA["slogan"], "priceRange": "€€",
        "address": {"@type": "PostalAddress", "streetAddress": FIRMA["strasse"], "postalCode": FIRMA["plz"],
                    "addressLocality": FIRMA["ort"], "addressRegion": "NRW", "addressCountry": "DE"},
        "geo": {"@type": "GeoCoordinates", "latitude": FIRMA["geo"][0], "longitude": FIRMA["geo"][1]},
        "areaServed": [{"@type": "City", "name": o} for o in ORTE],
        "openingHoursSpecification": [{"@type": "OpeningHoursSpecification",
                                       "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                                       "opens": "07:00", "closes": "20:00"}],
        "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Leistungen", "itemListElement": [
            {"@type": "Offer", "itemOffered": {"@type": "Service", "name": l["name"]}} for l in LEISTUNGEN]},
    }


def schema_faq(items):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False) + "</script>"


NAV = [("index.html#leistungen", "Leistungen"), ("hausverwaltungen.html", "Für Verwaltungen"),
       ("index.html#preisrechner", "Preisrechner"), ("ratgeber.html", "Ratgeber"), ("index.html#kontakt", "Kontakt")]


def page(slug, title, desc, body, schema=(), nav_home=False):
    canonical = FIRMA["url"] + "/" + ("" if slug == "index.html" else slug)
    s_text, s_link = saison()
    nav = "".join(f'<a href="{(h.replace("index.html", "") if nav_home else h)}">{t}</a>' for h, t in NAV)
    schemas = "".join(ld(x) for x in schema)
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#0d100e">
<meta property="og:type" content="website">
<meta property="og:locale" content="de_DE">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{FIRMA['url']}/img/logo.jpg">
<link rel="icon" href="img/favicon.svg" type="image/svg+xml">
<link rel="preload" href="fonts/archivo.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="fonts/inter.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="style.css?v={HEUTE:%Y%m%d}">
{schemas}
</head>
<body>
<a class="skip" href="#main">Zum Inhalt springen</a>
<div class="season"><a href="{s_link}">{s_text}</a></div>
<div class="topbar"><div class="container">
  <span><span class="dot"></span>Gütersloh &amp; Umgebung<span class="hours"> · {FIRMA['zeiten']}</span></span>
  <span><a href="tel:{FIRMA['tel_link']}">{FIRMA['tel']}</a><span class="hide-sm"> · <a href="mailto:{FIRMA['mail']}">{FIRMA['mail']}</a></span></span>
</div></div>
<header class="header"><div class="container">
  <a class="brand" href="{'#top' if nav_home else 'index.html'}">{LOGO}</a>
  <button class="nav-toggle" aria-label="Menü öffnen" aria-expanded="false" aria-controls="nav"><span></span><span></span><span></span></button>
  <nav class="nav" id="nav" aria-label="Hauptmenü">{nav}<a class="btn btn-primary" href="{'#kontakt' if nav_home else 'index.html#kontakt'}">Kostenlos anfragen</a></nav>
</div></header>
<main id="main">
{body}
</main>
{cta_band()}
{footer()}
<div class="mobilebar">
  <a class="btn btn-ghost" style="color:#fff;border-color:#3a423c" href="tel:{FIRMA['tel_link']}">{icon('phone')} Anrufen</a>
  <a class="btn btn-wa" href="{wa()}" target="_blank" rel="noopener">{WA_SVG} WhatsApp</a>
</div>
<a class="wa-float" href="{wa()}" target="_blank" rel="noopener" aria-label="Per WhatsApp schreiben" style="color:#fff">{WA_SVG}</a>
<script src="app.js?v={HEUTE:%Y%m%d}" defer></script>
</body>
</html>
"""


def cta_band():
    return f"""<section class="cta-band"><div class="container">
  <div><h2>Bereit für Ihren Helden?</h2><p>Kostenlose Objektbesichtigung · Antwort innerhalb von 24 Stunden</p></div>
  <div class="btn-row"><a class="btn btn-dark" href="tel:{FIRMA['tel_link']}">{icon('phone')} {FIRMA['tel']}</a>
  <a class="btn btn-ghost" href="{wa()}" target="_blank" rel="noopener">{WA_SVG} WhatsApp</a></div>
</div></section>"""


def footer():
    leist = "".join(f'<li><a href="{l["slug"]}.html">{l["name"]}</a></li>' for l in LEISTUNGEN if l["slug"])
    orte = "".join(f"<li>{o}</li>" for o in ORTE[:7])
    return f"""<footer class="footer"><div class="container">
<div class="cols">
  <div><a class="brand" href="index.html" style="color:#fff">{LOGO}</a>
  <p style="margin-top:18px;max-width:34ch">Hausmeisterservice für Hausverwaltungen, Eigentümer und Gewerbe in Gütersloh &amp; Umgebung. {FIRMA['slogan']}</p></div>
  <div><h4>Leistungen</h4><ul>{leist}<li><a href="hausverwaltungen.html">Für Hausverwaltungen</a></li></ul></div>
  <div><h4>Einsatzgebiet</h4><ul>{orte}</ul></div>
  <div><h4>Kontakt</h4><ul>
    <li>{FIRMA['name']}<br>{FIRMA['strasse']}<br>{FIRMA['plz']} {FIRMA['ort']}</li>
    <li><a href="tel:{FIRMA['tel_link']}">{FIRMA['tel']}</a></li>
    <li><a href="mailto:{FIRMA['mail']}">{FIRMA['mail']}</a></li>
    <li>{FIRMA['zeiten']}</li></ul></div>
</div>
<div class="legal"><span>© {HEUTE.year} {FIRMA['name']} · Inhaber {FIRMA['inhaber']}</span>
<span><a href="impressum.html">Impressum</a> · <a href="datenschutz.html">Datenschutz</a> · <a href="ratgeber.html">Ratgeber</a></span></div>
</div></footer>"""


def leistung_cards(link_prefix=""):
    out = []
    for l in LEISTUNGEN:
        cls = "card feature reveal" if l.get("feature") else "card reveal"
        more = f'<a class="more" href="{link_prefix}{l["slug"]}.html" aria-label="Mehr zu {e(l["name"])}">Mehr erfahren →</a>' if l["slug"] else '<span class="pill">Immer inklusive</span>'
        out.append(f"""<article class="{cls}">
  <div class="icon">{icon(l['icon'])}</div>
  <h3>{l['name']}</h3>
  <p>{l['kurz']}</p>
  <div class="price"><span><b>{l['preis']}</b> <small>{l['einheit']}</small></span>{more}</div>
</article>""")
    return "\n".join(out)


def faq_html(items):
    return '<div class="faq">' + "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in items) + "</div>"


# ---------------------------------------------------------------- Startseite
def startseite(artikel):
    towns = "".join(f'<span class="{"main" if i == 0 else ""}">{o}</span>' for i, o in enumerate(ORTE))
    pins = [("Gütersloh", 50, 50, "center"), ("Harsewinkel", 28, 24, ""), ("Herzebrock-Clarholz", 24, 70, ""),
            ("Rheda-Wiedenbrück", 44, 80, ""), ("Rietberg", 62, 86, ""), ("Verl", 74, 62, ""),
            ("Schloß Holte-St.", 82, 40, ""), ("Steinhagen", 66, 18, ""), ("Halle (Westf.)", 40, 10, "")]
    pin_html = "".join(f'<span class="pin {c}" style="left:{x}%;top:{y}%">{n}</span>' for n, x, y, c in pins)
    neueste = "".join(f'<article class="card reveal"><time datetime="{a["datum"]}">{fmt_datum(a["datum"])}</time><h3>{e(a["titel"])}</h3><p>{e(a["beschreibung"])}</p><div class="price"><a class="more" href="{a["datei"]}">Weiterlesen →</a></div></article>' for a in artikel[:3])
    body = f"""
<section class="hero" id="top"><div class="container">
  <div>
    <span class="badge"><span class="dot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#7ccc13"></span> Jetzt in Gütersloh &amp; Umgebung verfügbar</span>
    <h1>Ihr Haus.<span class="hl">Unsere Pflicht.</span></h1>
    <p class="lead">Hausmeisterservice für Hausverwaltungen, Eigentümer und Gewerbe in Gütersloh: Treppenhausreinigung, Winterdienst, Gartenpflege und Kleinreparaturen – mit festem Ansprechpartner und Protokoll nach jedem Einsatz.</p>
    <div class="btn-row">
      <a class="btn btn-primary" href="#kontakt">Kostenlose Besichtigung {icon('arrow')}</a>
      <a class="btn btn-ghost" href="#preisrechner">Preis berechnen</a>
    </div>
    <div class="trust">
      <div><strong>24 h</strong><span>Reaktionszeit</span></div>
      <div><strong>0 €</strong><span>Erstbesichtigung</span></div>
      <div><strong>1</strong><span>fester Ansprechpartner</span></div>
      <div><strong>6 Tage</strong><span>erreichbar, 7–20 Uhr</span></div>
    </div>
  </div>
  <div class="hero-visual" aria-hidden="true">
    <div class="report">
      <div class="report-head"><div><b>Objektprotokoll</b><br><small>Musterstraße 12 · Gütersloh</small></div><span class="pill">Erledigt</span></div>
      <ul>
        <li><span class="chk">{icon('check')}</span><span>Treppenhaus gereinigt<small>EG bis 3. OG, Handläufe, Eingang</small></span></li>
        <li><span class="chk">{icon('check')}</span><span>Gehweg geräumt &amp; gestreut<small>Winterdienst · 06:45 Uhr</small></span></li>
        <li><span class="chk">{icon('check')}</span><span>Leuchtmittel im Keller getauscht<small>Kleinreparatur · Foto im Anhang</small></span></li>
        <li><span class="chk">{icon('check')}</span><span>Gebäudekontrolle ohne Befund<small>Inklusive bei jedem Einsatz</small></span></li>
      </ul>
    </div>
    <div class="chat">Super, danke! Wie immer zuverlässig 👍<small>Beispiel · 07:52</small></div>
  </div>
</div></section>

<section class="section" id="leistungen"><div class="container">
  <div class="section-head"><span class="eyebrow">Was wir tun</span><h2>Alles aus einer Hand</h2>
  <p class="lead">Ein Dienstleister statt fünf: Wir übernehmen die laufende Betreuung Ihrer Immobilie – planbar, dokumentiert und zu transparenten Preisen.</p></div>
  <div class="grid grid-3">{leistung_cards()}</div>
  <div class="note">{icon('euro')} Treuerabatt: Bei wöchentlicher Reinigung (4× im Monat) erhalten Sie 10 % Rabatt auf die monatliche Reinigungsrechnung.</div>
</div></section>

<section class="section dark" id="verwaltungen"><div class="container split">
  <div>
    <span class="eyebrow">Für Hausverwaltungen &amp; WEGs</span>
    <h2>Weniger Anrufe.<br><span class="hl">Mehr Ruhe.</span></h2>
    <p class="lead">Sie verwalten Objekte – wir kümmern uns darum, dass dort alles läuft. Mit klaren Abläufen, die Ihnen Arbeit abnehmen statt neue zu machen.</p>
    <ul class="checklist">
      <li><b>Ein fester Ansprechpartner</b>Inhaber {FIRMA['inhaber']} persönlich – kein Callcenter, keine Warteschleife.</li>
      <li><b>Protokoll nach jedem Einsatz</b>Mit Fotos, direkt weiterleitbar an Eigentümer und Beirat.</li>
      <li><b>Probleme früh erkennen</b>Gebäudekontrolle bei jeder Leistung inklusive.</li>
      <li><b>Erreichbar per WhatsApp</b>Kurze Wege, schnelle Antworten – {FIRMA['zeiten']}.</li>
    </ul>
    <a class="btn btn-primary" href="hausverwaltungen.html">Leistungen für Verwaltungen {icon('arrow')}</a>
  </div>
  <div class="stat-panel reveal">
    <h3>Der Unterschied</h3>
    <table class="compare"><thead><tr><th></th><th>Oft üblich</th><th>Hausmeister Helden</th></tr></thead><tbody>
      <tr><td>Rückmeldung</td><td>Tage</td><td>Innerhalb 24 h</td></tr>
      <tr><td>Ansprechpartner</td><td>Wechselnd</td><td>Immer derselbe</td></tr>
      <tr><td>Nachweis</td><td>Keiner</td><td>Protokoll + Fotos</td></tr>
      <tr><td>Kontrollgänge</td><td>Aufpreis</td><td>Inklusive</td></tr>
      <tr><td>Besichtigung</td><td>Kostenpflichtig</td><td>Kostenlos</td></tr>
    </tbody></table>
  </div>
</div></section>

<section class="section soft" id="ablauf"><div class="container">
  <div class="section-head center"><span class="eyebrow">So einfach geht's</span><h2>In 4 Schritten betreut</h2></div>
  <div class="steps">
    <div class="step reveal"><h3>Anfrage</h3><p>Per Telefon, WhatsApp oder Formular – wir melden uns innerhalb von 24 Stunden.</p></div>
    <div class="step reveal"><h3>Besichtigung</h3><p>Wir schauen uns Ihr Objekt kostenlos und unverbindlich vor Ort an.</p></div>
    <div class="step reveal"><h3>Angebot</h3><p>Sie erhalten ein klares Festpreis-Angebot – ohne versteckte Kosten.</p></div>
    <div class="step reveal"><h3>Start</h3><p>Wir legen los und berichten nach jedem Einsatz mit Protokoll.</p></div>
  </div>
</div></section>

<section class="section" id="preisrechner"><div class="container">
  <div class="section-head"><span class="eyebrow">Interaktiver Preisrechner</span><h2>Was kostet Ihr Hausmeisterservice?</h2>
  <p class="lead">Leistungen wählen, Anzahl der Wohneinheiten einstellen – und sofort einen Richtwert sehen.</p></div>
  <form class="calc" id="rechner" onsubmit="return false">
    <div class="calc-in">
      <fieldset><legend>Welche Leistungen benötigen Sie?</legend><div class="chips">
        <label class="chip"><input type="checkbox" name="l" value="reinigung" checked><span>Treppenhausreinigung</span></label>
        <label class="chip"><input type="checkbox" name="l" value="winter"><span>Winterdienst</span></label>
        <label class="chip"><input type="checkbox" name="l" value="garten"><span>Gartenarbeit</span></label>
        <label class="chip"><input type="checkbox" name="l" value="muell" checked><span>Mülltonnen-Service</span></label>
        <label class="chip"><input type="checkbox" name="l" value="reparatur"><span>Kleinreparaturen</span></label>
      </div></fieldset>
      <fieldset><legend><label for="einheiten">Anzahl Wohneinheiten</label></legend>
        <div class="range-row"><input type="range" id="einheiten" min="1" max="60" value="10"><output id="einheiten-out" for="einheiten">10</output></div>
      </fieldset>
      <p style="color:var(--muted);font-size:.9rem;margin:0">Die Gebäudekontrolle ist bei jeder Beauftragung kostenlos inklusive.</p>
    </div>
    <div class="calc-out" aria-live="polite">
      <span class="eyebrow" style="color:#7ccc13">Geschätzter Monatspreis ab</span>
      <div class="total" id="summe">– €</div>
      <ul class="breakdown" id="aufstellung"></ul>
      <a class="btn btn-primary" id="rechner-cta" href="{wa()}" target="_blank" rel="noopener">Konkretes Angebot anfragen {icon('arrow')}</a>
      <small>Alle Preise sind Richtwerte. Das tatsächliche Angebot hängt von Ihrem Objekt ab.</small>
    </div>
  </form>
</div></section>

<section class="section soft" id="gebiet"><div class="container split">
  <div>
    <span class="eyebrow">Einsatzgebiet</span><h2>Gütersloh &amp; Umgebung</h2>
    <p class="lead">Wir sind in Gütersloh zu Hause und betreuen Objekte im gesamten Umland. Kurze Wege bedeuten schnelle Einsätze – gerade im Winterdienst entscheidend.</p>
    <div class="towns">{towns}</div>
  </div>
  <div class="map reveal" role="img" aria-label="Einsatzgebiet rund um Gütersloh">{pin_html}</div>
</div></section>

<section class="section" id="ueber-uns"><div class="container split">
  <div>
    <span class="eyebrow">Über uns</span><h2>Nicht irgendein Hausmeister.</h2>
    <p class="lead">Hausmeister Helden steht für einen einfachen Anspruch: Was wir zusagen, halten wir. Wir sind schnell erreichbar, arbeiten sorgfältig und sagen Ihnen offen, was ein Objekt braucht – und was nicht.</p>
    <div class="owner"><div class="avatar">MO</div><div><b>{FIRMA['inhaber']}</b><br><span style="color:var(--muted)">Inhaber &amp; Ihr persönlicher Ansprechpartner</span></div></div>
  </div>
  <div class="values">
    <div class="reveal"><b>Blitzschnell</b><p>Per Telefon und WhatsApp erreichbar – Antwort in Stunden, nicht Tagen.</p></div>
    <div class="reveal"><b>Persönlich</b><p>Kein Callcenter. Sie sprechen immer direkt mit dem Inhaber.</p></div>
    <div class="reveal"><b>Proaktiv</b><p>Regelmäßige Kontrollen – wir erkennen Probleme, bevor sie teuer werden.</p></div>
    <div class="reveal"><b>Transparent</b><p>Klare Preise, schriftliches Angebot, keine versteckten Kosten.</p></div>
  </div>
</div></section>

<section class="section soft" id="faq"><div class="container">
  <div class="section-head center"><span class="eyebrow">Häufige Fragen</span><h2>Gut zu wissen</h2></div>
  {faq_html(FAQ)}
</div></section>

{'<section class="section article-list"><div class="container"><div class="section-head"><span class="eyebrow">Ratgeber</span><h2>Wissen für Vermieter &amp; Verwalter</h2></div><div class="grid grid-3">' + neueste + '</div></div></section>' if artikel else ''}

<section class="section dark" id="kontakt"><div class="container contact">
  <div>
    <span class="eyebrow">Kontakt &amp; Anfrage</span><h2>Kostenlose Besichtigung anfragen</h2>
    <p class="lead">Wir besichtigen Ihr Objekt unverbindlich und erstellen ein individuelles Angebot – komplett kostenlos.</p>
    <ul class="contact-list">
      <li><span class="icon">{icon('phone')}</span><div><small>Telefon</small><a href="tel:{FIRMA['tel_link']}">{FIRMA['tel']}</a></div></li>
      <li><span class="icon" style="color:#25d366">{WA_SVG}</span><div><small>WhatsApp</small><a href="{wa()}" target="_blank" rel="noopener">{FIRMA['tel']}</a></div></li>
      <li><span class="icon">{icon('mail')}</span><div><small>E-Mail</small><a href="mailto:{FIRMA['mail']}">{FIRMA['mail']}</a></div></li>
      <li><span class="icon">{icon('pin')}</span><div><small>Adresse</small><span class="v">{FIRMA['strasse']}, {FIRMA['plz']} {FIRMA['ort']}</span></div></li>
      <li><span class="icon">{icon('clock')}</span><div><small>Erreichbarkeit</small><span class="v">{FIRMA['zeiten']}</span></div></li>
    </ul>
  </div>
  <form class="form" id="anfrage">
    <h3>Ihre Anfrage</h3>
    <div class="row">
      <div class="field"><label for="f-name">Name *</label><input id="f-name" name="name" autocomplete="name" required></div>
      <div class="field"><label for="f-firma">Firma / Verwaltung</label><input id="f-firma" name="firma" autocomplete="organization"></div>
    </div>
    <div class="row">
      <div class="field"><label for="f-tel">Telefon *</label><input id="f-tel" name="telefon" type="tel" autocomplete="tel" required></div>
      <div class="field"><label for="f-ort">Objekt / Ort</label><input id="f-ort" name="ort" placeholder="z. B. Gütersloh, 12 Einheiten"></div>
    </div>
    <div class="field"><label for="f-leistung">Leistung</label><select id="f-leistung" name="leistung">
      <option>Komplette Objektbetreuung</option>{''.join(f'<option>{l["name"]}</option>' for l in LEISTUNGEN if l['slug'])}<option>Sonstiges</option></select></div>
    <div class="field"><label for="f-msg">Nachricht</label><textarea id="f-msg" name="nachricht" rows="4" placeholder="Was dürfen wir für Sie tun?"></textarea></div>
    <div class="btn-row">
      <button class="btn btn-wa" type="submit" value="wa">{WA_SVG} Per WhatsApp senden</button>
      <button class="btn btn-dark" type="submit" value="mail">{icon('mail')} Per E-Mail senden</button>
    </div>
    <small>Ihre Angaben werden nicht auf dieser Webseite gespeichert, sondern öffnen eine fertige Nachricht in WhatsApp oder Ihrem E-Mail-Programm. Mehr in der <a href="datenschutz.html">Datenschutzerklärung</a>.</small>
  </form>
</div></section>
"""
    return page("index.html", "Hausmeisterservice Gütersloh | Hausmeister Helden",
                "Hausmeister Helden – Hausmeisterservice in Gütersloh & Umgebung: Treppenhausreinigung, Winterdienst, Gartenpflege, Kleinreparaturen. Antwort in 24 h, Besichtigung kostenlos.",
                body, [schema_business(), schema_faq(FAQ)], nav_home=True)


# ---------------------------------------------------------------- Leistungsseiten
def leistungsseite(l):
    umfang = "".join(f"<li>{e(x)}</li>" for x in l["umfang"])
    andere = "".join(f'<li><a href="{x["slug"]}.html">{x["name"]} in Gütersloh</a></li>' for x in LEISTUNGEN if x["slug"] and x is not l)
    body = f"""
<section class="page-hero"><div class="container">
  <div class="crumbs"><a href="index.html">Start</a> / <a href="index.html#leistungen">Leistungen</a> / {l['name']}</div>
  <h1>{e(l['titel'])}</h1>
  <p class="lead">{e(l['kurz'])}</p>
  <div class="btn-row"><a class="btn btn-primary" href="index.html#kontakt">Kostenlos anfragen {icon('arrow')}</a>
  <a class="btn btn-ghost" style="color:#fff;border-color:#3a423c" href="{wa('Hallo Hausmeister Helden, ich interessiere mich für ' + l['name'] + '.')}" target="_blank" rel="noopener">{WA_SVG} WhatsApp</a></div>
</div></section>
<section class="section"><div class="container with-aside">
  <div class="prose">
    <p class="lead">{e(l['intro'])}</p>
    <h2>Unsere Leistungen</h2>
    <ul class="checklist">{umfang}</ul>
    <h2>Für wen?</h2>
    <p>{e(l['fuer'])}</p>
    <h2>Preis</h2>
    <p><strong>{l['preis']} {l['einheit']}</strong> – als Richtwert. Das genaue Angebot erstellen wir nach einer kostenlosen Besichtigung. Die Gebäudekontrolle mit Protokoll ist immer inklusive.</p>
    <h2>Häufige Fragen</h2>
    {faq_html(l['faq'])}
    <h2>Weitere Leistungen</h2>
    <ul>{andere}</ul>
  </div>
  <aside class="aside-card">
    <div class="icon" style="background:rgba(124,204,19,.14);color:#7ccc13">{icon(l['icon'])}</div>
    <h3>{l['name']}</h3>
    <p><b style="color:#fff;font-size:1.4rem">{l['preis']}</b> {l['einheit']}</p>
    <ul class="checklist" style="margin:16px 0 24px">
      <li>Antwort innerhalb 24 h</li><li>Besichtigung kostenlos</li><li>Protokoll inklusive</li></ul>
    <a class="btn btn-primary" style="width:100%" href="tel:{FIRMA['tel_link']}">{icon('phone')} {FIRMA['tel']}</a>
  </aside>
</div></section>"""
    schema = [schema_business(), schema_faq(l["faq"]),
              {"@context": "https://schema.org", "@type": "Service", "name": l["titel"], "serviceType": l["name"],
               "provider": {"@id": FIRMA["url"] + "/#firma"}, "areaServed": ORTE, "description": l["intro"]}]
    return page(l["slug"] + ".html", f"{l['titel']} | Hausmeister Helden",
                f"{l['titel']}: {l['kurz']} {l['preis']} {l['einheit']}. Jetzt kostenlos anfragen.", body, schema)


def verwaltungsseite():
    body = f"""
<section class="page-hero"><div class="container">
  <div class="crumbs"><a href="index.html">Start</a> / Für Hausverwaltungen</div>
  <h1>Hausmeisterservice für Hausverwaltungen in Gütersloh</h1>
  <p class="lead">Sie verwalten. Wir halten Ihre Objekte in Schuss – zuverlässig, dokumentiert und mit einem Ansprechpartner für alle Liegenschaften.</p>
  <div class="btn-row"><a class="btn btn-primary" href="index.html#kontakt">Objektbesichtigung vereinbaren {icon('arrow')}</a></div>
</div></section>
<section class="section"><div class="container">
  <div class="section-head"><span class="eyebrow">Ihr Vorteil</span><h2>Was Verwaltungen an uns schätzen</h2></div>
  <div class="grid grid-3">
    <article class="card reveal"><div class="icon">{icon('user')}</div><h3>Ein Ansprechpartner</h3><p>Inhaber {FIRMA['inhaber']} ist direkt für Sie da – für alle Objekte, ohne Weiterleitung.</p></article>
    <article class="card reveal"><div class="icon">{icon('kontrolle')}</div><h3>Protokolle mit Fotos</h3><p>Nach jedem Einsatz – ideal für Eigentümer, Beirat und Ihre Dokumentation.</p></article>
    <article class="card reveal"><div class="icon">{icon('bolt')}</div><h3>Schnelle Reaktion</h3><p>Rückmeldung innerhalb von 24 Stunden, erreichbar {FIRMA['zeiten']}.</p></article>
    <article class="card reveal"><div class="icon">{icon('shield')}</div><h3>Winterdienst mit Nachweis</h3><p>Jeder Einsatz dokumentiert – für Ihre Verkehrssicherungspflicht.</p></article>
    <article class="card reveal"><div class="icon">{icon('euro')}</div><h3>Planbare Kosten</h3><p>Transparente Preise pro Einheit und klare Angebote – ohne versteckte Kosten.</p></article>
    <article class="card reveal"><div class="icon">{icon('reinigung')}</div><h3>Alles aus einer Hand</h3><p>Reinigung, Winterdienst, Garten, Tonnen und Reparaturen – ein Vertrag statt fünf.</p></article>
  </div>
</div></section>
<section class="section soft"><div class="container">
  <div class="section-head"><span class="eyebrow">Leistungen</span><h2>Unser Leistungsangebot</h2></div>
  <div class="grid grid-3">{leistung_cards()}</div>
</div></section>
<section class="section"><div class="container">
  <div class="section-head center"><span class="eyebrow">Häufige Fragen</span><h2>Fragen von Verwaltungen</h2></div>
  {faq_html(FAQ[:4])}
</div></section>"""
    return page("hausverwaltungen.html", "Hausmeisterservice für Hausverwaltungen in Gütersloh | Hausmeister Helden",
                "Hausmeisterservice für Hausverwaltungen und WEGs in Gütersloh: ein Ansprechpartner, Protokolle mit Fotos, Winterdienst mit Nachweis, Antwort in 24 h.",
                body, [schema_business(), schema_faq(FAQ[:4])])


# ---------------------------------------------------------------- Ratgeber
def md(text):
    """Sehr kleiner Markdown-Konverter: #/##/###, Absätze, - Listen, **fett**, [Link](url)."""
    def inline(s):
        s = e(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)
        return s
    out, liste, para = [], False, []

    def flush():
        nonlocal para
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("- "):
            flush()
            if not liste:
                out.append("<ul>"); liste = True
            out.append("<li>" + inline(s[2:]) + "</li>"); continue
        if liste:
            out.append("</ul>"); liste = False
        if not s:
            flush(); continue
        m = re.match(r"(#{2,3}) (.+)", s)
        if m:
            flush(); lvl = len(m.group(1)); out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>"); continue
        para.append(s)
    flush()
    if liste:
        out.append("</ul>")
    return "\n".join(out)


def fmt_datum(d):
    y, m, t = d.split("-")
    return f"{int(t)}.{int(m)}.{y}"


def lade_artikel():
    arts = []
    for f in sorted((ROOT / "inhalte" / "ratgeber").glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        meta, _, inhalt = raw.partition("\n---\n")
        kv = dict(line.split(":", 1) for line in meta.strip("-\n").splitlines() if ":" in line)
        kv = {k.strip(): v.strip() for k, v in kv.items()}
        arts.append({"titel": kv["titel"], "beschreibung": kv["beschreibung"], "datum": kv["datum"],
                     "datei": "ratgeber-" + f.stem + ".html", "html": md(inhalt)})
    return sorted(arts, key=lambda a: a["datum"], reverse=True)


def artikelseite(a):
    body = f"""
<section class="page-hero"><div class="container">
  <div class="crumbs"><a href="index.html">Start</a> / <a href="ratgeber.html">Ratgeber</a></div>
  <h1>{e(a['titel'])}</h1><p class="lead">{e(a['beschreibung'])}</p>
  <p style="color:#98a29a;font-size:.9rem">{fmt_datum(a['datum'])} · von {FIRMA['inhaber']}, {FIRMA['name']}</p>
</div></section>
<section class="section"><div class="container with-aside">
  <article class="prose">{a['html']}
  <p style="margin-top:2em;font-size:.9rem;color:var(--muted)">Hinweis: Dieser Beitrag ersetzt keine Rechtsberatung.</p></article>
  <aside class="aside-card"><h3>Lieber abgeben?</h3><p>Wir übernehmen das für Sie – in Gütersloh &amp; Umgebung.</p>
  <a class="btn btn-primary" style="width:100%" href="index.html#kontakt">Kostenlos anfragen</a></aside>
</div></section>"""
    schema = [{"@context": "https://schema.org", "@type": "Article", "headline": a["titel"], "description": a["beschreibung"],
               "datePublished": a["datum"], "author": {"@type": "Person", "name": FIRMA["inhaber"]},
               "publisher": {"@id": FIRMA["url"] + "/#firma"}}]
    return page(a["datei"], f"{a['titel']} | Hausmeister Helden", a["beschreibung"], body, schema)


def ratgeberliste(arts):
    cards = "".join(f'<article class="card reveal"><time datetime="{a["datum"]}">{fmt_datum(a["datum"])}</time><h3>{e(a["titel"])}</h3><p>{e(a["beschreibung"])}</p><div class="price"><a class="more" href="{a["datei"]}">Weiterlesen →</a></div></article>' for a in arts)
    body = f"""
<section class="page-hero"><div class="container"><div class="crumbs"><a href="index.html">Start</a> / Ratgeber</div>
<h1>Ratgeber für Vermieter &amp; Verwalter</h1><p class="lead">Praxiswissen rund um Hausmeisterservice, Winterdienst, Reinigung und Pflege von Immobilien in Gütersloh.</p></div></section>
<section class="section article-list"><div class="container"><div class="grid grid-3">{cards or '<p>Bald gibt es hier die ersten Beiträge.</p>'}</div></div></section>"""
    return page("ratgeber.html", "Ratgeber für Vermieter & Hausverwaltungen | Hausmeister Helden",
                "Tipps zu Winterdienst, Treppenhausreinigung, Gartenpflege und Objektbetreuung – vom Hausmeisterservice aus Gütersloh.", body)


# ---------------------------------------------------------------- Rechtliches
def impressum():
    body = f"""<section class="page-hero"><div class="container"><h1>Impressum</h1></div></section>
<section class="section"><div class="container prose">
<h2>Angaben gemäß § 5 DDG</h2>
<p>{FIRMA['name']}<br>Inhaber: {FIRMA['inhaber']}<br>{FIRMA['strasse']}<br>{FIRMA['plz']} {FIRMA['ort']}</p>
<h2>Kontakt</h2><p>Telefon: {FIRMA['tel']}<br>E-Mail: <a href="mailto:{FIRMA['mail']}">{FIRMA['mail']}</a></p>
<!-- OFFEN: Umsatzsteuer-ID (falls vorhanden) und Rechtsform ergänzen -->
<h2>Verantwortlich für den Inhalt</h2><p>{FIRMA['inhaber']}, Anschrift wie oben.</p>
<h2>Verbraucherstreitbeilegung</h2><p>Wir sind nicht bereit und nicht verpflichtet, an Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle teilzunehmen.</p>
<h2>Haftung für Inhalte und Links</h2><p>Die Inhalte dieser Seite wurden mit größter Sorgfalt erstellt. Für die Richtigkeit, Vollständigkeit und Aktualität übernehmen wir keine Gewähr. Für Inhalte verlinkter externer Seiten sind ausschließlich deren Betreiber verantwortlich.</p>
</div></section>"""
    return page("impressum.html", "Impressum | Hausmeister Helden", "Impressum von Hausmeister Helden, Gütersloh.", body)


def datenschutz():
    body = f"""<section class="page-hero"><div class="container"><h1>Datenschutzerklärung</h1></div></section>
<section class="section"><div class="container prose">
<h2>1. Verantwortlicher</h2>
<p>{FIRMA['name']}, Inhaber {FIRMA['inhaber']}, {FIRMA['strasse']}, {FIRMA['plz']} {FIRMA['ort']}, Telefon {FIRMA['tel']}, E-Mail <a href="mailto:{FIRMA['mail']}">{FIRMA['mail']}</a>.</p>
<h2>2. Das Wichtigste vorab</h2>
<p>Diese Webseite setzt <strong>keine Cookies</strong>, verwendet <strong>keine Analyse- oder Werbetools</strong> und lädt <strong>keine Inhalte von Drittanbietern</strong> (Schriften und Bilder liegen auf unserem eigenen Server).</p>
<h2>3. Hosting und Server-Logfiles</h2>
<p>Die Webseite wird bei der IONOS SE, Elgendorfer Str. 57, 56410 Montabaur, gehostet. Beim Aufruf werden technisch notwendige Daten (z. B. IP-Adresse, Datum und Uhrzeit, aufgerufene Seite, Browser) in Server-Logfiles verarbeitet, um die Seite sicher und stabil bereitzustellen (Art. 6 Abs. 1 lit. f DSGVO). Mit IONOS besteht ein Vertrag zur Auftragsverarbeitung.</p>
<h2>4. Kontaktaufnahme</h2>
<p>Wenn Sie uns per Telefon, E-Mail oder WhatsApp kontaktieren, verarbeiten wir Ihre Angaben zur Bearbeitung Ihrer Anfrage und für mögliche Anschlussfragen (Art. 6 Abs. 1 lit. b und f DSGVO). Das Anfrageformular speichert keine Daten auf dieser Webseite, sondern öffnet eine vorausgefüllte Nachricht in WhatsApp oder Ihrem E-Mail-Programm.</p>
<p><strong>WhatsApp:</strong> Wenn Sie uns über WhatsApp schreiben, werden Daten von WhatsApp Ireland Ltd. (Meta) verarbeitet; dabei ist eine Übermittlung in die USA möglich. Wenn Sie das nicht möchten, nutzen Sie bitte Telefon oder E-Mail.</p>
<h2>5. Speicherdauer</h2>
<p>Wir löschen Ihre Daten, sobald sie für den Zweck nicht mehr erforderlich sind und keine gesetzlichen Aufbewahrungspflichten (z. B. für Angebote und Rechnungen) entgegenstehen.</p>
<h2>6. Ihre Rechte</h2>
<p>Sie haben das Recht auf Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung, Datenübertragbarkeit und Widerspruch (Art. 15–21 DSGVO) sowie das Recht auf Beschwerde bei einer Aufsichtsbehörde, z. B. der Landesbeauftragten für Datenschutz und Informationsfreiheit Nordrhein-Westfalen.</p>
<p>Stand: {HEUTE:%m/%Y}</p>
</div></section>"""
    return page("datenschutz.html", "Datenschutz | Hausmeister Helden", "Datenschutzerklärung von Hausmeister Helden, Gütersloh.", body)


def seite_404():
    body = f"""<section class="page-hero"><div class="container"><h1>Seite nicht gefunden</h1>
<p class="lead">Diese Seite gibt es nicht (mehr). Aber wir sind trotzdem für Sie da.</p>
<a class="btn btn-primary" href="index.html">Zur Startseite</a></div></section>"""
    return page("404.html", "Seite nicht gefunden | Hausmeister Helden", "Seite nicht gefunden.", body)


# ---------------------------------------------------------------- Build
def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for sub in ("fonts", "img"):
        shutil.copytree(ROOT / "static" / sub, OUT / sub)
    for f in ("style.css", "app.js"):
        shutil.copy(ROOT / "static" / f, OUT / f)
    (OUT / "img" / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#0d100e"/>'
        '<path d="M9 38L32 16l9 8v-7h7v13l7 8" fill="none" stroke="#7ccc13" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>'
        '<g fill="#7ccc13"><rect x="25" y="33" width="6" height="6" rx="1"/><rect x="33" y="33" width="6" height="6" rx="1"/>'
        '<rect x="25" y="41" width="6" height="6" rx="1"/><rect x="33" y="41" width="6" height="6" rx="1"/></g></svg>', encoding="utf-8")

    arts = lade_artikel()
    seiten = {"index.html": startseite(arts), "hausverwaltungen.html": verwaltungsseite(),
              "ratgeber.html": ratgeberliste(arts), "impressum.html": impressum(),
              "datenschutz.html": datenschutz(), "404.html": seite_404()}
    for l in LEISTUNGEN:
        if l["slug"]:
            seiten[l["slug"] + ".html"] = leistungsseite(l)
    for a in arts:
        seiten[a["datei"]] = artikelseite(a)
    for name, inhalt in seiten.items():
        (OUT / name).write_text(inhalt, encoding="utf-8")

    urls = "".join(f"<url><loc>{FIRMA['url']}/{'' if n == 'index.html' else n}</loc><lastmod>{HEUTE}</lastmod></url>"
                   for n in seiten if n != "404.html")
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {FIRMA['url']}/sitemap.xml\n", encoding="utf-8")
    (OUT / ".htaccess").write_text("ErrorDocument 404 /404.html\n<IfModule mod_expires.c>\nExpiresActive On\nExpiresByType text/css \"access plus 1 month\"\nExpiresByType application/javascript \"access plus 1 month\"\nExpiresByType font/woff2 \"access plus 1 year\"\nExpiresByType image/jpeg \"access plus 1 month\"\n</IfModule>\n", encoding="utf-8")
    print(f"{len(seiten)} Seiten gebaut -> {OUT}")


if __name__ == "__main__":
    main()
