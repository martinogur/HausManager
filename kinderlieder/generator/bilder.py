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
            "mond": _mond, "bett": _bett, "sterne": _sterne,
            "moehre": lambda z, f, t: _moehre(z, f, t, x=56, y=48, s=0.95, winkel=-45)}  # schräg und etwas kleiner, damit nichts abgeschnitten wird

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


REGENBOGEN = [(229, 57, 53, 255), (251, 140, 0, 255), (253, 216, 53, 255), (67, 160, 71, 255),
              (30, 136, 229, 255), (142, 36, 170, 255)]


def _regenbogen(z, f, t):
    for k, farbe in enumerate(REGENBOGEN):
        r = 40 - k * 5
        z.d.arc([z.P(50 - r, 72 - r), z.P(50 + r, 72 + r)], 180, 360, fill=farbe, width=int(5.2 * z.u))
    for cx in (16, 84):
        x = cx + math.sin(t * 1.2) * 1.5
        for dx, dy, r in ((-7, 0, 7), (0, -4, 9), (8, 0, 7), (0, 3, 7)):
            z.ell(x + dx, 72 + dy, r * 1.15, r, WEISS, outline=None)
    for k in range(4):
        a = t * 2.5 + k * 1.7
        z.stern(26 + k * 16, 18 + 6 * math.sin(a), 3.5 * (0.6 + 0.4 * math.sin(a * 2)), (255, 214, 64, 255))


def _blatt(z, f, t):
    gruen, dunkel = (67, 160, 71, 255), (46, 125, 50, 255)
    w = math.sin(t * 2) * 6
    pts = []
    for i in range(41):
        u = i / 40
        pts.append((50 + 26 * math.sin(math.pi * u), 14 + 68 * u))
    for i in range(41):
        u = 1 - i / 40
        pts.append((50 - 26 * math.sin(math.pi * u), 14 + 68 * u))
    c, s_ = math.cos(math.radians(w)), math.sin(math.radians(w))
    pts = [(50 + (x - 50) * c - (y - 50) * s_, 50 + (x - 50) * s_ + (y - 50) * c) for x, y in pts]
    z.poly(pts, gruen, outline=dunkel)
    def R(x, y):
        return (50 + (x - 50) * c - (y - 50) * s_, 50 + (x - 50) * s_ + (y - 50) * c)
    z.linie([R(50, 16), R(50, 92)], dunkel, 1.6)
    for y in (30, 44, 58, 70):
        z.linie([R(50, y + 6), R(36, y)], dunkel, 1.2)
        z.linie([R(50, y + 6), R(64, y)], dunkel, 1.2)
    _ = f


def _frosch(z, f, t):
    gruen, hell, linie = (124, 201, 107, 255), (216, 245, 198, 255), (47, 90, 38, 255)
    quak = max(0.0, math.sin(t * 5)) ** 3
    z.ell(50, 64, 34, 24, gruen, outline=linie)
    z.ell(50, 74, 22, 12, hell, outline=None)
    for sx in (-1, 1):
        z.ell(50 + sx * 17, 36, 12, 12, gruen, outline=linie)
        z.ell(50 + sx * 17, 36, 8, 8.5, WEISS, outline=None)
        z.ell(50 + sx * 17 + 1, 37, 4.2, 5, LINIE, outline=None)
        z.ell(50 + sx * 17, 35, 1.5, 1.5, WEISS, outline=None)
        z.ell(50 + sx * 26, 58, 4.5, 2.8, (255, 140, 160, 140), outline=None)
    if quak > 0.2:
        z.ell(50, 70 + quak * 4, 12 * quak + 4, 9 * quak + 3, (255, 182, 193, 230), outline=(200, 110, 130, 255))
    z.d.arc([z.P(32, 50), z.P(68, 66)], 20, 160, fill=linie, width=z.lw + 1)
    fnt = schrift(z.S * 0.1)
    if quak > 0.3:
        z.d.text(z.P(37, 8), "Quak!", font=fnt, fill=(46, 125, 50, 255))


def _traube(z, f, t):
    lila, dunkel = (142, 36, 170, 255), (90, 20, 110, 255)
    z.linie([(50, 22), (54, 10)], (110, 80, 50, 255), 2.5)
    z.ell(64, 18, 11, 6, (67, 160, 71, 255), outline=(46, 125, 50, 255), winkel=-20)
    reihen = [(30, [38, 50, 62]), (41, [32, 44, 56, 68]), (52, [38, 50, 62]), (63, [44, 56]), (73, [50])]
    for y, xs in reihen:
        for x in xs:
            z.ell(x, y, 7, 7, lila, outline=dunkel)
            z.ell(x - 2.2, y - 2.2, 1.8, 1.8, (230, 190, 245, 255), outline=None)
    for sx in (-1, 1):
        z.ell(50 + sx * 6, 46, 1.8, 2.4, WEISS, outline=None)
    z.d.arc([z.P(45, 49), z.P(55, 55)], 20, 160, fill=WEISS, width=z.lw)


