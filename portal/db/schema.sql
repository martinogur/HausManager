-- =============================================================================
-- Hausmeister Helden – Verwaltungsportal
-- Datenmodell (PostgreSQL 16) – Phase 1, Entwurf zur Freigabe
--
-- Grundsätze
--  * Jeder Datensatz hat eine UUID als Primärschlüssel (id) und – wo Menschen
--    darüber sprechen – zusätzlich eine lesbare Nummer (z. B. K-00012, AU-2026-0042).
--  * Dubletten werden per eindeutigem Index verhindert (normalisierte E-Mail,
--    Name+PLZ, Adresse, Message-ID, externe IDs von HubSpot/Lexware/Craftnote).
--  * Aufträge sind eindeutig Kunde + Objekt zugeordnet; ein Objekt kann nur einem
--    Kunden gehören (zusammengesetzter Fremdschlüssel verhindert falsche Zuordnung).
--  * Ausgehende E-Mails brauchen eine Freigabe (Datenbank-Regel, nicht nur App-Logik).
--  * Wichtige Änderungen landen automatisch im audit_log (Trigger).
--  * Geldbeträge in Cent (integer) – keine Rundungsfehler.
--  * Diese Datei ist die verbindliche Spezifikation. In Phase 2 wird sie in
--    Django-Migrationen übertragen; Tests prüfen, dass beide übereinstimmen.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;     -- Groß-/Kleinschreibung-unabhängige E-Mails
CREATE EXTENSION IF NOT EXISTS btree_gist; -- Überschneidungsprüfung bei Einsatzzeiten

CREATE SCHEMA IF NOT EXISTS hh;
SET search_path = hh, public;

-- ---------------------------------------------------------------- Aufzählungen
CREATE TYPE rolle            AS ENUM ('admin', 'buero', 'mitarbeiter');
CREATE TYPE kundentyp        AS ENUM ('hausverwaltung', 'weg', 'wohnungsunternehmen', 'gewerbe', 'privat', 'partner');
CREATE TYPE kundenstatus     AS ENUM ('interessent', 'aktiv', 'pausiert', 'beendet');
CREATE TYPE intervall        AS ENUM ('einmalig', 'woechentlich', 'zweiwoechentlich', 'monatlich', 'saisonal', 'nach_bedarf');
CREATE TYPE auftragsstatus   AS ENUM ('anfrage', 'angebot', 'bestaetigt', 'geplant', 'in_arbeit', 'erledigt', 'abgerechnet', 'storniert');
CREATE TYPE einsatzstatus    AS ENUM ('geplant', 'zugewiesen', 'in_arbeit', 'erledigt', 'ausgefallen');
CREATE TYPE beschaeftigung   AS ENUM ('inhaber', 'minijob', 'teilzeit', 'vollzeit', 'subunternehmer');
CREATE TYPE bewerbungsstatus AS ENUM ('eingegangen', 'gesichtet', 'gespraech', 'probearbeit', 'zusage', 'absage', 'zurueckgezogen');
CREATE TYPE angebotsstatus   AS ENUM ('entwurf', 'versendet', 'angenommen', 'abgelehnt', 'abgelaufen');
CREATE TYPE rechnungsstatus  AS ENUM ('entwurf', 'offen', 'bezahlt', 'ueberfaellig', 'storniert');
CREATE TYPE mailrichtung     AS ENUM ('eingang', 'ausgang');
CREATE TYPE mailstatus       AS ENUM ('neu', 'zugeordnet', 'entwurf', 'freigegeben', 'gesendet', 'verworfen', 'fehler');
CREATE TYPE anfragestatus    AS ENUM ('neu', 'in_bearbeitung', 'besichtigung', 'angebot', 'gewonnen', 'verloren');
CREATE TYPE fototyp          AS ENUM ('vorher', 'nachher', 'schaden', 'protokoll', 'sonstiges');

-- ---------------------------------------------------------------- Hilfsfunktionen
-- updated_at automatisch setzen
CREATE FUNCTION setze_geaendert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.geaendert_am := now(); RETURN NEW; END $$;

