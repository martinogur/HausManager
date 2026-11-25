# Portal-Server bei Hetzner – vollautomatische Einrichtung

Stand: 25.11.2026 · Variante **ohne SSH und ohne SOPS**: Der Server richtet sich selbst ein, erzeugt seine
Secrets selbst und holt neue Versionen selbst vom Zweig `portal-live`. Verwaltet wird er nur über die
Hetzner-Web-Konsole. (Die SOPS/age-Variante mit SSH in `docs/04-betrieb.md` bleibt als Alternative bestehen.)

| Datei | Zweck |
|---|---|
| `cloud-init.yaml` | wird beim Anlegen als `user_data` übergeben: installiert und startet alles |
| `server_erstellen.py` | legt Firewall + Server über die Hetzner-API an (idempotent, nur Standardbibliothek) |
| `compose.server.yml` | Server-Ergänzung zu `../docker-compose.yml` (Basis bleibt unverändert) |
| `tests/` | Tests: nachgebaute Hetzner-API, cloud-init-Prüfung, Docker-Integrationstest |

## 1. Ablauf

1. **Zweig `portal-live` anlegen** (nur nach Freigabe des Inhabers): Er enthält genau die Version, die
   auf dem Server laufen soll. Der Server klont das öffentliche Repository ohne Zugangsdaten.
2. **Trockenlauf** – zeigt Plan, Servertyp und Monatspreis, ändert nichts:
   ```bash
   python3 portal/deploy/hetzner/server_erstellen.py --trockenlauf
   ```
3. **Anlegen:** `python3 portal/deploy/hetzner/server_erstellen.py`
   * Firewall `hh-portal`: eingehend nur TCP 80, TCP 443, UDP 443 (HTTP/3), ICMP. **Kein SSH.**
   * Server `hh-portal-1`: günstigster verfügbarer x86-Typ mit ≥ 2 vCPU / ≥ 4 GB RAM in Nürnberg (nbg1)
     oder Falkenstein (fsn1), Ubuntu 24.04, Label `app=hh-portal`, Hetzner-Backups an.
   * Ausgabe: IPv4/IPv6. Ein zweiter Aufruf legt nichts doppelt an (prüft nur und korrigiert Firewall-Regeln).
4. **DNS:** A-Record `portal.haus-meister-helden.de` → IPv4 (optional AAAA → IPv6, Präfix mit `::1`).
5. Der Server richtet sich in ca. 5–10 Minuten selbst ein (`/var/log/hh-einrichtung.log`):
   Swap 2 GB, Docker (offizielles Repository, compose-Plugin), ufw (nur 80/443), SSH-Dienst aus,
   automatische Sicherheitsupdates (Neustart bei Bedarf um 04:30), Clone von `portal-live` nach
   `/srv/portal/repo`, `/srv/portal/.env` mit neuen Zufallswerten, `docker compose up -d --build`
   (inkl. migrate-Job), systemd-Timer.
6. Caddy holt das Let's-Encrypt-Zertifikat, sobald der DNS-Eintrag stimmt. Caddy versucht es in größer
   werdenden Abständen erneut; schneller geht es mit `hh-compose restart caddy`.
7. **Admin-Konto anlegen** (Abschnitt 3), dann im Browser anmelden und die Zwei-Faktor-Anmeldung einrichten.

Token: `server_erstellen.py` liest `HCLOUD_TOKEN` (Projekt-Token „Lesen & Schreiben“, Hetzner Console →
Projekt → Sicherheit → API-Tokens). Ohne Variable wird der Platzhalter `proxy-injiziert` gesendet, den der
Sitzungs-Proxy durch den echten Token ersetzt. Der Token wird nie ausgegeben. Bei HTTP 401 erscheint ein
Hinweis, was zu tun ist.

## 2. Kosten (laut API, Stand der Abfrage – der Trockenlauf zeigt die aktuellen Zahlen)

| Posten | ca. €/Monat netto |
|---|---|
| Server (Shared vCPU, 2 vCPU / 4 GB, z. B. CX23 oder CPX22 – Auswahl automatisch nach Preis) | 4–7 |
| Hetzner-Backups (+20 % des Serverpreises, 7 Abbilder) | 1–1,50 |
| Öffentliche IPv4 | ca. 0,50–0,60 |
| Firewall, Let's Encrypt, Docker, Caddy | 0 |
| später: Storage Box BX11 für restic (nach Freigabe) | ca. 4 |
| **Summe** | **ca. 6–9 jetzt, 10–14 mit Storage Box** |

