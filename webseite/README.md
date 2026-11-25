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
→ Push auf Branch webseite-live → GitHub Pages (alle 30 Min.) → www.haus-meister-helden.de
```

- `python3 webseite/build.py` baut die Seite nach `public/`.
- `python3 webseite/freigabe.py` erstellt die Übersicht in `freigabe/` (Screenshots, Prüfung, Liste der geänderten Seiten).
- Freigabe-Link (bleibt immer gleich): https://claude.ai/artifact/ASec45HoYTtWniU4ZzWRiB

### Hosting: GitHub Pages (eingerichtet am 24.11.2026)
- Der Workflow `.github/workflows/webseite.yml` auf dem Branch `main` veröffentlicht den Ordner `webseite/public`
  vom Branch `webseite-live` – alle 30 Minuten automatisch oder sofort über GitHub → Actions → „Run workflow“.
- Die Domain `haus-meister-helden.de` (bei IONOS) zeigt per DNS auf GitHub Pages. E-Mail-Postfächer bleiben bei IONOS.
- `webseite-live` wird nur nach Freigabe des Inhabers aktualisiert.

Danach in der **Google Search Console** die `sitemap.xml` einreichen.

## Vor dem Livegang prüfen (Inhaber)
- [ ] Impressum und Datenschutz prüfen (Rechtsform, ggf. USt-IdNr. ergänzen). Die Texte sind Vorlagen und ersetzen keine Rechtsberatung.
- [ ] Preise: netto oder brutto? Das muss auf der Seite stehen.
- [ ] Echte Fotos (Team, Einsätze, Vorher/Nachher) schicken, dann baut der Agent sie ein.
- [ ] Echte Google-Bewertungen bzw. Kundenstimmen freigeben, dann kommen sie auf die Startseite.
