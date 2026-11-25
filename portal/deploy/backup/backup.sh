#!/usr/bin/env bash
# Nächtliche Datensicherung des Portals:
#   1. pg_dump (Custom-Format) der Datenbank + Rollen (ohne Passwörter)
#      – zusammen mit den Zeilenanzahlen wichtiger Tabellen aus DEMSELBEN Datenbank-Snapshot
#   2. Dateien-Volume (hochgeladene Dokumente und Fotos)
#   3. alles verschlüsselt mit restic in das Repository aus RESTIC_REPOSITORY
#   4. Aufbewahrung: 7 täglich, 4 wöchentlich, 12 monatlich (forget --prune)
#   5. restic check
#
# Aufruf (als root auf dem Server, normalerweise über hh-backup.timer):
#   bash portal/deploy/backup/backup.sh          # Backup
#   bash portal/deploy/backup/backup.sh --init   # einmalig: restic-Repository anlegen
#
# Konfiguration aus portal/deploy/.env (oder HH_ENV_DATEI): RESTIC_REPOSITORY, RESTIC_PASSWORD,
# optional HH_MELDE_URL. Weitere optionale Variablen:
#   HH_BACKUP_DB_URL     lokale DB-URL statt Compose-Dienst "db" (für Tests)
#   HH_DATEIEN_PFAD      Pfad der Dateien (Standard: Mountpoint des Volumes hh-portal_dateien; "-" = überspringen)
#   HH_BACKUP_ARBEIT     Arbeitsordner (Standard /var/backups/hh-portal)
#   HH_CHECK_DATEN       z. B. "5%": restic check liest zusätzlich diesen Anteil der Daten
set -Eeuo pipefail
umask 077

# shellcheck source=gemeinsam.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/gemeinsam.sh"

lade_env "${HH_ENV_DATEI:-$DEPLOY_DIR/.env}" RESTIC_REPOSITORY RESTIC_PASSWORD HH_MELDE_URL
pruefe_restic
HH_RESTIC_HOST=${HH_RESTIC_HOST:-hh-portal}

INIT=0
[ "${1:-}" = "--init" ] && INIT=1

# Nur ein Lauf gleichzeitig
SPERRE=${HH_BACKUP_SPERRE:-/run/lock/hh-portal-backup.lock}
exec 9>"$SPERRE"
flock -n 9 || fehler "Es läuft bereits ein Backup ($SPERRE)."

DB_ORDNER="$HH_BACKUP_ARBEIT/db"
# Klartext-Dump nicht länger als nötig auf der Platte lassen; Fehler melden
beenden() {
  local rc=$?
  rm -f "$DB_ORDNER/hh.dump" "$DB_ORDNER/globals.sql"
  if [ "$rc" -ne 0 ]; then
    log "Backup FEHLGESCHLAGEN (Exit-Code $rc)"
    melden "${HH_MELDE_URL:-}" /fail
  fi
  exit "$rc"
}
trap beenden EXIT

if ! restic cat config >/dev/null 2>&1; then
  if [ "$INIT" = 1 ]; then
    log "Lege restic-Repository an …"
    restic init
  else
    fehler "restic-Repository nicht erreichbar oder nicht angelegt. Erstmalig: backup.sh --init"
  fi
fi
[ "$INIT" = 1 ] && { log "Repository bereit."; exit 0; }

