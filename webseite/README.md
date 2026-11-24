# Webseite Hausmeister Helden

Neue, schnelle Webseite: 12 Seiten, ohne Cookies und ohne Tracking (kein Cookie-Banner nötig), optimiert für Handy und Google.

| Ordner/Datei | Inhalt |
|---|---|
| `public/` | **Die fertige Webseite.** Genau diesen Inhalt hochladen. |
| `build.py` | Alle Texte, Preise, Leistungen, FAQ. Danach `python3 webseite/build.py` ausführen. |
| `inhalte/ratgeber/` | Ratgeber-Artikel (der Agent ergänzt jede Woche einen). |
| `static/` | Design (CSS), Preisrechner/Formular (JS), Schriften, Logo. |

## Veröffentlichung: vollautomatisch nach Freigabe

```
Agent baut die Seite (Di + Fr) → Freigabe-Übersicht (Artifact) → du schreibst „Webseite freigeben“
→ Push auf Branch webseite-live → IONOS Deploy Now → www.haus-meister-helden.de
```

- `python3 webseite/build.py` baut die Seite nach `public/`.
- `python3 webseite/freigabe.py` erstellt die Übersicht in `freigabe/` (Screenshots, Prüfung, Liste der geänderten Seiten).
- Freigabe-Link (bleibt immer gleich): https://claude.ai/artifact/ASec45HoYTtWniU4ZzWRiB

### Einmalig einrichten: IONOS Deploy Now (macht der Inhaber, ca. 10 Minuten)
Deploy Now ist der IONOS-Dienst, der eine Webseite direkt aus GitHub veröffentlicht. Passwörter musst du dafür nicht weitergeben.
1. Erste Freigabe im Chat geben („Webseite freigeben“). Dadurch entsteht der Branch `webseite-live`.
2. Im IONOS-Konto **Deploy Now** öffnen → Projekt anlegen → mit GitHub verbinden → Repository `martinogur/HausManager` wählen.
3. Bei den Build-Einstellungen: **kein Framework / statische Seite**, Build-Befehl leer lassen, **Veröffentlichungsordner: `webseite/public`**.
4. **Produktions-Branch: `webseite-live`.**
5. In den Projekteinstellungen **Domain verbinden** → `haus-meister-helden.de` (und `www.`). Achtung: Dadurch wird die alte Baukasten-Seite ersetzt.
6. Claude Bescheid geben („Deploy Now ist eingerichtet“). Dann wird in `freigabe.py` `DEPLOY_NOW_VERBUNDEN = True` gesetzt und die Live-Seite geprüft.

Danach in der **Google Search Console** die `sitemap.xml` einreichen.

## Vor dem Livegang prüfen (Inhaber)
- [ ] Impressum und Datenschutz prüfen (Rechtsform, ggf. USt-IdNr. ergänzen). Die Texte sind Vorlagen und ersetzen keine Rechtsberatung.
- [ ] Preise: netto oder brutto? Das muss auf der Seite stehen.
- [ ] Echte Fotos (Team, Einsätze, Vorher/Nachher) schicken, dann baut der Agent sie ein.
- [ ] Echte Google-Bewertungen bzw. Kundenstimmen freigeben, dann kommen sie auf die Startseite.
