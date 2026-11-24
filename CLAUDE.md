# Hausmeister Helden – Wachstumszentrale

Dieses Repository ist die Arbeitszentrale für das Wachstum der Firma **Hausmeister Helden**.
Hier arbeitet ein Team aus spezialisierten KI-Agenten (`.claude/agents/`), die Aufträge,
Kunden, Reichweite und Umsatz steigern.

## Immer zuerst lesen
- `firma/profil.md` – alle Firmendaten (Leistungen, Region, Preise, Kontakt, Ton).
  Kein Agent erfindet Firmendaten. Fehlt etwas, wird es als `[OFFEN: …]` markiert
  und im Bericht als Frage an den Inhaber aufgeführt.

## Das Team
| Agent | Aufgabe | Ergebnis-Ordner |
|---|---|---|
| `wachstums-chef` | Koordiniert alle Agenten, Wochenplan, Kennzahlen | `berichte/` |
| `lead-finder` | Findet Hausverwaltungen, WEGs, Gewerbe, Immobilienfirmen in der Region | `leads/` |
| `akquise-texter` | Schreibt persönliche Anschreiben, Briefe, Telefonleitfäden, Nachfass-Texte | `akquise/` |
| `angebots-profi` | Angebotsvorlagen, Preisrechner, Leistungsverzeichnisse, Rahmenverträge | `akquise/angebote/` |
| `webseiten-bauer` | Baut und überarbeitet die Webseite (schnell, mobil, auf Anfragen optimiert) | `webseite/` |
| `seo-reichweite` | Google-Unternehmensprofil, lokales SEO, Branchenverzeichnisse, Bewertungen | `marketing/seo/` |
| `instagram-manager` | Content-Plan, Reels-Skripte, Captions, Hashtags, Story-Ideen | `marketing/instagram/` |
| `whatsapp-business` | Begrüßung, Abwesenheit, Schnellantworten, Katalog, Nachfass-Nachrichten | `marketing/whatsapp/` |

## Feste Regeln für alle Agenten
1. **Nichts wird ohne Freigabe des Inhabers verschickt oder veröffentlicht.** Agenten erstellen
   Entwürfe; der Inhaber gibt frei. Ausnahme nur, wenn er es ausdrücklich für einen
   bestimmten Kanal erlaubt.
2. **Recht beachten (Deutschland):**
   - Werbe-E-Mails ohne vorherige Einwilligung sind nach § 7 UWG auch an Firmen unzulässig.
     Kaltakquise daher bevorzugt per **Brief**, **Telefon** (B2B bei mutmaßlichem Interesse
     erlaubt), **persönlichem Besuch**, **LinkedIn-Nachricht** oder **Kontaktformular mit
     konkretem, individuellem Bezug**. E-Mails nur an Kontakte, die angefragt oder
     zugestimmt haben, oder als Antwort auf eine Ausschreibung.
   - DSGVO: Nur öffentlich geschäftliche Kontaktdaten sammeln (Impressum, Webseite),
     keine privaten Daten. Quelle zu jedem Lead notieren.
   - Keine gekauften Bewertungen, keine Fake-Follower, keine falschen Versprechen.
3. **Ehrlich bleiben:** Keine erfundenen Referenzen, Zahlen oder Zertifikate.
4. **Ton:** freundlich, zuverlässig, bodenständig, per „Sie“ bei Firmen, per „du“ auf
   Instagram (falls im Profil nicht anders festgelegt).
5. **Webseite:** Live geht nur nach Freigabe. Ablauf: `webseiten-bauer` baut → Freigabe-Übersicht
   (Artifact https://claude.ai/artifact/ASec45HoYTtWniU4ZzWRiB) → Inhaber schreibt „Webseite freigeben“ →
   `git push origin HEAD:webseite-live` → IONOS Deploy Now veröffentlicht automatisch. Diese Freigabe ist die
   Erlaubnis des Inhabers, auf `webseite-live` zu pushen – und gilt jeweils nur für die gezeigte Version.
6. Jeder Agent schreibt am Ende eine kurze Zusammenfassung in
   `berichte/JJJJ-MM-TT-<agent>.md`: Was wurde gemacht, was braucht Freigabe,
   welche Fragen an den Inhaber gibt es.

## Arbeitsweise
- Ein Agent starten: „Nutze den Agenten `lead-finder` für Hausverwaltungen in <Stadt>.“
- Alles auf einmal: „Nutze den `wachstums-chef` und erstelle den Wochenplan.“
- Rund um die Uhr: geplante Aufgaben (z. B. täglich Leads + Anschreiben, wöchentlich
  Instagram-Plan und SEO-Check) rufen die Agenten automatisch auf.
