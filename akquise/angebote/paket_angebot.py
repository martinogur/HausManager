#!/usr/bin/env python3
"""Paket-Angebote je Objekt (3 Pakete zur Auswahl) als Markdown + druckfertiges PDF.

Für Anfragen, bei denen die Objektdaten noch fehlen: Richtpreise auf Basis einer dokumentierten Annahme
(Standard: Mehrfamilienhaus, 1 Treppenhaus, 3 Etagen …), Festpreis nach kostenloser Besichtigung.
Preise kommen aus derselben Kalkulation wie das Portal (portal/app/vertrieb/kalkulation.py, Preisliste 24.11.2026).

Aufruf:  python3 akquise/angebote/paket_angebot.py anfragen/<ordner>/kunde.json
Ergebnis im selben Ordner: <Nr>.md, <Nr>.pdf je Objekt, alle-angebote.pdf, FREIGABE.md
Nichts wird verschickt – der Inhaber gibt frei (CLAUDE.md, Regel 1).
"""

import datetime as dt
import html
import json
import sys
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "portal" / "app"))
sys.path.insert(0, str(REPO / "akquise"))

import brief_pdf  # noqa: E402
from vertrieb import kalkulation as k  # noqa: E402

STANDARD_ANNAHME = {  # „MFH 6 WE“ aus akquise/angebote/preiskalkulation.md, Abschnitt 4
    "beschreibung": "Mehrfamilienhaus mit 1 Treppenhaus und 3 Etagen, ca. 25 m Gehweg/Zuwege, 150 m² Rasen, "
                    "20 m² Beete, 15 m Hecke, 6 Abfuhrtermine und 9 Tonnen-Leerungen im Monat",
    "treppenhaeuser": 1, "etagen": 3, "aufzug": False, "winterdienst_lfm": 25, "rasen_qm": 150, "beet_qm": 20,
    "hecke_lfm": 15, "muell_termine_monat": 6, "muell_leerungen_monat": 9,
}
PAKETE = [
    ("Paket 1 – Sauber", "Treppenhausreinigung wöchentlich, Mülltonnen-Service inkl. Müllplatz, Sichtkontrolle bei jedem Einsatz",
     dict(reinigung="woechentlich", muell=True)),
    ("Paket 2 – Gepflegt", "wie Paket 1 + Gartenpflege (Rasen, Beete, Hecke, Laub) + monatliche Objektkontrolle mit Fotoprotokoll",
     dict(reinigung="woechentlich", muell=True, garten=True, kontrolle=1)),
    ("Paket 3 – Rundum sorglos", "wie Paket 2 + Winterdienst November–März mit Einsatzprotokoll (Saisonpreis auf 12 Monate verteilt)",
     dict(reinigung="woechentlich", muell=True, garten=True, kontrolle=1, winter=True)),
]


def eur(cent) -> str:
    return f"{Decimal(cent) / 100:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def objektdaten(a: dict, p: dict) -> k.Objektdaten:
    return k.Objektdaten(
        treppenhaeuser=a["treppenhaeuser"], etagen=a["etagen"], aufzug=a["aufzug"], reinigung=p.get("reinigung"),
        winterdienst_lfm=Decimal(str(a["winterdienst_lfm"])) if p.get("winter") else None,
        rasen_qm=Decimal(str(a["rasen_qm"])) if p.get("garten") else Decimal(0),
        beet_qm=Decimal(str(a["beet_qm"])) if p.get("garten") else Decimal(0),
        hecke_lfm=Decimal(str(a["hecke_lfm"])) if p.get("garten") else Decimal(0),
        muell_termine_monat=a["muell_termine_monat"] if p.get("muell") else 0,
        muell_leerungen_monat=a["muell_leerungen_monat"] if p.get("muell") else 0,
        muellplatz=bool(p.get("muell")), kontrollen_monat=p.get("kontrolle", 0),
    )


def rechne(annahme: dict) -> list[dict]:
    zeilen = []
    for name, inhalt, p in PAKETE:
        r = k.kalkuliere(objektdaten(annahme, p), "inhaber")
        zeilen.append({"name": name, "inhalt": inhalt, "netto": r.monat_netto_cent, "brutto": r.monat_brutto_cent,
                       "marge": r.marge_prozent, "minuten": r.minuten_monat, "warnungen": r.warnungen,
                       "positionen": [(p.bezeichnung, p.monat_netto_cent) for p in r.positionen]})
    return zeilen


def winter_saison(annahme: dict) -> int:
    return k.PREISE["wd_grund"] + int(Decimal(str(annahme["winterdienst_lfm"])) * k.PREISE["wd_lfm"])


