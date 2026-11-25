# Liederwiese-Automatik

Zwei Agenten arbeiten zusammen:

| Agent | Was er tut | Wo er läuft |
|---|---|---|
| **1. Tagesagent** | Jeden Morgen: neues Lied **und** neues Short aus `IDEEN.md` schreiben, prüfen, rendern (Video, MP3, Thumbnail, Beschreibung), dir die Dateien schicken und ins Repository pushen | Claude-Cloud (geplante Aufgabe „Liederwiese: Tagesvideo“) |
| **2. Upload-Agent** | Sobald ein neues Lied/Short gepusht wird: Gesang und Sprache bei **ElevenLabs** erzeugen, Video in 1440p rendern, **zu YouTube hochladen** (Titel, Beschreibung, Tags, Thumbnail, „Für Kinder“, „KI-Inhalt“), danach ein **Refrain-Short** mit Link zum ganzen Lied. Jeden Samstag zusätzlich ein **Sammelvideo** (~30 Minuten, mit Kapiteln) | GitHub Actions (`.github/workflows/liederwiese-youtube.yml`) |

Die Zugangsdaten (YouTube, ElevenLabs) liegen nur als **GitHub-Secrets** vor, nie im Code und nie in Claude.

### Qualität und Reichweite – was automatisch passiert

- **Ton:** Gesang und Sprechstimme von ElevenLabs (natürliche Stimme). Die Liedzeilen werden per Forced Alignment
  Wort für Wort mit dem Gesang synchronisiert (Mitsingtext, Bilder, Zahlen, Effekte). Stereo-Hall und Mastering auf
  −14 LUFS (YouTube-Standard). Ohne ElevenLabs-Schlüssel fällt der Generator auf die kostenlose Stimme zurück.
- **Bild:** 2560×1440 (Shorts 1440×2560). YouTube verarbeitet Uploads ab 1440p mit einem besseren Codec, dadurch
  sieht das Video auch in 1080p und auf dem Handy schärfer aus. Farben korrekt nach BT.709, hohe Bitrate.
- **Reichweite:** suchoptimierte Titel (Liedname zuerst), Liedtext in der Beschreibung, Klassiker (gemeinfreie
  Volkslieder) im Wechsel mit eigenen Liedern, zu jedem Lied ein Refrain-Short mit Link, wöchentlich ein langes
  Sammelvideo mit Kapitelmarken, feste Veröffentlichungszeit (`YT_VEROEFFENTLICHEN_UM`).
- **Kosten sparen:** Jede ElevenLabs-Tonspur wird im Release `liederwiese-archiv` gespeichert; erneutes Rendern
  (z. B. nach Bildkorrekturen) kostet kein Guthaben.

---

## Einmalige Einrichtung des YouTube-Uploads (ca. 20 Minuten, nur du kannst das)

1. **Google-Cloud-Projekt anlegen:** <https://console.cloud.google.com/> → „Neues Projekt“ → Name z. B. `Liederwiese Upload`.
2. **YouTube Data API v3 aktivieren:** „APIs & Dienste“ → „Bibliothek“ → „YouTube Data API v3“ → Aktivieren.
3. **OAuth-Zustimmungsbildschirm** („Google Auth Platform“):
   - Nutzertyp **Extern**, App-Name `Liederwiese Upload`, deine E-Mail als Support- und Entwickler-Kontakt.
   - Unter „Zielgruppe“ dich selbst als **Testnutzer** eintragen.
   - Danach **„App veröffentlichen“** (In Produktion) klicken. Sonst läuft der Zugang nach 7 Tagen ab. Eine Prüfung durch
     Google ist für deinen eigenen Kanal nicht nötig. Beim Anmelden erscheint dann nur ein Hinweis „App nicht überprüft“,
     den du mit „Erweitert → Weiter“ bestätigst.
4. **Zugangsdaten erstellen:** „Clients“ / „Anmeldedaten“ → „OAuth-Client-ID“ → Anwendungstyp **Desktop-App** →
   JSON herunterladen (`client_secret_….json`).
5. **Refresh-Token holen (auf deinem Computer):**
   ```bash
   pip install google-auth-oauthlib
   python3 kinderlieder/generator/youtube_token_holen.py client_secret_….json
   ```
   Melde dich im Browser mit dem Google-Konto an, **zu dem der YouTube-Kanal gehört**.
