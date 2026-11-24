#!/usr/bin/env python3
"""Erstellt die Freigabe-Übersicht für die Webseite (webseite/freigabe/).

Ablauf: build.py -> freigabe.py -> Übersicht als Artifact veröffentlichen ->
Inhaber gibt im Chat frei -> `git push origin HEAD:webseite-live` -> IONOS Deploy Now
veröffentlicht automatisch auf www.haus-meister-helden.de.

Änderungen für die Übersicht stehen in freigabe/aenderungen.md (eine Zeile pro Punkt, "- ...").
"""
import datetime as dt
import html
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
PUBLIC = ROOT / "public"
OUT = ROOT / "freigabe"
LIVE_BRANCH = "webseite-live"
# Wird auf True gesetzt, sobald IONOS Deploy Now mit dem Branch webseite-live verbunden ist.
DEPLOY_NOW_VERBUNDEN = False

SEITEN_NAMEN = {
    "index.html": "Startseite", "hausverwaltungen.html": "Für Hausverwaltungen", "ratgeber.html": "Ratgeber (Übersicht)",
    "impressum.html": "Impressum", "datenschutz.html": "Datenschutz", "404.html": "Fehlerseite (404)",
}
OFFENE_PUNKTE = [
    "Impressum: Rechtsform und ggf. USt-IdNr. ergänzen, Texte rechtlich prüfen lassen",
    "Preise: netto oder brutto? Muss auf der Seite stehen",
    "Echte Fotos (Team, Einsätze, Vorher/Nachher) schicken",
    "Echte Google-Bewertungen / Kundenstimmen freigeben",
]


def git(*args):
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def status_der_seiten(seiten):
    subprocess.run(["git", "-C", str(REPO), "fetch", "-q", "origin", LIVE_BRANCH], capture_output=True)
    live = git("rev-parse", "--verify", "-q", f"origin/{LIVE_BRANCH}")
    if not live:
        return {s: "neu" for s in seiten}, False
    st = {}
    for s in seiten:
        alt = git("show", f"{live}:webseite/public/{s}")
        if alt is None:
            st[s] = "neu"
        else:
            neu = (PUBLIC / s).read_text(encoding="utf-8")
            st[s] = "unverändert" if alt == neu else "geändert"
    return st, True


def titel(datei):
    t = (PUBLIC / datei).read_text(encoding="utf-8")
    a = t.find("<title>") + 7
    return html.unescape(t[a:t.find("</title>")].split(" | ")[0])


def screenshots():
    js = r"""
const {chromium,devices}=require('playwright');const http=require('http');const fs=require('fs');const path=require('path');
const dir=process.argv[2], out=process.argv[3];
const types={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.woff2':'font/woff2','.svg':'image/svg+xml','.jpg':'image/jpeg','.png':'image/png'};
const srv=http.createServer((q,r)=>{let p=path.join(dir,decodeURIComponent(q.url.split('?')[0]));if(p.endsWith('/'))p+='index.html';
 fs.readFile(p,(e,d)=>{if(e){r.writeHead(404);r.end();return}r.writeHead(200,{'content-type':types[path.extname(p)]||'application/octet-stream'});r.end(d)})}).listen(0,async()=>{
 const port=srv.address().port;const b=await chromium.launch();const fehler=[];
 const sets=[['desktop',{viewport:{width:1366,height:860},deviceScaleFactor:1}],['handy',devices['iPhone 13']]];
 for(const [n,o] of sets){const c=await b.newContext(o);const p=await c.newPage();p.on('pageerror',e=>fehler.push(n+': '+e));
  p.on('console',m=>{if(m.type()==='error')fehler.push(n+': '+m.text())});
  await p.goto(`http://localhost:${port}/index.html`,{waitUntil:'networkidle'});await p.waitForTimeout(400);
  const w=await p.evaluate(()=>innerWidth);if(n==='handy'&&w!==390)fehler.push('Handy: Seite breiter als Bildschirm ('+w+'px)');
  await p.screenshot({path:path.join(out,'vorschau-'+n+'.png')});await c.close();}
 await b.close();srv.close();fs.writeFileSync(path.join(out,'pruefung.json'),JSON.stringify(fehler));});
"""
    f = OUT / "_shot.js"
    f.write_text(js, encoding="utf-8")
    subprocess.run(["node", str(f), str(PUBLIC), str(OUT)], check=True, cwd="/tmp")
    f.unlink()
    return json.loads((OUT / "pruefung.json").read_text())


