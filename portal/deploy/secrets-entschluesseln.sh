#!/usr/bin/env bash
# Entschlüsselt portal/deploy/secrets.enc.yaml (SOPS + age) in den Arbeitsspeicher.
#
# Ergebnis:  /run/hh-portal/portal.env  (tmpfs, Rechte 600, Ordner 700)
#            portal/deploy/.env  → Symlink darauf (für docker compose und backup.sh)
# Nach einem Neustart ist /run leer; der systemd-Dienst hh-secrets.service ruft das Skript
# deshalb vor dem Start des Portals erneut auf.
#
# Aufruf (als root auf dem Server):
#   bash portal/deploy/secrets-entschluesseln.sh
#
# Umgebungsvariablen (alle optional):
#   SOPS_AGE_KEY_FILE   privater age-Schlüssel        (Standard /etc/hh-portal/age.key)
#   HH_SECRETS_DATEI    verschlüsselte Datei          (Standard <dieser Ordner>/secrets.enc.yaml)
#   HH_SECRETS_ZIEL     Zielordner (muss tmpfs sein)  (Standard /run/hh-portal)
#   HH_KEIN_LINK=1      keinen Symlink .env anlegen
#   HH_ERLAUBE_KEIN_TMPFS=1  nur für Tests: Ziel darf auf normaler Platte liegen
set -euo pipefail
umask 077

HIER=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
QUELLE=${HH_SECRETS_DATEI:-$HIER/secrets.enc.yaml}
ZIEL=${HH_SECRETS_ZIEL:-/run/hh-portal}
export SOPS_AGE_KEY_FILE=${SOPS_AGE_KEY_FILE:-/etc/hh-portal/age.key}
SOPS=${SOPS:-sops}

fehler() { echo "FEHLER: $*" >&2; exit 1; }

command -v "$SOPS" >/dev/null 2>&1 || fehler "sops ist nicht installiert (siehe docs/04-betrieb.md)."
[ -f "$QUELLE" ] || fehler "Verschlüsselte Datei fehlt: $QUELLE"
[ -r "$SOPS_AGE_KEY_FILE" ] || fehler "age-Schlüssel nicht lesbar: $SOPS_AGE_KEY_FILE"

# Der private Schlüssel darf nur für den Besitzer lesbar sein
rechte=$(stat -c '%a' "$SOPS_AGE_KEY_FILE")
case "$rechte" in
  400|600) ;;
  *) fehler "age-Schlüssel hat Rechte $rechte – bitte: chmod 600 $SOPS_AGE_KEY_FILE" ;;
esac

mkdir -p "$ZIEL"
chmod 700 "$ZIEL"
dateisystem=$(stat -f -c '%T' "$ZIEL")
if [ "$dateisystem" != "tmpfs" ] && [ "$dateisystem" != "ramfs" ] && [ "${HH_ERLAUBE_KEIN_TMPFS:-0}" != "1" ]; then
  fehler "$ZIEL liegt nicht im Arbeitsspeicher (Dateisystem: $dateisystem). Abbruch, damit keine Klartext-Secrets auf die Platte gelangen."
fi

tmp=$(mktemp "$ZIEL/.portal.env.XXXXXX")
trap 'rm -f "$tmp"' EXIT

"$SOPS" --decrypt --input-type yaml --output-type dotenv "$QUELLE" > "$tmp"

# Prüfen: nur KEY=wert-Zeilen mit sicheren Zeichen (docker compose würde $ und Anführungszeichen auswerten)
zeile_nr=0
while IFS= read -r zeile || [ -n "$zeile" ]; do
  zeile_nr=$((zeile_nr + 1))
  [ -z "$zeile" ] && continue
  case "$zeile" in \#*) continue ;; esac
  if ! [[ "$zeile" =~ ^[A-Z][A-Z0-9_]*=[A-Za-z0-9._:/@,+=%-]*$ ]]; then
    schluessel=${zeile%%=*}
    fehler "Zeile $zeile_nr ($schluessel): ungültiger Name oder unerlaubte Zeichen im Wert. Erlaubt: A-Z a-z 0-9 . _ : / @ , + = % -"
  fi
done < "$tmp"

for pflicht in DJANGO_SECRET_KEY DJANGO_ALLOWED_HOSTS DJANGO_CSRF_TRUSTED_ORIGINS DATABASE_URL POSTGRES_PASSWORD ACME_EMAIL; do
  grep -q "^${pflicht}=." "$tmp" || fehler "Pflichtwert fehlt oder ist leer: $pflicht"
done
if grep -q 'PLATZHALTER' "$tmp"; then
  fehler "In den Secrets steht noch ein PLATZHALTER – bitte mit 'sops $QUELLE' ersetzen."
fi

chmod 600 "$tmp"
mv -f "$tmp" "$ZIEL/portal.env"
trap - EXIT

if [ "${HH_KEIN_LINK:-0}" != "1" ]; then
  ln -sfn "$ZIEL/portal.env" "$HIER/.env"
fi

anzahl=$(grep -c '^[A-Z]' "$ZIEL/portal.env" || true)
echo "OK: $anzahl Werte nach $ZIEL/portal.env entschlüsselt (Rechte 600)."
