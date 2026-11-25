"""Einstellungen: Pflicht-Variablen, DATABASE_URL-Auswertung, Deploy-Prüfung."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.settings import datenbank_aus_url

APP_DIR = Path(__file__).resolve().parents[2]


def _python(code: str, **env_zusatz) -> subprocess.CompletedProcess:
    """Führt Python-Code mit sauberer Umgebung (ohne pytest) im App-Ordner aus."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
    env["DJANGO_SETTINGS_MODULE"] = "config.settings"
    env.update(env_zusatz)
    return subprocess.run(
        [sys.executable, "-c", code], cwd=APP_DIR, env=env, capture_output=True, text=True, timeout=120
    )


def test_ohne_secret_key_bricht_start_ab():
    ergebnis = _python("import django; django.setup()", DJANGO_DEBUG="0")
    assert ergebnis.returncode != 0
    assert "ImproperlyConfigured" in ergebnis.stderr
    assert "DJANGO_SECRET_KEY" in ergebnis.stderr


def test_mit_secret_key_startet():
    ergebnis = _python(
        "import django; django.setup(); from django.conf import settings; print(settings.DEBUG)",
        DJANGO_DEBUG="0",
        DJANGO_SECRET_KEY="nur-fuer-den-test-" + "k" * 50,
    )
    assert ergebnis.returncode == 0, ergebnis.stderr
    assert ergebnis.stdout.strip() == "False"


def test_debug_ist_standardmaessig_aus():
    ergebnis = _python(
        "import django; django.setup(); from django.conf import settings; "
        "print(settings.DEBUG, settings.SESSION_COOKIE_SECURE, settings.CSRF_COOKIE_SECURE, settings.SECURE_SSL_REDIRECT)",
        DJANGO_SECRET_KEY="nur-fuer-den-test-" + "k" * 50,
    )
    assert ergebnis.returncode == 0, ergebnis.stderr
    assert ergebnis.stdout.split() == ["False", "True", "True", "True"]


def test_check_deploy_ohne_warnungen():
    """manage.py check --deploy darf im Betriebsmodus keine Warnungen melden."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
    env.update(
        DJANGO_DEBUG="0",
        DJANGO_SECRET_KEY="nur-fuer-den-test-" + "Zx9!kQ" * 10,
        DJANGO_ALLOWED_HOSTS="portal.example.org",
        DJANGO_CSRF_TRUSTED_ORIGINS="https://portal.example.org",
    )
    ergebnis = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=APP_DIR, env=env, capture_output=True, text=True, timeout=120,
    )
    assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr


def test_datenbank_url_wird_zerlegt():
    db = datenbank_aus_url("postgresql://nutzer:geh%40im%2Fwort@db.example.org:6543/portal?sslmode=require")
    assert db["ENGINE"] == "django.db.backends.postgresql"
    assert db["NAME"] == "portal"
    assert db["USER"] == "nutzer"
    assert db["PASSWORD"] == "geh@im/wort"
    assert db["HOST"] == "db.example.org"
    assert db["PORT"] == "6543"
    assert db["OPTIONS"] == {"sslmode": "require", "options": "-c search_path=hh,public"}


@pytest.mark.parametrize("url", ["mysql://a:b@h/db", "postgresql://a:b@h/"])
def test_datenbank_url_ungueltig(url):
    with pytest.raises(ImproperlyConfigured):
        datenbank_aus_url(url)


def test_search_path_auf_schema_hh(settings):
    assert settings.DATABASES["default"]["OPTIONS"]["options"] == "-c search_path=hh,public"
    assert settings.PASSWORD_HASHERS[0] == "django.contrib.auth.hashers.Argon2PasswordHasher"
    assert settings.SESSION_COOKIE_AGE == 8 * 60 * 60
