#!/usr/bin/env python3
"""Erzeugt fertige Instagram-Grafiken (und einfache Text-Reels) im Hausmeister-Helden-Design.

Kein Filmen nötig: Inhalt kommt aus einer JSON-Datei, z. B. marketing/instagram/2026-KW48.json:
{
  "posts": [
    {"id": "01-winterdienst-pflichten", "format": "karussell",   # karussell = 1080x1350 PNGs
     "folien": [
       {"art": "titel", "kicker": "Winterdienst", "titel": "3 Pflichten für Vermieter", "text": "Was Sie jetzt wissen müssen"},
       {"art": "punkt", "nr": "1", "titel": "Räumen & streuen", "text": "Gehweg und Zugang müssen sicher sein."},
       {"art": "liste", "titel": "Checkliste", "punkte": ["…", "…"]},
       {"art": "cta", "titel": "Lieber abgeben?", "text": "Wir übernehmen das – mit Protokoll."}
     ]},
    {"id": "02-mythen-reel", "format": "reel", "sekunden_pro_folie": 3, "folien": [...]}  # reel = 1080x1920 + MP4
  ]
}
Zusätzlich für Werbeanzeigen (marketing/instagram/werbung/anzeigen.json):
  {"art": "anzeige", "kicker": "…", "titel": "…", "text": "…", "punkte": ["…"], "button": "…"}  # Einzelbild mit Button
  Jede Folie optional "schrift": 110  -> Titelgröße in px erzwingen, falls ein langes Wort übersteht
  Post-Option "story_rand": true  -> größerer Rand oben/unten (Story-/Reel-Bedienelemente verdecken nichts)
  Folien-Option "platz_unten": 420 -> Inhalt rückt nach oben, unten bleiben ca. so viele px frei (für Quiz-/Link-Sticker)
Aufruf: python3 marketing/instagram/grafik.py marketing/instagram/2026-KW48.json
Ergebnis: marketing/instagram/grafiken/<KW>/<post-id>/folie-01.png … (+ reel.mp4)
"""
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FONTS = REPO / "webseite" / "static" / "fonts"
TEL = "05241 3389748"
WEB = "haus-meister-helden.de"

HOUSE = ('<svg viewBox="0 0 64 48" class="house"><path d="M5 31L29 9l10 9v-8h7v14l11 10" fill="none" stroke="#7ccc13" '
         'stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/><g fill="#7ccc13"><rect x="21" y="25" width="5" height="5" rx="1"/>'
         '<rect x="28" y="25" width="5" height="5" rx="1"/><rect x="21" y="32" width="5" height="5" rx="1"/><rect x="28" y="32" width="5" height="5" rx="1"/></g></svg>')

