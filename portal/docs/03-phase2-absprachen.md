# Phase 2 – verbindliche Absprachen für alle Agenten

Ziel Phase 2: lauffähiges Grundgerüst (Anmeldung, 2FA, Rollen, Dashboard, Audit, Fachmodelle, Betrieb, CI) **nur mit Testdaten**.
Keine kostenpflichtigen Dienste, keine echten Zugangsdaten, keine Echtdaten.

## Umgebung (lokal, bereits eingerichtet)
- Python-Umgebung: `/tmp/hh-venv` (`/tmp/hh-venv/bin/python`, Pakete aus `portal/app/requirements-dev.txt`, Django 5.2.19 LTS)
- PostgreSQL 16 läuft lokal: `postgresql://hh:nur-lokal-entwicklung@localhost:5432/hh_dev` (Rolle `hh` ist Superuser, darf Test-DBs anlegen). Nur für Entwicklung.
- Neue Pakete nur nach Absprache mit der Hauptsitzung (dann fest gepinnt in `requirements*.txt`).

## Projektstruktur (Django-Projekt-Wurzel: `portal/app/`)
| Pfad | Zuständig |
|---|---|
| `manage.py`, `config/` (settings, urls, wsgi, asgi) | Agent **Kern** |
| `kern/` – lädt `portal/db/schema.sql` per Migration, Audit-Middleware, Hilfen | Agent **Kern** |
| `konten/` – Benutzermodell, Login, 2FA, Rollen, Rechte-Hilfen | Agent **Kern** |
| `berichte/` – Dashboard | Agent **Kern** |
| `templates/` (Basislayout, Login, Dashboard), `static/` (CSS/JS, Marke) | Agent **Kern** |
| `stammdaten/`, `auftraege/`, `personal/`, `dokumente/`, `kommunikation/`, `integrationen/`, `ki/` – Modelle, Admin, Tests, Testdaten-Befehl | Agent **Fachmodelle** |
| `portal/deploy/`, `.github/workflows/portal-tests.yml`, `portal/docs/04-betrieb.md`, `portal/docs/wiederherstellung.md` | Agent **Betrieb** |
| `portal/db/schema.sql` | nur Hauptsitzung (Änderungswünsche melden) |

Die leeren App-Ordner (mit `apps.py`, `models.py`, `migrations/`) existieren bereits. Klassenname der AppConfig: `<App>Config` (z. B. `StammdatenConfig`).

## Feste Entscheidungen
1. **Datenbankschema `hh`.** `DATABASES['default']['OPTIONS'] = {"options": "-c search_path=hh,public"}`. Auch Djangos eigene Tabellen (Sessions, Admin-Log, OTP) liegen in `hh`.
2. **Schema-Quelle = `portal/db/schema.sql`.** Migration `kern/migrations/0001_schema.py` führt die Datei per `RunSQL` aus (Reverse: `DROP SCHEMA hh CASCADE`). Die Datei wird zur Laufzeit gelesen, nicht kopiert.
3. **Fachmodelle sind `managed = False`** und bilden die Tabellen aus `schema.sql` exakt ab (`db_table = "kunden"` usw., Spaltennamen identisch, `id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`, Geld als `IntegerField` in Cent, Enums als `CharField` mit `choices` aus dem Schema, Arrays über `django.contrib.postgres.fields.ArrayField`, `citext` als `CharField`/`EmailField`). Zusammengesetzte Constraints macht die Datenbank. Jede Fach-App hat eine Migration `0001_initial`, die von `kern.0001_schema` abhängt (`dependencies = [("kern", "0001_schema")]`).
4. **Benutzer:** `AUTH_USER_MODEL = "konten.Benutzer"`, Modell auf Tabelle `benutzer` (`managed = False`, `AbstractBaseUser`, ohne `PermissionsMixin`). Die fehlenden Login-Spalten (`password`, `last_login`) fügt `konten/migrations/0001_initial.py` per `RunSQL` (`ALTER TABLE hh.benutzer ADD COLUMN …`) hinzu, abhängig von `kern.0001_schema`. Rechte über das Feld `rolle` (`admin`, `buero`, `mitarbeiter`). `is_staff`/`is_superuser`/`has_perm`/`has_module_perms` werden als Properties bzw. Methoden aus der Rolle abgeleitet (admin = alles; buero = Django-Admin lesend/schreibend außer Benutzerverwaltung; mitarbeiter = kein Admin). Fremdschlüssel aus Fachmodellen auf Benutzer: `settings.AUTH_USER_MODEL` mit `db_column` wie im Schema.
5. **Rechte-Hilfen** in `konten/rechte.py`: `rolle_erforderlich(*rollen)` (Decorator), `RolleErforderlichMixin`, `ist_admin(user)`, `ist_buero(user)`. Mitarbeiter sehen später nur eigene Einsätze; Fachmodelle stellen dafür `Einsatz.objects.fuer_benutzer(user)` (QuerySet-Methode) bereit.
6. **Audit:** Middleware `kern.middleware.AuditBenutzerMiddleware` setzt pro Request `SELECT set_config('app.benutzer', <email>, false)` und nach dem Request auf `''` zurück. Die Trigger in `schema.sql` schreiben das ins `audit_log`.
7. **2FA:** `django-otp` mit TOTP (`django_otp.plugins.otp_totp`); für Rollen `admin` und `buero` Pflicht. Nach dem Login ohne bestätigtes Gerät → Einrichtung (QR-Code) bzw. Code-Abfrage.
8. **Passwörter:** Argon2 als erster Hasher. Session-Cookies `Secure`/`HttpOnly`/`SameSite=Lax` (Secure nur wenn `DJANGO_DEBUG=0`), Session-Timeout 8 h, CSRF überall.
9. **Konfiguration nur über Umgebungsvariablen** (keine Secrets im Code): `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (0/1), `DJANGO_ALLOWED_HOSTS` (kommagetrennt), `DJANGO_CSRF_TRUSTED_ORIGINS`, `DATABASE_URL` (postgresql://…). In `DEBUG` darf ein Entwicklungs-Fallback für SECRET_KEY genutzt werden; ohne DEBUG bricht der Start ab, wenn er fehlt. Vorlage: `portal/deploy/.env.example` (Agent Betrieb).
10. **Sprache/Zeit:** `LANGUAGE_CODE = "de-de"`, `TIME_ZONE = "Europe/Berlin"`, `USE_TZ = True`. Oberflächentexte auf Deutsch, kurz und klar.
11. **Oberfläche:** Server-gerendert + HTMX, mobil zuerst. Marke wie die Webseite: Grün `#7ccc13`, Schwarz `#111412`, Schriften Archivo + Inter – Schriftdateien aus `webseite/static/fonts/` nach `portal/app/static/fonts/` kopieren (lokal ausliefern, keine CDNs).
12. **Tests:** `pytest` mit `pytest-django`; Konfiguration in `portal/app/pytest.ini` (`DJANGO_SETTINGS_MODULE = config.settings`, `python_files = tests.py test_*.py`). Aufruf aus `portal/app`: `DATABASE_URL=postgresql://hh:nur-lokal-entwicklung@localhost:5432/hh_dev /tmp/hh-venv/bin/pytest -q`. Jeder Agent testet seine Teile; am Ende müssen **alle** Tests gemeinsam grün sein.
13. **Keine echten Personen- oder Firmendaten** in Tests/Testdaten (Beispielnamen, `example.org`-Adressen). Keine externen Netzaufrufe in Tests.
14. **Nicht committen** – die Hauptsitzung führt zusammen, testet und committet.