def markdown(kunde: dict, objekt: dict, nr: str, pakete: list[dict], annahme: dict, datum: str, gueltig: str) -> str:
    du = kunde.get("anrede_du", False)
    z = [f"# Angebot {nr}: Hausmeisterservice {objekt['adresse']}", "",
         f"Empfänger: {kunde['name']} ({kunde.get('kontakt', '')}) · Datum: {datum} · gültig bis {gueltig}", "",
         f"{kunde['gruss']}", "",
         ("vielen Dank für deine Anfrage. Gern betreuen wir dein Objekt – mit festem Ansprechpartner und Antwort innerhalb von 24 Stunden."
          if du else "vielen Dank für Ihre Anfrage. Gern betreuen wir Ihr Objekt – mit festem Ansprechpartner und Antwort innerhalb von 24 Stunden."),
         "",
         ("Da wir das Objekt noch nicht gesehen haben, bekommst du drei Pakete mit Richtpreisen zur Auswahl. "
          "Nach einer kostenlosen Besichtigung machen wir daraus einen verbindlichen Festpreis."
          if du else "Da wir das Objekt noch nicht gesehen haben, erhalten Sie drei Pakete mit Richtpreisen zur Auswahl. "
          "Nach einer kostenlosen Besichtigung machen wir daraus einen verbindlichen Festpreis."), "",
         "| Paket | Leistungen | Monat netto | Monat brutto |", "|---|---|---|---|"]
    for p in pakete:
        z.append(f"| **{p['name']}** | {p['inhalt']} | **{eur(p['netto'])}** | {eur(p['brutto'])} |")
    z += ["", f"Richtpreis-Annahme: {annahme['beschreibung']}.",
          f"Winterdienst-Saisonpreis (in Paket 3 enthalten): {eur(winter_saison(annahme))} netto für Nov.–März.", "",
          "Einzelpreise (netto): Treppenhaus 12,00 € je Treppenhaus + 8,00 € je Etage und Reinigung (Aufzug 4,45 €) · "
          "Mülltonnen 6,50 € je Abfuhrtermin + 1,34 € je Leerung, Müllplatz 4,45 € je Woche · Gartenpflege nach Fläche "
          "(Rasen 0,14 €/m² je Mahd, Beete 0,45 €/m², Hecke 1,78 €/m je Schnitt) · Objektkontrolle mit Fotoprotokoll 27,00 € · "
          "Winterdienst 220,00 € + 9,50 € je lfd. Meter und Saison · Kleinreparaturen 53,50 €/Std. (15-Minuten-Takt, mind. 30 Min.).", "",
          "Bedingungen: Laufzeit 12 Monate, danach Verlängerung um jeweils 12 Monate, Kündigung 3 Monate zum Laufzeitende. "
          "Monatliche Rechnung, zahlbar innerhalb von 14 Tagen. Alle Preise zzgl. 19 % USt. (Preisliste vom 24.11.2026).", "",
          "Mit freundlichen Grüßen", "Martin Ogur", "Hausmeister Helden"]
    return "\n".join(z) + "\n"


CSS_EXTRA = """
.tab{width:100%;border-collapse:collapse;font-size:9.4pt;margin:2mm 0 4mm}
.tab th{text-align:left;font-size:7.8pt;text-transform:uppercase;letter-spacing:.04em;color:#4a524c;border-bottom:.6pt solid #141814;padding:1.6mm 1.5mm}
.tab td{border-bottom:.3pt solid #c9d0ca;padding:2mm 1.5mm;vertical-align:top}
.tab td.z{text-align:right;white-space:nowrap}
.tab tr.hl td{background:#f2f9e7}
.klein{font-size:8.6pt;color:#3a413b}
.kasten{border:.4mm solid #7ccc13;border-radius:2mm;padding:3mm 4mm;margin:3mm 0}
.ankreuz span{display:inline-block;margin-right:7mm}
.inhalt2{position:absolute;top:45mm;left:25mm;right:20mm;bottom:30mm}
.inhalt2 p{margin:0 0 3mm}
"""


