#!/usr/bin/env python3
"""Macht aus den Brief-Entwürfen (akquise/briefe/*.md) druckfertige PDFs nach DIN 5008 (Form B, Fensterkuvert DL/C5/6).

Aufruf:
  python3 akquise/brief_pdf.py                 # alle Briefe
  python3 akquise/brief_pdf.py L001 L002       # nur diese
  python3 akquise/brief_pdf.py --variante A    # Briefe mit Varianten: A = nach Telefonat, B = niemand erreicht (Standard)
Ergebnis: akquise/briefe/pdf/<Brief>.pdf und akquise/briefe/pdf/alle-briefe.pdf (zum Drucken in einem Rutsch).
Offene Platzhalter [OFFEN …] werden gelb markiert und am Ende aufgelistet – solche Briefe nicht verschicken.
"""
import datetime as dt
import html
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BRIEFE = REPO / "akquise" / "briefe"
OUT = BRIEFE / "pdf"
FONTS = REPO / "webseite" / "static" / "fonts"
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]

ABSENDER_ZEILE = "Hausmeister Helden · Auf der Benkert 68 · 33330 Gütersloh"
FUSS = [
    ("Hausmeister Helden", "Inhaber Martin Ogur<br>Auf der Benkert 68<br>33330 Gütersloh"),
    ("Kontakt", "Telefon / WhatsApp 05241 3389748<br>info@haus-meister-helden.de<br>www.haus-meister-helden.de"),
    ("Erreichbar", "Mo–Sa, 7:00–20:00 Uhr<br>Antwort innerhalb von 24 Stunden<br>Besichtigung kostenlos"),
]
LOGO = ('<svg viewBox="0 0 240 56" class="logo"><g fill="none" stroke="#7ccc13" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M5 31L29 9l10 9v-8h7v14l11 10"/></g><g fill="#7ccc13"><rect x="21" y="25" width="5" height="5" rx="1"/>'
        '<rect x="28" y="25" width="5" height="5" rx="1"/><rect x="21" y="32" width="5" height="5" rx="1"/><rect x="28" y="32" width="5" height="5" rx="1"/></g>'
        '<text x="68" y="31" font-family="Archivo" font-weight="850" font-size="27" fill="#111" textLength="164" lengthAdjust="spacingAndGlyphs">HAUSMEISTER</text>'
        '<text x="69" y="50" font-family="Archivo" font-weight="500" font-size="12.5" fill="#111" textLength="160" lengthAdjust="spacing">HELDEN</text></svg>')

CSS = f"""
@font-face{{font-family:Archivo;src:url("{(FONTS / 'archivo.woff2').as_uri()}");font-weight:100 900;font-stretch:62% 125%}}
@font-face{{font-family:Inter;src:url("{(FONTS / 'inter.woff2').as_uri()}");font-weight:100 900}}
@page{{size:A4;margin:0}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:Inter,sans-serif;font-size:10.5pt;line-height:1.45;color:#141814}}
.seite{{position:relative;width:210mm;height:297mm;padding:0 20mm 0 25mm;page-break-after:always;overflow:hidden}}
.seite:last-child{{page-break-after:auto}}
.kopf{{position:absolute;top:12mm;left:25mm;right:20mm;display:flex;justify-content:space-between;align-items:flex-start}}
.logo{{width:62mm;height:auto}}
.kopf .kontakt{{text-align:right;font-size:8.5pt;line-height:1.5;color:#4a524c}}
.kopf .kontakt b{{color:#141814}}
.linie{{position:absolute;top:38mm;left:25mm;right:20mm;height:1.2mm;background:#7ccc13;border-radius:1mm}}
.anschrift{{position:absolute;top:45mm;left:25mm;width:85mm;height:45mm}}
.anschrift .ruecksende{{font-size:7pt;color:#5c645e;border-bottom:.3pt solid #9aa49c;padding-bottom:1mm;margin-bottom:3mm;white-space:nowrap}}
.anschrift .empf{{font-size:10.5pt;line-height:1.4}}
.datum{{position:absolute;top:97mm;right:20mm;font-size:10pt}}
.inhalt{{position:absolute;top:103.5mm;left:25mm;right:20mm;bottom:30mm}}
.betreff{{font-weight:700;font-size:11pt;margin:0 0 6mm}}
.inhalt p{{margin:0 0 3.2mm}}
.inhalt ul{{margin:0 0 3.2mm;padding-left:5mm}}
.inhalt li{{margin:0 0 1.4mm}}
.inhalt strong{{font-weight:650}}
.gruss{{margin-top:5mm}}
.ps{{margin-top:5mm;font-size:9.5pt;color:#2b302c}}
.offen{{background:#fff1a8;outline:.4mm solid #e0b400}}
.fuss{{position:absolute;left:25mm;right:20mm;bottom:10mm;display:grid;grid-template-columns:repeat(3,1fr);gap:6mm;border-top:.4pt solid #c9d0ca;padding-top:2.5mm;font-size:7.5pt;line-height:1.45;color:#4a524c}}
.fuss b{{color:#141814;display:block}}
.falz1,.falz2,.loch{{position:absolute;left:5mm;width:4mm;height:0;border-top:.3pt solid #9aa49c}}
.falz1{{top:105mm}}.falz2{{top:210mm}}.loch{{top:148.5mm;width:6mm}}
"""


