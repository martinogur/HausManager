# Notfallplan: Wiederherstellung des Verwaltungsportals

Stand: 25.11.2026 · Phase 2 (Entwurf, gilt ab Produktivbetrieb) · Ablage: zusätzlich ausgedruckt im Büro-Ordner „Notfall“

## 1. Ziele

| Kennzahl | Ziel | Wie erreicht |
|---|---|---|
| **RPO**: maximaler Datenverlust | **24 Stunden** | tägliches Backup um ca. 02:30 nach restic (Storage Box, anderer Standort) + Hetzner Server-Backups |
| **RTO**: maximale Ausfallzeit | **4 Stunden** | Schritt-für-Schritt-Anleitung unten, wöchentlicher automatischer Wiederherstellungstest, Probelauf jedes Quartal |

---

## 2. Wer tut was

| Rolle | Person | Aufgaben |
|---|---|---|
| **Entscheidung & Zugänge** | Martin Ogur (Inhaber) | Notfall ausrufen, Hetzner-Console-Zugang, neuen Server freigeben, age-Notfallschlüssel und `RESTIC_PASSWORD` aus dem Passwort-Manager bereitstellen, Kunden und Mitarbeiter informieren, ggf. Datenschutz-Meldung (Abschnitt 6) |
| **Technische Durchführung** | Techniker:in bzw. eine Claude-Code-Sitzung unter Martins Aufsicht | Schritte in Abschnitt 4 ausführen, Ergebnis prüfen, Protokoll schreiben |
| **Büro** | Büro-Mitarbeiter:in | Während des Ausfalls Termine und Einsätze auf Papier bzw. im Kalender notieren und später nachtragen |

Martin gibt keine Schlüssel per Chat oder E-Mail weiter. Er gibt sie selbst auf dem Server ein bzw. fügt sie dort ein.

### Notfall-Karte (im Passwort-Manager, Ordner „hh-portal Notfall“)
- Hetzner-Console-Zugang (inkl. 2FA)
- age-Notfallschlüssel (`AGE-SECRET-KEY-1…`)
- `RESTIC_PASSWORD` und Storage-Box-Zugang (Benutzer `uXXXXX`, SSH-Schlüssel oder Passwort)
- SSH-Schlüssel für den Server (`~/.ssh/hh-portal`)
- GitHub-Zugang (für den Deploy-Key des neuen Servers)
- IONOS-Zugang (DNS für `portal.haus-meister-helden.de`)

---

## 3. Welcher Fall liegt vor?

| Fall | Beispiel | Vorgehen |
|---|---|---|
| A: Anwendung hängt | Seite lädt nicht, Server erreichbar | `docker compose ps`, `docker compose logs web`, `docker compose restart web` (5 Min.) |
| B: fehlerhaftes Update | nach Deployment Fehler | auf vorige Version zurück: `04-betrieb.md`, Abschnitt 4.3 (15–30 Min.) |
| C: Daten versehentlich gelöscht/verfälscht | falscher Massen-Import | Datenbank aus Backup auf demselben Server: **Abschnitt 4.3** (30–60 Min.). Alternativ einzelne Datensätze aus dem `audit_log` rekonstruieren. |
| D: Server defekt oder gelöscht | Hetzner-Störung, versehentlich gelöscht | **neuer Server: Abschnitt 4** (2–4 h). Schneller: Hetzner Server-Backup wiederherstellen, falls vorhanden und aktuell |
| E: Server kompromittiert | fremde Prozesse, Ransomware | Server **vom Netz** (Hetzner-Firewall alles sperren), **nicht** reparieren. Neuer Server nach Abschnitt 4, **alle Secrets neu erzeugen** (Abschnitt 5), Datenschutz-Meldung prüfen |

---

## 4. Wiederherstellung auf einem neuen Server (Fall D/E)

Geplante Zeit: ca. 2–3 Stunden, mit Puffer innerhalb von 4 h.