def _pflaume(z, f, t):
    lila, dunkel = (106, 27, 154, 255), (70, 15, 100, 255)
    z.linie([(50, 26), (52, 12)], (110, 80, 50, 255), 2.5)
    z.ell(62, 16, 12, 6, (67, 160, 71, 255), outline=(46, 125, 50, 255), winkel=-25)
    z.ell(50, 56, 28, 30, lila, outline=dunkel)
    z.d.arc([z.P(46, 28), z.P(58, 86)], 100, 260, fill=dunkel, width=z.lw)
    z.ell(38, 44, 5, 8, (200, 150, 230, 180), outline=None, winkel=20)
    for sx in (-1, 1):
        z.ell(50 + sx * 8, 56, 2, 2.6, WEISS, outline=None)
    z.d.arc([z.P(43, 59), z.P(57, 67)], 20, 160, fill=WEISS, width=z.lw)


ZEICHNER.update({"regenbogen": _regenbogen, "blatt": _blatt, "frosch": _frosch, "traube": _traube,
                 "pflaume": _pflaume})
ANIMIERT.update({"regenbogen", "blatt", "frosch"})
HINTERGRUND.update({"regenbogen": (225, 242, 255, 255)})


def _gesicht(z, cx, cy, gr=1.0, farbe=LINIE):
    for sx in (-1, 1):
        z.ell(cx + sx * 7 * gr, cy, 3.2 * gr, 3.8 * gr, WEISS, outline=None)
        z.ell(cx + sx * 7 * gr, cy + 0.6 * gr, 2 * gr, 2.4 * gr, farbe, outline=None)
        z.ell(cx + sx * 12 * gr, cy + 6 * gr, 3 * gr, 1.8 * gr, (255, 140, 160, 150), outline=None)
    z.d.arc([z.P(cx - 5 * gr, cy + 3 * gr), z.P(cx + 5 * gr, cy + 9 * gr)], 20, 160, fill=farbe, width=z.lw + 1)


def _form_farbe(f, standard):
    return f if f else standard


def _kreis(z, f, t):
    farbe = _form_farbe(f, (229, 57, 53, 255))
    s = 1 + 0.04 * math.sin(t * 4)
    z.ell(50, 52, 32 * s, 32 * s, farbe, outline=mischen(farbe, (0, 0, 0, 255), 0.3))
    _gesicht(z, 50, 48, 1.6)


def _dreieck(z, f, t):
    farbe = _form_farbe(f, (67, 160, 71, 255))
    w = math.sin(t * 3) * 4
    c, s_ = math.cos(math.radians(w)), math.sin(math.radians(w))
    ecken = [(50, 18), (82, 78), (18, 78)]
    pts = [(50 + (x - 50) * c - (y - 55) * s_, 55 + (x - 50) * s_ + (y - 55) * c) for x, y in ecken]
    z.poly(pts, farbe, outline=mischen(farbe, (0, 0, 0, 255), 0.3))
    for k, (x, y) in enumerate(pts):  # Ecken leuchten nacheinander auf
        if int(t * 2) % 3 == k:
            z.stern(x, y, 7, (255, 214, 64, 255))
    _gesicht(z, 50, 58, 1.4)


def _viereck(z, f, t):
    farbe = _form_farbe(f, (30, 136, 229, 255))
    w = math.sin(t * 3) * 4
    c, s_ = math.cos(math.radians(w)), math.sin(math.radians(w))
    ecken = [(20, 22), (80, 22), (80, 82), (20, 82)]
    pts = [(50 + (x - 50) * c - (y - 52) * s_, 52 + (x - 50) * s_ + (y - 52) * c) for x, y in ecken]
    z.poly(pts, farbe, outline=mischen(farbe, (0, 0, 0, 255), 0.3))
    for k, (x, y) in enumerate(pts):
        if int(t * 2) % 4 == k:
            z.stern(x, y, 7, (255, 214, 64, 255))
    _gesicht(z, 50, 48, 1.6)


def _formen(z, f, t):
    for k, (fn, x, y, gr) in enumerate([("k", 28, 40, 1), ("d", 70, 36, 1), ("v", 48, 72, 1)]):
        hops = abs(math.sin(t * 4 + k * 1.2)) * 4
        if fn == "k":
            z.ell(x, y - hops, 16, 16, (229, 57, 53, 255), outline=(150, 30, 30, 255))
        elif fn == "d":
            z.poly([(x, y - 18 - hops), (x + 17, y + 13 - hops), (x - 17, y + 13 - hops)], (67, 160, 71, 255),
                   outline=(40, 100, 40, 255))
        else:
            z.poly([(x - 15, y - 15 - hops), (x + 15, y - 15 - hops), (x + 15, y + 15 - hops),
                    (x - 15, y + 15 - hops)], (30, 136, 229, 255), outline=(20, 80, 150, 255))
        _gesicht(z, x, y - hops + (4 if fn == "d" else 0), 0.55)


