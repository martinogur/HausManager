"""YouTube-Metadaten (Titel, Beschreibung, Tags) für Lieder, Shorts, Refrain-Shorts und Sammelvideos.

Auf Reichweite ausgelegt:
- Titel beginnen mit dem Begriff, nach dem Eltern suchen (bei Klassikern der Liedname), danach der Nutzen
  („zum Mitsingen“, „mit Text“) und erst am Ende der Kanalname. Unter 70 Zeichen bleibt der Titel überall ganz lesbar.
- Die ersten zwei Zeilen der Beschreibung (in der Suche sichtbar) enthalten die wichtigsten Suchbegriffe.
- Liedtext in der Beschreibung (wird von YouTube durchsucht), Kapitelmarken bei Sammelvideos.
- Herkunft: Klassiker werden als traditionell/gemeinfrei gekennzeichnet, eigene Lieder als eigene Werke.
Wird von erstellen.py / short.py / refrain_short.py / sammelvideo.py als meta.json und beschreibung.txt
neben das Video gelegt und vom Upload-Skript (youtube_upload.py) verwendet.
"""
import json
from pathlib import Path

STANDARD_TAGS = ["Kinderlieder", "Kinderlied", "Kinderlieder zum Mitsingen", "Lieder für Kinder",
                 "Kleinkinder", "Kita", "Liederwiese"]


def _zeilentext(z):
    return z["text"] if isinstance(z, dict) else z


def _hashtags(tags):
    return " ".join("#" + t.replace(" ", "").replace("-", "").replace("'", "") for t in tags[:3])


def _herkunft(cfg, kanal_cfg):
    if cfg.get("herkunft"):
        return (f"Traditionelles Kinderlied, gemeinfrei ({cfg['herkunft']}). Arrangement, Gesang und Animation: "
                f"{kanal_cfg.get('kanalname', 'Liederwiese')}, erstellt mit KI-Unterstützung.")
    return kanal_cfg.get("hinweis_ki", "")


def _tags(cfg, extra=()):
    tags = list(dict.fromkeys(list(cfg.get("suchbegriffe", [])) + list(cfg.get("tags", [])) + list(extra)
                              + STANDARD_TAGS))
    # YouTube erlaubt insgesamt 500 Zeichen
    aus, laenge = [], 0
    for t in tags:
        if laenge + len(t) + 2 > 480:
            break
        aus.append(t)
        laenge += len(t) + 2
    return aus


def lied_titel(cfg, kanal_cfg):
    kanal = kanal_cfg.get("kanalname", "Liederwiese")
    if cfg.get("herkunft"):
        name = cfg.get("kurztitel", cfg["titel"])
        kandidaten = [f"{name} 🎵 Kinderlied zum Mitsingen mit Text | {kanal}",
                      f"{name} 🎵 Kinderlied zum Mitsingen | {kanal}", f"{name} | Kinderlied | {kanal}"]
    else:
        kandidaten = [f"{cfg['titel']} | Kinderlied zum Mitsingen", f"{cfg['titel']} | Kinderlied",
                      cfg["titel"]]
    return next((k for k in kandidaten if len(k) <= 100), cfg["titel"][:100])


def lied_meta(cfg, kanal_cfg, dauer_s):
    zeilen = []
    for name in cfg["ablauf"]:
        if isinstance(name, dict):
            continue
        teil = cfg["teile"][name]
        zeilen.append("Refrain:" if teil.get("art") == "refrain" else "Strophe:")
        zeilen += [_zeilentext(z) for z in teil["zeilen"]]
        zeilen.append("")
    tags = _tags(cfg)
    kanal = kanal_cfg.get("kanalname", "")
    beschreibung = "\n".join([
        cfg.get("beschreibung", ""),
        "",
        "🎵 Liedtext zum Mitsingen:",
        "",
        *zeilen,
        f"🌼 Jede Woche neue Kinderlieder zum Mitsingen, Mitzählen und Mitmachen auf der {kanal}!" if kanal else "",
        "",
        _herkunft(cfg, kanal_cfg),
        "",
        _hashtags(tags),
    ]).strip()
    return {"titel": lied_titel(cfg, kanal_cfg), "beschreibung": beschreibung[:4900], "tags": tags,
            "kategorie": "27", "fuer_kinder": True, "ki_inhalt": True, "art": "lied", "dauer_s": round(dauer_s, 1)}


def short_meta(cfg, kanal_cfg, dauer_s):
    titel = cfg["titel"]
    if "#shorts" not in titel.lower():
        titel = f"{titel} #shorts"
    tags = _tags(cfg, ["Ratespiel für Kinder", "Shorts"])
    beschreibung = "\n".join([
        cfg.get("beschreibung", ""),
        "",
        kanal_cfg.get("hinweis_ki", ""),
        "",
        "#shorts #kinder #ratespiel",
    ]).strip()
    return {"titel": titel[:100], "beschreibung": beschreibung, "tags": tags, "kategorie": "27",
            "fuer_kinder": True, "ki_inhalt": True, "art": "short", "dauer_s": round(dauer_s, 1)}


def refrain_short_meta(cfg, kanal_cfg, dauer_s, lied_url=""):
    name = cfg.get("kurztitel", cfg["titel"])
    titel = f"{name} 🎵 Sing mit! #shorts"
    tags = _tags(cfg, ["Shorts", "Kinderlied Refrain"])
    beschreibung = "\n".join([
        f"{name} – der Refrain zum Mitsingen!",
        f"▶ Das ganze Lied: {lied_url}" if lied_url else "▶ Das ganze Lied findest du auf unserem Kanal.",
        "",
        _herkunft(cfg, kanal_cfg),
        "",
        "#shorts " + _hashtags(tags),
    ]).strip()
    return {"titel": titel[:100], "beschreibung": beschreibung, "tags": tags, "kategorie": "27",
            "fuer_kinder": True, "ki_inhalt": True, "art": "short", "dauer_s": round(dauer_s, 1)}


def _zeit(s):
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def sammel_meta(titel, kapitel, kanal_cfg, dauer_s, tags=()):
    """kapitel: [(start_s, Liedname)] – ergibt YouTube-Kapitel (erstes bei 0:00, mind. 3, je ≥ 10 s)."""
    kanal = kanal_cfg.get("kanalname", "Liederwiese")
    tags = _tags({"tags": list(tags)}, ["Kinderlieder Mix", "Kinderlieder zum Mitsingen Mix",
                                        "Kinderlieder deutsch", "Kinderlieder Sammlung"])
    beschreibung = "\n".join([
        f"{len(kapitel)} Kinderlieder zum Mitsingen am Stück – {max(1, round(dauer_s / 60))} Minuten Musik für Kinder "
        f"ab 2 Jahren mit Bella Biene, Bruno Bär und Hopsi Hase.",
        "",
        "🎵 Alle Lieder:",
        *[f"{_zeit(t)} {n}" for t, n in kapitel],
        "",
        f"🌼 Jede Woche neue Kinderlieder auf der {kanal}!",
        "",
        "Traditionelle Lieder sind gemeinfrei; Arrangement, Gesang und Animation: "
        f"{kanal}, erstellt mit KI-Unterstützung.",
        "",
        "#Kinderlieder #Kinderliedermix #Mitsingen",
    ]).strip()
    return {"titel": titel[:100], "beschreibung": beschreibung[:4900], "tags": tags, "kategorie": "27",
            "fuer_kinder": True, "ki_inhalt": True, "art": "sammlung", "dauer_s": round(dauer_s, 1)}


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
