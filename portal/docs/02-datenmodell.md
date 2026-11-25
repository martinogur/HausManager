# Datenmodell (Übersicht)

Verbindliche Definition: [`portal/db/schema.sql`](../db/schema.sql) · Tests: `bash portal/db/tests/run.sh`

```mermaid
erDiagram
  KUNDEN ||--o{ ANSPRECHPARTNER : hat
  KUNDEN ||--o{ OBJEKTE : besitzt
  KUNDEN ||--o{ ANFRAGEN : stellt
  KUNDEN ||--o{ ANGEBOTE : erhaelt
  KUNDEN ||--o{ AUFTRAEGE : erteilt
  KUNDEN ||--o{ RECHNUNGEN : bekommt
  OBJEKTE ||--o{ LEISTUNGSVEREINBARUNGEN : "vereinbart (wiederkehrend)"
  LEISTUNGEN ||--o{ LEISTUNGSVEREINBARUNGEN : "aus Katalog"
  LEISTUNGEN ||--o{ ANGEBOTSPOSITIONEN : "aus Katalog"
  ANGEBOTE ||--|{ ANGEBOTSPOSITIONEN : enthaelt
  ANGEBOTE |o--o| AUFTRAEGE : "wird zu"
  OBJEKTE ||--o{ AUFTRAEGE : "betrifft (muss zum Kunden gehoeren)"
  AUFTRAEGE ||--o{ EINSAETZE : "geplant als"
  LEISTUNGSVEREINBARUNGEN ||--o{ EINSAETZE : "erzeugt automatisch"
  EINSAETZE ||--o{ EINSATZ_MITARBEITER : "zugewiesen"
  MITARBEITER ||--o{ EINSATZ_MITARBEITER : "arbeitet in"
  MITARBEITER ||--o{ ARBEITSZEITEN : bucht
  EINSAETZE ||--o{ ARBEITSZEITEN : "fuer"
  EINSAETZE ||--o{ FOTOS : dokumentiert
  DOKUMENTE ||--o| FOTOS : "Datei"
  MITARBEITER ||--o{ MITARBEITER_QUALIFIKATIONEN : hat
  MITARBEITER ||--o{ VERFUEGBARKEITEN : hat
  MITARBEITER ||--o{ ABWESENHEITEN : hat
  BENUTZER |o--o| MITARBEITER : "Login"
  STELLEN ||--o{ BEWERBUNGEN : erhaelt
  AUFTRAEGE ||--o| RECHNUNGEN : "abgerechnet (max. 1)"
  EMAIL_PROTOKOLLE }o--o| KUNDEN : "zugeordnet"
  EMAIL_PROTOKOLLE }o--o| ANFRAGEN : "erzeugt/gehoert zu"
  EMAIL_PROTOKOLLE }o--o| BEWERBUNGEN : "gehoert zu"
```

## Tabellen

| Bereich | Tabellen |
|---|---|
| Zugang | `benutzer` (Rolle admin/büro/mitarbeiter; Passwörter verwaltet Django) |
| Kunden | `kunden`, `ansprechpartner` (inkl. Nachweis E-Mail-Einwilligung) |
| Objekte & Leistungen | `objekte`, `leistungen` (Katalog mit Preisen), `leistungsvereinbarungen` (wiederkehrend je Objekt) |
| Vertrieb | `anfragen`, `angebote`, `angebotspositionen` |
| Ausführung | `auftraege`, `einsaetze`, `einsatz_mitarbeiter`, `arbeitszeiten`, `fotos` |
| Personal | `mitarbeiter`, `qualifikationen`, `mitarbeiter_qualifikationen`, `verfuegbarkeiten`, `abwesenheiten`, `stellen`, `bewerbungen` |
| Finanzen | `rechnungen` (Spiegel aus Lexware) |
| Ablage & Kommunikation | `dokumente`, `email_protokolle` |
| Technik | `nummernkreise`, `ki_aufrufe`, `sync_protokoll`, `audit_log` |
| Auswertungen (Views) | `v_umsatz_monat`, `v_arbeitsstunden_woche`, `v_offene_angebote` |

## Getestete Regeln (27)
Siehe Ausgabe von `run.sh`. Unter anderem: Dubletten, Objekt gehört zum Kunden, Angebots- und Mail-Freigabe, keine Doppelbelegung, keine überlappenden Zeiten, keine doppelten wiederkehrenden Einsätze, Rechnung je Auftrag nur einmal, Audit-Log mit Benutzer, Löschfrist Bewerbungen.
