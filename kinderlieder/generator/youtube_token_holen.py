#!/usr/bin/env python3
"""EINMALIG auf deinem eigenen Computer ausführen, um den YouTube-Zugang (Refresh-Token) zu erzeugen.

1. pip install google-auth-oauthlib
2. Die von Google heruntergeladene Datei client_secret_….json neben dieses Skript legen
3. python3 youtube_token_holen.py client_secret_….json
4. Im Browser mit dem Google-Konto des YouTube-Kanals anmelden und zustimmen
5. Die drei ausgegebenen Werte als GitHub-Secrets eintragen (siehe AUTOMATIK.md)

Die Werte sind geheim: nicht in Chats, E-Mails oder Dateien im Repository kopieren.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    datei = sys.argv[1]
    flow = InstalledAppFlow.from_client_secrets_file(datei, SCOPES)
    cred = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    info = json.load(open(datei))
    info = info.get("installed") or info.get("web")
    print("\nTrage diese drei Werte in GitHub ein (Settings → Secrets and variables → Actions → New repository secret):\n")
    print(f"YT_CLIENT_ID      = {info['client_id']}")
    print(f"YT_CLIENT_SECRET  = {info['client_secret']}")
    print(f"YT_REFRESH_TOKEN  = {cred.refresh_token}")


if __name__ == "__main__":
    main()
