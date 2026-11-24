#!/usr/bin/env python3
"""YouTube-Shorts im "Rate mal!"-Format (hochkant 1440x2560 bzw. 1080x1920, unter 60 Sekunden).

Ablauf pro Rätsel: Schattenbild erscheint -> Figur fragt -> Countdown 3-2-1 -> bunte Auflösung
mit Konfetti und Tusch -> Figur sagt die Antwort. Das Ende geht nahtlos in den Anfang über (Loop).

    python3 generator/short.py shorts/01_rate_mal_essen.json
    python3 generator/short.py --alle
"""
import argparse
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import mido
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bilder as BI      # noqa: E402
import erstellen as E    # noqa: E402
import grafik as G       # noqa: E402
import musik as M        # noqa: E402
import technik as T       # noqa: E402
import elevenlabs as EL   # noqa: E402
import youtube_meta as YM  # noqa: E402

BASIS = Path(__file__).resolve().parent.parent
W, H = T.groesse_hoch()
FPS = 30
TICK = 0.8  # Sekunden pro Countdown-Zahl


# --------------------------------------------------------------------------
# Ablauf planen
# --------------------------------------------------------------------------

def planen(cfg, el_ordner=None):
    """el_ordner gesetzt: Sprechstimme von ElevenLabs (wird dort zwischengespeichert), sonst MBROLA."""
    tempo = cfg.get("sprechtempo", 150)
    fragen = cfg.get("fragen", ["Was ist das?", "Und das hier?", "Und jetzt?", "Weißt du es?", "Und das?"])
    t = 0.15
    dinge, sprache, effekte = [], [], []
    stimme = EL.stimme_fuer(cfg) if el_ordner else None
    if el_ordner:
        Path(el_ordner).mkdir(parents=True, exist_ok=True)

    def sprich(text, start):
        if el_ordner:
            wav, dauer = EL.sprechen(text, stimme, el_ordner)
            sprache.append({"start": start, "ende": start + dauer, "text": text, "wav": wav})
            return start + dauer
        pho = M.sprache_pho(text, tempo)
        dauer = sum(d for _, d, _ in pho) / 1000.0
        sprache.append({"start": start, "ende": start + dauer, "text": text, "pho": pho})
        return start + dauer

    for i, d in enumerate(cfg["dinge"]):
        frage = d.get("frage") or (cfg.get("start", "Rate mal! Was ist das?") if i == 0
                                   else fragen[(i - 1) % len(fragen)])
        effekte.append((t, "wusch"))
        q_ende = sprich(frage, t + 0.1)
        if d.get("geraeusch"):  # z. B. Tiergeräusch nach der Frage
            effekte.append((q_ende + 0.05, d["geraeusch"]))
            q_ende += 0.7
        cd = q_ende + 0.25
        for k in range(3):
            effekte.append((cd + k * TICK, "tick"))
        aufl = cd + 3 * TICK
        effekte += [(aufl, "tada"), (aufl + 0.05, "glitzer")]
        a_ende = sprich(d["antwort"], aufl + 0.3)
        ende = a_ende + 0.7
        dinge.append({**d, "start": t, "countdown": cd, "aufloesung": aufl, "ende": ende})
        t = ende
    schluss = t
    s_ende = sprich(cfg.get("ende", "Wie viele hast du erraten?"), schluss + 0.1)
    dauer = s_ende + 1.2
    return {"dinge": dinge, "sprache": sprache, "effekte": effekte, "schluss": schluss, "dauer": dauer}


# --------------------------------------------------------------------------
# Musik: fröhliche Schleife I-V-vi-IV
# --------------------------------------------------------------------------

