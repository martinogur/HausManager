# Bewertungen – legal und automatisch

| Baustein | Datei | Status |
|---|---|---|
| Weiterleitungsseite (Ziel aller QR-Codes und Links) | `webseite/build.py` → `bewertung.html` | fertig, Google-Link wird eingetragen, sobald das Profil steht |
| Druck: A6-Karte zum Hinterlassen beim Kunden, Visitenkarte (Rückseite mit QR) | `druck/karte-a6.pdf`, `druck/visitenkarte.pdf` (neu erzeugen: `python marketing/bewertungen/karten.py`) | fertig |
| Nachrichten (Bitte, Erinnerung, Antworten) | `vorlagen.md` | fertig |
| Liste aller Anfragen | `anfragen.csv` | wird vom Agenten gepflegt |
| Agent | `.claude/agents/bewertungs-manager.md` | läuft donnerstags mit dem SEO-Lauf |
| Automatik im Portal (Phase 4) | Bitte automatisch nach „Einsatz erledigt“, Erinnerung nach 5 Tagen, Übersicht im Dashboard | geplant |

**Sobald das Google-Profil existiert:** Google-Unternehmensprofil → „Bewertungen erhalten“ → Link kopieren → an Claude schicken.
Dann wird `FIRMA["google_bewertung"]` gesetzt, und die Seite geht nach Freigabe online.