6. **Secrets in GitHub eintragen:** Repository `HausManager` → Settings → Secrets and variables → Actions →
   „New repository secret“, und zwar die drei ausgegebenen Werte `YT_CLIENT_ID`, `YT_CLIENT_SECRET` und `YT_REFRESH_TOKEN`.
7. Optional unter „Variables“:
   - `YT_SICHTBARKEIT`: `private` (Standard), `unlisted` oder `public`
   - `YT_PLAYLIST_LIEDER` / `YT_PLAYLIST_SHORTS` / `YT_PLAYLIST_SAMMLUNG`: Playlist-IDs (aus der Playlist-URL `list=…`)
   - `YT_VEROEFFENTLICHEN_UM`: z. B. `16:30` – Videos werden zur nächsten solchen Uhrzeit (deutsche Zeit) öffentlich.
     Empfehlung: Lieder `16:30` (nach der Kita), Shorts mit `YT_VEROEFFENTLICHEN_UM_SHORTS` z. B. `07:30`.
     Wirkt nur mit `YT_SICHTBARKEIT=public`, also erst nach der Google-Prüfung (siehe unten).
   - `SAMMEL_MINUTEN`: Länge des wöchentlichen Sammelvideos (Standard 30)

## Einrichtung ElevenLabs (natürlicher Gesang und Sprechstimme, ca. 10 Minuten)

1. Konto auf <https://elevenlabs.io> anlegen und ein **bezahltes Abo** wählen (erst ab einem bezahlten Abo dürfen
   Musik und Stimmen kommerziell genutzt werden). Ein Lied von ~3 Minuten verbraucht ~3 Musik-Minuten; prüfe auf
   <https://elevenlabs.io/pricing>, welches Abo zu ~1 Lied pro Tag passt (+ Sprachzeichen für Shorts).
2. Profil → „API Keys“ → neuen Schlüssel erstellen (Rechte: Text to Speech, Music, Forced Alignment).
3. GitHub → Settings → Secrets and variables → Actions:
   - **Secret** `ELEVENLABS_API_KEY` = der Schlüssel
   - **Variable** `ELEVENLABS_STIMME` = `voice_id` der Sprechstimme (freundliche, warme, deutsche Erzählerstimme aus der
     Voice Library; die ID steht in der Stimm-Ansicht). Optional je Figur: `ELEVENLABS_STIMME_BIENE`,
     `ELEVENLABS_STIMME_BAER`, `ELEVENLABS_STIMME_HASE`.
4. Fertig. Der nächste Push erzeugt Lied und Short mit ElevenLabs. Im Workflow-Ergebnis steht je Lied die
   „Abweichung“ der Wortsynchronisation (kleiner ist besser); bei auffällig hohen Werten das Video kurz prüfen.

**Solange kein ElevenLabs-Schlüssel eingetragen ist** (aktueller Stand), nutzen Tagesagent und GitHub Actions
automatisch die bisherige kostenlose Stimme (MBROLA). Es muss dafür nichts umgestellt werden; sobald das Secret
`ELEVENLABS_API_KEY` existiert, singt in GitHub Actions automatisch ElevenLabs. Der Tagesagent in Claude rendert
immer mit der kostenlosen Stimme (er hat keinen Schlüssel).

**Testen:** GitHub → Actions → „Liederwiese YouTube“ → „Run workflow“ → bei `dateien` z. B.
`kinderlieder/shorts/01_rate_mal_essen.json` eintragen.

### Wichtig zu „automatisch posten“

