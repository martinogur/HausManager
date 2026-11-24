#!/usr/bin/env python3
"""Refrain-Short: schneidet aus einem fertigen Lied-Video den (ersten) Refrain heraus und macht daraus ein
Hochkant-Short (Titel oben, Video in der Mitte, Hinweis aufs ganze Lied unten, unscharfer Hintergrund).

    python3 generator/refrain_short.py ausgabe/07_bruno_baer_gute_nacht

Ergebnis: ausgabe/shorts/<lied>_refrain/short.mp4 + meta.json + beschreibung.txt
Liegt neben dem Lied schon youtube.json (Lied bereits hochgeladen), kommt der Link in die Beschreibung.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import technik as T        # noqa: E402
import youtube_meta as YM  # noqa: E402

BASIS = Path(__file__).resolve().parent.parent
SCHRIFT = BASIS / "assets" / "Quicksand-Bold.ttf"


def _esc(text):
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def ausschnitt(zeiten, max_dauer=45.0):
    """Erster Refrain (+ etwas Luft); falls zu kurz, mit dem folgenden Abschnitt."""
    ab = zeiten["abschnitte"]
    i = next((k for k, a in enumerate(ab) if a["art"] == "refrain"), None)
    if i is None:
        i = next(k for k, a in enumerate(ab) if a["art"] == "strophe")
    start = max(0.0, ab[i]["start"] - 0.6)
    ende = ab[i]["ende"] + 0.9
    if ende - start < 15 and i + 1 < len(ab):
        ende = ab[i + 1]["ende"] + 0.5
    return start, min(ende, start + max_dauer)


def erstellen(lied_ordner):
    lied_ordner = Path(lied_ordner)
    zeiten = json.loads((lied_ordner / "zeiten.json").read_text())
    meta_lied = json.loads((lied_ordner / "meta.json").read_text())
    cfg = json.loads((BASIS / "songs" / f"{lied_ordner.name}.json").read_text())
    kanal_cfg = json.loads((BASIS / "kanal.json").read_text())
    ziel = BASIS / "ausgabe" / "shorts" / f"{lied_ordner.name}_refrain"
    ziel.mkdir(parents=True, exist_ok=True)
    W, H = T.groesse_hoch()
    start, ende = ausschnitt(zeiten)
    d = ende - start
    akzent = cfg.get("akzent", "#e5398f").lstrip("#")
    titel = cfg.get("kurztitel", cfg["titel"])
    fh = int(H * 0.05)
    filt = (
        f"[0:v]split=2[a][b];"
        f"[a]scale=-2:{H},crop={W}:{H},boxblur=30:3,eq=brightness=-0.08[hg];"
        f"[b]scale={W}:-2[vg];"
        f"[hg][vg]overlay=0:(H-h)/2-{int(H * 0.02)}[m];"
        f"[m]drawtext=fontfile='{SCHRIFT}':text='{_esc(titel)}':fontsize={fh}:fontcolor=white:"
        f"borderw={int(fh * 0.14)}:bordercolor=0x{akzent}:x=(w-tw)/2:y=h*0.13,"
        f"drawtext=fontfile='{SCHRIFT}':text='Sing mit!':fontsize={int(fh * 0.8)}:fontcolor=0xffe066:"
        f"borderw={int(fh * 0.1)}:bordercolor=0x000000@0.5:x=(w-tw)/2:y=h*0.2,"
        f"drawtext=fontfile='{SCHRIFT}':text='Das ganze Lied auf dem Kanal':fontsize={int(fh * 0.7)}:"
        f"fontcolor=white:borderw={int(fh * 0.1)}:bordercolor=0x{akzent}:x=(w-tw)/2:y=h*0.8,"
        f"fade=t=in:st=0:d=0.3,fade=t=out:st={d - 0.4:.2f}:d=0.4,format=yuv420p[v];"
        f"[0:a]afade=t=in:d=0.3,afade=t=out:st={d - 0.6:.2f}:d=0.6[au]")
    video = lied_ordner / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.2f}", "-t", f"{d:.2f}", "-i", str(video),
                    "-filter_complex", filt, "-map", "[v]", "-map", "[au]",
                    *T.video_kodierung(ziel / "short.mp4")[2:]], check=True)
    lied_url = ""
    if (lied_ordner / "youtube.json").exists():
        lied_url = json.loads((lied_ordner / "youtube.json").read_text()).get("url", "")
    meta = YM.refrain_short_meta(cfg, kanal_cfg, d, lied_url)
    YM.schreiben(meta, ziel)
    print(f"  ✔ Refrain-Short {d:.0f}s → {ziel}")
    return ziel


if __name__ == "__main__":
    for o in sys.argv[1:]:
        erstellen(o)
