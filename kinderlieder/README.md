# Kinderlieder-Generator 🎵🐝

Erstellt **vollautomatisch und kostenlos** fertige Kinderlied-Videos für YouTube.

| Teil | womit | Kosten |
|---|---|---|
| Liedtext + Sprechtexte | Claude (KI) schreibt sie in eine `songs/*.json` | 0 € |
| Melodie | komponierte, eingängige Kinderlied-Melodien (3 Stile), passend zum Text, automatisch harmonisiert | 0 € |
| Begleitung | Glockenspiel/Marimba/Xylophon, Klavier/Gitarre, Bass, Schlagzeug (FluidSynth) | 0 € |
| Gesang + Sprechstimme | **ElevenLabs** (Eleven Music + Text-to-Speech, natürliche Stimme; Wortzeiten per Forced Alignment). Ohne Schlüssel: kostenlose Kinderstimme (espeak-ng + MBROLA) | Abo ElevenLabs / 0 € |
| Geräusche | Plopp, Tatü-Tata, Piep, Boing, Schrubb, Glitzer, Wecker, Gähnen (selbst erzeugt) | 0 € |
| Animation | Figur mit Mundbewegung, Bilder zu jeder Zeile, Zahlen mit Möhren, Sprechblasen, Tag/Nacht, Mitsing-Text | 0 € |

Pro Lied entstehen in `ausgabe/<lied>/`:

- `video.mp4`: das fertige Video (2560×1440, 30 Bilder/s, BT.709; mit `LIEDERWIESE_AUFLOESUNG=1080` 1920×1080)
- `vorschaubild.png`: das Thumbnail (1280×720)
- `youtube_text.txt`: Titel, Beschreibung mit Liedtext, Tags und die richtigen Upload-Einstellungen
- `lied.mp3`: nur das Lied

## Automatik

Jeden Morgen ein neues Lied + Short und automatischer YouTube-Upload: siehe **[AUTOMATIK.md](AUTOMATIK.md)** (Themenliste in [IDEEN.md](IDEEN.md)).

## Benutzung

```bash
./installieren.sh                                   # einmalig
python3 generator/erstellen.py --alle               # alle Lieder (ca. 3 Min. pro Lied)
python3 generator/erstellen.py songs/01_bella_biene_farben.json
python3 generator/erstellen.py songs/xyz.json --vorschau   # schnelle Testversion
```

### Weitere Werkzeuge

```bash
python3 generator/refrain_short.py ausgabe/07_xyz            # Refrain-Short (hochkant) aus dem fertigen Lied
python3 generator/sammelvideo.py --ordner ausgabe/archiv --minuten 30   # langer Mix mit Kapitelmarken
LIEDERWIESE_KLANG=synth python3 generator/erstellen.py …    # kostenlose Stimme erzwingen (z. B. für Vorschauen)
```

## Ein neues Lied machen

Bitte Claude: *„Schreib ein neues Lied für den Kinderlieder-Generator über ‹Thema› mit ‹Figur›.“* Speichere es als
`songs/04_name.json` und starte `python3 generator/erstellen.py songs/04_name.json`.

### Aufbau der Lied-Datei

```jsonc
{
  "titel": "…", "kurztitel": "…",
  "figur": {"typ": "biene|baer|hase|katze|frosch", "name": "…", "farbe": "#…" /* optional */},
  "melodie": "A|B|C|D|E|F",    // A = singend, B = Fanfare, C = hüpfend, D = wiegend, E = Bogen, F = verspielt
  "tempo": 100, "tonart": "C|D|F|G…",
  "instrument": "glockenspiel|marimba|xylophon|musikbox|celesta|klavier|floete",
  "begleitung": "klavier|gitarre",
  "akzent": "#e5398f",         // Farbe für Titel und Mitsing-Text
  "teile": {
    "refrain": {"art": "refrain", "zeilen": ["…", "…", "…", "…"]},
    "rot": {"art": "strophe", "farbe": "#e53935", "wort": "ROT", "zeilen": [
      {"text": "…", "bild": "blume", "landen": true},
      {"text": "…", "bild": "feuerwehr", "effekt": "tatue"},
      {"text": "…", "effekt": {"typ": "piep", "wort": "piep"}}
    ]}
  },
  "ablauf": [{"sprich": "Hallo Kinder! …"}, "refrain", {"sprich": "…"}, "rot", "refrain"],
  "tschuess": "Tschüss, bis bald!",
  "suchbegriffe": ["…"],       // Begriffe, nach denen Eltern suchen (kommen zuerst in die Tags)
  "herkunft": "…",             // nur bei gemeinfreien Klassikern: Urheber + Todesjahr bzw. „volkstümlich“
  "stil": ["…"],               // optional: zusätzliche (englische) Stilangaben für ElevenLabs
  "klang": "auto"              // auto | elevenlabs | synth
}
```

