"""Bilder (Icons), die passend zum Liedtext eingeblendet werden. Alle mit Pillow gezeichnet.

bild_sprite(typ, groesse, farbe, t) -> RGBA-Bild (groesse x groesse), t = Zeit für Animationen.
"""
import math
import random

from PIL import Image, ImageDraw

from grafik import ellipse_poly, rgb, mischen, schrift, sonne as sonne_sprite

LINIE = (60, 45, 50, 255)
WEISS = (255, 255, 255, 255)

ANIMIERT = {"feuerwehr", "meer", "fisch", "wecker", "zaehneputzen", "sterne", "kueken", "mond", "bett", "himmel"}


class Zeichner:
    def __init__(self, groesse):
        self.S = groesse * 2
        self.u = self.S / 100.0
        self.img = Image.new("RGBA", (self.S, self.S), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)
        self.lw = max(2, int(1.4 * self.u))

    def P(self, x, y):
        return (x * self.u, y * self.u)

    def ell(self, cx, cy, rx, ry, fill, outline=LINIE, winkel=0.0, breite=None):
        pts = [self.P(x, y) for x, y in ellipse_poly(cx, cy, rx, ry, winkel)]
        self.d.polygon(pts, fill=fill, outline=outline, width=(breite or self.lw) if outline else 0)

    def poly(self, pts, fill, outline=LINIE):
        self.d.polygon([self.P(x, y) for x, y in pts], fill=fill, outline=outline,
                       width=self.lw if outline else 0)

    def rrect(self, x0, y0, x1, y1, r, fill, outline=LINIE):
        self.d.rounded_rectangle([self.P(x0, y0), self.P(x1, y1)], radius=r * self.u, fill=fill,
                                 outline=outline, width=self.lw if outline else 0)

    def linie(self, pts, farbe=LINIE, breite=1.4):
        self.d.line([self.P(x, y) for x, y in pts], fill=farbe, width=max(1, int(breite * self.u)), joint="curve")

    def stern(self, cx, cy, r, fill, zacken=5, innen=0.45, drehung=-90):
        pts = []
        for i in range(zacken * 2):
            rr = r if i % 2 == 0 else r * innen
            a = math.radians(drehung + i * 180 / zacken)
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        self.poly(pts, fill, outline=None)

    def fertig(self):
        return self.img.resize((self.S // 2, self.S // 2), Image.LANCZOS)


# --------------------------------------------------------------------------

def _blume(z, f, t):
    z.linie([(50, 52), (50, 98)], (60, 150, 60, 255), 4)
    z.ell(62, 80, 11, 4.5, (80, 175, 70, 255), outline=None, winkel=-30)
    dunkel = mischen(f, (0, 0, 0, 255), 0.25)
    for i in range(6):
        a = 2 * math.pi * i / 6
        z.ell(50 + math.cos(a) * 16, 36 + math.sin(a) * 16, 13, 9.5, f, outline=dunkel, winkel=math.degrees(a))
    z.ell(50, 36, 10, 10, (255, 220, 70, 255), outline=(220, 160, 30, 255))
    for sx in (-1, 1):
        z.ell(50 + sx * 3.5, 34, 1.3, 1.8, LINIE, outline=None)
    z.d.arc([z.P(45, 35), z.P(55, 41)], 20, 160, fill=LINIE, width=z.lw)


def _erdbeere(z, f, t):
    rot = (229, 57, 53, 255)
    pts = []
    for i in range(40):
        a = 2 * math.pi * i / 40
        x, y = math.cos(a), math.sin(a)
        breite = 30 * (1 - 0.35 * max(0, y))
        pts.append((50 + breite * x, 55 + 32 * y * (1.15 if y > 0 else 0.8)))
    z.poly(pts, rot)
    rng = random.Random(4)
    for _ in range(14):
        x, y = rng.uniform(32, 68), rng.uniform(42, 78)
        if abs(x - 50) < 30 * (1 - 0.35 * max(0, (y - 55) / 32)) - 5:
            z.ell(x, y, 1.4, 2.2, (255, 235, 120, 255), outline=None)
    for i in range(5):
        a = math.radians(-90 + (i - 2) * 38)
        z.ell(50 + math.cos(a) * 9, 31 + math.sin(a) * 4 + 3, 9, 3.5, (70, 170, 70, 255), winkel=math.degrees(a))
    z.linie([(50, 28), (52, 16)], (70, 140, 60, 255), 2.5)
    for sx in (-1, 1):
        z.ell(50 + sx * 8, 52, 2, 2.6, LINIE, outline=None)
    z.d.arc([z.P(44, 56), z.P(56, 64)], 20, 160, fill=LINIE, width=z.lw)


def _feuerwehr(z, f, t):
    rot = (220, 40, 40, 255)
    z.rrect(8, 44, 70, 76, 3, rot)
    z.rrect(62, 34, 92, 76, 4, rot)
    z.rrect(68, 39, 86, 52, 2, (170, 220, 255, 255))
    z.rrect(8, 62, 92, 66, 0, WEISS, outline=None)
    # Leiter
    z.linie([(12, 38), (60, 38)], (190, 190, 200, 255), 2)
    z.linie([(12, 32), (60, 32)], (190, 190, 200, 255), 2)
    for x in range(14, 60, 7):
        z.linie([(x, 32), (x, 38)], (190, 190, 200, 255), 1.5)
    z.linie([(20, 38), (20, 44)], LINIE, 1.5)
    z.linie([(54, 38), (54, 44)], LINIE, 1.5)
    # Blaulicht (blinkt)
    an = int(t * 5) % 2 == 0
    z.rrect(72, 26, 82, 34, 2, (60, 140, 255, 255) if an else (170, 200, 240, 255))
    if an:
        for a in (-40, 0, 40):
            r = math.radians(-90 + a)
            z.linie([(77 + math.cos(r) * 8, 30 + math.sin(r) * 8), (77 + math.cos(r) * 14, 30 + math.sin(r) * 14)],
                    (60, 140, 255, 255), 1.6)
    for x in (26, 74):
        z.ell(x, 78, 9, 9, (50, 50, 60, 255))
        z.ell(x, 78, 3.5, 3.5, (200, 200, 210, 255), outline=None)


def _banane(z, f, t):
    gelb = (253, 216, 53, 255)
    aussen = [(50 + 36 * math.cos(math.radians(a)), 30 + 36 * math.sin(math.radians(a))) for a in range(15, 166, 5)]
    innen = [(50 + 31 * math.cos(math.radians(a)), 20 + 31 * math.sin(math.radians(a))) for a in range(160, 19, -5)]
    z.poly(aussen + innen, gelb)
    z.linie([(50 + 33 * math.cos(math.radians(a)), 26 + 33 * math.sin(math.radians(a))) for a in range(40, 141, 10)],
            (230, 180, 40, 255), 1.2)
    z.ell(aussen[0][0], aussen[0][1] - 2, 3, 3, (120, 80, 30, 255), outline=None)
    z.ell(aussen[-1][0], aussen[-1][1] - 2, 3, 3, (120, 80, 30, 255), outline=None)
    for sx in (-1, 1):
        z.ell(50 + sx * 7, 55, 1.8, 2.4, LINIE, outline=None)
    z.d.arc([z.P(45, 56), z.P(55, 62)], 20, 160, fill=LINIE, width=z.lw)


def _kueken(z, f, t):
    gelb = (255, 214, 64, 255)
    hops = abs(math.sin(t * 6)) * 4
    z.linie([(42, 86), (40, 94)], (240, 140, 30, 255), 2)
    z.linie([(58, 86), (60, 94)], (240, 140, 30, 255), 2)
    z.ell(50, 64 - hops, 28, 24, gelb)
    z.ell(50, 36 - hops, 19, 18, gelb)
    z.ell(30, 62 - hops, 7, 12, gelb, winkel=30 + math.sin(t * 12) * 15)
    z.ell(70, 62 - hops, 7, 12, gelb, winkel=-30 - math.sin(t * 12) * 15)
    for sx in (-1, 1):
        z.ell(50 + sx * 7, 33 - hops, 2.4, 3, LINIE, outline=None)
        z.ell(50 + sx * 12, 40 - hops, 3, 2, (255, 140, 160, 160), outline=None)
    offen = int(t * 4) % 2
    z.poly([(45, 40 - hops), (55, 40 - hops), (50, 46 + offen * 3 - hops)], (245, 140, 30, 255))
    z.linie([(50, 18 - hops), (47, 12 - hops)], (230, 180, 40, 255), 1.6)
    z.linie([(50, 18 - hops), (54, 12 - hops)], (230, 180, 40, 255), 1.6)


def _himmel(z, f, t):
    x = 50 + math.sin(t * 0.8) * 4
    for cx, cy, r in [(x - 14, 52, 13), (x, 44, 17), (x + 15, 50, 13), (x, 56, 12)]:
        z.ell(cx, cy, r * 1.15, r, WEISS, outline=None)
    for k, (bx, by) in enumerate([(24, 26), (76, 30), (70, 74)]):
        s = 1 + 0.3 * math.sin(t * 3 + k)
        z.ell(bx + math.sin(t + k) * 3, by, 5 * s, 2.5 * s, (255, 255, 255, 180), outline=None)


def _meer(z, f, t):
    for k, (farbe, y0) in enumerate([((100, 181, 246, 255), 44), ((30, 136, 229, 255), 56), ((21, 101, 192, 255), 70)]):
        pts = [(0, 100), (0, y0)]
        for i in range(41):
            x = i * 2.5
            pts.append((x, y0 + 4 * math.sin(x / 8 + t * (2.5 + k) + k)))
        pts.append((100, 100))
        z.poly(pts, farbe, outline=None)
        for i in range(0, 41, 8):
            x = i * 2.5 + 3
            z.ell(x, y0 + 4 * math.sin(x / 8 + t * (2.5 + k) + k) + 1, 3, 1.2, (255, 255, 255, 200), outline=None)
    z.ell(78, 22, 9, 9, (255, 214, 64, 255), outline=None)


def _fisch(z, f, t):
    farbe = (255, 152, 0, 255) if f is None else f
    w = math.sin(t * 7) * 6
    dy = math.sin(t * 2) * 3
    z.poly([(72, 50 + dy), (92, 34 + dy + w), (90, 66 + dy + w)], farbe)
    z.ell(48, 50 + dy, 28, 18, farbe)
    z.ell(48, 34 + dy, 9, 5, mischen(farbe, (0, 0, 0, 255), 0.15), winkel=-15)
    for x in (52, 60):
        z.linie([(x, 38 + dy), (x - 4, 50 + dy), (x, 62 + dy)], mischen(farbe, (0, 0, 0, 255), 0.25), 1.2)
    z.ell(32, 46 + dy, 5, 5.5, WEISS)
    z.ell(31, 47 + dy, 2.5, 3, LINIE, outline=None)
    z.d.arc([z.P(22, 50 + dy), z.P(30, 58 + dy)], 20, 160, fill=LINIE, width=z.lw)
    for k in range(3):
        alt = (t * 0.8 + k / 3) % 1
        z.ell(16 - k * 2, 40 + dy - alt * 35, 2 + k, 2 + k, (180, 225, 255, 220), outline=(120, 180, 230, 255), breite=2)


def _wecker(z, f, t):
    w = math.sin(t * 45) * 2.5
    rot = (229, 57, 53, 255)
    for sx in (-1, 1):
        z.ell(50 + sx * 20 + w, 24, 9, 7, (200, 200, 210, 255), winkel=sx * 30)
        z.linie([(50 + sx * 18 + w, 76), (50 + sx * 24 + w, 88)], LINIE, 2.5)
    z.ell(50 + w, 54, 29, 29, rot)
    z.ell(50 + w, 54, 22, 22, WEISS)
    for i in range(12):
        a = 2 * math.pi * i / 12
        z.ell(50 + w + math.cos(a) * 18, 54 + math.sin(a) * 18, 1, 1, LINIE, outline=None)
    z.linie([(50 + w, 54), (50 + w, 40)], LINIE, 2.2)
    z.linie([(50 + w, 54), (60 + w, 58)], LINIE, 2.2)
    for sx in (-1, 1):
        for k in range(2):
            r = 34 + k * 7
            a0 = 200 if sx < 0 else -20
            z.d.arc([z.P(50 - r, 54 - r), z.P(50 + r, 54 + r)], a0 - 15, a0 + 15, fill=(255, 160, 0, 255),
                    width=z.lw)


def _zahnbuerste_zeichnen(z, x, y, winkel, laenge=60, farbe=(33, 150, 243, 255)):
    """Zahnbürste mit Kopf bei (x, y), Griff zeigt in Richtung 'winkel'."""
    c, s = math.cos(math.radians(winkel)), math.sin(math.radians(winkel))

    def R(px, py):
        return (x + px * c - py * s, y + px * s + py * c)
    z.poly([R(0, -4), R(laenge, -3), R(laenge, 3), R(0, 4)], farbe)
    z.poly([R(-2, -6), R(20, -6), R(20, 4), R(-2, 4)], WEISS)
    for k in range(6):
        px = 0 + k * 3.4
        z.poly([R(px, -6), R(px + 2.6, -6), R(px + 2.6, -16), R(px, -16)], (130, 210, 255, 255), outline=None)


def _zahnbuerste(z, f, t):
    _zahnbuerste_zeichnen(z, 20, 60, -30, 70, (33, 150, 243, 255) if f is None else f)
    for k in range(4):
        a = t * 2 + k * 1.6
        z.stern(70 + math.cos(a) * 18, 30 + math.sin(a) * 10, 4, (255, 230, 90, 255))


def _zahnpasta(z, f, t):
    z.rrect(12, 44, 64, 68, 6, WEISS)
    z.rrect(16, 50, 60, 54, 0, (229, 57, 53, 255), outline=None)
    z.rrect(16, 57, 60, 61, 0, (33, 150, 243, 255), outline=None)
    z.poly([(6, 40), (14, 44), (14, 68), (6, 72)], (220, 220, 230, 255))
    z.rrect(64, 49, 76, 63, 2, (33, 150, 243, 255))
    raus = min(1.0, (t % 3) / 1.2)
    for k in range(int(1 + raus * 4)):
        z.ell(80 + k * 4, 56 - k * 1.5, 5, 4.5, WEISS if k % 2 == 0 else (130, 210, 255, 255), outline=(150, 190, 220, 255))


def _zaehneputzen(z, f, t):
    # Mund
    z.ell(50, 52, 42, 30, (240, 110, 130, 255))
    z.ell(50, 52, 35, 23, (140, 30, 50, 255), outline=None)
    z.ell(50, 66, 18, 7, (240, 120, 140, 255), outline=None)
    sauber = min(1.0, (t % 4) / 3)
    zahnfarbe = mischen((235, 225, 190, 255), WEISS, sauber)
    for i in range(6):
        x = 22 + i * 9.6
        z.rrect(x, 31, x + 8.6, 44 - abs(i - 2.5) * 0.8, 3, zahnfarbe, outline=(190, 180, 170, 255))
        z.rrect(x + 1, 60 + abs(i - 2.5) * 0.8, x + 8.6, 72, 3, zahnfarbe, outline=(190, 180, 170, 255))
    # Schaum
    rng = random.Random(int(t * 8))
    bx = 50 + 20 * math.sin(t * 13)
    for _ in range(9):
        z.ell(bx + rng.uniform(-14, 14), rng.uniform(34, 70), rng.uniform(2, 4.5), rng.uniform(2, 4.5),
              (255, 255, 255, 235), outline=(200, 220, 240, 255), breite=2)
    _zahnbuerste_zeichnen(z, bx - 6, 50, 0, 70)
    # Glitzern
    if sauber > 0.6:
        for k in range(3):
            a = t * 3 + k * 2.1
            z.stern(28 + k * 22, 22 + 4 * math.sin(a), 5 * (0.6 + 0.4 * math.sin(a * 2)), (255, 235, 90, 255))


def _mond(z, f, t):
    lay = Image.new("RGBA", z.img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([z.P(18, 18), z.P(82, 82)], fill=(255, 224, 102, 255))
    d.ellipse([z.P(36, 8), z.P(96, 68)], fill=(0, 0, 0, 0))
    z.img.alpha_composite(lay)
    z.d.arc([z.P(26, 46), z.P(36, 52)], 200, 340, fill=LINIE, width=z.lw)
    z.d.arc([z.P(26, 56), z.P(40, 64)], 20, 160, fill=LINIE, width=z.lw)
    for k in range(3):
        alt = (t * 0.5 + k / 3) % 1
        fnt = schrift(z.S * (0.07 + 0.03 * k))
        z.d.text(z.P(62 + k * 9 + alt * 4, 50 - k * 12 - alt * 8), "z", font=fnt,
                 fill=(255, 255, 255, int(255 * (1 - alt))))


def _bett(z, f, t):
    braun = (161, 110, 70, 255)
    z.rrect(8, 36, 16, 86, 2, braun)
    z.rrect(84, 52, 92, 86, 2, braun)
    z.rrect(12, 62, 88, 74, 2, braun)
    z.rrect(18, 48, 40, 60, 5, WEISS)
    # schlafender Bär
    z.ell(32, 44, 4, 4, (176, 122, 79, 255))
    z.ell(44, 44, 4, 4, (176, 122, 79, 255))
    z.ell(38, 52, 10, 9, (176, 122, 79, 255))
    z.d.arc([z.P(32, 50), z.P(37, 54)], 200, 340, fill=LINIE, width=z.lw)
    z.d.arc([z.P(39, 50), z.P(44, 54)], 200, 340, fill=LINIE, width=z.lw)
    z.rrect(40, 52, 86, 66, 4, (66, 133, 244, 255))
    for x in range(46, 84, 9):
        z.stern(x, 59, 2.6, (255, 230, 90, 255))
    atem = 0.5 + 0.5 * math.sin(t * 2)
    fnt = schrift(z.S * (0.08 + 0.03 * atem))
    z.d.text(z.P(55, 18 + 4 * (1 - atem)), "Z z z", font=fnt, fill=(120, 140, 255, 255))


def _sterne(z, f, t):
    for k, (x, y, r) in enumerate([(30, 30, 14), (68, 26, 10), (56, 62, 16), (24, 72, 8), (82, 70, 9)]):
        s = 0.75 + 0.25 * math.sin(t * 3 + k * 1.3)
        z.stern(x, y, r * s, (255, 224, 102, 255), drehung=-90 + k * 7)


def _moehre(z, f, t, x=50, y=50, s=1.0, winkel=-25):
    c, si = math.cos(math.radians(winkel)), math.sin(math.radians(winkel))

    def R(px, py):
        return (x + (px * c - py * si) * s, y + (px * si + py * c) * s)
    z.poly([R(-34, -13), R(-34, 13), R(34, 0)], (255, 140, 30, 255))
    for px in (-20, -6, 8):
        z.linie([R(px, -6 + (px + 20) * 0.12), R(px + 5, -3 + (px + 20) * 0.12)], (200, 100, 20, 255), 1.2 * s)
    for a in (-35, 0, 35):
        r = math.radians(a)
        z.ell(*R(-34 - 8 * math.cos(r), 8 * math.sin(r)), 9 * s, 3 * s, (70, 170, 70, 255),
              winkel=winkel + 180 + a)


ZEICHNER = {"blume": _blume, "erdbeere": _erdbeere, "feuerwehr": _feuerwehr, "banane": _banane,
            "kueken": _kueken, "himmel": _himmel, "meer": _meer, "fisch": _fisch, "wecker": _wecker,
            "zahnbuerste": _zahnbuerste, "zahnpasta": _zahnpasta, "zaehneputzen": _zaehneputzen,
            "mond": _mond, "bett": _bett, "sterne": _sterne, "moehre": _moehre}

HINTERGRUND = {"himmel": (100, 181, 246, 255), "meer": (187, 222, 251, 255), "mond": (40, 53, 107, 255),
               "sterne": (40, 53, 107, 255), "bett": (225, 230, 255, 255)}


HAUT = (242, 199, 165, 255)
HAUT_LINIE = (150, 100, 70, 255)


def _hand(z, cx, cy, winkel, spiegel=1, g=1.35):
    """Einfache Kinderhand (Handfläche + 4 Finger + Daumen)."""
    c, s_ = math.cos(math.radians(winkel)), math.sin(math.radians(winkel))

    def R(px, py):
        px *= spiegel * g
        py *= g
        return (cx + px * c - py * s_, cy + px * s_ + py * c)

    def fl(fx, fy, rx, ry, w):
        pts = [R(x, y) for x, y in ellipse_poly(fx, fy, rx, ry, w * spiegel)]
        z.poly(pts, HAUT, outline=HAUT_LINIE)
    for dx, fy, l, w in [(-8.5, -16, 8, -8), (-2.8, -18.5, 9.5, -2), (3, -18, 9, 3), (8.5, -15, 7, 9)]:
        fl(dx, fy, 3.2, l, w)
    fl(-13, -2, 3.4, 7.5, -55)
    fl(0, -2, 12.5, 11.5, 0)


def _blasen(z, t, anzahl=8, bereich=(15, 85, 20, 80), seed=2):
    rng = random.Random(seed)
    for k in range(anzahl):
        x0 = rng.uniform(bereich[0], bereich[1])
        r = rng.uniform(3, 7)
        ph = (t * rng.uniform(0.25, 0.5) + rng.random()) % 1
        y = bereich[3] - ph * (bereich[3] - bereich[2])
        x = x0 + math.sin(t * 2 + k) * 3
        z.ell(x, y, r, r, (200, 235, 255, 110), outline=(120, 190, 240, 255), breite=2)
        z.ell(x - r * 0.35, y - r * 0.35, r * 0.25, r * 0.25, (255, 255, 255, 230), outline=None)


def _haende(z, f, t):
    reib = math.sin(t * 9) * 5
    _hand(z, 42 + reib, 58, -20, 1)
    _hand(z, 58 - reib, 60, 20, -1)
    rng = random.Random(int(t * 6))
    for _ in range(10):
        x, y = rng.uniform(32, 68), rng.uniform(48, 72)
        r = rng.uniform(2.5, 5)
        z.ell(x, y, r, r, (255, 255, 255, 235), outline=(190, 215, 240, 255), breite=2)
    _blasen(z, t, 6, (20, 80, 10, 45))


def _wasserhahn(z, f, t):
    grau, dunkel = (176, 190, 197, 255), (120, 135, 145, 255)
    z.rrect(16, 32, 36, 50, 3, grau, outline=dunkel)
    z.rrect(34, 36, 62, 46, 4, grau, outline=dunkel)
    z.rrect(54, 36, 66, 54, 4, grau, outline=dunkel)
    z.rrect(22, 22, 30, 32, 2, (229, 57, 53, 255))
    z.rrect(16, 19, 36, 23, 2, (229, 57, 53, 255))
    # Wasserstrahl
    z.rrect(56.5, 54, 63.5, 82, 3, (100, 181, 246, 230), outline=None)
    for k in range(6):
        y = 54 + ((t * 60 + k * 7) % 28)
        z.ell(60, y, 1.6, 3, (255, 255, 255, 200), outline=None)
    # Becken und Spritzer
    z.ell(60, 86, 26, 6, (144, 202, 249, 255), outline=(100, 160, 220, 255))
    for k in range(5):
        ph = (t * 2.5 + k / 5) % 1
        a = math.radians(200 + k * 35)
        z.ell(60 + math.cos(a) * ph * 18, 84 - math.sin(math.radians(60 + k * 15)) * ph * 14 * (1 - ph) * 2,
              2, 2, (100, 181, 246, 255), outline=None)


def _seife(z, f, t):
    _blasen(z, t, 9, (15, 85, 8, 55), seed=5)
    z.rrect(20, 52, 80, 82, 12, (244, 143, 177, 255), outline=(194, 84, 120, 255))
    z.rrect(26, 56, 74, 64, 4, (248, 187, 208, 255), outline=None)
    fnt = schrift(z.S * 0.1)
    z.d.text(z.P(31, 64), "SEIFE", font=fnt, fill=(255, 255, 255, 255))
    for x in (38, 62):
        z.ell(x, 50, 6, 5, WEISS, outline=(190, 215, 240, 255), breite=2)


def _handtuch(z, f, t):
    blau = (66, 165, 245, 255)
    z.linie([(12, 20), (88, 20)], (150, 110, 80, 255), 3)
    w = math.sin(t * 2) * 2
    z.poly([(22, 20), (78, 20), (80 + w, 86), (20 + w, 86)], blau, outline=(30, 110, 190, 255))
    for y in (68, 74):
        z.poly([(21 + w * (y - 20) / 66, y), (79 + w * (y - 20) / 66, y), (79.3 + w * (y - 20) / 66, y + 3),
                (20.7 + w * (y - 20) / 66, y + 3)], WEISS, outline=None)
    z.ell(50, 44, 9, 9, WEISS, outline=None)
    z.stern(50, 44, 6, (255, 214, 64, 255))
    for k in range(3):
        a = t * 3 + k * 2.1
        z.stern(30 + k * 20, 12 + 3 * math.sin(a), 3.5 * (0.6 + 0.4 * math.sin(a * 2)), (255, 214, 64, 255))


ZEICHNER.update({"haende": _haende, "wasserhahn": _wasserhahn, "seife": _seife, "handtuch": _handtuch})
ANIMIERT.update({"haende", "wasserhahn", "seife", "handtuch"})
HINTERGRUND.update({"wasserhahn": (227, 242, 253, 255)})


def bild_sprite(typ, groesse, farbe=None, t=0.0):
    """Rundes Bild mit Rahmen. farbe = Rahmenfarbe (und Blumenfarbe)."""
    f = rgb(farbe) if farbe else None
    z = Zeichner(groesse)
    rahmen = f or (255, 183, 77, 255)
    hg = HINTERGRUND.get(typ, WEISS)
    z.ell(50, 51.5, 47, 47, (0, 0, 0, 45), outline=None)
    z.ell(50, 50, 47, 47, hg, outline=rahmen, breite=int(2.6 * z.u))
    if typ == "sonne":
        s = sonne_sprite(int(z.S * 0.25)).rotate(-t * 20, resample=Image.BICUBIC)
        z.img.alpha_composite(s, ((z.S - s.width) // 2, (z.S - s.height) // 2))
    elif typ in ZEICHNER:
        # Inhalt auf eigene Ebene zeichnen und auf den Kreis beschneiden
        inhalt = Zeichner(groesse)
        ZEICHNER[typ](inhalt, f if typ in ("blume", "fisch") else None, t)
        maske = Image.new("L", z.img.size, 0)
        ImageDraw.Draw(maske).ellipse([z.P(4.5, 4.5), z.P(95.5, 95.5)], fill=255)
        alpha = Image.composite(inhalt.img.getchannel("A"), Image.new("L", z.img.size, 0), maske)
        inhalt.img.putalpha(alpha)
        z.img.alpha_composite(inhalt.img)
    return z.fertig()


def zahl_sprite(zahl, groesse, farbe, objekt="moehre"):
    """Große Zahl + entsprechend viele Möhren (oder Punkte) zum Mitzählen."""
    f = rgb(farbe)
    B, H = int(groesse * 1.25), int(groesse)
    img = Image.new("RGBA", (B * 2, H * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([8, 16, B * 2 - 2, H * 2 - 2], radius=H * 0.2, fill=(0, 0, 0, 45))
    d.rounded_rectangle([0, 0, B * 2 - 10, H * 2 - 18], radius=H * 0.2, fill=WEISS, outline=f,
                        width=int(H * 0.05))
    fnt = schrift(H * 0.85)
    txt = str(zahl)
    bb = d.textbbox((0, 0), txt, font=fnt)
    d.text(((B * 2 - 10 - (bb[2] - bb[0])) / 2 - bb[0], H * 0.08 - bb[1]), txt, font=fnt, fill=f,
           stroke_width=int(H * 0.02), stroke_fill=mischen(f, (0, 0, 0, 255), 0.2))
    if zahl == 0:
        fnt2 = schrift(H * 0.16)
        d.text((B * 0.62, H * 1.42), "keine mehr!", font=fnt2, fill=(120, 120, 140, 255))
    else:
        reihen = 1 if zahl <= 5 else 2
        pro = min(5, zahl)
        feld = (B * 2 - 10) / 5.3
        z = Zeichner(int(feld / 2))
        _moehre(z, None, 0, x=55, y=50, s=1.2, winkel=-60)
        m = z.fertig().resize((int(feld), int(feld)), Image.LANCZOS)
        for i in range(zahl):
            r, c = divmod(i, 5)
            n_reihe = pro if r == 0 else zahl - 5
            x0 = (B * 2 - 10 - n_reihe * feld) / 2 + c * feld
            y0 = H * (1.05 if reihen == 1 else 0.88) + r * feld * 0.85
            img.alpha_composite(m, (int(x0), int(y0)))
    return img.resize((B, H), Image.LANCZOS)
