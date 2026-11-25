"""Migrationen: Schema aus schema.sql, Django-Tabellen in hh, leere DB vor/zurück."""

import os
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

APP_DIR = Path(__file__).resolve().parents[2]


def _tabellen(schema: str) -> set[str]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s", [schema])
        return {zeile[0] for zeile in cursor.fetchall()}


@pytest.mark.django_db
def test_fach_und_django_tabellen_liegen_in_hh():
    tabellen = _tabellen("hh")
    for name in ("benutzer", "kunden", "einsaetze", "audit_log", "django_session", "django_admin_log",
                 "django_content_type", "auth_permission", "otp_totp_totpdevice", "django_cache"):
        assert name in tabellen, name
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = 'hh' AND table_name = 'benutzer'"
        )
        spalten = {zeile[0] for zeile in cursor.fetchall()}
    assert {"password", "last_login", "rolle", "email"} <= spalten


@pytest.mark.django_db
def test_alle_migrationen_angewendet_und_keine_fehlen():
    executor = MigrationExecutor(connection)
    assert executor.migration_plan(executor.loader.graph.leaf_nodes()) == []
    # Modelle von kern/konten/berichte passen zu den Migrationen
    call_command("makemigrations", "kern", "konten", "berichte", check=True, dry_run=True, verbosity=0)


def _db_url(name: str) -> str:
    teile = urlsplit(os.environ["DATABASE_URL"])
    return urlunsplit(teile._replace(path=f"/{name}"))


def _manage(url: str, *args) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
    env.update(DATABASE_URL=url, DJANGO_DEBUG="1")
    return subprocess.run(
        [sys.executable, "manage.py", *args], cwd=APP_DIR, env=env, capture_output=True, text=True, timeout=300
    )


def test_migrationen_auf_leerer_db_vor_und_zurueck():
    """Frische, leere Datenbank: migrate → kern zurück auf null → migrate."""
    name = f"test_hh_leer_{uuid.uuid4().hex[:8]}"
    verwaltung = psycopg.connect(_db_url("postgres"), autocommit=True)
    try:
        verwaltung.execute(f'CREATE DATABASE "{name}"')
        url = _db_url(name)

        ergebnis = _manage(url, "migrate", "--noinput")
        assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr

        with psycopg.connect(url) as db:
            anzahl = db.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'hh' AND table_name = 'django_session'"
            ).fetchone()[0]
            assert anzahl == 1

        ergebnis = _manage(url, "migrate", "kern", "zero", "--noinput")
        assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr
        with psycopg.connect(url) as db:
            assert db.execute("SELECT count(*) FROM pg_namespace WHERE nspname = 'hh'").fetchone()[0] == 0

        ergebnis = _manage(url, "migrate", "--noinput")
        assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr
    finally:
        verwaltung.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        verwaltung.close()