def _ball(z, f, t):
    hops = abs(math.sin(t * 4)) * 14
    z.ell(50, 88, 22 - hops * 0.5, 4, (0, 0, 0, 50), outline=None)
    cy = 62 - hops
    farben = [(229, 57, 53, 255), (253, 216, 53, 255), (30, 136, 229, 255), WEISS, (67, 160, 71, 255), WEISS]
    for k, farbe in enumerate(farben):
        a0 = k * 60 + t * 90
        pts = [(50, cy)] + [(50 + 24 * math.cos(math.radians(a)), cy + 24 * math.sin(math.radians(a)))
                            for a in range(int(a0), int(a0) + 61, 6)]
        z.poly(pts, farbe, outline=None)
    z.ell(50, cy, 24, 24, None)
    z.ell(42, cy - 9, 5, 3, (255, 255, 255, 180), outline=None, winkel=-30)


def _partyhut(z, f, t):
    z.poly([(50, 12), (76, 84), (24, 84)], (171, 71, 188, 255))
    for k, y in enumerate((34, 52, 70)):
        b = (y - 12) / 72 * 26
        z.poly([(50 - b, y), (50 + b, y), (50 + b + 2, y + 6), (50 - b - 2, y + 6)],
               (253, 216, 53, 255) if k % 2 == 0 else (77, 208, 225, 255), outline=None)
    z.poly([(50, 12), (76, 84), (24, 84)], None)
    for k in range(5):
        a = t * 4 + k * 1.3
        z.ell(50 + math.cos(a) * 6, 10 + math.sin(a) * 3, 3, 3, [(229, 57, 53, 255), (253, 216, 53, 255),
              (30, 136, 229, 255), (67, 160, 71, 255), (255, 112, 67, 255)][k], outline=None)
    z.rrect(20, 82, 80, 88, 3, (255, 214, 64, 255))


def _pizza(z, f, t):
    z.poly([(50, 88), (14, 20), (86, 20)], (255, 213, 128, 255), outline=(200, 140, 60, 255))
    z.poly([(50, 80), (20, 26), (80, 26)], (229, 75, 50, 255), outline=None)
    z.rrect(12, 14, 88, 24, 5, (214, 150, 70, 255), outline=(170, 110, 50, 255))
    for x, y in ((38, 36), (60, 34), (50, 52), (44, 64), (58, 50)):
        z.ell(x, y, 5, 5, (180, 30, 40, 255), outline=(130, 20, 30, 255))
    for x, y in ((30, 30), (68, 40), (52, 70)):
        z.ell(x, y, 2.5, 4, (255, 245, 200, 255), outline=None)


def _fenster(z, f, t):
    z.rrect(16, 14, 84, 84, 3, (161, 110, 70, 255))
    z.rrect(22, 20, 78, 78, 1, (144, 202, 249, 255), outline=(120, 80, 50, 255))
    z.ell(62, 34, 7, 7, (255, 214, 64, 255), outline=None)
    for cx in (34, 50):
        x = cx + math.sin(t * 0.8) * 3
        z.ell(x, 58, 9, 5, WEISS, outline=None)
    z.rrect(48, 20, 52, 78, 0, (161, 110, 70, 255), outline=None)
    z.rrect(22, 47, 78, 51, 0, (161, 110, 70, 255), outline=None)
    w = math.sin(t * 1.5) * 2
    z.poly([(16, 12), (32 + w, 12), (24 + w, 86), (14, 86)], (239, 83, 80, 255))
    z.poly([(84, 12), (68 - w, 12), (76 - w, 86), (86, 86)], (239, 83, 80, 255))
    z.rrect(10, 84, 90, 90, 2, (161, 110, 70, 255))


def _geschenk(z, f, t):
    w = math.sin(t * 5) * 2
    z.rrect(18, 40, 82, 88, 3, (30, 136, 229, 255))
    z.rrect(14, 30 + w * 0.3, 86, 42 + w * 0.3, 3, (66, 165, 245, 255))
    z.rrect(45, 30, 55, 88, 0, (229, 57, 53, 255), outline=None)
    z.rrect(18, 58, 82, 66, 0, (229, 57, 53, 255), outline=None)
    for sx in (-1, 1):
        z.ell(50 + sx * 10, 24 + w * 0.3, 10, 6, (229, 57, 53, 255), winkel=sx * 25)
    z.ell(50, 27 + w * 0.3, 4, 4, (198, 40, 40, 255))
    for k in range(3):
        a = t * 3 + k * 2.1
        z.stern(20 + k * 30, 14 + 3 * math.sin(a), 3.5 * (0.6 + 0.4 * math.sin(a * 2)), (255, 214, 64, 255))


ZEICHNER.update({"kreis": _kreis, "dreieck": _dreieck, "viereck": _viereck, "formen": _formen, "ball": _ball,
                 "partyhut": _partyhut, "pizza": _pizza, "fenster": _fenster, "geschenk": _geschenk})
