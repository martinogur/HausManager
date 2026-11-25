# Datenbankschema

PostgreSQL 16, Schema `hh`. Quellen:
* `portal/db/schema.sql`: Grundschema mit 28 Tabellen (Phase 1, Details in `portal/docs/02-datenmodell.md`)
* `portal/db/erweiterungen/0003_betriebssystem.sql`: Betriebssystem mit 11 Tabellen und 3 Sichten (diese Stufe)

Migrationen lesen diese Dateien zur Laufzeit (`kern.0001_schema`, `kern.0003_betriebssystem`). Die SQL-Dateien sind die
einzige Quelle. Tests: `bash portal/db/tests/run.sh` (58 Regeln), `test_schema_abgleich` (Modelle = Tabellen).

Grundsätze: UUID-Schlüssel + lesbare Nummern · Geld in Cent · Dubletten per eindeutigem Index · Audit-Trigger auf
allen Fachtabellen · Regeln in der Datenbank, nicht nur im Code.

## 1. Grundschema (Auszug)

| Bereich | Tabellen |
|---|---|
| Benutzer | `benutzer` (Rollen admin/buero/mitarbeiter) |
| Stammdaten | `kunden`, `ansprechpartner` (E-Mail-Einwilligung mit Nachweis), `objekte`, `leistungen`, `leistungsvereinbarungen` |
| Personal | `mitarbeiter`, `qualifikationen`, `mitarbeiter_qualifikationen`, `verfuegbarkeiten`, `abwesenheiten`, `stellen`, `bewerbungen` (Löschfrist 6 Monate) |
| Vertrieb/Ausführung | `anfragen`, `angebote` + `angebotspositionen` (Summe per Trigger, Versand nur mit Freigabe), `auftraege`, `einsaetze`, `einsatz_mitarbeiter` (keine Doppelbelegung), `arbeitszeiten` (keine Überlappung) |
| Dokumente | `dokumente` (SHA-256 gegen Dubletten), `fotos` (vorher/nachher/schaden …) |
| Abrechnung | `rechnungen` (Spiegel Lexware, eine je Auftrag) |
| Kommunikation | `email_protokolle` (Message-ID eindeutig, Versand nur mit Freigabe) |
| Protokolle | `ki_aufrufe`, `sync_protokoll`, `audit_log` |

## 2. Erweiterung 0003 „Betriebssystem“

### Aufträge (erweitert)
Neue Spalten: `prioritaet` (niedrig/normal/hoch/dringend), `geschaetzte_minuten`, `materialkosten_cent`,
`verkaufspreis_netto_cent`, `bemerkungen`. Neuer Status `zu_pruefen`.

| Status (DB) | Anzeige |
|---|---|
| `anfrage` | Neu |
| `zu_pruefen` | Zu prüfen |
| `angebot` | Angebot erforderlich |
| `bestaetigt` | Freigegeben |
| `geplant` | Geplant |
| `in_arbeit` | In Bearbeitung |
| `erledigt` | Erledigt |
| `abgerechnet` | Abgerechnet (nur mit Rechnung) |
| `storniert` | Storniert |

**Trigger `auftraege_statuswechsel`** erlaubt nur fachlich sinnvolle Wechsel. Beispiele: kein Sprung von „Neu“ nach
„Erledigt“, „Abgerechnet“ nur mit nicht stornierter Rechnung, „Abgerechnet“ ist Endstatus. Python-Spiegel:
`auftraege/status.py`. Ein Test prüft, dass beide übereinstimmen.

**Tatsächliche Arbeitszeit, Personalkosten, Deckungsbeitrag:** Sicht `v_auftrag_wirtschaftlichkeit`
(Arbeitszeiten × Stundenlohn × (1 + Lohnnebenkosten), bei Personen ohne Stundenlohn ein kalkulatorischer Satz).

### Neue Tabellen

| Tabelle | Zweck | Regeln in der Datenbank |
|---|---|---|
| `firmenparameter` | Einstellbare Werte: Einsatzgebiet (Gütersloh, 30 km), Lohnnebenkosten 32,8 %, kalk. Stundensatz, Ziel-DB 30 %, KI-Tagesbudget, KI-Hauptschalter | Audit |
| `leads` | Akquise-Pipeline (neu → qualifiziert → Kontakt geplant → kontaktiert → im Gespräch → Angebot → gewonnen/verloren/gesperrt), Score, Priorität A/B/C, Begründung, Wiedervorlage | **Quelle Pflicht** (DSGVO); Dublette Firma+PLZ; Einwilligung nur mit Nachweis; Widerspruch ⇒ Status gesperrt; gewonnen ⇒ Kunde |
| `lead_kontakte` | Kontaktprotokoll | **Keine Werbe-E-Mail ohne Einwilligung oder Einladung**; **kein Kontakt nach Widerspruch**; **Agenten nur mit erteilter Freigabe** |
| `agenten` | Register: aktiv, Modell, Tagesbudget, max. Schritte/Laufzeit/Versuche | Code-Format |
| `agenten_auftraege` | Warteschlange: Status, Priorität, Eingabe/Ergebnis, Versuche, Sperre (Lease), Kosten | **Tiefe ≤ 3**, **keine gleiche Agent+Aufgabe in einer Kette**, **≤ 20 Aufträge je Kette**, Versuche ≤ Maximum, Abschluss nur mit Endzeit |
| `agenten_protokoll` | Jeder Schritt (Start, KI-Aufruf, Delegation, Freigabe, Ergebnis, Fehler) | **Nur anfügen** |
| `freigaben` | Warteschlange für menschliche Entscheidungen | **Entscheidung nur mit Person und Zeitpunkt**; nur eine offene Freigabe je Bezug |
| `ereignisse` | Outbox: `anfrage.neu`, `email.eingang`, `bewerbung.neu`, `lead.neu`, `auftrag.status`, `einsatz.erledigt`, `angebot.status`, `rechnung.status`, `freigabe.entschieden` | Entstehen **per Trigger** auf den Fachtabellen |
| `automatisierungen` | Register mit Auslöser, aktiv, letzter Lauf/Erfolg, Fehler in Folge | Audit |
| `automatisierungs_laeufe` | Jeder Lauf mit Ergebnis/Fehler | Je Automatisierung + Ereignis höchstens **ein** erfolgreicher Lauf |
| `social_beitraege` | Redaktionskalender (Instagram, Facebook, Google) | **Veröffentlicht nur mit Freigabe**; ein Beitrag je Slot |

Außerdem: `ki_aufrufe` hat neu `agent` und `agenten_auftrag_id` (Budget je Agent und Tag).

### Sichten
* `v_auftrag_wirtschaftlichkeit`: Ist-Minuten, Personalkosten, Deckungsbeitrag (absolut und in %)
* `v_wiederkehrende_umsaetze`: Monatsumsatz aus gültigen Leistungsvereinbarungen (wöchentlich × 52/12, 14-täglich × 26/12, saisonal ÷ 12)
* `v_ki_kosten_tag`: Aufrufe, Tokens, Kosten und Fehler je Tag und Agent

## 3. Änderungen am Schema

Neue Änderungen kommen als weitere Datei `erweiterungen/00NN_*.sql` mit Rückweg-Datei, plus Migration in `kern`,
plus SQL-Tests in `portal/db/tests/test_*.sql`. Bereits ausgerollte Dateien werden nicht mehr verändert.
Ausnahme bis zur Produktivsetzung: 0003 ist noch nirgends produktiv.
