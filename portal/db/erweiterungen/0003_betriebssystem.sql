-- =============================================================================
-- Hausmeister Helden AI OS – Erweiterung 0003 „Betriebssystem“
--
-- Ergänzt das Grundschema (schema.sql) um alles, was KI-Agenten und
-- Automatisierungen brauchen, ohne bestehende Tabellen umzubauen:
--   * Akquise-Pipeline (leads, lead_kontakte) mit UWG-/DSGVO-Regeln in der Datenbank
--   * Agenten-Register, Agenten-Aufträge mit Schleifenschutz, Agenten-Protokoll
--   * Freigabe-Warteschlange (nichts geht ohne Freigabe nach außen)
--   * Ereignisse (Outbox) – Trigger auf Fachtabellen erzeugen sie automatisch
--   * Automatisierungen und ihre Läufe
--   * Redaktionskalender (social_beitraege)
--   * Firmenparameter (Kalkulation, Einsatzgebiet, KI-Budget)
--   * Auftragssteuerung: Priorität, Planzeit, Material, Verkaufspreis, Statusregeln
--
-- Wird von der Migration kern.0003_betriebssystem ausgeführt (Rückweg:
-- 0003_betriebssystem_zurueck.sql). Geld in Cent, Zeiten als timestamptz.
-- =============================================================================

SET search_path = hh, public;

-- ---------------------------------------------------------------- Aufträge: Steuerung & Wirtschaftlichkeit
-- Neuer Status „zu prüfen“ zwischen Anfrage (= „Neu“) und Angebot.
-- Hinweis: Der neue ENUM-Wert ist erst nach dem Ende dieser Transaktion benutzbar;
-- er wird hier nur in PL/pgSQL-Funktionen (Laufzeit) verwendet.
ALTER TYPE auftragsstatus ADD VALUE IF NOT EXISTS 'zu_pruefen' AFTER 'anfrage';

CREATE TYPE prioritaet AS ENUM ('niedrig', 'normal', 'hoch', 'dringend');

ALTER TABLE auftraege
    ADD COLUMN prioritaet               prioritaet NOT NULL DEFAULT 'normal',
    ADD COLUMN geschaetzte_minuten      integer CHECK (geschaetzte_minuten >= 0),
    ADD COLUMN materialkosten_cent      integer NOT NULL DEFAULT 0 CHECK (materialkosten_cent >= 0),
    ADD COLUMN verkaufspreis_netto_cent integer CHECK (verkaufspreis_netto_cent >= 0),
    ADD COLUMN bemerkungen              text;

-- Erlaubte Statuswechsel (fachlicher Ablauf). Rücksprünge nur dort, wo sie sinnvoll sind.
CREATE FUNCTION auftrag_statuswechsel_pruefen() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE erlaubt text[];
BEGIN
    IF NEW.status = OLD.status THEN RETURN NEW; END IF;
    erlaubt := CASE OLD.status::text
        WHEN 'anfrage'     THEN ARRAY['zu_pruefen', 'angebot', 'bestaetigt', 'storniert']
        WHEN 'zu_pruefen'  THEN ARRAY['anfrage', 'angebot', 'bestaetigt', 'storniert']
        WHEN 'angebot'     THEN ARRAY['zu_pruefen', 'bestaetigt', 'storniert']
        WHEN 'bestaetigt'  THEN ARRAY['angebot', 'geplant', 'in_arbeit', 'storniert']
        WHEN 'geplant'     THEN ARRAY['bestaetigt', 'in_arbeit', 'erledigt', 'storniert']
        WHEN 'in_arbeit'   THEN ARRAY['geplant', 'erledigt']
        WHEN 'erledigt'    THEN ARRAY['in_arbeit', 'abgerechnet']
        WHEN 'abgerechnet' THEN ARRAY[]::text[]
        WHEN 'storniert'   THEN ARRAY['anfrage']
    END;
    IF NOT (NEW.status::text = ANY (erlaubt)) THEN
        RAISE EXCEPTION 'Statuswechsel % → % ist nicht erlaubt', OLD.status, NEW.status
            USING ERRCODE = 'check_violation';
    END IF;
    -- Abgerechnet nur mit (nicht stornierter) Rechnung zu diesem Auftrag
    IF NEW.status = 'abgerechnet' AND NOT EXISTS (
        SELECT 1 FROM rechnungen r WHERE r.auftrag_id = NEW.id AND r.status <> 'storniert') THEN
        RAISE EXCEPTION 'Auftrag % hat keine Rechnung – „abgerechnet“ nicht möglich', NEW.auftragsnummer
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.status = 'bestaetigt' AND NEW.bestaetigt_am IS NULL THEN
        NEW.bestaetigt_am := now();
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER auftraege_statuswechsel BEFORE UPDATE OF status ON auftraege
    FOR EACH ROW EXECUTE FUNCTION auftrag_statuswechsel_pruefen();