def inline(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[(OFFEN[^\]]*)\]", r'<span class="offen">[\1]</span>', s)
    s = re.sub(r"\[(Datum[^\]]*|Name[^\]]*|Sehr geehrte[^\]]*)\]", r'<span class="offen">[\1]</span>', s)
    return s


def heute():
    d = dt.date.today()
    return f"{d.day}. {MONATE[d.month - 1]} {d.year}"


def zerlege(text, variante):
    teile = re.split(r"^---\s*$", text, flags=re.M)
    if len(teile) < 3:
        raise ValueError("Brief-Abschnitt zwischen den ---‑Linien nicht gefunden")
    zeilen = teile[1].strip("\n").splitlines()
    bloecke, akt = [], []
    for z in zeilen:
        if z.strip():
            akt.append(z.rstrip())
        elif akt:
            bloecke.append(akt); akt = []
    if akt:
        bloecke.append(akt)
    # Block 0 = Absender (wird durch eigenen Briefkopf ersetzt), Block 1 = Empfänger, Block 2 = Ort/Datum
    empf = [z for z in bloecke[1] if not (variante == "B" and "aus dem Telefonat" in z)]
    rest = bloecke[3:] if len(bloecke) > 2 and re.match(r"^Gütersloh,", bloecke[2][0]) else bloecke[2:]
    body = []
    for b in rest:
        neu = []
        for z in b:
            m = re.match(r"^\*Variante ([AB])[^*]*:\*\s*(.*)$", z)
            if m:
                if m.group(1) == variante:
                    neu.append(m.group(2))
                continue
            m = re.match(r"^\[[^\]]*\]\s*/\s*(.+)$", z)  # „[Sehr geehrte/r …] / Sehr geehrte Damen und Herren,“
            if m:
                z = m.group(1)
            neu.append(z)
        if neu:
            body.append(neu)
    return empf, body


def body_html(body):
    out, betreff_gesetzt = [], False
    for b in body:
        if not betreff_gesetzt and len(b) == 1 and re.match(r"^\*\*.+\*\*$", b[0]):
            out.append(f'<p class="betreff">{inline(b[0][2:-2])}</p>'); betreff_gesetzt = True; continue
        if all(z.startswith("- ") for z in b):
            out.append("<ul>" + "".join(f"<li>{inline(z[2:])}</li>" for z in b) + "</ul>"); continue
        txt = " ".join(b)
        if txt.startswith("Mit freundlichen Grüßen"):
            out.append('<p class="gruss">' + "<br>".join(inline(z) for z in b) + "</p>")
            out.append('<div style="height:12mm"></div>')
            continue
        if b[0] in ("Martin Ogur",):
            out.append("<p>" + "<br>".join(inline(z) for z in b) + "</p>"); continue
        if txt.startswith("P.S."):
            out.append(f'<p class="ps">{inline(txt)}</p>'); continue
        out.append(f"<p>{inline(txt)}</p>")
    return "\n".join(out)


