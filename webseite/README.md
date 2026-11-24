# Webseite Hausmeister Helden

Neue, schnelle Webseite: 12 Seiten, ohne Cookies und ohne Tracking (kein Cookie-Banner nötig), optimiert für Handy und Google.

| Ordner/Datei | Inhalt |
|---|---|
| `public/` | **Die fertige Webseite.** Genau diesen Inhalt hochladen. |
| `build.py` | Alle Texte, Preise, Leistungen, FAQ. Danach `python3 webseite/build.py` ausführen. |
| `inhalte/ratgeber/` | Ratgeber-Artikel (der Agent ergänzt jede Woche einen). |
| `static/` | Design (CSS), Preisrechner/Formular (JS), Schriften, Logo. |

## Online stellen bei IONOS

Die jetzige Seite läuft im **IONOS-Baukasten (MyWebsite)**. Dort kann man keine eigenen Dateien hochladen.
Es gibt zwei Wege:

**A) IONOS-Webhosting (empfohlen):**
1. Im IONOS-Konto prüfen, ob ein **Webhosting-Paket mit Webspace** vorhanden ist. Falls nicht, das kleinste Webhosting-Paket buchen.
2. Unter **Hosting → SFTP & SSH** die Zugangsdaten ansehen.
3. Mit einem SFTP-Programm (z. B. FileZilla, kostenlos) verbinden und den **Inhalt** von `webseite/public/` in das Webspace-Verzeichnis hochladen.
4. Unter **Domains & SSL** die Domain `haus-meister-helden.de` auf dieses Webspace-Verzeichnis zeigen lassen (statt auf den Baukasten). SSL-Zertifikat aktivieren.
5. Den Baukasten-Vertrag erst kündigen, wenn die neue Seite läuft.

**B) Kostenloses Hosting + IONOS-Domain:** `public/` zum Beispiel bei Netlify oder Cloudflare Pages hochladen und in IONOS die DNS-Einträge der Domain dorthin zeigen lassen.
Dann muss in `datenschutz()` in `build.py` der Hosting-Anbieter angepasst werden.

Nach dem Umzug: In der **Google Search Console** die `sitemap.xml` einreichen.

## Vor dem Livegang prüfen (Inhaber)
- [ ] Impressum und Datenschutz prüfen (Rechtsform, ggf. USt-IdNr. ergänzen). Die Texte sind Vorlagen und ersetzen keine Rechtsberatung.
- [ ] Preise: netto oder brutto? Das muss auf der Seite stehen.
- [ ] Echte Fotos (Team, Einsätze, Vorher/Nachher) schicken, dann baut der Agent sie ein.
- [ ] Echte Google-Bewertungen bzw. Kundenstimmen freigeben, dann kommen sie auf die Startseite.
