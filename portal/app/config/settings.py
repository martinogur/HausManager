"""
Einstellungen des Verwaltungsportals von Hausmeister Helden.

Grundsatz: Alles, was sich zwischen Entwicklung, Test und Betrieb unterscheidet
oder geheim ist, kommt ausschließlich aus Umgebungsvariablen (Vorlage:
``portal/deploy/.env.example``). Im Code stehen keine Zugangsdaten.

Wichtige Variablen
------------------
DJANGO_SECRET_KEY            Pflicht, wenn DJANGO_DEBUG=0
DJANGO_DEBUG                 0 (Standard, sicher) oder 1 (Entwicklung)
DJANGO_ALLOWED_HOSTS         kommagetrennt, z. B. "portal.haus-meister-helden.de"
DJANGO_CSRF_TRUSTED_ORIGINS  kommagetrennt, mit Schema, z. B. "https://portal.haus-meister-helden.de"
DATABASE_URL                 postgresql://benutzer:passwort@host:5432/datenbank[?sslmode=require]

Optionale Variablen (mit sicheren Standardwerten)
-------------------------------------------------
DJANGO_SSL_REDIRECT          1 = http → https umleiten (Standard ohne DEBUG: 1)
DJANGO_HINTER_PROXY          1 = X-Forwarded-Proto vom Reverse-Proxy (Caddy) vertrauen (Standard ohne DEBUG: 1)
DJANGO_HSTS_SEKUNDEN         Dauer des HSTS-Headers (Standard 31536000 = 1 Jahr)
DJANGO_ADMIN_PFAD            Pfad der Verwaltungsoberfläche (Standard "admin/")
DJANGO_LOG_LEVEL             Standard INFO
DJANGO_DB_CONN_MAX_AGE       Sekunden, die eine DB-Verbindung offen bleibt (Standard 60)
DJANGO_TEST_DB_NAME          Name der Test-Datenbank (nützlich, wenn mehrere Testläufe parallel laufen)
DJANGO_STATIC_ROOT           Zielordner für collectstatic (Standard <app>/staticfiles)
"""

import os
import sys
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


# ----------------------------------------------------------------------------- Hilfen
def env_bool(name: str, standard: bool) -> bool:
    """Liest eine Ja/Nein-Umgebungsvariable (1/0, true/false, ja/nein)."""
    wert = os.environ.get(name)
    if wert is None or wert.strip() == "":
        return standard
    return wert.strip().lower() in {"1", "true", "ja", "yes", "on"}


def env_liste(name: str) -> list[str]:
    """Liest eine kommagetrennte Liste und entfernt Leerzeichen und leere Einträge."""
    return [teil.strip() for teil in os.environ.get(name, "").split(",") if teil.strip()]


def datenbank_aus_url(url: str) -> dict:
    """
    Wandelt eine DATABASE_URL (postgresql://…) in Djangos DATABASES-Eintrag um.

    Bewusst ohne Zusatzpaket (dj-database-url). Unterstützt Benutzer, Passwort
    (URL-kodiert), Host, Port, Datenbankname und Query-Parameter wie
    ``?sslmode=require``, die unverändert an psycopg weitergereicht werden.
    """
    teile = urlsplit(url)
    if teile.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("DATABASE_URL muss mit postgresql:// beginnen.")
    name = unquote(teile.path.lstrip("/"))
    if not name:
        raise ImproperlyConfigured("DATABASE_URL enthält keinen Datenbanknamen.")

    optionen = dict(parse_qsl(teile.query))
    # Alles (auch Djangos eigene Tabellen) liegt im Schema "hh"; "public" enthält
    # nur die Erweiterungen (pgcrypto, citext, btree_gist).
    optionen["options"] = "-c search_path=hh,public"

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": name,
        "USER": unquote(teile.username or ""),
        "PASSWORD": unquote(teile.password or ""),
        "HOST": teile.hostname or "",
        "PORT": str(teile.port or ""),
        "OPTIONS": optionen,
    }


# ----------------------------------------------------------------------------- Grundschalter
DEBUG = env_bool("DJANGO_DEBUG", False)

# Läuft gerade die Testsuite? (pytest bzw. "manage.py test"). Nur dann gibt es
# einen zufälligen Ersatz-Schlüssel und keine https-Umleitung. pytest ist im
# Produktiv-Image nicht installiert und wird dort nie importiert.
TESTLAUF = "pytest" in sys.modules or sys.argv[1:2] == ["test"]

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        # Nur für die lokale Entwicklung – niemals im Betrieb verwenden.
        SECRET_KEY = "nur-entwicklung-unsicher-" + "x" * 40
    elif TESTLAUF:
        import secrets

        SECRET_KEY = "test-" + secrets.token_urlsafe(50)
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY fehlt. Ohne DJANGO_DEBUG=1 startet das Portal nicht ohne geheimen Schlüssel."
        )

ALLOWED_HOSTS = env_liste("DJANGO_ALLOWED_HOSTS")
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

CSRF_TRUSTED_ORIGINS = env_liste("DJANGO_CSRF_TRUSTED_ORIGINS")


