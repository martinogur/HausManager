-- Rückweg zu 0003_betriebssystem.sql (Migration kern.0003 rückwärts).
-- Der ENUM-Wert auftragsstatus 'zu_pruefen' bleibt bestehen (PostgreSQL kann Werte nicht entfernen);
-- ohne die Statusregel ist er harmlos.
SET search_path = hh, public;

DROP VIEW IF EXISTS v_ki_kosten_tag, v_wiederkehrende_umsaetze, v_auftrag_wirtschaftlichkeit;
DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['anfragen', 'email_protokolle', 'bewerbungen', 'auftraege', 'einsaetze', 'angebote', 'rechnungen']
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I_ereignisse ON %I', t, t);
    END LOOP;
END $$;
DROP TRIGGER IF EXISTS auftraege_statuswechsel ON auftraege;
DROP TABLE IF EXISTS social_beitraege, automatisierungs_laeufe, automatisierungen, ereignisse,
                     lead_kontakte, freigaben, agenten_protokoll CASCADE;
ALTER TABLE ki_aufrufe DROP COLUMN IF EXISTS agent, DROP COLUMN IF EXISTS agenten_auftrag_id;
DROP TABLE IF EXISTS agenten_auftraege, agenten, leads, firmenparameter CASCADE;
DROP FUNCTION IF EXISTS ereignisse_aus_fachdaten(), ereignis_ausloesen(text, text, uuid, jsonb),
    lead_kontakt_freigabe_pruefen(), lead_kontakt_pruefen(), agentenauftrag_kette_pruefen(), nur_anfuegen(),
    auftrag_statuswechsel_pruefen();
ALTER TABLE auftraege DROP COLUMN IF EXISTS prioritaet, DROP COLUMN IF EXISTS geschaetzte_minuten,
    DROP COLUMN IF EXISTS materialkosten_cent, DROP COLUMN IF EXISTS verkaufspreis_netto_cent,
    DROP COLUMN IF EXISTS bemerkungen;
DROP TYPE IF EXISTS beitragsstatus, beitragsformat, freigabestatus, freigabeart, agentenauftragsstatus,
    kontaktkanal, zielgruppe, leadprioritaet, leadstatus, prioritaet;
