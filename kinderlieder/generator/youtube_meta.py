"""YouTube-Metadaten (Titel, Beschreibung, Tags) für Lieder und Shorts.

Wird von erstellen.py / short.py als meta.json und beschreibung.txt neben das Video gelegt
und vom Upload-Skript (youtube_upload.py) verwendet.
"""
import json
from pathlib import Path


def _zeilentext(z):
    return z["text"] if isinstance(z, dict) else z


def lied_meta(cfg, kanal_cfg, dauer_s):
    titel = f"{cfg['titel']} | Kinderlied zum Mitsingen"
    if len(titel) > 100:
        titel = cfg["titel"][:100]
    zeilen = []
    for name in cfg["ablauf"]:
        if isinstance(name, dict):
            continue
        teil = cfg["teile"][name]
        zeilen.append("Refrain:" if teil.get("art") == "refrain" else "Strophe:")
        zeilen += [_zeilentext(z) for z in teil["zeilen"]]
        zeilen.append("")
    tags = cfg.get("tags", [])
    kanal = kanal_cfg.get("kanalname", "")
    beschreibung = "\n".join([
        cfg.get("beschreibung", ""),
        "",
        "🎵 Liedtext zum Mitsingen:",
        "",
        *zeilen,
        f"🌼 Mehr Lieder zum Mitsingen, Mitzählen und Mitmachen gibt es auf der {kanal}!" if kanal else "",
        "",
        kanal_cfg.get("hinweis_ki", ""),
        "",
        " ".join("#" + t.replace(" ", "") for t in tags[:3]),
    ]).strip()
    return {"titel": titel, "beschreibung": beschreibung[:4900], "tags": tags, "kategorie": "27",
            "fuer_kinder": True, "ki_inhalt": True, "art": "lied", "dauer_s": round(dauer_s, 1)}


def short_meta(cfg, kanal_cfg, dauer_s):
    titel = cfg["titel"]
    if "#shorts" not in titel.lower():
        titel = f"{titel} #shorts"
    tags = cfg.get("tags", [])
    beschreibung = "\n".join([
        cfg.get("beschreibung", ""),
        "",
        kanal_cfg.get("hinweis_ki", ""),
        "",
        "#shorts #kinder #ratespiel",
    ]).strip()
    return {"titel": titel[:100], "beschreibung": beschreibung, "tags": tags, "kategorie": "27",
            "fuer_kinder": True, "ki_inhalt": True, "art": "short", "dauer_s": round(dauer_s, 1)}


def schreiben(meta, ordner):
    ordner = Path(ordner)
    (ordner / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    lang = f"{int(meta['dauer_s'] // 60)}:{int(meta['dauer_s'] % 60):02d} min"
    (ordner / "beschreibung.txt").write_text(
        f"TITEL\n{meta['titel']}\n\nBESCHREIBUNG\n{meta['beschreibung']}\n\n"
        f"TAGS\n{', '.join(meta['tags'])}\n\n"
        "EINSTELLUNGEN\n"
        "- Zielgruppe: Ja, speziell für Kinder (Made for Kids)\n"
        "- Veränderte oder synthetische Inhalte: Ja\n"
        "- Kategorie: Bildung\n"
        f"- Länge: {lang}\n")
