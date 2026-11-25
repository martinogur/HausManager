#!/usr/bin/env python3
"""Konkrete Angebote je Objekt mit Einzelpositionen (nach Ansicht / Besichtigung).

Eingabe: kunde.json mit "objekte": [{"adresse": …, "leistungen": {…}}]. Unterstützte Leistungen:
  treppenhaus:   {"treppenhaeuser": 1, "etagen": 3, "etagen_text": "EG, 1. OG, DG", "option_etagen": 1, "option_text": "Keller"}
  hecke:         {"lfm": 15, "schnitte": 2, "hoehe_m": 2, "stunden": 2.5, "monate": "März und Oktober"}
                 (1.3.–30.9. nur schonender Form-/Pflegeschnitt; starker Rückschnitt nur 1.10.–28.2., § 39 BNatSchG)
  rasen:         {"qm": 20, "mahden": 18}
  winterdienst:  {"lfm": 18}  oder  {"lfm": null, "schaetzung_lfm": 40, "hinweis": "…"}
Preise: Preisliste vom 24.11.2026 über portal/app/vertrieb/kalkulation.py (eine Quelle für Portal und Angebote).
Aufruf:  python3 akquise/angebote/objekt_angebot.py anfragen/<ordner>/kunde.json
"""

import datetime as dt
import html
import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import paket_angebot as pa  # noqa: E402  (setzt auch die Pfade für brief_pdf und Kalkulation)
from paket_angebot import brief_pdf, eur, k  # noqa: E402

STUNDE = k.SELBSTKOSTEN_STUNDE_CENT["inhaber"]