def seiten_html(kunde, objekt, nr, pakete, annahme, gueltig) -> list[str]:
    du = kunde.get("anrede_du", False)
    e = html.escape
    zeilen = "".join(
        f'<tr{" class=hl" if i == 1 else ""}><td><strong>{e(p["name"])}</strong><br><span class="klein">{e(p["inhalt"])}</span></td>'
        f'<td class="z"><strong>{eur(p["netto"])}</strong></td><td class="z">{eur(p["brutto"])}</td></tr>' for i, p in enumerate(pakete))
    s1 = f"""
<p class="betreff">Angebot {e(nr)}: Hausmeisterservice {e(objekt['adresse'])}</p>
<p>{e(kunde['gruss'])}</p>
<p>{'vielen Dank für deine Anfrage. Gern betreuen wir dein Objekt – mit mir als festem Ansprechpartner und Antwort innerhalb von 24 Stunden.' if du else 'vielen Dank für Ihre Anfrage. Gern betreuen wir Ihr Objekt – mit festem Ansprechpartner und Antwort innerhalb von 24 Stunden.'}</p>
<p>{'Da wir das Objekt noch nicht gemeinsam angesehen haben, bekommst du drei Pakete mit <strong>Richtpreisen</strong> zur Auswahl. Nach einer <strong>kostenlosen Besichtigung</strong> machen wir daraus einen verbindlichen Festpreis – nach Aufwand gerechnet, nicht pro Wohneinheit.' if du else 'Da wir das Objekt noch nicht angesehen haben, erhalten Sie drei Pakete mit <strong>Richtpreisen</strong> zur Auswahl. Nach einer <strong>kostenlosen Besichtigung</strong> machen wir daraus einen verbindlichen Festpreis.'}</p>
<table class="tab"><thead><tr><th>Paket</th><th style="text-align:right">Monat netto</th><th style="text-align:right">Brutto</th></tr></thead><tbody>{zeilen}</tbody></table>
<p class="klein">Richtpreise für ein {e(annahme['beschreibung'])}. Winterdienst-Saisonpreis (Paket 3): {eur(winter_saison(annahme))} netto für November bis März. Sichtkontrolle (Licht, Türen, Müllplatz) bei jedem Einsatz inklusive.</p>
<p>{'Sag mir einfach, welches Paket dich interessiert – oder ob du einzelne Leistungen kombinieren möchtest. Den Besichtigungstermin stimmen wir kurz telefonisch ab.' if du else 'Teilen Sie uns gern mit, welches Paket Sie interessiert. Den Besichtigungstermin stimmen wir kurz telefonisch ab.'}</p>
<p class="gruss">Viele Grüße<br>Martin Ogur</p>
"""
    kreuze = "".join(f"<span>☐ {e(p['name'])}</span>" for p in pakete)
    s2 = f"""
<p class="betreff">Einzelpreise und Bedingungen zu Angebot {e(nr)}</p>
<table class="tab"><thead><tr><th>Leistung</th><th>Preis netto</th></tr></thead><tbody>
<tr><td>Treppenhausreinigung (Treppen, Podeste, Flure feucht, Handläufe, Schalter, Haustür)</td><td>12,00 € je Treppenhaus + 8,00 € je Etage und Reinigung; Aufzug 4,45 €; 14-täglich +15 % je Reinigung</td></tr>
<tr><td>Mülltonnen-Service (raus- und reinstellen nach Abfuhrkalender)</td><td>6,50 € je Abfuhrtermin + 1,34 € je Leerung; Müllplatz kehren 4,45 € je Woche</td></tr>
<tr><td>Gartenpflege (Rasen mähen inkl. Kanten, Beete, Heckenschnitt, Laub, Grünschnitt-Entsorgung)</td><td>13,50 € je Gartengang; Rasen 0,14 €/m² je Mahd; Beete 0,45 €/m²; Hecke 1,78 €/m je Schnitt; Laub 0,05 €/m²; Entsorgung 0,11 €/m² und Jahr</td></tr>
<tr><td>Objektkontrolle mit Fotoprotokoll (eigener Termin)</td><td>27,00 € je Begehung</td></tr>
<tr><td>Winterdienst November–März (Räumen, Streuen inkl. Streugut, Einsatzprotokoll)</td><td>220,00 € Grundpauschale + 9,50 € je lfd. Meter und Saison</td></tr>
<tr><td>Kleinreparaturen und Sonderarbeiten (getrennt abgerechnet)</td><td>53,50 € je Stunde, je angefangene 15 Min. 13,50 €, mind. 30 Min.; Material nach Beleg</td></tr>
</tbody></table>
<p class="klein"><strong>Bedingungen:</strong> Richtpreis – verbindlicher Festpreis nach kostenloser Besichtigung. Angebot gültig bis {e(gueltig)}. Laufzeit 12 Monate, danach Verlängerung um jeweils 12 Monate, Kündigung mit 3 Monaten Frist zum Laufzeitende in Textform. Abrechnung monatlich, zahlbar innerhalb von 14 Tagen ohne Abzug. Auf Wunsch getrennte Rechnungen je Objekt und Kostenart (für die Betriebskostenabrechnung). Kleinreparaturen ab 250 € netto nur nach vorheriger Freigabe. Ausgefallene Einsätze holen wir innerhalb von 2 Werktagen nach oder schreiben sie gut. Alle Preise zzgl. 19 % USt. (Preisliste vom 24.11.2026).</p>
<div class="kasten"><p><strong>Besichtigung / Beauftragung</strong></p>
<p class="ankreuz">{kreuze}</p>
<p class="klein">☐ Bitte zuerst kostenlose Besichtigung vereinbaren &nbsp;&nbsp; Wunschtermin: ____________________</p>
<p class="klein" style="margin-top:8mm">Ort, Datum: ______________________ &nbsp; Unterschrift: ______________________________</p></div>
"""
    fuss = "".join(f"<div><b>{a}</b>{b}</div>" for a, b in brief_pdf.FUSS)
    kopf = (f'<div class="kopf">{brief_pdf.LOGO}<div class="kontakt"><b>Martin Ogur</b> · Inhaber<br>Telefon / WhatsApp 05241 3389748<br>'
            f'info@haus-meister-helden.de</div></div><div class="linie"></div>')
    empf = "<br>".join(e(z) for z in kunde["anschrift"])
    seite1 = (f'<section class="seite">{kopf}<div class="anschrift"><div class="ruecksende">{brief_pdf.ABSENDER_ZEILE}</div>'
              f'<div class="empf">{empf}</div></div><div class="datum">Gütersloh, {brief_pdf.heute()}</div>'
              f'<div class="inhalt">{s1}</div><div class="fuss">{fuss}</div></section>')
    seite2 = f'<section class="seite">{kopf}<div class="inhalt2">{s2}</div><div class="fuss">{fuss}</div></section>'
    return [seite1, seite2]