| Schritt | Was | Wer | ca. Zeit |
|---|---|---|---|
| 0 | Notfall ausrufen, Büro informieren, Startzeit notieren | Martin | 5 Min. |
| 1 | Neuen Server anlegen, Firewall, SSH, Updates, Docker (`04-betrieb.md`, 3.1–3.5) | Technik | 45 Min. |
| 2 | Code holen (3.6), sops installieren | Technik | 15 Min. |
| 3 | Secrets wiederherstellen (4.1) | Martin + Technik | 15 Min. |
| 4 | Backup zurückholen, Datenbank und Dateien einspielen (4.2) | Technik | 30 Min. |
| 5 | Portal starten, DNS umstellen, prüfen (4.4) | Technik | 30 Min. |
| 6 | Freigabe des Betriebs, Kunden/Mitarbeiter informieren | Martin | 10 Min. |

### 4.1 Secrets auf dem neuen Server
Der alte Server-Schlüssel ist verloren. Die Secrets werden mit **Martins Notfallschlüssel** entschlüsselt, danach bekommt der neue Server einen eigenen Schlüssel:
```bash
sudo install -d -m 700 /etc/hh-portal
sudo age-keygen -o /etc/hh-portal/age.key && sudo chmod 600 /etc/hh-portal/age.key
sudo age-keygen -y /etc/hh-portal/age.key          # neuer Public Key

# Martin fügt seinen Notfallschlüssel vorübergehend ein (nur im Arbeitsspeicher):
sudo install -m 600 /dev/null /run/hh-notfall.key && sudo nano /run/hh-notfall.key
cd /opt/hh-portal/portal/deploy
# in .sops.yaml den alten Server-Key durch den neuen ersetzen, dann:
sudo SOPS_AGE_KEY_FILE=/run/hh-notfall.key sops updatekeys -y secrets.enc.yaml
sudo shred -u /run/hh-notfall.key
sudo bash secrets-entschluesseln.sh                 # → /run/hh-portal/portal.env + .env-Symlink
```
Die geänderte `.sops.yaml` und `secrets.enc.yaml` committen und pushen (über den Arbeitsrechner, nicht mit dem lesenden Deploy-Key).

**Fall E (kompromittiert):** Vor dem Start alle Werte mit `sops secrets.enc.yaml` neu setzen: `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD` + `DATABASE_URL`, später auch API-Tokens. Das alte `RESTIC_PASSWORD` bleibt, bis das Backup eingespielt ist. Danach `restic key add` / `restic key remove` ausführen.

### 4.2 Backup zurückholen
```bash
sudo -i
set -a; . /run/hh-portal/portal.env; set +a       # RESTIC_REPOSITORY, RESTIC_PASSWORD
# Storage-Box-SSH-Zugang einrichten (04-betrieb.md, Abschnitt 5, Schritte 1–2)
restic snapshots --tag hh-portal                  # gewünschten Stand wählen (Standard: latest)
restic restore latest --tag hh-portal --target /var/tmp/wiederherstellung
find /var/tmp/wiederherstellung -name hh.dump     # …/var/backups/hh-portal/db/hh.dump
```

Datenbank einspielen (frische, leere Datenbank `hh` des neuen Containers):
```bash
cd /opt/hh-portal/portal/deploy
docker compose up -d db
until docker compose exec -T db pg_isready -U hh -d hh; do sleep 2; done
W=/var/tmp/wiederherstellung
docker compose exec -T db pg_restore -U hh -d hh --no-owner --exit-on-error \
  < $W/var/backups/hh-portal/db/hh.dump
```

Dateien einspielen (Volume `dateien`):
```bash
docker compose run --rm --no-deps -T --entrypoint sh \
  -v $W/var/lib/docker/volumes/hh-portal_dateien/_data:/quelle:ro \
  web -c 'cp -a /quelle/. /srv/portal/daten/'
```
Hinweis: Lag das Volume auf dem alten Server unter einem anderen Pfad, findet ihn `find $W -maxdepth 6 -type d -name _data`.

### 4.3 Nur die Datenbank zurücksetzen (Fall C, gleicher Server)
```bash
cd /opt/hh-portal/portal/deploy
sudo systemctl start hh-backup.service              # aktuellen (fehlerhaften) Stand trotzdem sichern
sudo docker compose stop web caddy                  # Portal kurz offline
# Dump wie in 4.2 mit restic holen (ggf. älteren Snapshot statt latest)
sudo docker compose exec -T db psql -U hh -d postgres -c "DROP DATABASE hh WITH (FORCE)" -c "CREATE DATABASE hh"
sudo docker compose exec -T db pg_restore -U hh -d hh --no-owner --exit-on-error < <pfad>/hh.dump
sudo docker compose up -d
```
Vorsichtiger ist es, den Dump zuerst in eine zweite Datenbank (`hh_alt`) einzuspielen und nur die betroffenen Datensätze zu übernehmen.

