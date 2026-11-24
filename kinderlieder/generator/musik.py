"""Musik-Teil: Silben, Melodie, Begleitung, Kinderstimme (Gesang + Sprechen) und Geräusche.

Alles kostenlos und offline:
  * espeak-ng + MBROLA (deutsche Stimme de7) -> Stimme; per Formant-Verschiebung kindlich gemacht
  * FluidSynth + FluidR3 General-MIDI-Soundfont -> Instrumente
  * numpy -> Geräuscheffekte (Plopp, Boing, Piep, Tatü-Tata, Glitzer, Schrubb …)
"""
import math
import random
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import mido
import numpy as np

SOUNDFONTS = [
    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    "/usr/share/sounds/sf2/default-GM.sf2",
    "/usr/share/soundfonts/FluidR3_GM.sf2",
]
MBROLA_DB = "/usr/share/mbrola/de7/de7"
MBROLA_SR = 22050
ESPEAK_VOICE = "mb-de7"
# Formant-Faktor: >1 = kleinerer "Stimmtrakt" = Kinderstimme (1.0 = Erwachsene)
KIND = 1.2

TONARTEN = {"C": 60, "Cis": 61, "Des": 61, "D": 62, "Es": 63, "E": 64, "F": 65,
            "Fis": 66, "G": 55, "As": 56, "A": 57, "B": 58, "H": 59}
DUR = [0, 2, 4, 5, 7, 9, 11]

INSTRUMENTE = {"glockenspiel": 9, "musikbox": 10, "celesta": 8, "marimba": 12,
               "xylophon": 13, "klavier": 0, "floete": 73, "flöte": 73,
               "gitarre": 24, "ukulele": 24, "pfeifen": 78, "pizzicato": 45}

