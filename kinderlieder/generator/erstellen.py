#!/usr/bin/env python3
"""Erstellt aus einer Lied-Datei (songs/*.json) automatisch ein fertiges YouTube-Video.

    python3 generator/erstellen.py songs/01_bella_biene_farben.json
    python3 generator/erstellen.py --alle
    python3 generator/erstellen.py songs/xyz.json --vorschau     # schnell, kleine Auflösung

Ergebnis in ausgabe/<liedname>/:
    video.mp4, vorschaubild.png, youtube_text.txt, lied.mp3
"""
import argparse
import json
import math
import random
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bilder as BI  # noqa: E402
import grafik as G   # noqa: E402
import musik as M    # noqa: E402

BASIS = Path(__file__).resolve().parent.parent

ZAHLWOERTER = {"null": 0, "eins": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6,
               "sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12}


def ease_pop(x):
    """0..1 -> Einblendung mit kleinem Überschwinger."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    return 1 + 2.2 * (x - 1) ** 3 + 1.2 * (x - 1) ** 2


# --------------------------------------------------------------------------
# Einblendungen planen (Bilder, Zahlen)
# --------------------------------------------------------------------------

def anzeigen_planen(lied):
    """Liste von Einblendungen: {start, ende, typ ('bild'|'zahl'), wert, farbe, wort, landen}."""
    res = []
    abschn_ende = {}
    for a0, a1, name, art, teil in lied.abschnitte:
        abschn_ende[name] = lied.sek(a1)
    zeilen = lied.zeilen
    for i, z in enumerate(zeilen):
        teil, info = z["teil"], z["info"]
        naechste = zeilen[i + 1] if i + 1 < len(zeilen) else None
        gleich = naechste is not None and naechste["abschnitt"] == z["abschnitt"]
        ende = (naechste["start"] - 0.35) if gleich else z["ende"] + 0.9
        farbe = info.get("farbe", teil.get("farbe"))
        if teil.get("zahlen"):
            zahlen = [(ZAHLWOERTER[M.wort_sauber(w).lower()], a) for (w, a, e) in z["woerter"]
                      if a is not None and M.wort_sauber(w).lower() in ZAHLWOERTER]
            for k, (n, a) in enumerate(zahlen):
                e2 = zahlen[k + 1][1] - 0.02 if k + 1 < len(zahlen) else ende
                res.append({"start": a - 0.08, "ende": e2, "typ": "zahl", "wert": n,
                            "farbe": farbe or "#43a047", "wort": None, "landen": False})
            continue
        bild = info.get("bild", teil.get("bild"))
        if not bild:
            continue
        neu = {"start": z["start"] - 0.35, "ende": ende, "typ": "bild", "wert": bild, "farbe": farbe,
               "wort": teil.get("wort"), "landen": bool(info.get("landen"))}
        alt = res[-1] if res else None
        if alt and alt["typ"] == "bild" and alt["wert"] == bild and abs(alt["ende"] - neu["start"]) < 0.5:
            alt["ende"] = neu["ende"]  # gleiches Bild weiter zeigen
        else:
            res.append(neu)
    return res


# --------------------------------------------------------------------------
# Audio
# --------------------------------------------------------------------------

def audio_erstellen(lied, anzeigen, tmp):
    M.begleitung_midi(lied, tmp / "begleitung.mid")
    M.begleitung_rendern(tmp / "begleitung.mid", tmp / "begleitung.wav")
    M.stimme_pho(lied, tmp / "stimme.pho")
    M.stimme_rendern(tmp / "stimme.pho", tmp / "stimme_roh.wav")
    effekte = list(lied.effekte) + [(a["start"] + 0.05, "plopp") for a in anzeigen]
    M.effekte_rendern(effekte, lied.dauer, tmp / "effekte.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp / "stimme_roh.wav", "-af",
                    "highpass=f=130,lowpass=f=10000,"
                    "equalizer=f=3200:t=o:w=1.4:g=4,equalizer=f=350:t=o:w=1:g=-2,"
                    "acompressor=threshold=-22dB:ratio=3:attack=4:release=90:makeup=2,"
                    "aecho=0.85:0.5:35:0.12",
                    tmp / "stimme.wav"], check=True)
    d = lied.dauer
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp / "begleitung.wav", "-i", tmp / "stimme.wav",
                    "-i", tmp / "effekte.wav", "-filter_complex",
                    "[1:a]aresample=44100,asplit=2[v1][v2];"
                    "[0:a]volume=0.8[m0];"
                    "[m0][v1]sidechaincompress=threshold=0.04:ratio=3:attack=15:release=350:makeup=1[m];"
                    "[v2]volume=2.0[v];[2:a]aresample=44100,volume=0.9[fx];"
                    "[m][v][fx]amix=inputs=3:duration=longest:normalize=0,"
                    f"apad=whole_dur={d:.2f},atrim=0:{d:.2f},"
                    f"afade=t=out:st={d - 1.2:.2f}:d=1.2,loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-ar", "44100", "-ac", "2", tmp / "mix.wav"], check=True)


def huellkurve(wav, fps, n_frames):
    """Lautstärke der Stimme pro Videobild (für die Mundbewegung)."""
    with wave.open(str(wav)) as w:
        sr = w.getframerate()
        kan = w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
    if kan > 1:
        x = x.reshape(-1, kan).mean(axis=1)
    spf = sr / fps
    env = np.zeros(n_frames, np.float32)
    for i in range(n_frames):
        a, b = int(i * spf), int((i + 1) * spf)
        if a < len(x):
            seg = x[a:b]
            env[i] = math.sqrt(float(np.mean(seg * seg))) if len(seg) else 0
    ref = np.percentile(env[env > 0], 90) if np.any(env > 0) else 1
    return np.clip(env / ref, 0, 1)


# --------------------------------------------------------------------------
# Video
# --------------------------------------------------------------------------

class Szene:
    def __init__(self, lied, cfg, kanal, anzeigen, W, H, fps):
        self.lied, self.cfg, self.W, self.H, self.fps = lied, cfg, W, H, fps
        self.anzeigen = anzeigen
        fig = cfg.get("figur", {})
        self.typ = fig.get("typ", "baer")
        self.figur = G.Figur(self.typ, fig.get("farbe"))
        self.fgroesse = int(H * 0.62)
        self.bildgroesse = int(H * 0.46)

        # Hintergründe: Refrain/Sprechen = Grundpalette, Strophen wechseln, Nacht-Abschnitte dunkel
        verschoben = random.Random(cfg.get("titel", "")).randrange(len(G.PALETTEN))
        self.pal = {}
        k = 1
        for a0, a1, name, art, teil in lied.abschnitte:
            if name in self.pal:
                continue
            if teil.get("nacht"):
                self.pal[name] = "nacht"
            elif art == "strophe":
                self.pal[name] = (verschoben + k) % len(G.PALETTEN)
                k += 1
            else:
                self.pal[name] = verschoben
        self.bgs = {}
        for p in set(self.pal.values()):
            self.bgs[p] = G.hintergrund(W, H, G.NACHT if p == "nacht" else G.PALETTEN[p])

        self.sonne = G.sonne(int(H * 0.075))
        self.mond = G.mond(int(H * 0.08))
        rng = random.Random(7)
        self.sterne = [(G.stern(int(H * rng.uniform(0.008, 0.016))), W * rng.uniform(0.02, 0.98),
                        H * rng.uniform(0.03, 0.55), rng.uniform(0, 6)) for _ in range(28)]
        self.wolken = [(G.wolke(int(W * rng.uniform(0.13, 0.2))), rng.uniform(0, W), H * y,
                        rng.uniform(12, 30) * W / 1920) for y in (0.1, 0.24, 0.05)]
        self.blumen_pos = [(W * x, H * (0.74 + 0.03 * (i % 2)), i)
                           for i, x in enumerate([0.04, 0.13, 0.36, 0.47, 0.88, 0.96])]
        self.blumen_farben = ["#e53935", "#fbc02d", "#8e24aa", "#1e88e5", "#ff7043", "#ec407a"]
        self.blumen_cache = {}
        self.noten = G.noten_sprites(int(H * 0.06))
        akzent = cfg.get("akzent", "#e5398f")
        self.karaoke = G.Karaoke(W, H, akzent)
        self.titel = G.gestapelt([G.text_sprite(z, H * 0.1, G.rgb("#ffffff"), rand=G.rgb(akzent),
                                                randbreite=int(H * 0.012))
                                  for z in _umbruch(cfg.get("kurztitel", cfg["titel"]), 14)])
        self.tschuess = G.text_sprite("Tschüss!", H * 0.13, G.rgb("#ffffff"), rand=G.rgb(akzent),
                                      randbreite=int(H * 0.014))
        self.kanal_sprite = G.text_sprite(kanal, H * 0.035, (255, 255, 255, 230), rand=(0, 0, 0, 90),
                                          randbreite=2) if kanal else None
        self.buerste = G.zahnbuerste_klein(int(self.fgroesse * 0.42))
        self.blasen = {}
        self.statisch = {}
        self.wort_cache = {}
        rng = random.Random(3)
        self.partikel = []
        for z in lied.zeilen:
            for (w, a, e) in z["woerter"]:
                if a is not None and rng.random() < 0.5:
                    self.partikel.append((a, rng.choice(self.noten), rng.uniform(-0.6, 0.6), rng.uniform(0.8, 1.2)))
        self.intro_ende = lied.sek(16)
        self.outro_start = lied.sek(next(a[0] for a in lied.abschnitte if a[2] == "outro"))
        self.blink = sorted(random.Random(9).uniform(0, lied.dauer) for _ in range(int(lied.dauer / 3.2)))
        self._fx, self._fy = None, None

    # ---------------------------------------------------------------------
    def abschnitt_bei(self, t):
        beat = self.lied.beat(t)
        akt = self.lied.abschnitte[0]
        for a in self.lied.abschnitte:
            if a[0] <= beat + 1e-6:
                akt = a
        return akt

    def blume(self, farbe):
        if farbe not in self.blumen_cache:
            self.blumen_cache[farbe] = G.blume(int(self.H * 0.07), farbe)
        return self.blumen_cache[farbe]

    def bild_fuer(self, a, t):
        if a["typ"] == "zahl":
            key = ("zahl", a["wert"], a["farbe"])
            if key not in self.statisch:
                self.statisch[key] = BI.zahl_sprite(a["wert"], int(self.H * 0.42), a["farbe"])
            return self.statisch[key]
        typ = a["wert"]
        if typ in BI.ANIMIERT or typ == "sonne":
            spr = BI.bild_sprite(typ, self.bildgroesse, a["farbe"], t)
        else:
            key = (typ, a["farbe"])
            if key not in self.statisch:
                self.statisch[key] = BI.bild_sprite(typ, self.bildgroesse, a["farbe"], t)
            spr = self.statisch[key]
        if a.get("wort"):
            key = ("wort", a["wort"], a["farbe"])
            if key not in self.wort_cache:
                self.wort_cache[key] = G.text_sprite(a["wort"], self.H * 0.09, G.rgb(a["farbe"] or "#e5398f"),
                                                     randbreite=int(self.H * 0.012))
            ws = self.wort_cache[key]
            img = Image.new("RGBA", (max(spr.width, ws.width), spr.height + int(ws.height * 0.8)), (0, 0, 0, 0))
            img.alpha_composite(spr, ((img.width - spr.width) // 2, 0))
            img.alpha_composite(ws, ((img.width - ws.width) // 2, img.height - ws.height))
            return img
        return spr

    def bild(self, i, mund):
        W, H = self.W, self.H
        t = i / self.fps
        beat = self.lied.beat(t)
        akt = self.abschnitt_bei(t)
        teil = akt[4]
        pal = self.pal[akt[2]]
        frame = self.bgs[pal].copy()
        a_start = self.lied.sek(akt[0])
        if t - a_start < 0.8:
            vor = [a for a in self.lied.abschnitte if a[1] <= akt[0] + 1e-6]
            if vor:
                p0 = self.pal[vor[-1][2]]
                if p0 != pal:
                    frame = Image.blend(self.bgs[p0], self.bgs[pal], (t - a_start) / 0.8)
        nacht = pal == "nacht"

        # Himmel
        if nacht:
            for spr, x, y, ph in self.sterne:
                if 0.5 + 0.5 * math.sin(t * 2.5 + ph) > 0.25:
                    frame.paste(spr, (int(x), int(y)), spr)
            frame.paste(self.mond, (int(W * 0.88 - self.mond.width / 2), int(H * 0.17 - self.mond.height / 2)),
                        self.mond)
        else:
            s = self.sonne.rotate(-t * 12, resample=Image.BICUBIC)
            frame.paste(s, (int(W * 0.88 - s.width / 2), int(H * 0.17 - s.height / 2)), s)
            for spr, x0, y, v in self.wolken:
                x = (x0 + t * v) % (W + spr.width) - spr.width
                frame.paste(spr, (int(x), int(y)), spr)
        # Blumen (nehmen in Farb-Strophen die Strophenfarbe an)
        for x, y, k in self.blumen_pos:
            spr = self.blume(teil.get("farbe") if teil.get("wort") and not teil.get("nacht")
                             else self.blumen_farben[k])
            dy = -abs(math.sin(math.pi * (beat + k * 0.5) / 2)) * H * 0.012
            frame.paste(spr, (int(x - spr.width / 2), int(y + dy - spr.height * 0.3)), spr)

        # Einblendung links
        aktiv = None
        bx, by = W * 0.27, H * 0.44
        for a in self.anzeigen:
            if a["start"] <= t < a["ende"]:
                aktiv = a
                spr = self.bild_fuer(a, t)
                sc = ease_pop((t - a["start"]) / 0.45) * (1 + 0.025 * math.sin(math.pi * beat))
                if t > a["ende"] - 0.25:
                    sc *= max(0.0, (a["ende"] - t) / 0.25)
                if sc > 0.02:
                    w, h = max(1, int(spr.width * sc)), max(1, int(spr.height * sc))
                    sp = spr.resize((w, h), Image.BILINEAR)
                    frame.paste(sp, (int(bx - w / 2), int(by - h / 2)), sp)

        # Sprechblase aktiv?
        sprech = next((sp for sp in self.lied.sprache if sp["start"] - 0.15 <= t < sp["ende"] + 0.7), None)

        # Figur – Position
        S = self.fgroesse
        text_aktiv = t < self.intro_ende - 0.2 or (t > self.outro_start + 0.3 and not sprech)
        ziel_x = 0.68 if (aktiv or text_aktiv) else 0.5
        if sprech:
            ziel_x = 0.62
        ziel_y = None
        if aktiv and aktiv.get("landen") and self.typ == "biene":
            ziel_x, ziel_y = 0.39, 0.33
        if self._fx is None:
            self._fx, self._fy = ziel_x, ziel_y or 0
        self._fx += (ziel_x - self._fx) * 0.07
        z = self.figur_zustand(t, mund, sprech is not None)
        spr = self.figur.sprite(S, z["mund"], z["blinzeln"], z["arm"], z["ohr"], z["fluegel"], z["blick"])
        fx = W * self._fx
        if self.typ == "biene":
            normal_y = 0.42 + math.sin(t * 1.7) * 0.03
            ziel = ziel_y if ziel_y is not None else normal_y
            self._fy = self._fy + (ziel - self._fy) * 0.07 if self._fy else ziel
            fy = H * self._fy
            if ziel_y is None:
                fx += math.sin(t * 0.9) * W * 0.02
            sw, sh = S, S
            if ziel_y is not None:
                sw = sh = int(S * 0.8)
        else:
            sq = z["hupf"]
            sw, sh = int(S * (1 + 0.02 * (1 - sq))), int(S * (1 - 0.03 * (1 - sq)))
            fy = H * 0.86 - sh * 0.92 / 2 - sq * H * 0.035
        sp = spr.resize((sw, sh), Image.LANCZOS)
        x0, y0 = int(fx - sw / 2), int(fy - sh / 2)
        frame.paste(sp, (x0, y0), sp)
        # Zahnbürste in der Hand beim Putzen
        if teil.get("putzen"):
            br = self.buerste
            mx = x0 + sw * 0.5 + math.sin(t * 14) * sw * 0.05 - br.width * 0.06
            my = y0 + sh * 0.565 - br.height * 0.55
            frame.paste(br, (int(mx), int(my)), br)

        # Noten-Partikel
        for (t0, spr_n, dx, v) in self.partikel:
            alt = t - t0
            if 0 <= alt < 1.8:
                x = fx + sw * 0.28 + dx * W * 0.05 * alt + math.sin(alt * 4) * W * 0.008
                y = fy - sh * 0.25 - alt * H * 0.18 * v
                a = 1.0 if alt < 1.2 else (1.8 - alt) / 0.6
                n = spr_n
                if a < 1:
                    n = spr_n.copy()
                    n.putalpha(Image.eval(n.getchannel("A"), lambda p: int(p * a)))
                frame.paste(n, (int(x), int(y)), n)

        # Titel (Intro) und Tschüss (Outro)
        if t < self.intro_ende - 0.2:
            sc = ease_pop(t / 0.7) * (1 + 0.025 * math.sin(math.pi * beat))
            rest = self.intro_ende - 0.2 - t
            if rest < 0.4:
                sc *= rest / 0.4
            self._text(frame, self.titel, sc, W * 0.32, H * 0.42)
        if t > self.outro_start + 0.3 and not sprech:
            sc = ease_pop((t - self.outro_start - 0.3) / 0.7) * (1 + 0.03 * math.sin(math.pi * beat))
            self._text(frame, self.tschuess, sc, W * 0.3, H * 0.42)

        # Sprechblase
        if sprech:
            key = sprech["text"]
            if key not in self.blasen:
                self.blasen[key] = G.sprechblase(key, H)
            bl = self.blasen[key]
            sc = ease_pop((t - sprech["start"] + 0.15) / 0.35)
            if t > sprech["ende"] + 0.45:
                sc *= max(0.0, (sprech["ende"] + 0.7 - t) / 0.25)
            if sc > 0.02:
                w, h = int(bl.width * sc), int(bl.height * sc)
                b = bl.resize((max(1, w), max(1, h)), Image.BILINEAR)
                rx = fx - sw * 0.22
                ry = fy - sh * 0.12
                frame.paste(b, (int(max(W * 0.02, rx - w)), int(max(H * 0.03, ry - h))), b)

        self._karaoke(frame, t)
        if self.kanal_sprite:
            frame.paste(self.kanal_sprite, (int(W * 0.02), int(H * 0.025)), self.kanal_sprite)

        if t < 0.5 or t > self.lied.dauer - 1.0:
            f = min(t / 0.5, (self.lied.dauer - t) / 1.0)
            frame = Image.blend(Image.new("RGB", frame.size, (255, 255, 255)), frame, max(0.0, min(1.0, f)))
        return frame

    def figur_zustand(self, t, mund, spricht):
        beat = self.lied.beat(t)
        hupf = abs(math.sin(math.pi * (beat % 1.0)))
        if spricht:
            hupf = 1 - 0.3 * abs(math.sin(math.pi * t * 1.2))
        return {
            "mund": mund,
            "blinzeln": any(0 <= t - b < 0.12 for b in self.blink),
            "arm": (math.sin(t * 9) * 0.8 + 0.4) if spricht else math.sin(math.pi * beat / 2) * 0.6,
            "ohr": math.sin(math.pi * beat),
            "fluegel": abs(math.sin(t * 38)),
            "blick": 1.2 * math.sin(t * 0.7),
            "hupf": hupf,
        }

    def _text(self, frame, spr, sc, cx, cy):
        if sc <= 0.02:
            return
        w, h = max(1, int(spr.width * sc)), max(1, int(spr.height * sc))
        sp = spr.resize((w, h), Image.BILINEAR)
        frame.paste(sp, (int(cx - w / 2), int(cy - h / 2)), sp)

    def _karaoke(self, frame, t):
        W, H = self.W, self.H
        zeilen = self.lied.zeilen
        vor = 60.0 / self.lied.tempo * 1.5
        zi = None
        for i, z in enumerate(zeilen):
            if z["start"] - vor <= t:
                zi = i
        if zi is None:
            return
        z = zeilen[zi]
        naechste = zeilen[zi + 1] if zi + 1 < len(zeilen) else None
        if t > z["ende"] + 0.8 and (naechste is None or naechste["start"] - vor > t):
            return
        sichtbar = [w for (w, a, e) in z["woerter"]]
        k = 0
        for j, (w, a, e) in enumerate(z["woerter"]):
            if a is not None and a <= t:
                k = j + 1
        box = self.karaoke.box
        bx, by = int((W - box.width) / 2), int(H * 0.8)
        frame.paste(box, (bx, by), box)
        sp = self.karaoke.zeile(zi, sichtbar, k)
        frame.paste(sp, (int((W - sp.width) / 2), by + int(box.height * 0.08)), sp)
        if naechste and naechste["abschnitt"] == z["abschnitt"]:
            n = self.karaoke.naechste(zi + 1, naechste["text"])
            frame.paste(n, (int((W - n.width) / 2), by + int(box.height * 0.62)), n)


def vorschaubild(szene, pfad, cfg):
    """Thumbnail 1280x720: Figur groß, Titel groß, Bilder aus dem Lied."""
    W, H = 1280, 720
    bg = G.hintergrund(W, H, G.PALETTEN[random.Random(cfg.get("titel", "")).randrange(len(G.PALETTEN))])
    s = szene.sonne.resize((int(H * 0.25), int(H * 0.25)))
    bg.paste(s, (int(W * 0.82), int(H * 0.04)), s)
    fs = int(H * 0.95)
    fig = szene.figur.sprite(fs, mund=0.75, arm=0.8, fluegel=1.0).resize((fs, fs), Image.LANCZOS)
    bg.paste(fig, (int(W * 0.5), int(H * 0.08)), fig)
    akzent = cfg.get("akzent", "#e5398f")
    zeilen = cfg.get("vorschautext") or _umbruch(cfg.get("kurztitel", cfg["titel"]))
    y = H * 0.06
    for z in zeilen:
        tx = G.text_sprite(z, H * 0.12, G.rgb("#ffffff"), rand=G.rgb(akzent), randbreite=int(H * 0.018))
        if tx.width > W * 0.56:
            f = W * 0.56 / tx.width
            tx = tx.resize((int(tx.width * f), int(tx.height * f)), Image.LANCZOS)
        bg.paste(tx, (int(W * 0.04), int(y)), tx)
        y += tx.height * 0.92
    # bis zu drei Bilder aus dem Lied unten links
    gezeigt, x = [], W * 0.03
    for a in szene.anzeigen:
        key = (a["typ"], a["wert"])
        if key in gezeigt or len(gezeigt) >= 3:
            continue
        gezeigt.append(key)
        if a["typ"] == "zahl":
            sp = BI.zahl_sprite(a["wert"], int(H * 0.22), a["farbe"])
        else:
            sp = BI.bild_sprite(a["wert"], int(H * 0.25), a["farbe"], 1.0)
        bg.paste(sp, (int(x), int(H * 0.72)), sp)
        x += sp.width + W * 0.012
    bg.save(pfad)


def _umbruch(text, max_zeichen=13):
    woerter, zeilen, akt = text.replace(",", "").split(), [], ""
    for w in woerter:
        if len(akt) + len(w) + 1 > max_zeichen and akt:
            zeilen.append(akt)
            akt = w
        else:
            akt = (akt + " " + w).strip()
    zeilen.append(akt)
    return zeilen


def youtube_text(cfg, kanal_cfg, lied, pfad):
    titel = f"{cfg['titel']} | Kinderlied zum Mitsingen"
    zeilen = []
    for name in cfg["ablauf"]:
        if isinstance(name, dict):
            continue
        teil = cfg["teile"][name]
        zeilen.append("Refrain:" if teil.get("art") == "refrain" else "Strophe:")
        zeilen += [M._zeilentext(z) for z in teil["zeilen"]]
        zeilen.append("")
    tags = cfg.get("tags", [])
    hashtags = " ".join("#" + t.replace(" ", "") for t in tags[:3])
    text = f"""TITEL
{titel[:100]}

BESCHREIBUNG
{cfg.get('beschreibung', '')}

🎵 Liedtext zum Mitsingen:

{chr(10).join(zeilen)}
{kanal_cfg.get('hinweis_ki', '')}

{hashtags}

TAGS (kommagetrennt)
{', '.join(tags)}

EINSTELLUNGEN BEIM HOCHLADEN
- Zielgruppe: "Ja, er ist speziell für Kinder" (Made for Kids)
- Veränderte oder synthetische Inhalte: bei Cartoon-Animation nicht verpflichtend, "Ja" angeben ist trotzdem empfehlenswert
- Kategorie: Bildung oder Musik
- Sprache: Deutsch
- Länge: {int(lied.dauer // 60)}:{int(lied.dauer % 60):02d} min
"""
    Path(pfad).write_text(text)


def erstellen(song_pfad, vorschau=False, nur_audio=False):
    song_pfad = Path(song_pfad)
    cfg = json.loads(song_pfad.read_text())
    kanal_cfg = json.loads((BASIS / "kanal.json").read_text()) if (BASIS / "kanal.json").exists() else {}
    kanal = kanal_cfg.get("kanalname", "")
    ziel = BASIS / "ausgabe" / song_pfad.stem
    ziel.mkdir(parents=True, exist_ok=True)
    W, H, fps = (640, 360, 20) if vorschau else (1920, 1080, 30)
    t0 = time.time()
    print(f"▶ {cfg['titel']}")
    lied = M.Lied(cfg)
    anzeigen = anzeigen_planen(lied)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        print("  • Musik, Stimme und Geräusche …")
        audio_erstellen(lied, anzeigen, tmp)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp / "mix.wav", "-b:a", "192k", ziel / "lied.mp3"],
                       check=True)
        if nur_audio:
            subprocess.run(["cp", tmp / "stimme.wav", ziel / "nur_stimme.wav"], check=True)
            return
        n = int(lied.dauer * fps)
        env = huellkurve(tmp / "stimme.wav", fps, n)
        szene = Szene(lied, cfg, kanal, anzeigen, W, H, fps)
        vorschaubild(szene, ziel / "vorschaubild.png", cfg)
        youtube_text(cfg, kanal_cfg, lied, ziel / "youtube_text.txt")
        print(f"  • Animation ({n} Bilder, {W}x{H}) …")
        ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-i", str(tmp / "mix.wav"),
                               "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                               "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                               str(ziel / ("vorschau.mp4" if vorschau else "video.mp4"))], stdin=subprocess.PIPE)
        mund = 0.0
        for i in range(n):
            mund = max(env[i], mund * 0.6)
            ff.stdin.write(szene.bild(i, float(mund)).tobytes())
            if i % (fps * 20) == 0:
                print(f"    {i / fps:5.0f}s / {lied.dauer:.0f}s", flush=True)
        ff.stdin.close()
        ff.wait()
    print(f"  ✔ fertig in {time.time() - t0:.0f}s → {ziel}")


def main():
    ap = argparse.ArgumentParser(description="Kinderlied-Video automatisch erstellen")
    ap.add_argument("lieder", nargs="*", help="Pfad(e) zu songs/*.json")
    ap.add_argument("--alle", action="store_true", help="alle Lieder in songs/ erstellen")
    ap.add_argument("--vorschau", action="store_true", help="schnelle Vorschau in kleiner Auflösung")
    ap.add_argument("--nur-audio", action="store_true", help="nur das Lied (mp3) erzeugen")
    a = ap.parse_args()
    lieder = sorted((BASIS / "songs").glob("[0-9]*.json")) if a.alle else a.lieder
    if not lieder:
        ap.print_help()
        return
    for l in lieder:
        erstellen(l, a.vorschau, a.nur_audio)


if __name__ == "__main__":
    main()
