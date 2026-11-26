# Roadmap

Legende: ✅ umgesetzt & getestet · 🟡 umgesetzt, Live-Test mit echten Zugangsdaten offen · ⏳ offen

| Phase | Inhalt | Stand |
|---|---|---|
| 1 | Projektstruktur, Datenbank (20 Tabellen, Alembic), Auth/Rollen, Dashboard (15 Bereiche), Docker, Backups, Monitoring, CI | ✅ (Docker-Images lokal nicht gebaut – kein Docker-Daemon in der Entwicklungsumgebung; Compose-Datei validiert) |
| 2 | Deal-Suche + Preisfehler-Erkennung: Keepa-Client, CSV-Feeds, Score 0–100, Mehrfach-Verifikation, Alarme | ✅ Logik · 🟡 Keepa live · ⏳ Amazon Creators API |
| 3 | Affiliate-Links (Kanal-Tracking-IDs), Deal-Datenbank, Klick-Tracking, Provisionsimport | ✅ |
| 4 | Grafiken (4 Vorlagen × 3 Formate), Reel-Video, Kanaltexte, optional Claude-Feinschliff mit Budget | ✅ Grafik/Texte · 🟡 Claude live |
| 5 | Instagram Graph API (Post/Story/Reel, Permalink, Insights) | 🟡 |
| 6 | Pinterest API v5 (Boards anlegen, Pins, Analytics) | 🟡 |
| 7 | WhatsApp-Kanal: Freigabe-Workflow, Kanalpaket (Texte, Profilbild, QR); Telegram-Kanal automatisch | ✅ WhatsApp-Workflow · 🟡 Telegram live |
| 8 | Website: Deal-Liste, Kategorien, Suche, Detailseiten mit Preisverlauf, Sitemap, robots, strukturierte Daten | ✅ (Impressum/Datenschutz müssen befüllt werden) |
| 9 | Growth-Agent: Kennzahlen, Lernsystem, Vorschläge, Frequenzausbau | ✅ |
| 10 | Vollautomatik: Celery-Zeitplan, Locks, Fehlerisolation, Auto-Pause, Not-Aus | ✅ Logik · ⏳ Betrieb unter Last |

## Nächste Schritte (empfohlene Reihenfolge)

1. **Woche 1:** Server + Domain, `.env`, Partner-Tag, Keepa-Key → echte Deals im Dashboard (noch `DRY_RUN=true`).
2. **Woche 2:** S3 + Telegram-Kanal live (einfachste offizielle API), dann Pinterest. Erste Woche nur 3 Beiträge/Tag.
3. **Woche 3:** Instagram (App-Review dauert), WhatsApp-Kanal anlegen, Website mit Impressum live, Search Console.
4. **Woche 4:** Provisionsberichte importieren, Growth-Auswertung, Limits schrittweise erhöhen lassen.
5. Danach: Amazon Creators API als zweite Preisquelle (unabhängige Verifikation), Newsletter, Preisalarm (siehe docs/BUSINESS_IDEAS.md).