def seite(empf, body):
    fuss = "".join(f"<div><b>{k}</b>{v}</div>" for k, v in FUSS)
    return f"""<section class="seite">
<div class="falz1"></div><div class="loch"></div><div class="falz2"></div>
<div class="kopf">{LOGO}<div class="kontakt"><b>Martin Ogur</b> · Inhaber<br>Telefon / WhatsApp 05241 3389748<br>info@haus-meister-helden.de</div></div>
<div class="linie"></div>
<div class="anschrift"><div class="ruecksende">{ABSENDER_ZEILE}</div><div class="empf">{"<br>".join(inline(z) for z in empf)}</div></div>
<div class="datum">Gütersloh, {heute()}</div>
<div class="inhalt">{body_html(body)}</div>
<div class="fuss">{fuss}</div>
</section>"""


def dokument(seiten):
    return f'<!doctype html><html lang="de"><head><meta charset="utf-8"><style>{CSS}</style></head><body>{"".join(seiten)}</body></html>'


def pdf(jobs):
    js = """const {chromium}=require('playwright');const jobs=JSON.parse(process.argv[process.argv.length-1]);(async()=>{const b=await chromium.launch();
const p=await b.newPage();const res=[];for(const [src,out] of jobs){await p.goto('file://'+src);await p.evaluate(()=>document.fonts.ready);
const over=await p.evaluate(()=>[...document.querySelectorAll('.inhalt')].map(e=>{let fs=10.5;while(e.scrollHeight>e.clientHeight+2&&fs>9){fs-=0.25;e.style.fontSize=fs+'pt';e.style.lineHeight='1.4';}return e.scrollHeight>e.clientHeight+2;}));
await p.pdf({path:out,format:'A4',printBackground:true,preferCSSPageSize:true});res.push([out,over]);}
await b.close();console.log(JSON.stringify(res))})();"""
    r = subprocess.run(["node", "-e", js, json.dumps(jobs)], check=True, cwd="/tmp", capture_output=True, text=True)
    return json.loads(r.stdout.strip().splitlines()[-1])


def main(args):
    variante = "B"
    if "--variante" in args:
        i = args.index("--variante"); variante = args[i + 1].upper(); del args[i:i + 2]
    dateien = sorted(BRIEFE.glob("*.md"))
    if args:
        dateien = [d for d in dateien if any(d.name.startswith(a) for a in args)]
    OUT.mkdir(exist_ok=True)
    seiten, jobs, offen = [], [], {}
    for d in dateien:
        text = d.read_text(encoding="utf-8")
        empf, body = zerlege(text, variante)
        s = seite(empf, body)
        seiten.append(s)
        brieftext = "\n".join(empf + [z for b in body for z in b])
        o = sorted(set(re.findall(r"\[(?:OFFEN[^\]]*|Datum[^\]]*|Name[^\]]*)\]", brieftext)))
        if o:
            offen[d.stem] = o
        h = OUT / f"_{d.stem}.html"
        h.write_text(dokument([s]), encoding="utf-8")
        jobs.append([str(h), str(OUT / f"{d.stem}.pdf")])
    alle = OUT / "_alle.html"
    alle.write_text(dokument(seiten), encoding="utf-8")
    jobs.append([str(alle), str(OUT / "alle-briefe.pdf")])
    ergebnis = pdf(jobs)
    for h in OUT.glob("_*.html"):
        h.unlink()
    zu_lang = [Path(o).stem for o, over in ergebnis[:-1] if any(over)]
    print(f"{len(dateien)} Briefe als PDF in {OUT} (+ alle-briefe.pdf), Variante {variante}")
    if zu_lang:
        print("ZU LANG für eine Seite (kürzen!):", ", ".join(zu_lang))
    if offen:
        print("Noch offene Platzhalter (vor Versand füllen):")
        for k, v in offen.items():
            print(f"  {k}: {'; '.join(v)}")


if __name__ == "__main__":
    main(sys.argv[1:])