# ----------------------------------------------------------------------------- Anwendungen
INSTALLED_APPS = [
    # Django-Admin mit Pflicht-2FA (eigene Site-Klasse, siehe kern/admin_site.py)
    "kern.adminconfig.PortalAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # Fremdpakete
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_htmx",
    # Projekt-Apps
    "kern",
    "konten",
    "berichte",
    "stammdaten",
    "auftraege",
    "personal",
    "dokumente",
    "kommunikation",
    "integrationen",
    "ki",
    "agenten",
    "vertrieb",
    "marketing",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # Früh, damit request.htmx auch in der 2FA-Middleware bekannt ist
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Ergänzt request.user um is_verified() (bestätigter zweiter Faktor)
    "django_otp.middleware.OTPMiddleware",
    # Admin/Büro ohne bestätigten zweiten Faktor → Einrichtung bzw. Code-Abfrage
    "konten.middleware.ZweiFaktorPflichtMiddleware",
    # Schreibt die E-Mail des angemeldeten Benutzers in die DB-Sitzung (Audit-Trigger)
    "kern.middleware.AuditBenutzerMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Content-Security-Policy und Permissions-Policy
    "kern.middleware.SicherheitsHeaderMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "kern.context_processors.portal",
            ],
        },
    },
]


# ----------------------------------------------------------------------------- Datenbank
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    raise ImproperlyConfigured(
        "DATABASE_URL fehlt (z. B. postgresql://benutzer:passwort@localhost:5432/datenbank)."
    )
DATABASES = {"default": datenbank_aus_url(DATABASE_URL)}
DATABASES["default"]["CONN_MAX_AGE"] = int(os.environ.get("DJANGO_DB_CONN_MAX_AGE", "60"))
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
if os.environ.get("DJANGO_TEST_DB_NAME"):
    DATABASES["default"]["TEST"] = {"NAME": os.environ["DJANGO_TEST_DB_NAME"]}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Zwischenspeicher in der Datenbank (Tabelle hh.django_cache, angelegt per
# Migration kern.0002). Funktioniert über mehrere Gunicorn-Prozesse hinweg –
# wichtig für die Anmeldesperre – und braucht keinen zusätzlichen Dienst.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}


# ----------------------------------------------------------------------------- Anmeldung & Passwörter
AUTH_USER_MODEL = "konten.Benutzer"
LOGIN_URL = "konten:anmelden"
LOGIN_REDIRECT_URL = "berichte:dashboard"
LOGOUT_REDIRECT_URL = "konten:anmelden"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ("email", "anzeigename")},
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Anmeldesperre: nach so vielen Fehlversuchen ist das Konto so lange gesperrt
ANMELDUNG_MAX_FEHLVERSUCHE = 5
ANMELDUNG_SPERRE_SEKUNDEN = 15 * 60

# Rollen, für die der zweite Faktor (TOTP) Pflicht ist
ZWEI_FAKTOR_PFLICHT_ROLLEN = ("admin", "buero")
OTP_TOTP_ISSUER = "Hausmeister Helden Portal"

# Pfad der Django-Verwaltungsoberfläche (ohne führenden Schrägstrich)
ADMIN_PFAD = os.environ.get("DJANGO_ADMIN_PFAD", "admin/").strip("/") + "/"


# ----------------------------------------------------------------------------- Sitzung, Cookies, Sicherheit
SESSION_COOKIE_AGE = 8 * 60 * 60  # 8 Stunden
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_NAME = "hh_sitzung"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_NAME = "hh_csrf"

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

if not DEBUG:
    # Hinter Caddy: Caddy setzt X-Forwarded-Proto und überschreibt Werte von außen.
    if env_bool("DJANGO_HINTER_PROXY", True):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SSL_REDIRECT", not TESTLAUF)
    # Gesundheitsprüfung des Containers läuft intern per http.
    SECURE_REDIRECT_EXEMPT = [r"^gesund$"]
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SEKUNDEN", str(365 * 24 * 60 * 60)))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # Preload ist nur für die Hauptdomain sinnvoll, nicht für portal.<domain>.
    SECURE_HSTS_PRELOAD = False
    SILENCED_SYSTEM_CHECKS = ["security.W021"]


# ----------------------------------------------------------------------------- Sprache & Zeit
LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True


# ----------------------------------------------------------------------------- Statische Dateien
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = Path(os.environ.get("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles")))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # Im Betrieb: komprimiert + Dateinamen mit Prüfsumme (lange cachebar).
        # In Entwicklung und Tests: ohne Manifest, damit kein collectstatic nötig ist.
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or TESTLAUF
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}


# Hochgeladene Dateien (Fotos, Dokumente); im Betrieb ein gesichertes Volume
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))
MEDIA_URL = "/medien/"

# In Entwicklung/Tests liefert WhiteNoise direkt aus den Quellordnern (ohne collectstatic)
WHITENOISE_AUTOREFRESH = DEBUG or TESTLAUF
WHITENOISE_USE_FINDERS = DEBUG or TESTLAUF


# ----------------------------------------------------------------------------- Protokollierung
LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        # Ausgabe auf stdout – Docker sammelt die Protokolle ein.
        "konsole": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["konsole"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["konsole"], "level": LOG_LEVEL, "propagate": False},
        "django.security": {"handlers": ["konsole"], "level": "INFO", "propagate": False},
        # SQL-Abfragen nie protokollieren (könnten personenbezogene Daten enthalten)
        "django.db.backends": {"handlers": ["konsole"], "level": "WARNING", "propagate": False},
        "kern": {"handlers": ["konsole"], "level": LOG_LEVEL, "propagate": False},
        "konten": {"handlers": ["konsole"], "level": LOG_LEVEL, "propagate": False},
        "berichte": {"handlers": ["konsole"], "level": LOG_LEVEL, "propagate": False},
    },
}

# TOTP-Schlüssel anderer Benutzer in der Verwaltungsoberfläche nicht anzeigen
OTP_ADMIN_HIDE_SENSITIVE_DATA = True
