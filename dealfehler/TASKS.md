# Aufgaben & ehrlicher Teststatus

## Was nachweislich funktioniert (automatisierte Tests, 45 grün)

* Score-Berechnung inkl. aller Deckel (`tests/test_scoring.py`)
* Compliance-Regeln und dass alle generierten Texte sie bestehen (`tests/test_rules.py`)
* Frequenzmanagement: Limits, Abstände, Ruhezeiten, Not-Aus, Auto-Pause, Ausbau (`tests/test_frequency.py`)
* **End-to-End-Pipeline gegen echte PostgreSQL**: Fund → Score → 2× Verifikation → Links → Grafiken → Compliance →
  Planung → Veröffentlichung → kein Doppelpost; Preisänderung/Angebotsende pausiert Beiträge; Not-Aus; API-Fehler
  → Auto-Pause; Demo-Daten werden nie veröffentlicht; Agentenfehler isoliert; Growth lernt aus Klicks/Provisionen
* REST-API: Login, Rollenrechte, Feed-Import, manuelle Preisbestätigung, öffentliche Website-API, Klick-Beacon,
  Provisionsimport, Agentensteuerung, Health/Metrics, WhatsApp-Kanalpaket
* Plattform-Clients (Instagram, Pinterest, Telegram, Keepa) **gegen simulierte HTTP-Antworten**
* Grafiken in allen Vorlagen/Formaten, MP4-Reel via ffmpeg
* Frontend: TypeScript-Check + Production-Build; Dashboard manuell im Browser geprüft (keine Konsolenfehler, mobil ohne horizontales Scrollen)
* Lokaler Live-Lauf: API + Worker-Logik + Dashboard mit Demo-Daten

## Was NICHT live getestet ist (benötigt Zugangsdaten)

| Integration | Was fehlt | Test nach Einrichtung |
|---|---|---|
| Keepa | `KEEPA_API_KEY` (kostenpflichtig, Token-Kontingent) | Agent „Deal Hunter“ im Dashboard starten, Fehlerprotokoll prüfen |
| Amazon PartnerNet | `AMAZON_PARTNER_TAG`, Kanal-Tracking-IDs | Link aus Deal-Detail öffnen, in PartnerNet-Bericht Klick prüfen |
| Instagram | Meta-App mit `instagram_content_publish`, Professional-Konto, Long-lived Token, **S3 mit öffentlicher https-URL** | API-Verbindungen → „live prüfen“, dann Plattform aktivieren mit `DRY_RUN=false` und Tageslimit 1 |
| Pinterest | App mit Standard-Zugang, Token mit `boards:write`, `pins:write` | wie oben; Boards werden beim ersten Pin angelegt |
| Telegram | Bot-Token, Bot als Admin im Kanal | wie oben |
| Claude | `ANTHROPIC_API_KEY` | Instagram-Hooks werden per KI verfeinert (Budget-Guard + Compliance-Vorprüfung), ohne Key Vorlagentexte. Live-Aufruf ungetestet |
| Docker | Images wurden in der Entwicklungsumgebung nicht gebaut (kein Docker-Daemon) | `docker compose up -d --build` auf dem Server |

## Offene Aufgaben

- [ ] **Amazon Creators API** als Datenquelle (Nachfolger der PA-API 5, OAuth 2.0, neue Zugangsdaten) – liefert offizielle Preise/Verfügbarkeit und eine zweite, unabhängige Preisquelle für die Verifikation
- [ ] Insights-Abruf (Instagram `insights`, Pinterest `analytics`) periodisch in `publications.metrics` schreiben (Client-Methoden vorhanden)
- [ ] Reels automatisch einplanen (Renderer vorhanden; benötigt S3, da Instagram Video-URLs selbst lädt)
- [ ] Impressum und Datenschutzerklärung befüllen (Pflicht vor Livegang)
- [ ] TLS-Reverse-Proxy (Caddy/Traefik) + Domain
- [ ] Token-Ablauf-Überwachung Instagram (Long-lived Token ~60 Tage) – aktuell nur über Health-Check sichtbar
- [ ] Awin-Produktfeed automatisch abrufen (CSV-Import funktioniert bereits)
- [ ] Newsletter (Double-Opt-in) – erst nach Website-Traffic; Amazon-Links nicht direkt in E-Mails (siehe Compliance)

## Entscheidungen, die du treffen musst

1. Domain für die Website
2. Hosting (empfohlen: 1 VPS mit 4 GB RAM + S3-kompatibler Speicher, z.B. Hetzner)
3. Ob Telegram als zusätzlicher Kanal genutzt werden soll (einfachste vollautomatische Verteilung)
4. KI-Budget pro Monat