- **Google sperrt Uploads aus neuen, ungeprüften API-Projekten auf „Privat“.** Die Videos landen also zuerst privat in
  deinem YouTube Studio, und du schaltest sie dort mit einem Klick auf „Öffentlich“ (oder planst sie). Damit Uploads direkt
  öffentlich erscheinen, musst du das Projekt einmal prüfen lassen: [YouTube API Services Audit](https://support.google.com/youtube/contact/yt_api_form).
  Danach `YT_SICHTBARKEIT` auf `public` setzen.
- **Empfehlung:** Auch nach der Prüfung lieber `private` lassen und jedes Video vor dem Veröffentlichen einmal ansehen und
  anhören. Das schützt vor Fehlern, und YouTube vergütet keine ungeprüft massenhaft erzeugten Inhalte.
- Ein Upload verbraucht 1.600 von 10.000 Einheiten des täglichen API-Kontingents. Bis zu 6 Videos pro Tag sind also möglich.
- Das eigene Thumbnail funktioniert erst, wenn dein Kanal per Telefonnummer bestätigt ist (YouTube Studio → Einstellungen →
  Kanal → Funktionsberechtigung).

---

## Arbeitsanweisung für den Tagesagenten

> Diese Anleitung befolgt die geplante Aufgabe jeden Morgen. Sie darf von dir (Mensch) angepasst werden.

### 0. Vorbereitung
- Repository `martinogur/HausManager` verwenden und mit dem Branch `claude/brave-lovelace-klsf6s` arbeiten
  (`git fetch origin claude/brave-lovelace-klsf6s && git checkout claude/brave-lovelace-klsf6s && git pull`).
  Falls das Pushen dorthin nicht erlaubt ist: auf den Branch pushen, den die Sitzung vorgibt.
- Programme prüfen: `which espeak-ng mbrola fluidsynth ffmpeg`. Falls etwas fehlt:
  `apt-get install -y ffmpeg fluidsynth fluid-soundfont-gm espeak-ng mbrola mbrola-de7 && pip install mido numpy pillow`.
- Arbeitsverzeichnis: `kinderlieder/`. `README.md` lesen (Dateiformat, Bilder, Effekte, Melodien).

### 1. Lied schreiben
- **Auswahl:** im Wechsel ein **Klassiker** (erste offene Idee unter „Klassiker“) und ein **eigenes Lied** (erste offene
  Idee unter „Eigene Lieder“). Steht ein Klassiker zur Jahreszeit an (z. B. Nikolaus vor dem 6.12., Winterlieder im
  Dezember), hat er Vorrang. Nächste freie Nummer verwenden: `songs/NN_figur_thema.json`.
- **Klassiker:**
  - Nur gemeinfreie Lieder (Urheber seit über 70 Jahren tot oder volkstümlich), traditioneller Text in der bekannten
    Fassung, keine Zusatzstrophen moderner Bearbeiter. Bei Zweifel an der Herkunft: Lied überspringen und das im
    Bericht sagen.
  - `"herkunft"` eintragen (z. B. `"Text: Hoffmann von Fallersleben (†1874), Melodie: volkstümlich"`).
  - `"kurztitel"` = genau der bekannte Liedname (danach suchen Eltern), `"titel"` = Liedname + Figur.
  - Die traditionelle Melodie als eigene Tonfolge eintragen (`"melodie": [[…], …]` je Teil, Tonstufen 0 = do …
    7 = do'), damit auch die Vorschau richtig klingt. Silbenzahl je Zeile kann vom Original abweichen
    (6–8-Silben-Regel gilt hier nicht).
  - Sprechteile und Bilder wie bei eigenen Liedern (eigene Figuren Bella, Bruno, Hopsi).
- **Suchbegriffe:** `"suchbegriffe"` mit 3–6 Begriffen, nach denen Eltern suchen würden (z. B. `"Hänschen klein"`,
  `"Hänschen klein Kinderlied"`, `"Hänschen klein Text"`). Sie kommen zuerst in die Tags.
- **Qualität:**
  - Zielgruppe 2 bis 6 Jahre.
  - Jede Zeile hat 7 Silben (6 bis 8 sind okay), mit reinen Paarreimen.
  - Einfache Wörter, viel Wiederholung, ein klares Lernziel.
  - Ein Refrain mit 4 Zeilen, 2 bis 3 Strophen mit je 4 Zeilen.
  - Kurze, freundliche Sprechteile mit einer Frage an die Kinder.
  - Ein `tschuess` mit einer kurzen Zusammenfassung des Gelernten.
  - Jede Zeile einer Strophe bekommt ein passendes `bild`. Effekte nur dort, wo sie zum Text passen.
- **Abwechslung:**
  - Eine Melodie (`A` bis `F`), die in den letzten zwei Liedern nicht vorkam.
  - Ein anderes Instrument und eine andere Akzentfarbe als im letzten Lied.
  - Die Figur passend zur Idee wählen (Bella, Bruno oder Hopsi; `katze`/`frosch` als neue Freunde erlaubt).
  - Länge 2 bis 3:30 Minuten.
- **Verboten:**
  - Geschützte Lieder, Melodien, Aufnahmen oder Figuren nachahmen (z. B. Disney, Peppa, LooLoo Kids, Cocomelon,
    moderne Kinderlieder von lebenden oder vor weniger als 70 Jahren gestorbenen Autoren). Gemeinfreie Klassiker
    (siehe oben) sind erlaubt.
  - Videos anderer Kanäle wiederverwenden oder nachbauen.
  - Markennamen, Angst machende, gefährliche oder abwertende Inhalte.
  - Aufrufe an Kinder, etwas zu kaufen oder zu abonnieren.
- **Neue Bilder:** Wenn ein benötigtes Bild fehlt, eine neue Zeichenfunktion in `generator/bilder.py` im Stil der vorhandenen
  ergänzen (in `ZEICHNER` eintragen, animierte auch in `ANIMIERT`). Dann ein Kontaktbild rendern und **ansehen**, ob es
  eindeutig erkennbar ist. Bei Bedarf verbessern.
- `python3 generator/pruefen.py songs/NN_….json` muss ohne ✘ durchlaufen. Warnungen beheben, wo sinnvoll.

### 2. Short schreiben
- Die erste offene Idee unter „Shorts“ in `IDEEN.md` nehmen. Datei `shorts/NN_thema.json` (Format: siehe vorhandene Shorts).
- Es gibt 4 bis 5 Rätsel, das Short ist kürzer als 59 Sekunden.
- Die Figur wechselt gegenüber dem letzten Short.
- Lustige Antworten mit Geräusch-Wörtern („Ein Ball! Boing, boing!“).
- `python3 generator/pruefen.py shorts/NN_….json` muss ohne ✘ durchlaufen.

### 3. Rendern und Qualität prüfen
0. Lokal immer mit der kostenlosen Stimme rendern (`export LIEDERWIESE_KLANG=synth`), damit kein ElevenLabs-Guthaben
   doppelt verbraucht wird. Die Endfassung mit ElevenLabs macht GitHub Actions.
1. `python3 generator/erstellen.py songs/NN_….json --vorschau` ausführen. Danach aus `ausgabe/NN_…/vorschau.mp4` je
   Abschnitt ein Standbild ziehen (`ffmpeg -ss <sek> … -frames:v 1`) und **ansehen**:
   - Passt jedes Bild zur Zeile?
   - Ist der Text lesbar?
   - Verdeckt nichts die Figur oder den Text?
   Fehler beheben und neu prüfen.
2. Tonhöhe stichprobenartig prüfen (Autokorrelation der Stimmspur, wie in früheren Sitzungen). Alle Töne sollten auf
   ±0,6 Halbtöne genau sitzen.
3. Endfassung: `python3 generator/erstellen.py songs/NN_….json` und `python3 generator/short.py shorts/NN_….json`.
   Danach `vorschau.mp4` löschen.
4. Ergebnis je Lied: `video.mp4`, `lied.mp3`, `vorschaubild.png`, `beschreibung.txt`, `meta.json`.
   Je Short: `short.mp4`, `beschreibung.txt`, `meta.json`.

### 4. Abschließen
- In `IDEEN.md` beide Ideen auf `[x]` setzen und unter „Erledigt“ eintragen: `JJJJ-MM-TT – Titel – Datei`.
- Committen (nur Quelldateien: JSON, `bilder.py` usw., **keine** Videos, `ausgabe/` ist ignoriert) und pushen. Der Push
  startet automatisch den Upload-Agenten (GitHub Actions).
- Dem Nutzer mit `SendUserFile` (status `proactive`) schicken:
  - vom Lied: `video.mp4`, `lied.mp3`, `vorschaubild.png`, `beschreibung.txt`
  - vom Short: `short.mp4`
- Eine kurze Zusammenfassung auf Deutsch schreiben: Titel, Inhalt, Länge, was neu ist, ob etwas auffiel.
  Ehrlich sagen, dass der Ton nicht angehört, sondern nur technisch geprüft wurde. Das Refrain-Short entsteht
  automatisch in GitHub Actions, das Sammelvideo samstags. Nur falls der Nutzer ElevenLabs eingerichtet hat: sagen,
  dass die geschickten Dateien eine Vorschau mit der kostenlosen Stimme sind und die ElevenLabs-Fassung aus
  GitHub Actions kommt.
- **Nicht** selbst zu YouTube hochladen, keine Zugangsdaten anfassen, nichts löschen, was nicht vom Agenten selbst stammt.
