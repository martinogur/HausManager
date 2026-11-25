#!/usr/bin/env bash
# Wöchentlicher Wiederherstellungstest:
#   1. neuestes restic-Snapshot finden und Alter prüfen (RPO: höchstens HH_MAX_ALTER_STUNDEN, Standard 26 h)
#   2. Dump daraus holen und in eine TEMPORÄRE Datenbank wiederherstellen (Produktion bleibt unberührt)
#   3. Zeilenanzahlen wichtiger Tabellen mit den beim Backup festgehaltenen Werten vergleichen
#   4. temporäre Datenbank wieder löschen
#
# Aufruf (als root auf dem Server, normalerweise über hh-restore-test.timer):
#   bash portal/deploy/backup/restore-test.sh
#
# Konfiguration wie backup.sh (RESTIC_REPOSITORY, RESTIC_PASSWORD aus portal/deploy/.env),
# optional HH_MELDE_URL_RESTORE, HH_BACKUP_DB_URL (lokale DB statt Compose-Dienst), HH_SNAPSHOT (Standard latest).
set -Eeuo pipefail
umask 077

# shellcheck source=gemeinsam.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/gemeinsam.sh"

lade_env "${HH_ENV_DATEI:-$DEPLOY_DIR/.env}" RESTIC_REPOSITORY RESTIC_PASSWORD HH_MELDE_URL_RESTORE
pruefe_restic
HH_RESTIC_HOST=${HH_RESTIC_HOST:-hh-portal}
SNAPSHOT=${HH_SNAPSHOT:-latest}
MAX_ALTER=${HH_MAX_ALTER_STUNDEN:-26}

ARBEIT=$(mktemp -d "${TMPDIR:-/var/tmp}/hh-restore-test.XXXXXX")
TESTDB="hh_restore_test_$(date +%Y%m%d%H%M%S)"
TESTDB_ANGELEGT=0

beenden() {
  local rc=$?
  if [ "$TESTDB_ANGELEGT" = 1 ]; then
    echo "DROP DATABASE IF EXISTS \"$TESTDB\" WITH (FORCE);" | db_psql postgres >/dev/null 2>&1 \
      || log "Hinweis: temporäre Datenbank $TESTDB konnte nicht gelöscht werden."
  fi
  rm -rf "$ARBEIT"
  if [ "$rc" -ne 0 ]; then
    log "Wiederherstellungstest FEHLGESCHLAGEN (Exit-Code $rc)"
    melden "${HH_MELDE_URL_RESTORE:-}" /fail
  fi
  exit "$rc"
}
trap beenden EXIT

# --- 1. Snapshot ------------------------------------------------------------------------------
INFO=$(restic snapshots --json --host "$HH_RESTIC_HOST" --tag "$HH_RESTIC_TAG" ${SNAPSHOT:+--latest 1}) \
  || fehler "Snapshots konnten nicht gelesen werden."
read -r SNAP_ID SNAP_ZEIT < <(python3 -c '
import json, sys
s = json.load(sys.stdin)
if not s: sys.exit(1)
s = sorted(s, key=lambda x: x["time"])[-1]
print(s["short_id"], s["time"])' <<<"$INFO") || fehler "Kein Snapshot mit Tag $HH_RESTIC_TAG gefunden."
[ "$SNAPSHOT" = latest ] || SNAP_ID=$SNAPSHOT

alter_std=$(( ( $(date +%s) - $(date -d "$SNAP_ZEIT" +%s) ) / 3600 ))
log "Snapshot $SNAP_ID vom $SNAP_ZEIT (vor $alter_std h)"
if [ "$SNAPSHOT" = latest ] && [ "$alter_std" -gt "$MAX_ALTER" ]; then
  fehler "Neuestes Backup ist $alter_std h alt (Grenze $MAX_ALTER h) – Backup-Lauf prüfen!"
fi

# --- 2. Dump holen und wiederherstellen -------------------------------------------------------
restic dump "$SNAP_ID" "$HH_BACKUP_ARBEIT/db/hh.dump" > "$ARBEIT/hh.dump"
restic dump "$SNAP_ID" "$HH_BACKUP_ARBEIT/db/zeilen.txt" > "$ARBEIT/zeilen-erwartet.txt"
[ -s "$ARBEIT/hh.dump" ] || fehler "Dump im Snapshot ist leer."

log "Stelle in temporäre Datenbank $TESTDB wieder her …"
echo "CREATE DATABASE \"$TESTDB\" TEMPLATE template0 ENCODING 'UTF8';" | db_psql postgres
TESTDB_ANGELEGT=1
db_pg_restore "$TESTDB" --no-owner --no-privileges --exit-on-error < "$ARBEIT/hh.dump"

# --- 3. Zeilen vergleichen --------------------------------------------------------------------
zaehl_sql | db_psql "$TESTDB" -A -t > "$ARBEIT/zeilen-ist.txt"

fehlerzahl=0
while IFS='|' read -r tabelle erwartet; do
  [ -n "$tabelle" ] || continue
  ist=$(grep -E "^${tabelle}\|" "$ARBEIT/zeilen-ist.txt" | cut -d'|' -f2 || true)
  if [ "$erwartet" = "-1" ]; then
    log "  $tabelle: fehlte schon im Original (übersprungen)"
  elif [ "$ist" = "$erwartet" ]; then
    log "  OK   $tabelle: $ist Zeilen"
  else
    log "  FEHL $tabelle: erwartet $erwartet, wiederhergestellt ${ist:-?}"
    fehlerzahl=$((fehlerzahl + 1))
  fi
done < "$ARBEIT/zeilen-erwartet.txt"

# Schema-Grundprüfung: Schema hh und Migrationstabelle vorhanden
echo "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'hh';" \
  | db_psql "$TESTDB" -A -t > "$ARBEIT/tabellen.txt"
log "  Tabellen im Schema hh: $(cat "$ARBEIT/tabellen.txt")"
[ "$(cat "$ARBEIT/tabellen.txt")" -gt 0 ] || fehlerzahl=$((fehlerzahl + 1))

[ "$fehlerzahl" -eq 0 ] || fehler "$fehlerzahl Abweichung(en) beim Wiederherstellungstest."

log "Wiederherstellungstest erfolgreich (Snapshot $SNAP_ID)."
melden "${HH_MELDE_URL_RESTORE:-}" ""
