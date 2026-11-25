-- Tests für das Datenmodell. Aufruf (gegen eine leere Testdatenbank mit geladenem schema.sql):
--   psql -v ON_ERROR_STOP=1 -d <testdb> -f portal/db/tests/test_schema.sql
-- Jeder Test meldet OK oder bricht mit FEHLER ab. Alles läuft in einer Transaktion und wird zurückgerollt.
SET search_path = hh, public;
BEGIN;

-- Hilfsfunktion: erwartet, dass eine Anweisung mit einem bestimmten Fehlercode scheitert
CREATE FUNCTION pg_temp.muss_scheitern(sql text, erwarteter_code text, name text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        EXECUTE sql;
    EXCEPTION WHEN others THEN
        IF SQLSTATE = erwarteter_code THEN RAISE NOTICE 'OK   %', name; RETURN; END IF;
        RAISE EXCEPTION 'FEHLER %: falscher Fehlercode % (%), erwartet %', name, SQLSTATE, SQLERRM, erwarteter_code;
    END;
    RAISE EXCEPTION 'FEHLER %: Anweisung hätte scheitern müssen', name;
END $$;
CREATE FUNCTION pg_temp.pruefe(bedingung boolean, name text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN IF bedingung THEN RAISE NOTICE 'OK   %', name; ELSE RAISE EXCEPTION 'FEHLER %', name; END IF; END $$;

SELECT set_config('app.benutzer', 'test@haus-meister-helden.de', true);

-- Stammdaten
INSERT INTO benutzer (id, email, anzeigename, rolle) VALUES
  ('00000000-0000-0000-0000-000000000001', 'martin@example.org', 'Martin', 'admin');
INSERT INTO kunden (id, name, typ, plz, ort) VALUES
  ('10000000-0000-0000-0000-000000000001', 'Muster Hausverwaltung GmbH', 'hausverwaltung', '33330', 'Gütersloh'),
  ('10000000-0000-0000-0000-000000000002', 'Andere Verwaltung KG', 'hausverwaltung', '33378', 'Rheda-Wiedenbrück');
INSERT INTO objekte (id, kunde_id, bezeichnung, strasse, hausnummer, plz, ort, treppenhaeuser, etagen) VALUES
  ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'WEG Beispielweg 1', 'Beispielweg', '1', '33330', 'Gütersloh', 1, 3);
INSERT INTO mitarbeiter (id, vorname, nachname, beschaeftigung, email) VALUES
  ('30000000-0000-0000-0000-000000000001', 'Max', 'Muster', 'minijob', 'max@example.org');
INSERT INTO leistungen (id, code, name, einheit, preis_netto_cent) VALUES
  ('40000000-0000-0000-0000-000000000001', 'TH-GRUND', 'Treppenhausreinigung Grundpreis', 'je Reinigung', 1200),
  ('40000000-0000-0000-0000-000000000002', 'TH-ETAGE', 'Treppenhausreinigung je Etage', 'je Etage', 800);

-- 1 Lesbare Nummern werden vergeben
SELECT pg_temp.pruefe((SELECT kundennummer FROM kunden WHERE id = '10000000-0000-0000-0000-000000000001') ~ '^K-[0-9]{5}$', 'Kundennummer wird automatisch vergeben');

-- 2 Dubletten
SELECT pg_temp.muss_scheitern($$INSERT INTO kunden (name, typ, plz) VALUES ('muster  hausverwaltung gmbh', 'hausverwaltung', '33330')$$, '23505', 'Kunde doppelt (Groß-/Kleinschreibung, Leerzeichen)');
SELECT pg_temp.muss_scheitern($$INSERT INTO objekte (kunde_id, bezeichnung, strasse, hausnummer, plz, ort) VALUES ('10000000-0000-0000-0000-000000000002', 'x', 'BEISPIELWEG', '1', '33330', 'Gütersloh')$$, '23505', 'Objekt mit gleicher Adresse doppelt');
INSERT INTO ansprechpartner (kunde_id, nachname, email) VALUES ('10000000-0000-0000-0000-000000000001', 'Schmidt', 'Schmidt@Example.org');
SELECT pg_temp.muss_scheitern($$INSERT INTO ansprechpartner (kunde_id, nachname, email) VALUES ('10000000-0000-0000-0000-000000000002', 'Schmidt', 'schmidt@example.org')$$, '23505', 'Ansprechpartner-E-Mail doppelt');
SELECT pg_temp.muss_scheitern($$INSERT INTO kunden (name, typ, plz) VALUES ('X', 'privat', '3333')$$, '23514', 'Ungültige PLZ abgelehnt');

-- 3 Einwilligung für Werbe-E-Mails braucht einen Nachweis
SELECT pg_temp.muss_scheitern($$INSERT INTO ansprechpartner (kunde_id, nachname, email_einwilligung) VALUES ('10000000-0000-0000-0000-000000000001', 'Meier', now())$$, '23514', 'Einwilligung ohne Quelle abgelehnt');

-- 4 Auftrag: Objekt muss zum Kunden gehören
SELECT pg_temp.muss_scheitern($$INSERT INTO auftraege (kunde_id, objekt_id, titel) VALUES ('10000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000001', 'falsch')$$, '23503', 'Auftrag mit fremdem Objekt abgelehnt');
INSERT INTO auftraege (id, kunde_id, objekt_id, titel) VALUES
  ('50000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'Treppenhausreinigung wöchentlich');
SELECT pg_temp.pruefe((SELECT auftragsnummer FROM auftraege WHERE id = '50000000-0000-0000-0000-000000000001') ~ '^AU-[0-9]{4}-[0-9]{4}$', 'Auftragsnummer mit Jahr');

-- 5 Angebot: Summe aus Positionen, kein Versand ohne Freigabe
INSERT INTO angebote (id, kunde_id, objekt_id) VALUES ('60000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001');
INSERT INTO angebotspositionen (angebot_id, pos, leistung_id, beschreibung, menge, einheit, einzelpreis_netto_cent, intervall) VALUES
  ('60000000-0000-0000-0000-000000000001', 1, '40000000-0000-0000-0000-000000000001', 'Grundpreis', 4.33, 'Reinigungen/Monat', 1200, 'woechentlich'),
  ('60000000-0000-0000-0000-000000000001', 2, '40000000-0000-0000-0000-000000000002', '3 Etagen', 12.99, 'Etagen-Reinigungen/Monat', 800, 'woechentlich');
SELECT pg_temp.pruefe((SELECT summe_netto_cent FROM angebote WHERE id = '60000000-0000-0000-0000-000000000001') = 15588, 'Angebotssumme 155,88 € automatisch berechnet');
SELECT pg_temp.muss_scheitern($$UPDATE angebote SET status = 'versendet' WHERE id = '60000000-0000-0000-0000-000000000001'$$, '23514', 'Angebot ohne Freigabe nicht versendbar');
UPDATE angebote SET status = 'versendet', freigegeben_von = '00000000-0000-0000-0000-000000000001', freigegeben_am = now() WHERE id = '60000000-0000-0000-0000-000000000001';
SELECT pg_temp.pruefe(true, 'Angebot mit Freigabe versendbar');

-- 6 Einsatzplanung: keine Doppelbelegung eines Mitarbeiters
INSERT INTO einsaetze (id, auftrag_id, geplant_von, geplant_bis) VALUES
  ('70000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000001', '2026-12-01 08:00+01', '2026-12-01 09:00+01'),
  ('70000000-0000-0000-0000-000000000002', '50000000-0000-0000-0000-000000000001', '2026-12-01 08:30+01', '2026-12-01 10:00+01');
INSERT INTO einsatz_mitarbeiter (einsatz_id, mitarbeiter_id) VALUES ('70000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001');
SELECT pg_temp.muss_scheitern($$INSERT INTO einsatz_mitarbeiter (einsatz_id, mitarbeiter_id) VALUES ('70000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000001')$$, '23P01', 'Mitarbeiter nicht gleichzeitig in zwei Einsätzen');
UPDATE einsaetze SET geplant_von = '2026-12-01 10:00+01', geplant_bis = '2026-12-01 11:00+01' WHERE id = '70000000-0000-0000-0000-000000000002';
INSERT INTO einsatz_mitarbeiter (einsatz_id, mitarbeiter_id) VALUES ('70000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000001');
SELECT pg_temp.pruefe(true, 'Nach Verschieben ist die Zuweisung möglich');
SELECT pg_temp.muss_scheitern($$UPDATE einsaetze SET geplant_von = '2026-12-01 08:30+01' WHERE id = '70000000-0000-0000-0000-000000000002'$$, '23P01', 'Verschieben in Überschneidung wird verhindert');

-- 7 Wiederkehrende Arbeiten nicht doppelt erzeugen
INSERT INTO leistungsvereinbarungen (id, objekt_id, leistung_id, intervall, wochentag, preis_netto_cent, gueltig_von) VALUES
  ('80000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000001', 'woechentlich', 2, 3600, '2026-12-01');
SELECT pg_temp.muss_scheitern($$INSERT INTO leistungsvereinbarungen (objekt_id, leistung_id, intervall, preis_netto_cent, gueltig_von) VALUES ('20000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000001', 'woechentlich', 3600, '2026-12-01')$$, '23514', 'Wöchentlich ohne Wochentag abgelehnt');
INSERT INTO einsaetze (auftrag_id, geplant_von, geplant_bis, erzeugt_aus) VALUES
  ('50000000-0000-0000-0000-000000000001', '2026-12-08 08:00+01', '2026-12-08 09:00+01', '80000000-0000-0000-0000-000000000001');
SELECT pg_temp.muss_scheitern($$INSERT INTO einsaetze (auftrag_id, geplant_von, geplant_bis, erzeugt_aus) VALUES ('50000000-0000-0000-0000-000000000001', '2026-12-08 13:00+01', '2026-12-08 14:00+01', '80000000-0000-0000-0000-000000000001')$$, '23505', 'Wiederkehrender Einsatz am selben Tag nicht doppelt');

-- 8 Zeiterfassung: keine überlappenden Buchungen, Pause plausibel
INSERT INTO arbeitszeiten (mitarbeiter_id, einsatz_id, beginn, ende, pause_minuten) VALUES
  ('30000000-0000-0000-0000-000000000001', '70000000-0000-0000-0000-000000000001', '2026-12-01 08:00+01', '2026-12-01 09:05+01', 0);
SELECT pg_temp.muss_scheitern($$INSERT INTO arbeitszeiten (mitarbeiter_id, beginn, ende) VALUES ('30000000-0000-0000-0000-000000000001', '2026-12-01 09:00+01', '2026-12-01 10:00+01')$$, '23P01', 'Überlappende Arbeitszeit abgelehnt');
SELECT pg_temp.muss_scheitern($$INSERT INTO arbeitszeiten (mitarbeiter_id, beginn, ende, pause_minuten) VALUES ('30000000-0000-0000-0000-000000000001', '2026-12-02 08:00+01', '2026-12-02 09:00+01', 60)$$, '23514', 'Pause länger als Arbeitszeit abgelehnt');
SELECT pg_temp.pruefe((SELECT stunden FROM v_arbeitsstunden_woche LIMIT 1) = 1.08, 'Wochenstunden-Auswertung (1:05 h = 1,08 h)');

-- 9 E-Mail: kein Versand ohne Freigabe, kein Doppelimport
INSERT INTO email_protokolle (richtung, message_id, postfach, von, an, betreff, status) VALUES
  ('eingang', '<abc@mail.example>', 'info@haus-meister-helden.de', 'kunde@example.org', ARRAY['info@haus-meister-helden.de']::citext[], 'Anfrage', 'neu');
SELECT pg_temp.muss_scheitern($$INSERT INTO email_protokolle (richtung, message_id, postfach, von, an, status) VALUES ('eingang', '<abc@mail.example>', 'info@haus-meister-helden.de', 'kunde@example.org', ARRAY['info@haus-meister-helden.de']::citext[], 'neu')$$, '23505', 'Gleiche E-Mail nicht doppelt importiert');
SELECT pg_temp.muss_scheitern($$INSERT INTO email_protokolle (richtung, postfach, von, an, status, gesendet_am) VALUES ('ausgang', 'info@haus-meister-helden.de', 'info@haus-meister-helden.de', ARRAY['kunde@example.org']::citext[], 'gesendet', now())$$, '23514', 'Ausgehende E-Mail ohne Freigabe nicht sendbar');

-- 10 Bewerbung: keine Doppelbewerbung, Löschfrist gesetzt
INSERT INTO stellen (id, titel, beschaeftigung) VALUES ('90000000-0000-0000-0000-000000000001', 'Aushilfe Reinigung', 'minijob');
INSERT INTO bewerbungen (stelle_id, vorname, nachname, email, datenschutz_ok_am) VALUES ('90000000-0000-0000-0000-000000000001', 'Eva', 'Beispiel', 'eva@example.org', now());
SELECT pg_temp.muss_scheitern($$INSERT INTO bewerbungen (stelle_id, vorname, nachname, email, datenschutz_ok_am) VALUES ('90000000-0000-0000-0000-000000000001', 'Eva', 'Beispiel', 'EVA@example.org', now())$$, '23505', 'Doppelbewerbung auf dieselbe Stelle abgelehnt');
SELECT pg_temp.pruefe((SELECT loeschen_ab FROM bewerbungen LIMIT 1) = current_date + 180, 'Löschfrist Bewerbung = 6 Monate');

-- 11 Rechnung: ein Auftrag nur einmal abgerechnet
INSERT INTO rechnungen (kunde_id, auftrag_id, summe_netto_cent, summe_brutto_cent) VALUES ('10000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000001', 15588, 18550);
SELECT pg_temp.muss_scheitern($$INSERT INTO rechnungen (kunde_id, auftrag_id, summe_netto_cent, summe_brutto_cent) VALUES ('10000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000001', 1, 1)$$, '23505', 'Auftrag nicht doppelt abrechenbar');

-- 12 Audit-Log schreibt mit, inkl. Benutzer
UPDATE kunden SET status = 'aktiv' WHERE id = '10000000-0000-0000-0000-000000000001';
SELECT pg_temp.pruefe(EXISTS (SELECT 1 FROM audit_log WHERE tabelle = 'kunden' AND aktion = 'UPDATE' AND neu->>'status' = 'aktiv' AND benutzer = 'test@haus-meister-helden.de'), 'Änderung im Audit-Log mit Benutzer');
SELECT pg_temp.pruefe((SELECT count(*) FROM audit_log WHERE tabelle = 'auftraege') >= 1, 'Aufträge werden protokolliert');

-- 13 Dokumente brauchen einen Bezug
SELECT pg_temp.muss_scheitern($$INSERT INTO dokumente (dateiname, mime_typ, groesse_bytes, sha256, speicher_schluessel, kategorie) VALUES ('a.pdf', 'application/pdf', 10, 'x', 'k1', 'vertrag')$$, '23514', 'Dokument ohne Bezug abgelehnt');

DO $$ BEGIN RAISE NOTICE 'ALLE TESTS BESTANDEN'; END $$;
ROLLBACK;
