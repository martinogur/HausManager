"""Grafik-Teil: Figuren, Hintergrund und Karaoke-Text – alles mit Pillow gezeichnet."""
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SCHRIFT = str(ASSETS / "Quicksand-Bold.ttf")

FIGUREN = {
    "baer":  {"koerper": "#b07a4f", "hell": "#ecc9a2", "linie": "#4a2f1d", "innen": "#ecc9a2"},
    "katze": {"koerper": "#f2a65a", "hell": "#fde3c4", "linie": "#6b3a12", "innen": "#f7b6c8"},
    "hase":  {"koerper": "#e9e2f2", "hell": "#ffffff", "linie": "#5a4a6b", "innen": "#f7b6c8"},
    "biene": {"koerper": "#ffd23f", "hell": "#fff1a8", "linie": "#3b2f2f", "innen": "#3b2f2f"},
    "frosch": {"koerper": "#7cc96b", "hell": "#d8f5c6", "linie": "#2f5a26", "innen": "#d8f5c6"},
}

PALETTEN = [  # Himmel oben, Himmel unten, Hügel hinten, Hügel vorne
    ("#79c4f2", "#dff3ff", "#93d46c", "#62b94b"),
    ("#ffb08a", "#fff0cf", "#9ad46f", "#6bbf4f"),
    ("#b7a5f4", "#f1ebff", "#86cf7a", "#56b366"),
    ("#74ddcc", "#e6fff9", "#a8da6c", "#78c04c"),
    ("#f7a8c8", "#fff0f6", "#8fd47a", "#5fba55"),
]


def rgb(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mischen(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def schrift(groesse):
    return ImageFont.truetype(SCHRIFT, int(groesse))


def ellipse_poly(cx, cy, rx, ry, winkel=0.0, n=48):
    c, s = math.cos(math.radians(winkel)), math.sin(math.radians(winkel))
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + x * c - y * s, cy + x * s + y * c))
    return pts


def band_poly(cx, cy, rx, ry, y1, y2, n=16):
    """Fläche einer Ellipse zwischen y1 und y2 (für Bienenstreifen)."""
    y1, y2 = max(y1, cy - ry + 0.01), min(y2, cy + ry - 0.01)
    ys = [y1 + (y2 - y1) * i / n for i in range(n + 1)]
    links = [(cx - rx * math.sqrt(max(0, 1 - ((y - cy) / ry) ** 2)), y) for y in ys]
    rechts = [(cx + rx * math.sqrt(max(0, 1 - ((y - cy) / ry) ** 2)), y) for y in reversed(ys)]
    return links + rechts


# --------------------------------------------------------------------------
# Figuren
# --------------------------------------------------------------------------

