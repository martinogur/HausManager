#!/usr/bin/env python3
"""Sammelvideo („Mix“): hängt fertige Lied-Videos zu einem langen Video mit Kapitelmarken aneinander.

    python3 generator/sammelvideo.py ausgabe/archiv/*.mp4 --titel "…"          # bestimmte Videos
    python3 generator/sammelvideo.py --ordner ausgabe/archiv --minuten 30        # neueste bis ~30 Minuten

Jedes Eingangsvideo braucht daneben <name>.json (meta.json des Liedes) oder einen Ordner <name>/ mit meta.json.
Nur Videos mit gleicher Auflösung werden verbunden (ohne Neukodierung, daher schnell und ohne Qualitätsverlust).
Ergebnis: ausgabe/sammlung/<datum>/video.mp4, vorschaubild.png, meta.json, beschreibung.txt
"""
import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grafik as G         # noqa: E402
import youtube_meta as YM  # noqa: E402

BASIS = Path(__file__).resolve().parent.parent


def _probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(video)],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    s = d["streams"][0]
    return (s["width"], s["height"], s["r_frame_rate"]), float(d["format"]["duration"])


def _meta(video):
    video = Path(video)
    for p in (video.with_suffix(".json"), video.parent / "meta.json"):
        if p.exists():
            return json.loads(p.read_text())
    return {"titel": video.stem}


def _name(meta):
    t = meta.get("titel", "")
    for trenner in (" 🎵", " |", " – "):
        t = t.split(trenner)[0]
    return t.strip()


def vorschaubild(bilder, text, pfad):
    W, H = 1280, 720
    bg = Image.new("RGB", (W, H), (255, 214, 64))
    for i in range(4):  # 2x2-Raster, bei weniger Liedern wiederholt
        img = Image.open(bilder[i % len(bilder)]).convert("RGB").resize((W // 2, H // 2))
        bg.paste(img, ((i % 2) * W // 2, (i // 2) * H // 2))
    tx = G.text_sprite(text, H * 0.2, G.rgb("#ffffff"), rand=G.rgb("#e53935"), randbreite=int(H * 0.025))
    bg = bg.convert("RGBA")
    lage = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(lage).rounded_rectangle([(W - tx.width) / 2 - 40, (H - tx.height) / 2 - 25,
                                            (W + tx.width) / 2 + 40, (H + tx.height) / 2 + 25],
                                           radius=40, fill=(255, 255, 255, 150))
    bg.alpha_composite(lage)
    bg.alpha_composite(tx, ((W - tx.width) // 2, (H - tx.height) // 2))
    bg.convert("RGB").save(pfad)


def erstellen(videos, titel=None, ziel=None):
    kanal_cfg = json.loads((BASIS / "kanal.json").read_text())
    if not videos:
        raise SystemExit("Keine Videos angegeben")
    format0, _ = _probe(videos[0])
    teile, kapitel, t = [], [], 0.0
    for v in videos:
        fmt, dauer = _probe(v)
        if fmt != format0:
            print(f"  ⚠ übersprungen (anderes Format {fmt}): {v}")
            continue
        teile.append(Path(v).resolve())
        kapitel.append((t, _name(_meta(v))))
        t += dauer
    if len(teile) < 3:
        raise SystemExit("Für Kapitelmarken braucht ein Sammelvideo mindestens 3 Lieder")
    minuten = round(t / 60)
    titel = titel or f"Kinderlieder zum Mitsingen 🎵 {minuten} Minuten Mix | {kanal_cfg.get('kanalname', '')}"
    ziel = Path(ziel or BASIS / "ausgabe" / "sammlung" / datetime.date.today().isoformat())
    ziel.mkdir(parents=True, exist_ok=True)
    liste = ziel / "liste.txt"
    liste.write_text("".join(f"file '{p}'\n" for p in teile))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(liste), "-c", "copy",
                    "-movflags", "+faststart", str(ziel / "video.mp4")], check=True)
    liste.unlink()
    bilder = [p for p in (Path(v).with_suffix(".png") for v in teile) if p.exists()]
    bilder += [p for p in (Path(v).parent / "vorschaubild.png" for v in teile) if p.exists() and p not in bilder]
    if bilder:
        vorschaubild(bilder, f"{minuten} MIN", ziel / "vorschaubild.png")
    YM.schreiben(YM.sammel_meta(titel, kapitel, kanal_cfg, t), ziel)
    print(f"  ✔ Sammelvideo: {len(teile)} Lieder, {minuten} min → {ziel}")
    return ziel


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="*")
    ap.add_argument("--ordner", help="Ordner mit <name>.mp4 (+ <name>.json, <name>.png), neueste zuerst")
    ap.add_argument("--minuten", type=float, default=30)
    ap.add_argument("--titel")
    ap.add_argument("--ziel")
    a = ap.parse_args()
    videos = a.videos
    if a.ordner:
        alle = sorted(Path(a.ordner).glob("*.mp4"), key=lambda p: p.name, reverse=True)
        videos, summe = [], 0.0
        for v in alle:
            if summe >= a.minuten * 60:
                break
            videos.append(v)
            summe += _probe(v)[1]
        videos.reverse()
    erstellen(videos, a.titel, a.ziel)


if __name__ == "__main__":
    main()