- **Zeilen:** 7 Silben sind ideal (Melodie-Grundmaß), 5 bis 9 gehen auch (höchstens 15). Paarreime.
- **Bilder** (`bild`): `blume`, `erdbeere`, `feuerwehr`, `sonne`, `banane`, `kueken`, `himmel`, `meer`, `fisch`,
  `wecker`, `zahnbuerste`, `zahnpasta`, `zaehneputzen` (animiert), `mond`, `bett`, `sterne`, `moehre`, `haende`, `wasserhahn`, `seife`, `handtuch`, `regenbogen`, `blatt`, `frosch`, `traube`, `pflaume`, `kreis`, `dreieck`, `viereck`, `formen`, `ball`, `partyhut`, `pizza`, `fenster`, `geschenk`, `kuscheltier` (Schäfchen), `schaf`, `lampe` (Nachtlicht), `buch`
- **Teil-Optionen:**
  - `"zahlen": true` (für einen Teil oder eine einzelne Zeile): Jedes gesungene Zahlwort (eins … zwölf, null) erscheint groß mit genau so vielen Möhren. Mit `"zaehlobjekt": "punkt"` werden stattdessen Punkte gezeigt, mit `"schaf"` Schäfchen.
  - `"nacht": true`: Nachthimmel mit Mond und Sternen. Geht auch bei Sprechteilen (`{"sprich": "…", "nacht": true}`);
    `"ende_nacht": true` (oberste Ebene) zeigt auch den Schluss nachts.
  - `"putzen": true`: Die Figur putzt sich mit einer Zahnbürste die Zähne.
  - `"seifenblasen": true`: Seifenblasen steigen im ganzen Bild auf.
  - `"melodie": [[…], …]`: eigene Tonfolge (Tonstufen 0 = do … 7 = do') pro Zeile.
- **Effekte** (`effekt`): `tatue`, `piep`, `boing`, `schrubb`, `glitzer`, `klingel`, `gaehn`, `summ`, `plopp`, `platsch`, `blubb`, `quak`.
  Bei jeder neuen Einblendung ertönt automatisch ein „Plopp“.
- **Vorschaubild:** `"vorschau_nacht": true` zeigt es als Nachtbild, `"vorschau_bilder": ["…", "…", "…"]` wählt die drei Bilder unten links selbst aus.
- Der Kanalname, der oben links im Video steht, wird in `kanal.json` eingestellt.

## Hochladen auf YouTube

1. Video und Vorschaubild hochladen.
2. Titel, Beschreibung und Tags aus `youtube_text.txt` kopieren.
3. **Zielgruppe: „Ja, speziell für Kinder“.** Das ist Pflicht.
4. „Veränderte oder synthetische Inhalte“: am besten „Ja“ angeben.

## Grenzen

- ElevenLabs erzeugt die Melodie selbst. Bei Klassikern wird die traditionelle Melodie im Stil verlangt, aber nicht
  garantiert; die ersten Klassiker daher anhören. Ohne passenden Gesang: `"klang": "synth"` setzen.

## Grenzen der kostenlosen Version

- Die Stimme ist eine **Sprachsynthese**, die auf Kinderstimme getrimmt ist: verständlich und lustig, aber immer noch hörbar
  computergeneriert. Für Studioqualität brauchst du ein bezahltes Suno-Abo (mit kommerzieller Lizenz) oder deine eigene Stimme.
- YouTube bezahlt keine massenhaft gleichförmigen Videos („inauthentische Inhalte“). Veröffentliche lieber weniger Lieder,
  die etwas beibringen.
- Lizenzen: Der FluidR3-Soundfont (MIT) und die Schrift Quicksand (OFL) sind auch kommerziell frei. Die Lizenz der
  MBROLA-Stimme de7 (DFKI) verbietet nur den Verkauf der Stimmdatenbank selbst. Bevor der Kanal Geld verdient, solltest du
  trotzdem auf eine Stimme mit eindeutiger kommerzieller Lizenz umsteigen.

## Shorts („Rate mal!“-Quiz, hochkant)

```bash
python3 generator/short.py --alle                          # alle Shorts in shorts/
python3 generator/short.py shorts/01_rate_mal_essen.json
```

Ergebnis: `ausgabe/shorts/<name>/short.mp4` (1080×1920, 30 bis 45 Sekunden) und `youtube_text.txt`.

**Ablauf pro Rätsel:** Schattenbild erscheint mit „?“ → Figur fragt → Countdown 3-2-1 (Ticken) → Auflösung mit
Strahlen, Konfetti und Tusch → Figur sagt die Antwort. Danach kommt das nächste Rätsel. Das Ende („Wie viele hast du
erraten?“) geht nahtlos in den Anfang über, damit das Short in Schleife läuft.

**Warum das funktioniert:** Gleich im ersten Bild steht eine Frage (Aufhänger), Kinder raten aktiv mit, alle 6 bis 7
Sekunden passiert etwas Neues, und das Video ist kurz und läuft gern mehrmals.

Aufbau der Datei (`shorts/*.json`): `titel`, `figur`, `banner`, `akzent`, `palette` (0–4), `tempo`, `instrument`,
`start` (erste Frage), `fragen` (weitere Fragen), `dinge` (Liste mit `bild`, `wort`, `antwort`, `farbe`), `ende`.
Als `bild` gehen alle Bilder von oben sowie `figur:biene`, `figur:baer`, `figur:hase`, `figur:katze` und `figur:frosch`.
Mit **4 bis 5 Rätseln** bleibt das Short unter 60 Sekunden.
