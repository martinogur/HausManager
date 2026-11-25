"""ElevenLabs-Anbindung: natürlicher Gesang (Eleven Music) und natürliche Sprechstimme (Text-to-Speech).

Ablauf für ein Lied:
1. Sprechteile und Abschiedstext als Sprache erzeugen (mit Zeitstempeln) -> deren Länge ist bekannt.
2. Aus der Lied-Datei einen Kompositionsplan bauen: Intro, Strophen/Refrains mit den Liedzeilen und für jeden
   Sprechteil eine ruhige Instrumentalpause, genau so lang wie der gesprochene Text.
3. Eleven Music erzeugt daraus das Lied (Musik + Gesang).
4. Forced Alignment liefert die Zeit jedes gesungenen Wortes -> Mitsingtext, Bilder, Zahlen und Effekte laufen
   synchron zum echten Gesang.
Alle Ergebnisse werden zwischengespeichert (ausgabe/<lied>/elevenlabs/). Ein Lied kostet so nur einmal Guthaben;
erneutes Rendern (z. B. neue Bilder) nutzt die gespeicherten Dateien.

Zugang: Umgebungsvariable ELEVENLABS_API_KEY (in GitHub als Secret, nie im Code).
Optional: ELEVENLABS_STIMME (voice_id der Sprechstimme), ELEVENLABS_STIMME_<FIGUR> (z. B. ..._BAER),
          ELEVENLABS_TTS_MODELL (Standard eleven_multilingual_v2), ELEVENLABS_MUSIK_MODELL (Standard music_v2_5).
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import time
import wave
from pathlib import Path

import numpy as np

API = "https://api.elevenlabs.io"
SR = 44100

INSTRUMENT_STIL = {
    "glockenspiel": "glockenspiel", "marimba": "marimba", "xylophon": "xylophone", "musikbox": "music box",
    "celesta": "celesta", "klavier": "piano", "floete": "flute", "gitarre": "acoustic guitar",
}


def verfuegbar():
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


class ElevenLabsFehler(RuntimeError):
    pass


def _anfrage(methode, pfad, *, json_body=None, params=None, files=None, data=None, versuche=4, roh=False):
    import requests
    kopf = {"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}
    for v in range(versuche):
        try:
            r = requests.request(methode, API + pfad, headers=kopf, json=json_body, params=params, files=files,
                                 data=data, timeout=600)
        except requests.RequestException as e:
            if v == versuche - 1:
                raise ElevenLabsFehler(f"{pfad}: {e}") from e
            time.sleep(5 * (v + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(10 * (v + 1))
            continue
        if r.status_code >= 400:
            raise ElevenLabsFehler(f"{pfad}: HTTP {r.status_code}: {r.text[:800]}")
        return r.content if roh else r.json()
    raise ElevenLabsFehler(f"{pfad}: keine Antwort nach {versuche} Versuchen")


def _zu_wav(mp3, wav):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-ar", str(SR), "-ac", "2", str(wav)], check=True)


def _wav_dauer(wav):
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


# --------------------------------------------------------------------------
# Sprechen

def stimme_fuer(cfg):
    typ = cfg.get("figur", {}).get("typ", "").upper()
    return (cfg.get("elevenlabs_stimme") or os.environ.get(f"ELEVENLABS_STIMME_{typ}")
            or os.environ.get("ELEVENLABS_STIMME") or "")


def sprechen(text, voice_id, ordner):
    """Text -> (wav-Pfad, Dauer in s). Zwischengespeichert nach Textinhalt."""
    if not voice_id:
        raise ElevenLabsFehler("Keine Sprechstimme: ELEVENLABS_STIMME (voice_id) fehlt")
    modell = os.environ.get("ELEVENLABS_TTS_MODELL", "eleven_multilingual_v2")
    schl = hashlib.sha1(f"{voice_id}|{modell}|{text}".encode()).hexdigest()[:12]
    mp3 = Path(ordner) / f"sprache_{schl}.mp3"
    if not mp3.exists():
        antwort = _anfrage("POST", f"/v1/text-to-speech/{voice_id}/with-timestamps",
                           params={"output_format": "mp3_44100_128"},
                           json_body={"text": text, "model_id": modell,
                                      "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35,
                                                         "use_speaker_boost": True, "speed": 0.95}})
        mp3.write_bytes(base64.b64decode(antwort["audio_base64"]))
    wav = mp3.with_suffix(".wav")
    if not wav.exists():
        _zu_wav(mp3, wav)
    return wav, _wav_dauer(wav)


# --------------------------------------------------------------------------
# Kompositionsplan

def _stile(cfg):
    nacht = any(t.get("nacht") for t in cfg["teile"].values())
    instr = [INSTRUMENT_STIL.get(cfg.get("instrument", ""), ""), INSTRUMENT_STIL.get(cfg.get("begleitung", ""), "")]
    pos = ["children's song for toddlers and preschoolers", "German lyrics, very clear German pronunciation",
           "warm, bright young female lead vocal, friendly and smiling, sung clearly and not too fast",
           "simple, catchy sing-along melody", f"{int(cfg.get('tempo', 100))} BPM",
           "polished modern kids music production, high quality, warm mix"]
    pos += [f"{i} accents" for i in instr if i]
    if nacht:
        pos += ["gentle lullaby", "soft and calm", "dreamy"]
    else:
        pos += ["cheerful", "playful", "happy"]
    if cfg.get("herkunft"):
        pos += ["traditional German folk melody", "faithful to the traditional tune"]
    pos += cfg.get("stil", [])
    neg = ["explicit content", "rap", "distorted guitars", "heavy drums", "aggressive", "dark", "sad",
           "autotune effect", "spoken word"] + cfg.get("stil_nicht", [])
    return pos[:50], neg[:50]


def _ms(sek):
    return int(round(max(3.0, min(120.0, sek)) * 1000))


def plan_bauen(cfg, lied, sprach_dauern):
    """-> (chunks, abschnitte_sek) – abschnitte_sek: [(start, ende, name, art, teil)] in Sekunden."""
    pos, neg = _stile(cfg)
    chunks, abschnitte, t = [], [], 0.0
    strophe_nr, sprich_nr = 0, 0
    for a0, a1, name, art, teil in sorted(lied.abschnitte, key=lambda a: a[0]):
        dauer = lied.sek(a1) - lied.sek(a0)
        if art == "sprechen":
            dauer = max(3.0, sprach_dauern[sprich_nr] + 1.3)
            sprich_nr += 1
            text = "{soft instrumental break, no vocals}"
            stile = pos[:] + ["instrumental only", "quiet, soft background"]
        elif art in ("intro", "zwischenspiel"):
            text = "[Intro]\n{instrumental intro, no vocals}" if art == "intro" else "{short instrumental fill}"
            stile = pos[:] + ["instrumental only"]
        elif art == "outro":
            dauer = max(dauer, (sprach_dauern[-1] + 2.5) if cfg.get("tschuess") else dauer)
            text = "[Outro]\n{gentle instrumental ending with final chord, no vocals}"
            stile = pos[:] + ["instrumental only", "ending"]
        else:
            if art == "refrain":
                kopf = "[Chorus]"
            else:
                strophe_nr += 1
                kopf = f"[Verse {strophe_nr}]"
            zeilen = [z["text"] if isinstance(z, dict) else z for z in teil["zeilen"]]
            text = kopf + "\n" + "\n".join(zeilen)
            stile = pos[:]
        ms = _ms(dauer)
        chunks.append({"text": text, "duration_ms": ms, "positive_styles": stile, "negative_styles": neg,
                       "context_adherence": "high"})
        abschnitte.append((t, t + ms / 1000, name, art, teil))
        t += ms / 1000
    return chunks, abschnitte


def lied_erzeugen(cfg, chunks, ordner):
    """Kompositionsplan -> wav (zwischengespeichert nach Planinhalt)."""
    modell = os.environ.get("ELEVENLABS_MUSIK_MODELL", "music_v2_5")
    plan = {"chunks": chunks}
    schl = hashlib.sha1(json.dumps([modell, plan], sort_keys=True).encode()).hexdigest()[:12]
    mp3 = Path(ordner) / f"lied_{schl}.mp3"
    (Path(ordner) / f"plan_{schl}.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    if not mp3.exists():
        seed = int(hashlib.sha1(cfg["titel"].encode()).hexdigest()[:7], 16)
        for fmt in ("mp3_44100_192", "mp3_44100_128"):
            try:
                daten = _anfrage("POST", "/v1/music", params={"output_format": fmt}, roh=True,
                                 json_body={"composition_plan": plan, "model_id": modell, "seed": seed})
                break
            except ElevenLabsFehler as e:
                if "output_format" not in str(e) and "tier" not in str(e).lower():
                    raise
        mp3.write_bytes(daten)
    wav = mp3.with_suffix(".wav")
    if not wav.exists():
        _zu_wav(mp3, wav)
    return wav


def ausrichten(wav_oder_mp3, text, ordner):
    schl = hashlib.sha1((Path(wav_oder_mp3).name + text).encode()).hexdigest()[:12]
    pfad = Path(ordner) / f"ausrichtung_{schl}.json"
    if not pfad.exists():
        with open(wav_oder_mp3, "rb") as f:
            antwort = _anfrage("POST", "/v1/forced-alignment", files={"file": (Path(wav_oder_mp3).name, f)},
                               data={"text": text})
        pfad.write_text(json.dumps(antwort, ensure_ascii=False))
    return json.loads(pfad.read_text())


# --------------------------------------------------------------------------
# Zeiten in das Lied-Objekt übernehmen

def _norm(w):
    return re.sub(r"[^\wäöüß]", "", w.lower())


def zeiten_uebernehmen(lied, abschnitte_sek, woerter, sprach_starts, sprach_dauern, gesamt):
    """Ersetzt die (synthetischen) Zeiten im Lied-Objekt durch die echten aus ElevenLabs."""
    import difflib
    tb = lied.beat
    lied.abschnitte = [(tb(a), tb(b), n, art, teil) for a, b, n, art, teil in abschnitte_sek]
    sung = [a for a in abschnitte_sek if a[3] not in ("intro", "outro", "sprechen", "zwischenspiel")]
    # Zeilen nach Abschnitt gruppieren (in Reihenfolge) und jedem gesungenen Abschnitt zuordnen
    gruppen, akt, letzte = [], [], None
    for z in lied.zeilen:
        if z["abschnitt"] != letzte and akt:
            gruppen.append(akt)
            akt = []
        akt.append(z)
        letzte = z["abschnitt"]
    if akt:
        gruppen.append(akt)
    for g, a in zip(gruppen, sung):
        n = len(g)
        for i, z in enumerate(g):
            z["_fenster"] = (a[0] + (a[1] - a[0]) * i / n, a[0] + (a[1] - a[0]) * (i + 1) / n)

    # Wörter des Liedtextes in Reihenfolge den ausgerichteten Wörtern zuordnen
    ziel = [(zi, wi, _norm(w)) for zi, z in enumerate(lied.zeilen) for wi, (w, _, _) in enumerate(z["woerter"])]
    quelle = [(_norm(w["text"]), w["start"], w["end"]) for w in woerter if _norm(w["text"])]
    sm = difflib.SequenceMatcher(a=[x[2] for x in ziel], b=[q[0] for q in quelle], autojunk=False)
    zeit = {}
    for blk in sm.get_matching_blocks():
        for j in range(blk.size):
            zeit[blk.a + j] = quelle[blk.b + j][1:]
    for zi, z in enumerate(lied.zeilen):
        f0, f1 = z["_fenster"]
        idx = [i for i, x in enumerate(ziel) if x[0] == zi]
        treffer = [zeit[i] for i in idx if i in zeit and f0 - 2.0 <= zeit[i][0] <= f1 + 2.0]
        if len(treffer) >= max(1, len(idx) // 2):
            start, ende = min(t[0] for t in treffer), max(t[1] for t in treffer)
        else:  # Ausrichtung unsicher -> gleichmäßig im geplanten Fenster
            start, ende = f0 + 0.1, f1 - 0.2
        neu = []
        n = len(z["woerter"])
        for wi, (w, _, _) in enumerate(z["woerter"]):
            i = next((x for x in idx if ziel[x][1] == wi), None)
            if i in zeit and start - 0.5 <= zeit[i][0] <= ende + 0.5:
                a, e = zeit[i]
            else:
                a = start + (ende - start) * wi / max(1, n)
                e = start + (ende - start) * (wi + 1) / max(1, n)
            neu.append((w, a, e))
        z["woerter"], z["start"], z["ende"] = neu, start, ende
        z.pop("_fenster", None)
    for sp, st, d in zip(lied.sprache, sprach_starts, sprach_dauern):
        sp["start"], sp["ende"] = st, st + d
    lied.effekte = []
    for z in lied.zeilen:
        lied._effekt_planen(z["info"], z)
    lied.ende_beat = tb(max(gesamt - 1.5, 1.0))


def stimm_huelle(lied, sprach_wavs, gesamt, pfad):
    """Ersatz-Stimmspur nur für die Mundbewegung: Silbenimpulse während der gesungenen Wörter
    plus die echten Sprechteile."""
    n = int((gesamt + 1) * SR)
    spur = np.zeros(n, np.float32)
    for z in lied.zeilen:
        for w, a, e in z["woerter"]:
            if a is None:
                continue
            silben = max(1, len(re.findall(r"[aeiouyäöü]+", w.lower())))
            i0, i1 = int(a * SR), min(n, int(e * SR))
            if i1 <= i0:
                continue
            t = np.arange(i1 - i0) / SR
            puls = 0.55 + 0.45 * np.abs(np.sin(np.pi * silben * t / max(1e-3, (e - a))))
            spur[i0:i1] = np.maximum(spur[i0:i1], (0.5 * puls * np.sin(2 * np.pi * 300 * t)).astype(np.float32))
    for (wav, st) in sprach_wavs:
        with wave.open(str(wav)) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
            x = x.reshape(-1, w.getnchannels()).mean(axis=1)
        i0 = int(st * SR)
        x = x[: max(0, n - i0)]
        spur[i0:i0 + len(x)] += x
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(spur, -1, 1) * 32767).astype(np.int16).tobytes())


def tonspur(cfg, lied, ordner, tmp):
    """Erzeugt alles Nötige und gibt (lied_wav, [(sprach_wav, start)], stimm_huelle_wav, gesamt) zurück.
    Passt dabei die Zeiten im Lied-Objekt an."""
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    stimme = stimme_fuer(cfg)
    texte = [sp["text"] for sp in lied.sprache]  # inkl. Abschiedstext als letzter Eintrag
    hat_tschuess = bool(cfg.get("tschuess"))
    sprach = [sprechen(t, stimme, ordner) for t in texte]
    dauern = [d for _, d in sprach]
    chunks, abschnitte = plan_bauen(cfg, lied, dauern)
    print(f"  • ElevenLabs: Lied mit {len(chunks)} Abschnitten ({abschnitte[-1][1]:.0f}s) …", flush=True)
    lied_wav = lied_erzeugen(cfg, chunks, ordner)
    laenge = _wav_dauer(lied_wav)
    gesungen = "\n".join(z["text"] for z in lied.zeilen)
    ausr = ausrichten(lied_wav.with_suffix(".mp3"), gesungen, ordner)
    print(f"  • Ausrichtung: {len(ausr.get('words', []))} Wörter, Abweichung {ausr.get('loss', 0):.2f}")
    # Sprechteile in die Instrumentalpausen legen, Abschied in das Outro
    starts = []
    pausen = [a for a in abschnitte if a[3] == "sprechen"]
    outro = next((a for a in abschnitte if a[3] == "outro"), abschnitte[-1])
    for i in range(len(texte)):
        if hat_tschuess and i == len(texte) - 1:
            starts.append(outro[0] + 1.0)
        else:
            starts.append(pausen[i][0] + 0.6 if i < len(pausen) else 0.6)
    gesamt = max(laenge, starts[-1] + dauern[-1] + 1.0) if starts else laenge
    zeiten_uebernehmen(lied, abschnitte, ausr.get("words", []), starts, dauern, gesamt)
    huelle = Path(tmp) / "stimme.wav"
    stimm_huelle(lied, [(w, s) for (w, _), s in zip(sprach, starts)], gesamt, huelle)
    (ordner / "info.json").write_text(json.dumps({
        "lied": lied_wav.name, "dauer": gesamt, "ausrichtung_abweichung": ausr.get("loss"),
        "sprechteile": [{"datei": w.name, "start": s} for (w, _), s in zip(sprach, starts)]}, indent=1))
    return lied_wav, [(w, s) for (w, _), s in zip(sprach, starts)], huelle, gesamt
