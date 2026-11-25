# Aufgabenliste (priorisiert)

Stand 25.11.2026. P0 = blockiert den Betrieb, P1 = vor Produktivsetzung, P2 = danach.

## Erledigt in dieser Ausbaustufe

- [x] Bestandsaufnahme aller Branches, Übernahme des Portal-Stands (Phase 1+2) in den Arbeitsbranch
- [x] DB-Erweiterung 0003 (11 Tabellen, 3 Sichten, Trigger) + 31 neue SQL-Tests
- [x] Auftragsstatus nach Betriebsablauf inkl. „Zu prüfen“, Statusregeln in DB und Code
- [x] Wirtschaftlichkeit je Auftrag (Ist-Zeit, Personal-, Materialkosten, Deckungsbeitrag)
- [x] Angebotskalkulation nach freigegebener Preisliste (Beispielobjekte exakt), Angebotsrechner
- [x] Lead-Scoring A/B/C, Einsatzgebiet 30 km, zulässige Kontaktwege (UWG), Widerspruch, Lead → Kunde
- [x] Import des Lead-Bestands (52 Leads inkl. Einladungsbelege), Fressnapf als offene Chance
- [x] Agenten-Laufzeit (Warteschlange, Budget, Grenzen, Backoff, Eskalation, Kosten nach Rollback)
- [x] 13 Agenten mit 19 Aufgaben, Claude-Client (Structured Outputs, Fallback, Kostenprotokoll)
- [x] Freigabe-Warteschlange mit Folgeaktionen, 18 Automatisierungen, Zeitplan, Überwachung
- [x] IONOS IMAP/SMTP, HubSpot-Deal, Lexware-Entwurf + Statusabgleich (gedrosselt), Make-Webhook
- [x] Steuerungsoberfläche (15 Bereiche), mobile Einsatzansicht mit Zeit, Bericht, Fotos ohne EXIF
- [x] Worker-Dienst im Docker-Stack, Erweiterungs-SQL im Image, Secrets-Vorlagen
- [x] Dokumentation (10 Dateien)

## P0 – Entscheidungen/Zugänge (Inhaber)

- [ ] D1 Architektur bestätigen · D2 Hetzner buchen · D3 Anthropic-Schlüssel mit Limit
- [ ] D4 Fressnapf-Status und Leistungsumfang nachtragen
- [ ] D5 IONOS-Postfach-Zugang · D6 HubSpot ja/nein · D7 Lexware XL ja/nein · D8 Craftnote-Ablösung · D9 USt-Regelung

## P1 – vor Produktivsetzung (Entwicklung)

- [ ] Löschjobs: Bewerbungen nach `loeschen_ab` (inkl. Dateien), Leads 24 Monate ohne Aktivität, Protokolle 12 Monate
- [ ] Rate-Limit für `/api/` in Caddy; Worker-Herzschlag in `/gesund` + externe Uptime-Prüfung
- [ ] E-Mail-Anhänge als Dokumente speichern (IONOS), HTML-Mails in Text umwandeln
- [ ] Instagram-Veröffentlichung aus dem Redaktionskalender (`posten.py` liest freigegebene `social_beitraege`)
- [ ] Wochenbericht zusätzlich als E-Mail an den Inhaber (über Freigabe-freien Kanal „an sich selbst“ – Regel klären)
- [ ] Qualifikationen ↔ Leistungen verknüpfen (Disposition berücksichtigt Qualifikation)
- [ ] Datenimport echter Kunden/Objekte (CSV-Import mit Dublettenprüfung)
- [ ] Verzeichnis der Verarbeitungstätigkeiten, AV-Verträge sammeln, Datenschutzhinweise Mitarbeiter/Bewerber
- [ ] Prompts mit 20 echten (anonymisierten) Mails prüfen; Eval-Set für Einordnung und Antwortqualität

## P2 – Optimierung

- [ ] Bewertungsanfragen nach erledigten Aufträgen (Tabelle `bewertungsanfragen`, Phase-4-Plan)
- [ ] Social-Kennzahlen importieren (Reichweite, Interaktionen) und im Marketing-Bereich auswerten
- [ ] Routenoptimierung/Tourenplanung für wiederkehrende Einsätze (Fahrzeit sparen)
- [ ] Angebots-PDF aus dem Portal (heute Vorlagen in `akquise/angebote/vorlagen/`)
- [ ] Kosten-Review der KI nach 4 Wochen (Effort je Zweck, ggf. kleineres Modell für Einordnung nach Messung)
- [ ] Schema-Verbesserungen aus `berichte/2026-11-25-portal-phase2.md` (Punkte 1–8)
