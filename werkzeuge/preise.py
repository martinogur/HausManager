#!/usr/bin/env python3
"""Preis-Abgleich: hält alle Stellen mit der EINEN Preisliste synchron.

Einzige Quelle: portal/app/vertrieb/preisliste.json (Portal, Angebotsgeneratoren, Webseite, Firmenprofil lesen daraus).

  python3 werkzeuge/preise.py --schreiben   # Preisabschnitt in firma/profil.md erzeugen + Webseite neu bauen
  python3 werkzeuge/preise.py --pruefen     # Fehler (Exit 1), wenn Profil oder Webseite nicht zur Preisliste passen;
                                            # Warnungen für Dokumente mit veralteten Preisen (Liste in preisliste.json)

Die Webseite geht danach NICHT automatisch live – Freigabe-Ablauf laut CLAUDE.md Regel 5.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LISTE = REPO / "portal" / "app" / "vertrieb" / "preisliste.json"
PROFIL = REPO / "firma" / "profil.md"
START, ENDE = "<!-- PREISE:START (automatisch aus preisliste.json – nicht von Hand ändern) -->", "<!-- PREISE:ENDE -->"


def eur(cent, stellen=2) -> str:
    text = f"{float(cent) / 100:,.{stellen}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text} €"


def profil_abschnitt(pl: dict) -> str:
    p, w = pl["preise"], pl["winterdienst_staffel"]
    th = round((p["th_grund"] + 3 * p["th_etage"]) * 52 / 12)
    hoehe = str(pl["hecke"]["hoehe_pauschal_bis_m"]).replace(".", ",")
    zeilen = [
        START,
        f"## Preise (Stand {pl['stand']} – netto zzgl. 19 % MwSt.)",
        "Einzige Quelle: `portal/app/vertrieb/preisliste.json`. Herleitung: `akquise/angebote/preiskalkulation.md`. "
        "Abrechnung nach Aufwand, nicht pro Wohneinheit.",
        *[f"- Freigabe {f}" for f in pl["freigaben"]],
        f"- Arbeitsstunde (Kleinreparaturen, Sonderarbeiten): {eur(p['stunde'])}/h, je angefangene 15 Min. {eur(p['viertelstunde'])}, "
        f"mindestens 30 Min. ({eur(p['mindestauftrag'])})",
        f"- Anfahrt: Gütersloh bis 10 km {eur(p['anfahrt_zone1'])}, Umland 10–25 km {eur(p['anfahrt_zone2'])}",
        f"- Treppenhausreinigung: {eur(p['th_grund'])} je Treppenhaus und Reinigung + {eur(p['th_etage'])} je Etage; "
        f"Aufzug {eur(p['th_aufzug'])}; 14-täglich +{round(float(p['th_zuschlag_14taegig']) * 100)} % je Reinigung "
        f"(Beispiel: 1 Treppenhaus, 3 Etagen, wöchentlich ≈ {eur(th, 0)}/Monat)",
        f"- Winterdienst (Standard, Saison Nov–März): Bereitstellung {eur(w['bereitstellung'])} je Objekt und Saison; "
        f"Streueinsatz (Glätte, Schnee bis 3 cm) {eur(w['streu_bis_25m'])}; Räumen + Streuen bis 15 cm {eur(w['raeum_bis_25m'])} je Einsatz "
        f"(bis {w['grund_meter']} m; je weiterer Meter +{eur(w['streu_je_weiterer_m'])} bzw. +{eur(w['raeum_je_weiterer_m'])}); "
        f"über 15 cm nach Aufwand {eur(p['stunde'])}/h",
        f"- Winterdienst (Option Saisonpauschale, alle Einsätze inkl.): {eur(p['wd_grund'])} je Objekt + {eur(p['wd_lfm'])} je lfd. Meter; "
        f"Einzeleinsatz ohne Vertrag {eur(p['wd_einzeleinsatz'])}",
        f"- Gartenpflege: {eur(p['ga_gang'])} je Einsatz + Rasen {eur(p['ga_rasen_qm'])}/m²/Mahd, Beet {eur(p['ga_beet_qm'])}/m², "
        f"Hecke bis {hoehe} m Höhe {eur(p['ga_hecke_lfm'])}/m je Schnitt, höhere Hecken nach Aufwand ({eur(p['stunde'])}/h + "
        f"{eur(pl['hecke']['entsorgung_cent'])} Entsorgung je Schnitt), Laub {eur(p['ga_laub_qm'])}/m², Grünschnitt {eur(p['ga_entsorgung_qm'])}/m²/Jahr",
        f"- Mülltonnen-Service: {eur(p['mu_termin'])} je Abfuhrtermin + {eur(p['mu_leerung'])} je Leerung; Müllplatz kehren {eur(p['mu_platz_woche'])}/Woche",
        f"- Objektkontrolle mit Fotoprotokoll als eigener Termin: {eur(p['kontrolle'])}; Sichtkontrolle bei jedem Einsatz inklusive",
        ENDE,
    ]
    return "\n".join(zeilen)


def profil_neu(pl: dict, text: str) -> str:
    neu = profil_abschnitt(pl)
    if START in text:
        return re.sub(re.escape(START) + r".*?" + re.escape(ENDE), lambda _: neu, text, flags=re.S)
    # Erstmalig: alten Abschnitt „## Preise …“ bis zu den manuell gepflegten [OFFEN]-Zeilen ersetzen
    m = re.search(r"^## Preise.*?(?=^- Kein Treuerabatt)", text, flags=re.S | re.M)
    if not m:
        raise SystemExit("Preisabschnitt in firma/profil.md nicht gefunden")
    return text[:m.start()] + neu + "\n" + text[m.end():]


def webseite_passt(pl: dict) -> list[str]:
    fehler = []
    index = (REPO / "webseite" / "public" / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<script id="hh-preise" type="application/json">(.*?)</script>', index, flags=re.S)
    if not m:
        return ["webseite/public/index.html enthält keine Preisliste (build.py ausführen)"]
    js = json.loads(m.group(1))
    p = pl["preise"]
    soll = {"th_grund": p["th_grund"], "th_etage": p["th_etage"], "mu_termin": p["mu_termin"], "mu_leerung": p["mu_leerung"],
            "wd": pl["winterdienst_staffel"], "wd_grund": p["wd_grund"], "wd_lfm": p["wd_lfm"]}
    for k, v in soll.items():
        if js.get(k) != v:
            fehler.append(f"Webseite: {k} = {js.get(k)} statt {v} – webseite/build.py ausführen")
    seite = (REPO / "webseite" / "public" / "winterdienst-guetersloh.html").read_text(encoding="utf-8")
    if eur(pl["winterdienst_staffel"]["bereitstellung"]) not in seite:
        fehler.append("Webseite: Winterdienst-Seite zeigt nicht die aktuelle Bereitstellungspauschale")
    return fehler


def veraltete_stellen(pl: dict) -> list[str]:
    funde = []
    muster = [re.compile(x) for x in pl.get("veraltete_preise", [])]
    ausnahmen = {REPO / a for a in pl.get("veraltet_ausnahmen", [])}
    if not muster:
        return funde
    for datei in REPO.rglob("*"):
        if datei in ausnahmen or datei.suffix not in {".md", ".json", ".html", ".js", ".csv"} or any(t in datei.parts for t in (".git", "anfragen", "berichte", "node_modules")):
            continue
        try:
            text = datei.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for mu in muster:
            if mu.search(text):
                funde.append(f"{datei.relative_to(REPO)}: „{mu.search(text).group(0)}“")
    return funde


def main(argv: list[str]) -> int:
    pl = json.loads(LISTE.read_text(encoding="utf-8"))
    if "--schreiben" in argv:
        PROFIL.write_text(profil_neu(pl, PROFIL.read_text(encoding="utf-8")), encoding="utf-8")
        subprocess.run([sys.executable, str(REPO / "webseite" / "build.py")], check=True)
        print("Profil und Webseite aus der Preisliste erzeugt. Webseite geht erst nach Freigabe live.")
    fehler = []
    profil = PROFIL.read_text(encoding="utf-8")
    if profil_neu(pl, profil) != profil:
        fehler.append("firma/profil.md: Preisabschnitt weicht von der Preisliste ab – werkzeuge/preise.py --schreiben")
    fehler += webseite_passt(pl)
    for f in fehler:
        print("FEHLER", f)
    for w in veraltete_stellen(pl):
        print("WARNUNG veralteter Preis:", w)
    if not fehler:
        print("Preise stimmen überein (Portal, Angebote, Webseite, Firmenprofil).")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
