# Portal Phase 2 – Abschlussbericht (25.11.2026)

## Ergebnis
- Drei Agenten parallel (Kern, Fachmodelle, Betrieb), zusammengeführt und gemeinsam getestet.
- **116 von 116 Tests grün** (pytest) + **27 Datenbank-Tests grün** (`portal/db/tests/run.sh`).
- `manage.py check --deploy` ohne Befund (HSTS-Preload bewusst aus), `makemigrations --check` ohne Änderungen.
- Entwicklungsdatenbank migriert, fiktive Testdaten geladen (`manage.py testdaten`).

## Inhalt
- Kern: Anmeldung, Pflicht-2FA (TOTP) für Admin/Büro, Rollen, Sperre nach 5 Fehlversuchen, Dashboard (Kennzahlen, Einsätze heute, „Heute zu tun“), reduzierte Mitarbeiter-Startseite, Audit-Benutzer je Request, `/gesund`, Sicherheits-Header, `admin_anlegen`.
- Fachmodelle: alle 26 Fachtabellen als Django-Modelle (Schema-Abgleich getestet), Verwaltungsmasken, Rechte (Stundenlohn nur Admin), Testdaten-Befehl.
- Betrieb: Docker (Non-Root, read-only), Compose mit Caddy (HTTPS), SOPS-Secrets, restic-Backups mit Restore-Test (inkl. Notfall-Durchlauf), systemd-Timer, GitHub-Actions-Tests, Betriebs- und Notfallhandbuch.
- Hauptsitzung: Audit-Log speichert keine Passwort-Hashes/Login-Zeiten mehr (schema.sql), Test verschärft.

## Für Phase 3/4 vorgemerkt (Schema-Verbesserungen)
1. `einsatz_mitarbeiter`, `mitarbeiter_qualifikationen`: eigener UUID-Primärschlüssel + UNIQUE (Pflege im Admin).
2. citext-Typ-Cache in `kern.0001_schema` leeren (Workaround in kommunikation entfernen).
3. `email_protokolle.an` als `text[]` (klein geschrieben) statt `citext[]`.
4. ENUM/CHECK für `abwesenheiten.grund`, `anfragen.kanal`, `dokumente.kategorie`.
5. Direkter FK `angebote.kunde_id`/`auftraege.kunde_id` → `kunden`.
6. `dokumente.loeschen_ab` für Bewerbungsunterlagen per Trigger aus `bewerbungen.loeschen_ab`.
7. Regel: Einsatz-Status „zugewiesen“ nur mit mindestens einer Zuweisung.
8. Tabelle `bewertungsanfragen` (Bewertungsautomatik).

## Entscheidungen für Martin (vor Phase 3)
- Hetzner-Server + Storage Box buchen (ca. 10–14 €/Monat) – erst nach Freigabe.
- SSH nur von festen IPs oder offen? Externe Überwachung (Uptime/Backup) gewünscht?
- Notfall-Schlüssel (age) und `RESTIC_PASSWORD` in den Passwort-Manager.
- HSTS 1 Jahr inkl. Subdomains bestätigen.