def musik_midi(cfg, dauer, pfad):
    tempo = cfg.get("tempo", 116)
    g = M.TONARTEN.get(cfg.get("tonart", "C"), 60)
    tpb = 480
    ev = []

    def note(k, b, l, m, v):
        a, e = int(b * tpb), int((b + l) * tpb)
        ev.append((a, 1, mido.Message("note_on", channel=k, note=int(m), velocity=int(v))))
        ev.append((max(a + 1, e), 0, mido.Message("note_off", channel=k, note=int(m), velocity=0)))
    ev += [(0, 0, mido.Message("program_change", channel=0, program=M.INSTRUMENTE.get(cfg.get("instrument", "glockenspiel"), 9))),
           (0, 0, mido.Message("program_change", channel=1, program=0)),
           (0, 0, mido.Message("program_change", channel=2, program=32)),
           (0, 0, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo)))]
    folge = ["I", "V", "VI", "IV"]
    takte = int(dauer * tempo / 60 / 4) + 2
    for k in range(takte):
        b = 4 * k
        r = M.STUFEN[folge[k % 4]]
        akk = [M.stufe_zu_midi(g - 12, r + j) for j in (0, 2, 4)]
        akk = [a + 12 if a < g - 7 else a for a in akk]
        note(2, b, 0.9, g - 24 + M.DUR[r % 7], 90)
        note(2, b + 2, 0.9, g - 24 + M.DUR[r % 7] + 7, 80)
        for s in (1, 3):
            for m in akk:
                note(1, b + s, 0.35, m, 58)
        for j, m in enumerate(akk + [akk[1], akk[2], akk[1], akk[0], akk[1]]):
            note(0, b + j * 0.5, 0.45, m + 24, 52 if j % 2 else 64)
        note(9, b, 0.2, 36, 92)
        note(9, b + 2, 0.2, 36, 84)
        note(9, b + 1, 0.2, 39, 62)
        note(9, b + 3, 0.2, 39, 62)
        for e in range(8):
            note(9, b + e / 2, 0.1, 42, 30 if e % 2 else 44)
    ev.sort(key=lambda x: (x[0], x[1]))
    mf = mido.MidiFile(ticks_per_beat=tpb)
    tr = mido.MidiTrack()
    mf.tracks.append(tr)
    last = 0
    for tick, _, msg in ev:
        tr.append(msg.copy(time=tick - last))
        last = tick
    mf.save(pfad)


def _sprachspur(plan, pfad):
    import wave
    import numpy as np
    n = int((plan["dauer"] + 1) * 44100)
    spur = np.zeros(n, np.float32)
    for sp in plan["sprache"]:
        with wave.open(str(sp["wav"])) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
            x = x.reshape(-1, w.getnchannels()).mean(axis=1)
        i0 = int(sp["start"] * 44100)
        x = x[: max(0, n - i0)]
        spur[i0:i0 + len(x)] += x
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes((np.clip(spur, -1, 1) * 32767).astype(np.int16).tobytes())


def audio(cfg, plan, tmp):
    musik_midi(cfg, plan["dauer"], tmp / "musik.mid")
    M.begleitung_rendern(tmp / "musik.mid", tmp / "musik.wav")
    if plan["sprache"] and "wav" in plan["sprache"][0]:
        _sprachspur(plan, tmp / "stimme_roh.wav")
    else:
        M.stimme_pho(SimpleNamespace(silben=[], sprache=plan["sprache"]), tmp / "stimme.pho")
        M.stimme_rendern(tmp / "stimme.pho", tmp / "stimme_roh.wav")
    M.effekte_rendern(plan["effekte"], plan["dauer"], tmp / "effekte.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp / "stimme_roh.wav", "-af", T.STIMM_FILTER,
                    tmp / "stimme.wav"], check=True)
    d = plan["dauer"]
    T.mischen(tmp / "musik.wav", tmp / "stimme.wav", tmp / "effekte.wav", tmp / "roh_mix.wav", tmp,
              musik_pegel=0.6, stimme_pegel=2.2, effekt_pegel=1.0, hall_anteil=0.1)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp / "roh_mix.wav", "-af", f"atrim=0:{d:.2f}",
                    tmp / "roh_mix2.wav"], check=True)
    T.mastern(tmp / "roh_mix2.wav", tmp / "mix.wav", d, einblenden=0.05, ausblenden=0.6)


# --------------------------------------------------------------------------
# Bild
# --------------------------------------------------------------------------

