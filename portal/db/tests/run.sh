#!/usr/bin/env bash
# Lädt schema.sql in eine frische, temporäre PostgreSQL-16-Datenbank und führt die Tests aus.
# Aufruf: bash portal/db/tests/run.sh   (braucht PostgreSQL 16 Binaries, z. B. /usr/lib/postgresql/16/bin)
set -euo pipefail
BIN=${PG_BIN:-/usr/lib/postgresql/16/bin}
HIER=$(cd "$(dirname "$0")" && pwd)
D=$(mktemp -d /tmp/hh-pgtest.XXXX); chmod 755 "$D"
cp "$HIER/../schema.sql" "$HIER/test_schema.sql" "$D/"; chmod 644 "$D"/*.sql
ALS="" ; [ "$(id -u)" = 0 ] && { chown postgres "$D"; ALS="su postgres -c"; }
lauf() { if [ -n "$ALS" ]; then su postgres -c "$1"; else bash -c "$1"; fi; }
lauf "$BIN/initdb -D $D/data -E UTF8 --locale=C.UTF-8 -A trust >/dev/null"
lauf "$BIN/pg_ctl -D $D/data -o '-k $D -p 5499 -c listen_addresses=' -l $D/log -w start >/dev/null"
trap 'lauf "$BIN/pg_ctl -D $D/data stop -m fast >/dev/null"; rm -rf "$D"' EXIT
lauf "$BIN/psql -h $D -p 5499 -q -v ON_ERROR_STOP=1 -c 'create database hh'"
lauf "$BIN/psql -h $D -p 5499 -d hh -q -v ON_ERROR_STOP=1 -f $D/schema.sql"
lauf "$BIN/psql -h $D -p 5499 -d hh -q -v ON_ERROR_STOP=1 -f $D/test_schema.sql" 2>&1 | grep -oE '(OK   .*|FEHLER.*|ALLE TESTS BESTANDEN)'
