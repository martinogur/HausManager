#!/usr/bin/env python3
"""Erstellt Profilbild, Kanalbanner und Wasserzeichen für den YouTube-Kanal (aus kanal.json)."""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grafik as G  # noqa: E402

BASIS = Path(__file__).resolve().parent.parent
ZIEL = BASIS / "kanal"


def figuren(groesse):
    return [G.Figur(t).sprite(groesse, mund=m, arm=a, fluegel=1.0).resize((groesse, groesse), Image.LANCZOS)
            for t, m, a in (("hase", 0.5, 0.7), ("biene", 0.0, 0.6), ("baer", 0.6, 0.9))]


def logo_text(name, hoehe, akzent="#e5398f"):
    return G.text_sprite(name, hoehe, G.rgb("#ffffff"), rand=G.rgb(akzent), randbreite=int(hoehe * 0.14))


def profilbild(name, pfad):
    S = 800
    bg = G.hintergrund(S, S, G.PALETTEN[0])
    s = G.sonne(int(S * 0.07))
    bg.paste(s, (int(S * 0.68), int(S * 0.08)), s)
    for spr, x, y in ((G.wolke(220), 60, 90), (G.wolke(160), 420, 190)):
        bg.paste(spr, (x, y), spr)
    hase, biene, baer = figuren(int(S * 0.5))
    bg.paste(hase, (int(S * 0.0), int(S * 0.38)), hase)
    bg.paste(baer, (int(S * 0.5), int(S * 0.4)), baer)
    b2 = biene.resize((int(S * 0.36), int(S * 0.36)), Image.LANCZOS)
    bg.paste(b2, (int(S * 0.32), int(S * 0.14)), b2)
    t = logo_text(name, S * 0.15)
    if t.width > S * 0.76:
        f = S * 0.76 / t.width
        t = t.resize((int(t.width * f), int(t.height * f)), Image.LANCZOS)
    bg.paste(t, ((S - t.width) // 2, int(S * 0.73)), t)
    bg.save(pfad)


def banner(name, slogan, pfad):
    W, H = 2560, 1440
    bg = G.hintergrund(W, H, G.PALETTEN[0])
    # sicherer Bereich (überall sichtbar): 1546 x 423 in der Mitte
    sx0, sy0 = (W - 1546) // 2, (H - 423) // 2
    s = G.sonne(110)
    bg.paste(s, (int(W * 0.8), int(H * 0.08)), s)
    for x, y, b in ((150, 140, 420), (900, 90, 360), (1650, 200, 300), (2150, 420, 380)):
        w = G.wolke(b)
        bg.paste(w, (x, y), w)
    farben = ["#e53935", "#fbc02d", "#8e24aa", "#1e88e5", "#ff7043", "#ec407a"]
    for i in range(22):
        bl = G.blume(70, farben[i % len(farben)])
        bg.paste(bl, (40 + i * 118, int(H * 0.86) + (i % 2) * 30), bl)
    hase, biene, baer = figuren(380)
    bg.paste(hase, (sx0 - 60, sy0 + 10), hase)
    bg.paste(baer, (sx0 + 1546 - 320, sy0 + 20), baer)
    b2 = biene.resize((240, 240), Image.LANCZOS)
    bg.paste(b2, (sx0 + 1546 - 300, sy0 - 150), b2)
    t = logo_text(name, 175)
    sl = G.text_sprite(slogan, 52, (90, 70, 110, 255), rand=(255, 255, 255, 255), randbreite=8)
    y = sy0 + (423 - t.height - sl.height) // 2
    bg.paste(t, ((W - t.width) // 2, y), t)
    bg.paste(sl, ((W - sl.width) // 2, y + t.height + 5), sl)
    bg.save(pfad)


def wasserzeichen(name, pfad):
    S = 300
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([6, 6, S - 6, S - 6], fill=(255, 255, 255, 255), outline=G.rgb("#e5398f"), width=14)
    b = G.Figur("biene").sprite(int(S * 0.62), mund=0.4, fluegel=1).resize((int(S * 0.62),) * 2, Image.LANCZOS)
    img.alpha_composite(b, (int(S * 0.19), int(S * 0.06)))
    t = G.text_sprite("ABO", S * 0.17, G.rgb("#ffffff"), rand=G.rgb("#e5398f"), randbreite=8)
    img.alpha_composite(t, ((S - t.width) // 2, int(S * 0.66)))
    img.save(pfad)


def main():
    cfg = json.loads((BASIS / "kanal.json").read_text())
    ZIEL.mkdir(exist_ok=True)
    name = cfg["kanalname"]
    profilbild(name, ZIEL / "profilbild.png")
    banner(name, cfg.get("slogan", ""), ZIEL / "banner.png")
    wasserzeichen(name, ZIEL / "wasserzeichen.png")
    print("Kanalgrafiken erstellt in", ZIEL)


if __name__ == "__main__":
    main()