-- ---------------------------------------------------------------- Firmenparameter
-- Einstellbare Werte für Kalkulation, Einsatzgebiet und Kostenkontrolle (Änderungen im Audit-Log).
CREATE TABLE firmenparameter (
    schluessel      text PRIMARY KEY,
    wert            jsonb NOT NULL,
    beschreibung    text NOT NULL,
    geaendert_am    timestamptz NOT NULL DEFAULT now()
);
INSERT INTO firmenparameter (schluessel, wert, beschreibung) VALUES
  ('einsatzgebiet_zentrum',          '{"ort": "Gütersloh", "lat": 51.9069, "lon": 8.3786}', 'Mittelpunkt des Einsatzgebiets (Firmensitz)'),
  ('einsatzgebiet_radius_km',        '30',    'Einsatzgebiet: Umkreis in km (Luftlinie)'),
  ('lohnnebenkosten_prozent',        '32.8',  'Arbeitgeberanteile/Abgaben auf den Stundenlohn (Minijob-Pauschale ca. 32,8 %, laut Preiskalkulation)'),
  ('kalk_stundensatz_ohne_lohn_cent','2765',  'Kalkulatorischer Stundensatz für Personen ohne Stundenlohn (Inhaber: 36.000 € / 1.302 h)'),
  ('ziel_deckungsbeitrag_prozent',   '30',    'Ziel-Deckungsbeitrag je Auftrag in % vom Netto-Verkaufspreis (Warnschwelle)'),
  ('ki_tagesbudget_gesamt_cent',     '200',   'Harte Obergrenze KI-Kosten pro Tag über alle Agenten (Cent, USD-Preise 1:1 als Cent gerechnet)'),
  ('ki_aktiv',                       'true',  'Hauptschalter: KI-Aufrufe erlaubt (false = alle Agenten arbeiten nur regelbasiert)');

-- ---------------------------------------------------------------- Akquise: Leads
CREATE TYPE leadstatus     AS ENUM ('neu', 'qualifiziert', 'kontakt_geplant', 'kontaktiert', 'im_gespraech',
                                    'angebot', 'gewonnen', 'verloren', 'gesperrt');
CREATE TYPE leadprioritaet AS ENUM ('A', 'B', 'C');
CREATE TYPE zielgruppe     AS ENUM ('hausverwaltung', 'wohnungsunternehmen', 'gewerbeimmobilie', 'einzelhandel',
                                    'buero', 'investor', 'eigentuemer', 'unternehmen', 'partnernetz', 'privat', 'sonstige');
CREATE TYPE kontaktkanal   AS ENUM ('brief', 'telefon', 'email', 'kontaktformular', 'portal', 'persoenlich', 'linkedin');

