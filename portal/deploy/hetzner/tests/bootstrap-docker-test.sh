#!/usr/bin/env bash
# Integrationstest des Bootstrap-Teils von cloud-init.yaml mit echtem Docker (Domain localhost):
#   .env-Erzeugung → Clone von portal-live → Build → migrate → up -d → /gesund → Backup →
#   zweiter Lauf ohne neuen Commit (nichts passiert) → neuer Commit (Update) → hh-status.
# Ohne System-Teil (apt, ufw, swap, systemd). Belegt die Ports 80/443 des Rechners.
#
#   bash portal/deploy/hetzner/tests/bootstrap-docker-test.sh [arbeitsordner]
#
# Hinter einem TLS-prüfenden Proxy: HH_TEST_CA=/pfad/ca.crt (wird als BuildKit-Secret pip_ca
# übergeben, Build mit --network host).
set -Eeuo pipefail
HIER=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REPO=$(cd "$HIER/../../.." && pwd)
W=${1:-$(mktemp -d)}
mkdir -p "$W"; W=$(cd "$W" && pwd)
echo "Arbeitsordner: $W"
fehler() { echo "TEST FEHLGESCHLAGEN: $*" >&2; exit 1; }

# 1. Skripte und Einstellungen aus cloud-init.yaml auspacken
rm -rf "$W/bin" "$W/etc"; mkdir -p "$W/bin" "$W/etc"
python3 - "$HIER/cloud-init.yaml" "$W" <<'EOF'
import os, sys, yaml
for f in yaml.safe_load(open(sys.argv[1]))["write_files"]:
    name = os.path.basename(f["path"])
    if f["content"].startswith("#!"):
        ziel = os.path.join(sys.argv[2], "bin", name)
    elif name == "einstellungen":
        ziel = os.path.join(sys.argv[2], "etc", name)
    else:
        continue
    open(ziel, "w").write(f["content"])
    os.chmod(ziel, 0o755)
EOF

# 2. Test-"GitHub": lokales Repo mit Zweig portal-live = aktueller Arbeitsstand
rm -rf "$W/origin"
git clone --quiet --no-hardlinks "$REPO" "$W/origin"
rm -rf "$W/origin/portal"; mkdir -p "$W/origin/portal"
tar -C "$REPO/portal" --exclude=./deploy/.env --exclude=__pycache__ --exclude=.pytest_cache -cf - . | tar -C "$W/origin/portal" -xf -
git -C "$W/origin" checkout --quiet -B portal-live
git -C "$W/origin" add -A portal
git -C "$W/origin" -c user.name=test -c user.email=test@example.org commit --quiet -m "Test portal-live" --allow-empty

# 3. Test-Override: Build hinter dem Proxy
EXTRA="$W/compose.test.yml"
if [ -n "${HH_TEST_CA:-}" ]; then
  cat > "$EXTRA" <<EOF
services:
  web:
    build: {network: host, secrets: [pip_ca]}
  migrate:
    build: {network: host, secrets: [pip_ca]}
secrets:
  pip_ca:
    file: $HH_TEST_CA
EOF
else
  echo "services: {}" > "$EXTRA"
fi

export PATH="$W/bin:$PATH"
export HH_EINSTELLUNGEN="$W/etc/einstellungen" HH_DOMAIN=localhost HH_BASIS="$W/srv" HH_LOG_DIR="$W/log" \
       HH_REPO_URL="file://$W/origin" HH_BRANCH=portal-live HH_COMPOSE_EXTRA="$EXTRA" \
       HH_NUR_PORTAL=1 HH_OHNE_SYSTEMD=1

# 4. Ersteinrichtung
hh-einrichten
[ "$(stat -c %a "$HH_BASIS/.env")" = 600 ] || fehler ".env hat nicht Rechte 600"
grep -q '^DJANGO_ALLOWED_HOSTS=localhost$' "$HH_BASIS/.env" || fehler "ALLOWED_HOSTS"
grep -q '^ACME_EMAIL=info@haus-meister-helden.de$' "$HH_BASIS/.env" || fehler "ACME_EMAIL"
grep -Eq '^DJANGO_SECRET_KEY=[0-9a-f]{100}$' "$HH_BASIS/.env" || fehler "SECRET_KEY"
PW=$(sed -n 's/^POSTGRES_PASSWORD=//p' "$HH_BASIS/.env")
grep -q "^DATABASE_URL=postgresql://hh:$PW@db:5432/hh$" "$HH_BASIS/.env" || fehler "DATABASE_URL passt nicht zu POSTGRES_PASSWORD"
[ -L "$HH_BASIS/repo/portal/deploy/.env" ] || fehler "Symlink portal/deploy/.env fehlt"
grep -q ' OK ' "$HH_BASIS/stand/letztes-update" || fehler "erstes Update nicht OK: $(cat "$HH_BASIS/stand/letztes-update")"
[ "$(docker inspect -f '{{.State.ExitCode}}' "$(hh-compose ps -aq migrate)")" = 0 ] || fehler "migrate-Job"
curl -fsSk --resolve localhost:443:127.0.0.1 https://localhost/gesund | grep -q ok || fehler "/gesund über Caddy"
echo "OK: Ersteinrichtung, /gesund antwortet"