## 3. Hetzner-Web-Konsole und Admin-Konto

1. Hetzner Console → Server `hh-portal-1` → **Konsole** (Symbol `>_`). Benutzer `root`.
2. Root-Passwort: Weil kein SSH-Key hinterlegt ist, schickt Hetzner es per E-Mail. Kommt keine E-Mail:
   Server → **Rescue → Root-Passwort zurücksetzen** (zeigt ein neues Passwort einmalig an).
   Beim ersten Anmelden verlangt Ubuntu ein neues Passwort – im Passwort-Manager speichern.
3. Admin-Konto anlegen:
   ```
   hh-admin-anlegen
   ```
   Das Skript macht zuerst einen **Tastaturtest** (`yz@-_` eintippen). Die Web-Konsole überträgt Tasten
   je nach Browser-Tastatur manchmal falsch (z. B. y/z vertauscht). Stimmt der Test nicht, bricht das Skript
   ab, bevor ein Passwort gesetzt wird, das im Browser später anders aussähe. Abhilfe: Tastaturbelegung des
   Servers mit `dpkg-reconfigure keyboard-configuration` anpassen (oder Browser-Tastatur auf US stellen) und erneut versuchen.
   Danach fragt es E-Mail und Name, zeigt beides zur Kontrolle und fragt das Passwort (mind. 12 Zeichen,
   zweimal, unsichtbar). Intern: `docker compose exec web python manage.py admin_anlegen`.

## 4. Status

```
hh-status
```
zeigt Container (web/db „healthy“, migrate „exited 0“), aktive Version und Stand von `portal-live`,
letztes Update (+ Ende von `/var/log/hh-update.log`), Timer, Zertifikat (Aussteller, Ablauf), `/gesund`,
letzte Sicherungen, Plattenplatz, RAM/Swap.

Weitere Befehle: `hh-compose ps`, `hh-compose logs --tail=100 web`, `journalctl -u hh-update`,
`cat /var/log/hh-einrichtung.log`.

## 5. Updates über `portal-live`

* `hh-update.timer` prüft alle 15 Minuten `git fetch origin portal-live`.
* Neuer Commit → **Sicherung** (`hh-backup vor-update`) → `git checkout` → `docker compose build --pull`
  → `up -d` (der migrate-Job läuft vor dem neuen web-Container) → wartet, bis `web` gesund ist.
* Schlägt Build, Migration oder Gesundheitsprüfung fehl, läuft die bisherige Version weiter, das Repo wird
  auf sie zurückgesetzt, `hh-status` zeigt den Fehler, und dieser Commit wird übersprungen, bis ein neuer
  kommt (sofort erneut versuchen: `hh-update --jetzt`).
* Das Image-Tag ist der Commit (`hh-portal-web:<12 Zeichen>`); die letzten 3 Images bleiben für schnelles
  Zurückrollen liegen.
* Wer `portal-live` aktualisiert, entscheidet damit über den Live-Stand: **nur nach Freigabe des Inhabers**.
* Die Skripte unter `/usr/local/bin/hh-*` stammen aus `cloud-init.yaml` und werden durch Updates **nicht**
  ersetzt. Ändern sie sich, in der Web-Konsole neu einspielen (oder Server neu aufsetzen).

## 6. Zurückrollen

* **Normalfall:** `portal-live` auf den vorigen guten Commit setzen, z. B.
  `git push --force origin <guter-commit>:portal-live`. Der Server rollt diesen Stand beim nächsten
  Timer-Lauf aus (vorher wieder eine Sicherung). Sofort: in der Konsole `hh-update --jetzt`.
* **Migrationen** werden dabei nicht rückgängig gemacht. War die neue Version mit einer nicht
  rückwärtskompatiblen Migration aktiv, zusätzlich die Datenbank aus der Sicherung vor dem Update
  wiederherstellen:
  ```bash
  hh-compose stop web caddy
  ls -lt /srv/portal/backups/          # hh-<datum>-vor-update.dump wählen
  hh-compose exec -T db pg_restore -U hh -d hh --clean --if-exists < /srv/portal/backups/hh-…-vor-update.dump
  hh-compose up -d
  ```
  Ausführlich (Rollen, Prüfung der Zeilenzahlen): `docs/wiederherstellung.md`.