CREATE TABLE leads (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    leadnummer              text NOT NULL UNIQUE DEFAULT naechste_nummer('LD', false),
    externe_ref             text UNIQUE,            -- z. B. 'L001' aus leads/leads.csv
    firma                   text NOT NULL,
    zielgruppe              zielgruppe NOT NULL,
    strasse                 text,
    plz                     text CHECK (plz ~ '^[0-9]{5}$'),
    ort                     text,
    entfernung_km           numeric(5,1) CHECK (entfernung_km >= 0),
    im_einsatzgebiet        boolean,                -- NULL = noch nicht geprüft
    webseite                text,
    telefon                 text,
    email                   citext,                 -- nur öffentliche Geschäftsadresse (Impressum)
    ansprechpartner         text,
    position                text,
    -- DSGVO: Herkunft jedes Leads ist Pflicht
    quelle                  text NOT NULL CHECK (length(trim(quelle)) > 0),
    objekte_geschaetzt      text,
    regelmaessiger_bedarf   boolean,
    geschaetzter_monatsumsatz_cent integer CHECK (geschaetzter_monatsumsatz_cent >= 0),
    leistungsinteresse      text[],
    score                   smallint CHECK (score BETWEEN 0 AND 100),
    prioritaet              leadprioritaet,
    score_begruendung       jsonb,
    status                  leadstatus NOT NULL DEFAULT 'neu',
    naechste_aktion         text,
    wiedervorlage_am        date,
    -- UWG § 7: Werbe-E-Mail nur mit Einwilligung (mit Nachweis) oder als Antwort auf eine öffentliche Einladung
    email_einwilligung      timestamptz,
    einwilligung_quelle     text,
    einladung_beleg         text,                   -- z. B. URL einer Partner-/Nachunternehmer-Seite
    widerspruch_am          timestamptz,            -- Werbewiderspruch: danach kein Werbekontakt mehr
    kunde_id                uuid REFERENCES kunden (id) ON DELETE SET NULL,
    hubspot_company_id      text UNIQUE,
    notizen                 text,
    erstellt_am             timestamptz NOT NULL DEFAULT now(),
    geaendert_am            timestamptz NOT NULL DEFAULT now(),
    CHECK (email_einwilligung IS NULL OR einwilligung_quelle IS NOT NULL),
    CHECK ((score IS NULL) = (prioritaet IS NULL)),
    CHECK (status <> 'gewonnen' OR kunde_id IS NOT NULL),
    CHECK (widerspruch_am IS NULL OR status IN ('gesperrt', 'gewonnen', 'verloren'))
);
CREATE UNIQUE INDEX leads_firma_plz_eindeutig ON leads (lower(regexp_replace(firma, '\s+', ' ', 'g')), coalesce(plz, ''));
CREATE INDEX leads_wiedervorlage ON leads (wiedervorlage_am) WHERE status NOT IN ('gewonnen', 'verloren', 'gesperrt');

CREATE TABLE lead_kontakte (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id         uuid NOT NULL REFERENCES leads (id) ON DELETE CASCADE,
    kanal           kontaktkanal NOT NULL,
    richtung        text NOT NULL CHECK (richtung IN ('ausgehend', 'eingehend')),
    zeitpunkt       timestamptz NOT NULL DEFAULT now(),
    zusammenfassung text NOT NULL,
    ergebnis        text,
    durch           text NOT NULL,              -- Benutzer-E-Mail oder 'agent:<code>'
    freigabe_id     uuid,                       -- FK unten (freigaben folgt)
    erstellt_am     timestamptz NOT NULL DEFAULT now()
);

-- Rechtsregeln für ausgehende Kontakte – greifen auch, wenn ein Programmteil Fehler macht
CREATE FUNCTION lead_kontakt_pruefen() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE l leads;
BEGIN
    IF NEW.richtung <> 'ausgehend' THEN RETURN NEW; END IF;
    SELECT * INTO l FROM leads WHERE id = NEW.lead_id;
    IF l.widerspruch_am IS NOT NULL AND NEW.zeitpunkt >= l.widerspruch_am THEN
        RAISE EXCEPTION 'Lead % hat der Kontaktaufnahme widersprochen', l.leadnummer USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.kanal = 'email' AND l.email_einwilligung IS NULL AND l.einladung_beleg IS NULL THEN
        RAISE EXCEPTION 'Werbe-E-Mail an % ohne Einwilligung oder Einladung (§ 7 UWG)', l.leadnummer
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.durch LIKE 'agent:%' AND NEW.freigabe_id IS NULL THEN
        RAISE EXCEPTION 'Agenten dürfen ausgehende Kontakte nur mit Freigabe protokollieren' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER lead_kontakte_pruefen BEFORE INSERT OR UPDATE ON lead_kontakte
    FOR EACH ROW EXECUTE FUNCTION lead_kontakt_pruefen();

-- ---------------------------------------------------------------- Agenten
CREATE TABLE agenten (
    code                    text PRIMARY KEY CHECK (code ~ '^[a-z][a-z_]{2,39}$'),
    name                    text NOT NULL,
    beschreibung            text NOT NULL,
    aktiv                   boolean NOT NULL DEFAULT true,
    modell                  text,                -- NULL = arbeitet nur regelbasiert
    tagesbudget_cent        integer NOT NULL DEFAULT 50 CHECK (tagesbudget_cent >= 0),
    max_schritte            smallint NOT NULL DEFAULT 8 CHECK (max_schritte BETWEEN 1 AND 50),
    max_laufzeit_sekunden   integer NOT NULL DEFAULT 120 CHECK (max_laufzeit_sekunden BETWEEN 5 AND 3600),
    max_versuche            smallint NOT NULL DEFAULT 3 CHECK (max_versuche BETWEEN 1 AND 10),
    erstellt_am             timestamptz NOT NULL DEFAULT now(),
    geaendert_am            timestamptz NOT NULL DEFAULT now()
);