-- Laufende, lesbare Nummern (Präfix + Jahr + Zähler)
CREATE TABLE nummernkreise (
    kreis       text PRIMARY KEY,           -- z. B. 'AU-2026'
    letzte_nr   integer NOT NULL DEFAULT 0
);
CREATE FUNCTION naechste_nummer(praefix text, mit_jahr boolean DEFAULT true) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE k text; n integer;
BEGIN
    k := CASE WHEN mit_jahr THEN praefix || '-' || to_char(now(), 'YYYY') ELSE praefix END;
    INSERT INTO nummernkreise (kreis, letzte_nr) VALUES (k, 1)
        ON CONFLICT (kreis) DO UPDATE SET letzte_nr = nummernkreise.letzte_nr + 1
        RETURNING letzte_nr INTO n;
    RETURN k || '-' || lpad(n::text, CASE WHEN mit_jahr THEN 4 ELSE 5 END, '0');
END $$;

-- ---------------------------------------------------------------- Benutzer & Rollen
-- Anmeldung/Passwörter verwaltet das Framework (Django auth, Argon2). Hier nur die Zuordnung.
CREATE TABLE benutzer (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email           citext NOT NULL UNIQUE,
    anzeigename     text NOT NULL,
    rolle           rolle NOT NULL DEFAULT 'mitarbeiter',
    aktiv           boolean NOT NULL DEFAULT true,
    zwei_faktor     boolean NOT NULL DEFAULT false,
    erstellt_am     timestamptz NOT NULL DEFAULT now(),
    geaendert_am    timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- Kunden
CREATE TABLE kunden (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kundennummer        text NOT NULL UNIQUE DEFAULT naechste_nummer('K', false),
    name                text NOT NULL,
    typ                 kundentyp NOT NULL,
    status              kundenstatus NOT NULL DEFAULT 'interessent',
    strasse             text,
    plz                 text CHECK (plz ~ '^[0-9]{5}$'),
    ort                 text,
    telefon             text,
    email               citext,
    webseite            text,
    quelle              text,                -- z. B. 'Webseite', 'Brief L002', 'Empfehlung'
    notizen             text,
    hubspot_company_id  text UNIQUE,
    lexware_contact_id  uuid UNIQUE,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now()
);
-- Dublettenschutz: gleicher Name am gleichen Ort nur einmal
CREATE UNIQUE INDEX kunden_name_plz_eindeutig ON kunden (lower(regexp_replace(name, '\s+', ' ', 'g')), coalesce(plz, ''));

CREATE TABLE ansprechpartner (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kunde_id            uuid NOT NULL REFERENCES kunden (id) ON DELETE CASCADE,
    anrede              text,
    vorname             text,
    nachname            text NOT NULL,
    funktion            text,
    email               citext,
    telefon             text,
    mobil               text,
    ist_hauptkontakt    boolean NOT NULL DEFAULT false,
    email_einwilligung  timestamptz,         -- Nachweis für Werbe-E-Mails (§ 7 UWG); NULL = keine
    einwilligung_quelle text,                -- z. B. 'Telefonat 03.12.2026, Notiz MO'
    hubspot_contact_id  text UNIQUE,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now(),
    CHECK (email_einwilligung IS NULL OR einwilligung_quelle IS NOT NULL)
);
CREATE UNIQUE INDEX ansprechpartner_email_eindeutig ON ansprechpartner (email) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX ein_hauptkontakt_je_kunde ON ansprechpartner (kunde_id) WHERE ist_hauptkontakt;

-- ---------------------------------------------------------------- Objekte (Liegenschaften)
CREATE TABLE objekte (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    objektnummer        text NOT NULL UNIQUE DEFAULT naechste_nummer('OB', false),
    kunde_id            uuid NOT NULL REFERENCES kunden (id) ON DELETE RESTRICT,
    bezeichnung         text NOT NULL,       -- z. B. 'WEG Strengerstraße 10'
    strasse             text NOT NULL,
    hausnummer          text NOT NULL,
    plz                 text NOT NULL CHECK (plz ~ '^[0-9]{5}$'),
    ort                 text NOT NULL,
    wohneinheiten       smallint CHECK (wohneinheiten >= 0),
    gewerbeeinheiten    smallint CHECK (gewerbeeinheiten >= 0),
    treppenhaeuser      smallint CHECK (treppenhaeuser >= 0),
    etagen              smallint CHECK (etagen >= 0),
    aufzug              boolean NOT NULL DEFAULT false,
    gehweg_meter        numeric(6,1) CHECK (gehweg_meter >= 0),
    gruenflaeche_qm     numeric(8,1) CHECK (gruenflaeche_qm >= 0),
    zugang_hinweise     text,                -- Schlüssel, Codes NICHT hier speichern (siehe Doku)
    entfernung_km       numeric(5,1),
    craftnote_project_id text UNIQUE,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id, kunde_id)                    -- Ziel für zusammengesetzte Fremdschlüssel
);
CREATE UNIQUE INDEX objekte_adresse_eindeutig ON objekte (lower(strasse), lower(hausnummer), plz);

