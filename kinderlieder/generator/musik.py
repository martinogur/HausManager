"""Musik-Teil: Silben, Melodie, Begleitung (MIDI) und Gesang (Sprachsynthese).

Alles kostenlos und offline:
  * espeak-ng + MBROLA (deutsche Stimme de7)  -> Gesangsstimme
  * FluidSynth + FluidR3 General-MIDI-Soundfont -> Instrumente
"""
import math
import random
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import mido

SOUNDFONTS = [
    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    "/usr/share/sounds/sf2/default-GM.sf2",
    "/usr/share/soundfonts/FluidR3_GM.sf2",
]
MBROLA_DB = "/usr/share/mbrola/de7/de7"
ESPEAK_VOICE = "mb-de7"

TONARTEN = {"C": 60, "Cis": 61, "Des": 61, "D": 62, "Es": 63, "E": 64, "F": 65,
            "Fis": 66, "G": 55, "As": 56, "A": 57, "B": 58, "H": 59}
DUR = [0, 2, 4, 5, 7, 9, 11]

INSTRUMENTE = {"glockenspiel": 9, "musikbox": 10, "celesta": 8, "marimba": 12,
               "xylophon": 13, "klavier": 0, "floete": 73, "flöte": 73,
               "gitarre": 24, "ukulele": 24, "pfeifen": 78}

