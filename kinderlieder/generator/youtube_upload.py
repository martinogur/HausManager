#!/usr/bin/env python3
"""Lädt fertige Videos (ausgabe/<name>/ mit meta.json) zu YouTube hoch.

Zugangsdaten kommen aus Umgebungsvariablen (in GitHub als Secrets hinterlegt, nie im Code):
    YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Optional:
    YT_SICHTBARKEIT  private | unlisted | public   (Standard: private)
    YT_PLAYLIST_LIEDER, YT_PLAYLIST_SHORTS, YT_PLAYLIST_SAMMLUNG   Playlist-IDs, in die neue Videos kommen
    YT_VEROEFFENTLICHEN_UM   z. B. "16:30" (Uhrzeit Deutschland): Videos werden privat hochgeladen und zur
                             nächsten solchen Uhrzeit automatisch öffentlich (nur wirksam mit YT_SICHTBARKEIT=public;
                             funktioniert erst, wenn das API-Projekt von Google geprüft ist)

    python3 generator/youtube_upload.py ausgabe/07_irgendwas ausgabe/shorts/04_xyz
"""
import datetime
import json
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]


def youtube():
    fehlt = [k for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN") if not os.environ.get(k)]
    if fehlt:
        raise SystemExit(f"Fehlende Zugangsdaten: {', '.join(fehlt)} (siehe AUTOMATIK.md)")
    cred = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
                       client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
                       token_uri="https://oauth2.googleapis.com/token", scopes=SCOPES)
    return build("youtube", "v3", credentials=cred, cache_discovery=False)


def veroeffentlichungszeit(uhrzeit, jetzt=None):
    """Nächster Zeitpunkt „HH:MM“ (Deutschland), mindestens 30 Minuten in der Zukunft, als UTC-ISO-String."""
    zone = ZoneInfo("Europe/Berlin")
    jetzt = jetzt or datetime.datetime.now(zone)
    h, m = (int(x) for x in uhrzeit.split(":"))
    ziel = jetzt.replace(hour=h, minute=m, second=0, microsecond=0)
    if ziel < jetzt + datetime.timedelta(minutes=30):
        ziel += datetime.timedelta(days=1)
    return ziel.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hochladen(yt, ordner):
    ordner = Path(ordner)
    meta = json.loads((ordner / "meta.json").read_text())
    video = ordner / ("short.mp4" if meta.get("art") == "short" else "video.mp4")
    sicht = os.environ.get("YT_SICHTBARKEIT", "private")
    body = {
        "snippet": {"title": meta["titel"], "description": meta["beschreibung"], "tags": meta["tags"][:30],
                    "categoryId": meta.get("kategorie", "27"), "defaultLanguage": "de",
                    "defaultAudioLanguage": "de"},
        "status": {"privacyStatus": sicht, "selfDeclaredMadeForKids": True,
                   "containsSyntheticMedia": bool(meta.get("ki_inhalt", True)), "embeddable": True},
    }
    um = os.environ.get("YT_VEROEFFENTLICHEN_UM", "").strip()
    if um and sicht == "public":
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = veroeffentlichungszeit(um)
        sicht = f"geplant {body['status']['publishAt']}"
    print(f"⬆ {meta['titel']} ({sicht})")
    anfrage = yt.videos().insert(part="snippet,status", body=body,
                                 media_body=MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True))
    antwort = None
    while antwort is None:
        status, antwort = anfrage.next_chunk()
        if status:
            print(f"   {int(status.progress() * 100)} %")
    vid = antwort["id"]
    print(f"   ✔ https://youtu.be/{vid}")
    bild = ordner / "vorschaubild.png"
    if bild.exists() and meta.get("art") != "short":
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(bild))).execute()
            print("   ✔ Thumbnail gesetzt")
        except HttpError as e:
            print(f"   ⚠ Thumbnail nicht gesetzt (Kanal evtl. noch nicht per Telefon bestätigt): {e.reason}")
    pl = {"short": os.environ.get("YT_PLAYLIST_SHORTS"),
          "sammlung": os.environ.get("YT_PLAYLIST_SAMMLUNG") or os.environ.get("YT_PLAYLIST_LIEDER")
          }.get(meta.get("art"), os.environ.get("YT_PLAYLIST_LIEDER"))
    if pl:
        try:
            yt.playlistItems().insert(part="snippet", body={"snippet": {
                "playlistId": pl, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
            print("   ✔ zur Playlist hinzugefügt")
        except HttpError as e:
            print(f"   ⚠ Playlist: {e.reason}")
    (ordner / "youtube.json").write_text(json.dumps({"video_id": vid, "url": f"https://youtu.be/{vid}",
                                                     "sichtbarkeit": sicht}, indent=2))
    return vid


def main():
    ordner = sys.argv[1:]
    if not ordner:
        raise SystemExit(__doc__)
    yt = youtube()
    fehler = 0
    for o in ordner:
        try:
            hochladen(yt, o)
        except HttpError as e:
            fehler += 1
            print(f"   ✘ Upload fehlgeschlagen für {o}: {e}")
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