-- ---------------------------------------------------------------- Leistungen (Katalog)
CREATE TABLE leistungen (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code                text NOT NULL UNIQUE,   -- z. B. 'TH-REINIGUNG'
    name                text NOT NULL,
    einheit             text NOT NULL,          -- 'je Reinigung', 'je Etage', 'Std.', 'je lfm/Saison' …
    preis_netto_cent    integer NOT NULL CHECK (preis_netto_cent >= 0),
    ust_satz            numeric(4,2) NOT NULL DEFAULT 19.00,
    betriebskostenart   text,                   -- für Umlage: 'Gebäudereinigung', 'Gartenpflege', 'Hauswart', 'Winterdienst' …
    aktiv               boolean NOT NULL DEFAULT true,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now()
);

-- Vertraglich vereinbarte, wiederkehrende Leistungen je Objekt (Grundlage für Automatisierung D)
CREATE TABLE leistungsvereinbarungen (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    objekt_id           uuid NOT NULL REFERENCES objekte (id) ON DELETE CASCADE,
    leistung_id         uuid NOT NULL REFERENCES leistungen (id),
    intervall           intervall NOT NULL,
    wochentag           smallint CHECK (wochentag BETWEEN 1 AND 7),   -- 1 = Montag
    monatstag           smallint CHECK (monatstag BETWEEN 1 AND 28),
    menge               numeric(8,2) NOT NULL DEFAULT 1,
    preis_netto_cent    integer NOT NULL CHECK (preis_netto_cent >= 0),
    gueltig_von         date NOT NULL,
    gueltig_bis         date,
    saison_von_monat    smallint CHECK (saison_von_monat BETWEEN 1 AND 12),
    saison_bis_monat    smallint CHECK (saison_bis_monat BETWEEN 1 AND 12),
    standard_mitarbeiter_id uuid,           -- FK unten (Mitarbeiter-Tabelle folgt)
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now(),
    CHECK (gueltig_bis IS NULL OR gueltig_bis >= gueltig_von),
    CHECK (intervall <> 'woechentlich'     OR wochentag IS NOT NULL),
    CHECK (intervall <> 'zweiwoechentlich' OR wochentag IS NOT NULL),
    CHECK (intervall <> 'monatlich'        OR monatstag IS NOT NULL OR wochentag IS NOT NULL),
    CHECK (intervall <> 'saisonal' OR (saison_von_monat IS NOT NULL AND saison_bis_monat IS NOT NULL))
);

-- ---------------------------------------------------------------- Mitarbeiter
CREATE TABLE mitarbeiter (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    personalnummer      text NOT NULL UNIQUE DEFAULT naechste_nummer('MA', false),
    benutzer_id         uuid UNIQUE REFERENCES benutzer (id) ON DELETE SET NULL,
    vorname             text NOT NULL,
    nachname            text NOT NULL,
    email               citext UNIQUE,
    telefon             text,
    beschaeftigung      beschaeftigung NOT NULL,
    wochenstunden_soll  numeric(4,1) CHECK (wochenstunden_soll >= 0),
    stundenlohn_cent    integer CHECK (stundenlohn_cent >= 0),   -- nur Rolle admin sichtbar
    eintritt            date,
    austritt            date,
    fuehrerschein       boolean NOT NULL DEFAULT false,
    notizen             text,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now(),
    CHECK (austritt IS NULL OR eintritt IS NULL OR austritt >= eintritt)
);
ALTER TABLE leistungsvereinbarungen
    ADD FOREIGN KEY (standard_mitarbeiter_id) REFERENCES mitarbeiter (id) ON DELETE SET NULL;

