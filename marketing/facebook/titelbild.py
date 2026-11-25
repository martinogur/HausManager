#!/usr/bin/env python3
"""Erzeugt das Titelbild (Cover) der Facebook-Seite im Hausmeister-Helden-Design.

grafik.py kann nur feste Instagram-Formate (1080x1350 / 1080x1920). Dieses Skript nutzt
dasselbe Muster (HTML -> Playwright-Screenshot) und dieselben Bausteine (Schriften, Farben,
Haus-Logo, render()) aus marketing/instagram/grafik.py, aber in freiem Format.

Format: 1640 x 624 px (= doppelte Auflösung der Desktop-Anzeige 820 x 312).
Am Handy schneidet Facebook links und rechts ab (Anzeige ca. 640 x 360, also Seitenverhältnis 16:9):
sichtbar bleibt nur die Mitte, ca. 1100 px breit. Deshalb steht alles Wichtige in der Mitte.

Aufruf:  python3 marketing/facebook/titelbild.py            -> marketing/facebook/grafiken/titelbild.png
         python3 marketing/facebook/titelbild.py --raster   -> zusätzlich titelbild-raster.png (zeigt Handy-Ausschnitt)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "instagram"))
from grafik import FONTS, HOUSE, TEL, WEB, render  # noqa: E402

W, H = 1640, 624
MOBIL_BREITE = round(H * 16 / 9)  # ca. 1109 px sichtbare Mitte am Handy

LEISTUNGEN = ["Treppenhausreinigung", "Winterdienst", "Gartenpflege", "Kleinreparaturen", "Mülltonnen-Service"]


def html(raster=False):
    fonts = FONTS.as_uri()
    rand = (W - MOBIL_BREITE) // 2
    raster_css = (f".raster{{position:absolute;top:0;bottom:0;left:{rand}px;width:{MOBIL_BREITE}px;"
                  "outline:4px dashed #ff3b6b;z-index:9}") if raster else ""
    punkte = "".join(f"<span>{l}</span>" for l in LEISTUNGEN)
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><style>
@font-face{{font-family:A;src:url("{fonts}/archivo.woff2");font-weight:100 900;font-stretch:62% 125%}}
@font-face{{font-family:I;src:url("{fonts}/inter.woff2");font-weight:100 900}}
*{{box-sizing:border-box;margin:0}}
html,body{{width:{W}px;height:{H}px}}
body{{font-family:I,sans-serif;color:#eef1ec;background:#0d100e;position:relative;overflow:hidden}}
.bg{{position:absolute;inset:0;background:radial-gradient(700px 520px at 100% 0,rgba(124,204,19,.24),transparent 60%),radial-gradient(640px 520px at 0 100%,rgba(124,204,19,.12),transparent 60%)}}
.grid{{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.04) 1px,transparent 1px);background-size:64px 64px;mask-image:linear-gradient(180deg,#000,transparent 85%)}}
.wrap{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px;text-align:center;padding-bottom:10px}}
.marke{{display:flex;align-items:center;gap:14px;font-family:A;font-weight:850;font-stretch:82%;font-size:26px;letter-spacing:.04em;text-align:left}}
.marke .house{{width:50px;height:38px}}
.marke small{{display:block;font-family:I;font-weight:500;font-size:14px;letter-spacing:.5em;color:#a8b1aa}}
h1{{font-family:A;font-stretch:84%;font-weight:850;text-transform:uppercase;line-height:.92;font-size:92px;letter-spacing:-.01em}}
em{{font-style:normal;color:#7ccc13}}
.leist{{display:flex;flex-wrap:wrap;justify-content:center;gap:10px 12px;max-width:1040px}}
.leist span{{font-size:20px;font-weight:600;color:#dfe5de;border:2px solid #2f3a30;border-radius:999px;padding:6px 16px;background:rgba(255,255,255,.03)}}
.kontakt{{display:flex;align-items:center;gap:20px;font-size:22px;color:#c3cbc4}}
.kontakt b{{color:#0b0d0b;background:#7ccc13;border-radius:999px;padding:9px 22px;font-weight:800}}
{raster_css}
</style></head><body><div class="bg"></div><div class="grid"></div>
<div class="wrap">
<div class="marke">{HOUSE}<div>HAUSMEISTER<small>HELDEN</small></div></div>
<h1>Ihr Haus.<br><em>Unsere Pflicht.</em></h1>
<div class="leist">{punkte}</div>
<div class="kontakt"><b>WhatsApp &amp; Telefon {TEL}</b><span>Gütersloh &amp; Umgebung</span></div>
</div>{'<div class="raster"></div>' if raster else ''}</body></html>"""


def main():
    ziel = Path(__file__).resolve().parent / "grafiken"
    ziel.mkdir(parents=True, exist_ok=True)
    jobs = []
    varianten = [("titelbild", False)] + ([("titelbild-raster", True)] if "--raster" in sys.argv else [])
    for name, raster in varianten:
        h = ziel / f"_{name}.html"
        h.write_text(html(raster), encoding="utf-8")
        jobs.append([str(h), str(ziel / f"{name}.png"), W, H])
    render(jobs)
    for h in ziel.glob("_*.html"):
        h.unlink()
    print("fertig:", ", ".join(Path(j[1]).name for j in jobs), f"({W}x{H}, Handy-Mitte {MOBIL_BREITE} px)")


if __name__ == "__main__":
    main()
