# Betriebshandbuch: Verwaltungsportal Hausmeister Helden

Stand: 25.11.2026 · Phase 2 · Status: **Entwurf. Nichts davon ist gebucht oder eingerichtet.**

> **Wichtig:** Server, Storage Box und alle anderen kostenpflichtigen Dienste werden erst gebucht,
> wenn Martin das freigegeben hat (laut Plan ab Phase 3 für die Testumgebung). Bis dahin läuft
> alles nur lokal und in der CI. Echte Zugangsdaten gehören nie ins Repository, in den Chat oder in E-Mails.

---

## 1. Überblick

```
Internet ──► Hetzner Cloud Firewall (22, 80, 443)
              │
              ▼
          ┌──────────── Server (Ubuntu 24.04) ─────────────────────────────┐
          │  caddy  :80/:443  HTTPS, HSTS, Security-Header, statische Dateien │
          │    │  (Netz "aussen" + "intern")                                 │
          │    ▼                                                             │
          │  web (Django + gunicorn, Nicht-Root, read-only)  ── Volume dateien │
          │    │  (nur Netz "intern", kein Zugang nach außen)                │
          │    ▼                                                             │
          │  db (PostgreSQL 16, kein veröffentlichter Port) ── Volume pg_daten │
          │                                                                  │
          │  systemd: hh-secrets → hh-portal · hh-backup.timer · hh-restore-test.timer │
          └──────────────────────────────────────────────────────────────────┘
              │ nachts, verschlüsselt (restic)
              ▼
          Hetzner Storage Box (anderer Standort)
```

| Datei | Zweck |
|---|---|
| `portal/deploy/Dockerfile` | Image der Web-Anwendung (Multi-Stage, Python 3.13, Nicht-Root, `collectstatic` im Build, Healthcheck `/gesund`) |
| `portal/deploy/docker-compose.yml` | Dienste `caddy`, `web`, `migrate` (Einmal-Job), `db` |
| `portal/deploy/Caddyfile` | HTTPS, HSTS, Security-Header, zstd/gzip, statische Dateien |
| `portal/deploy/.env.example` | Vorlage aller Umgebungsvariablen (nur Platzhalter) |
| `portal/deploy/.sops.yaml`, `secrets.beispiel.yaml` | Regeln und Aufbau der verschlüsselten Secrets |
| `portal/deploy/secrets-entschluesseln.sh` | entschlüsselt `secrets.enc.yaml` nach `/run/hh-portal/portal.env` (Arbeitsspeicher) |
| `portal/deploy/backup/backup.sh` | pg_dump + Dateien → restic, Aufbewahrung, `restic check` |
| `portal/deploy/backup/restore-test.sh` | stellt das letzte Backup in eine temporäre DB wieder her und vergleicht Zeilenanzahlen |
| `portal/deploy/backup/systemd/*` | systemd-Units und Timer (Alternative: `backup/cron.beispiel`) |
| `.github/workflows/portal-tests.yml` | automatische Tests bei jedem Push (kein Deployment) |

Notfall: siehe [`wiederherstellung.md`](wiederherstellung.md).

---

## 2. Kosten (Richtwerte, netto, vor Buchung auf hetzner.com prüfen)

| Posten | ca. €/Monat | Wann |
|---|---|---|
| Hetzner Cloud Server, 2 vCPU / 4 GB RAM / 40 GB (Shared vCPU, z. B. Typ CX22 oder aktueller Nachfolger) | 4–7 | nach Freigabe (Phase 3) |
| Automatische Server-Backups bei Hetzner (+20 % des Serverpreises, 7 Abbilder) | 1–2 | mit dem Server |
| Öffentliche IPv4-Adresse (falls nicht im Serverpreis enthalten) | ca. 0,60 | mit dem Server |
| Hetzner Storage Box BX11 (1 TB) für restic | ca. 4 | nach Freigabe (Phase 3/8) |
| Hetzner Cloud Firewall, Let's Encrypt, Docker, Caddy, restic, SOPS, age, GitHub Actions (öffentliche Standard-Runner bzw. Freikontingent) | 0 | – |
| **Summe Betrieb** | **ca. 10–14** | |

