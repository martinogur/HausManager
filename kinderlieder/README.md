# Kinderlieder-Generator 🎵🐝

Erstellt **vollautomatisch und kostenlos** fertige Kinderlied-Videos für YouTube:

| Teil | womit | Kosten |
|---|---|---|
| Liedtext | Claude (KI) schreibt ihn in eine `songs/*.json` | 0 € |
| Melodie + Begleitung | wird aus dem Text automatisch komponiert (FluidSynth, freie Instrumente) | 0 € |
| Gesang | Computerstimme, die die Melodie singt (espeak-ng + MBROLA) | 0 € |
| Animation | Figur, Hintergrund und Mitsing-Text werden gezeichnet (Python/Pillow) | 0 € |
| Video | Full HD, 30 Bilder/s, MP4 (ffmpeg) | 0 € |

Pro Lied entstehen in `ausgabe/<lied>/`:

- `video.mp4`: das fertige Video (1920×1080) zum Hochladen
- `vorschaubild.png`: das Thumbnail (1280×720)
- `youtube_text.txt`: Titel, Beschreibung mit Liedtext, Tags und die richtigen Upload-Einstellungen
- `lied.mp3`: nur das Lied

## Benutzung

```bash
./installieren.sh                                   # einmalig
python3 generator/erstellen.py --alle               # alle Lieder erstellen
python3 generator/erstellen.py songs/01_bella_biene_farben.json
python3 generator/erstellen.py songs/xyz.json --vorschau   # schnelle Testversion
```

Ein Lied dauert in Full HD ungefähr 5 bis 10 Minuten.

## Ein neues Lied machen

1. Bitte Claude: *„Schreib ein neues Lied für den Kinderlieder-Generator über ‹Thema› mit ‹Figur›.“*
   Als Vorlage dient `songs/_vorlage.json.txt`.
2. Speichere es als `songs/04_name.json`.
3. Starte `python3 generator/erstellen.py songs/04_name.json`.

**Regeln für Texte:** pro Zeile 5 bis 9 Silben (höchstens 15), am besten vier Zeilen pro Teil, Paarreime.

**Einstellungen in der JSON-Datei:**

- `figur.typ`: `biene`, `baer`, `hase`, `katze` oder `frosch`. Mit `figur.farbe` (z. B. `"#ff9ec7"`) änderst du die Farbe.
- `instrument`: `glockenspiel`, `marimba`, `xylophon`, `musikbox`, `celesta`, `klavier` oder `floete`
- `begleitung`: `klavier` oder `gitarre`
- `tempo`: Schläge pro Minute, 90 bis 120 ist gut für Kinder
- `tonart`: `C`, `D`, `F` …
- `seed`: eine andere Zahl ergibt eine andere Melodie
- `zeige`: blendet links ein Wort oder eine Zahl ein. Mit `"blume": true` erscheint zusätzlich eine Blume in dieser Farbe.
  Das geht für einen ganzen Teil oder für jede Zeile einzeln (siehe `03_hopsi_hase_zaehlen.json`).

Der Kanalname, der oben links im Video steht, wird in `kanal.json` eingestellt.

## Hochladen auf YouTube

1. Video und Vorschaubild hochladen.
2. Titel, Beschreibung und Tags aus `youtube_text.txt` kopieren.
3. **Zielgruppe: „Ja, speziell für Kinder“.** Das ist Pflicht (COPPA).
4. „Veränderte oder synthetische Inhalte“: Bei einem Cartoon ist die Angabe nicht verpflichtend. Wir empfehlen trotzdem „Ja“.

## Grenzen der kostenlosen Version

- Die Stimme klingt nach **Computer bzw. Roboter**. Für einen Kinderkanal ist das als Stil in Ordnung, aber keine Studioqualität.
  Später kannst du stattdessen Suno (bezahlt, mit kommerzieller Lizenz) oder deine eigene Stimme nehmen.
- YouTube bezahlt keine massenhaft gleichförmigen Videos („inauthentische Inhalte“). Veröffentliche lieber weniger Lieder mit
  durchdachtem Inhalt, z. B. zum Lernen von Farben, Zahlen oder Routinen.
- Lizenzen: Der FluidR3-Soundfont (MIT) und die Schrift Quicksand (OFL) sind ausdrücklich auch für kommerzielle Zwecke frei.
  Die Lizenz der MBROLA-Stimme de7 (DFKI) verbietet nur, die *Stimmdatenbank selbst* zu verkaufen.
  Erzeugte Lieder sind davon nicht ausdrücklich ausgeschlossen. Bevor der Kanal Geld verdient, solltest du trotzdem
  auf eine Stimme mit klarer kommerzieller Lizenz umsteigen (z. B. ein bezahltes Suno-Abo oder deine eigene Stimme).