def strahlen(r, farbe=(255, 236, 140)):
    S = r * 2
    img = Image.new("RGBA", (S * 2, S * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S
    for i in range(16):
        a0 = 2 * math.pi * i / 16
        a1 = a0 + math.pi / 16
        d.polygon([(c, c), (c + math.cos(a0) * S, c + math.sin(a0) * S),
                   (c + math.cos(a1) * S, c + math.sin(a1) * S)], fill=farbe + (150,))
    return img.resize((S, S), Image.LANCZOS)


class ShortSzene:
    def __init__(self, cfg, plan, kanal):
        self.cfg, self.plan = cfg, plan
        akzent = cfg.get("akzent", "#e5398f")
        self.akzent = akzent
        self.bg = G.hintergrund(W, H, G.PALETTEN[cfg.get("palette", 0) % len(G.PALETTEN)])
        self.sonne = G.sonne(int(W * 0.09))
        rng = random.Random(4)
        self.wolken = [(G.wolke(int(W * rng.uniform(0.3, 0.42))), rng.uniform(0, W), H * y, rng.uniform(15, 35))
                       for y in (0.05, 0.2, 0.33)]
        self.blumen = [(G.blume(int(W * 0.09), c), W * x, H * (0.83 + 0.015 * (i % 2)))
                       for i, (x, c) in enumerate(zip([0.06, 0.2, 0.8, 0.94],
                                                      ["#e53935", "#fbc02d", "#8e24aa", "#1e88e5"]))]
        groesse = W * 0.13
        self.banner = G.text_sprite(cfg.get("banner", "RATE MAL!"), groesse, G.rgb("#ffffff"),
                                    rand=G.rgb(akzent), randbreite=int(W * 0.018))
        if self.banner.width > W * 0.86:  # lange Banner verkleinern, damit sie (auch beim Pulsieren) ganz sichtbar sind
            self.banner = G.text_sprite(cfg.get("banner"), groesse * W * 0.86 / self.banner.width, G.rgb("#ffffff"),
                                        rand=G.rgb(akzent), randbreite=int(W * 0.018))
        self.frage = G.text_sprite("?", W * 0.28, G.rgb("#ffffff"), rand=G.rgb(akzent), randbreite=int(W * 0.02))
        self.zahlen = {n: G.text_sprite(str(n), W * 0.2, G.rgb("#ffffff"), rand=G.rgb(akzent),
                                        randbreite=int(W * 0.02)) for n in (1, 2, 3)}
        self.kanal = G.text_sprite(kanal, W * 0.045, (255, 255, 255, 230), rand=(0, 0, 0, 90), randbreite=2) \
            if kanal else None
        self.ende_text = G.gestapelt([G.text_sprite(z, W * 0.1, G.rgb("#ffffff"), rand=G.rgb(akzent),
                                                    randbreite=int(W * 0.014))
                                      for z in E._umbruch(cfg.get("ende", "Wie viele hast du erraten?"), 14)])
        self.strahlen = strahlen(int(W * 0.5))
        fig = cfg.get("figur", {})
        self.figur = G.Figur(fig.get("typ", "biene"), fig.get("farbe"))
        self.typ = fig.get("typ", "biene")
        self.gr = int(W * 0.76)
        self.cache = {}
        self.worte = {}
        self.blink = sorted(random.Random(9).uniform(0, plan["dauer"]) for _ in range(int(plan["dauer"] / 3)))
        rng = random.Random(8)
        farben = [(229, 57, 53), (251, 192, 45), (67, 160, 71), (30, 136, 229), (142, 36, 170), (255, 112, 67)]
        self.konfetti = [(rng.uniform(0.05, 0.95), rng.uniform(-0.1, 0.25), rng.uniform(0.25, 0.55),
                          rng.choice(farben), rng.uniform(0, 6), rng.uniform(12, 24)) for _ in range(60)]

    def ding(self, d, t, sil):
        bild = d["bild"]
        key = (bild, sil)
        animiert = not sil and (bild in BI.ANIMIERT or bild == "sonne")
        if key in self.cache and not animiert:
            return self.cache[key]
        if bild.startswith("figur:"):
            img = BI.bild_sprite("leer", self.gr, d.get("farbe"), t)
            f = G.Figur(bild.split(":", 1)[1]).sprite(int(self.gr * 0.82), mund=0.0 if sil else 0.6, arm=0.6)
            f = f.resize((int(self.gr * 0.82),) * 2, Image.LANCZOS)
            if sil:
                f = BI.schatten(f)
            img.alpha_composite(f, (int(self.gr * 0.09), int(self.gr * 0.1)))
        else:
            img = BI.bild_sprite(bild, self.gr, d.get("farbe"), t, silhouette=sil)
        if not animiert:
            self.cache[key] = img
        return img

    def wort(self, d):
        if d["wort"] not in self.worte:
            sp = G.text_sprite(d["wort"], W * 0.12, G.rgb(d.get("farbe") or self.akzent),
                               randbreite=int(W * 0.016))
            if sp.width > W * 0.92:
                f = W * 0.92 / sp.width
                sp = sp.resize((int(sp.width * f), int(sp.height * f)), Image.LANCZOS)
            self.worte[d["wort"]] = sp
        return self.worte[d["wort"]]

    def paste_skaliert(self, frame, spr, sc, cx, cy, winkel=0.0):
        if sc <= 0.02:
            return
        w, h = max(1, int(spr.width * sc)), max(1, int(spr.height * sc))
        sp = spr.resize((w, h), Image.BILINEAR)
        if winkel:
            sp = sp.rotate(winkel, resample=Image.BICUBIC, expand=True)
        frame.paste(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)), sp)

    def bild(self, i, mund):
        t = i / FPS
        plan = self.plan
        frame = self.bg.copy()
        s = self.sonne.rotate(8 * math.sin(t * 1.5), resample=Image.BICUBIC)
        frame.paste(s, (int(W * 0.86 - s.width / 2), int(H * 0.25 - s.height / 2)), s)
        for spr, x0, y, v in self.wolken:
            x = (x0 + t * v) % (W + spr.width) - spr.width
            frame.paste(spr, (int(x), int(y)), spr)
        for spr, x, y in self.blumen:
            dy = -abs(math.sin(t * 4 + x)) * 10
            frame.paste(spr, (int(x - spr.width / 2), int(y + dy)), spr)

        # Banner + Fortschritt
        self.paste_skaliert(frame, self.banner, 1 + 0.04 * math.sin(t * 6), W / 2, H * 0.1)
        n = len(plan["dinge"])
        akt = next((k for k, d in enumerate(plan["dinge"]) if d["start"] <= t < d["ende"]), None)
        dr = ImageDraw.Draw(frame)
        for k in range(n):
            x = W / 2 + (k - (n - 1) / 2) * 70
            erledigt = t >= plan["dinge"][k]["aufloesung"]
            r = 22 if k == akt else 16
            dr.ellipse([x - r, H * 0.175 - r, x + r, H * 0.175 + r],
                       fill=G.rgb(self.akzent)[:3] if erledigt else (255, 255, 255),
                       outline=G.rgb(self.akzent)[:3], width=5)

        cx, cy = W / 2, H * 0.40
        sprung = 0.0
        if akt is not None:
            d = plan["dinge"][akt]
            if t < d["aufloesung"]:
                # Schattenbild mit Fragezeichen + Countdown
                sc = E.ease_pop((t - d["start"]) / 0.4) * (1 + 0.03 * math.sin(t * 7))
                self.paste_skaliert(frame, self.ding(d, t, True), sc, cx, cy, 4 * math.sin(t * 5))
                self.paste_skaliert(frame, self.frage, E.ease_pop((t - d["start"] - 0.2) / 0.4)
                                    * (1 + 0.1 * abs(math.sin(t * 5))), W * 0.84, H * 0.24, -12)
                if t >= d["countdown"]:
                    k = min(2, int((t - d["countdown"]) / TICK))
                    ph = (t - d["countdown"]) - k * TICK
                    zahl = 3 - k
                    r = int(W * 0.13)
                    bx, by = W * 0.5, H * 0.635
                    sc2 = E.ease_pop(ph / 0.25)
                    dr.ellipse([bx - r * sc2, by - r * sc2, bx + r * sc2, by + r * sc2],
                               fill=G.rgb(self.akzent)[:3], outline=(255, 255, 255), width=10)
                    self.paste_skaliert(frame, self.zahlen[zahl], sc2 * 0.9, bx, by + 5)
            else:
                # Auflösung: Strahlen, buntes Bild, Wort, Konfetti
                alt = t - d["aufloesung"]
                st = self.strahlen.rotate(t * 30, resample=Image.BICUBIC)
                if alt < 0.4:
                    st = st.copy()
                    st.putalpha(st.getchannel("A").point(lambda p: int(p * alt / 0.4)))
                frame.paste(st, (int(cx - st.width / 2), int(cy - st.height / 2)), st)
                sc = E.ease_pop(alt / 0.35) * (1 + 0.03 * math.sin(t * 7))
                if t > d["ende"] - 0.25:
                    sc *= max(0.0, (d["ende"] - t) / 0.25)
                self.paste_skaliert(frame, self.ding(d, t, False), sc * 1.05, cx, cy)
                self.paste_skaliert(frame, self.wort(d), E.ease_pop((alt - 0.15) / 0.35), W / 2, H * 0.645)
                if alt < 2.2:
                    for (x0, y0, v, farbe, ph, gr) in self.konfetti:
                        y = H * (y0 + alt * v)
                        x = W * x0 + math.sin(alt * 5 + ph) * 30
                        w2 = gr * abs(math.sin(alt * 8 + ph))
                        dr.rectangle([x - w2, y - gr * 0.5, x + w2, y + gr * 0.5], fill=farbe)
                sprung = max(0.0, math.sin(min(alt, 0.5) / 0.5 * math.pi))
        elif t >= plan["schluss"]:
            alt = t - plan["schluss"]
            self.paste_skaliert(frame, self.ende_text, E.ease_pop(alt / 0.5) * (1 + 0.04 * math.sin(t * 6)),
                                W / 2, H * 0.43)
            for k in range(5):
                a = t * 1.5 + k * 1.25
                st = G.stern(int(W * 0.03))
                frame.paste(st, (int(W / 2 + math.cos(a) * W * 0.38), int(H * 0.43 + math.sin(a) * H * 0.13)), st)

        # Figur unten
        S = int(W * 0.44)
        blinz = any(0 <= t - b < 0.12 for b in self.blink)
        spr = self.figur.sprite(S, mund, blinz, arm=0.8 * math.sin(t * 6) + (0.6 if sprung else 0),
                                ohr=math.sin(t * 5), fluegel=abs(math.sin(t * 38)), blick=1.5 * math.sin(t))
        sp = spr.resize((S, S), Image.LANCZOS)
        hupf = abs(math.sin(t * math.pi * 2)) * 12 + sprung * 70
        frame.paste(sp, (int(W / 2 - S / 2), int(H * 0.835 - S / 2 - hupf)), sp)
        if self.kanal:
            frame.paste(self.kanal, (int(W * 0.04), int(H * 0.02)), self.kanal)
        return frame