* **Ganzer Server:** Hetzner Console → Backups (tägliche Abbilder, 7 Stück) → wiederherstellen.

## 7. Sicherungen

* `hh-backup.timer` täglich ca. 02:30 Uhr: `pg_dump` (Custom-Format, geprüft mit `pg_restore --list`)
  und ein Archiv der hochgeladenen Dateien nach `/srv/portal/backups` (Rechte 700), **14 Tage** Aufbewahrung.
  Hand-Sicherung: `hh-backup hand`. Protokoll: `/var/log/hh-backup.log`.
* Diese Sicherungen liegen auf derselben Platte; gegen Serververlust schützen die Hetzner-Backups.
* **Später (nach Freigabe):** restic → Storage Box mit `../backup/backup.sh` (liest `portal/deploy/.env`,
  das auf dem Server ein Symlink auf `/srv/portal/.env` ist). `RESTIC_PASSWORD` ist schon erzeugt;
  **vor dem ersten restic-Backup im Passwort-Manager notieren**, sonst sind die externen Sicherungen nach
  einem Serververlust nicht lesbar. `RESTIC_REPOSITORY` in `/srv/portal/.env` eintragen.

## 8. Technische Details

* Pfade: `/srv/portal/repo` (Clone), `/srv/portal/.env` (600), `/srv/portal/backups`, `/srv/portal/stand`
  (`aktiv`, `letztes-update`, `fehlgeschlagen`), Einstellungen ohne Secrets in `/etc/hh-portal/einstellungen`.
* `hh-compose` = `docker compose --project-directory /srv/portal/repo/portal/deploy --env-file /srv/portal/.env
  -f docker-compose.yml -f hetzner/compose.server.yml`, `PORTAL_VERSION` = aktueller Commit.
* **Warum `compose.server.yml`?** `docker-compose.yml` ist auf die SOPS-Variante ausgelegt
  (`.env` als Symlink in den Arbeitsspeicher). Hier liegt die Umgebung als Datei vom Server selbst; die
  Basis bleibt unverändert, die Override-Datei ergänzt nur Server-Besonderheiten (`ACME_CA` an Caddy
  durchreichen, Versions-Label). Fehlt sie im ausgerollten Stand, läuft die Basis allein.
* Secrets: `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD` (auch in `DATABASE_URL`), `RESTIC_PASSWORD` entstehen
  per `openssl rand -hex` beim ersten Start; eine vorhandene `.env` wird nie überschrieben.
* `systemd`: `hh-portal.service` (Start beim Booten), `hh-update.timer` (5 min nach Boot, dann 15 min nach
  jedem Lauf), `hh-backup.timer` (täglich, `Persistent=true`). Diese Units ersetzen auf dem Hetzner-Server
  die gleichnamigen SOPS-Units aus `../backup/systemd/` (dort nicht zusätzlich installieren).
* Docker veröffentlicht nur 80/443 (Caddy); Datenbank und Anwendung hängen im internen Netz.
  Hinweis: Docker-Ports umgehen ufw – maßgeblich ist die Hetzner-Firewall, ufw ist die zweite Linie.
* Testumgebung: `HH_DOMAIN`, `HH_BASIS`, `HH_LOG_DIR`, `HH_REPO_URL`, `HH_BRANCH`, `HH_COMPOSE_EXTRA`,
  `HH_NUR_PORTAL=1`, `HH_OHNE_SYSTEMD=1`, `HH_EINSTELLUNGEN` (siehe `tests/bootstrap-docker-test.sh`).

## 9. Löschen

```bash
python3 portal/deploy/hetzner/server_erstellen.py --loeschen               # zeigt nur an
python3 portal/deploy/hetzner/server_erstellen.py --loeschen --ja-wirklich # löscht Server + Firewall
```
Vernichtet den Server samt Daten und Hetzner-Backups. Nur auf ausdrücklichen Wunsch des Inhabers.

## 10. Tests

```bash
python3 -m unittest discover -s portal/deploy/hetzner/tests -v       # API-Fake, cloud-init-Schema, Skripte
bash portal/deploy/hetzner/tests/bootstrap-docker-test.sh           # mit Docker, Domain localhost, Ports 80/443
#   hinter einem TLS-Proxy: HH_TEST_CA=/pfad/ca.crt bash …
```