mkdir -p "$DB_ORDNER"
chmod 700 "$HH_BACKUP_ARBEIT" "$DB_ORDNER"
rm -f "$DB_ORDNER"/*

# --- 1. Datenbank: Snapshot exportieren, Zeilen zählen, mit demselben Snapshot dumpen ---------
log "Sichere Datenbank $HH_DB_NAME …"
coproc PSQL { db_psql "$HH_DB_NAME" -A -t; }
echo "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SELECT pg_export_snapshot();" >&"${PSQL[1]}"
IFS= read -r -t 60 SNAPSHOT <&"${PSQL[0]}" || fehler "Konnte keinen Datenbank-Snapshot exportieren."
[[ "$SNAPSHOT" =~ ^[0-9A-F-]+$ ]] || fehler "Unerwartete Antwort beim Snapshot-Export: $SNAPSHOT"

{ zaehl_sql; echo '\echo __ENDE__'; } >&"${PSQL[1]}"
: > "$DB_ORDNER/zeilen.txt"
ende=0
while IFS= read -r -t 120 zeile <&"${PSQL[0]}"; do
  if [ "$zeile" = "__ENDE__" ]; then ende=1; break; fi
  echo "$zeile" >> "$DB_ORDNER/zeilen.txt"
done
[ "$ende" = 1 ] && [ -s "$DB_ORDNER/zeilen.txt" ] || fehler "Zeilenanzahlen konnten nicht ermittelt werden."

db_pg_dump --format=custom --compress=6 --snapshot="$SNAPSHOT" > "$DB_ORDNER/hh.dump"

echo "COMMIT;" >&"${PSQL[1]}"
PSQL_PID_MERKEN=$PSQL_PID
eval "exec ${PSQL[1]}>&-"
wait "$PSQL_PID_MERKEN" || fehler "psql-Sitzung für den Snapshot endete mit Fehler."

# Rollen (ohne Passwörter) – für die Wiederherstellung auf einem neuen Server
if [ -n "${HH_BACKUP_DB_URL:-}" ]; then
  pg_dumpall --globals-only --no-role-passwords -d "$HH_BACKUP_DB_URL" > "$DB_ORDNER/globals.sql"
else
  compose exec -T db pg_dumpall -U "$HH_DB_USER" --globals-only --no-role-passwords > "$DB_ORDNER/globals.sql"
fi

# Dump lesbar? (Inhaltsverzeichnis lesen)
if [ -n "${HH_BACKUP_DB_URL:-}" ]; then
  pg_restore --list "$DB_ORDNER/hh.dump" > /dev/null
else
  compose exec -T db pg_restore --list < "$DB_ORDNER/hh.dump" > /dev/null
fi
log "Dump ok: $(du -h "$DB_ORDNER/hh.dump" | cut -f1), Zeilen: $(tr '\n' ' ' < "$DB_ORDNER/zeilen.txt")"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$DB_ORDNER/zeitpunkt.txt"

# --- 2. Dateien -------------------------------------------------------------------------------
PFADE=("$DB_ORDNER")
DATEIEN=${HH_DATEIEN_PFAD:-}
if [ -z "$DATEIEN" ]; then
  DATEIEN=$(docker volume inspect --format '{{ .Mountpoint }}' hh-portal_dateien 2>/dev/null) \
    || fehler "Volume hh-portal_dateien nicht gefunden (HH_DATEIEN_PFAD setzen oder '-' zum Überspringen)."
fi
if [ "$DATEIEN" != "-" ]; then
  [ -d "$DATEIEN" ] || fehler "Dateien-Ordner fehlt: $DATEIEN"
  PFADE+=("$DATEIEN")
fi

# --- 3. restic --------------------------------------------------------------------------------
log "Lade Sicherung in das restic-Repository …"
restic backup --host "$HH_RESTIC_HOST" --tag "$HH_RESTIC_TAG" --one-file-system --no-scan "${PFADE[@]}"

log "Aufbewahrung anwenden (7 täglich, 4 wöchentlich, 12 monatlich) …"
restic forget --host "$HH_RESTIC_HOST" --tag "$HH_RESTIC_TAG" \
  --keep-daily 7 --keep-weekly 4 --keep-monthly 12 --prune

log "Repository prüfen …"
if [ -n "${HH_CHECK_DATEN:-}" ]; then
  restic check --read-data-subset="$HH_CHECK_DATEN"
else
  restic check
fi

log "Backup erfolgreich."
melden "${HH_MELDE_URL:-}" ""
