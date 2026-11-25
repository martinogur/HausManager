"""Gemeinsame Technik für Lieder und Shorts: Video-Kodierung, Hall und Mastering.

- Video: x264 in hoher Qualität, Farbraum BT.709 korrekt umgerechnet und gekennzeichnet
  (sonst wirken Farben auf YouTube/Handys leicht verfälscht).
- Auflösung: Standard 1440p (bzw. 1440x2560 bei Shorts). YouTube verarbeitet Uploads ab 1440p mit
  einem besseren Codec (VP9/AV1), dadurch sieht das Video auch in 1080p und auf dem Handy schärfer aus.
  Mit LIEDERWIESE_AUFLOESUNG=1080 lässt sich das abschalten (schneller).
- Hall: echter Stereo-Faltungshall (selbst erzeugte Impulsantwort) statt einfachem Echo.
- Mastering: zweistufige Lautheitsnormalisierung auf -14 LUFS (YouTube-Standard), linear, ohne „Pumpen“.
"""
import json
import os
import subprocess
import wave
from pathlib import Path

import numpy as np

HOEHE = int(os.environ.get("LIEDERWIESE_AUFLOESUNG", "1440"))


def groesse_quer():
    return (HOEHE * 16 // 9 // 2 * 2, HOEHE)


def groesse_hoch():
    return (HOEHE, HOEHE * 16 // 9 // 2 * 2)


def video_kodierung(ziel):
    """ffmpeg-Ausgabeargumente für rgb24-Eingang + Tonspur als zweiten Eingang."""
    return ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-tune", "animation",
            "-profile:v", "high", "-g", "60", "-bf", "2",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
            "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", str(ziel)]


def hall_ir(pfad, dauer=1.4, nachhall=0.9, sr=44100, seed=5):
    """Stereo-Impulsantwort eines kleinen, warmen Raums (exponentiell abklingendes, gefiltertes Rauschen
    mit leicht unterschiedlichen Kanälen für Breite)."""
    rng = np.random.default_rng(seed)
    n = int(dauer * sr)
    t = np.arange(n) / sr
    kanaele = []
    for k in range(2):
        rausch = rng.standard_normal(n)
        # Höhen klingen schneller ab als Tiefen: zwei Bänder mit verschiedener Abklingzeit
        tief = np.convolve(rausch, np.ones(8) / 8, mode="same")
        hoch = rausch - tief
        h = tief * np.exp(-6.9 * t / nachhall) + 0.5 * hoch * np.exp(-6.9 * t / (nachhall * 0.45))
        h[: int(0.012 * sr)] *= np.linspace(0, 1, int(0.012 * sr))  # Vorverzögerung/Einblenden
        kanaele.append(h / np.sqrt(np.sum(h ** 2)))
    daten = np.stack(kanaele, axis=1)
    daten = daten / np.abs(daten).max() * 0.9
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((daten * 32767).astype(np.int16).tobytes())
    return pfad


def mastern(eingang, ausgang, dauer, einblenden=0.0, ausblenden=1.2):
    """Zweistufige, lineare Lautheitsnormalisierung auf -14 LUFS / -1,5 dBTP mit sanften Blenden."""
    blenden = (f"afade=t=in:d={einblenden},") if einblenden else ""
    blenden += f"afade=t=out:st={max(0, dauer - ausblenden):.2f}:d={ausblenden}"
    mess = subprocess.run(["ffmpeg", "-v", "info", "-i", str(eingang), "-af",
                           f"{blenden},loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    werte = json.loads(mess[mess.rindex("{"): mess.rindex("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={werte['input_i']}:"
          f"measured_TP={werte['input_tp']}:measured_LRA={werte['input_lra']}:"
          f"measured_thresh={werte['input_thresh']}:offset={werte['target_offset']}")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(eingang), "-af", f"{blenden},{ln}",
                    "-ar", "44100", "-ac", "2", str(ausgang)], check=True)


# Stimmbearbeitung: Höhen offen lassen (früher bei 10 kHz abgeschnitten), sanft entzischen, komprimieren
STIMM_FILTER = ("highpass=f=120,equalizer=f=350:t=o:w=1:g=-2,equalizer=f=3200:t=o:w=1.4:g=3,"
                "equalizer=f=7000:t=q:w=2:g=-3,equalizer=f=11000:t=o:w=1:g=1.5,"
                "acompressor=threshold=-22dB:ratio=3:attack=4:release=90:makeup=2")


def mischen(musik, stimme, effekte, ziel, tmp, musik_pegel=0.8, stimme_pegel=2.0, effekt_pegel=0.9,
            hall_anteil=0.16):
    """Musik + Stimme (+ Hall) + Geräusche zusammenmischen (noch ohne Mastering)."""
    ir = hall_ir(Path(tmp) / "hall.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(musik), "-i", str(stimme), "-i", str(effekte),
                    "-i", str(ir), "-filter_complex",
                    "[1:a]aresample=44100,asplit=3[v1][v2][v3];"
                    f"[0:a]volume={musik_pegel}[m0];"
                    "[m0][v1]sidechaincompress=threshold=0.04:ratio=3:attack=15:release=350:makeup=1[m];"
                    f"[v2]volume={stimme_pegel},pan=stereo|c0=c0|c1=c0[v];"
                    f"[v3]volume={stimme_pegel * hall_anteil},pan=stereo|c0=c0|c1=c0[vs];"
                    "[vs][3:a]afir=dry=0:wet=10:length=1[vh];"
                    f"[2:a]aresample=44100,volume={effekt_pegel}[fx];"
                    "[m][v][vh][fx]amix=inputs=4:duration=longest:normalize=0",
                    "-ar", "44100", "-ac", "2", str(ziel)], check=True)
