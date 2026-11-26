#!/bin/sh
# Tägliches PostgreSQL-Backup mit Rotation. Läuft im Container "backup" (siehe docker-compose.yml).
# Optional: Medien werden im S3-Bucket gehalten (dort Versionierung/Lifecycle aktivieren).
set -eu
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
DIR="${BACKUP_DIR:-/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DIR"
pg_dump --format=custom --no-owner "$DATABASE_URL_PG" > "$DIR/dealfehler-$STAMP.dump.tmp"
mv "$DIR/dealfehler-$STAMP.dump.tmp" "$DIR/dealfehler-$STAMP.dump"
find "$DIR" -name 'dealfehler-*.dump' -mtime +"$KEEP_DAYS" -delete
echo "Backup ok: $DIR/dealfehler-$STAMP.dump"
