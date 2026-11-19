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
import grafik as G  # noqa: E402
import musik as M   # noqa: E402

BASIS = Path(__file__).resolve().parent.parent


def ease_pop(x):
    """0..1 -> Überschwinger-Einblendung."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    return 1 + 2.2 * (x - 1) ** 3 + 1.2 * (x - 1) ** 2


# --------------------------------------------------------------------------
# Audio
# --------------------------------------------------------------------------

def audio_erstellen(lied, tmp):
    M.begleitung_midi(lied, tmp / "begleitung.mid")
    M.begleitung_rendern(tmp / "begleitung.mid", tmp / "begleitung.wav")
    M.gesang_pho(lied, tmp / "gesang.pho")
    M.gesang_rendern(tmp / "gesang.pho", tmp / "gesang_roh.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp / "gesang_roh.wav", "-af",
                    "aresample=44100,highpass=f=110,lowpass=f=9000,"
                    "acompressor=threshold=-20dB:ratio=3:attack=5:release=80,"
                    "aecho=0.8:0.6:45|90:0.22|0.12",
                    tmp / "gesang.wav"], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp / "begleitung.wav", "-i", tmp / "gesang.wav",
                    "-filter_complex",
                    "[0:a]volume=0.75[m];[1:a]volume=1.9[v];[m][v]amix=inputs=2:duration=longest:normalize=0,"
                    f"apad=whole_dur={lied.dauer:.2f},atrim=0:{lied.dauer:.2f},"
                    "afade=t=out:st=%.2f:d=1.2,loudnorm=I=-14:TP=-1.5:LRA=11" % (lied.dauer - 1.2),
                    "-ar", "44100", tmp / "mix.wav"], check=True)


def huellkurve(wav, fps, n_frames):
    """Lautstärke des Gesangs pro Videobild (für Mundbewegung)."""
    with wave.open(str(wav)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
    spf = sr / fps
    env = np.zeros(n_frames, np.float32)
    for i in range(n_frames):
        a, b = int(i * spf), int((i + 1) * spf)
        if a < len(x):
            seg = x[a:b]
            env[i] = math.sqrt(float(np.mean(seg * seg))) if len(seg) else 0
    ref = np.percentile(env[env > 0], 90) if np.any(env > 0) else 1
    env = np.clip(env / ref, 0, 1)
    return env


# --------------------------------------------------------------------------
# Video
# --------------------------------------------------------------------------

class Szene:
    def __init__(self, lied, cfg, kanal, W, H, fps):
        self.lied, self.cfg, self.W, self.H, self.fps = lied, cfg, W, H, fps
        fig = cfg.get("figur", {})
        self.typ = fig.get("typ", "baer")
        self.figur = G.Figur(self.typ, fig.get("farbe"))
        self.fgroesse = int(H * 0.62)
        self.kanal = kanal

        # Paletten je Abschnitt (Refrain immer gleich)
        namen = []
        for a in lied.abschnitte:
            if a[2] not in namen:
                namen.append(a[2])
        self.pal_index = {}
        k = 1
        for n in namen:
            art = next(a[3] for a in lied.abschnitte if a[2] == n)
            if art in ("refrain", "intro", "outro", "zwischenspiel"):
                self.pal_index[n] = 0
            else:
                self.pal_index[n] = k % len(G.PALETTEN)
                k += 1
        verschoben = random.Random(cfg.get("seed", 1)).randrange(len(G.PALETTEN))
        self.bgs = {}
        for i in set(self.pal_index.values()):
            self.bgs[i] = G.hintergrund(W, H, G.PALETTEN[(i + verschoben) % len(G.PALETTEN)])

        self.sonne = G.sonne(int(H * 0.075))
        rng = random.Random(7)
        self.wolken = [(G.wolke(int(W * rng.uniform(0.13, 0.2))), rng.uniform(0, W), H * y, rng.uniform(12, 30) * W / 1920)
                       for y in (0.1, 0.24, 0.05)]
        self.blumen = []
        farben = ["#e53935", "#fbc02d", "#8e24aa", "#1e88e5", "#ff7043", "#ec407a"]
        for i, x in enumerate([0.04, 0.13, 0.36, 0.47, 0.88, 0.96]):
            self.blumen.append((G.blume(int(H * 0.07), farben[i % len(farben)]), W * x, H * (0.74 + 0.03 * (i % 2)), i))
        self.noten = G.noten_sprites(int(H * 0.06))
        akzent = cfg.get("akzent", "#e5398f")
        self.karaoke = G.Karaoke(W, H, akzent)
        self.titel = G.gestapelt([G.text_sprite(z, H * 0.1, G.rgb("#ffffff"), rand=G.rgb(akzent),
                                               randbreite=int(H * 0.012))
                                  for z in _umbruch(cfg.get("kurztitel", cfg["titel"]), 14)])
        self.tschuess = G.text_sprite("Tschüss!", H * 0.13, G.rgb("#ffffff"), rand=G.rgb(akzent),
                                      randbreite=int(H * 0.014))
        self.kanal_sprite = G.text_sprite(kanal, H * 0.035, (255, 255, 255, 230), rand=(0, 0, 0, 90),
                                          randbreite=2)
        # Zeige-Elemente: je Zeile oder je Abschnitt
        self.zeige_zeiten = []  # (start, ende, sprite)
        cache = {}
        for (a0, a1, name, art, teil) in lied.abschnitte:
            if teil.get("zeige"):
                key = json.dumps(teil["zeige"], sort_keys=True)
                cache.setdefault(key, G.zeige_sprite(teil["zeige"], H))
                self.zeige_zeiten.append((lied.sek(a0) - 0.3, lied.sek(a1) - 0.2, cache[key]))
        for z in lied.zeilen:
            if z["zeige"]:
                key = json.dumps(z["zeige"], sort_keys=True)
                cache.setdefault(key, G.zeige_sprite(z["zeige"], H))
                self.zeige_zeiten.append((z["start"] - 0.35, z["ende"] + 0.5, cache[key]))
        # Noten-Partikel bei jedem gesungenen Wortanfang
        rng = random.Random(3)
        self.partikel = []
        for z in lied.zeilen:
            for (w, a, e) in z["woerter"]:
                if a is not None and rng.random() < 0.55:
                    self.partikel.append((a, rng.choice(self.noten), rng.uniform(-0.6, 0.6), rng.uniform(0.8, 1.2)))
        self.erster_gesang = lied.zeilen[0]["start"]
        self.outro_start = lied.sek(next(a[0] for a in lied.abschnitte if a[2] == "outro"))
        self.blink = sorted(random.Random(9).uniform(0, lied.dauer) for _ in range(int(lied.dauer / 3.2)))

    # ---------------------------------------------------------------------
    def abschnitt_bei(self, t):
        beat = t * self.lied.tempo / 60
        akt = self.lied.abschnitte[0]
        for a in self.lied.abschnitte:
            if a[0] <= beat:
                akt = a
        return akt

    def figur_zustand(self, t, mund):
        beat = t * self.lied.tempo / 60
        phase = beat % 1.0
        hupf = abs(math.sin(math.pi * phase))
        blinzeln = any(0 <= t - b < 0.12 for b in self.blink)
        return {
            "mund": mund,
            "blinzeln": blinzeln,
            "arm": math.sin(math.pi * beat / 2) * (0.6 if t > self.erster_gesang - 1 else 0.25),
            "ohr": math.sin(math.pi * beat),
            "fluegel": abs(math.sin(t * 38)),
            "blick": 1.2 * math.sin(t * 0.7),
            "hupf": hupf,
        }

    def bild(self, i, mund):
        W, H = self.W, self.H
        t = i / self.fps
        beat = t * self.lied.tempo / 60
        akt = self.abschnitt_bei(t)
        pal = self.pal_index[akt[2]]
        frame = self.bgs[pal].copy()
        # Übergang zwischen Paletten
        a_start = self.lied.sek(akt[0])
        if t - a_start < 0.6:
            vor = [a for a in self.lied.abschnitte if a[1] <= akt[0] + 1e-6]
            if vor:
                p0 = self.pal_index[vor[-1][2]]
                if p0 != pal:
                    frame = Image.blend(self.bgs[p0], self.bgs[pal], (t - a_start) / 0.6)

        # Sonne
        ang = -t * 12
        s = self.sonne.rotate(ang, resample=Image.BICUBIC)
        frame.paste(s, (int(W * 0.88 - s.width / 2), int(H * 0.17 - s.height / 2)), s)
        # Wolken
        for spr, x0, y, v in self.wolken:
            x = (x0 + t * v) % (W + spr.width) - spr.width
            frame.paste(spr, (int(x), int(y)), spr)
        # Blumen
        for spr, x, y, k in self.blumen:
            dy = -abs(math.sin(math.pi * (beat + k * 0.5) / 2)) * H * 0.012
            frame.paste(spr, (int(x - spr.width / 2), int(y + dy - spr.height * 0.3)), spr)

        # Zeige-Element (links)
        zeige_aktiv = False
        for z0, z1, spr in self.zeige_zeiten:
            if z0 <= t < z1:
                zeige_aktiv = True
                sc = ease_pop((t - z0) / 0.45) * (1 + 0.03 * math.sin(math.pi * beat))
                if t > z1 - 0.25:
                    sc *= max(0.0, (z1 - t) / 0.25)
                if sc > 0.02:
                    w, h = max(1, int(spr.width * sc)), max(1, int(spr.height * sc))
                    sp = spr.resize((w, h), Image.BILINEAR)
                    frame.paste(sp, (int(W * 0.27 - w / 2), int(H * 0.44 - h / 2)), sp)

        # Figur
        z = self.figur_zustand(t, mund)
        text_aktiv = t < self.erster_gesang - 0.2 or t > self.outro_start + 0.3
        ziel = 0.68 if (zeige_aktiv or text_aktiv) else 0.5
        self._fx = ziel if not hasattr(self, "_fx") else self._fx + (ziel - self._fx) * 0.08
        fx = W * self._fx
        S = self.fgroesse
        spr = self.figur.sprite(S, z["mund"], z["blinzeln"], z["arm"], z["ohr"], z["fluegel"], z["blick"])
        if self.typ == "biene":
            fy = H * 0.42 + math.sin(t * 1.7) * H * 0.03
            fx += math.sin(t * 0.9) * W * 0.02
            sw, sh = S, S
        else:
            sq = z["hupf"]
            sw, sh = int(S * (1 + 0.02 * (1 - sq))), int(S * (1 - 0.03 * (1 - sq)))
            fy = H * 0.86 - sh * 0.92 / 2 - sq * H * 0.035
            fy += sh * 0.0
        sp = spr.resize((sw, sh), Image.LANCZOS)
        frame.paste(sp, (int(fx - sw / 2), int(fy - sh / 2)), sp)

        # Noten-Partikel
        for (t0, spr_n, dx, v) in self.partikel:
            alt = t - t0
            if 0 <= alt < 1.8:
                x = fx + S * 0.28 + dx * W * 0.05 * alt + math.sin(alt * 4) * W * 0.008
                y = fy - S * 0.25 - alt * H * 0.18 * v
                a = 1.0 if alt < 1.2 else (1.8 - alt) / 0.6
                if a < 1:
                    n = spr_n.copy()
                    n.putalpha(Image.eval(n.getchannel("A"), lambda p: int(p * a)))
                else:
                    n = spr_n
                frame.paste(n, (int(x), int(y)), n)

        # Titel (Intro) und Tschüss (Outro)
        if t < self.erster_gesang - 0.2:
            sc = ease_pop(t / 0.7) * (1 + 0.025 * math.sin(math.pi * beat))
            rest = self.erster_gesang - 0.2 - t
            if rest < 0.4:
                sc *= rest / 0.4
            self._text(frame, self.titel, sc, W * 0.32, H * 0.42)
        if t > self.outro_start + 0.3:
            sc = ease_pop((t - self.outro_start - 0.3) / 0.7) * (1 + 0.03 * math.sin(math.pi * beat))
            self._text(frame, self.tschuess, sc, W * 0.3, H * 0.42)

        # Karaoke
        self._karaoke(frame, t)
        # Kanalname
        frame.paste(self.kanal_sprite, (int(W * 0.02), int(H * 0.025)), self.kanal_sprite)

        # Ein-/Ausblenden
        if t < 0.5 or t > self.lied.dauer - 1.0:
            f = min(t / 0.5, (self.lied.dauer - t) / 1.0)
            frame = Image.blend(Image.new("RGB", frame.size, (255, 255, 255)), frame, max(0.0, min(1.0, f)))
        return frame

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
        if t > z["ende"] + 1.0 and (naechste is None or naechste["start"] - vor > t):
            return
        sichtbar = [w for (w, a, e) in z["woerter"]]
        # Anzahl hervorgehobener Wörter = bis einschließlich des zuletzt begonnenen Wortes
        k_echt = 0
        for j, (w, a, e) in enumerate(z["woerter"]):
            if a is not None and a <= t:
                k_echt = j + 1
        box = self.karaoke.box
        bx, by = int((W - box.width) / 2), int(H * 0.8)
        frame.paste(box, (bx, by), box)
        sp = self.karaoke.zeile(zi, sichtbar, k_echt)
        frame.paste(sp, (int((W - sp.width) / 2), by + int(box.height * 0.08)), sp)
        if naechste and naechste["abschnitt"] == z["abschnitt"]:
            n = self.karaoke.naechste(zi + 1, naechste["text"])
            frame.paste(n, (int((W - n.width) / 2), by + int(box.height * 0.62)), n)


def vorschaubild(szene, pfad, cfg):
    """Thumbnail 1280x720: Figur groß, Titel groß."""
    W, H = 1280, 720
    bg = G.hintergrund(W, H, G.PALETTEN[random.Random(cfg.get("seed", 1)).randrange(len(G.PALETTEN))])
    bg.paste(szene.sonne.resize((int(H * 0.25), int(H * 0.25))), (int(W * 0.82), int(H * 0.04)),
             szene.sonne.resize((int(H * 0.25), int(H * 0.25))))
    fs = int(H * 0.95)
    fig = szene.figur.sprite(fs, mund=0.75, arm=0.8, fluegel=1.0).resize((fs, fs), Image.LANCZOS)
    bg.paste(fig, (int(W * 0.5), int(H * 0.08)), fig)
    akzent = cfg.get("akzent", "#e5398f")
    zeilen = cfg.get("vorschautext") or _umbruch(cfg.get("kurztitel", cfg["titel"]))
    y = H * 0.18
    for z in zeilen:
        tx = G.text_sprite(z, H * 0.13, G.rgb("#ffffff"), rand=G.rgb(akzent), randbreite=int(H * 0.018))
        if tx.width > W * 0.6:
            f = W * 0.6 / tx.width
            tx = tx.resize((int(tx.width * f), int(tx.height * f)), Image.LANCZOS)
        bg.paste(tx, (int(W * 0.04), int(y)), tx)
        y += tx.height * 0.95
    for t in (sorted(szene.zeige_zeiten, key=lambda x: x[0])[:1] if len(zeilen) <= 2 else []):
        sp = t[2]
        f = H * 0.32 / sp.height
        sp = sp.resize((int(sp.width * f), int(sp.height * f)), Image.LANCZOS)
        bg.paste(sp, (int(W * 0.08), int(H * 0.62)), sp)
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
        teil = cfg["teile"][name]
        zeilen.append(("Refrain:" if teil.get("art") == "refrain" else "Strophe:"))
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
- Veränderte oder synthetische Inhalte: Bei Cartoon-Animation nicht verpflichtend, wir empfehlen "Ja" anzugeben
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
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        print("  • Musik und Gesang …")
        audio_erstellen(lied, tmp)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp / "mix.wav", "-b:a", "192k", ziel / "lied.mp3"],
                       check=True)
        if nur_audio:
            return
        n = int(lied.dauer * fps)
        env = huellkurve(tmp / "gesang_roh.wav", fps, n)
        szene = Szene(lied, cfg, kanal, W, H, fps)
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
            if i % (fps * 10) == 0:
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
    lieder = sorted((BASIS / "songs").glob("*.json")) if a.alle else a.lieder
    if not lieder:
        ap.print_help()
        return
    for l in lieder:
        erstellen(l, a.vorschau, a.nur_audio)


if __name__ == "__main__":
    main()
