# syntax=docker/dockerfile:1.7
#
# Image der Web-Anwendung (Django + gunicorn) – Verwaltungsportal Hausmeister Helden
#
# Build-Kontext ist portal/app, das Datenbankschema kommt als zweiter Kontext "db" dazu,
# weil die Migration kern/0001_schema die Datei portal/db/schema.sql zur Laufzeit liest:
#
#   docker build -f portal/deploy/Dockerfile --build-context db=portal/db -t hh-portal-web portal/app
#
# (docker compose erledigt das automatisch, siehe docker-compose.yml)
#
# Im Container liegt die Repository-Struktur gespiegelt vor:
#   /srv/portal/app   Django-Projekt (manage.py, config/, …)
#   /srv/portal/db    schema.sql + erweiterungen/ (Migration kern/0003 liest sie zur Laufzeit)
#   /srv/portal/daten Hochgeladene Dateien (Volume, MEDIA_ROOT)
#   /srv/static       Kopie der statischen Dateien für Caddy (Volume, wird vom migrate-Job befüllt)

ARG PYTHON_IMAGE=python:3.13.18-slim-trixie

# ---------------------------------------------------------------------------
# Stufe 1: Abhängigkeiten in ein eigenes virtualenv installieren
# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS abhaengigkeiten

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN python -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
# Nur Laufzeit-Pakete (requirements.txt), keine Entwicklungswerkzeuge.
# Optional: CA-Zertifikat für Builds hinter einem TLS-prüfenden Proxy als BuildKit-Secret
# (--secret id=pip_ca,src=…); es landet nicht im Image.
RUN --mount=type=secret,id=pip_ca,required=false \
    if [ -s /run/secrets/pip_ca ]; then export PIP_CERT=/run/secrets/pip_ca; fi; \
    /opt/venv/bin/pip install -r /tmp/requirements.txt

# ---------------------------------------------------------------------------
# Stufe 2: schlankes Laufzeit-Image, Nicht-Root-Benutzer
# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS laufzeit

LABEL org.opencontainers.image.title="hh-portal-web" \
      org.opencontainers.image.description="Verwaltungsportal Hausmeister Helden (Django)" \
      org.opencontainers.image.vendor="Hausmeister Helden"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    DJANGO_SETTINGS_MODULE=config.settings

# Fester Benutzer ohne Login-Shell; UID/GID 10001 kollidieren nicht mit Host-Benutzern
RUN groupadd --system --gid 10001 portal \
 && useradd --system --uid 10001 --gid portal --no-create-home \
            --home-dir /srv/portal --shell /usr/sbin/nologin portal \
 && mkdir -p /srv/portal/daten /srv/static \
 && chown portal:portal /srv/portal/daten /srv/static

COPY --from=abhaengigkeiten /opt/venv /opt/venv

# Code und Schema gehören root und sind für den Dienst nur lesbar
COPY --from=db schema.sql /srv/portal/db/schema.sql
COPY --from=db erweiterungen /srv/portal/db/erweiterungen
COPY . /srv/portal/app
WORKDIR /srv/portal/app

# Statische Dateien beim Build einsammeln. Die Werte hier sind reine Platzhalter,
# damit die Einstellungen ohne DEBUG laden – sie landen nicht in der Laufzeit-Umgebung.
RUN DJANGO_DEBUG=0 \
    DJANGO_SECRET_KEY=nur-fuer-collectstatic-im-build-kein-geheimnis \
    DJANGO_ALLOWED_HOSTS=localhost \
    DJANGO_CSRF_TRUSTED_ORIGINS=https://localhost \
    DATABASE_URL=postgresql://build:build@localhost:5432/build \
    python manage.py collectstatic --noinput \
 && python -m compileall -q /srv/portal/app

# Gesundheitsprüfung ohne curl: fragt /gesund mit dem ersten erlaubten Hostnamen ab
# und meldet sich als HTTPS-Anfrage (wie hinter Caddy), damit kein Redirect greift.
COPY <<'EOF' /usr/local/bin/gesundheitscheck
#!/usr/bin/env python3
import os, sys, urllib.request

hosts = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
host = next((h.lstrip(".") for h in hosts if h != "*"), "localhost")

class KeinRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

anfrage = urllib.request.Request(
    "http://127.0.0.1:8000/gesund",
    headers={"Host": host, "X-Forwarded-Proto": "https"},
)
try:
    with urllib.request.build_opener(KeinRedirect).open(anfrage, timeout=4) as antwort:
        sys.exit(0 if antwort.status == 200 else 1)
except Exception as fehler:  # noqa: BLE001 – jede Störung heißt "nicht gesund"
    print(f"/gesund nicht erreichbar: {fehler}", file=sys.stderr)
    sys.exit(1)
EOF
RUN chmod 0755 /usr/local/bin/gesundheitscheck

USER portal:portal
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["/usr/local/bin/gesundheitscheck"]

# Worker-Anzahl über GUNICORN_WORKERS (Standard 3 für 2 vCPU).
# --forwarded-allow-ips="*" ist hier vertretbar, weil Port 8000 nur im internen
# Docker-Netz erreichbar ist (nur Caddy spricht mit gunicorn).
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout ${GUNICORN_TIMEOUT:-60} --max-requests 1000 --max-requests-jitter 100 --worker-tmp-dir /dev/shm --forwarded-allow-ips='*' --access-logfile - --error-logfile -"]