### 4.4 Starten und prüfen
```bash
cd /opt/hh-portal/portal/deploy
sudo PORTAL_VERSION=$(git rev-parse --short HEAD) docker compose up -d --build
sudo docker compose ps                    # migrate: "No migrations to apply." bzw. exited (0)
```
- DNS bei IONOS: `A`/`AAAA` von `portal.haus-meister-helden.de` auf die neue IP setzen. Caddy holt das Zertifikat, sobald der Name auf den Server zeigt (bei TTL 300 s nach wenigen Minuten).
- Prüfen:
  - `curl -fsS https://portal.haus-meister-helden.de/gesund` liefert `{"status": "ok"}`
  - Anmeldung mit 2FA funktioniert
  - Kunden- und Auftragszahlen im Dashboard sind plausibel und passen zu `zeilen.txt` aus dem Backup
  - ein hochgeladenes Foto lässt sich öffnen
  - der letzte Eintrag im Audit-Log liegt vor dem Backup-Zeitpunkt
- systemd-Dienste und Timer installieren (`04-betrieb.md`, 3.8). Ein Backup sofort von Hand starten.
- Alten Server endgültig löschen, sobald alles läuft. Im Fall E erst nach Sicherung der Spuren, falls eine Anzeige erstattet wird.
- Wiederherstellungsordner löschen: `rm -rf /var/tmp/wiederherstellung`.

---

## 5. Secrets nach einem Vorfall erneuern

| Secret | Erneuern | Wirkung |
|---|---|---|
| `DJANGO_SECRET_KEY` | `openssl rand -hex 50` | alle Sitzungen ungültig, Nutzer melden sich neu an |
| `POSTGRES_PASSWORD` + `DATABASE_URL` | im laufenden Container `ALTER ROLE hh PASSWORD '…'`, dann Secrets anpassen | – |
| Benutzerpasswörter/2FA | Admin erzwingt Zurücksetzen | Nutzer richten neu ein |
| `RESTIC_PASSWORD` | `restic key add` (neu) → `restic key remove <alt>` | Backups bleiben lesbar |
| age-Schlüssel | neuen Key erzeugen, `.sops.yaml` anpassen, `sops updatekeys` | alter Key wertlos |
| API-Tokens (ab Phase 5) | beim jeweiligen Anbieter widerrufen und neu erzeugen | – |

---

## 6. Datenschutz

Gehen bei einem Vorfall personenbezogene Daten verloren oder gelangen sie in fremde Hände, gilt Art. 33 DSGVO: Meldung an die Aufsichtsbehörde (für NRW: LDI NRW) **innerhalb von 72 Stunden**, außer das Risiko für die Betroffenen ist voraussichtlich gering. Bei hohem Risiko müssen nach Art. 34 auch die Betroffenen informiert werden. Martin entscheidet und dokumentiert das, auch wenn keine Meldung nötig ist.

---

## 7. Üben und Prüfen

| Was | Wann | Wer |
|---|---|---|
| Automatischer Wiederherstellungstest (`restore-test.sh`) | jeden Sonntag | automatisch; Fehler stehen im Journal (`journalctl -t hh-alarm`) |
| Kontrolle: Laufen Backups und Tests? (`systemctl list-timers 'hh-*'`, `restic snapshots`) | monatlich | Technik |
| Vollständiger Probelauf von Abschnitt 4 auf einem Wegwerf-Server (Kosten wenige Cent je Stunde, nach Freigabe) | vierteljährlich und vor Produktivsetzung | Technik + Martin |
| Notfall-Karte im Passwort-Manager aktuell? | halbjährlich | Martin |

Jeder echte Vorfall und jeder Probelauf bekommt ein kurzes Protokoll in `berichte/`: Datum, Ursache, Dauer, Datenverlust, was verbessert wird.