STUFEN = {"I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5}

# --------------------------------------------------------------------------
# Komponierte Melodien (Tonstufen: 0=do 1=re 2=mi 3=fa 4=sol 5=la 6=ti 7=do')
# Grundrhythmus je Zeile: 6 Viertel + 1 Halbe (typischer Kinderlied-Vers mit 7 Silben)
# Aufbau: Zeile 1 und 3 = Frage, Zeile 2 = offen, Zeile 4 = endet auf dem Grundton
# --------------------------------------------------------------------------
MELODIEN = {
    "A": {  # singend, Terzen wie ein Ruf ("so-mi")
        "refrain": [[4, 2, 4, 2, 4, 5, 4], [3, 3, 2, 1, 2, 3, 1],
                    [4, 2, 4, 2, 4, 5, 7], [5, 4, 3, 2, 1, 1, 0]],
        "strophe": [[0, 0, 2, 2, 4, 4, 2], [3, 3, 5, 5, 4, 3, 4],
                    [0, 0, 2, 2, 4, 4, 7], [6, 6, 5, 5, 4, 1, 0]],
    },
    "B": {  # fröhliche Fanfare
        "refrain": [[0, 2, 4, 7, 6, 5, 4], [5, 5, 4, 3, 2, 3, 1],
                    [0, 2, 4, 7, 6, 5, 4], [5, 4, 3, 1, 2, 1, 0]],
        "strophe": [[4, 4, 2, 2, 3, 3, 1], [2, 2, 0, 0, 1, 2, 4],
                    [4, 4, 2, 2, 3, 3, 5], [4, 4, 3, 1, 2, 1, 0]],
    },
    "D": {  # wiegend, Dreiklang-Hüpfer
        "refrain": [[0, 2, 4, 2, 0, 2, 4], [5, 4, 3, 2, 1, 2, 4],
                    [0, 2, 4, 2, 0, 2, 4], [5, 5, 4, 4, 2, 1, 0]],
        "strophe": [[2, 2, 4, 4, 3, 3, 2], [1, 1, 3, 3, 2, 1, 4],
                    [2, 2, 4, 4, 5, 5, 4], [5, 4, 3, 2, 1, 1, 0]],
    },
    "E": {  # Bogen: steigt auf und fällt wie ein Regenbogen
        "refrain": [[7, 7, 6, 5, 4, 5, 4], [3, 3, 2, 3, 4, 2, 1],
                    [7, 7, 6, 5, 4, 5, 7], [6, 5, 4, 3, 2, 1, 0]],
        "strophe": [[0, 2, 4, 5, 4, 2, 4], [3, 3, 2, 2, 1, 2, 4],
                    [0, 2, 4, 5, 4, 2, 7], [6, 5, 4, 2, 1, 1, 0]],
    },
    "F": {  # verspielt, Terz-Hüpfer
        "refrain": [[2, 4, 4, 2, 3, 5, 5], [4, 3, 2, 1, 2, 3, 4],
                    [2, 4, 4, 2, 3, 5, 5], [4, 3, 2, 1, 2, 1, 0]],
        "strophe": [[0, 0, 2, 2, 4, 4, 4], [5, 4, 5, 4, 3, 2, 1],
                    [0, 0, 2, 2, 4, 4, 7], [6, 4, 5, 3, 2, 1, 0]],
    },
    "C": {  # hüpfend, große Sprünge
        "refrain": [[0, 4, 0, 4, 2, 4, 7], [6, 5, 4, 3, 2, 3, 4],
                    [0, 4, 0, 4, 2, 4, 7], [6, 5, 4, 2, 1, 1, 0]],
        "strophe": [[0, 0, 1, 1, 2, 2, 3], [4, 4, 5, 5, 4, 3, 4],
                    [6, 6, 7, 7, 8, 8, 7], [9, 7, 4, 2, 4, 7, 7]],
    },
}
GRUNDRHYTHMUS = [2, 2, 2, 2, 2, 2, 4]  # in Achteln, Summe 16 = 2 Takte


def soundfont():
    for s in SOUNDFONTS:
        if Path(s).exists():
            return s
    raise SystemExit("Kein Soundfont gefunden (bitte 'fluid-soundfont-gm' installieren).")


# --------------------------------------------------------------------------
# Silben
# --------------------------------------------------------------------------

def ist_vokal(ph):
    return ph[0] in "aeiouyEIOUY29@6"


def _pho_parsen(text):
    res = []
    for zeile in text.splitlines():
        teile = zeile.split()
        if len(teile) >= 2:
            punkte = [(float(teile[i]), float(teile[i + 1])) for i in range(2, len(teile) - 1, 2)]
            res.append((teile[0], int(teile[1]), punkte))
    return res


@lru_cache(maxsize=None)
def phoneme(wort):
    """Phoneme eines Wortes als Liste (name, dauer_ms) laut espeak-ng."""
    out = subprocess.run(["espeak-ng", "-v", ESPEAK_VOICE, "--pho", "-q", wort],
                         capture_output=True, text=True, check=True).stdout
    return [(p, d) for p, d, _ in _pho_parsen(out) if p != "_"]


def silben_eines_wortes(wort):
    phs = phoneme(wort)
    kerne = []
    for i, (p, _) in enumerate(phs):
        if p == "6":
            # vokalisches r: nach Vokal kein eigener Kern ("hier"), sonst schon ("unter")
            # nach Doppellaut aber schon ("Feu-er", "Ei-er")
            if i == 0 or not ist_vokal(phs[i - 1][0]) or phs[i - 1][0] in ("aI", "aU", "OY"):
                kerne.append(i)
        elif ist_vokal(p):
            kerne.append(i)
    if not kerne:
        return [], phs
    silben = [{"onset": [], "kern": phs[k], "coda": []} for k in kerne]
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


def wort_sauber(roh):
    return re.sub(r"[^\wäöüÄÖÜß'-]", "", roh).replace("-", " ").strip()


def zeile_zu_silben(text):
    """Teilt eine Liedzeile in Wörter und Silben."""
    woerter = [w for w in re.split(r"\s+", text.strip()) if w]
    alle, wortinfo, rest = [], [], []
    for wi, roh in enumerate(woerter):
        sauber = wort_sauber(roh)
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
# Melodie an Silbenzahl anpassen und harmonisieren
# --------------------------------------------------------------------------

def anpassen(vorlage, n):
    """Passt eine 7-Ton-Vorlage [(stufe, achtel)] an n Silben an (teilen / zusammenlegen)."""
    noten = [list(x) for x in vorlage]
    if n > 15:
        raise SystemExit(f"Zeile hat {n} Silben – bitte auf zwei Zeilen aufteilen (max. 15).")
    while len(noten) < n:
        # längste Note teilen (frühere bevorzugt; letzte Note nur wenn nötig)
        kand = [i for i in range(len(noten) - 1) if noten[i][1] >= 2] or [len(noten) - 1]
        i = max(kand, key=lambda k: (noten[k][1], -k))
        if noten[i][1] < 2:
            raise SystemExit("Zeile zu lang für die Melodie.")
        st, l = noten[i]
        nxt = noten[i + 1][0] if i + 1 < len(noten) else st
        zweite = st + (1 if nxt > st else -1 if nxt < st else 0) if abs(nxt - st) >= 2 else st
        noten[i:i + 1] = [[st, l // 2], [zweite, l - l // 2]]
    while len(noten) > n:
        # kürzestes Paar (nicht die letzte Note) zusammenlegen
        i = min(range(len(noten) - 2), key=lambda k: (noten[k][1] + noten[k + 1][1], -k))
        noten[i:i + 2] = [[noten[i][0], noten[i][1] + noten[i + 1][1]]]
    return noten


AKKORD_KAND = ["I", "IV", "V", "VI"]


def akkordtoene(stufe):
    r = STUFEN[stufe]
    return {(r + k) % 7 for k in (0, 2, 4)}


def harmonisieren(noten, schluss):
    """Wählt je Takt (8 Achtel) den passendsten Akkord zu den Melodietönen."""
    res = []
    for takt in range(2):
        best, best_s = "I", -1
        for akk in AKKORD_KAND:
            s, pos = 0.0, 0
            for st, l in noten:
                if takt * 8 <= pos < takt * 8 + 8:
                    gew = l * (1.6 if pos % 4 == 0 else 1.0)
                    s += gew if st % 7 in akkordtoene(akk) else -0.3 * gew
                pos += l
            s += {"I": 0.3, "V": 0.2, "IV": 0.1, "VI": 0.0}[akk]
            if s > best_s:
                best, best_s = akk, s
        res.append(best)
    if schluss:
        res[1] = "I"
    return res


def stufe_zu_midi(grund, stufe):
    return grund + 12 * (stufe // 7) + DUR[stufe % 7]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


# --------------------------------------------------------------------------
# Sprechen
# --------------------------------------------------------------------------

def sprache_pho(text, tempo=145):
    """Phoneme + Tonhöhen eines gesprochenen Satzes (lebhaft, kindlich)."""
    out = subprocess.run(["espeak-ng", "-v", ESPEAK_VOICE, "--pho", "-q", "-s", str(tempo), text],
                         capture_output=True, text=True, check=True).stdout
    phs = _pho_parsen(out)
    alle = [v for _, _, pts in phs for _, v in pts]
    mittel = sum(alle) / len(alle) if alle else 200
    ziel = 285.0  # mittlere Tonhöhe des Kindes (Hz)
    res = []
    for p, d, pts in phs:
        neu = [(pos, ziel + (v - mittel) * 1.7 * ziel / mittel) for pos, v in pts]
        res.append((p, d, neu))
    # Pausen am Ende entfernen
    while res and res[-1][0] == "_":
        res.pop()
    return res


# --------------------------------------------------------------------------
# Lied-Ablauf
# --------------------------------------------------------------------------

class Lied:
    """Baut den kompletten Ablauf eines Liedes (Zeiten in Schlägen)."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.tempo = cfg.get("tempo", 100)
        self.grund = TONARTEN.get(cfg.get("tonart", "C"), 60)
        self.melodie = MELODIEN.get(cfg.get("melodie", "A"), MELODIEN["A"])
        self.noten_melodie = []     # (start_beat, dauer_beat, midi, gesungen?)
        self.silben = []            # gesungene Silben mit Zeit + Tonhöhe
        self.zeilen = []            # für Karaoke
        self.akkorde = []           # (takt_start_beat, stufe, art)
        self.abschnitte = []        # (start_beat, ende_beat, name, art, teil-cfg)
        self.sprache = []           # {"start", "ende", "text", "pho"}
        self.effekte = []           # (zeit_s, typ)
        self.bauen()

    def sek(self, beat):
        return beat * 60.0 / self.tempo

    def beat(self, sek):
        return sek * self.tempo / 60.0

    def zeile_noten(self, text, art, slot, teil):
        silben, wortinfo = zeile_zu_silben(text)
        n = len(silben)
        eigene = teil.get("melodie")
        if eigene and slot < len(eigene) and len(eigene[slot]) == n:
            rh = [l for _, l in anpassen([(0, l) for l in GRUNDRHYTHMUS], n)]
            noten = list(zip(eigene[slot], rh))
        else:
            vorlage = list(zip(self.melodie[art if art in self.melodie else "strophe"][slot % 4],
                               GRUNDRHYTHMUS))
            noten = anpassen(vorlage, n)
        return silben, wortinfo, noten

    def _vamp(self, t, takte, art="sprechen"):
        folge = ["I", "IV", "V", "I"]
        for k in range(takte):
            self.akkorde.append((t + 4 * k, folge[k % 4], art))

    def _sprechen(self, t, text, nacht=False):
        pho = sprache_pho(text, self.cfg.get("sprechtempo", 145))
        dauer = sum(d for _, d, _ in pho) / 1000.0
        takt = self.sek(4)
        takte = max(2, math.ceil((dauer + 0.9) / takt))
        start = self.sek(t) + 0.35
        self.sprache.append({"start": start, "ende": start + dauer, "text": text, "pho": pho})
        self.abschnitte.append((t, t + 4 * takte, f"sprechen{len(self.sprache)}", "sprechen",
                                {"nacht": True} if nacht else {}))
        self._vamp(t, takte)
        return t + 4 * takte

    def bauen(self):
        cfg = self.cfg
        teile = cfg["teile"]
        ablauf = cfg["ablauf"]
        t = 0.0
        erstes_name = next(a for a in ablauf if isinstance(a, str))
        erstes = teile[erstes_name]
        # Intro: 4 Takte, Instrument spielt die ersten zwei Zeilen des ersten Teils
        self.abschnitte.append((t, t + 16, "intro", "intro", {}))
        art0 = erstes.get("art", "strophe")
        for z in range(2):
            _, _, noten = self.zeile_noten(_zeilentext(erstes["zeilen"][z]), art0, z, erstes)
            pos = 0
            for st, l in noten:
                self.noten_melodie.append((t + 8 * z + pos / 2, l / 2, stufe_zu_midi(self.grund, st), False))
                pos += l
            for k, akk in enumerate(harmonisieren(noten, z % 2 == 1)):
                self.akkorde.append((t + 8 * z + 4 * k, akk, "intro"))
        t += 16
        vorher_gesprochen = False
        for si, eintrag in enumerate(ablauf):
            if isinstance(eintrag, dict):
                t = self._sprechen(t, eintrag["sprich"], eintrag.get("nacht", False))
                vorher_gesprochen = True
                continue
            name = eintrag
            teil = teile[name]
            art = teil.get("art", "strophe")
            if si > 0 and art == "strophe" and not vorher_gesprochen:
                self.abschnitte.append((t, t + 8, f"zwischenspiel{si}", "zwischenspiel", {}))
                self.akkorde += [(t, "I", "zwischenspiel"), (t + 4, "V", "zwischenspiel")]
                for j, st in enumerate([4, 2, 0, 2, 4, 5, 4, 1]):
                    self.noten_melodie.append((t + j, 0.5, stufe_zu_midi(self.grund, st + 7), False))
                t += 8
            vorher_gesprochen = False
            start = t
            for z, zeile in enumerate(teil["zeilen"]):
                text = _zeilentext(zeile)
                silben, wortinfo, noten = self.zeile_noten(text, art, z, teil)
                for k, akk in enumerate(harmonisieren(noten, z % 4 == 3)):
                    self.akkorde.append((t + 4 * k, akk, art))
                zinfo = zeile if isinstance(zeile, dict) else {}
                zeil = {"text": text, "start": None, "ende": None, "woerter": [], "info": zinfo,
                        "teil": teil, "abschnitt_name": name, "abschnitt": len(self.abschnitte)}
                sil0 = len(self.silben)
                pos = 0
                for s_obj, (st, l) in zip(silben, noten):
                    midi = stufe_zu_midi(self.grund, st)
                    b0, dl = t + pos / 2, l / 2
                    pos += l
                    self.noten_melodie.append((b0, dl, midi, True))
                    s_obj.update({"start": self.sek(b0), "dauer": self.sek(dl), "midi": midi,
                                  "zeilenende": False})
                    self.silben.append(s_obj)
                self.silben[-1]["zeilenende"] = True
                for roh, idx in wortinfo:
                    if idx:
                        a = self.silben[sil0 + idx[0]]
                        e = self.silben[sil0 + idx[-1]]
                        zeil["woerter"].append((roh, a["start"], e["start"] + e["dauer"]))
                    else:
                        zeil["woerter"].append((roh, None, None))
                zeitw = [w for w in zeil["woerter"] if w[1] is not None]
                zeil["start"], zeil["ende"] = zeitw[0][1], zeitw[-1][2]
                self._effekt_planen(zinfo, zeil)
                self.zeilen.append(zeil)
                t += 8
            self.abschnitte.append((start, t, name, art, teil))
        # Outro: Instrument spielt die letzten zwei Zeilen des Refrains
        self.abschnitte.append((t, t + 20, "outro", "outro", {"nacht": True} if cfg.get("ende_nacht") else {}))
        ref_name = next((n for n in ablauf if isinstance(n, str) and teile[n].get("art") == "refrain"),
                        erstes_name)
        ref = teile[ref_name]
        art = ref.get("art", "strophe")
        for k, z in enumerate((2, 3)):
            if z < len(ref["zeilen"]):
                _, _, noten = self.zeile_noten(_zeilentext(ref["zeilen"][z]), art, z, ref)
                pos = 0
                for st, l in noten:
                    self.noten_melodie.append((t + 8 * k + pos / 2, l / 2, stufe_zu_midi(self.grund, st), False))
                    pos += l
                for j, akk in enumerate(harmonisieren(noten, z == 3)):
                    self.akkorde.append((t + 8 * k + 4 * j, akk, "outro"))
        self.noten_melodie.append((t + 16, 4, stufe_zu_midi(self.grund, 7), False))
        self.akkorde.append((t + 16, "SCHLUSS", "outro"))
        self.effekte.append((self.sek(t + 16), "glitzer"))
        self.ende_beat = t + 20
        # Abschluss-Sprechtext nach dem Schlussakkord
        if cfg.get("tschuess"):
            pho = sprache_pho(cfg["tschuess"], cfg.get("sprechtempo", 145))
            dauer = sum(d for _, d, _ in pho) / 1000.0
            start = self.sek(t + 17)
            self.sprache.append({"start": start, "ende": start + dauer, "text": cfg["tschuess"], "pho": pho})
            self.ende_beat = max(self.ende_beat, self.beat(start + dauer + 0.8))
        self.abschnitte.sort(key=lambda a: a[0])

    def _effekt_planen(self, zinfo, zeil):
        eff = zinfo.get("effekt")
        if not eff:
            return
        if isinstance(eff, str):
            eff = {"typ": eff}
        zeit = zeil["ende"] + 0.05
        if eff.get("wort"):
            for (w, a, e) in zeil["woerter"]:
                if a is not None and wort_sauber(w).lower() == eff["wort"].lower():
                    zeit = a
                    break
        self.effekte.append((zeit, eff["typ"]))

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
        ev.append((a, 1, mido.Message("note_on", channel=kanal, note=int(midi), velocity=int(max(1, min(127, vel))))))
        ev.append((max(a + 1, e), 0, mido.Message("note_off", channel=kanal, note=int(midi), velocity=0)))

    melo = INSTRUMENTE.get(cfg.get("instrument", "glockenspiel"), 9)
    begl = INSTRUMENTE.get(cfg.get("begleitung", "klavier"), 0)
    ev += [(0, 0, mido.Message("program_change", channel=0, program=melo)),
           (0, 0, mido.Message("program_change", channel=1, program=begl)),
           (0, 0, mido.Message("program_change", channel=2, program=32)),
           (0, 0, mido.Message("program_change", channel=3, program=10)),
           (0, 0, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(lied.tempo)))]
    hoch = 12 if melo in (8, 9, 10) else 0
    for b, d, m, gesungen in lied.noten_melodie:
        note(0, b, d * 0.95, m + hoch, 48 if gesungen else 92)

    g = lied.grund
    for b, stufe, art in lied.akkorde:
        if stufe == "SCHLUSS":
            for m in (g - 12, g, g + 4, g + 7, g + 12):
                note(1, b, 4, m, 80)
            note(2, b, 4, g - 24, 95)
            note(9, b, 3, 49, 85)
            note(9, b, 0.5, 36, 100)
            continue
        r = STUFEN[stufe]
        wurzel = g - 12 + DUR[r % 7]
        akk = [stufe_zu_midi(g - 12, r + k) for k in (0, 2, 4)]
        akk = [a + 12 if a < g - 7 else a for a in akk]
        if art == "sprechen":
            # leise Begleitung unter dem Sprechen: Akkord + Spieluhr-Arpeggio
            for m in akk:
                note(1, b, 3.8, m, 38)
            note(2, b, 1.8, wurzel - 12, 55)
            for k, m in enumerate(akk + [akk[1]]):
                note(3, b + k, 0.9, m + 24, 45)
            for e in range(4):
                note(9, b + e, 0.1, 70, 30)
            continue
        # Bass: 1 und 3
        note(2, b, 0.9, wurzel - 12, 95)
        note(2, b + 2, 0.9, wurzel - 12 + 7, 85)
        # Akkorde auf 2 und 4 (hüpfend), leise Fläche auf 1
        for k in (1, 3):
            for m in akk:
                note(1, b + k, 0.4, m, 66)
        for m in akk:
            note(1, b, 0.9, m, 48)
        # Schlagzeug
        intro = art == "intro"
        note(9, b, 0.2, 36, 90)
        note(9, b + 2, 0.2, 36, 80)
        if not intro:
            note(9, b + 1, 0.2, 39, 60)
            note(9, b + 3, 0.2, 39, 60)
        for e in range(8):
            note(9, b + e / 2, 0.1, 70 if intro else 42, 32 if e % 2 else 46)
        if art == "refrain":
            note(9, b + 3.5, 0.1, 54, 40)  # Tamburin-Schlag im Refrain

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
# Stimme (MBROLA) – Gesang und Sprechen in einer Spur
# --------------------------------------------------------------------------

def stimme_pho(lied, pfad):
    """Schreibt eine MBROLA-.pho-Datei. Zeiten/Tonhöhen werden für die Kinderstimme
    vorverzerrt (Dauer * KIND, Tonhöhe / KIND) und später um KIND beschleunigt."""
    zeilen = []
    pos = 0.0  # ms in Endzeit

    def raus(name, dauer, punkte):
        nonlocal pos
        dauer = max(15.0, dauer)
        p = " ".join(f"{a:.0f} {f / KIND:.1f}" for a, f in punkte)
        zeilen.append(f"{name} {int(round(dauer * KIND))} {p}".strip())
        pos += int(round(dauer * KIND)) / KIND

    def pause(bis):
        while bis - pos > 1:
            raus("_", min(800.0, bis - pos), [])

    def ph(name, dauer, f, vib=False):
        if vib and dauer > 380:
            pts = [(0, f * 0.97), (12, f), (45, f), (60, f * 1.012), (75, f * 0.988), (90, f * 1.01), (100, f * 0.995)]
        else:
            pts = [(0, f * 0.985), (15, f), (100, f)]
        raus(name, dauer, pts)

    # Ereignisse (Silben und Sprechsätze) nach Zeit sortieren
    ereignisse = [("silbe", s["start"], s) for s in lied.silben] + [("satz", sp["start"], sp) for sp in lied.sprache]
    ereignisse.sort(key=lambda e: e[1])
    sil = lied.silben
    sil_index = {id(s): i for i, s in enumerate(sil)}
    for art, _, obj in ereignisse:
        if art == "satz":
            pause(obj["start"] * 1000)
            for p, d, pts in obj["pho"]:
                if p == "_":
                    raus("_", d, [])
                else:
                    raus(p, d, pts)
            continue
        s = obj
        i = sil_index[id(s)]
        f = hz(s["midi"])
        start = s["start"] * 1000
        dauer = s["dauer"] * 1000
        ons = [(p, min(d, 110)) for p, d in s["onset"]]
        cod = [(p, min(d, 100)) for p, d in s["coda"]]
        ons_t = sum(d for _, d in ons)
        beginn = max(pos, start - ons_t * 0.8)
        pause(beginn)
        verfuegbar = start + 0.2 * ons_t - pos
        skal = 1.0 if ons_t <= 0 or verfuegbar >= ons_t else max(0.45, verfuegbar / ons_t)
        for p, d in ons:
            ph(p, d * skal, f)
        legato = 0.85 if s["zeilenende"] else 0.97
        ende = start + dauer * legato
        if i + 1 < len(sil):
            nxt = sil[i + 1]
            n_ons = sum(min(d, 110) for _, d in nxt["onset"])
            ende = min(ende, nxt["start"] * 1000 - n_ons * 0.8)
        cod_t = sum(d for _, d in cod)
        vokal = max(70, ende - pos - cod_t)
        ph(s["kern"][0], vokal, f, vib=True)
        for p, d in cod:
            ph(p, d, f)
    zeilen.append("_ 500")
    Path(pfad).write_text("\n".join(zeilen) + "\n")


def stimme_rendern(pho_pfad, wav_pfad):
    """MBROLA -> WAV mit Kinderstimme (Formanten und Tonhöhe um KIND angehoben, Zeit wieder korrekt)."""
    roh = Path(str(wav_pfad) + ".roh.wav")
    subprocess.run(["mbrola", "-e", MBROLA_DB, str(pho_pfad), str(roh)], check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(roh), "-af",
                    f"asetrate={int(MBROLA_SR * KIND)},aresample=44100", str(wav_pfad)], check=True)
    roh.unlink()


# --------------------------------------------------------------------------
# Geräuscheffekte
# --------------------------------------------------------------------------

SR = 44100


def _ton(f0, f1, dauer, form="sinus", huelle=None):
    n = int(SR * dauer)
    t = np.arange(n) / SR
    f = np.linspace(f0, f1, n) if np.isscalar(f0) else f0
    phase = 2 * np.pi * np.cumsum(f) / SR
    if form == "sinus":
        x = np.sin(phase)
    else:  # weiches Rechteck
        x = np.tanh(3 * np.sin(phase))
    if huelle is None:
        huelle = np.exp(-t * 6 / dauer)
    return x * huelle


def effekt_klang(typ):
    if typ == "plopp":
        x = _ton(500, 1300, 0.09)
    elif typ == "boing":
        n = int(SR * 0.45)
        t = np.arange(n) / SR
        f = 180 + 320 * np.exp(-t * 6) * (1 + 0.35 * np.sin(2 * np.pi * 14 * t))
        x = _ton(f, None, 0.45)
    elif typ == "piep":
        x = np.concatenate([_ton(2300, 2900, 0.08), np.zeros(int(SR * 0.06)), _ton(2500, 3100, 0.08)])
    elif typ == "tatue":
        teile = []
        for f in (440, 587, 440, 587):
            n = int(SR * 0.32)
            h = np.minimum(1, np.minimum(np.arange(n) / 600, (n - np.arange(n)) / 600))
            teile.append(_ton(f, f, 0.32, "rechteck", h) * 0.5)
        x = np.concatenate(teile)
    elif typ == "glitzer":
        teile = np.zeros(int(SR * 0.9))
        for k, f in enumerate([1568, 1976, 2349, 2637, 3136, 3520, 3951]):
            s = int(SR * 0.06 * k)
            ton = _ton(f, f, 0.5) * 0.6
            teile[s:s + len(ton)] += ton[:len(teile) - s]
        x = teile
    elif typ == "schrubb":
        rng = np.random.default_rng(1)
        teile = []
        for k in range(4):
            n = int(SR * 0.16)
            rausch = rng.standard_normal(n)
            rausch = np.convolve(rausch, np.ones(6) / 6, "same") - np.convolve(rausch, np.ones(60) / 60, "same")
            h = np.sin(np.pi * np.arange(n) / n)
            teile += [rausch * h * 0.7, np.zeros(int(SR * 0.04))]
        x = np.concatenate(teile)
    elif typ == "klingel":
        n = int(SR * 0.9)
        t = np.arange(n) / SR
        x = np.sin(2 * np.pi * 1800 * t) * (np.sin(2 * np.pi * 18 * t) > 0) * np.exp(-t * 1.5) * 0.5
    elif typ == "summ":
        n = int(SR * 0.9)
        t = np.arange(n) / SR
        f = 210 + 12 * np.sin(2 * np.pi * 5 * t)
        x = _ton(f, None, 0.9, "rechteck", np.sin(np.pi * t / 0.9)) * 0.35
    elif typ == "platsch":
        rng = np.random.default_rng(3)
        n = int(SR * 0.5)
        t = np.arange(n) / SR
        rausch = rng.standard_normal(n)
        rausch = np.convolve(rausch, np.ones(8) / 8, "same")
        x = rausch * np.exp(-t * 9) * 0.8 + _ton(900, 300, 0.5) * 0.4
    elif typ == "blubb":
        teile = np.zeros(int(SR * 0.7))
        for k, f in enumerate([300, 420, 360, 520]):
            s = int(SR * 0.14 * k)
            ton = _ton(f, f * 2.2, 0.1) * 0.7
            teile[s:s + len(ton)] += ton
        x = teile
    elif typ == "quak":
        teile = []
        for f in (150, 130):
            n = int(SR * 0.22)
            tt = np.arange(n) / SR
            h = np.sin(np.pi * tt / 0.22) * (0.6 + 0.4 * (np.sin(2 * np.pi * 30 * tt) > 0))
            teile += [_ton(f, f * 0.8, 0.22, "rechteck", h) * 0.45, np.zeros(int(SR * 0.08))]
        x = np.concatenate(teile)
    elif typ == "tick":
        x = _ton(1500, 1200, 0.05) * 0.8
    elif typ == "tada":
        teile = np.zeros(int(SR * 1.0))
        for k, f in enumerate([523, 659, 784, 1047]):
            s = int(SR * 0.07 * k)
            dl = 0.8 - 0.07 * k
            ton = _ton(f, f, dl, "rechteck") * 0.25 + _ton(f * 2, f * 2, dl) * 0.2
            teile[s:s + len(ton)] += ton
        x = teile
    elif typ == "wusch":
        rng = np.random.default_rng(5)
        n = int(SR * 0.35)
        tt = np.arange(n) / SR
        r = rng.standard_normal(n)
        r = np.convolve(r, np.ones(4) / 4, "same")
        x = r * np.sin(np.pi * tt / 0.35) * 0.35
    elif typ == "gaehn":
        x = _ton(520, 260, 0.8, "sinus", np.sin(np.pi * np.arange(int(SR * 0.8)) / (SR * 0.8))) * 0.5
    else:
        x = _ton(800, 800, 0.1)
    return x.astype(np.float32)


def effekte_rendern(effekte, dauer, pfad):
    import wave
    spur = np.zeros(int(SR * (dauer + 2)), np.float32)
    for zeit, typ in effekte:
        k = effekt_klang(typ)
        s = int(zeit * SR)
        if s < len(spur):
            e = min(len(spur), s + len(k))
            spur[s:e] += k[:e - s] * 0.5
    spur = np.clip(spur, -1, 1)
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((spur * 32767).astype(np.int16).tobytes())
