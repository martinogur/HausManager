# DealFehler

**Gute Deals. Schlechte Preise. Dein Vorteil.**

Automatisiertes Deal- und Preisfehler-Netzwerk: Eine zentrale Deal-Datenbank, aus der spezialisierte
Agenten Angebote finden, gegen die eigene Preishistorie bewerten, eigene Grafiken erzeugen, Inhalte
regelkonform prüfen und kontrolliert auf Website, Instagram, Pinterest, Telegram und WhatsApp verteilen.

> Status: Phase 1 (Fundament) vollständig, Phasen 2–10 als lauffähiger Kern implementiert und getestet.
> Live-Anbindungen an Instagram, Pinterest, Telegram, Keepa und Claude sind **programmiert und gegen
> simulierte API-Antworten getestet, aber noch nicht mit echten Zugangsdaten verifiziert** – siehe [TASKS.md](TASKS.md).
> Standard ist `DRY_RUN=true`: Social-Media-Beiträge werden nur simuliert.

## Inhalt

| Dokument | Zweck |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Aufbau, Datenmodell, Datenfluss, Technologieentscheidungen |
| [AGENTS.md](AGENTS.md) | Alle Agenten, Zuständigkeiten, Zeitplan, Sicherheitsmechanismen |
| [ROADMAP.md](ROADMAP.md) | Phasen 1–10 mit Stand |
| [TASKS.md](TASKS.md) | Offene Aufgaben, fehlende Zugänge, ehrlicher Teststatus |
| [docs/SETUP_ACCESS.md](docs/SETUP_ACCESS.md) | Schritt für Schritt: Zugänge einrichten |
| [docs/COMPLIANCE.md](docs/COMPLIANCE.md) | Kennzeichnung, Preisangaben, Plattformregeln – wie das System sie durchsetzt |
| [docs/BUSINESS_IDEAS.md](docs/BUSINESS_IDEAS.md) | Bewertete zusätzliche Einnahmequellen |

## Schnellstart (lokal, ohne Docker)

Voraussetzungen: Python 3.12+, Node 22, PostgreSQL 16, Redis 7, ffmpeg, DejaVu-Fonts.

```bash
# Datenbank
createuser -P dealfehler && createdb -O dealfehler dealfehler && createdb -O dealfehler dealfehler_test

# Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cat > .env <<'ENV'
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PASSWORD=ein-langes-passwort
AMAZON_PARTNER_TAG=deinetag-21
DRY_RUN=true
ENV
alembic upgrade head
uvicorn app.main:app --reload            # API auf :8000
celery -A app.worker worker -B -l INFO   # Agenten (zweites Terminal)

# Frontend
cd ../web && npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev   # :3000, Dashboard unter /admin
```

Ohne echte Datenquelle: Dashboard → Einstellungen → **Demo-Modus** aktivieren, dann „Master-Zyklus starten“.
Demo-Deals durchlaufen die ganze Pipeline, werden aber von der Compliance **nie** veröffentlicht.

## Produktion (Docker)

```bash
cp .env.example .env    # Werte setzen: SECRET_KEY, POSTGRES_PASSWORD, Admin, Partner-Tag …
docker compose up -d --build
```

Dienste: `db` (PostgreSQL), `redis`, `api` (FastAPI, führt Migrationen aus), `worker` + `beat` (Celery-Agenten),
`web` (Next.js: Website + Dashboard), `backup` (tägliches `pg_dump`, Rotation 14 Tage).
API und Web lauschen nur auf `127.0.0.1` – davor einen TLS-Reverse-Proxy (z.B. Caddy/Traefik) setzen.

Wiederherstellung: `docker compose stop worker beat && docker compose run --rm -v ./backups:/backups backup /scripts/restore.sh /backups/<datei>.dump`

## Tests

```bash
cd backend && pytest -q      # 45 Tests: Score, Compliance, Frequenz, End-to-End-Pipeline, API, Plattform-Clients, Grafik/Video
ruff check app tests
cd ../web && npm run typecheck && npm run build
```

Die Tests laufen gegen eine echte PostgreSQL-Datenbank (`TEST_DATABASE_URL`, Standard `dealfehler_test`).
CI: `.github/workflows/dealfehler-ci.yml`.

## Sicherheitsgrundsätze (Kurzfassung)

* Nur offizielle APIs (Meta Graph API, Pinterest API v5, Telegram Bot API, Keepa). Kein Scraping, keine Captcha-Umgehung, keine WhatsApp-Web-Bots, keine Fake-Interaktionen.
* Jeder Beitrag: Werbekennzeichnung am Anfang, Preis mit Zeitstempel, eigene Grafik, Preis unmittelbar vor Veröffentlichung erneut geprüft.
* „Preisfehler“ nur nach Admin-Bestätigung – sonst „Preisfehler-Verdacht“.
* Eigene konservative Limits je Plattform, Ruhezeiten, Mindestabstände, Duplikatsperre, automatische Pause bei API-Fehlern/Rate-Limits, Not-Aus je Plattform und global.
* Geheimnisse nur in Umgebungsvariablen. Das Dashboard zeigt nur, *ob* ein Zugang konfiguriert ist.
