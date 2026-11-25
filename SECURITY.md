# Sicherheit, Datenschutz und Kontrolle

Ergänzt `portal/docs/01-architektur.md` (Abschnitt 6) und `portal/docs/04-betrieb.md` (Betrieb, Backups, Notfall).

## 1. Rollen und Rechte

| Rolle | Darf | Darf nicht |
|---|---|---|
| `admin` (Geschäftsführer) | alles, Agenten/Automatisierungen ein- und ausschalten, Stundenlöhne sehen | – |
| `buero` | Steuerung, Stammdaten, **Freigaben entscheiden**, Agentenaufgaben von Hand starten | Benutzerverwaltung, Agenten/Automatisierungen schalten |
| `mitarbeiter` | nur **eigene** Einsätze: Objektadresse, Zugangshinweis, Zeit Start/Stopp, Fotos, Bericht, „erledigt“ | Kennzahlen, Kunden, Preise, Löhne, fremde Einsätze/Fotos (404), Steuerungsseiten (403) |

* **Pflicht-2FA (TOTP)** für admin und büro, Argon2-Passwörter, Sperre nach 5 Fehlversuchen, Sitzung 8 h.
* Rechte prüft jede Ansicht serverseitig (`konten/rechte.py`, `Einsatz.objects.fuer_benutzer`). Tests decken 403/404-Fälle ab.
* **Freigaben entscheiden nur Menschen.** Die Datenbank verlangt `entschieden_von` und `entschieden_am`.

## 2. Keine Aktion nach außen ohne Freigabe (technisch erzwungen)

| Aktion | Sicherung |
|---|---|
| E-Mail senden | DB: Status `freigegeben`/`gesendet` nur mit Freigabe durch eine Person; SMTP-Job sendet nur `freigegeben` |
| Angebot versenden | DB: Status ≠ Entwurf nur mit `freigegeben_am` |
| Akquise-Kontakt | DB: Agent darf keinen ausgehenden Kontakt ohne **erteilte** Freigabe protokollieren; keine Werbe-E-Mail ohne Einwilligung/Einladung; kein Kontakt nach Widerspruch |
| Social-Media-Beitrag | DB: „veröffentlicht“ nur mit Freigabe |
| Rechnung | Nur Entwurf in Lexware (`finalize` wird nie gesetzt). Festschreiben macht der Inhaber in Lexware. |
| Zahlungen, Verträge, Einstellungen | Kein Agent hat dafür eine Funktion |

## 3. Secrets

* **Keine Zugangsdaten im Code oder im Repository.** Alle Werte kommen aus Umgebungsvariablen.
* Server: `secrets.enc.yaml` (SOPS + age), entschlüsselt nur in den Arbeitsspeicher (`/run/hh-portal/portal.env`).
* Jeder Dienst bekommt nur seine Variablen. **Nur `agenten`** kennt die Schlüssel für Claude, IONOS, HubSpot und Lexware und hat als einziger Dienst Internetzugang (Netz `ausgehend`). `web` bleibt im internen Netz.
* Make-Webhook: Token im Header `X-HH-Token`, Vergleich in konstanter Zeit, ohne Token ist der Webhook aus (404).
* Neue Schlüssel bitte nie im Chat weitergeben. Eintrag per `sops secrets.enc.yaml` auf dem Server bzw. über die sichere Eingabe.

## 4. Protokollierung

| Protokoll | Inhalt |
|---|---|
| `audit_log` | Jede Änderung an Fachdaten mit Benutzer, alt/neu (ohne Passwort-Hashes) – nur anfügbar |
| `agenten_protokoll` | Jeder Agentenschritt – nur anfügbar |
| `ki_aufrufe` | Zweck, Modell, Tokens, Kosten, Fehler je KI-Aufruf |
| `sync_protokoll` | Jeder Aufruf externer Systeme (HubSpot, Lexware, IONOS, Make) mit Status |
| `automatisierungs_laeufe` | Jeder Automatisierungslauf |

## 5. Kosten- und Lastkontrolle

* **KI:** Tagesbudget je Agent (`agenten.tagesbudget_cent`) und gesamt (`ki_tagesbudget_gesamt_cent`, Standard 2 €/Tag),
  Hauptschalter `ki_aktiv`, Schritt- und Zeitgrenzen, Warnung ab 80 %. Zusätzlich ein Ausgabenlimit im Anthropic-Konto setzen.
* **Externe APIs:** Lexware max. 2 Anfragen/s (Drosselung im Code), IMAP-Abruf alle 3 min, Versand max. 20 Mails je Lauf.
* **Webhook:** max. 20 KB je Anfrage, idempotent über `referenz`. *Offen:* Rate-Limit am Reverse-Proxy (Caddy) für `/api/`.
* **Anmeldung:** Sperre nach Fehlversuchen (bestehend).

## 6. Datenschutz (DSGVO)

| Thema | Umsetzung |
|---|---|
| Datenminimierung | Leads nur mit öffentlichen Geschäftsdaten + **Pflicht-Quelle**; an die KI nur der nötige Auszug |
| Werbung | § 7 UWG in DB-Regeln; Widerspruch sperrt sofort (Art. 21 DSGVO); jeder Brief mit Widerspruchshinweis |
| Bewerber | Neutrale Zusammenfassung ohne Bewertung und ohne AGG-Merkmale; Löschfrist 6 Monate automatisch |
| Beschäftigte | Keine GPS-Ortung; **Foto-Metadaten (EXIF/GPS) werden beim Hochladen entfernt**; Fotos nur über geprüfte Ansicht abrufbar |
| Schlüssel/Codes | Werden nicht im Portal gespeichert (nur Zugangshinweise) |
| Auftragsverarbeitung | AV-Verträge nötig mit: Hetzner, IONOS, Anthropic, HubSpot, Lexware, Make (und Craftnote solange genutzt) |
| Verzeichnis der Verarbeitungstätigkeiten | *Offen* – Vorlage in Phase 8 (siehe TASKS.md) |

### Lösch- und Aufbewahrungsregeln

| Daten | Frist | Umsetzung |
|---|---|---|
| Bewerbungen + Unterlagen | 6 Monate nach Eingang (AGG) | `bewerbungen.loeschen_ab` automatisch; *Löschjob offen* |
| Arbeitszeitnachweise | mind. 2 Jahre (MiLoG § 17) | keine automatische Löschung |
| Rechnungen | 10 Jahre (§ 147 AO) | führend in Lexware |
| Leads ohne Kontakt/Interesse | 24 Monate nach letztem Kontakt (Vorschlag) | *Löschjob offen* |
| Widersprüche | dauerhaft (Sperrvermerk, nur Firma + Datum) | Status `gesperrt` |
| Agenten-/KI-Protokolle | 12 Monate (Vorschlag) | *Löschjob offen* |

## 7. Backups und Wiederherstellung

Nächtlich `pg_dump` + Dateien mit restic (verschlüsselt) auf eine Hetzner Storage Box, Aufbewahrung 7/4/12, wöchentlicher
automatischer Restore-Test (`portal/deploy/backup/`). Fotos liegen im Volume `dateien` und sind im Backup enthalten.
Ziel: höchstens 24 h Datenverlust, Wiederanlauf in unter 4 h (`portal/docs/wiederherstellung.md`).

## 8. Transport und Härtung

HTTPS (Caddy, HSTS), Sicherheits-Header und Content-Security-Policy ohne Inline-Skripte, CSRF überall (Webhook mit Token
statt CSRF), Container ohne Root und schreibgeschützt, Datenbank nur intern erreichbar, Firewall nur 80/443.