CREATE TYPE agentenauftragsstatus AS ENUM ('wartend', 'laeuft', 'erledigt', 'fehlgeschlagen', 'abgebrochen', 'eskaliert');

CREATE TABLE agenten_auftraege (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent                   text NOT NULL REFERENCES agenten (code),
    aufgabe                 text NOT NULL CHECK (aufgabe ~ '^[a-z][a-z0-9_]{2,59}$'),
    eingabe                 jsonb NOT NULL DEFAULT '{}',
    ergebnis                jsonb,
    status                  agentenauftragsstatus NOT NULL DEFAULT 'wartend',
    prioritaet              smallint NOT NULL DEFAULT 5 CHECK (prioritaet BETWEEN 1 AND 9),   -- 1 = sehr dringend
    eltern_id               uuid REFERENCES agenten_auftraege (id) ON DELETE SET NULL,
    kette_id                uuid NOT NULL,       -- Wurzel der Delegationskette (per Trigger)
    tiefe                   smallint NOT NULL DEFAULT 0 CHECK (tiefe BETWEEN 0 AND 3),
    ausgeloest_von          text NOT NULL,       -- 'benutzer:<email>', 'agent:<code>', 'ereignis:<id>', 'zeitplan:<code>'
    idempotenz_schluessel   text UNIQUE,
    versuche                smallint NOT NULL DEFAULT 0 CHECK (versuche >= 0),
    max_versuche            smallint NOT NULL DEFAULT 3 CHECK (max_versuche BETWEEN 1 AND 10),
    faellig_ab              timestamptz NOT NULL DEFAULT now(),
    gesperrt_bis            timestamptz,         -- Arbeitsplatz-Sperre (Lease) des Workers
    gestartet_am            timestamptz,
    beendet_am              timestamptz,
    kosten_cent             numeric(10,4) NOT NULL DEFAULT 0,
    fehler                  text,
    erstellt_am             timestamptz NOT NULL DEFAULT now(),
    CHECK (versuche <= max_versuche),
    CHECK (status NOT IN ('erledigt', 'fehlgeschlagen', 'abgebrochen', 'eskaliert') OR beendet_am IS NOT NULL)
);
CREATE INDEX agenten_auftraege_warteschlange ON agenten_auftraege (prioritaet, faellig_ab) WHERE status = 'wartend';
CREATE INDEX agenten_auftraege_kette ON agenten_auftraege (kette_id);

-- Schleifenschutz: Tiefe begrenzt, kein Agent bekommt in derselben Kette dieselbe Aufgabe erneut,
-- höchstens 20 Aufträge je Kette.
CREATE FUNCTION agentenauftrag_kette_pruefen() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE e agenten_auftraege; anzahl integer;
BEGIN
    IF NEW.eltern_id IS NULL THEN
        NEW.kette_id := NEW.id;
        NEW.tiefe := 0;
        RETURN NEW;
    END IF;
    SELECT * INTO e FROM agenten_auftraege WHERE id = NEW.eltern_id;
    NEW.kette_id := e.kette_id;
    NEW.tiefe := e.tiefe + 1;          -- CHECK (tiefe <= 3) greift
    IF EXISTS (
        WITH RECURSIVE vorfahren AS (
            SELECT id, eltern_id, agent, aufgabe FROM agenten_auftraege WHERE id = NEW.eltern_id
            UNION ALL
            SELECT a.id, a.eltern_id, a.agent, a.aufgabe FROM agenten_auftraege a JOIN vorfahren v ON a.id = v.eltern_id
        ) SELECT 1 FROM vorfahren WHERE agent = NEW.agent AND aufgabe = NEW.aufgabe) THEN
        RAISE EXCEPTION 'Schleife erkannt: % / % kommt in der Kette schon vor', NEW.agent, NEW.aufgabe
            USING ERRCODE = 'check_violation';
    END IF;
    SELECT count(*) INTO anzahl FROM agenten_auftraege WHERE kette_id = NEW.kette_id;
    IF anzahl >= 20 THEN
        RAISE EXCEPTION 'Kette % hat bereits 20 Aufträge', NEW.kette_id USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER agenten_auftraege_kette BEFORE INSERT ON agenten_auftraege
    FOR EACH ROW EXECUTE FUNCTION agentenauftrag_kette_pruefen();