# 5. Zweiter Lauf der Einrichtung: .env bleibt, kein neues Update
cp "$HH_BASIS/.env" "$W/env.vorher"
hh-einrichten >/dev/null
cmp -s "$HH_BASIS/.env" "$W/env.vorher" || fehler ".env wurde überschrieben"
zeilen=$(wc -l < "$HH_LOG_DIR/hh-update.log")
hh-update
[ "$(wc -l < "$HH_LOG_DIR/hh-update.log")" = "$zeilen" ] || fehler "hh-update ohne neuen Commit hat etwas getan"
echo "OK: idempotent"

# 6. Neuer Commit auf portal-live → Update mit Sicherung vorher
git -C "$W/origin" -c user.name=test -c user.email=test@example.org commit --quiet --allow-empty -m "Test-Update"
hh-update
[ "$(cat "$HH_BASIS/stand/aktiv")" = "$(git -C "$W/origin" rev-parse HEAD)" ] || fehler "Update nicht ausgerollt"
ls "$HH_BASIS/backups"/hh-*-vor-update.dump >/dev/null || fehler "keine Sicherung vor dem Update"
docker image inspect "hh-portal-web:$(git -C "$W/origin" rev-parse --short=12 HEAD)" >/dev/null || fehler "Image-Tag"
echo "OK: Update mit Sicherung"

# 7. tägliche Sicherung, Admin-Befehl (nicht interaktiv über HH_ADMIN_PASSWORT), Status
hh-backup taeglich
docker compose version >/dev/null
hh-compose exec -T -e HH_ADMIN_PASSWORT=Test-Passwort-2026-lang web \
  python manage.py admin_anlegen --email admin@example.org --name "Test Admin" | grep -q angelegt || fehler "admin_anlegen"
hh-status | tee "$W/status.txt"
grep -q "Portal antwortet\|gültiges Zertifikat" "$W/status.txt" || fehler "hh-status /gesund"

# 8. Kaputter Commit: Build schlägt fehl → alte Version läuft weiter, Commit wird übersprungen
AKTIV=$(cat "$HH_BASIS/stand/aktiv")
echo 'RUN false' >> "$W/origin/portal/deploy/Dockerfile"
git -C "$W/origin" -c user.name=test -c user.email=test@example.org commit --quiet -am "Kaputter Build"
if hh-update; then fehler "kaputter Build wurde nicht erkannt"; fi
[ "$(cat "$HH_BASIS/stand/aktiv")" = "$AKTIV" ] || fehler "aktiv-Stand verändert"
[ "$(git -C "$HH_BASIS/repo" rev-parse HEAD)" = "$AKTIV" ] || fehler "Repo nicht auf alte Version zurückgesetzt"
grep -q FEHLER "$HH_BASIS/stand/letztes-update" || fehler "Fehler nicht vermerkt"
curl -fsSk --resolve localhost:443:127.0.0.1 https://localhost/gesund | grep -q ok || fehler "alte Version antwortet nicht"
hh-update || fehler "übersprungener Commit führt erneut zu Fehler"
# Zurückrollen = portal-live auf den guten Commit setzen (force push)
git -C "$W/origin" reset --quiet --hard HEAD~1
hh-update
[ "$(cat "$HH_BASIS/stand/aktiv")" = "$AKTIV" ] || fehler "Zurückrollen"
echo "OK: kaputter Commit abgefangen, Zurückrollen per portal-live"
echo "ALLE BOOTSTRAP-TESTS OK"
echo "Aufräumen: HH_EINSTELLUNGEN=$HH_EINSTELLUNGEN HH_BASIS=$HH_BASIS HH_COMPOSE_EXTRA=$EXTRA PATH=$W/bin:\$PATH hh-compose down -v"
