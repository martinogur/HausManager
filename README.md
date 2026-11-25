# Hausmeister Helden AI OS

Betriebssystem für **Hausmeister Helden** (Gütersloh + 30 km): ein Verwaltungsportal mit KI-Agenten,
Automatisierungen, Freigabe-Warteschlange und Controlling. Hinzu kommt die Wachstumszentrale, in der
Claude-Code-Agenten Leads, Briefe, Webseite und Social-Media-Inhalte erarbeiten.

**Grundsatz:** Agenten erledigen die operative Arbeit und schlagen vor. Was nach außen geht (E-Mails, Briefe,
Angebote, Rechnungen, Posts), braucht eine Freigabe durch den Geschäftsführer. Das erzwingt die Datenbank.

## Stand (25.11.2026)

| Bereich | Stand |
|---|---|
| Portal-Fundament (Login, 2FA, Rollen, Audit, Datenmodell, Betrieb, Backups) | ✅ fertig, getestet |
| Datenbank-Erweiterung „Betriebssystem“ (Akquise, Agenten, Freigaben, Ereignisse, Automatisierungen, Redaktionskalender) | ✅ fertig, 58 DB-Tests |
| 13 KI-Agenten mit Laufzeit, Budget, Grenzen, Eskalation | ✅ fertig, regelbasiert lauffähig, KI nach API-Schlüssel |
| 18 Automatisierungen (Ereignisse + Zeitpläne) | ✅ fertig |
| Steuerungsoberfläche (15 Bereiche + Freigaben, mobil) | ✅ fertig |
| Integrationen IONOS, HubSpot, Lexware, Make | ✅ Code fertig und getestet, **Zugangsdaten fehlen** |
| Produktivbetrieb (Hetzner-Server) | ⏳ wartet auf Freigabe der Kosten |

Tests: **217 Anwendungstests + 58 Datenbanktests + 12 Deploy-Tests**, alle grün.

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [PROJECT_MASTERPLAN.md](PROJECT_MASTERPLAN.md) | Bestandsaufnahme, Zielbild, Entscheidungen, offene Punkte für den Inhaber |
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | Komponenten, führende Systeme, Datenflüsse, Betrieb |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Tabellen, Regeln in der Datenbank, Auswertungen |
| [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) | Die 13 Agenten, Laufzeit, Schleifenschutz, Budgets, Eskalation |
| [AUTOMATION_MAP.md](AUTOMATION_MAP.md) | Jede Automatisierung: Auslöser → Agent → Freigabe → Ergebnis |
| [SECURITY.md](SECURITY.md) | Rechte, Secrets, Freigaben, Datenschutz, Backups, Kostenkontrolle |
| [API_INTEGRATIONS.md](API_INTEGRATIONS.md) | IONOS, HubSpot, Lexware, Craftnote, Make, Claude: Stand und Bedarf |
| [ROADMAP.md](ROADMAP.md) | Phasen 1–8 mit Status |
| [TASKS.md](TASKS.md) | Priorisierte Aufgabenliste |
| [CLAUDE.md](CLAUDE.md) | Regeln für die Claude-Code-Agenten der Wachstumszentrale |

Detaildokumente des Portals: `portal/docs/` (Architektur Phase 1, Datenmodell, Betriebshandbuch, Wiederherstellung).

## Verzeichnis

```
portal/app/        Django-Anwendung (Portal, Agenten, Automatisierungen, Oberfläche)
  agenten/         Agenten-Laufzeit, KI-Client, Freigaben, Automatisierungen, team/ (Aufgaben der 13 Agenten)
  vertrieb/        Leads, Scoring, Einsatzgebiet, Angebotskalkulation
  cockpit/         Steuerungsoberfläche + mobile Einsatzansicht
  integrationen/   IONOS (IMAP/SMTP), HubSpot, Lexware, Make-Webhook, Sync-Protokoll
  berichte/        Dashboard, Controlling-Kennzahlen
portal/db/         schema.sql + erweiterungen/0003_betriebssystem.sql + SQL-Tests
portal/deploy/     Docker Compose, Caddy, SOPS-Secrets, Backups, Hetzner-Automatik
leads/ akquise/ marketing/ personal/ webseite/ firma/   Arbeitsergebnisse der Wachstumszentrale
.claude/agents/    Claude-Code-Agenten (Recherche, Texte, Grafiken, Webseite)
```

## Lokal starten

```bash
python3 -m venv /tmp/hh-venv && /tmp/hh-venv/bin/pip install -r portal/app/requirements-dev.txt
# PostgreSQL 16 lokal, Datenbank hh_dev für Benutzer hh
export DATABASE_URL=postgresql://hh:nur-lokal-entwicklung@localhost:5432/hh_dev DJANGO_DEBUG=1
cd portal/app
python manage.py migrate && python manage.py agenten_sync
python manage.py agent_beauftragen lead_research bestand_importieren --sofort   # 52 Leads aus leads/leads.csv
python manage.py agenten_arbeiten                                               # ein Worker-Lauf
python manage.py runserver
```

Tests: `pytest -q` (in `portal/app`), `bash portal/db/tests/run.sh` (Datenbankregeln).
Ohne `ANTHROPIC_API_KEY` arbeiten alle Agenten regelbasiert. Das ist volle Funktion ohne KI-Texte.
