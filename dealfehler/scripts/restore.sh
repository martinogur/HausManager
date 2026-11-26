#!/bin/sh
# Wiederherstellung: ./scripts/restore.sh /backups/dealfehler-YYYYmmdd-HHMMSS.dump
# ACHTUNG: überschreibt die Datenbank. Vorher Worker stoppen: docker compose stop worker beat
set -eu
[ -f "${1:-}" ] || { echo "Backup-Datei angeben"; exit 1; }
pg_restore --clean --if-exists --no-owner --dbname "$DATABASE_URL_PG" "$1"
echo "Wiederhergestellt aus $1 – danach: docker compose start worker beat"
