#!/usr/bin/env python3
"""Prüft eine Lied- oder Short-Datei VOR dem Rendern auf typische Fehler.

    python3 generator/pruefen.py songs/07_xyz.json
    python3 generator/pruefen.py shorts/04_xyz.json

Gibt Warnungen (⚠) und Fehler (✘) aus. Exit-Code 1 bei Fehlern.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bilder as BI   # noqa: E402
import grafik as G    # noqa: E402
import musik as M     # noqa: E402

BEKANNTE_BILDER = set(BI.ZEICHNER) | {"sonne", "leer"}
EFFEKTE = {"plopp", "boing", "piep", "tatue", "glitzer", "schrubb", "klingel", "summ", "platsch", "blubb",
           "quak", "gaehn", "tick", "tada", "wusch"}


def pruefe_lied(cfg):
    fehler, warn = [], []
    for k in ("titel", "kurztitel", "figur", "teile", "ablauf", "beschreibung", "tags"):
        if k not in cfg:
            fehler.append(f"Feld fehlt: {k}")
    if cfg.get("figur", {}).get("typ") not in G.FIGUREN:
        fehler.append(f"Unbekannte Figur: {cfg.get('figur')}")
    if cfg.get("melodie", "A") not in M.MELODIEN:
        fehler.append(f"Unbekannte Melodie: {cfg.get('melodie')} (vorhanden: {', '.join(M.MELODIEN)})")
    for name in cfg.get("ablauf", []):
        if isinstance(name, str) and name not in cfg.get("teile", {}):
            fehler.append(f"Ablauf nennt unbekannten Teil: {name}")
        if isinstance(name, dict) and len(name.get("sprich", "")) > 160:
            warn.append(f"Sprechtext sehr lang ({len(name['sprich'])} Zeichen): {name['sprich'][:40]}…")
    for tname, teil in cfg.get("teile", {}).items():
        for i, mel in enumerate(teil.get("melodie", [])):
            if mel and isinstance(mel[0], (list, tuple)) and sum(x[1] for x in mel) != 16:
                fehler.append(f"{tname}: Melodie Zeile {i + 1} hat {sum(x[1] for x in mel)} statt 16 Achtel")
        if len(teil.get("zeilen", [])) != 4 and not cfg.get("herkunft"):
            warn.append(f"{tname}: {len(teil.get('zeilen', []))} Zeilen (empfohlen: 4)")
        for b in [teil.get("bild")] + [z.get("bild") for z in teil["zeilen"] if isinstance(z, dict)]:
            if b and b not in BEKANNTE_BILDER:
                fehler.append(f"{tname}: Bild '{b}' gibt es nicht (erst in bilder.py zeichnen)")
        for z in teil["zeilen"]:
            text = M._zeilentext(z)
            n = len(M.zeile_zu_silben(text)[0])
            if n > 15:
                fehler.append(f"{tname}: {n} Silben – zu lang: „{text}“")
            elif n not in (6, 7, 8) and not cfg.get("herkunft"):
                warn.append(f"{tname}: {n} Silben (ideal 7): „{text}“")
            eff = z.get("effekt") if isinstance(z, dict) else None
            typ = eff.get("typ") if isinstance(eff, dict) else eff
            if typ and typ not in EFFEKTE:
                fehler.append(f"{tname}: unbekannter Effekt '{typ}'")
    if not cfg.get("suchbegriffe"):
        warn.append("Keine \"suchbegriffe\" – für mehr Reichweite 3–6 Suchbegriffe eintragen")
    if not fehler:
        lied = M.Lied(cfg)
        print(f"  Länge: {int(lied.dauer // 60)}:{int(lied.dauer % 60):02d} min")
        if lied.dauer > 240:
            warn.append("Länger als 4 Minuten – für Kleinkinder eher kürzen")
    return fehler, warn


def pruefe_short(cfg):
    fehler, warn = [], []
    for d in cfg.get("dinge", []):
        b = d.get("bild", "")
        if not (b in BEKANNTE_BILDER or (b.startswith("figur:") and b.split(":")[1] in G.FIGUREN)):
            fehler.append(f"Bild '{b}' gibt es nicht")
        if d.get("anzahl") and not (1 <= int(d["anzahl"]) <= 9 and b in BI.ZEICHNER):
            fehler.append(f"Zählrätsel '{b}': Anzahl 1–9 und ein gezeichnetes Bild nötig")
        if d.get("geraeusch") and d["geraeusch"] not in EFFEKTE:
            fehler.append(f"Unbekanntes Geräusch '{d['geraeusch']}'")
    if not 3 <= len(cfg.get("dinge", [])) <= 5:
        warn.append(f"{len(cfg.get('dinge', []))} Rätsel (empfohlen 4–5)")
    if not fehler:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import short as S
        d = S.planen(cfg)["dauer"]
        print(f"  Länge: {d:.0f} s")
        if d > 59:
            fehler.append("Länger als 59 Sekunden – kein Short mehr, bitte ein Rätsel weniger")
    return fehler, warn


def main():
    gesamt = 0
    for p in sys.argv[1:]:
        cfg = json.loads(Path(p).read_text())
        print(f"▶ {p}")
        f, w = pruefe_short(cfg) if "dinge" in cfg else pruefe_lied(cfg)
        for x in w:
            print(f"  ⚠ {x}")
        for x in f:
            print(f"  ✘ {x}")
        if not f:
            print("  ✔ in Ordnung")
        gesamt += len(f)
    sys.exit(1 if gesamt else 0)


if __name__ == "__main__":
    main()
