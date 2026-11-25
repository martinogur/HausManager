-- Tests für die Erweiterung 0003 (Agenten, Akquise, Freigaben, Ereignisse, Auftragsregeln).
-- Läuft nach schema.sql + erweiterungen/*.sql in einer Transaktion und wird zurückgerollt.
SET search_path = hh, public;
BEGIN;

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

INSERT INTO benutzer (id, email, anzeigename, rolle) VALUES
  ('00000000-0000-0000-0000-000000000001', 'chef@example.org', 'Chef', 'admin');
INSERT INTO kunden (id, name, typ, plz, ort) VALUES
  ('10000000-0000-0000-0000-000000000001', 'Beispiel Verwaltung GmbH', 'hausverwaltung', '33330', 'Gütersloh');
INSERT INTO objekte (id, kunde_id, bezeichnung, strasse, hausnummer, plz, ort) VALUES
  ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'WEG Testweg 1', 'Testweg', '1', '33330', 'Gütersloh');
INSERT INTO mitarbeiter (id, vorname, nachname, beschaeftigung, stundenlohn_cent) VALUES
  ('30000000-0000-0000-0000-000000000001', 'Mia', 'Muster', 'minijob', 1500);

-- 1 Auftragsstatus: erlaubte und verbotene Wechsel
INSERT INTO auftraege (id, kunde_id, objekt_id, titel, status, verkaufspreis_netto_cent, materialkosten_cent) VALUES
  ('50000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001',
   'Heckenschnitt', 'anfrage', 20000, 1000);
UPDATE auftraege SET status = 'zu_pruefen' WHERE id = '50000000-0000-0000-0000-000000000001';
SELECT pg_temp.pruefe((SELECT status = 'zu_pruefen' FROM auftraege WHERE id = '50000000-0000-0000-0000-000000000001'), 'Status Neu → Zu prüfen');
SELECT pg_temp.muss_scheitern($$UPDATE auftraege SET status = 'erledigt' WHERE id = '50000000-0000-0000-0000-000000000001'$$, '23514', 'Sprung Zu prüfen → Erledigt verboten');
UPDATE auftraege SET status = 'bestaetigt' WHERE id = '50000000-0000-0000-0000-000000000001';
SELECT pg_temp.pruefe((SELECT bestaetigt_am IS NOT NULL FROM auftraege WHERE id = '50000000-0000-0000-0000-000000000001'), 'Freigegeben setzt bestaetigt_am');
UPDATE auftraege SET status = 'geplant' WHERE id = '50000000-0000-0000-0000-000000000001';
UPDATE auftraege SET status = 'in_arbeit' WHERE id = '50000000-0000-0000-0000-000000000001';
UPDATE auftraege SET status = 'erledigt' WHERE id = '50000000-0000-0000-0000-000000000001';
SELECT pg_temp.muss_scheitern($$UPDATE auftraege SET status = 'abgerechnet' WHERE id = '50000000-0000-0000-0000-000000000001'$$, '23514', 'Abgerechnet ohne Rechnung verboten');
INSERT INTO rechnungen (kunde_id, auftrag_id, summe_netto_cent, summe_brutto_cent) VALUES
  ('10000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000001', 20000, 23800);
UPDATE auftraege SET status = 'abgerechnet' WHERE id = '50000000-0000-0000-0000-000000000001';
SELECT pg_temp.muss_scheitern($$UPDATE auftraege SET status = 'in_arbeit' WHERE id = '50000000-0000-0000-0000-000000000001'$$, '23514', 'Abgerechnet ist Endstatus');

-- 2 Ereignisse entstehen automatisch
SELECT pg_temp.pruefe((SELECT count(*) FROM ereignisse WHERE typ = 'auftrag.status' AND bezug_id = '50000000-0000-0000-0000-000000000001') = 6,
    'Jeder Statuswechsel erzeugt ein Ereignis');
INSERT INTO anfragen (id, kanal, betreff) VALUES ('70000000-0000-0000-0000-000000000001', 'webseite', 'Treppenhaus');
SELECT pg_temp.pruefe(EXISTS (SELECT 1 FROM ereignisse WHERE typ = 'anfrage.neu' AND bezug_id = '70000000-0000-0000-0000-000000000001'), 'Neue Anfrage erzeugt Ereignis');
INSERT INTO email_protokolle (richtung, postfach, von, an, betreff) VALUES ('eingang', 'info@example.org', 'kunde@example.org', '{info@example.org}', 'Hallo');
SELECT pg_temp.pruefe(EXISTS (SELECT 1 FROM ereignisse WHERE typ = 'email.eingang'), 'Eingehende E-Mail erzeugt Ereignis');

-- 3 Wirtschaftlichkeit: Ist-Zeit und Personalkosten aus Arbeitszeiten
INSERT INTO einsaetze (id, auftrag_id, geplant_von, geplant_bis, status) VALUES
  ('80000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000001', '2026-12-01 08:00+01', '2026-12-01 11:00+01', 'geplant');
INSERT INTO arbeitszeiten (mitarbeiter_id, einsatz_id, beginn, ende, pause_minuten) VALUES
  ('30000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000001', '2026-12-01 08:00+01', '2026-12-01 10:15+01', 15);
-- 2 h × 15 € × 1,328 = 39,84 € → 3984 Cent; DB = 20000 − 1000 − 3984 = 15016
SELECT pg_temp.pruefe((SELECT ist_minuten = 120 AND personalkosten_cent = 3984 AND deckungsbeitrag_cent = 15016
                       FROM v_auftrag_wirtschaftlichkeit WHERE auftrag_id = '50000000-0000-0000-0000-000000000001'),
    'Deckungsbeitrag aus Zeiten, Lohn und Nebenkosten');

-- 4 Leads: Quelle Pflicht, Dubletten, UWG-Regeln
SELECT pg_temp.muss_scheitern($$INSERT INTO leads (firma, zielgruppe, quelle) VALUES ('Ohne Quelle GmbH', 'hausverwaltung', ' ')$$, '23514', 'Lead ohne Quelle abgelehnt');
INSERT INTO leads (id, firma, zielgruppe, plz, ort, quelle, email) VALUES
  ('90000000-0000-0000-0000-000000000001', 'Test Hausverwaltung GmbH', 'hausverwaltung', '33330', 'Gütersloh', 'Impressum https://example.org', 'info@example.org');
SELECT pg_temp.pruefe((SELECT leadnummer ~ '^LD-[0-9]{5}$' FROM leads WHERE id = '90000000-0000-0000-0000-000000000001'), 'Leadnummer wird vergeben');
SELECT pg_temp.pruefe(EXISTS (SELECT 1 FROM ereignisse WHERE typ = 'lead.neu' AND bezug_id = '90000000-0000-0000-0000-000000000001'), 'Neuer Lead erzeugt Ereignis');
SELECT pg_temp.muss_scheitern($$INSERT INTO leads (firma, zielgruppe, plz, quelle) VALUES ('test  hausverwaltung gmbh', 'hausverwaltung', '33330', 'x')$$, '23505', 'Lead doppelt abgelehnt');
SELECT pg_temp.muss_scheitern($$INSERT INTO lead_kontakte (lead_id, kanal, richtung, zusammenfassung, durch) VALUES ('90000000-0000-0000-0000-000000000001', 'email', 'ausgehend', 'Werbung', 'chef@example.org')$$, '23514', 'Werbe-E-Mail ohne Einwilligung abgelehnt');
INSERT INTO lead_kontakte (lead_id, kanal, richtung, zusammenfassung, durch) VALUES ('90000000-0000-0000-0000-000000000001', 'brief', 'ausgehend', 'Vorstellungsbrief', 'chef@example.org');
SELECT pg_temp.muss_scheitern($$INSERT INTO lead_kontakte (lead_id, kanal, richtung, zusammenfassung, durch) VALUES ('90000000-0000-0000-0000-000000000001', 'brief', 'ausgehend', 'Brief', 'agent:sales')$$, '23514', 'Agent ohne Freigabe kann keinen Kontakt protokollieren');
SELECT pg_temp.muss_scheitern($$UPDATE leads SET widerspruch_am = now() WHERE id = '90000000-0000-0000-0000-000000000001'$$, '23514', 'Widerspruch nur mit Status gesperrt');
UPDATE leads SET widerspruch_am = now() - interval '1 minute', status = 'gesperrt' WHERE id = '90000000-0000-0000-0000-000000000001';
SELECT pg_temp.muss_scheitern($$INSERT INTO lead_kontakte (lead_id, kanal, richtung, zusammenfassung, durch) VALUES ('90000000-0000-0000-0000-000000000001', 'telefon', 'ausgehend', 'Anruf', 'chef@example.org')$$, '23514', 'Nach Widerspruch kein Kontakt');
SELECT pg_temp.muss_scheitern($$UPDATE leads SET status = 'gewonnen', widerspruch_am = NULL WHERE id = '90000000-0000-0000-0000-000000000001'$$, '23514', 'Gewonnen nur mit Kunde');

-- 5 Agenten-Aufträge: Tiefe, Schleifen, Kette
INSERT INTO agenten (code, name, beschreibung) VALUES ('ceo', 'CEO', 'x'), ('sales', 'Sales', 'x'), ('offer', 'Angebot', 'x'), ('quality', 'Qualität', 'x');
INSERT INTO agenten_auftraege (id, agent, aufgabe, ausgeloest_von) VALUES ('a0000000-0000-0000-0000-000000000001', 'ceo', 'tagesplan', 'zeitplan:test');
SELECT pg_temp.pruefe((SELECT kette_id = id AND tiefe = 0 FROM agenten_auftraege WHERE id = 'a0000000-0000-0000-0000-000000000001'), 'Wurzelauftrag startet eigene Kette');
INSERT INTO agenten_auftraege (id, agent, aufgabe, ausgeloest_von, eltern_id) VALUES ('a0000000-0000-0000-0000-000000000002', 'sales', 'lead_bewerten', 'agent:ceo', 'a0000000-0000-0000-0000-000000000001');
SELECT pg_temp.pruefe((SELECT kette_id = 'a0000000-0000-0000-0000-000000000001' AND tiefe = 1 FROM agenten_auftraege WHERE id = 'a0000000-0000-0000-0000-000000000002'), 'Delegation erbt Kette, Tiefe +1');
SELECT pg_temp.muss_scheitern($$INSERT INTO agenten_auftraege (agent, aufgabe, ausgeloest_von, eltern_id) VALUES ('ceo', 'tagesplan', 'agent:sales', 'a0000000-0000-0000-0000-000000000002')$$, '23514', 'Schleife ceo → sales → ceo (gleiche Aufgabe) verhindert');
INSERT INTO agenten_auftraege (id, agent, aufgabe, ausgeloest_von, eltern_id) VALUES ('a0000000-0000-0000-0000-000000000003', 'offer', 'angebot_berechnen', 'agent:sales', 'a0000000-0000-0000-0000-000000000002');
INSERT INTO agenten_auftraege (id, agent, aufgabe, ausgeloest_von, eltern_id) VALUES ('a0000000-0000-0000-0000-000000000004', 'quality', 'pruefen', 'agent:offer', 'a0000000-0000-0000-0000-000000000003');
SELECT pg_temp.muss_scheitern($$INSERT INTO agenten_auftraege (agent, aufgabe, ausgeloest_von, eltern_id) VALUES ('sales', 'nachfassen', 'agent:quality', 'a0000000-0000-0000-0000-000000000004')$$, '23514', 'Maximale Delegationstiefe 3');
SELECT pg_temp.muss_scheitern($$UPDATE agenten_auftraege SET versuche = 4 WHERE id = 'a0000000-0000-0000-0000-000000000001'$$, '23514', 'Mehr Versuche als erlaubt verhindert');
SELECT pg_temp.muss_scheitern($$UPDATE agenten_auftraege SET status = 'erledigt' WHERE id = 'a0000000-0000-0000-0000-000000000001'$$, '23514', 'Abschluss nur mit Endzeit');
INSERT INTO agenten_protokoll (auftrag_id, art, inhalt) VALUES ('a0000000-0000-0000-0000-000000000001', 'start', '{}');
SELECT pg_temp.muss_scheitern($$UPDATE agenten_protokoll SET art = 'fehler'$$, '42501', 'Agenten-Protokoll ist nur anfügbar');

-- 6 Freigaben: Entscheidung nur mit Mensch, eine offene je Bezug
INSERT INTO freigaben (id, art, titel, angefordert_von, bezug_tabelle, bezug_id) VALUES
  ('b0000000-0000-0000-0000-000000000001', 'lead_kontakt', 'Brief an Test', 'agent:sales', 'leads', '90000000-0000-0000-0000-000000000001');
SELECT pg_temp.pruefe((SELECT freigabenummer ~ '^FG-[0-9]{4}-[0-9]{4}$' FROM freigaben WHERE id = 'b0000000-0000-0000-0000-000000000001'), 'Freigabenummer mit Jahr');
SELECT pg_temp.muss_scheitern($$INSERT INTO freigaben (art, titel, angefordert_von, bezug_tabelle, bezug_id) VALUES ('lead_kontakt', 'doppelt', 'agent:sales', 'leads', '90000000-0000-0000-0000-000000000001')$$, '23505', 'Nur eine offene Freigabe je Bezug');
SELECT pg_temp.muss_scheitern($$UPDATE freigaben SET status = 'freigegeben' WHERE id = 'b0000000-0000-0000-0000-000000000001'$$, '23514', 'Freigabe ohne entscheidende Person abgelehnt');
UPDATE freigaben SET status = 'freigegeben', entschieden_von = '00000000-0000-0000-0000-000000000001', entschieden_am = now()
 WHERE id = 'b0000000-0000-0000-0000-000000000001';
SELECT pg_temp.pruefe(EXISTS (SELECT 1 FROM ereignisse WHERE typ = 'freigabe.entschieden' AND bezug_id = 'b0000000-0000-0000-0000-000000000001'), 'Entscheidung erzeugt Ereignis');

-- 7 Social: veröffentlicht nur mit Freigabe
SELECT pg_temp.muss_scheitern($$INSERT INTO social_beitraege (plattform, format, geplant_fuer, thema, status, veroeffentlicht_am, erstellt_von) VALUES ('instagram', 'post', now(), 'Test', 'veroeffentlicht', now(), 'agent:social')$$, '23514', 'Beitrag ohne Freigabe nicht veröffentlichbar');

-- 8 Wiederkehrender Umsatz
INSERT INTO leistungen (id, code, name, einheit, preis_netto_cent) VALUES ('40000000-0000-0000-0000-000000000001', 'TH', 'Treppenhaus', 'je Reinigung', 3600);
INSERT INTO leistungsvereinbarungen (objekt_id, leistung_id, intervall, wochentag, preis_netto_cent, gueltig_von) VALUES
  ('20000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000001', 'woechentlich', 2, 3600, current_date - 1);
SELECT pg_temp.pruefe((SELECT sum(monatsumsatz_cent) = 15600 FROM v_wiederkehrende_umsaetze), 'Wöchentlich 36 € = 156 € im Monat');

DO $$ BEGIN RAISE NOTICE 'ALLE TESTS BESTANDEN'; END $$;
ROLLBACK;