-- Lückenloses Protokoll je Agentenauftrag (nur anfügen)
CREATE TABLE agenten_protokoll (
    id              bigserial PRIMARY KEY,
    auftrag_id      uuid NOT NULL REFERENCES agenten_auftraege (id) ON DELETE CASCADE,
    art             text NOT NULL CHECK (art IN ('start', 'ki_aufruf', 'werkzeug', 'delegation', 'freigabe',
                                                 'ergebnis', 'fehler', 'eskalation', 'abbruch')),
    inhalt          jsonb NOT NULL DEFAULT '{}',
    zeitpunkt       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX agenten_protokoll_auftrag ON agenten_protokoll (auftrag_id, id);
CREATE FUNCTION nur_anfuegen() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION '% ist nur anfügbar', TG_TABLE_NAME USING ERRCODE = 'insufficient_privilege'; END $$;
CREATE TRIGGER agenten_protokoll_nur_anfuegen BEFORE UPDATE ON agenten_protokoll
    FOR EACH ROW EXECUTE FUNCTION nur_anfuegen();

-- KI-Aufrufe dem Agenten zuordnen (Budget je Agent und Tag)
ALTER TABLE ki_aufrufe
    ADD COLUMN agent              text REFERENCES agenten (code) ON DELETE SET NULL,
    ADD COLUMN agenten_auftrag_id uuid REFERENCES agenten_auftraege (id) ON DELETE SET NULL;
CREATE INDEX ki_aufrufe_tag ON ki_aufrufe (((erstellt_am AT TIME ZONE 'Europe/Berlin')::date), agent);

-- ---------------------------------------------------------------- Freigaben
CREATE TYPE freigabeart    AS ENUM ('email_versand', 'angebot_versand', 'lead_kontakt', 'social_beitrag',
                                    'einsatz_zuweisung', 'rechnung_entwurf', 'eskalation', 'sonstiges');
CREATE TYPE freigabestatus AS ENUM ('offen', 'freigegeben', 'abgelehnt', 'erledigt', 'abgelaufen');

CREATE TABLE freigaben (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    freigabenummer      text NOT NULL UNIQUE DEFAULT naechste_nummer('FG'),
    art                 freigabeart NOT NULL,
    titel               text NOT NULL,
    begruendung         text,
    vorschlag           jsonb NOT NULL DEFAULT '{}',   -- z. B. Mailtext, Positionen, Beitragstext
    bezug_tabelle       text,
    bezug_id            uuid,
    angefordert_von     text NOT NULL,                 -- 'agent:<code>' oder Benutzer-E-Mail
    agenten_auftrag_id  uuid REFERENCES agenten_auftraege (id) ON DELETE SET NULL,
    prioritaet          prioritaet NOT NULL DEFAULT 'normal',
    status              freigabestatus NOT NULL DEFAULT 'offen',
    entschieden_von     uuid REFERENCES benutzer (id),
    entschieden_am      timestamptz,
    kommentar           text,
    frist               date,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now(),
    -- Entscheidungen trifft immer ein Mensch
    CHECK (status NOT IN ('freigegeben', 'abgelehnt', 'erledigt') OR (entschieden_von IS NOT NULL AND entschieden_am IS NOT NULL))
);
CREATE UNIQUE INDEX freigabe_offen_eindeutig ON freigaben (art, bezug_tabelle, bezug_id)
    WHERE status = 'offen' AND bezug_id IS NOT NULL;
CREATE INDEX freigaben_offen ON freigaben (prioritaet, erstellt_am) WHERE status = 'offen';
ALTER TABLE lead_kontakte ADD FOREIGN KEY (freigabe_id) REFERENCES freigaben (id) ON DELETE SET NULL;

-- Eine Freigabe für einen Lead-Kontakt muss tatsächlich freigegeben sein
CREATE FUNCTION lead_kontakt_freigabe_pruefen() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.freigabe_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM freigaben WHERE id = NEW.freigabe_id AND status IN ('freigegeben', 'erledigt')) THEN
        RAISE EXCEPTION 'Freigabe ist nicht erteilt' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER lead_kontakte_freigabe BEFORE INSERT OR UPDATE ON lead_kontakte
    FOR EACH ROW EXECUTE FUNCTION lead_kontakt_freigabe_pruefen();

