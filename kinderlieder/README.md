# Kinderlieder-Generator 🎵🐝

Erstellt **vollautomatisch und kostenlos** fertige Kinderlied-Videos für YouTube.

| Teil | womit | Kosten |
|---|---|---|
| Liedtext + Sprechtexte | Claude (KI) schreibt sie in eine `songs/*.json` | 0 € |
| Melodie | komponierte, eingängige Kinderlied-Melodien (3 Stile), passend zum Text, automatisch harmonisiert | 0 € |
| Begleitung | Glockenspiel/Marimba/Xylophon, Klavier/Gitarre, Bass, Schlagzeug (FluidSynth) | 0 € |
| Stimme | **Kinderstimme**: singt die Melodie und spricht zwischen den Strophen (espeak-ng + MBROLA, Formant-Verschiebung) | 0 € |
| Geräusche | Plopp, Tatü-Tata, Piep, Boing, Schrubb, Glitzer, Wecker, Gähnen (selbst erzeugt) | 0 € |
| Animation | Figur mit Mundbewegung, Bilder zu jeder Zeile, Zahlen mit Möhren, Sprechblasen, Tag/Nacht, Mitsing-Text | 0 € |

Pro Lied entstehen in `ausgabe/<lied>/`:

- `video.mp4`: das fertige Video (1920×1080, 30 Bilder/s)
- `vorschaubild.png`: das Thumbnail (1280×720)
- `youtube_text.txt`: Titel, Beschreibung mit Liedtext, Tags und die richtigen Upload-Einstellungen
- `lied.mp3`: nur das Lied

## Benutzung

```bash
./installieren.sh                                   # einmalig
python3 generator/erstellen.py --alle               # alle Lieder (ca. 3 Min. pro Lied)
python3 generator/erstellen.py songs/01_bella_biene_farben.json
python3 generator/erstellen.py songs/xyz.json --vorschau   # schnelle Testversion
```

## Ein neues Lied machen

Bitte Claude: *„Schreib ein neues Lied für den Kinderlieder-Generator über ‹Thema› mit ‹Figur›.“* Speichere es als
`songs/04_name.json` und starte `python3 generator/erstellen.py songs/04_name.json`.

### Aufbau der Lied-Datei

```jsonc
{
  "titel": "…", "kurztitel": "…",
  "figur": {"typ": "biene|baer|hase|katze|frosch", "name": "…", "farbe": "#…" /* optional */},
  "melodie": "A|B|C|D|E",      // A = singend, B = Fanfare, C = hüpfend, D = wiegend, E = Bogen
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
  "tschuess": "Tschüss, bis bald!"
}
```

- **Zeilen:** 7 Silben sind ideal (Melodie-Grundmaß), 5 bis 9 gehen auch (höchstens 15). Paarreime.
- **Bilder** (`bild`): `blume`, `erdbeere`, `feuerwehr`, `sonne`, `banane`, `kueken`, `himmel`, `meer`, `fisch`,
  `wecker`, `zahnbuerste`, `zahnpasta`, `zaehneputzen` (animiert), `mond`, `bett`, `sterne`, `moehre`, `haende`, `wasserhahn`, `seife`, `handtuch`, `regenbogen`, `blatt`, `frosch`, `traube`, `pflaume`
- **Teil-Optionen:**
  - `"zahlen": true`: Jedes gesungene Zahlwort (eins … zwölf, null) erscheint groß mit genau so vielen Möhren.
  - `"nacht": true`: Nachthimmel mit Mond und Sternen.
  - `"putzen": true`: Die Figur putzt sich mit einer Zahnbürste die Zähne.
  - `"seifenblasen": true`: Seifenblasen steigen im ganzen Bild auf.
  - `"melodie": [[…], …]`: eigene Tonfolge (Tonstufen 0 = do … 7 = do') pro Zeile.
- **Effekte** (`effekt`): `tatue`, `piep`, `boing`, `schrubb`, `glitzer`, `klingel`, `gaehn`, `summ`, `plopp`, `platsch`, `blubb`, `quak`.
  Bei jeder neuen Einblendung ertönt automatisch ein „Plopp“.
- Der Kanalname, der oben links im Video steht, wird in `kanal.json` eingestellt.

## Hochladen auf YouTube

1. Video und Vorschaubild hochladen.
2. Titel, Beschreibung und Tags aus `youtube_text.txt` kopieren.
3. **Zielgruppe: „Ja, speziell für Kinder“.** Das ist Pflicht.
4. „Veränderte oder synthetische Inhalte“: am besten „Ja“ angeben.

## Grenzen der kostenlosen Version

- Die Stimme ist eine **Sprachsynthese**, die auf Kinderstimme getrimmt ist: verständlich und lustig, aber immer noch hörbar
  computergeneriert. Für Studioqualität brauchst du ein bezahltes Suno-Abo (mit kommerzieller Lizenz) oder deine eigene Stimme.
- YouTube bezahlt keine massenhaft gleichförmigen Videos („inauthentische Inhalte“). Veröffentliche lieber weniger Lieder,
  die etwas beibringen.
- Lizenzen: Der FluidR3-Soundfont (MIT) und die Schrift Quicksand (OFL) sind auch kommerziell frei. Die Lizenz der
  MBROLA-Stimme de7 (DFKI) verbietet nur den Verkauf der Stimmdatenbank selbst. Bevor der Kanal Geld verdient, solltest du
  trotzdem auf eine Stimme mit eindeutiger kommerzieller Lizenz umsteigen.