CSS = """
@font-face{font-family:A;src:url("FONTS/archivo.woff2");font-weight:100 900;font-stretch:62% 125%}
@font-face{font-family:I;src:url("FONTS/inter.woff2");font-weight:100 900}
*{box-sizing:border-box;margin:0}
html,body{width:WPX;height:HPX}
body{font-family:I,sans-serif;color:#eef1ec;background:#0d100e;position:relative;overflow:hidden}
.bg{position:absolute;inset:0;background:radial-gradient(900px 700px at 100% 0,rgba(124,204,19,.22),transparent 60%),radial-gradient(700px 600px at 0 100%,rgba(124,204,19,.10),transparent 60%)}
.grid{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.04) 1px,transparent 1px);background-size:72px 72px;mask-image:linear-gradient(180deg,#000,transparent 80%)}
.wrap{position:absolute;inset:0;padding:96px 88px;display:flex;flex-direction:column}
.top{display:flex;align-items:center;gap:16px;font-family:A;font-weight:850;font-stretch:82%;font-size:30px;letter-spacing:.04em}
.top .house{width:58px;height:44px}
.top small{display:block;font-family:I;font-weight:500;font-size:16px;letter-spacing:.5em;color:#a8b1aa}
.count{margin-left:auto;font-family:I;font-weight:600;font-size:24px;color:#8a948c}
.main{flex:1;display:flex;flex-direction:column;justify-content:center;gap:36px}
.kicker{display:inline-flex;align-items:center;gap:16px;font-weight:700;font-size:28px;letter-spacing:.16em;text-transform:uppercase;color:#7ccc13}
.kicker:before{content:"";width:48px;height:6px;border-radius:3px;background:#7ccc13}
h1{font-family:A;font-stretch:84%;font-weight:850;text-transform:uppercase;line-height:.98;font-size:FS1px;letter-spacing:-.01em}
em{font-style:normal;color:#7ccc13}
.card em{color:#3d6f08}
h2{font-family:A;font-stretch:86%;font-weight:800;text-transform:uppercase;line-height:1.02;font-size:FS2px}
p{font-size:40px;line-height:1.4;color:#c3cbc4;max-width:20em}
.nr{font-family:A;font-stretch:78%;font-weight:850;font-size:220px;line-height:.8;color:#7ccc13}
ul{list-style:none;padding:0;display:flex;flex-direction:column;gap:26px}
li{display:flex;gap:26px;align-items:flex-start;font-size:38px;line-height:1.3;color:#e3e8e2}
li:before{content:"";flex:none;width:46px;height:46px;border-radius:12px;margin-top:2px;background:#7ccc13 url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='3.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M5 12l5 5 9-10'/%3E%3C/svg%3E") center/28px no-repeat}
.card{background:#fff;color:#111412;border-radius:36px;padding:56px;display:flex;flex-direction:column;gap:22px}
.card p{color:#4c544e}
.btn{display:inline-flex;align-self:flex-start;align-items:center;gap:16px;background:#7ccc13;color:#0b0d0b;font-weight:800;font-size:36px;border-radius:999px;padding:26px 44px}
.foot{display:flex;justify-content:space-between;align-items:center;font-size:26px;color:#a8b1aa;border-top:2px solid #2a302b;padding-top:30px}
.foot b{color:#fff}
.swipe{color:#7ccc13;font-weight:700}
"""


def esc(s):
    return html.escape(str(s or ""))


def titel_html(t):
    # *wort* wird grün hervorgehoben
    parts = esc(t).split("*")
    return "".join(f"<em>{p}</em>" if i % 2 else p for i, p in enumerate(parts))