-- ---------------------------------------------------------------- Ereignisse (Outbox)
CREATE TABLE ereignisse (
    id                      bigserial PRIMARY KEY,
    typ                     text NOT NULL CHECK (typ ~ '^[a-z_]+\.[a-z_]+$'),   -- z. B. 'anfrage.neu'
    bezug_tabelle           text,
    bezug_id                uuid,
    daten                   jsonb NOT NULL DEFAULT '{}',
    idempotenz_schluessel   text UNIQUE,
    erstellt_am             timestamptz NOT NULL DEFAULT now(),
    verarbeitet_am          timestamptz,
    versuche                smallint NOT NULL DEFAULT 0,
    naechster_versuch       timestamptz NOT NULL DEFAULT now(),
    fehler                  text
);
CREATE INDEX ereignisse_offen ON ereignisse (naechster_versuch) WHERE verarbeitet_am IS NULL;

CREATE FUNCTION ereignis_ausloesen(p_typ text, p_tabelle text, p_id uuid, p_daten jsonb) RETURNS void
LANGUAGE sql AS $$
    INSERT INTO ereignisse (typ, bezug_tabelle, bezug_id, daten) VALUES (p_typ, p_tabelle, p_id, coalesce(p_daten, '{}'));
$$;

-- Fachtabellen melden Änderungen selbst – kein Programmteil kann das Ereignis „vergessen“
CREATE FUNCTION ereignisse_aus_fachdaten() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    CASE TG_TABLE_NAME
    WHEN 'anfragen' THEN
        IF TG_OP = 'INSERT' THEN PERFORM ereignis_ausloesen('anfrage.neu', 'anfragen', NEW.id, jsonb_build_object('kanal', NEW.kanal)); END IF;
    WHEN 'email_protokolle' THEN
        IF TG_OP = 'INSERT' AND NEW.richtung = 'eingang' THEN
            PERFORM ereignis_ausloesen('email.eingang', 'email_protokolle', NEW.id, jsonb_build_object('von', NEW.von::text));
        END IF;
    WHEN 'bewerbungen' THEN
        IF TG_OP = 'INSERT' THEN PERFORM ereignis_ausloesen('bewerbung.neu', 'bewerbungen', NEW.id, '{}'); END IF;
    WHEN 'leads' THEN
        IF TG_OP = 'INSERT' THEN PERFORM ereignis_ausloesen('lead.neu', 'leads', NEW.id, '{}'); END IF;
    WHEN 'auftraege' THEN
        IF TG_OP = 'UPDATE' AND NEW.status IS DISTINCT FROM OLD.status THEN
            PERFORM ereignis_ausloesen('auftrag.status', 'auftraege', NEW.id,
                jsonb_build_object('alt', OLD.status::text, 'neu', NEW.status::text));
        END IF;
    WHEN 'einsaetze' THEN
        IF TG_OP = 'UPDATE' AND NEW.status = 'erledigt' AND OLD.status IS DISTINCT FROM NEW.status THEN
            PERFORM ereignis_ausloesen('einsatz.erledigt', 'einsaetze', NEW.id, jsonb_build_object('auftrag_id', NEW.auftrag_id));
        END IF;
    WHEN 'angebote' THEN
        IF TG_OP = 'UPDATE' AND NEW.status IS DISTINCT FROM OLD.status THEN
            PERFORM ereignis_ausloesen('angebot.status', 'angebote', NEW.id,
                jsonb_build_object('alt', OLD.status::text, 'neu', NEW.status::text));
        END IF;
    WHEN 'rechnungen' THEN
        IF TG_OP = 'UPDATE' AND NEW.status IS DISTINCT FROM OLD.status THEN
            PERFORM ereignis_ausloesen('rechnung.status', 'rechnungen', NEW.id,
                jsonb_build_object('alt', OLD.status::text, 'neu', NEW.status::text));
        END IF;
    WHEN 'freigaben' THEN
        IF TG_OP = 'UPDATE' AND NEW.status IS DISTINCT FROM OLD.status AND NEW.status IN ('freigegeben', 'abgelehnt') THEN
            PERFORM ereignis_ausloesen('freigabe.entschieden', 'freigaben', NEW.id,
                jsonb_build_object('art', NEW.art::text, 'status', NEW.status::text));
        END IF;
    END CASE;
    RETURN NULL;