def main():
    OUT.mkdir(exist_ok=True)
    seiten = sorted(p.name for p in PUBLIC.glob("*.html"))
    seiten.sort(key=lambda s: (s != "index.html", s in ("impressum.html", "datenschutz.html", "404.html"), s))
    status, live_gibt_es = status_der_seiten(seiten)
    fehler = screenshots()
    aend_datei = OUT / "aenderungen.md"
    aenderungen = [l[2:].strip() for l in aend_datei.read_text(encoding="utf-8").splitlines() if l.startswith("- ")] if aend_datei.exists() else []
    version = git("rev-parse", "--short", "HEAD") or "?"
    jetzt = dt.datetime.now().strftime("%d.%m.%Y, %H:%M")
    n_neu = sum(1 for s in status.values() if s == "neu")
    n_geaendert = sum(1 for s in status.values() if s == "geändert")

    e = html.escape
    zeilen = "".join(
        f'<tr><td><span class="pname">{e(SEITEN_NAMEN.get(s) or titel(s))}</span><span class="file">{s}</span></td>'
        f'<td><span class="tag t-{ {"neu": "neu", "geändert": "mod", "unverändert": "same"}[status[s]] }">{status[s]}</span></td>'
        f'<td><a href="vorschau/{s}" target="_blank" rel="noopener">Ansehen</a></td></tr>' for s in seiten)
    aend_html = "".join(f"<li>{e(a)}</li>" for a in aenderungen) or "<li>Keine Beschreibung hinterlegt.</li>"
    offen_html = "".join(f"<li>{e(a)}</li>" for a in OFFENE_PUNKTE)
    pruef = ('<p class="ok">Automatische Prüfung bestanden: keine Fehler, Handy-Ansicht passt.</p>' if not fehler else
             '<p class="warn">Prüfung hat Hinweise gefunden:</p><ul>' + "".join(f"<li>{e(x)}</li>" for x in fehler) + "</ul>")
    deploy = ("Nach deiner Freigabe veröffentlicht IONOS Deploy Now die Seite automatisch auf <b>www.haus-meister-helden.de</b>, meist innerhalb weniger Minuten."
              if DEPLOY_NOW_VERBUNDEN else
              "Noch nicht verbunden: Sobald IONOS Deploy Now eingerichtet ist, geht die Seite nach deiner Freigabe automatisch online. Bis dahin wird nur der Stand gespeichert.")

    page = f"""<title>Webseiten-Freigabe Hausmeister Helden</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Layout: eine ruhige Spalte – Status oben, dann Vorschau, Änderungen, Seitenliste. Marke: Grün aus dem Logo + Schwarz. */
@font-face{{font-family:"Archivo";src:url("vorschau/fonts/archivo.woff2") format("woff2");font-weight:100 900;font-stretch:62% 125%;font-display:swap}}
@font-face{{font-family:"Inter";src:url("vorschau/fonts/inter.woff2") format("woff2");font-weight:100 900;font-display:swap}}
:root{{--bg:#f6f8f3;--card:#ffffff;--fg:#141814;--muted:#5c645e;--line:#e1e6dc;--accent:#7ccc13;--accent-ink:#3d6f08;--accent-soft:#eef7e1;
--warn:#a15c00;--warn-soft:#fff3df;--blue:#1f5fbf;--blue-soft:#e8f0fc;--head:"Archivo",system-ui,sans-serif;--body:"Inter",system-ui,-apple-system,"Segoe UI",sans-serif}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0f120f;--card:#171b17;--fg:#eef1ec;--muted:#9aa49c;--line:#2a302a;--accent:#8bd925;--accent-ink:#a6e85a;--accent-soft:#1c2a12;--warn:#f0b057;--warn-soft:#2e2412;--blue:#8db6f5;--blue-soft:#152338;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#0f120f;--card:#171b17;--fg:#eef1ec;--muted:#9aa49c;--line:#2a302a;--accent:#8bd925;--accent-ink:#a6e85a;--accent-soft:#1c2a12;--warn:#f0b057;--warn-soft:#2e2412;--blue:#8db6f5;--blue-soft:#152338;color-scheme:dark}}
body{{background:var(--bg);color:var(--fg);font-family:var(--body);font-size:16px;line-height:1.55}}
.wrap{{max-width:980px;margin:0 auto;padding-block:28px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:20px}}
h1,h2{{font-family:var(--head);font-stretch:85%;text-transform:uppercase;line-height:1.05;margin:0;text-wrap:balance}}
h1{{font-size:clamp(1.9rem,5vw,2.8rem);font-weight:850}}
h2{{font-size:1.25rem;font-weight:800;letter-spacing:.01em}}
.brand{{display:flex;align-items:center;gap:10px;font-family:var(--head);font-weight:850;font-stretch:82%;letter-spacing:.02em;font-size:1rem}}
.brand svg{{width:34px;height:26px}}
.head{{display:grid;gap:12px}}
.meta{{color:var(--muted);font-size:.9rem;font-variant-numeric:tabular-nums}}
.pill{{display:inline-flex;align-items:center;gap:8px;padding:6px 12px;border-radius:999px;background:var(--warn-soft);color:var(--warn);font-weight:700;font-size:.85rem;width:fit-content}}
.pill::before{{content:"";width:8px;height:8px;border-radius:50%;background:currentColor}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px;display:grid;gap:14px;min-width:0}}
.approve{{border:2px solid var(--accent);background:var(--accent-soft)}}
.approve .cmd{{font-family:var(--head);font-stretch:90%;font-weight:800;font-size:1.35rem;background:var(--card);border:1px dashed var(--accent-ink);border-radius:10px;padding:10px 14px;width:fit-content;color:var(--accent-ink)}}
.approve p,.card p{{margin:0}}
.deploy{{font-size:.92rem;color:var(--muted)}}
.stats{{display:flex;flex-wrap:wrap;gap:8px}}
.shots{{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,1fr);gap:16px;align-items:start}}
@media (max-width:640px){{.shots{{grid-template-columns:1fr}}}}
.shot{{display:grid;gap:8px;min-width:0}}
.shot a{{display:block;border:1px solid var(--line);border-radius:12px;overflow:hidden}}
.shot img{{display:block;width:100%;height:auto}}
.shot span{{font-size:.82rem;color:var(--muted);font-weight:600;letter-spacing:.06em;text-transform:uppercase}}
ul.list{{margin:0;padding-left:1.2em;display:grid;gap:6px}}
.tablewrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:.95rem}}
td{{padding:11px 8px;border-bottom:1px solid var(--line);vertical-align:middle}}
tr:last-child td{{border-bottom:0}}
td:last-child{{text-align:right;white-space:nowrap}}
.pname{{display:block;font-weight:650}}
.file{{display:block;font-size:.8rem;color:var(--muted)}}
.tag{{display:inline-block;padding:3px 10px;border-radius:999px;font-size:.78rem;font-weight:700}}
.t-neu{{background:var(--blue-soft);color:var(--blue)}}
.t-mod{{background:var(--warn-soft);color:var(--warn)}}
.t-same{{background:transparent;color:var(--muted);border:1px solid var(--line)}}
a{{color:var(--accent-ink);font-weight:700}}
a:focus-visible{{outline:3px solid var(--accent);outline-offset:2px;border-radius:4px}}
.ok{{color:var(--accent-ink);font-weight:600}}
.warn{{color:var(--warn);font-weight:600}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media (max-width:760px){{.two{{grid-template-columns:1fr}}}}
</style>
<div class="wrap">
  <header class="head">
    <div class="brand"><svg viewBox="0 0 64 48" aria-hidden="true"><path d="M5 31L29 9l10 9v-8h7v14l11 10" fill="none" stroke="var(--accent)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/><g fill="var(--accent)"><rect x="21" y="25" width="5" height="5" rx="1"/><rect x="28" y="25" width="5" height="5" rx="1"/><rect x="21" y="32" width="5" height="5" rx="1"/><rect x="28" y="32" width="5" height="5" rx="1"/></g></svg>HAUSMEISTER HELDEN</div>
    <h1>Webseiten-Freigabe</h1>
    <span class="pill">Wartet auf deine Freigabe</span>
    <div class="meta">Stand {jetzt} Uhr · Version {version} · Ziel: www.haus-meister-helden.de</div>
  </header>

  <section class="card approve" aria-labelledby="h-frei">
    <h2 id="h-frei">So gibst du frei</h2>
    <p>Schau dir die Vorschau an. Wenn alles passt, schreib im Chat mit Claude:</p>
    <div class="cmd">Webseite freigeben</div>
    <p>Wenn du etwas ändern willst, schreib einfach, was anders sein soll. Dann kommt eine neue Übersicht.</p>
    <p class="deploy">{deploy}</p>
  </section>

  <section class="card" aria-labelledby="h-vor">
    <h2 id="h-vor">Vorschau Startseite</h2>
    <div class="shots">
      <div class="shot"><span>Computer</span><a href="vorschau/index.html" target="_blank" rel="noopener"><img src="vorschau-desktop.png" alt="Startseite auf dem Computer" width="1366" height="860"></a></div>
      <div class="shot"><span>Handy</span><a href="vorschau/index.html" target="_blank" rel="noopener"><img src="vorschau-handy.png" alt="Startseite auf dem Handy" width="390" height="664"></a></div>
    </div>
    <p><a href="vorschau/index.html" target="_blank" rel="noopener">Komplette Webseite in der Vorschau öffnen →</a></p>
    {pruef}
  </section>

  <div class="two">
    <section class="card" aria-labelledby="h-neu">
      <h2 id="h-neu">Was ist neu</h2>
      <div class="stats"><span class="tag t-neu">{n_neu} neu</span><span class="tag t-mod">{n_geaendert} geändert</span>{'' if live_gibt_es else '<span class="tag t-same">Erste Veröffentlichung</span>'}</div>
      <ul class="list">{aend_html}</ul>
    </section>
    <section class="card" aria-labelledby="h-offen">
      <h2 id="h-offen">Von dir noch offen</h2>
      <ul class="list">{offen_html}</ul>
    </section>
  </div>

  <section class="card" aria-labelledby="h-seiten">
    <h2 id="h-seiten">Alle Seiten ({len(seiten)})</h2>
    <div class="tablewrap"><table><tbody>{zeilen}</tbody></table></div>
  </section>
</div>
"""
    (OUT / "index.html").write_text(page, encoding="utf-8")
    # Dateiliste für die Veröffentlichung (Artifact `files`)
    files = {"vorschau-desktop.png": str((OUT / "vorschau-desktop.png").relative_to(REPO)),
             "vorschau-handy.png": str((OUT / "vorschau-handy.png").relative_to(REPO))}
    for p in sorted(PUBLIC.rglob("*")):
        if p.is_file() and p.suffix in (".html", ".css", ".js", ".woff2", ".svg", ".jpg", ".png"):
            files["vorschau/" + str(p.relative_to(PUBLIC))] = str(p.relative_to(REPO))
    (OUT / "dateien.json").write_text(json.dumps(files, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Übersicht: {OUT/'index.html'} · {len(seiten)} Seiten · {n_neu} neu, {n_geaendert} geändert · Prüfung: {'ok' if not fehler else fehler}")


if __name__ == "__main__":
    main()