def folie_html(f, i, n, reel, story_rand=False):
    art = f.get("art", "punkt")
    w, h = (1080, 1920) if reel else (1080, 1350)
    lang = len(f.get("titel", ""))
    fs1 = 150 if lang < 18 else 124 if lang < 30 else 100
    if reel:
        fs1 += 20
    fs1 = int(f.get("schrift", fs1))  # optional: Titelgröße in px erzwingen (bei langen Wörtern)
    css = (CSS.replace("FONTS", FONTS.as_uri()).replace("WPX", f"{w}px").replace("HPX", f"{h}px")
           .replace("FS1", str(fs1)).replace("FS2", "96"))
    if art == "titel":
        body = (f'<div class="kicker">{esc(f.get("kicker"))}</div><h1>{titel_html(f.get("titel"))}</h1>'
                + (f'<p>{esc(f.get("text"))}</p>' if f.get("text") else ""))
    elif art == "punkt":
        body = ((f'<div class="nr">{esc(f.get("nr"))}</div>' if f.get("nr") else "")
                + f'<h2>{titel_html(f.get("titel"))}</h2>' + (f'<p>{esc(f.get("text"))}</p>' if f.get("text") else ""))
    elif art == "liste":
        body = (f'<h2>{titel_html(f.get("titel"))}</h2><ul>' + "".join(f"<li>{esc(p)}</li>" for p in f.get("punkte", [])) + "</ul>")
    elif art == "mythos":
        body = (f'<div class="kicker">Mythos</div><h2 style="color:#8a948c;text-decoration:line-through;text-decoration-color:#7ccc13;text-decoration-thickness:8px">{esc(f.get("mythos"))}</h2>'
                f'<div class="card"><div class="kicker" style="color:#3d6f08">Fakt</div><p style="font-size:40px;color:#111412">{esc(f.get("fakt"))}</p></div>')
    elif art == "anzeige":
        body = (f'<div class="kicker">{esc(f.get("kicker"))}</div><h1>{titel_html(f.get("titel"))}</h1>'
                + (f'<p>{esc(f.get("text"))}</p>' if f.get("text") else "")
                + ('<ul>' + "".join(f"<li>{esc(p)}</li>" for p in f.get("punkte", [])) + "</ul>" if f.get("punkte") else "")
                + f'<div class="btn">{esc(f.get("button") or "WhatsApp " + TEL)}</div>')
    elif art == "cta":
        body = (f'<div class="card"><h2>{titel_html(f.get("titel"))}</h2>'
                + (f'<p>{esc(f.get("text"))}</p>' if f.get("text") else "")
                + f'<div class="btn">WhatsApp {TEL}</div></div>'
                f'<p style="font-size:34px">Hausmeisterservice für Gütersloh &amp; Umgebung · Besichtigung kostenlos</p>')
    else:
        raise ValueError(f"Unbekannte Folienart: {art}")
    swipe = '<span class="swipe">Wischen →</span>' if (not reel and i < n) else f"<span>{WEB}</span>"
    count = f'<span class="count">{i}/{n}</span>' if n > 1 else ""
    if story_rand:
        css += ".wrap{padding:250px 88px 330px}"
    if f.get("platz_unten"):
        css += f".main{{padding-bottom:{int(f['platz_unten'])}px}}"
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><style>{css}</style></head><body>
<div class="bg"></div><div class="grid"></div><div class="wrap">
<div class="top">{HOUSE}<div>HAUSMEISTER<small>HELDEN</small></div>{count}</div>
<div class="main">{body}</div>
<div class="foot"><span><b>{TEL}</b> · WhatsApp</span>{swipe}</div>
</div></body></html>"""


def render(jobs):
    """jobs: Liste (html_pfad, png_pfad, breite, hoehe)"""
    js = """const {chromium}=require('playwright');const jobs=JSON.parse(process.argv[process.argv.length-1]);(async()=>{const b=await chromium.launch();
for(const [src,out,w,h] of jobs){const p=await b.newPage({viewport:{width:w,height:h},deviceScaleFactor:1});
await p.goto('file://'+src);await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(150);await p.screenshot({path:out});await p.close();}
await b.close()})();"""
    subprocess.run(["node", "-e", js, json.dumps(jobs)], check=True, cwd="/tmp")


def main(pfad):
    pfad = Path(pfad).resolve()
    plan = json.loads(pfad.read_text(encoding="utf-8"))
    ziel_basis = pfad.parent / "grafiken" / pfad.stem
    for post in plan["posts"]:
        reel = post.get("format") == "reel"
        ziel = ziel_basis / post["id"]
        if ziel.exists():
            shutil.rmtree(ziel)
        ziel.mkdir(parents=True)
        folien = post["folien"]
        jobs = []
        for i, f in enumerate(folien, 1):
            h = ziel / f"_folie-{i:02d}.html"
            h.write_text(folie_html(f, i, len(folien), reel, post.get("story_rand", False)), encoding="utf-8")
            jobs.append([str(h), str(ziel / f"folie-{i:02d}.png"), 1080, 1920 if reel else 1350])
        render(jobs)
        for h in ziel.glob("_folie-*.html"):
            h.unlink()
        if reel and len(folien) > 1:  # Einzelbild (z. B. Story-Anzeige) braucht kein Video
            sek = float(post.get("sekunden_pro_folie", 3))
            liste = ziel / "_liste.txt"
            pngs = sorted(ziel.glob("folie-*.png"))
            liste.write_text("".join(f"file '{p}'\nduration {sek}\n" for p in pngs) + f"file '{pngs[-1]}'\n")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(liste),
                            "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-movflags", "+faststart", str(ziel / "reel.mp4")], check=True)
            liste.unlink()
        print(f"{post['id']}: {len(folien)} Folien" + (" + reel.mp4" if reel and len(folien) > 1 else ""))


if __name__ == "__main__":
    main(sys.argv[1])