CREATE TABLE qualifikationen (
    id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name    text NOT NULL UNIQUE                -- z. B. 'Winterdienst', 'Elektro-Kleinreparatur', 'Gartengeräte'
);
CREATE TABLE mitarbeiter_qualifikationen (
    mitarbeiter_id      uuid NOT NULL REFERENCES mitarbeiter (id) ON DELETE CASCADE,
    qualifikation_id    uuid NOT NULL REFERENCES qualifikationen (id) ON DELETE CASCADE,
    gueltig_bis         date,
    PRIMARY KEY (mitarbeiter_id, qualifikation_id)
);
-- Verfügbarkeit: wöchentliche Grundverfügbarkeit + Abwesenheiten
CREATE TABLE verfuegbarkeiten (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mitarbeiter_id      uuid NOT NULL REFERENCES mitarbeiter (id) ON DELETE CASCADE,
    wochentag           smallint NOT NULL CHECK (wochentag BETWEEN 1 AND 7),
    von                 time NOT NULL,
    bis                 time NOT NULL CHECK (bis > von)
);
CREATE TABLE abwesenheiten (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mitarbeiter_id      uuid NOT NULL REFERENCES mitarbeiter (id) ON DELETE CASCADE,
    von                 date NOT NULL,
    bis                 date NOT NULL CHECK (bis >= von),
    grund               text NOT NULL       -- 'Urlaub', 'krank', 'sonstiges' (keine Diagnosen!)
);