ANIMIERT.update({"kreis", "dreieck", "viereck", "formen", "ball", "partyhut", "fenster", "geschenk"})
FORMFARBE = {"kreis", "dreieck", "viereck"}


# --- Gute-Nacht-Bilder ----------------------------------------------------

def _schaf_zeichnen(z, cx, cy, s=1.0, t=0.0, augen_zu=True):
    """Kuscheliges Schäfchen (Wolle aus Kreisen, dunkler Kopf)."""
    wolle = (250, 248, 240, 255)
    rand = (170, 160, 150, 255)
    for dx in (-14, 14):
        z.rrect(cx + dx * s - 3 * s, cy + 10 * s, cx + dx * s + 3 * s, cy + 24 * s, 2 * s, (90, 75, 80, 255))
    z.ell(cx, cy + 2 * s, 24 * s, 16 * s, wolle, outline=rand)
    for k in range(10):
        a = math.radians(k * 36)
        z.ell(cx + math.cos(a) * 21 * s, cy + 2 * s + math.sin(a) * 13 * s, 7 * s, 7 * s, wolle, outline=rand)
    z.ell(cx, cy + 2 * s, 20 * s, 12 * s, wolle, outline=None)
    kx, ky = cx - 20 * s, cy - 6 * s
    z.ell(kx - 8 * s, ky - 2 * s, 6 * s, 3 * s, (110, 90, 95, 255), winkel=-25)
    z.ell(kx + 8 * s, ky - 2 * s, 6 * s, 3 * s, (110, 90, 95, 255), winkel=25)
    z.ell(kx, ky + 3 * s, 9 * s, 11 * s, (110, 90, 95, 255))
    for k in range(4):
        z.ell(kx - 6 * s + k * 4 * s, ky - 7 * s, 4 * s, 4 * s, wolle, outline=rand)
    if augen_zu:
        z.d.arc([z.P(kx - 6 * s, ky), z.P(kx - 1 * s, ky + 4 * s)], 20, 160, fill=WEISS, width=z.lw)
        z.d.arc([z.P(kx + 1 * s, ky), z.P(kx + 6 * s, ky + 4 * s)], 20, 160, fill=WEISS, width=z.lw)
    else:
        for ax in (-3.5, 3.5):
            z.ell(kx + ax * s, ky + 2 * s, 2 * s, 2.4 * s, WEISS, outline=None)
            z.ell(kx + ax * s, ky + 2.5 * s, 1.1 * s, 1.4 * s, LINIE, outline=None)
    z.ell(kx - 5.5 * s, ky + 8 * s, 2.2 * s, 1.4 * s, (255, 150, 170, 255), outline=None)
    z.ell(kx + 5.5 * s, ky + 8 * s, 2.2 * s, 1.4 * s, (255, 150, 170, 255), outline=None)


def _kuscheltier(z, f, t):
    """Kuscheltier: ein Schäfchen mit Schleife, das sanft atmet."""
    atem = 1 + 0.03 * math.sin(t * 2)
    z.ell(50, 86, 30, 4, (0, 0, 0, 40), outline=None)
    _schaf_zeichnen(z, 56, 56, 1.25 * atem, t)
    z.ell(36, 66, 5, 3.5, (229, 57, 53, 255), winkel=30)
    z.ell(26, 66, 5, 3.5, (229, 57, 53, 255), winkel=-30)
    z.ell(31, 66, 2.2, 2.2, (198, 40, 40, 255))
    for k in range(2):
        a = (t * 0.6 + k / 2) % 1
        z.stern(76 + 6 * k, 22 - 10 * a, 4 * (1 - a * 0.5), (255, 214, 64, int(255 * (1 - a))))


def _schaf(z, f, t):
    """Schäfchen mit offenen Augen (zum Schäfchen-Zählen), hüpft leicht."""
    hops = abs(math.sin(t * 3)) * 5
    z.ell(50, 88, 26, 4, (0, 0, 0, 40), outline=None)
    _schaf_zeichnen(z, 56, 54 - hops, 1.3, t, augen_zu=False)


