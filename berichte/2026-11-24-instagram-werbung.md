# Bericht 24.11.2026 – instagram-manager: Werbung, automatisch posten, Profil

## Was wurde gemacht
1. **Werbekampagne (Meta-Anzeigen)** – `marketing/instagram/werbung/kampagne.md`
   - Ziel „Interaktion“ → WhatsApp-Unterhaltungen (05241 3389748); Plan B Website-Klicks mit URL-Kennung.
   - Zielgruppe Gütersloh + 25 km, 30–65+, Interessen als Vorschlag.
   - 3 Anzeigen (A Winterdienst, B Ein Ansprechpartner, C Kostenlose Besichtigung) mit Primärtext, Überschrift, Beschreibung, Button,
     vorausgefüllter WhatsApp-Nachricht mit Kennung „(Anzeige A/B/C)“.
   - Grafiken aus `marketing/instagram/werbung/anzeigen.json`, gerendert und geprüft (lange Titel verkleinert):
     - A: `marketing/instagram/werbung/grafiken/anzeigen/A-winterdienst-feed/folie-01.png`, `…/A-winterdienst-story/folie-01.png`, `…/A-winterdienst-reel/reel.mp4`
     - B: `…/B-ansprechpartner-feed/folie-01.png`, `…/B-ansprechpartner-story/folie-01.png`, `…/B-ansprechpartner-reel/reel.mp4`
     - C: `…/C-besichtigung-feed/folie-01.png`, `…/C-besichtigung-story/folie-01.png`, `…/C-besichtigung-reel/reel.mp4`
   - Budget: 9 €/Tag (3 Anzeigengruppen × 3 €) für 14 Tage ≈ 126 €; Sparvariante 5 €/Tag ≈ 70 €. Umschicht-Regeln (Tag 3/7/14), Kennzahlen, Auswertungstabelle.
   - Schritt-für-Schritt-Anleitung für den Werbeanzeigenmanager inkl. Business-Konto, Facebook-Seite, WhatsApp-Verknüpfung.
2. **Automatisch posten** – `marketing/instagram/automatisch-posten.md`
   - Weg 1: Meta Business Suite Planer (4 Posts in ca. 10 Min.; Reel mit Trend-Sound über die Instagram-App planen).
   - Weg 2: Instagram Graph API (Voraussetzungen, Token, öffentliche JPEG-URLs, Limits laut Meta-Doku, wöchentlicher Ablauf mit Freigabe). Nur beschrieben, nichts eingerichtet.
   - Kommentar-/DM-Automatisierung als Option (Stichwort „WINTER“ → private Antwort), mit Metas Regeln (1 Antwort/Kommentar, 7 Tage, 24-h-Fenster). Kein ungefragtes Massen-Anschreiben.
3. **Profil** – `marketing/instagram/profil.md`, neuer Abschnitt 7 „In 15 Minuten einrichten“ (Business-Konto, Kategorie, Facebook-Seite, Bio zum Kopieren, Kontakt-Buttons, Links inkl. Impressum, erste 3 Posts mit Anheften, Highlights mit den Covern, Test).
4. **Werkzeug** – `marketing/instagram/grafik.py` erweitert (abwärtskompatibel, KW48 neu gerendert ohne Fehler):
   neue Folienart `anzeige` (Einzelbild mit Button), Option `story_rand` (Sicherheitsrand für Story/Reel-Bedienelemente),
   Folien-Option `schrift` (Titelgröße erzwingen), kein Zähler „1/1“ bei Einzelbildern, kein Video bei Einzelbild-Reels.

## Was braucht Freigabe
- Die 3 Anzeigen (Texte + Grafiken) und das Budget.
- Ob Anzeigen mit „Sie“ (so entworfen) oder „du“ laufen sollen.
- Weg 2 (automatisches Posten) nur nach ausdrücklicher Erlaubnis für Instagram + Wochenfreigabe.

## Fragen an den Inhaber
1. Ist WhatsApp Business auf der Festnetznummer 05241 3389748 eingerichtet und lässt es sich mit der Facebook-Seite verknüpfen? (Sonst Plan B Website-Klicks.)
2. Gibt es schon eine Facebook-Seite und einen Instagram-Benutzernamen?
3. Einsatzradius 25 km bestätigt?
4. Welches Budget: 5, 9 oder 10 €/Tag? Welcher Zielwert „Kosten pro echte Anfrage“ ist okay?
5. Gibt es eine Winterdienst-Unterseite und die genaue Impressum-URL?
6. Für Weg 2: Wo sollen die Bilder öffentlich liegen (Ordner `/ig/` auf der Webseite mit Dauer-Erlaubnis oder separater Speicher)?
7. KW48-Posts sprechen von „Einsatzprotokoll“ beim Winterdienst – das steht nicht in `firma/profil.md`. Stimmt das? (In den Anzeigen weggelassen.)
8. Logo-Datei für das Profilbild?

Nichts committet, nichts veröffentlicht.
