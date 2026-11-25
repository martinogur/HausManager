#!/usr/bin/env python3
"""Druckfertige Bewertungskarten mit QR-Code (Ziel: https://www.haus-meister-helden.de/bewertung.html).

Die Seite leitet zum Google-Bewertungslink weiter (in webseite/build.py → FIRMA["google_bewertung"]).
Deshalb bleiben gedruckte Karten gültig, auch wenn sich der Google-Link ändert.

Aufruf (braucht das Paket qrcode, z. B. aus /tmp/hh-venv):
  /tmp/hh-venv/bin/python marketing/bewertungen/karten.py
Ergebnis: marketing/bewertungen/druck/karte-a6.pdf und visitenkarte.pdf (Vorder- und Rückseite)
"""
import io
import subprocess
from pathlib import Path

import qrcode
import qrcode.image.svg

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "druck"
FONTS = REPO / "webseite" / "static" / "fonts"
ZIEL = "https://www.haus-meister-helden.de/bewertung.html"
TEL = "05241 3389748"

HAUS = ('<svg viewBox="0 0 64 48" class="haus"><path d="M5 31L29 9l10 9v-8h7v14l11 10" fill="none" stroke="#7ccc13" stroke-width="6" '
        'stroke-linecap="round" stroke-linejoin="round"/><g fill="#7ccc13"><rect x="21" y="25" width="5" height="5" rx="1"/>'
        '<rect x="28" y="25" width="5" height="5" rx="1"/><rect x="21" y="32" width="5" height="5" rx="1"/><rect x="28" y="32" width="5" height="5" rx="1"/></g></svg>')


def qr_svg():
    img = qrcode.make(ZIEL, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=1,
                      error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO(); img.save(buf)
    s = buf.getvalue().decode()
    return s[s.index("<svg"):]


CSS = f"""
@font-face{{font-family:A;src:url("{(FONTS / 'archivo.woff2').as_uri()}");font-weight:100 900;font-stretch:62% 125%}}
@font-face{{font-family:I;src:url("{(FONTS / 'inter.woff2').as_uri()}");font-weight:100 900}}
*{{box-sizing:border-box;margin:0}}
body{{font-family:I,sans-serif;color:#111412}}
.seite{{position:relative;overflow:hidden;page-break-after:always}}
.seite:last-child{{page-break-after:auto}}
.dunkel{{background:#0d100e;color:#eef1ec}}
.marke{{display:flex;align-items:center;gap:2.5mm;font-family:A;font-weight:850;font-stretch:82%;letter-spacing:.03em}}
.marke small{{display:block;font-family:I;font-weight:500;letter-spacing:.45em;font-size:.5em;color:#a8b1aa}}
h1{{font-family:A;font-stretch:84%;font-weight:850;text-transform:uppercase;line-height:1}}
h1 em{{font-style:normal;color:#7ccc13}}
.qr{{background:#fff;border-radius:3mm;padding:2.5mm}}
.qr svg{{display:block;width:100%;height:auto}}
.qr path{{fill:#111412}}
.sterne{{color:#7ccc13;letter-spacing:.15em}}
"""


def a6():
    return f"""<section class="seite dunkel" style="width:105mm;height:148mm;padding:10mm 9mm">
<div class="marke" style="font-size:5.2mm">{HAUS.replace('class="haus"', 'style="width:11mm;height:8.5mm"')}<div>HAUSMEISTER<small>HELDEN</small></div></div>
<h1 style="font-size:10.5mm;margin-top:9mm">Danke für<br><em>Ihren Auftrag!</em></h1>
<p style="font-size:3.5mm;line-height:1.45;color:#c3cbc4;margin-top:4mm">Wie zufrieden waren Sie mit unserer Arbeit? Ihre ehrliche Bewertung bei Google hilft uns – und anderen Eigentümern in Gütersloh.</p>
<div style="display:flex;gap:5mm;align-items:center;margin-top:7mm">
  <div class="qr" style="width:36mm">{qr_svg()}</div>
  <div style="font-size:3.2mm;line-height:1.5;color:#c3cbc4">QR-Code mit der Handy-Kamera scannen<br><b style="color:#fff">dauert ca. 30 Sekunden</b><br><span style="font-size:2.7mm;color:#8a948c">haus-meister-helden.de/bewertung.html</span></div>
</div>
<div style="position:absolute;left:9mm;right:9mm;bottom:8mm;border-top:.3mm solid #2a302b;padding-top:3mm;font-size:2.9mm;color:#a8b1aa;display:flex;justify-content:space-between">
  <span>Fragen? <b style="color:#fff">{TEL}</b></span><span>auch per WhatsApp</span></div>
</section>"""


def visitenkarte():
    vorne = f"""<section class="seite" style="width:85mm;height:55mm;padding:6mm;background:#fff">
<div class="marke" style="font-size:4.6mm">{HAUS.replace('class="haus"', 'style="width:10mm;height:7.5mm"')}<div>HAUSMEISTER<small style="color:#5c645e">HELDEN</small></div></div>
<div style="height:.8mm;background:#7ccc13;border-radius:1mm;margin:3.2mm 0"></div>
<div style="font-size:3mm;line-height:1.5"><b>Martin Ogur</b> · Inhaber<br>Hausmeisterservice für Gütersloh &amp; Umgebung<br>
<b>{TEL}</b> · Telefon &amp; WhatsApp<br>info@haus-meister-helden.de<br>www.haus-meister-helden.de</div>
</section>"""
    hinten = f"""<section class="seite dunkel" style="width:85mm;height:55mm;padding:6mm;display:flex;gap:4.5mm;align-items:center">
<div class="qr" style="width:30mm;flex:none">{qr_svg()}</div>
<div><h1 style="font-size:5.6mm">Wie war's?<br><em>Bewerten Sie uns!</em></h1>
<p style="font-size:2.7mm;line-height:1.45;color:#c3cbc4;margin-top:2mm">Code scannen und Ihre ehrliche Meinung bei Google hinterlassen. Danke!</p></div>
</section>"""
    return vorne + hinten


def pdf(html, ziel, breite, hoehe):
    h = OUT / (ziel + ".html")
    h.write_text(f'<!doctype html><html lang="de"><head><meta charset="utf-8"><style>{CSS}</style></head><body>{html}</body></html>', encoding="utf-8")
    js = ("const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage();"
          f"await p.goto('file://{h}');await p.evaluate(()=>document.fonts.ready);"
          f"await p.pdf({{path:'{OUT / (ziel + '.pdf')}',width:'{breite}',height:'{hoehe}',printBackground:true,pageRanges:''}});"
          f"await p.setViewportSize({{width:900,height:900}});await p.screenshot({{path:'{OUT / (ziel + '.png')}',fullPage:true}});await b.close()}})();")
    subprocess.run(["node", "-e", js], check=True, cwd="/tmp")
    h.unlink()


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    pdf(a6(), "karte-a6", "105mm", "148mm")
    pdf(visitenkarte(), "visitenkarte", "85mm", "55mm")
    print("Fertig:", ", ".join(sorted(p.name for p in OUT.glob("*.pdf"))))