def c(wert) -> int:
    return int(Decimal(wert).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def positionen(l: dict) -> dict:
    """Monatliche Positionen, Optionen, Winterdienst und interne Selbstkosten."""
    pos, optionen, intern = [], [], []
    if t := l.get("treppenhaus"):
        for rhythmus, name in (("woechentlich", "wöchentlich"), ("zweiwoechentlich", "14-täglich")):
            o = k.Objektdaten(treppenhaeuser=t.get("treppenhaeuser", 1), etagen=t["etagen"], aufzug=t.get("aufzug", False), reinigung=rhythmus)
            p = k.treppenhaus(o)
            text = (f"Treppenhausreinigung {name}: {t.get('treppenhaeuser', 1)} Treppenhaus, {t['etagen']} Etagen "
                    f"({t.get('etagen_text', '')}) – Treppen, Podeste, Flure feucht, Handläufe, Schalter, Haustür")
            if rhythmus == "woechentlich":
                pos.append((text, p.monat_netto_cent, "Gebäudereinigung"))
                intern.append(("Treppenhaus", p.monat_netto_cent, c(p.minuten_monat / 60 * STUNDE + p.material_monat_cent)))
            else:
                optionen.append((f"Alternativ {name} statt wöchentlich", p.monat_netto_cent, "statt"))
        if t.get("option_etagen"):
            mehr = k.Objektdaten(treppenhaeuser=t.get("treppenhaeuser", 1), etagen=t["etagen"] + t["option_etagen"], reinigung="woechentlich")
            optionen.append((f"Option {t.get('option_text', 'weitere Etage')} mitreinigen (wöchentlich)",
                             k.treppenhaus(mehr).monat_netto_cent - pos[0][1], "zusätzlich"))
    if h := l.get("hecke"):
        if h.get("stunden"):   # hohe Hecke: nach Aufwand (beidseitig + oben) + Entsorgung
            je = k.heckenschnitt(h["stunden"], h.get("entsorgung_cent", 1500))
            detail = (f"ca. {str(h['stunden']).replace('.', ',')} Std. × 53,50 € + {eur(h.get('entsorgung_cent', 1500))} Entsorgung Schnittgut")
            minuten = Decimal(str(h["stunden"])) * 60 * h["schnitte"]
        else:
            je = k.PREISE["ga_gang"] + c(k.PREISE["ga_hecke_lfm"] * h["lfm"])
            detail = "inkl. Schnittgut"
            minuten = (k.ZEIT["ga_ruest"] + k.ZEIT["ga_hecke_lfm"] * h["lfm"]) * h["schnitte"]
        jahr = je * h["schnitte"]
        monate = h.get("monate", "März und Oktober")
        pos.append((f"Heckenschnitt {h['schnitte']}× im Jahr ({monate}; beidseitig und oben – ab 1. März nur schonender Form- und Pflegeschnitt nach Prüfung auf Vogelnester, kräftiger Rückschnitt im Oktober), "
                    f"ca. {h['lfm']} m, Höhe ca. {h.get('hoehe_m', 2)} m: {eur(je)} je Schnitt ({detail}), {eur(jahr)} im Jahr",
                    c(Decimal(jahr) / 12), "Gartenpflege"))
        intern.append(("Hecke", c(Decimal(jahr) / 12), c(minuten / 60 * STUNDE / 12)))
    if r := l.get("rasen"):
        je = k.PREISE["ga_gang"] + c(k.PREISE["ga_rasen_qm"] * r["qm"])
        jahr = je * r["mahden"] + c(k.PREISE["ga_entsorgung_qm"] * r["qm"])
        pos.append((f"Rasen mähen inkl. Kanten und Schnittgut, ca. {r['qm']} m², ca. {r['mahden']} Mahden April–Oktober "
                    f"({eur(je)} je Mahd, {eur(jahr)} im Jahr inkl. Grünschnitt-Entsorgung)", c(Decimal(jahr) / 12), "Gartenpflege"))
        minuten = (k.ZEIT["ga_ruest"] + k.ZEIT["ga_rasen_qm"] * r["qm"]) * r["mahden"]
        intern.append(("Rasen", c(Decimal(jahr) / 12), c(minuten / 60 * STUNDE / 12)))
    winter = None
    if w := l.get("winterdienst"):
        lfm = w.get("lfm") or w.get("schaetzung_lfm")
        winter = {**k.winterdienst_staffel(lfm), "lfm": lfm, "geschaetzt": not w.get("lfm"), "hinweis": w.get("hinweis", "")}
    return {"pos": pos, "optionen": optionen, "winter": winter, "intern": intern,
            "monat": sum(p[1] for p in pos)}


def seiten(kunde, objekt, nr, r, gueltig):
    e = html.escape
    zeilen = "".join(f"<tr><td>{e(t)}<br><span class='klein'>Kostenart: {e(ka)}</span></td><td class='z'>{eur(b)}</td></tr>"
                     for t, b, ka in r["pos"])
    zeilen += (f"<tr class='hl'><td><strong>Monatspauschale netto</strong></td><td class='z'><strong>{eur(r['monat'])}</strong></td></tr>"
               f"<tr><td>zzgl. 19 % USt.</td><td class='z'>{eur(c(Decimal(r['monat']) * Decimal('0.19')))}</td></tr>"
               f"<tr><td><strong>Monatspauschale brutto</strong></td><td class='z'><strong>{eur(c(Decimal(r['monat']) * Decimal('1.19')))}</strong></td></tr>")
    w = r["winter"]
    winter_html = ""
    if w:
        lfm_text = (f"ca. {w['lfm']} m (geschätzt – {e(w['hinweis'])}; wird bei der Besichtigung gemessen)" if w["geschaetzt"]
                    else f"{w['lfm']} m Bürgersteig")
        winter_html = f"""
<p class="betreff" style="margin-top:2mm">Winterdienst 1. November bis 31. März</p>
<p class="klein">Flächen: {e(w.get('flaechen', 'Hauseingang und Bürgersteig vor dem Objekt'))}, {lfm_text}. Wir kommen morgens selbstständig, ohne Anruf, an allen Wochentagen – zusätzliche Einsätze im Tagesverlauf auf Zuruf.</p>
<table class="tab"><thead><tr><th>Position</th><th style="text-align:right">netto</th></tr></thead><tbody>
<tr><td><strong>Bereitstellung</strong> je Saison (einmalig): Geräte, Vorhaltung Streumittel, Wetterkontrolle, Einsatzprotokoll</td><td class="z">{eur(w['bereitstellung_cent'])}</td></tr>
<tr><td><strong>Streueinsatz</strong> bei Glätte und Schnee bis 3 cm (Fall 1)</td><td class="z">{eur(w['streu_cent'])} je Einsatz</td></tr>
<tr><td><strong>Räumen und Streuen</strong> bei Schnee ab 3 cm bis 15 cm Gesamtschneedecke (Fall 2)</td><td class="z">{eur(w['raeum_cent'])} je Einsatz</td></tr>
<tr><td><strong>Mehraufwand</strong> bei mehr als 15 cm Schnee (Fall 3), nach tatsächlichem Aufwand</td><td class="z">{eur(w['stunde_cent'])} je Stunde</td></tr>
</tbody></table>
<p class="klein">Je Einsatz wird nur ein Fall berechnet, belegt durch das Einsatzprotokoll. Streumittel inklusive (abstumpfend; Tausalz nur, soweit die Straßenreinigungssatzung der Stadt Gütersloh es erlaubt). Wir übernehmen die Räum- und Streupflicht für die vereinbarten Flächen.</p>"""
    opt = "".join(f"<tr><td>{e(t)}</td><td class='z'>{'+' if art == 'zusätzlich' else ''}{eur(b)}{'' if art == 'zusätzlich' else ' statt ' + eur(r['pos'][0][1])} / Monat</td></tr>"
                  for t, b, art in r["optionen"])
    s1 = f"""
<p class="betreff">Angebot {e(nr)}: Hausmeisterservice {e(objekt['adresse'])}</p>
<p>{e(kunde['gruss'])}</p>
<p>{e(kunde.get('dank', 'vielen Dank für deine Anfrage.'))} Hier ist unser Angebot für {e(objekt['adresse'])} – berechnet nach dem tatsächlichen Aufwand, nicht pro Wohneinheit. Ich bin dein fester Ansprechpartner und melde mich innerhalb von 24 Stunden.</p>
<table class="tab"><thead><tr><th>Leistung (monatlich)</th><th style="text-align:right">netto</th></tr></thead><tbody>{zeilen}</tbody></table>
{('<table class="tab"><thead><tr><th>Wahlweise</th><th style="text-align:right">netto</th></tr></thead><tbody>' + opt + '</tbody></table>') if opt else ''}
<p class="klein">Sichtkontrolle (Licht, Türen, Müllplatz) bei jedem Einsatz inklusive. Angaben nach Ansicht von außen; ändert sich bei der kurzen Besichtigung etwas (z. B. Etagenzahl), passen wir den Preis transparent nach denselben Einzelpreisen an.</p>
"""
    s2 = f"""
{winter_html}
<p class="klein"><strong>Auf Wunsch zusätzlich:</strong> Mülltonnen-Service 6,50 € je Abfuhrtermin + 1,34 € je Leerung · Objektkontrolle mit Fotoprotokoll 27,00 € je Begehung · Kleinreparaturen 53,50 € je Stunde (15-Minuten-Takt, mind. 30 Min.), Material nach Beleg.</p>
<p class="klein"><strong>Bedingungen:</strong> Angebot gültig bis {e(gueltig)}. Laufzeit 12 Monate, danach Verlängerung um jeweils 12 Monate, Kündigung mit 3 Monaten Frist zum Laufzeitende in Textform. Abrechnung monatlich (Winterdienst-Einsätze mit der Monatsrechnung), zahlbar innerhalb von 14 Tagen. Auf Wunsch getrennte Rechnungen je Objekt und Kostenart für die Betriebskostenabrechnung. Kleinreparaturen ab 250 € netto nur nach vorheriger Freigabe. Alle Preise zzgl. 19 % USt. (Preisliste vom 24.11.2026).</p>
<div class="kasten"><p><strong>Beauftragung</strong></p>
<p class="klein">☐ Monatspauschale (Pos. oben) &nbsp; ☐ Winterdienst &nbsp; {''.join(f'☐ {e(t.split(" (")[0])} &nbsp; ' for t, _, _ in r['optionen'])}</p>
<p class="klein">Gewünschter Beginn: ____________________</p>
<p class="klein" style="margin-top:7mm">Ort, Datum: ______________________ &nbsp; Unterschrift: ______________________________</p></div>
<p class="gruss">Viele Grüße<br>Martin Ogur</p>
"""
    fuss = "".join(f"<div><b>{a}</b>{b}</div>" for a, b in brief_pdf.FUSS)
    kopf = (f'<div class="kopf">{brief_pdf.LOGO}<div class="kontakt"><b>Martin Ogur</b> · Inhaber<br>Telefon / WhatsApp 05241 3389748<br>'
            f'info@haus-meister-helden.de</div></div><div class="linie"></div>')
    empf = "<br>".join(e(z) for z in kunde["anschrift"])
    return [
        f'<section class="seite">{kopf}<div class="anschrift"><div class="ruecksende">{brief_pdf.ABSENDER_ZEILE}</div>'
        f'<div class="empf">{empf}</div></div><div class="datum">Gütersloh, {brief_pdf.heute()}</div>'
        f'<div class="inhalt">{s1}</div><div class="fuss">{fuss}</div></section>',
        f'<section class="seite">{kopf}<div class="inhalt2">{s2}</div><div class="fuss">{fuss}</div></section>',
    ]


def main(pfad: str) -> None:
    datei = Path(pfad).resolve()
    kunde = json.loads(datei.read_text(encoding="utf-8"))
    ordner = datei.parent
    heute = dt.date.today()
    gueltig = (heute + dt.timedelta(days=30)).strftime("%d.%m.%Y")
    alle, jobs, notiz = [], [], [f"# Freigabe: Festpreis-Angebote für {kunde['name']} ({heute:%d.%m.%Y})", ""]
    for i, objekt in enumerate(kunde["objekte"], start=1):
        nr = f"AG-{heute:%Y%m%d}-{kunde['kuerzel']}{i}"
        r = positionen(objekt["leistungen"])
        s = seiten(kunde, objekt, nr, r, gueltig)
        alle += s
        h = ordner / f"_{nr}.html"
        h.write_text(brief_pdf.dokument(s).replace("</style>", pa.CSS_EXTRA + "</style>"), encoding="utf-8")
        jobs.append([str(h), str(ordner / f"{nr}.pdf")])
        kosten = sum(x[2] for x in r["intern"])
        erloes = sum(x[1] for x in r["intern"])
        notiz += [f"## {nr} – {objekt['adresse']}", ""]
        notiz += [f"- {t}: **{eur(b)}**/Monat" for t, b, _ in r["pos"]]
        notiz += [f"- **Monatspauschale: {eur(r['monat'])} netto** ({eur(c(Decimal(r['monat']) * Decimal('1.19')))} brutto)"]
        notiz += [f"- Wahlweise: {t}: {eur(b)} ({art})" for t, b, art in r["optionen"]]
        if w := r["winter"]:
            notiz += [f"- Winterdienst: Bereitstellung {eur(w['bereitstellung_cent'])}/Saison · Streuen {eur(w['streu_cent'])} · "
                      f"Räumen+Streuen {eur(w['raeum_cent'])} · >15 cm {eur(w['stunde_cent'])}/Std. "
                      f"({w['lfm']} m{' GESCHÄTZT – vor Ort messen' if w['geschaetzt'] else ''}); Selbstkosten je Streueinsatz "
                      f"{eur(w['selbstkosten_einsatz_cent'])}"]
        notiz += [f"- Intern: Selbstkosten {eur(kosten)}/Monat, Marge {(Decimal(erloes - kosten) * 100 / erloes).quantize(Decimal('0.1'))} % "
                  "(nicht im Angebot)", ""]
    h = ordner / "_alle.html"
    h.write_text(brief_pdf.dokument(alle).replace("</style>", pa.CSS_EXTRA + "</style>"), encoding="utf-8")
    jobs.append([str(h), str(ordner / "alle-angebote.pdf")])
    ergebnis = brief_pdf.pdf(jobs)
    for x in ordner.glob("_*.html"):
        x.unlink()
    zu_lang = [Path(o).name for o, over in ergebnis if any(over)]
    if zu_lang:
        notiz.append(f"⚠ Seite zu voll (Schrift verkleinert): {', '.join(zu_lang)}")
    notiz += ["**Neu zur Bestätigung:** Winterdienst nach Marktmodell (Vergleichsangebot 03/2026): Bereitstellung 125 €, "
              "Streuen 25 €, Räumen+Streuen 53 € (bis 25 m, darüber +0,50 €/+1,20 € je Meter), >15 cm 53,50 €/Std.; "
              "Hecke über 1,5 m nach Aufwand (Std. × 53,50 € + 15 € Entsorgung).", "",
              f"**Nach Freigabe:** Antwort aus `antwort-email.md` mit `alle-angebote.pdf` aus dem IONOS-Postfach senden. Kontaktgrundlage: {kunde.get('kontaktgrundlage', 'Kunde hat angefragt')}."]
    (ordner / "FREIGABE.md").write_text("\n".join(notiz) + "\n", encoding="utf-8")
    print("\n".join(notiz))


if __name__ == "__main__":
    main(sys.argv[1])