def erstellen(pfad):
    pfad = Path(pfad)
    cfg = json.loads(pfad.read_text())
    kanal_cfg = json.loads((BASIS / "kanal.json").read_text())
    ziel = BASIS / "ausgabe" / "shorts" / pfad.stem
    ziel.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print(f"▶ {cfg['titel']}")
    el = EL.verfuegbar() and (os.environ.get("LIEDERWIESE_KLANG") or cfg.get("klang") or "auto") != "synth"
    plan = planen(cfg, ziel / "elevenlabs" if el else None)
    print(f"  • Stimme: {'ElevenLabs' if el else 'MBROLA (kostenlos)'}")
    if plan["dauer"] > 59:
        print(f"  ⚠ {plan['dauer']:.0f}s – länger als 59s, bitte weniger Rätsel verwenden")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        audio(cfg, plan, tmp)
        n = int(plan["dauer"] * FPS)
        env = E.huellkurve(tmp / "stimme.wav", FPS, n)
        szene = ShortSzene(cfg, plan, kanal_cfg.get("kanalname", ""))
        ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(tmp / "mix.wav"),
                               *T.video_kodierung(ziel / "short.mp4")], stdin=subprocess.PIPE)
        mund = 0.0
        for i in range(n):
            mund = max(env[i], mund * 0.6)
            ff.stdin.write(szene.bild(i, float(mund)).tobytes())
        ff.stdin.close()
        ff.wait()
    tags = cfg.get("tags", [])
    (ziel / "youtube_text.txt").write_text(
        f"TITEL\n{cfg['titel']} #shorts\n\nBESCHREIBUNG\n{cfg.get('beschreibung', '')}\n\n"
        f"{kanal_cfg.get('hinweis_ki', '')}\n\n#shorts #kinder #ratespiel\n\n"
        f"TAGS\n{', '.join(tags)}\n\nEINSTELLUNGEN\n- Zielgruppe: Ja, speziell für Kinder\n"
        f"- Länge: {plan['dauer']:.0f} Sekunden (Short)\n"
        "- Als Short hochladen: einfach das hochkant-Video in der YouTube-App hochladen\n")
    YM.schreiben(YM.short_meta(cfg, kanal_cfg, plan["dauer"]), ziel)
    print(f"  ✔ {plan['dauer']:.0f}s, fertig in {time.time() - t0:.0f}s → {ziel}")


def main():
    ap = argparse.ArgumentParser(description="Rate-mal-Shorts erstellen")
    ap.add_argument("shorts", nargs="*")
    ap.add_argument("--alle", action="store_true")
    a = ap.parse_args()
    liste = sorted((BASIS / "shorts").glob("[0-9]*.json")) if a.alle else a.shorts
    for s in liste:
        erstellen(s)


if __name__ == "__main__":
    main()
