# shellcheck shell=bash
# Gemeinsame Hilfen für backup.sh und restore-test.sh (wird per "source" geladen).
#
# Datenbankzugriff, zwei Betriebsarten:
#   - Standard (Server): über den Compose-Dienst "db" (docker compose exec), Binaries im Container
#   - Test/lokal:        HH_BACKUP_DB_URL=postgresql://… → lokale pg_dump/psql/pg_restore

BACKUP_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DEPLOY_DIR=$(cd "$BACKUP_DIR/.." && pwd)

# Pfad, unter dem der Dump im restic-Snapshot liegt (fest, damit restore-test ihn findet)
HH_BACKUP_ARBEIT=${HH_BACKUP_ARBEIT:-/var/backups/hh-portal}
HH_RESTIC_TAG=${HH_RESTIC_TAG:-hh-portal}
HH_DB_NAME=${HH_DB_NAME:-hh}
HH_DB_USER=${HH_DB_USER:-hh}
# Tabellen, deren Zeilenanzahl beim Backup festgehalten und beim Wiederherstellungstest verglichen wird
HH_PRUEF_TABELLEN=${HH_PRUEF_TABELLEN:-benutzer kunden ansprechpartner objekte leistungen auftraege einsaetze mitarbeiter arbeitszeiten bewerbungen angebote rechnungen dokumente fotos email_protokolle audit_log}

log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
fehler() { log "FEHLER: $*" >&2; exit 1; }

# Liest KEY=wert-Zeilen aus der .env-Datei, ohne sie als Shell-Code auszuführen.
# Exportiert nur die angegebenen Namen und überschreibt keine bereits gesetzten Variablen.
lade_env() {
  local datei=$1; shift
  [ -r "$datei" ] || return 0
  local zeile name wert gesucht
  while IFS= read -r zeile || [ -n "$zeile" ]; do
    [[ "$zeile" =~ ^([A-Z][A-Z0-9_]*)=(.*)$ ]] || continue
    name=${BASH_REMATCH[1]}
    wert=${BASH_REMATCH[2]}
    for gesucht in "$@"; do
      if [ "$name" = "$gesucht" ] && [ -z "${!name:-}" ]; then
        export "$name=$wert"
      fi
    done
  done < "$datei"
}

compose() {
  docker compose -f "$DEPLOY_DIR/docker-compose.yml" --project-directory "$DEPLOY_DIR" "$@"
}

# URL mit anderem Datenbanknamen (für HH_BACKUP_DB_URL)
url_mit_db() {
  local url=$1 db=$2 basis rest
  basis=${url%%\?*}
  rest=${url#"$basis"}
  printf '%s/%s%s' "${basis%/*}" "$db" "$rest"
}

# psql gegen eine Datenbank (Standard: Produktions-DB), liest SQL von stdin
db_psql() {
  local db=${1:-$HH_DB_NAME}; shift || true
  if [ -n "${HH_BACKUP_DB_URL:-}" ]; then
    psql "$(url_mit_db "$HH_BACKUP_DB_URL" "$db")" -X -q -v ON_ERROR_STOP=1 "$@"
  else
    compose exec -T db psql -U "$HH_DB_USER" -d "$db" -X -q -v ON_ERROR_STOP=1 "$@"
  fi
}

db_pg_dump() {
  if [ -n "${HH_BACKUP_DB_URL:-}" ]; then
    pg_dump "$(url_mit_db "$HH_BACKUP_DB_URL" "$HH_DB_NAME")" "$@"
  else
    compose exec -T db pg_dump -U "$HH_DB_USER" -d "$HH_DB_NAME" "$@"
  fi
}

# pg_restore in Datenbank $1, Dump kommt über stdin
db_pg_restore() {
  local db=$1; shift
  if [ -n "${HH_BACKUP_DB_URL:-}" ]; then
    pg_restore -d "$(url_mit_db "$HH_BACKUP_DB_URL" "$db")" "$@"
  else
    compose exec -T db pg_restore -U "$HH_DB_USER" -d "$db" "$@"
  fi
}

# SQL, das für jede Prüftabelle "tabelle|anzahl" ausgibt (-1 = Tabelle fehlt)
zaehl_sql() {
  local liste="" t
  for t in $HH_PRUEF_TABELLEN; do
    [[ "$t" =~ ^[a-z_][a-z0-9_]*$ ]] || fehler "Ungültiger Tabellenname: $t"
    liste+="${liste:+,}'$t'"
  done
  cat <<SQL
SELECT t || '|' || CASE WHEN to_regclass('hh.' || t) IS NULL THEN -1
       ELSE (xpath('/row/c/text()', query_to_xml(format('SELECT count(*) AS c FROM hh.%I', t), false, true, '')))[1]::text::bigint
       END
FROM unnest(ARRAY[$liste]::text[]) WITH ORDINALITY AS x(t, n) ORDER BY n;
SQL
}

pruefe_restic() {
  command -v restic >/dev/null 2>&1 || fehler "restic ist nicht installiert (apt install restic)."
  [ -n "${RESTIC_REPOSITORY:-}${RESTIC_REPOSITORY_FILE:-}" ] || fehler "RESTIC_REPOSITORY ist nicht gesetzt."
  [ -n "${RESTIC_PASSWORD:-}${RESTIC_PASSWORD_FILE:-}${RESTIC_PASSWORD_COMMAND:-}" ] || fehler "RESTIC_PASSWORD ist nicht gesetzt."
  case "${RESTIC_REPOSITORY:-}${RESTIC_PASSWORD:-}" in
    *PLATZHALTER*) fehler "RESTIC_REPOSITORY/RESTIC_PASSWORD enthalten noch Platzhalter." ;;
  esac
}

# Optionaler Ping an einen Überwachungsdienst (leere URL = aus).
# $1 = URL, $2 = "" bei Erfolg bzw. "/fail" bei Fehler (Schema wie Healthchecks.io)
melden() {
  local url=${1:-} suffix=${2:-}
  [ -n "$url" ] || return 0
  curl -fsS -m 10 --retry 3 -o /dev/null "${url%/}$suffix" || log "Hinweis: Meldung an den Überwachungsdienst fehlgeschlagen."
}
