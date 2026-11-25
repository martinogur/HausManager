#!/usr/bin/env bash
# Schema-Tests gegen einen laufenden PostgreSQL-16-Server (z. B. CI-Service-Container).
# Gegenstück zu run.sh (das einen eigenen Server mit lokalen Binaries startet).
#
# Aufruf:  SCHEMA_TEST_URL=postgresql://user:pass@host:5432/postgres bash portal/db/tests/run-ci.sh
#          (ohne SCHEMA_TEST_URL wird DATABASE_URL verwendet)
# Der Benutzer braucht das Recht, Datenbanken anzulegen. Es wird eine temporäre Datenbank
# angelegt und am Ende wieder gelöscht; bestehende Datenbanken bleiben unberührt.
set -euo pipefail
URL=${SCHEMA_TEST_URL:-${DATABASE_URL:?SCHEMA_TEST_URL oder DATABASE_URL setzen}}
HIER=$(cd "$(dirname "$0")" && pwd)
DB="hh_schematest_$$_$(date +%s)"

basis=${URL%%\?*}
rest=${URL#"$basis"}
ZIEL="${basis%/*}/$DB$rest"

psql "$URL" -X -q -v ON_ERROR_STOP=1 -c "CREATE DATABASE $DB TEMPLATE template0 ENCODING 'UTF8'"
trap 'psql "$URL" -X -q -c "DROP DATABASE IF EXISTS $DB WITH (FORCE)" >/dev/null 2>&1 || true' EXIT

psql "$ZIEL" -X -q -v ON_ERROR_STOP=1 -f "$HIER/../schema.sql"
for f in "$HIER"/../erweiterungen/[0-9]*.sql; do
  case "$f" in *_zurueck.sql) continue ;; esac
  psql "$ZIEL" -X -q -v ON_ERROR_STOP=1 -f "$f"
done
anzahl=0
for t in "$HIER"/test_*.sql; do
  AUSGABE=$(psql "$ZIEL" -X -q -v ON_ERROR_STOP=1 -f "$t" 2>&1) || {
    echo "$AUSGABE" | grep -oE '(OK   .*|FEHLER.*)' || echo "$AUSGABE"
    echo "Schema-Tests FEHLGESCHLAGEN ($t)" >&2
    exit 1
  }
  echo "$AUSGABE" | grep -oE '(OK   .*|FEHLER.*|ALLE TESTS BESTANDEN)'
  echo "$AUSGABE" | grep -q 'ALLE TESTS BESTANDEN' || { echo "Abschlussmeldung fehlt ($t)" >&2; exit 1; }
  anzahl=$((anzahl + $(echo "$AUSGABE" | grep -cE 'OK   ' || true)))
done
echo "$anzahl Tests OK"