END $$;
DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['anfragen', 'email_protokolle', 'bewerbungen', 'leads', 'auftraege', 'einsaetze',
                             'angebote', 'rechnungen', 'freigaben']
    LOOP
        EXECUTE format('CREATE TRIGGER %I_ereignisse AFTER INSERT OR UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION ereignisse_aus_fachdaten()', t, t);
    END LOOP;
END $$;

-- ---------------------------------------------------------------- Automatisierungen
CREATE TABLE automatisierungen (
    code                text PRIMARY KEY CHECK (code ~ '^[a-z][a-z0-9_]{2,59}$'),
    name                text NOT NULL,
    beschreibung        text NOT NULL,
    ausloeser           text NOT NULL,           -- 'ereignis:anfrage.neu' oder 'zeitplan:taeglich 18:00'
    aktiv               boolean NOT NULL DEFAULT true,
    letzter_lauf        timestamptz,
    letzter_erfolg      timestamptz,
    fehler_in_folge     integer NOT NULL DEFAULT 0 CHECK (fehler_in_folge >= 0),
    letzter_fehler      text,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE automatisierungs_laeufe (
    id                  bigserial PRIMARY KEY,
    automatisierung     text NOT NULL REFERENCES automatisierungen (code) ON DELETE CASCADE,
    ereignis_id         bigint REFERENCES ereignisse (id) ON DELETE SET NULL,
    gestartet_am        timestamptz NOT NULL DEFAULT now(),
    beendet_am          timestamptz,
    erfolgreich         boolean,
    ergebnis            jsonb,
    fehler              text
);
CREATE INDEX automatisierungs_laeufe_neu ON automatisierungs_laeufe (automatisierung, gestartet_am DESC);
-- Ein Ereignis wird von einer Automatisierung höchstens einmal erfolgreich verarbeitet
CREATE UNIQUE INDEX automatisierung_ereignis_einmal ON automatisierungs_laeufe (automatisierung, ereignis_id)
    WHERE ereignis_id IS NOT NULL AND erfolgreich;

-- ---------------------------------------------------------------- Redaktionskalender
CREATE TYPE beitragsformat AS ENUM ('post', 'karussell', 'reel', 'story');
CREATE TYPE beitragsstatus AS ENUM ('idee', 'entwurf', 'zur_freigabe', 'freigegeben', 'veroeffentlicht', 'verworfen');

CREATE TABLE social_beitraege (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    plattform           text NOT NULL CHECK (plattform IN ('instagram', 'facebook', 'google')),
    format              beitragsformat NOT NULL,
    geplant_fuer        timestamptz NOT NULL,
    thema               text NOT NULL,
    text                text,
    hashtags            text[],
    bildidee            text,
    medien_pfad         text,                   -- Datei im Repository/Dateispeicher
    status              beitragsstatus NOT NULL DEFAULT 'idee',
    freigabe_id         uuid REFERENCES freigaben (id) ON DELETE SET NULL,
    freigegeben_von     uuid REFERENCES benutzer (id),
    freigegeben_am      timestamptz,
    veroeffentlicht_am  timestamptz,
    externe_id          text UNIQUE,            -- Medien-ID der Plattform
    kennzahlen          jsonb,                  -- Reichweite, Interaktionen … (Import)
    erstellt_von        text NOT NULL,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now(),
    CHECK (status NOT IN ('freigegeben', 'veroeffentlicht') OR (freigegeben_von IS NOT NULL AND freigegeben_am IS NOT NULL)),
    CHECK (status <> 'veroeffentlicht' OR veroeffentlicht_am IS NOT NULL)
);
CREATE UNIQUE INDEX social_beitrag_slot ON social_beitraege (plattform, format, geplant_fuer) WHERE status <> 'verworfen';

-- ---------------------------------------------------------------- Trigger geaendert_am + Audit für neue Tabellen
DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['firmenparameter', 'leads', 'agenten', 'freigaben', 'automatisierungen', 'social_beitraege']
    LOOP
        EXECUTE format('CREATE TRIGGER %I_geaendert BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION setze_geaendert()', t, t);
        EXECUTE format('CREATE TRIGGER %I_audit AFTER INSERT OR UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION protokolliere()', t, t);
    END LOOP;
    EXECUTE 'CREATE TRIGGER lead_kontakte_audit AFTER INSERT OR UPDATE OR DELETE ON lead_kontakte FOR EACH ROW EXECUTE FUNCTION protokolliere()';
END $$;
-- firmenparameter hat keine id-Spalte: Audit nutzt dann datensatz_id = NULL, der Schlüssel steht in alt/neu.

-- ---------------------------------------------------------------- Auswertungen
-- Wirtschaftlichkeit je Auftrag: Ist-Zeit aus Arbeitszeiten, Personalkosten aus Stundenlohn + Nebenkosten
CREATE VIEW v_auftrag_wirtschaftlichkeit AS
WITH p AS (
    SELECT (SELECT (wert #>> '{}')::numeric FROM firmenparameter WHERE schluessel = 'lohnnebenkosten_prozent') AS lnk,
           (SELECT (wert #>> '{}')::numeric FROM firmenparameter WHERE schluessel = 'kalk_stundensatz_ohne_lohn_cent') AS kalk
), zeiten AS (
    SELECT e.auftrag_id,
           sum(extract(epoch FROM (z.ende - z.beginn)) / 60 - z.pause_minuten) AS ist_minuten,
           sum((extract(epoch FROM (z.ende - z.beginn)) / 3600 - z.pause_minuten / 60.0)
               * CASE WHEN m.stundenlohn_cent IS NOT NULL THEN m.stundenlohn_cent * (1 + p.lnk / 100) ELSE p.kalk END) AS personal_cent
    FROM arbeitszeiten z
    JOIN einsaetze e ON e.id = z.einsatz_id
    JOIN mitarbeiter m ON m.id = z.mitarbeiter_id
    CROSS JOIN p
    WHERE z.ende IS NOT NULL
    GROUP BY e.auftrag_id
)
SELECT a.id AS auftrag_id, a.auftragsnummer, a.status, a.prioritaet,
       a.geschaetzte_minuten,
       round(coalesce(zeiten.ist_minuten, 0))::integer AS ist_minuten,
       round(coalesce(zeiten.personal_cent, 0))::integer AS personalkosten_cent,
       a.materialkosten_cent,
       a.verkaufspreis_netto_cent,
       CASE WHEN a.verkaufspreis_netto_cent IS NULL THEN NULL
            ELSE a.verkaufspreis_netto_cent - a.materialkosten_cent - round(coalesce(zeiten.personal_cent, 0))::integer END
           AS deckungsbeitrag_cent,
       CASE WHEN coalesce(a.verkaufspreis_netto_cent, 0) = 0 THEN NULL
            ELSE round(100.0 * (a.verkaufspreis_netto_cent - a.materialkosten_cent - coalesce(zeiten.personal_cent, 0))
                       / a.verkaufspreis_netto_cent, 1) END AS deckungsbeitrag_prozent
FROM auftraege a LEFT JOIN zeiten ON zeiten.auftrag_id = a.id;

-- Wiederkehrender Monatsumsatz aus gültigen Leistungsvereinbarungen.
-- Preis gilt je Ausführung; bei „saisonal“ je Saison (auf 12 Monate verteilt).
CREATE VIEW v_wiederkehrende_umsaetze AS
SELECT v.id AS vereinbarung_id, o.kunde_id, v.objekt_id, v.intervall,
       round(v.preis_netto_cent * v.menge * CASE v.intervall
            WHEN 'woechentlich' THEN 52 / 12.0
            WHEN 'zweiwoechentlich' THEN 26 / 12.0
            WHEN 'monatlich' THEN 1
            WHEN 'saisonal' THEN 1 / 12.0
            ELSE 0 END)::integer AS monatsumsatz_cent
FROM leistungsvereinbarungen v JOIN objekte o ON o.id = v.objekt_id
WHERE v.gueltig_von <= current_date AND (v.gueltig_bis IS NULL OR v.gueltig_bis >= current_date)
  AND v.intervall NOT IN ('einmalig', 'nach_bedarf');

-- KI-Kosten je Tag und Agent (Europe/Berlin)
CREATE VIEW v_ki_kosten_tag AS
SELECT (erstellt_am AT TIME ZONE 'Europe/Berlin')::date AS tag, agent,
       count(*) AS aufrufe, sum(coalesce(eingabe_tokens, 0)) AS eingabe_tokens,
       sum(coalesce(ausgabe_tokens, 0)) AS ausgabe_tokens, sum(coalesce(kosten_cent, 0)) AS kosten_cent,
       count(*) FILTER (WHERE NOT erfolgreich) AS fehler
FROM ki_aufrufe GROUP BY 1, 2;

REVOKE UPDATE, DELETE ON agenten_protokoll FROM PUBLIC;