def main(pfad: str) -> None:
    datei = Path(pfad).resolve()
    kunde = json.loads(datei.read_text(encoding="utf-8"))
    ordner = datei.parent
    heute = dt.date.today()
    gueltig = (heute + dt.timedelta(days=30)).strftime("%d.%m.%Y")
    alle_seiten, jobs, freigabe = [], [], []
    for i, objekt in enumerate(kunde["objekte"], start=1):
        annahme = {**STANDARD_ANNAHME, **objekt.get("daten", {})}
        nr = f"AG-{heute:%Y%m%d}-{kunde['kuerzel']}{i}"
        pakete = rechne(annahme)
        (ordner / f"{nr}.md").write_text(markdown(kunde, objekt, nr, pakete, annahme, heute.strftime("%d.%m.%Y"), gueltig),
                                         encoding="utf-8")
        seiten = seiten_html(kunde, objekt, nr, pakete, annahme, gueltig)
        alle_seiten += seiten
        h = ordner / f"_{nr}.html"
        h.write_text(brief_pdf.dokument(seiten).replace("</style>", CSS_EXTRA + "</style>"), encoding="utf-8")
        jobs.append([str(h), str(ordner / f"{nr}.pdf")])
        freigabe.append((nr, objekt["adresse"], pakete))
    h = ordner / "_alle.html"
    h.write_text(brief_pdf.dokument(alle_seiten).replace("</style>", CSS_EXTRA + "</style>"), encoding="utf-8")
    jobs.append([str(h), str(ordner / "alle-angebote.pdf")])
    ergebnis = brief_pdf.pdf(jobs)
    for x in ordner.glob("_*.html"):
        x.unlink()
    zu_lang = [Path(o).name for o, over in ergebnis if any(over)]
    z = [f"# Freigabe: Angebote für {kunde['name']} ({heute:%d.%m.%Y})", "",
         f"Anfrage: {kunde.get('anfrage', '')}", "", "| Angebot | Objekt | Paket 1 | Paket 2 | Paket 3 | Marge (Inhaber) |", "|---|---|---|---|---|---|"]
    for nr, adresse, pakete in freigabe:
        z.append(f"| {nr} | {adresse} | {eur(pakete[0]['netto'])} | {eur(pakete[1]['netto'])} | {eur(pakete[2]['netto'])} | "
                 f"{' / '.join(str(p['marge']) + ' %' for p in pakete)} |")
    z += ["", "Alle Beträge netto pro Monat (Richtpreise, Annahme siehe Angebot). Interne Marge nach Selbstkosten 49,35 €/h – "
          "steht NICHT im Angebot.", "", "**Nach Freigabe:** Antwort aus `antwort-email.md` mit `alle-angebote.pdf` als Anhang "
          "aus dem IONOS-Postfach senden (Kunde hat selbst angefragt – E-Mail ist zulässig).", ""]
    if zu_lang:
        z.append(f"⚠ Seite zu voll (Schrift verkleinert): {', '.join(zu_lang)}")
    (ordner / "FREIGABE.md").write_text("\n".join(z) + "\n", encoding="utf-8")
    print("\n".join(z))


if __name__ == "__main__":
    main(sys.argv[1])