STUFEN = {"I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5}
AKKORDE = {
    "strophe": [("I", "IV"), ("V", "I"), ("I", "IV"), ("V", "I")],
    "refrain": [("IV", "I"), ("V", "I"), ("IV", "I"), ("V", "I")],
}


def soundfont():
    for s in SOUNDFONTS:
        if Path(s).exists():
            return s
    raise SystemExit("Kein Soundfont gefunden (bitte 'fluid-soundfont-gm' installieren).")


# --------------------------------------------------------------------------
# Silben
# --------------------------------------------------------------------------

def ist_vokal(ph):
    return ph[0] in "aeiouyEIOUY29@"


@lru_cache(maxsize=None)
def phoneme(wort):
    """Phoneme eines Wortes als Liste (name, dauer_ms) laut espeak-ng."""
    out = subprocess.run(["espeak-ng", "-v", ESPEAK_VOICE, "--pho", "-q", wort],
                         capture_output=True, text=True, check=True).stdout
    res = []
    for zeile in out.splitlines():
        teile = zeile.split()
        if len(teile) >= 2 and teile[0] != "_":
            res.append((teile[0], int(teile[1])))
    return res


def silben_eines_wortes(wort):
    phs = phoneme(wort)
    kerne = []
    for i, (p, _) in enumerate(phs):
        if p == "6":
            # vokalisches r: nach Vokal kein eigener Kern ("hier"), sonst schon ("unter")
            if i == 0 or not ist_vokal(phs[i - 1][0]):
                kerne.append(i)
        elif ist_vokal(p):
            kerne.append(i)
    if not kerne:
        return [], phs
    silben = []
    for j, k in enumerate(kerne):
        silben.append({"onset": [], "kern": phs[k], "coda": []})
    # Konsonanten verteilen
    silben[0]["onset"] = phs[:kerne[0]]
    for j in range(len(kerne) - 1):
        cl = phs[kerne[j] + 1:kerne[j + 1]]
        if len(cl) >= 2:
            silben[j]["coda"] = cl[:1]
            silben[j + 1]["onset"] = cl[1:]
        else:
            silben[j + 1]["onset"] = cl
    silben[-1]["coda"] = phs[kerne[-1] + 1:]
    return silben, []


def zeile_zu_silben(text):
    """Teilt eine Liedzeile in Wörter und Silben."""
    woerter = [w for w in re.split(r"\s+", text.strip()) if w]
    alle, wortinfo = [], []
    rest = []
    for wi, roh in enumerate(woerter):
        sauber = re.sub(r"[^\wäöüÄÖÜß'-]", "", roh).replace("-", " ").strip()
        silben, ohne = silben_eines_wortes(sauber) if sauber else ([], [])
        if not silben:
            if alle:
                alle[-1]["coda"] = alle[-1]["coda"] + ohne
            else:
                rest += ohne
            wortinfo.append((roh, []))
            continue
        if rest:
            silben[0]["onset"] = rest + silben[0]["onset"]
            rest = []
        idx = []
        for s in silben:
            s["wort"] = wi
            idx.append(len(alle))
            alle.append(s)
        wortinfo.append((roh, idx))
    return alle, wortinfo


# --------------------------------------------------------------------------
# Rhythmus und Melodie
# --------------------------------------------------------------------------

def rhythmus(n):
    """Liefert (start, laenge) in Achteln für n Silben in einer Zeile (2 Takte = 16 Achtel)."""
    if n <= 0:
        return []
    if n <= 4:
        st = [4 * i for i in range(n)]
    elif n <= 7:
        st = [2 * i for i in range(n)]
    elif n <= 15:
        B = 7 if n <= 13 else 8
        p = n - B
        paare = set() if p <= 0 else {int(round(x)) for x in _linspace(0, B - 2, p)}
        st, pos = [], 0
        for b in range(B):
            if b in paare:
                st += [pos, pos + 1]
            else:
                st.append(pos)
            pos += 2
    else:
        raise SystemExit(f"Zeile hat {n} Silben – bitte auf zwei Zeilen aufteilen (max. 15).")
    res = []
    for i, s in enumerate(st):
        ende = st[i + 1] if i + 1 < len(st) else max(s + 2, 14)
        res.append((s, ende - s))
    return res


def _linspace(a, b, n):
    if n == 1:
        return [a]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def akkordtoene(stufe):
    r = STUFEN[stufe]
    return {(r + k) % 7 for k in (0, 2, 4)}


def kontur(rng, akkorde, slot):
    """Melodieverlauf (Tonstufen) über 16 Achtel."""
    cur = rng.choice({0: [2, 4], 1: [4, 5, 2], 3: [4, 5, 3]}.get(slot, [2, 4]))
    beats = []
    for b in range(8):
        akk = akkorde[b // 4]
        if b % 2 == 0:
            ziel = cur + rng.choice([-2, -1, 1, 2, 0])
            kand = [t + o for t in akkordtoene(akk) for o in (-7, 0, 7) if -1 <= t + o <= 9]
            cur = min(kand, key=lambda t: (abs(t - ziel), t))
        else:
            cur = max(0, min(8, cur + rng.choice([-1, 1, 1, -1, 0, 2, -2])))
        beats.append(cur)
    k = []
    for b in range(8):
        k.append(beats[b])
        nxt = beats[b + 1] if b < 7 else beats[b]
        k.append((beats[b] + nxt) // 2 if abs(nxt - beats[b]) == 2 else beats[b])
    return k


def stufe_zu_midi(grund, stufe):
    return grund + 12 * (stufe // 7) + DUR[stufe % 7]


class Lied:
    """Baut den kompletten Ablauf eines Liedes (Zeiten in Schlägen)."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.tempo = cfg.get("tempo", 100)
        self.grund = TONARTEN.get(cfg.get("tonart", "C"), 60)
        self.rng_seed = cfg.get("seed", 1)
        self.konturen = {}
        self.noten_melodie = []     # (start_beat, dauer_beat, midi, gesungen?)
        self.silben = []            # Silben mit Zeit + Tonhöhe
        self.zeilen = []            # für Karaoke
        self.akkorde = []           # (takt_start_beat, stufe)
        self.abschnitte = []        # (start_beat, ende_beat, name, art, teil-cfg)
        self.bauen()

    def sek(self, beat):
        return beat * 60.0 / self.tempo

    def kontur_fuer(self, art, slot):
        basis = 0 if slot % 4 == 2 else slot % 4
        key = (art, basis)
        if key not in self.konturen:
            rng = random.Random(f"{self.rng_seed}-{art}-{basis}")
            self.konturen[key] = kontur(rng, AKKORDE[art][basis], basis)
        return self.konturen[key]

    def zeile_noten(self, text, art, slot):
        silben, wortinfo = zeile_zu_silben(text)
        rh = rhythmus(len(silben))
        k = self.kontur_fuer(art, slot)
        akk = AKKORDE[art][slot % 4]
        toene = []
        for i, (s, l) in enumerate(rh):
            st = k[min(s, 15)]
            if i == len(rh) - 1:
                if slot % 4 == 3:
                    st = min((0, 7), key=lambda t: abs(t - st))
                else:
                    kand = [t + o for t in akkordtoene(akk[1]) for o in (-7, 0, 7) if 0 <= t + o <= 8]
                    st = min(kand, key=lambda t: abs(t - st))
            toene.append(st)
        return silben, wortinfo, rh, toene

    def bauen(self):
        cfg = self.cfg
        teile = cfg["teile"]
        ablauf = cfg["ablauf"]
        t = 0.0
        erstes = teile[ablauf[0]]
        # Intro: 4 Takte, Instrument spielt die ersten zwei Zeilen des ersten Teils
        self.abschnitte.append((t, t + 16, "intro", "intro", {}))
        for i, stufe in enumerate(["I", "IV", "V", "I"]):
            self.akkorde.append((t + 4 * i, stufe))
        for z in range(2):
            _, _, rh, toene = self.zeile_noten(_zeilentext(erstes["zeilen"][z]), erstes.get("art", "strophe"), z)
            for (s, l), st in zip(rh, toene):
                self.noten_melodie.append((t + 8 * z + s / 2, l / 2, stufe_zu_midi(self.grund, st), False))
        t += 16
        for si, name in enumerate(ablauf):
            teil = teile[name]
            art = teil.get("art", "strophe")
            if si > 0 and art == "strophe":
                self.abschnitte.append((t, t + 8, "zwischenspiel", "zwischenspiel", {}))
                self.akkorde += [(t, "I"), (t + 4, "V")]
                for j, st in enumerate([4, 2, 0, 2, 4, 5, 4, 1]):
                    self.noten_melodie.append((t + j, 0.5, stufe_zu_midi(self.grund, st + 7), False))
                t += 8
            start = t
            for z, zeile in enumerate(teil["zeilen"]):
                text = _zeilentext(zeile)
                silben, wortinfo, rh, toene = self.zeile_noten(text, art, z)
                akk = AKKORDE[art][z % 4]
                self.akkorde += [(t, akk[0]), (t + 4, akk[1])]
                zeil = {"text": text, "start": None, "ende": None, "woerter": [],
                        "zeige": zeile.get("zeige") if isinstance(zeile, dict) else None,
                        "abschnitt": len(self.abschnitte)}
                sil_idx0 = len(self.silben)
                for s_obj, (s, l), st in zip(silben, rh, toene):
                    midi = stufe_zu_midi(self.grund, st)
                    b0, dl = t + s / 2, l / 2
                    self.noten_melodie.append((b0, dl, midi, True))
                    s_obj.update({"start": self.sek(b0), "dauer": self.sek(dl), "midi": midi,
                                  "zeilenende": False})
                    self.silben.append(s_obj)
                if len(self.silben) > sil_idx0:
                    self.silben[-1]["zeilenende"] = True
                for roh, idx in wortinfo:
                    if idx:
                        a = self.silben[sil_idx0 + idx[0]]
                        e = self.silben[sil_idx0 + idx[-1]]
                        zeil["woerter"].append((roh, a["start"], e["start"] + e["dauer"]))
                    else:
                        zeil["woerter"].append((roh, None, None))
                zeitw = [w for w in zeil["woerter"] if w[1] is not None]
                zeil["start"] = zeitw[0][1]
                zeil["ende"] = zeitw[-1][2]
                self.zeilen.append(zeil)
                t += 8
            self.abschnitte.append((start, t, name, art, teil))
        # Outro: Instrument spielt die letzten zwei Zeilen des Refrains
        self.abschnitte.append((t, t + 20, "outro", "outro", {}))
        ref = next((teile[n] for n in ablauf if teile[n].get("art") == "refrain"), erstes)
        art = ref.get("art", "strophe")
        for k, z in enumerate((2, 3)):
            if z < len(ref["zeilen"]):
                _, _, rh, toene = self.zeile_noten(_zeilentext(ref["zeilen"][z]), art, z)
                for (s, l), st in zip(rh, toene):
                    self.noten_melodie.append((t + 8 * k + s / 2, l / 2, stufe_zu_midi(self.grund, st), False))
            akk = AKKORDE[art][z % 4]
            self.akkorde += [(t + 8 * k, akk[0]), (t + 8 * k + 4, akk[1])]
        self.noten_melodie.append((t + 16, 4, stufe_zu_midi(self.grund, 7), False))
        self.akkorde.append((t + 16, "SCHLUSS"))
        self.ende_beat = t + 20
        self.abschnitte.sort(key=lambda a: a[0])

    @property
    def dauer(self):
        return self.sek(self.ende_beat) + 1.5


def _zeilentext(z):
    return z["text"] if isinstance(z, dict) else z


# --------------------------------------------------------------------------
# Begleitung (MIDI + FluidSynth)
# --------------------------------------------------------------------------

def begleitung_midi(lied, pfad):
    cfg = lied.cfg
    tpb = 480
    ev = []

    def note(kanal, start_beat, dauer_beat, midi, vel):
        a = int(round(start_beat * tpb))
        e = int(round((start_beat + dauer_beat) * tpb))
        ev.append((a, 1, mido.Message("note_on", channel=kanal, note=int(midi), velocity=int(vel))))
        ev.append((max(a + 1, e), 0, mido.Message("note_off", channel=kanal, note=int(midi), velocity=0)))

    melo = INSTRUMENTE.get(cfg.get("instrument", "glockenspiel"), 9)
    begl = INSTRUMENTE.get(cfg.get("begleitung", "klavier"), 0)
    ev += [(0, 0, mido.Message("program_change", channel=0, program=melo)),
           (0, 0, mido.Message("program_change", channel=1, program=begl)),
           (0, 0, mido.Message("program_change", channel=2, program=32)),
           (0, 0, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(lied.tempo)))]
    hoch = 12 if melo in (8, 9, 10) else 0
    for b, d, m, gesungen in lied.noten_melodie:
        note(0, b, d * 0.95, m + hoch, 62 if gesungen else 92)

    g = lied.grund
    for i, (b, stufe) in enumerate(lied.akkorde):
        if stufe == "SCHLUSS":
            for m in (g - 12, g, g + 4, g + 7, g + 12):
                note(1, b, 4, m, 80)
            note(2, b, 4, g - 24, 95)
            ev.append((int(b * tpb), 1, mido.Message("note_on", channel=9, note=49, velocity=90)))
            note(9, b, 0.5, 36, 100)
            continue
        r = STUFEN[stufe]
        wurzel = g - 12 + DUR[r % 7]
        akk = [stufe_zu_midi(g - 12, r + k) for k in (0, 2, 4)]
        akk = [a + 12 if a < g - 7 else a for a in akk]
        # Bass: 1 und 3
        note(2, b, 0.9, wurzel - 12, 95)
        note(2, b + 2, 0.9, wurzel - 12 + 7, 85)
        # Akkorde auf 2 und 4 (hüpfend), leise Fläche auf 1
        for k in (1, 3):
            for m in akk:
                note(1, b + k, 0.4, m, 70)
        for m in akk:
            note(1, b, 0.9, m, 50)
        # Schlagzeug
        intro = b < 16
        note(9, b, 0.2, 36, 90)
        note(9, b + 2, 0.2, 36, 80)
        if not intro:
            note(9, b + 1, 0.2, 39, 55)
            note(9, b + 3, 0.2, 39, 55)
        for e in range(8):
            note(9, b + e / 2, 0.1, 70 if intro else 42, 35 if e % 2 else 50)

    ev.sort(key=lambda x: (x[0], x[1]))
    mf = mido.MidiFile(ticks_per_beat=tpb)
    tr = mido.MidiTrack()
    mf.tracks.append(tr)
    last = 0
    for tick, _, msg in ev:
        tr.append(msg.copy(time=tick - last))
        last = tick
    mf.save(pfad)


def begleitung_rendern(midi_pfad, wav_pfad):
    subprocess.run(["fluidsynth", "-ni", "-g", "0.7", "-r", "44100", "-F", str(wav_pfad),
                    soundfont(), str(midi_pfad)], check=True, capture_output=True)


# --------------------------------------------------------------------------
# Gesang (MBROLA)
# --------------------------------------------------------------------------

def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def gesang_pho(lied, pfad):
    zeilen = []
    pos = 0.0  # ms

    def pause(bis):
        nonlocal pos
        while bis - pos > 1:
            d = min(1000.0, bis - pos)
            zeilen.append(f"_ {int(round(d))}")
            pos += int(round(d))

    def ph(name, dauer, f, vib=False):
        nonlocal pos
        dauer = max(20, int(round(dauer)))
        if vib and dauer > 380:
            pts = f"0 {f*0.97:.1f} 12 {f:.1f} 45 {f:.1f} 60 {f*1.012:.1f} 75 {f*0.988:.1f} 90 {f*1.01:.1f} 100 {f*0.995:.1f}"
        else:
            pts = f"0 {f*0.985:.1f} 15 {f:.1f} 100 {f:.1f}"
        zeilen.append(f"{name} {dauer} {pts}")
        pos += dauer

    sil = lied.silben
    for i, s in enumerate(sil):
        f = hz(s["midi"])
        start = s["start"] * 1000
        dauer = s["dauer"] * 1000
        ons = [(p, min(d, 75)) for p, d in s["onset"]]
        cod = [(p, min(d, 70)) for p, d in s["coda"]]
        ons_t = sum(d for _, d in ons)
        beginn = max(pos, start - ons_t)
        if beginn > pos:
            pause(beginn)
        skal = 1.0
        if ons and start - beginn < ons_t:
            skal = max(0.4, (start - beginn) / ons_t) if start > beginn else 0.5
        for p, d in ons:
            ph(p, d * skal, f)
        legato = 0.82 if s["zeilenende"] else 0.97
        ende = start + dauer * legato
        if i + 1 < len(sil):
            nxt = sil[i + 1]
            n_ons = sum(min(d, 75) for _, d in nxt["onset"])
            ende = min(ende, nxt["start"] * 1000 - n_ons * 0.6)
        cod_t = sum(d for _, d in cod)
        vokal = max(60, ende - pos - cod_t)
        ph(s["kern"][0], vokal, f, vib=True)
        for p, d in cod:
            ph(p, d, f)
    zeilen.append("_ 500")
    Path(pfad).write_text("\n".join(zeilen) + "\n")


def gesang_rendern(pho_pfad, wav_pfad):
    subprocess.run(["mbrola", "-e", MBROLA_DB, str(pho_pfad), str(wav_pfad)],
                   check=True, capture_output=True)