class Figur:
    """Zeichnet eine Figur in einem 120x120-Einheiten-Raster (2x überabgetastet)."""

    def __init__(self, typ, farbe=None):
        self.typ = typ if typ in FIGUREN else "baer"
        f = dict(FIGUREN[self.typ])
        if farbe:
            f["koerper"] = farbe
        self.f = {k: rgb(v) for k, v in f.items()}

    def sprite(self, groesse, mund=0.0, blinzeln=False, arm=0.0, ohr=0.0, fluegel=1.0, blick=0.0):
        S = groesse * 2
        u = S / 120.0
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        lw = max(2, int(1.1 * u))
        F = self.f

        def P(x, y):
            return ((x + 10) * u, (y + 15) * u)

        def ell(cx, cy, rx, ry, fill, outline=True, winkel=0.0):
            pts = [P(x, y) for x, y in ellipse_poly(cx, cy, rx, ry, winkel)]
            d.polygon(pts, fill=fill, outline=F["linie"] if outline else None,
                      width=lw if outline else 0)

        typ = self.typ
        # --- hinter dem Körper ---
        if typ == "biene":
            fl = (0.55 + 0.45 * fluegel)
            for sx in (-1, 1):
                ell(50 + sx * 22, 54, 15, 11 * fl, (210, 240, 255, 190), winkel=sx * -25)
        if typ == "hase":
            for sx in (-1, 1):
                w = sx * (8 + ohr * 6)
                ell(50 + sx * 12, 2, 7, 19, F["koerper"], winkel=w)
                ell(50 + sx * 12, 4, 3.5, 13, F["innen"], outline=False, winkel=w)
        # Arme
        if typ != "frosch":
            for sx in (-1, 1):
                ell(50 + sx * 23, 70, 5.5, 11, F["koerper"], winkel=sx * (35 + arm * 40))
        # Füße
        if typ != "biene":
            for sx in (-1, 1):
                ell(50 + sx * 12, 93, 9, 5, F["koerper"])
        # Körper
        ell(50, 74, 22, 19, F["koerper"])
        if typ == "biene":
            for y1 in (66, 77):
                d.polygon([P(x, y) for x, y in band_poly(50, 74, 22, 19, y1, y1 + 5)], fill=F["innen"])
            ell(50, 74, 22, 19, None)
        else:
            ell(50, 77, 13, 12, F["hell"], outline=False)
        # Ohren (vor dem Kopf gezeichnet = dahinter)
        if typ == "baer":
            for sx in (-1, 1):
                ell(50 + sx * 21, 18, 9, 9, F["koerper"])
                ell(50 + sx * 21, 18, 5, 5, F["innen"], outline=False)
        elif typ == "katze":
            for sx in (-1, 1):
                pts = [P(50 + sx * 26, 30), P(50 + sx * 21, 5), P(50 + sx * 7, 18)]
                d.polygon(pts, fill=F["koerper"], outline=F["linie"], width=lw)
                pts = [P(50 + sx * 23, 25), P(50 + sx * 20.5, 11), P(50 + sx * 12, 19)]
                d.polygon(pts, fill=F["innen"])
        elif typ == "biene":
            for sx in (-1, 1):
                d.line([P(50 + sx * 9, 18), P(50 + sx * 16, 2 + ohr * 2)], fill=F["linie"], width=lw)
                ell(50 + sx * 16, 2 + ohr * 2, 3.2, 3.2, F["linie"], outline=False)
        # Kopf
        if typ == "frosch":
            for sx in (-1, 1):
                ell(50 + sx * 13, 18, 10, 10, F["koerper"])
        ell(50, 40, 28, 24, F["koerper"])
        # Schnauze
        if typ == "baer":
            ell(50, 50, 10, 7.5, F["hell"], outline=False)
        # Augen
        ey = 18 if typ == "frosch" else 37
        for sx in (-1, 1):
            ex = 50 + sx * (13 if typ == "frosch" else 10)
            if blinzeln:
                d.arc([P(ex - 5, ey - 3), P(ex + 5, ey + 4)], 200, 340, fill=F["linie"], width=lw + 1)
            else:
                ell(ex, ey, 5.5, 6.5, (255, 255, 255, 255), outline=False)
                ell(ex + blick, ey + 1, 3.6, 4.2, (35, 30, 40, 255), outline=False)
                ell(ex + blick - 1.2, ey - 1, 1.3, 1.5, (255, 255, 255, 255), outline=False)
        # Bäckchen
        # (deckend gemischt, damit der Hintergrund nicht durchscheint)
        backe = mischen(F["koerper"], (255, 120, 150, 255), 0.5)
        for sx in (-1, 1):
            ell(50 + sx * 18, 47, 5, 3, backe, outline=False)
        # Nase
        if typ == "baer":
            ell(50, 46.5, 3.6, 2.6, F["linie"], outline=False)
        elif typ in ("katze", "hase"):
            d.polygon([P(47.5, 45), P(52.5, 45), P(50, 48)], fill=(240, 120, 150, 255))
            if typ == "katze":
                for sx in (-1, 1):
                    for dy in (-1.5, 1.5):
                        d.line([P(50 + sx * 7, 48 + dy), P(50 + sx * 19, 47 + dy * 2.2)],
                               fill=F["linie"], width=max(1, lw // 2))
        # Mund
        my = 53 if typ != "frosch" else 48
        breite = 12 if typ == "frosch" else 7
        if mund > 0.12:
            # lachender, offener Mund („D“-Form): Oberkante als leichtes Lächeln, unten rund, mit Zunge
            w = (breite - 1.5) + 2.5 * mund
            h = 2.5 + 6.5 * mund
            oben = [(50 + w * math.cos(math.pi * k / 12), my - 0.5 + 1.6 * math.sin(math.pi * k / 12))
                    for k in range(13)]
            unten = [(50 - w * math.cos(math.pi * k / 16), my + h * math.sin(math.pi * k / 16))
                     for k in range(1, 16)]
            umriss = [P(x, y) for x, y in oben + unten]
            maske = Image.new("L", img.size, 0)
            ImageDraw.Draw(maske).polygon(umriss, fill=255)
            mund_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
            md = ImageDraw.Draw(mund_img)
            md.polygon(umriss, fill=(122, 31, 43, 255))
            zx, zy = 50, my + h * 0.95
            md.ellipse([P(zx - w * 0.6, zy - h * 0.45), P(zx + w * 0.6, zy + h * 0.35)], fill=(240, 120, 140, 255))
            md.rectangle([P(50 - w, my - 1), P(50 + w, my + 0.9 + 0.6 * mund)], fill=(255, 255, 255, 255))
            mund_img.putalpha(Image.composite(mund_img.getchannel("A"), Image.new("L", img.size, 0), maske))
            img.alpha_composite(mund_img)
            d.polygon(umriss, outline=F["linie"], width=lw)
            # nach oben gezogene Mundwinkel
            for sx in (-1, 1):
                d.arc([P(50 + sx * w - 2.2, my - 2.4), P(50 + sx * w + 2.2, my + 0.8)],
                      *((110, 200) if sx < 0 else (340, 70)), fill=F["linie"], width=lw)
        else:
            # breites Lächeln mit Grübchen
            d.arc([P(50 - breite, my - 5), P(50 + breite, my + 3)], 15, 165, fill=F["linie"], width=lw + 1)
            for sx in (-1, 1):
                d.arc([P(50 + sx * breite * 0.97 - 1.6, my - 2.6), P(50 + sx * breite * 0.97 + 1.6, my + 0.2)],
                      *((120, 220) if sx < 0 else (320, 60)), fill=F["linie"], width=lw)
        return img


# --------------------------------------------------------------------------
# Szenen-Elemente
# --------------------------------------------------------------------------

def hintergrund(W, H, palette):
    oben, unten, h1, h2 = [rgb(c) for c in palette]
    t = np.linspace(0, 1, H)[:, None]
    arr = np.zeros((H, W, 3), np.float32)
    for i in range(3):
        arr[:, :, i] = oben[i] + (unten[i] - oben[i]) * t
    img = Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")
    lay = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    W2, H2 = W * 2, H * 2
    d.ellipse([-0.35 * W2, 0.62 * H2, 0.75 * W2, 1.5 * H2], fill=h1)
    d.ellipse([0.45 * W2, 0.66 * H2, 1.4 * W2, 1.5 * H2], fill=h1)
    d.ellipse([-0.5 * W2, 0.76 * H2, 1.5 * W2, 1.9 * H2], fill=h2)
    img.alpha_composite(lay.resize((W, H), Image.LANCZOS))
    return img.convert("RGB")


def sonne(r):
    S = int(r * 2.9) * 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S / 2
    R = r * 2
    for i in range(12):
        a = 2 * math.pi * i / 12
        pts = [(c + math.cos(a) * R * 1.15, c + math.sin(a) * R * 1.15),
               (c + math.cos(a + 0.13) * R * 1.0, c + math.sin(a + 0.13) * R * 1.0),
               (c + math.cos(a) * R * 1.42, c + math.sin(a) * R * 1.42),
               (c + math.cos(a - 0.13) * R * 1.0, c + math.sin(a - 0.13) * R * 1.0)]
        d.polygon(pts, fill=(255, 200, 40, 255))
    d.ellipse([c - R, c - R, c + R, c + R], fill=(255, 214, 64, 255), outline=(240, 160, 30, 255), width=int(R * 0.06))
    for sx in (-1, 1):
        d.ellipse([c + sx * R * 0.35 - R * 0.08, c - R * 0.2, c + sx * R * 0.35 + R * 0.08, c - R * 0.0],
                  fill=(90, 60, 20, 255))
    d.arc([c - R * 0.4, c - R * 0.15, c + R * 0.4, c + R * 0.45], 20, 160, fill=(90, 60, 20, 255), width=int(R * 0.07))
    return img.resize((S // 2, S // 2), Image.LANCZOS)


def wolke(b):
    h = int(b * 0.5)
    img = Image.new("RGBA", (b * 2, h * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    B, Hh = b * 2, h * 2
    for x, y, r in [(0.25, 0.62, 0.22), (0.45, 0.42, 0.3), (0.68, 0.55, 0.24), (0.5, 0.7, 0.25)]:
        d.ellipse([B * (x - r), Hh * (y - r * 1.6), B * (x + r), Hh * (y + r * 1.6)], fill=(255, 255, 255, 235))
    return img.resize((b, h), Image.LANCZOS)


def blume(groesse, farbe, stiel=True):
    S = groesse * 2
    img = Image.new("RGBA", (S, int(S * (1.6 if stiel else 1))), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S / 2
    R = S * 0.22
    lw = max(2, S // 60)
    if stiel:
        d.line([(c, c), (c, img.height)], fill=(60, 150, 60, 255), width=int(S * 0.06))
        d.polygon([(P[0], P[1]) for P in ellipse_poly(c + S * 0.16, c + S * 0.55, S * 0.16, S * 0.06, -30)],
                  fill=(80, 175, 70, 255))
    f = rgb(farbe)
    dunkel = mischen(f, (0, 0, 0, 255), 0.25)
    for i in range(6):
        a = 2 * math.pi * i / 6
        d.polygon(ellipse_poly(c + math.cos(a) * R * 1.1, c + math.sin(a) * R * 1.1, R * 0.95, R * 0.7,
                               math.degrees(a)), fill=f, outline=dunkel, width=lw)
    d.ellipse([c - R * 0.75, c - R * 0.75, c + R * 0.75, c + R * 0.75], fill=(255, 220, 70, 255),
              outline=(220, 160, 30, 255), width=lw)
    return img.resize((img.width // 2, img.height // 2), Image.LANCZOS)


def text_sprite(text, groesse, farbe, rand=(255, 255, 255, 255), randbreite=None):
    fnt = schrift(groesse)
    rb = randbreite if randbreite is not None else max(2, int(groesse * 0.09))
    box = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=fnt, stroke_width=rb)
    w, h = box[2] - box[0] + 8, box[3] - box[1] + 8
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((4 - box[0], 4 - box[1]), text, font=fnt, fill=farbe,
                             stroke_width=rb, stroke_fill=rand)
    return img


def zeige_sprite(zeige, H):
    farbe = zeige.get("farbe", "#e53935")
    text = zeige.get("text", "")
    if zeige.get("blume"):
        bl = blume(int(H * 0.36), farbe)
        tx = text_sprite(text, H * 0.085, rgb(farbe))
        img = Image.new("RGBA", (max(bl.width, tx.width), bl.height + tx.height - int(H * 0.08)), (0, 0, 0, 0))
        img.alpha_composite(bl, ((img.width - bl.width) // 2, 0))
        img.alpha_composite(tx, ((img.width - tx.width) // 2, img.height - tx.height))
        return img
    tx = text_sprite(text, H * (0.15 if len(text) <= 6 else 0.1), rgb(farbe), randbreite=0)
    pad = int(H * 0.05)
    w, h = tx.width + 2 * pad, tx.height + 2 * pad
    img = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 14, w * 2 - 6, h * 2 - 2], radius=int(h * 0.5), fill=(0, 0, 0, 40))
    d.rounded_rectangle([0, 0, w * 2 - 8, h * 2 - 14], radius=int(h * 0.5), fill=(255, 255, 255, 245),
                        outline=rgb(farbe), width=int(H * 0.012))
    img = img.resize((w, h), Image.LANCZOS)
    img.alpha_composite(tx, (pad - 4, pad - 7))
    return img


def noten_sprites(groesse):
    res = []
    fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(groesse)) \
        if Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf").exists() else schrift(groesse)
    for zeichen in ("♪", "♫"):
        for farbe in ("#e53935", "#8e24aa", "#1e88e5", "#43a047", "#fb8c00"):
            img = Image.new("RGBA", (int(groesse * 1.4), int(groesse * 1.4)), (0, 0, 0, 0))
            ImageDraw.Draw(img).text((groesse * 0.1, 0), zeichen, font=fnt, fill=rgb(farbe),
                                     stroke_width=max(2, int(groesse * 0.06)), stroke_fill=(255, 255, 255, 255))
            res.append(img)
    return res


class Karaoke:
    """Liedzeile mit Wort-für-Wort-Hervorhebung (zwischengespeichert)."""

    def __init__(self, W, H, akzent):
        self.W, self.H = W, H
        self.gross = schrift(H * 0.068)
        self.klein = schrift(H * 0.04)
        self.akzent = rgb(akzent)
        self.cache = {}
        bw, bh = int(W * 0.84), int(H * 0.17)
        box = Image.new("RGBA", (bw * 2, bh * 2), (0, 0, 0, 0))
        ImageDraw.Draw(box).rounded_rectangle([0, 0, bw * 2 - 1, bh * 2 - 1], radius=bh * 0.6,
                                              fill=(255, 255, 255, 215))
        self.box = box.resize((bw, bh), Image.LANCZOS)

    def zeile(self, zi, woerter, k):
        key = (zi, k)
        if key in self.cache:
            return self.cache[key]
        d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        leer = d0.textlength(" ", font=self.gross)
        breiten = [d0.textlength(w, font=self.gross) for w in woerter]
        gesamt = int(sum(breiten) + leer * (len(woerter) - 1)) + 20
        h = int(self.H * 0.09)
        img = Image.new("RGBA", (gesamt, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        x = 10
        for i, (w, b) in enumerate(zip(woerter, breiten)):
            farbe = self.akzent if i < k else (70, 70, 90, 255)
            d.text((x, h * 0.08), w, font=self.gross, fill=farbe)
            x += b + leer
        self.cache[key] = img
        return img

    def naechste(self, zi, text):
        key = ("n", zi)
        if key not in self.cache:
            d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
            w = int(d0.textlength(text, font=self.klein)) + 20
            img = Image.new("RGBA", (w, int(self.H * 0.06)), (0, 0, 0, 0))
            ImageDraw.Draw(img).text((10, 0), text, font=self.klein, fill=(130, 130, 150, 255))
            self.cache[key] = img
        return self.cache[key]


def gestapelt(sprites, abstand=0.9):
    """Mehrere Text-Sprites zentriert untereinander."""
    w = max(s.width for s in sprites)
    h = int(sum(s.height * abstand for s in sprites) + sprites[-1].height * (1 - abstand))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = 0
    for s in sprites:
        img.alpha_composite(s, ((w - s.width) // 2, int(y)))
        y += s.height * abstand
    return img


NACHT = ("#0f1b4c", "#3b4a8c", "#2e6b3a", "#244f2c")
WINTER = ("#8ecbf3", "#eef8ff", "#f2f7fc", "#d9e8f5")  # Himmel, verschneite Hügel


def mond(r):
    S = int(r * 2.4) * 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c, R = S / 2, r * 2
    d.ellipse([c - R * 1.15, c - R * 1.15, c + R * 1.15, c + R * 1.15], fill=(255, 240, 160, 50))
    d.ellipse([c - R, c - R, c + R, c + R], fill=(255, 228, 120, 255))
    d.ellipse([c - R * 0.2, c - R * 1.25, c + R * 1.5, c + R * 0.55], fill=(0, 0, 0, 0))
    d.arc([c - R * 0.75, c - R * 0.15, c - R * 0.35, c + R * 0.15], 200, 340, fill=(90, 60, 20, 255), width=int(R * 0.07))
    d.arc([c - R * 0.8, c + R * 0.15, c - R * 0.3, c + R * 0.5], 20, 160, fill=(90, 60, 20, 255), width=int(R * 0.07))
    return img.resize((S // 2, S // 2), Image.LANCZOS)


def stern(r, farbe=(255, 236, 140, 255)):
    S = int(r * 2.2) * 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c, R = S / 2, r * 2
    pts = []
    for i in range(10):
        rr = R if i % 2 == 0 else R * 0.45
        a = math.radians(-90 + i * 36)
        pts.append((c + rr * math.cos(a), c + rr * math.sin(a)))
    d.polygon(pts, fill=farbe)
    return img.resize((S // 2, S // 2), Image.LANCZOS)


def sprechblase(text, H, max_zeichen=24):
    fnt = schrift(H * 0.05)
    woerter, zeilen, akt = text.split(), [], ""
    for w in woerter:
        if len(akt) + len(w) + 1 > max_zeichen and akt:
            zeilen.append(akt)
            akt = w
        else:
            akt = (akt + " " + w).strip()
    zeilen.append(akt)
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    zh = H * 0.062
    bw = int(max(d0.textlength(z, font=fnt) for z in zeilen) + H * 0.08)
    bh = int(zh * len(zeilen) + H * 0.06)
    schw = int(H * 0.07)
    img = Image.new("RGBA", ((bw + 10) * 2, (bh + schw + 10) * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rand = (90, 80, 110, 255)
    lw = max(3, int(H * 0.006))
    # Schatten
    d.rounded_rectangle([10, 16, bw * 2 + 10, bh * 2 + 16], radius=bh * 0.5, fill=(0, 0, 0, 40))
    d.polygon([(bw * 2 - bh * 0.9, bh * 2 - 4), (bw * 2 - bh * 0.3, bh * 2 - 4), (bw * 2 + 4, (bh + schw) * 2)],
              fill=(255, 255, 255, 255), outline=rand, width=lw)
    d.rounded_rectangle([0, 0, bw * 2, bh * 2], radius=min(bh, bw) * 0.5 * 2 * 0.5, fill=(255, 255, 255, 255),
                        outline=rand, width=lw)
    d.polygon([(bw * 2 - bh * 0.9 + lw, bh * 2 - lw * 2), (bw * 2 - bh * 0.3 - lw, bh * 2 - lw * 2),
               (bw * 2 - bh * 0.6, bh * 2 + lw)], fill=(255, 255, 255, 255))
    img = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    for i, z in enumerate(zeilen):
        w = d.textlength(z, font=fnt)
        d.text(((bw - w) / 2, H * 0.025 + i * zh), z, font=fnt, fill=(60, 50, 80, 255))
    return img


def zahnbuerste_klein(laenge):
    """Zahnbürste waagerecht, Kopf links (für die Figur)."""
    S = laenge * 2
    h = int(S * 0.3)
    img = Image.new("RGBA", (S, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(2, S // 80)
    d.rounded_rectangle([S * 0.25, h * 0.45, S - 2, h * 0.75], radius=h * 0.15, fill=(33, 150, 243, 255),
                        outline=(40, 40, 60, 255), width=lw)
    d.rounded_rectangle([2, h * 0.42, S * 0.3, h * 0.78], radius=h * 0.08, fill=(255, 255, 255, 255),
                        outline=(40, 40, 60, 255), width=lw)
    for k in range(6):
        x = 6 + k * S * 0.045
        d.rectangle([x, h * 0.05, x + S * 0.03, h * 0.42], fill=(130, 210, 255, 255))
    for k in range(5):
        d.ellipse([S * (0.02 + k * 0.05), h * (0.0 + (k % 2) * 0.1), S * (0.02 + k * 0.05) + h * 0.22,
                   h * (0.22 + (k % 2) * 0.1)], fill=(255, 255, 255, 240))
    return img.resize((S // 2, h // 2), Image.LANCZOS)


def seifenblase(r):
    S = r * 4
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, S - 3, S - 3], fill=(200, 235, 255, 70), outline=(140, 200, 245, 220), width=max(2, S // 25))
    d.arc([S * 0.18, S * 0.18, S * 0.82, S * 0.82], 200, 260, fill=(255, 255, 255, 230), width=max(2, S // 14))
    d.ellipse([S * 0.62, S * 0.6, S * 0.72, S * 0.7], fill=(255, 200, 240, 160))
    return img.resize((S // 2, S // 2), Image.LANCZOS)