Kein Posten wird ohne Martins ausdrückliche Freigabe gebucht. Das Kostenlimit wird in der Hetzner Console unter *Limits/Benachrichtigungen* hinterlegt.

---

## 3. Server einrichten (Schritt für Schritt)

Alle Befehle als Beispiel; `<…>` ersetzen. Zeitbedarf beim ersten Mal: ca. 2–3 Stunden.

### 3.1 Server anlegen (erst nach Freigabe)
1. Martin legt in der [Hetzner Console](https://console.hetzner.cloud) ein Projekt „hh-portal“ an und schließt den **AV-Vertrag** (Auftragsverarbeitung nach DSGVO) ab.
2. Neuer Server:
   - Standort **Falkenstein** oder **Nürnberg** (Deutschland)
   - Image **Ubuntu 24.04**
   - Typ: 2 vCPU, 4 GB RAM
   - **Backups** aktivieren
   - SSH-Schlüssel hinterlegen (Schritt 3.2), **kein Root-Passwort**
   - Firewall aus Schritt 3.3 zuweisen
   - Name: `hh-portal-1`
3. DNS bei IONOS: `A`-Eintrag (und ggf. `AAAA`) `portal.haus-meister-helden.de` → IP des Servers. TTL anfangs 300 s.

### 3.2 SSH-Schlüssel
Auf Martins Rechner (bzw. dem Rechner, von dem administriert wird):
```bash
ssh-keygen -t ed25519 -C "hh-portal-admin" -f ~/.ssh/hh-portal
# Inhalt von ~/.ssh/hh-portal.pub in der Hetzner Console unter "SSH-Keys" hinzufügen
```
Den privaten Schlüssel mit Passphrase schützen und im Passwort-Manager sichern.

Nach dem ersten Login einen eigenen Admin-Benutzer anlegen und Root-Login abschalten:
```bash
ssh -i ~/.ssh/hh-portal root@<server-ip>
adduser --disabled-password --gecos "" betrieb
usermod -aG sudo betrieb
install -d -m 700 -o betrieb -g betrieb /home/betrieb/.ssh
cp /root/.ssh/authorized_keys /home/betrieb/.ssh/ && chown betrieb: /home/betrieb/.ssh/authorized_keys
passwd betrieb     # Passwort nur für sudo, im Passwort-Manager ablegen

cat > /etc/ssh/sshd_config.d/10-hh.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
EOF
sshd -t && systemctl reload ssh
```
In einem **zweiten** Terminal prüfen, dass `ssh -i ~/.ssh/hh-portal betrieb@<server-ip>` funktioniert, bevor die erste Sitzung geschlossen wird.

### 3.3 Firewall (Ports 22, 80, 443)
**Hetzner Cloud Firewall** (kostenlos, wirkt vor dem Server, auch für Docker-Ports):

| Richtung | Protokoll | Port | Quelle |
|---|---|---|---|
| eingehend | TCP | 22 | am besten nur feste IP(s) des Büros, sonst alle |
| eingehend | TCP | 80 | alle (Let's Encrypt + Umleitung auf HTTPS) |
| eingehend | TCP | 443 | alle |
| eingehend | UDP | 443 | alle (HTTP/3, optional) |
| ausgehend | alles | – | erlaubt |

Zusätzlich auf dem Server `ufw` als zweite Schicht:
```bash
apt install -y ufw
ufw default deny incoming && ufw default allow outgoing
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw allow 443/udp
ufw enable
```
Hinweis: Docker umgeht `ufw` für veröffentlichte Ports. Das ist hier unkritisch, weil nur Caddy (80/443) Ports veröffentlicht. Die Datenbank hat absichtlich **keinen** veröffentlichten Port. Maßgeblich ist die Hetzner-Firewall.

### 3.4 Automatische Sicherheitsupdates
```bash
apt update && apt full-upgrade -y
apt install -y unattended-upgrades apt-listchanges
dpkg-reconfigure -plow unattended-upgrades      # "Ja"
cat > /etc/apt/apt.conf.d/52hh-unattended <<'EOF'
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:15";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
EOF
timedatectl set-timezone Europe/Berlin
```
Der Neustart um 04:15 liegt zwischen Backup (02:30) und Wiederherstellungstest (So 05:00). Nach einem Neustart startet systemd die Secrets und das Portal automatisch (Abschnitt 3.8).

### 3.5 Docker installieren (offizielles Repository)
```bash
apt install -y ca-certificates curl git restic age
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  > /etc/apt/sources.list.d/docker.list
apt update && apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
cat > /etc/docker/daemon.json <<'EOF'
{ "log-driver": "json-file", "log-opts": { "max-size": "10m", "max-file": "5" }, "live-restore": true }
EOF
systemctl restart docker
```
Den Benutzer `betrieb` **nicht** in die Gruppe `docker` aufnehmen (das wäre gleichbedeutend mit Root). Docker-Befehle mit `sudo`.

### 3.6 Code auf den Server holen
Lesender **Deploy-Key** (kostenlos) statt persönlichem Token:
```bash
sudo ssh-keygen -t ed25519 -N "" -C "hh-portal-1 deploy" -f /root/.ssh/github-deploy
sudo cat /root/.ssh/github-deploy.pub
# → GitHub: Repository → Settings → Deploy keys → Add (nur lesen, "Allow write access" NICHT anhaken)
sudo GIT_SSH_COMMAND="ssh -i /root/.ssh/github-deploy" git clone git@github.com:<owner>/<repo>.git /opt/hh-portal
```

### 3.7 Secrets (SOPS + age)
Prinzip: Die Zugangsdaten liegen **verschlüsselt** in `portal/deploy/secrets.enc.yaml` im Repository. Entschlüsseln kann nur, wer einen der privaten age-Schlüssel hat:
1. Server-Schlüssel `/etc/hh-portal/age.key`, liegt nur auf dem Server.
2. Notfall-Schlüssel von Martin, liegt nur in seinem Passwort-Manager.

Zur Laufzeit stehen die Werte nur im Arbeitsspeicher (`/run/hh-portal/portal.env`, tmpfs).

**sops installieren** (ein einzelnes Programm; Version von <https://github.com/getsops/sops/releases> wählen und die Prüfsumme mit der `checksums.txt` des Releases vergleichen):
```bash
V=<version, z. B. 3.x.y>
curl -fsSLO https://github.com/getsops/sops/releases/download/v$V/sops-v$V.linux.amd64
curl -fsSLO https://github.com/getsops/sops/releases/download/v$V/sops-v$V.checksums.txt
sha256sum --ignore-missing -c sops-v$V.checksums.txt
install -m 0755 sops-v$V.linux.amd64 /usr/local/bin/sops
```

**Schlüssel erzeugen** (auf dem Server; der private Teil verlässt ihn nie):
```bash
install -d -m 700 /etc/hh-portal
age-keygen -o /etc/hh-portal/age.key && chmod 600 /etc/hh-portal/age.key
age-keygen -y /etc/hh-portal/age.key        # → Public Key des Servers (age1…)
```
Martin erzeugt seinen Notfall-Schlüssel auf seinem Rechner (`age-keygen -o hh-notfall.key`). Den **Inhalt** legt er als sichere Notiz im Passwort-Manager ab und löscht danach die Datei. Den Public Key (`age1…`) gibt er weiter.

**Beide Public Keys** in `portal/deploy/.sops.yaml` statt der Platzhalter eintragen. Danach die Secrets anlegen:
```bash
cd /opt/hh-portal/portal/deploy
cp secrets.beispiel.yaml secrets.enc.yaml
sops --encrypt --in-place secrets.enc.yaml   # erst verschlüsseln …
sops secrets.enc.yaml                        # … dann im Editor die echten Werte eintragen
```
Werte erzeugen: `openssl rand -hex 32`. Erlaubte Zeichen: `A–Z a–z 0–9 . _ : / @ , + = % -`. Das Skript lehnt `$`, Leerzeichen und Anführungszeichen ab, weil docker compose sie auswerten würde. `POSTGRES_PASSWORD` und das Passwort in `DATABASE_URL` müssen gleich sein.

Die **verschlüsselte** Datei `secrets.enc.yaml` und die geänderte `.sops.yaml` dürfen committet werden. Unverschlüsselte Kopien nie. Prüfen: `head secrets.enc.yaml` zeigt `ENC[AES256_GCM,…]`.

Entschlüsseln (macht systemd beim Start automatisch):
```bash
sudo bash /opt/hh-portal/portal/deploy/secrets-entschluesseln.sh
# → /run/hh-portal/portal.env (600) und Symlink portal/deploy/.env
```
Das Skript bricht ab, wenn der Schlüssel zu offene Rechte hat, das Ziel nicht im Arbeitsspeicher liegt, ein Pflichtwert fehlt oder noch `PLATZHALTER` drinsteht.

**Secret ändern:** `sops secrets.enc.yaml` → committen → auf dem Server `git pull`, Skript ausführen, `docker compose up -d`.
**Server-Schlüssel tauschen** (z. B. neuer Server): neuen Public Key in `.sops.yaml` eintragen, dann `sops updatekeys secrets.enc.yaml`. Dafür wird ein noch gültiger Schlüssel gebraucht, im Notfall der von Martin.

### 3.8 systemd-Dienste installieren
```bash
cd /opt/hh-portal/portal/deploy/backup/systemd
sudo cp hh-secrets.service hh-portal.service hh-backup.service hh-backup.timer \
        hh-restore-test.service hh-restore-test.timer hh-alarm@.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hh-secrets.service hh-portal.service
sudo systemctl enable --now hh-backup.timer hh-restore-test.timer
systemctl list-timers 'hh-*'
```
Die Units erwarten das Repository unter `/opt/hh-portal`. Alternative zu den Timern: `backup/cron.beispiel` (nur **eine** Variante nutzen).

---

## 4. Deployment

Phase 2 hat **keinen** automatischen Deployment-Job. Jedes Update auf dem Server erfolgt von Hand und nur nach Martins Freigabe der jeweiligen Version.

### 4.1 Erstes Starten
```bash
cd /opt/hh-portal/portal/deploy
sudo bash secrets-entschluesseln.sh
sudo PORTAL_VERSION=$(git rev-parse --short HEAD) docker compose up -d --build
sudo docker compose ps          # web und db "healthy", migrate "exited (0)"
curl -fsS https://portal.haus-meister-helden.de/gesund   # {"status": "ok"}
```
Erstes Admin-Konto anlegen (Befehl laut Agent Kern, z. B. `docker compose exec web python manage.py createsuperuser`). Danach sofort 2FA einrichten.

Ablauf bei jedem `up`:
1. `db` startet und wird `healthy`.
2. `migrate` führt `manage.py migrate` aus und kopiert die statischen Dateien ins Volume `statisch`.
3. `web` startet (gunicorn), Healthcheck `/gesund`.
4. `caddy` startet und holt bzw. erneuert das Zertifikat automatisch.

### 4.2 Update auf eine neue Version
```bash
cd /opt/hh-portal
sudo systemctl start hh-backup.service          # vorher sichern!
sudo GIT_SSH_COMMAND="ssh -i /root/.ssh/github-deploy" git pull --ff-only
cd portal/deploy
sudo PORTAL_VERSION=$(git rev-parse --short HEAD) docker compose up -d --build
sudo docker compose ps && sudo docker compose logs --tail=50 web migrate
```
Ausfallzeit: wenige Sekunden beim Neustart von `web`.

### 4.3 Zurück auf die vorige Version
```bash
cd /opt/hh-portal && sudo git checkout <vorheriger-commit>
cd portal/deploy && sudo PORTAL_VERSION=$(git rev-parse --short HEAD) docker compose up -d --build
```
Hat die neue Version Migrationen ausgeführt, die nicht rückwärts kompatibel sind: Datenbank aus dem Backup vor dem Update wiederherstellen (siehe `wiederherstellung.md`, Abschnitt 4.3).

### 4.4 Lokal ausprobieren (ohne Server)
```bash
cd portal/deploy
cp .env.example .env     # Platzhalter durch Testwerte ersetzen, PORTAL_DOMAIN=localhost,
                         # DJANGO_ALLOWED_HOSTS=localhost, DJANGO_CSRF_TRUSTED_ORIGINS=https://localhost
docker compose up -d --build
curl -k https://localhost/gesund
docker compose down      # mit -v werden auch die Test-Volumes gelöscht
```
Hinter einem TLS-prüfenden Firmen-Proxy kann das CA-Zertifikat als Build-Secret übergeben werden: `docker buildx build --secret id=pip_ca,src=<ca.crt> …`. Es landet nicht im Image.

---

## 5. Backups

| | |
|---|---|
| Was | Datenbank (`pg_dump`, Custom-Format) + Rollen (`pg_dumpall --globals-only`, ohne Passwörter) + Volume `dateien` |
| Wie | `restic`, verschlüsselt (AES-256) und dedupliziert, in das Repository `RESTIC_REPOSITORY` |
| Wohin | Hetzner Storage Box (anderer Standort), z. B. `sftp:uXXXXX@uXXXXX.your-storagebox.de:/./hh-portal` |
| Wann | täglich ca. 02:30 (`hh-backup.timer`) |
| Aufbewahrung | 7 tägliche, 4 wöchentliche, 12 monatliche Stände (`restic forget --prune`) |
| Prüfung | `restic check` nach jedem Backup. Sonntags ca. 05:00 `restore-test.sh`: letztes Backup in eine temporäre Datenbank einspielen, Zeilenanzahlen von 16 wichtigen Tabellen mit den Werten zum Sicherungszeitpunkt vergleichen (gleicher Datenbank-Snapshot), Alter des Backups ≤ 26 h |
| Zusätzlich | Hetzner Server-Backups (ganzer Server, 7 Abbilder) |

Einrichtung (nach Freigabe der Storage Box):
1. In der Storage Box SSH-Zugang aktivieren. Den öffentlichen Schlüssel `/root/.ssh/storagebox.pub` hinterlegen (vorher `ssh-keygen -t ed25519 -N "" -f /root/.ssh/storagebox`).
2. In `/root/.ssh/config` eintragen:
   ```
   Host uXXXXX.your-storagebox.de
     Port 23
     User uXXXXX
     IdentityFile /root/.ssh/storagebox
   ```
3. `RESTIC_REPOSITORY` und `RESTIC_PASSWORD` (`openssl rand -hex 32`) per `sops` in `secrets.enc.yaml` eintragen.
4. **`RESTIC_PASSWORD` zusätzlich in Martins Passwort-Manager ablegen.** Ohne dieses Passwort sind die Backups wertlos.
5. Repository anlegen und den ersten Lauf testen:
   ```bash
   sudo bash portal/deploy/backup/backup.sh --init
   sudo systemctl start hh-backup.service && journalctl -u hh-backup -n 50
   sudo systemctl start hh-restore-test.service && journalctl -u hh-restore-test -n 50
   ```

Hilfreiche Befehle (als root, Variablen aus `/run/hh-portal/portal.env`):
```bash
set -a; . /run/hh-portal/portal.env; set +a
restic snapshots --tag hh-portal
restic stats latest
```

Die Skripte lassen sich auch ohne Docker testen: `HH_BACKUP_DB_URL=postgresql://…` (lokale DB), `HH_DATEIEN_PFAD=<ordner>`, `HH_BACKUP_ARBEIT=<ordner>`, `HH_BACKUP_SPERRE=<datei>`.

---

## 6. Updates

| Was | Wie | Wie oft |
|---|---|---|
| Ubuntu-Sicherheitsupdates | automatisch (`unattended-upgrades`), Neustart 04:15 bei Bedarf | täglich |
| Docker Engine | über apt (mit den OS-Updates) | automatisch/monatlich prüfen |
| Caddy, PostgreSQL (Minor), Python-Basis-Image | Version in `docker-compose.yml` bzw. `Dockerfile` erhöhen → Pull Request → CI grün → Deployment nach Freigabe | monatlich, bei Sicherheitsmeldungen sofort |
| Python-Pakete | `requirements.txt` (fest gepinnt) anheben → CI → Deployment | monatlich, Django-Sicherheitsreleases sofort |
| PostgreSQL Major (z. B. 16 → 17) | **nicht** einfach Tag ändern: Backup, neues Volume, `pg_dump`/`pg_restore`, testen. Eigene Freigabe. | bei Bedarf (16 wird bis Nov. 2028 unterstützt) |

Alle Versionen sind fest gepinnt (`caddy:2.11.9`, `postgres:16.15-trixie`, `python:3.13.18-slim-trixie`). So ändert sich nichts unbemerkt.

---

## 7. Monitoring

Phase 2 nutzt nur kostenlose Bordmittel und keine externen Dienste:

- **Healthchecks:** `docker compose ps` zeigt `healthy`/`unhealthy`. `web` wird über `/gesund` geprüft (inkl. Datenbank), `db` über `pg_isready`. Abgestürzte Container startet `restart: unless-stopped` neu.
- **Backups:** Schlägt ein Lauf fehl, schreibt `hh-alarm@.service` einen Fehler ins Journal: `journalctl -t hh-alarm -p err`. Zusätzlich meldet `restore-test.sh` einen Fehler, wenn das neueste Backup älter als 26 h ist.
- **Protokolle:** `docker compose logs -f web caddy` (rotiert: 5 × 10 MB je Dienst), `journalctl -u hh-backup -u hh-restore-test`.
- **Ressourcen:** Grafiken in der Hetzner Console (CPU, Netz, Platte). Speicherplatz mit `df -h` und `docker system df` prüfen. Limits je Container: db 1 GB, web 768 MB, migrate 512 MB, caddy 256 MB.
- **Zertifikate:** erneuert Caddy automatisch. Hinweise von Let's Encrypt gehen an `ACME_EMAIL`.

Optional (erst nach Freigabe, externer Dienst): ein Uptime-Monitor für `https://portal.haus-meister-helden.de/gesund` und ein „Dead-Man's-Switch“ für Backups. Die Skripte rufen dafür nach Erfolg `HH_MELDE_URL` bzw. `HH_MELDE_URL_RESTORE` auf, bei Fehler dieselbe URL mit `/fail` (Schema wie Healthchecks.io). Leer = aus. Phase 5 kann zusätzlich eine Mail an Martin über IONOS-SMTP senden.

---

## 8. Sicherheits-Checkliste (vor Produktivsetzung, Phase 8)

- [ ] SSH nur mit Schlüssel, Root-Login aus, Hetzner-Firewall aktiv
- [ ] `unattended-upgrades` aktiv, Zeitzone Europe/Berlin
- [ ] `secrets.enc.yaml` verschlüsselt, `.env` ist ein Symlink nach `/run/hh-portal/`, keine Klartext-Secrets auf der Platte (`grep -r DJANGO_SECRET_KEY /opt /root /home` findet nur Platzhalter)
- [ ] age-Notfallschlüssel und `RESTIC_PASSWORD` in Martins Passwort-Manager
- [ ] Backup + Wiederherstellungstest laufen grün, ein vollständiger Wiederherstellungs-Probelauf ist dokumentiert
- [ ] `https://securityheaders.com` bzw. `ssllabs.com` mindestens A
- [ ] AV-Verträge Hetzner (Cloud + Storage Box) abgeschlossen
- [ ] Festplattenverschlüsselung bzw. verschlüsselte Dateiablage entschieden (siehe offene Punkte)
