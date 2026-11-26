# Architektur

## Überblick

```
             ┌────────────── Datenquellen (zugelassen) ───────────────┐
             │ Keepa API · CSV/Partner-Feeds (Awin …) · manuelle Prüfung │
             └───────────────────────────┬─────────────────────────────┘
                                         ▼
┌──────────────┐  Celery Beat   ┌──────────────────────────────────────────────┐
│ Redis        │◄──────────────►│ Worker: Master Agent → Pipeline-Agenten       │
│ Queue + Lock │                │ Publisher (1 min) · Preisüberwachung (15 min) │
└──────────────┘                │ Growth (täglich)                              │
                                └───────────────┬──────────────────────────────┘
                                                ▼
                         ┌──────────────────────────────────────┐
                         │ PostgreSQL – zentrale Deal-Datenbank  │
                         │ Produkte · Preisverlauf · Deals ·     │
                         │ Links · Medien · Beiträge · Klicks ·  │
                         │ Provisionen · Agentenläufe · Fehler · │
                         │ Kosten · Audit · Lern-Gewichte        │
                         └───────┬────────────────────┬─────────┘
                                 ▼                    ▼
                    ┌────────────────────┐   ┌──────────────────────────┐
                    │ FastAPI            │   │ Medien: lokal / S3        │
                    │ /api (JWT, Rollen) │   │ (eigene PNG/MP4-Grafiken) │
                    │ /api/public (Site) │   └──────────────────────────┘
                    └─────────┬──────────┘
                              ▼
                    ┌────────────────────────────┐        Offizielle APIs
                    │ Next.js                    │   Instagram Graph · Pinterest v5
                    │ / Website (SSR, SEO)       │   Telegram Bot · WhatsApp (manuell)
                    │ /admin Dashboard           │
                    └────────────────────────────┘
```

## Technologieentscheidungen

| Bereich | Wahl | Begründung |
|---|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic | typisiert, schnell, ausgereifte Migrationen |
| Jobs | Celery + Redis, Redis-Locks je Job | Wiederholungen, Zeitplan, kein Doppel-Lauf |
| DB | PostgreSQL 16 | Transaktionen, `FOR UPDATE SKIP LOCKED` gegen Doppelveröffentlichung |
| Frontend | Next.js 15 (App Router) | Website mit SSR/ISR für SEO **und** Dashboard in einer App |
| Grafik | Pillow + ffmpeg | deterministisch, kostenlos, keine fremden Bildrechte |
| KI | Claude API (optional) mit hartem Tages-/Monatsbudget | nur Feinschliff; System läuft ohne KI |
| Auth | JWT (HS256), bcrypt, Rollen viewer/editor/admin | einfach, zustandslos |
| Monitoring | `/healthz`, `/metrics` (Prometheus-Text), Fehlerprotokoll, Telegram-/Webhook-Alarme | ohne Zusatzdienste nutzbar |

**Abweichung:** Der Masterprompt nennt „KI-generierte Bilder“. Umgesetzt sind eigene, generierte Layout-Grafiken
(Pillow) – rechtlich sauber, kostenlos und reproduzierbar. Ein externer Bildgenerator ist bewusst nicht
eingebaut, weil generierte „Produktfotos“ das echte Produkt falsch darstellen können (Irreführungsrisiko).

**Abweichung:** Klicks werden per Beacon gezählt, der Affiliate-Link selbst bleibt der direkte, unverkürzte
Amazon-Link (`rel="sponsored"`). Keine eigene Weiterleitungsdomain → keine Link-Verschleierung.

## Datenmodell (Kern)

| Tabelle | Inhalt |
|---|---|
| `products` | Händler + externe ID (ASIN), Titel, Kategorie, Quelle, Bewertung |
| `price_points` | Jede Preisbeobachtung (Quelle, Zeit, verfügbar) – Basis aller Scores |
| `deals` | Status (11 Stufen), Typ, Score + Aufschlüsselung, Referenzpreis (Median 90 T.), Verifikationen, Priorität |
| `deal_events` | Lückenloses Statusprotokoll (wer, wann, warum) |
| `affiliate_links` | je Deal × Kanal (Tracking-ID), Prüfergebnis |
| `media_assets` | erzeugte Grafiken (Lizenz `generated`, gerenderter Preis) |
| `publications` | je Plattform: Text, Medien, Zeitplan, Status, externe ID, Fehler, Metriken; eindeutiger Inhalts-Hash |
| `platform_states` | Limits, Ausbau, Ruhezeiten, Mindest-Score, Not-Aus, Auto-Pause |
| `clicks`, `commissions` | gemessene Klicks; importierte Provisionen (geschätzt/bestätigt) |
| `agent_states`, `agent_runs` | Agenten an/aus, Fehlerserien, Laufprotokolle |
| `compliance_checks`, `error_logs`, `cost_entries`, `reports`, `audit_logs`, `kv_settings` | Betrieb, Lernsystem |

## Deal-Status

`neu → in_pruefung → verifiziert → medien_werden_erstellt → freigegeben → geplant → veroeffentlicht`
Nebenzweige: `preis_geaendert`, `abgelaufen`, `fehlerhaft`, `abgelehnt` (Score < 50; Ergänzung zum Masterprompt).
Erlaubte Übergänge zentral in `backend/app/domain/status.py`.

## Ausfallsicherheit

* Jeder Agent läuft isoliert; Fehler werden zurückgerollt, protokolliert, nach 5 Fehlern in Folge wird der Agent pausiert + Alarm.
* Publisher: Zeilensperre (`SKIP LOCKED`), Status `wird_veroeffentlicht`, eindeutiger Inhalts-Hash → keine Doppelposts nach Absturz.
* Vor jeder Veröffentlichung: Not-Aus, Limits, frischer Preis, erneute Compliance. Bei Unsicherheit wird **nicht** veröffentlicht.
* API-Fehler: Wiederholung mit Backoff (max. 3), nach 3 Fehlern in Folge 6 h Pause der Plattform; Rate-Limit → Pause bis `retry-after`.
* Backups: täglicher `pg_dump` mit Rotation; Medien im S3-Bucket (Versionierung aktivieren).

## Verzeichnisstruktur

```
dealfehler/
├── backend/            FastAPI, Agenten, Migrationen, Tests
│   ├── app/agents/     base, pipeline, publishing, growth, master, registry
│   ├── app/domain/     scoring, compliance, frequency, affiliate, status, dedup
│   ├── app/sources/    keepa, feed (CSV), demo
│   ├── app/publishers/ instagram, pinterest, messaging (telegram, whatsapp, website)
│   ├── app/creative/   render (Grafik/Reel), captions
│   ├── app/api/        admin, public, channel_kit
│   └── migrations/     Alembic
├── web/                Next.js: Website (/) + Dashboard (/admin)
├── scripts/            backup.sh, restore.sh
└── docker-compose.yml
```