-- ---------------------------------------------------------------- Bewerbungen
CREATE TABLE stellen (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    titel               text NOT NULL,      -- 'Aushilfe Reinigung (Minijob)', 'Hausmeister Teilzeit'
    beschaeftigung      beschaeftigung NOT NULL,
    offen               boolean NOT NULL DEFAULT true,
    erstellt_am         timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE bewerbungen (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    bewerbungsnummer    text NOT NULL UNIQUE DEFAULT naechste_nummer('BW'),
    stelle_id           uuid NOT NULL REFERENCES stellen (id),
    vorname             text NOT NULL,
    nachname            text NOT NULL,
    email               citext NOT NULL,
    telefon             text,
    wohnort             text,
    verfuegbar_ab       date,
    stunden_pro_woche   numeric(4,1),
    fuehrerschein       boolean,
    erfahrung           text,
    nachricht           text,
    status              bewerbungsstatus NOT NULL DEFAULT 'eingegangen',
    ki_zusammenfassung  text,               -- nur Zusammenfassung, keine Bewertung/Entscheidung
    datenschutz_ok_am   timestamptz NOT NULL,   -- Einwilligung im Formular
    loeschen_ab         date NOT NULL DEFAULT (current_date + 180),  -- 6 Monate nach Eingang (AGG-Frist)
    eingegangen_am      timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now()
);
-- Gleiche Person kann sich nicht doppelt auf dieselbe offene Stelle bewerben
CREATE UNIQUE INDEX bewerbung_eindeutig ON bewerbungen (email, stelle_id)
    WHERE status NOT IN ('absage', 'zurueckgezogen');

-- ---------------------------------------------------------------- Anfragen (Leads aus E-Mail/Webseite/WhatsApp)
CREATE TABLE anfragen (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    anfragenummer       text NOT NULL UNIQUE DEFAULT naechste_nummer('AN'),
    kunde_id            uuid REFERENCES kunden (id) ON DELETE SET NULL,
    ansprechpartner_id  uuid REFERENCES ansprechpartner (id) ON DELETE SET NULL,
    objekt_id           uuid REFERENCES objekte (id) ON DELETE SET NULL,
    kanal               text NOT NULL,      -- 'email', 'webseite', 'whatsapp', 'telefon', 'brief'
    betreff             text,
    gewuenschte_leistungen text[],
    ki_zusammenfassung  text,
    fehlende_angaben    text[],             -- von der KI erkannt, z. B. {'Adresse', 'Etagenzahl'}
    status              anfragestatus NOT NULL DEFAULT 'neu',
    hubspot_deal_id     text UNIQUE,
    eingegangen_am      timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- Angebote
CREATE TABLE angebote (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    angebotsnummer      text NOT NULL UNIQUE DEFAULT naechste_nummer('AG'),
    kunde_id            uuid NOT NULL,
    objekt_id           uuid NOT NULL,
    anfrage_id          uuid REFERENCES anfragen (id) ON DELETE SET NULL,
    status              angebotsstatus NOT NULL DEFAULT 'entwurf',
    gueltig_bis         date,
    laufzeit_monate     smallint,
    summe_netto_cent    integer NOT NULL DEFAULT 0,   -- per Trigger aus Positionen
    freigegeben_von     uuid REFERENCES benutzer (id),
    freigegeben_am      timestamptz,
    versendet_am        timestamptz,
    lexware_quotation_id uuid UNIQUE,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (objekt_id, kunde_id) REFERENCES objekte (id, kunde_id),
    -- Preise entscheidet der Inhaber: kein Versand ohne Freigabe
    CHECK (status IN ('entwurf') OR freigegeben_am IS NOT NULL)
);
CREATE TABLE angebotspositionen (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    angebot_id          uuid NOT NULL REFERENCES angebote (id) ON DELETE CASCADE,
    pos                 smallint NOT NULL,
    leistung_id         uuid REFERENCES leistungen (id),
    beschreibung        text NOT NULL,
    menge               numeric(10,2) NOT NULL CHECK (menge > 0),
    einheit             text NOT NULL,
    einzelpreis_netto_cent integer NOT NULL CHECK (einzelpreis_netto_cent >= 0),
    intervall           intervall NOT NULL DEFAULT 'einmalig',
    UNIQUE (angebot_id, pos)
);
CREATE FUNCTION angebot_summe() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE aid uuid := coalesce(NEW.angebot_id, OLD.angebot_id);
BEGIN
    UPDATE angebote SET summe_netto_cent = coalesce((
        SELECT round(sum(menge * einzelpreis_netto_cent))::integer FROM angebotspositionen WHERE angebot_id = aid), 0)
    WHERE id = aid;
    RETURN NULL;
END $$;
CREATE TRIGGER angebotspositionen_summe AFTER INSERT OR UPDATE OR DELETE ON angebotspositionen
    FOR EACH ROW EXECUTE FUNCTION angebot_summe();

-- ---------------------------------------------------------------- Aufträge & Einsätze
CREATE TABLE auftraege (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    auftragsnummer      text NOT NULL UNIQUE DEFAULT naechste_nummer('AU'),
    kunde_id            uuid NOT NULL,
    objekt_id           uuid NOT NULL,
    angebot_id          uuid UNIQUE REFERENCES angebote (id),
    leistungsvereinbarung_id uuid REFERENCES leistungsvereinbarungen (id) ON DELETE SET NULL,
    titel               text NOT NULL,
    beschreibung        text,
    status              auftragsstatus NOT NULL DEFAULT 'bestaetigt',
    bestaetigt_am       timestamptz,
    faellig_am          date,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now(),
    -- Objekt muss zum Kunden gehören
    FOREIGN KEY (objekt_id, kunde_id) REFERENCES objekte (id, kunde_id)
);
CREATE INDEX auftraege_status ON auftraege (status);

CREATE TABLE einsaetze (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    auftrag_id          uuid NOT NULL REFERENCES auftraege (id) ON DELETE CASCADE,
    geplant_von         timestamptz NOT NULL,
    geplant_bis         timestamptz NOT NULL,
    status              einsatzstatus NOT NULL DEFAULT 'geplant',
    erzeugt_aus         uuid REFERENCES leistungsvereinbarungen (id) ON DELETE SET NULL,
    notiz_buero         text,
    bericht_mitarbeiter text,
    ki_auswertung       text,
    craftnote_task_id   text UNIQUE,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now(),
    CHECK (geplant_bis > geplant_von)
);
-- Wiederkehrende Arbeiten nicht doppelt erzeugen: je Vereinbarung höchstens ein Einsatz pro Tag
CREATE UNIQUE INDEX einsatz_aus_vereinbarung_eindeutig
    ON einsaetze (erzeugt_aus, ((geplant_von AT TIME ZONE 'Europe/Berlin')::date)) WHERE erzeugt_aus IS NOT NULL;
CREATE INDEX einsaetze_zeitraum ON einsaetze USING gist (tstzrange(geplant_von, geplant_bis));

CREATE TABLE einsatz_mitarbeiter (
    einsatz_id          uuid NOT NULL REFERENCES einsaetze (id) ON DELETE CASCADE,
    mitarbeiter_id      uuid NOT NULL REFERENCES mitarbeiter (id) ON DELETE RESTRICT,
    zeitraum            tstzrange NOT NULL,   -- Kopie aus dem Einsatz für die Überschneidungsprüfung
    PRIMARY KEY (einsatz_id, mitarbeiter_id),
    -- Niemand kann gleichzeitig an zwei Einsätzen sein
    EXCLUDE USING gist (mitarbeiter_id WITH =, zeitraum WITH &&)
);

-- ---------------------------------------------------------------- Arbeitszeiten & Nachweise
CREATE TABLE arbeitszeiten (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mitarbeiter_id      uuid NOT NULL REFERENCES mitarbeiter (id) ON DELETE RESTRICT,
    einsatz_id          uuid REFERENCES einsaetze (id) ON DELETE SET NULL,
    beginn              timestamptz NOT NULL,
    ende                timestamptz,
    pause_minuten       smallint NOT NULL DEFAULT 0 CHECK (pause_minuten >= 0),
    taetigkeit          text,
    bestaetigt_von      uuid REFERENCES benutzer (id),
    bestaetigt_am       timestamptz,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now(),
    CHECK (ende IS NULL OR ende > beginn),
    CHECK (ende IS NULL OR pause_minuten * interval '1 minute' < ende - beginn),
    -- Keine doppelten/überlappenden Zeitbuchungen einer Person
    EXCLUDE USING gist (mitarbeiter_id WITH =, tstzrange(beginn, coalesce(ende, 'infinity')) WITH &&)
);

-- ---------------------------------------------------------------- Dokumente & Fotos
CREATE TABLE dokumente (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dateiname           text NOT NULL,
    mime_typ            text NOT NULL,
    groesse_bytes       bigint NOT NULL CHECK (groesse_bytes > 0),
    sha256              text NOT NULL,      -- Inhalt-Prüfsumme gegen doppelte Uploads
    speicher_schluessel text NOT NULL UNIQUE,   -- Pfad im verschlüsselten Dateispeicher
    kategorie           text NOT NULL,      -- 'vertrag', 'angebot', 'rechnung', 'foto', 'bewerbung', 'nachweis' …
    kunde_id            uuid REFERENCES kunden (id) ON DELETE CASCADE,
    objekt_id           uuid REFERENCES objekte (id) ON DELETE CASCADE,
    auftrag_id          uuid REFERENCES auftraege (id) ON DELETE CASCADE,
    einsatz_id          uuid REFERENCES einsaetze (id) ON DELETE CASCADE,
    mitarbeiter_id      uuid REFERENCES mitarbeiter (id) ON DELETE CASCADE,
    bewerbung_id        uuid REFERENCES bewerbungen (id) ON DELETE CASCADE,
    hochgeladen_von     uuid REFERENCES benutzer (id),
    loeschen_ab         date,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    CHECK (num_nonnulls(kunde_id, objekt_id, auftrag_id, einsatz_id, mitarbeiter_id, bewerbung_id) >= 1)
);
CREATE UNIQUE INDEX dokument_inhalt_eindeutig ON dokumente (sha256, coalesce(einsatz_id, objekt_id, auftrag_id, kunde_id, mitarbeiter_id, bewerbung_id));

CREATE TABLE fotos (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dokument_id         uuid NOT NULL UNIQUE REFERENCES dokumente (id) ON DELETE CASCADE,
    einsatz_id          uuid NOT NULL REFERENCES einsaetze (id) ON DELETE CASCADE,
    typ                 fototyp NOT NULL,
    aufgenommen_am      timestamptz,
    beschreibung        text
);

-- ---------------------------------------------------------------- Rechnungen (Spiegel aus Lexware Office)
CREATE TABLE rechnungen (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kunde_id            uuid NOT NULL REFERENCES kunden (id) ON DELETE RESTRICT,
    auftrag_id          uuid REFERENCES auftraege (id) ON DELETE SET NULL,
    lexware_invoice_id  uuid UNIQUE,        -- NULL, solange nur im Portal vorbereitet
    rechnungsnummer     text UNIQUE,        -- vergibt Lexware beim Festschreiben
    status              rechnungsstatus NOT NULL DEFAULT 'entwurf',
    rechnungsdatum      date,
    faellig_am          date,
    summe_netto_cent    integer NOT NULL CHECK (summe_netto_cent >= 0),
    summe_brutto_cent   integer NOT NULL CHECK (summe_brutto_cent >= summe_netto_cent),
    bezahlt_am          date,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now(),
    CHECK (status <> 'bezahlt' OR bezahlt_am IS NOT NULL)
);
-- Ein Auftrag wird nur einmal abgerechnet (Storno ausgenommen)
CREATE UNIQUE INDEX rechnung_je_auftrag ON rechnungen (auftrag_id) WHERE auftrag_id IS NOT NULL AND status <> 'storniert';

-- ---------------------------------------------------------------- E-Mail-Protokoll
CREATE TABLE email_protokolle (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    richtung            mailrichtung NOT NULL,
    message_id          text,               -- RFC-5322 Message-ID: verhindert Doppelimport
    in_reply_to         text,
    postfach            text NOT NULL,      -- 'info@haus-meister-helden.de'
    von                 citext NOT NULL,
    an                  citext[] NOT NULL,
    betreff             text,
    text_auszug         text,               -- gekürzt; Volltext + Anhänge als Dokument
    empfangen_am        timestamptz,
    status              mailstatus NOT NULL DEFAULT 'neu',
    kunde_id            uuid REFERENCES kunden (id) ON DELETE SET NULL,
    ansprechpartner_id  uuid REFERENCES ansprechpartner (id) ON DELETE SET NULL,
    anfrage_id          uuid REFERENCES anfragen (id) ON DELETE SET NULL,
    bewerbung_id        uuid REFERENCES bewerbungen (id) ON DELETE SET NULL,
    antwort_auf_id      uuid REFERENCES email_protokolle (id) ON DELETE SET NULL,
    ki_zusammenfassung  text,
    entwurf_text        text,               -- KI-Antwortentwurf (nur Vorschlag)
    freigegeben_von     uuid REFERENCES benutzer (id),
    freigegeben_am      timestamptz,
    gesendet_am         timestamptz,
    fehler              text,
    erstellt_am         timestamptz NOT NULL DEFAULT now(),
    geaendert_am        timestamptz NOT NULL DEFAULT now(),
    -- Ausgehende Mails dürfen nur nach manueller Freigabe gesendet werden
    CHECK (richtung = 'eingang' OR status NOT IN ('freigegeben', 'gesendet') OR (freigegeben_von IS NOT NULL AND freigegeben_am IS NOT NULL)),
    CHECK (status <> 'gesendet' OR gesendet_am IS NOT NULL)
);
CREATE UNIQUE INDEX email_message_id_eindeutig ON email_protokolle (postfach, message_id) WHERE message_id IS NOT NULL;
CREATE INDEX email_offen ON email_protokolle (status) WHERE status IN ('neu', 'entwurf');

-- ---------------------------------------------------------------- KI-Protokoll (Transparenz & Kosten)
CREATE TABLE ki_aufrufe (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    zweck               text NOT NULL,      -- 'anfrage_zusammenfassen', 'antwort_entwurf', 'bewerbung_zusammenfassen', 'wochenbericht' …
    modell              text NOT NULL,
    bezug_tabelle       text,
    bezug_id            uuid,
    eingabe_tokens      integer,
    ausgabe_tokens      integer,
    kosten_cent         numeric(10,4),
    erfolgreich         boolean NOT NULL,
    fehler              text,
    erstellt_am         timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- Integrations-Protokoll (HubSpot, Make, Craftnote, Lexware)
CREATE TABLE sync_protokoll (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    system              text NOT NULL CHECK (system IN ('hubspot', 'make', 'craftnote', 'lexware', 'ionos')),
    richtung            text NOT NULL CHECK (richtung IN ('import', 'export')),
    objekt_typ          text NOT NULL,
    lokale_id           uuid,
    externe_id          text,
    idempotenz_schluessel text UNIQUE,      -- verhindert doppelte Übertragung bei Wiederholung
    erfolgreich         boolean NOT NULL,
    http_status         smallint,
    fehler              text,
    erstellt_am         timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- Änderungsprotokoll (Audit)
CREATE TABLE audit_log (
    id                  bigserial PRIMARY KEY,
    tabelle             text NOT NULL,
    datensatz_id        uuid,
    aktion              text NOT NULL CHECK (aktion IN ('INSERT', 'UPDATE', 'DELETE')),
    alt                 jsonb,
    neu                 jsonb,
    benutzer            text,               -- aus current_setting('app.benutzer'), von der App gesetzt
    zeitpunkt           timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_datensatz ON audit_log (tabelle, datensatz_id);

CREATE FUNCTION protokolliere() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE alt jsonb; neu jsonb;
BEGIN
    IF TG_OP <> 'INSERT' THEN alt := to_jsonb(OLD) - 'geaendert_am'; END IF;
    IF TG_OP <> 'DELETE' THEN neu := to_jsonb(NEW) - 'geaendert_am'; END IF;
    IF TG_OP = 'UPDATE' AND alt = neu THEN RETURN NULL; END IF;
    INSERT INTO audit_log (tabelle, datensatz_id, aktion, alt, neu, benutzer)
    VALUES (TG_TABLE_NAME, coalesce((neu->>'id')::uuid, (alt->>'id')::uuid), TG_OP, alt, neu,
            nullif(current_setting('app.benutzer', true), ''));
    RETURN NULL;
END $$;

-- Trigger für geaendert_am und Audit auf allen Fachtabellen
DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['benutzer','kunden','ansprechpartner','objekte','leistungen','leistungsvereinbarungen',
                             'mitarbeiter','bewerbungen','anfragen','angebote','auftraege','einsaetze','arbeitszeiten',
                             'rechnungen','email_protokolle']
    LOOP
        EXECUTE format('CREATE TRIGGER %I_geaendert BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION setze_geaendert()', t, t);
        EXECUTE format('CREATE TRIGGER %I_audit AFTER INSERT OR UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION protokolliere()', t, t);
    END LOOP;
    FOREACH t IN ARRAY ARRAY['dokumente','fotos','angebotspositionen','einsatz_mitarbeiter']
    LOOP
        EXECUTE format('CREATE TRIGGER %I_audit AFTER INSERT OR UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION protokolliere()', t, t);
    END LOOP;
END $$;

-- Zeitraum der Mitarbeiterzuweisung immer aus dem Einsatz übernehmen
CREATE FUNCTION einsatz_zeitraum_uebernehmen() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    SELECT tstzrange(geplant_von, geplant_bis) INTO NEW.zeitraum FROM einsaetze WHERE id = NEW.einsatz_id;
    RETURN NEW;
END $$;
CREATE TRIGGER einsatz_mitarbeiter_zeitraum BEFORE INSERT OR UPDATE ON einsatz_mitarbeiter
    FOR EACH ROW EXECUTE FUNCTION einsatz_zeitraum_uebernehmen();
CREATE FUNCTION einsatz_zeitraum_weitergeben() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.geplant_von, NEW.geplant_bis) IS DISTINCT FROM (OLD.geplant_von, OLD.geplant_bis) THEN
        UPDATE einsatz_mitarbeiter SET zeitraum = tstzrange(NEW.geplant_von, NEW.geplant_bis) WHERE einsatz_id = NEW.id;
    END IF;
    RETURN NULL;
END $$;
CREATE TRIGGER einsaetze_zeitraum_weitergeben AFTER UPDATE ON einsaetze
    FOR EACH ROW EXECUTE FUNCTION einsatz_zeitraum_weitergeben();

-- ---------------------------------------------------------------- Auswertungen (Views)
CREATE VIEW v_umsatz_monat AS
SELECT date_trunc('month', rechnungsdatum)::date AS monat,
       count(*) AS rechnungen,
       sum(summe_netto_cent) / 100.0 AS umsatz_netto_eur,
       sum(summe_netto_cent) FILTER (WHERE status = 'bezahlt') / 100.0 AS bezahlt_netto_eur
FROM rechnungen WHERE status <> 'storniert' AND rechnungsdatum IS NOT NULL
GROUP BY 1;

CREATE VIEW v_arbeitsstunden_woche AS
SELECT m.id AS mitarbeiter_id, m.vorname || ' ' || m.nachname AS mitarbeiter,
       date_trunc('week', a.beginn AT TIME ZONE 'Europe/Berlin')::date AS woche,
       round(sum(extract(epoch FROM (a.ende - a.beginn)) / 3600 - a.pause_minuten / 60.0)::numeric, 2) AS stunden
FROM arbeitszeiten a JOIN mitarbeiter m ON m.id = a.mitarbeiter_id
WHERE a.ende IS NOT NULL
GROUP BY 1, 2, 3;

CREATE VIEW v_offene_angebote AS
SELECT g.angebotsnummer, k.name AS kunde, o.bezeichnung AS objekt, g.status, g.summe_netto_cent / 100.0 AS netto_eur, g.gueltig_bis
FROM angebote g JOIN kunden k ON k.id = g.kunde_id JOIN objekte o ON o.id = g.objekt_id
WHERE g.status IN ('entwurf', 'versendet');

-- ---------------------------------------------------------------- Rechte (Datenbankebene)
-- Die App verbindet sich mit einer eigenen Rolle ohne Superuser-Rechte; das Audit-Log ist nur anfügbar.
-- (Rollen werden im Deployment angelegt; hier die Regeln.)
REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC;