def _lampe(z, f, t):
    """Kleines Nachtlicht in Mondform, das warm leuchtet."""
    glanz = 0.8 + 0.2 * math.sin(t * 1.5)
    lay = Image.new("RGBA", z.img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k in range(6, 0, -1):
        r = 14 + k * 5
        d.ellipse([z.P(50 - r, 42 - r), z.P(50 + r, 42 + r)], fill=(255, 220, 120, int(28 * glanz)))
    z.img.alpha_composite(lay)
    z.rrect(30, 74, 70, 84, 4, (121, 134, 203, 255))
    z.rrect(44, 62, 56, 76, 2, (159, 168, 218, 255))
    z.ell(50, 42, 22, 22, (255, 236, 150, 255), outline=(240, 190, 70, 255))
    z.ell(42, 32, 6, 4, (255, 252, 230, 220), outline=None, winkel=-35)
    z.d.arc([z.P(40, 40), z.P(46, 45)], 20, 160, fill=LINIE, width=z.lw)
    z.d.arc([z.P(50, 40), z.P(56, 45)], 20, 160, fill=LINIE, width=z.lw)
    z.d.arc([z.P(44, 47), z.P(52, 52)], 20, 160, fill=LINIE, width=z.lw)
    z.ell(41, 50, 2.5, 1.6, (255, 150, 170, 255), outline=None)
    z.ell(56, 50, 2.5, 1.6, (255, 150, 170, 255), outline=None)


def _buch(z, f, t):
    """Aufgeschlagenes Bilderbuch mit Mond und Stern."""
    blatt = math.sin(t * 1.2) * 3
    z.ell(50, 84, 36, 4, (0, 0, 0, 40), outline=None)
    z.poly([(12, 30), (50, 36), (88, 30), (88, 78), (50, 84), (12, 78)], (30, 136, 229, 255))
    z.poly([(15, 28), (50, 34), (50, 80), (15, 74)], (255, 252, 240, 255))
    z.poly([(50, 34), (85, 28 + blatt), (85, 74 + blatt), (50, 80)], (255, 252, 240, 255))
    z.linie([(50, 34), (50, 80)], LINIE, 1.2)
    lay = Image.new("RGBA", z.img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([z.P(22, 40), z.P(42, 60)], fill=(255, 214, 64, 255))
    d.ellipse([z.P(28, 36), z.P(46, 56)], fill=(0, 0, 0, 0))
    z.img.alpha_composite(lay)
    z.stern(38, 66, 4, (255, 214, 64, 255))
    for k in range(4):
        y = 44 + k * 7 + blatt * (k / 4)
        z.linie([(57, y), (78, y - 1)], (160, 160, 180, 255), 1.6)
    for k in range(3):
        a = t * 2.5 + k * 2.1
        z.stern(26 + k * 24, 16 + 3 * math.sin(a), 3.5 * (0.6 + 0.4 * math.sin(a * 2)), (255, 214, 64, 255))


ZEICHNER.update({"kuscheltier": _kuscheltier, "schaf": _schaf, "lampe": _lampe, "buch": _buch})
ANIMIERT.update({"kuscheltier", "schaf", "lampe", "buch"})
HINTERGRUND.update({"lampe": (40, 53, 107, 255), "kuscheltier": (225, 230, 255, 255)})


# --- Nikolaus-Bilder --------------------------------------------------------

def _nikolaus(z, f, t):
    """Freundlicher Nikolaus: rote Bischofsmütze mit Stern, weißer Bart, lachendes Gesicht."""
    wackel = math.sin(t * 2.5) * 2
    rot, gold = (211, 47, 47, 255), (255, 202, 40, 255)
    # Mütze (Mitra)
    # spitze Bischofsmütze aus zwei Bögen, die sich oben treffen
    spitze = (50 + wackel * 0.3, 5)
    links = [(31 + 19 * (1 - math.cos(math.pi / 2 * k / 10)), 44 - 39 * math.sin(math.pi / 2 * k / 10))
             for k in range(10)]
    rechts = [(100 - x, y) for x, y in reversed(links)]
    z.poly(links + [spitze] + rechts, rot)
    z.poly([(47.5, 44), (47.5, 9), (52.5, 9), (52.5, 44)], gold, outline=None)
    z.poly(links + [spitze] + rechts, None)
    z.rrect(30, 38, 70, 46, 2, gold)
    z.stern(50, 26, 6.5, WEISS)
    # Gesicht
    z.ell(50, 54, 18, 15, HAUT, outline=HAUT_LINIE)
    # Bart (Wolken)
    for x, y, r in ((34, 64, 8), (42, 72, 9), (50, 76, 10), (58, 72, 9), (66, 64, 8), (50, 66, 9)):
        z.ell(x, y, r, r, WEISS, outline=(190, 190, 200, 255))
    z.ell(50, 66, 14, 7, WEISS, outline=None)
    # Schnurrbart + Mund
    z.ell(44, 61, 6, 3, WEISS, outline=(190, 190, 200, 255), winkel=-15)
    z.ell(56, 61, 6, 3, WEISS, outline=(190, 190, 200, 255), winkel=15)
    z.ell(50, 65.5, 3.2, 2.2, (198, 40, 40, 255), outline=None)
    # Augen (fröhlich zugekniffen) und Bäckchen
    for sx in (-1, 1):
        z.d.arc([z.P(50 + sx * 7 - 3, 50), z.P(50 + sx * 7 + 3, 55)], 200, 340, fill=LINIE, width=z.lw)
        z.ell(50 + sx * 12, 57, 3.2, 2, (244, 143, 177, 255), outline=None)
    z.ell(50, 57, 2.6, 2.2, (239, 154, 154, 255), outline=None)
    for k, (x, y) in enumerate(((18, 26), (82, 30))):
        a = t * 3 + k * 2.1
        z.stern(x, y + 3 * math.sin(a), 4 * (0.6 + 0.4 * math.sin(a * 2)), gold)


def _teller(z, f, t):
    """Nikolausteller mit Mandarine, Apfel, Nüssen und Schokoladenstern."""
    z.ell(50, 66, 40, 16, (144, 202, 249, 255), outline=(30, 136, 229, 255))
    z.ell(50, 64, 31, 11, WEISS, outline=None)
    # Nüsse
    for x, y in ((28, 62), (34, 68), (70, 66)):
        z.ell(x, y, 5, 4, (161, 110, 70, 255))
        z.linie([(x - 3, y), (x + 3, y)], (120, 80, 50, 255), 0.8)
    # Apfel
    z.ell(62, 52, 12, 11, (229, 57, 53, 255))
    z.linie([(62, 42), (63, 36)], (121, 85, 72, 255), 1.4)
    z.ell(67, 38, 4, 2, (76, 175, 80, 255), winkel=-30)
    z.ell(58, 48, 3, 2, (255, 255, 255, 140), outline=None)
    # Mandarine
    z.ell(42, 52, 12, 11, (255, 152, 0, 255))
    for k in range(5):
        a = math.radians(k * 72)
        z.ell(42 + math.cos(a) * 6, 52 + math.sin(a) * 5, 0.9, 0.9, (230, 120, 0, 255), outline=None)
    z.ell(42, 41.5, 2.5, 1.6, (76, 175, 80, 255), outline=None)
    # Schokoladenstern
    z.stern(52, 69, 7, (121, 85, 72, 255))
    for k in range(3):
        a = t * 3 + k * 2.1
        z.stern(22 + k * 28, 18 + 3 * math.sin(a), 3.5 * (0.6 + 0.4 * math.sin(a * 2)), (255, 214, 64, 255))


def _herz(z, f, t):
    """Lachendes Herz, das sanft pocht."""
    s = 1 + 0.06 * max(0.0, math.sin(t * 5))
    pts = []
    for k in range(60):
        a = 2 * math.pi * k / 60
        x = 16 * math.sin(a) ** 3
        y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((50 + x * 2.2 * s, 52 + y * 2.2 * s))
    z.poly(pts, (233, 30, 99, 255))
    z.ell(36, 38, 6, 4, (255, 255, 255, 120), outline=None, winkel=-35)
    for sx in (-1, 1):
        z.ell(50 + sx * 9, 48, 2.4, 3, LINIE, outline=None)
        z.ell(50 + sx * 15, 56, 3.5, 2, (248, 187, 208, 255), outline=None)
    z.d.arc([z.P(43, 50), z.P(57, 60)], 20, 160, fill=LINIE, width=z.lw + 1)
    for k in range(3):
        a = t * 3 + k * 2.1
        z.stern(20 + k * 30, 14 + 3 * math.sin(a), 3.5 * (0.6 + 0.4 * math.sin(a * 2)), (255, 214, 64, 255))


ZEICHNER.update({"nikolaus": _nikolaus, "teller": _teller, "herz": _herz})
ANIMIERT.update({"nikolaus", "teller", "herz"})


def schatten(img, farbe=(70, 50, 110)):
    """Schattenbild (Silhouette) für Rätsel: gleiche Form, eine Farbe."""
    a = img.getchannel("A")
    s = Image.new("RGBA", img.size, farbe + (255,))
    s.putalpha(a)
    return s


def bild_sprite(typ, groesse, farbe=None, t=0.0, silhouette=False):
    """Rundes Bild mit Rahmen. farbe = Rahmenfarbe (und Blumenfarbe).
    silhouette=True: Inhalt als einfarbiges Schattenbild (für Rate-Spiele)."""
    f = rgb(farbe) if farbe else None
    z = Zeichner(groesse)
    rahmen = f or (255, 183, 77, 255)
    hg = HINTERGRUND.get(typ, WEISS)
    z.ell(50, 51.5, 47, 47, (0, 0, 0, 45), outline=None)
    z.ell(50, 50, 47, 47, hg, outline=rahmen, breite=int(2.6 * z.u))
    if typ == "sonne":
        s = sonne_sprite(int(z.S * 0.25)).rotate(-t * 20, resample=Image.BICUBIC)
        if silhouette:
            s = schatten(s)
        z.img.alpha_composite(s, ((z.S - s.width) // 2, (z.S - s.height) // 2))
    elif typ in ZEICHNER:
        # Inhalt auf eigene Ebene zeichnen und auf den Kreis beschneiden
        inhalt = Zeichner(groesse)
        ZEICHNER[typ](inhalt, f if typ in ("blume", "fisch") or typ in FORMFARBE else None, t)
        maske = Image.new("L", z.img.size, 0)
        ImageDraw.Draw(maske).ellipse([z.P(4.5, 4.5), z.P(95.5, 95.5)], fill=255)
        alpha = Image.composite(inhalt.img.getchannel("A"), Image.new("L", z.img.size, 0), maske)
        inhalt.img.putalpha(alpha)
        z.img.alpha_composite(schatten(inhalt.img) if silhouette else inhalt.img)
    return z.fertig()


# --- Winter-Bilder -----------------------------------------------------------

def _flocke_zeichnen(z, cx, cy, r, farbe=(144, 202, 249, 255), drehung=0.0, breite=None):
    """Sechsstrahlige Schneeflocke mit kleinen Seitenästen."""
    b = breite or max(1.0, r * 0.09)
    for k in range(6):
        a = math.radians(drehung + k * 60)
        ex, ey = cx + r * math.cos(a), cy + r * math.sin(a)
        z.linie([(cx, cy), (ex, ey)], farbe, b)
        for f in (0.45, 0.7):
            mx, my = cx + r * f * math.cos(a), cy + r * f * math.sin(a)
            for sa in (-40, 40):
                a2 = a + math.radians(sa)
                z.linie([(mx, my), (mx + r * 0.25 * math.cos(a2), my + r * 0.25 * math.sin(a2))], farbe, b * 0.85)
    z.ell(cx, cy, r * 0.14, r * 0.14, farbe, outline=None)


def _schneeflocke(z, f, t):
    """Große Schneeflocke, die sich langsam dreht und glitzert."""
    _flocke_zeichnen(z, 50, 50, 36, (66, 165, 245, 255), drehung=t * 15, breite=3.2)
    _flocke_zeichnen(z, 50, 50, 36, (227, 242, 253, 255), drehung=t * 15, breite=1.2)
    for k in range(3):
        a = t * 3 + k * 2.1
        z.stern(20 + k * 30, 14 + 3 * math.sin(a), 3.5 * (0.6 + 0.4 * math.sin(a * 2)), (255, 214, 64, 255))


def _muetze_zeichnen(z, cx, cy, s, farbe=(229, 57, 53, 255)):
    hell = (255, 255, 255, 255)
    z.poly([(cx - 24 * s, cy + 6 * s), (cx - 20 * s, cy - 14 * s), (cx - 6 * s, cy - 26 * s),
            (cx + 6 * s, cy - 26 * s), (cx + 20 * s, cy - 14 * s), (cx + 24 * s, cy + 6 * s)], farbe)
    for k in range(3):
        y = cy - 18 * s + k * 7 * s
        z.linie([(cx - 18 * s + k * 1.5 * s, y), (cx + 18 * s - k * 1.5 * s, y)], (255, 255, 255, 170), 1.6 * s)
    z.rrect(cx - 26 * s, cy + 2 * s, cx + 26 * s, cy + 12 * s, 4 * s, hell)
    z.ell(cx, cy - 30 * s, 7 * s, 7 * s, hell)


def _schneemann(z, f, t):
    """Lachender Schneemann mit Möhrennase, Mütze und Schal."""
    wackel = math.sin(t * 2) * 1.5
    weiss, rand = (255, 255, 255, 255), (144, 164, 174, 255)
    z.ell(50, 96, 34, 6, (187, 222, 251, 255), outline=None)
    z.ell(50, 78, 22, 17, weiss, outline=rand)
    z.ell(50, 52, 16, 13, weiss, outline=rand)
    z.ell(50 + wackel * 0.2, 31, 12, 11, weiss, outline=rand)
    for y in (48, 56, 74, 82):
        z.ell(50, y, 2.2, 2.2, (55, 71, 79, 255), outline=None)
    # Arme (Zweige)
    braun = (121, 85, 72, 255)
    z.linie([(35, 50), (18, 40 + wackel)], braun, 1.6)
    z.linie([(22, 43 + wackel), (17, 36 + wackel)], braun, 1.2)
    z.linie([(65, 50), (82, 40 - wackel)], braun, 1.6)
    z.linie([(78, 43 - wackel), (84, 36 - wackel)], braun, 1.2)
    # Schal
    z.rrect(37, 40, 63, 45, 2, (30, 136, 229, 255))
    z.poly([(55, 43), (61, 43), (63, 56), (57, 56)], (30, 136, 229, 255))
    # Gesicht
    for sx in (-1, 1):
        z.ell(50 + sx * 4.5 + wackel * 0.2, 28, 1.8, 2.1, LINIE, outline=None)
        z.ell(50 + sx * 7.5 + wackel * 0.2, 33, 2.2, 1.4, (248, 187, 208, 255), outline=None)
    z.poly([(50 + wackel * 0.2, 31), (50 + wackel * 0.2, 34), (61 + wackel * 0.2, 33)], (255, 140, 30, 255))
    z.d.arc([z.P(45 + wackel * 0.2, 33), z.P(55 + wackel * 0.2, 38.5)], 20, 160, fill=LINIE, width=z.lw)
    _muetze_zeichnen(z, 50 + wackel * 0.2, 20, 0.45)
    # fallende Flöckchen
    for k in range(5):
        y = (t * 12 + k * 21) % 90 + 5
        _flocke_zeichnen(z, 12 + k * 19, y, 2.6, (144, 202, 249, 255), breite=0.7)


def _muetze(z, f, t):
    """Rote Bommelmütze."""
    w = math.sin(t * 3) * 2
    z.ell(50, 86, 30, 5, (0, 0, 0, 35), outline=None)
    _muetze_zeichnen(z, 50, 58 + w * 0.3, 1.25)


def _schal(z, f, t):
    """Gestreifter Schal mit Fransen, der im Wind weht."""
    w = math.sin(t * 2.5) * 3
    blau, weiss = (30, 136, 229, 255), (255, 255, 255, 255)
    z.poly([(16, 30), (84, 30), (84, 44), (16, 44)], blau)
    for x in range(24, 84, 12):
        z.poly([(x, 30), (x + 5, 30), (x + 5, 44), (x, 44)], weiss, outline=None)
    z.poly([(16, 30), (84, 30), (84, 44), (16, 44)], None)
    z.poly([(62, 40), (74, 40), (76 + w, 80), (64 + w, 80)], blau)
    for k, y in enumerate(range(48, 78, 8)):
        z.poly([(62.5 + (y - 40) * w / 40 * 0.5, y), (74.5 + (y - 40) * w / 40 * 0.5, y),
                (74.8 + (y - 40) * w / 40 * 0.5, y + 4), (62.8 + (y - 40) * w / 40 * 0.5, y + 4)], weiss, outline=None)
    z.poly([(62, 40), (74, 40), (76 + w, 80), (64 + w, 80)], None)
    for k in range(5):
        x = 64.5 + w + k * 2.6
        z.linie([(x, 80), (x + w * 0.2, 87)], blau, 1.2)


ZEICHNER.update({"schneeflocke": _schneeflocke, "schneemann": _schneemann, "muetze": _muetze, "schal": _schal})
ANIMIERT.update({"schneeflocke", "schneemann", "muetze", "schal"})
HINTERGRUND.update({"schneeflocke": (232, 245, 253, 255), "schneemann": (227, 242, 253, 255)})


def flocke_klein(groesse):
    """Kleine weiße Schneeflocke (für fallenden Schnee im Hintergrund)."""
    z = Zeichner(groesse)
    _flocke_zeichnen(z, 50, 50, 42, (90, 135, 185, 190), breite=10)
    _flocke_zeichnen(z, 50, 50, 42, (255, 255, 255, 245), breite=5.5)
    return z.fertig()


def menge_sprite(objekt, anzahl, groesse, farbe=None, t=0.0):
    """Rundes Bild mit `anzahl` gleichen Dingen zum Mitzählen (für Zähl-Shorts)."""
    basis = bild_sprite("leer", groesse, farbe, t)
    S = basis.width
    reihen = [anzahl] if anzahl <= 2 else [2, 1] if anzahl == 3 else ([anzahl - anzahl // 2, anzahl // 2] if anzahl <= 6
                                         else [anzahl - 2 * (anzahl // 3), anzahl // 3, anzahl // 3])
    feld = int(S * min(0.5, 0.7 / max(reihen), 0.68 / len(reihen)))  # passt immer in den Kreis
    f = rgb(farbe) if farbe else None
    z = Zeichner(feld)
    ZEICHNER[objekt](z, f if objekt in ("blume", "fisch") or objekt in FORMFARBE else None, t)
    ding = z.fertig()
    hoehe = len(reihen) * feld * 0.95
    y = (S - hoehe) / 2
    for n in reihen:
        x = (S - n * feld * 0.95) / 2
        for k in range(n):
            basis.alpha_composite(ding, (int(x + k * feld * 0.95), int(y)))
        y += feld * 0.95
    return basis


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
        if objekt == "punkt":
            z.ell(50, 50, 40, 40, f, outline=mischen(f, (0, 0, 0, 255), 0.25))
            z.ell(38, 38, 11, 11, (255, 255, 255, 150), outline=None)
        elif objekt == "schaf":
            _schaf_zeichnen(z, 56, 50, 1.45, augen_zu=False)
        elif objekt in ZEICHNER and objekt != "moehre":
            ZEICHNER[objekt](z, None, 0.0)
        else:
            _moehre(z, None, 0, x=55, y=50, s=1.2, winkel=-60)
        m = z.fertig().resize((int(feld), int(feld)), Image.LANCZOS)
        for i in range(zahl):
            r, c = divmod(i, 5)
            n_reihe = pro if r == 0 else zahl - 5
            x0 = (B * 2 - 10 - n_reihe * feld) / 2 + c * feld
            y0 = H * (1.05 if reihen == 1 else 0.88) + r * feld * 0.85
            img.alpha_composite(m, (int(x0), int(y0)))
    return img.resize((B, H), Image.LANCZOS)
