"""SQLite-Datenbank: Schema und Hilfsfunktionen."""
import os
import sqlite3

DB_PATH = os.environ.get("HAUSMANAGER_DB", os.path.join(os.path.dirname(__file__), "..", "data", "hausmanager.db"))

SCHEMA = """
-- ============ Modul 1: Eigene Immobilien ============
CREATE TABLE IF NOT EXISTS objekte (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    adresse TEXT,
    kaufpreis REAL DEFAULT 0,
    notiz TEXT
);
CREATE TABLE IF NOT EXISTS einheiten (
    id INTEGER PRIMARY KEY,
    objekt_id INTEGER NOT NULL REFERENCES objekte(id) ON DELETE CASCADE,
    bezeichnung TEXT NOT NULL,
    flaeche REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS mieter (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    telefon TEXT
);
CREATE TABLE IF NOT EXISTS vertraege (
    id INTEGER PRIMARY KEY,
    einheit_id INTEGER NOT NULL REFERENCES einheiten(id) ON DELETE CASCADE,
    mieter_id INTEGER NOT NULL REFERENCES mieter(id) ON DELETE CASCADE,
    beginn TEXT NOT NULL,             -- YYYY-MM-DD
    ende TEXT,                        -- leer = unbefristet
    kaltmiete REAL NOT NULL,
    nebenkosten REAL DEFAULT 0,
    kaution REAL DEFAULT 0,
    faellig_tag INTEGER DEFAULT 3,    -- Miete fällig bis zum x. Werktag/Tag
    letzte_erhoehung TEXT             -- Datum der letzten Mieterhöhung
);
-- Sollstellungen: pro Vertrag und Monat ein Eintrag (automatisch erzeugt)
CREATE TABLE IF NOT EXISTS sollstellungen (
    id INTEGER PRIMARY KEY,
    vertrag_id INTEGER NOT NULL REFERENCES vertraege(id) ON DELETE CASCADE,
    monat TEXT NOT NULL,              -- YYYY-MM
    betrag REAL NOT NULL,
    faellig_am TEXT NOT NULL,
    bezahlt REAL DEFAULT 0,
    mahnstufe INTEGER DEFAULT 0,
    UNIQUE(vertrag_id, monat)
);
CREATE TABLE IF NOT EXISTS zahlungen (
    id INTEGER PRIMARY KEY,
    vertrag_id INTEGER REFERENCES vertraege(id) ON DELETE SET NULL,
    datum TEXT NOT NULL,
    betrag REAL NOT NULL,
    verwendungszweck TEXT,
    auftraggeber TEXT,
    zugeordnet INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY,
    objekt_id INTEGER REFERENCES objekte(id) ON DELETE CASCADE,
    titel TEXT NOT NULL,
    beschreibung TEXT,
    prioritaet TEXT DEFAULT 'normal',
    status TEXT DEFAULT 'offen',
    erstellt TEXT DEFAULT (date('now'))
);
CREATE TABLE IF NOT EXISTS aufgaben (
    id INTEGER PRIMARY KEY,
    bereich TEXT NOT NULL,            -- immobilien | akquise
    schluessel TEXT UNIQUE,           -- verhindert Duplikate bei wiederholten Läufen
    titel TEXT NOT NULL,
    faellig TEXT,
    erledigt INTEGER DEFAULT 0,
    erstellt TEXT DEFAULT (date('now'))
);

-- ============ Modul 2: Hausmeister Helden – Akquise ============
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY,
    firma TEXT NOT NULL,
    ansprechpartner TEXT,
    anrede TEXT,                      -- 'Herr' | 'Frau' | ''
    email TEXT,
    telefon TEXT,
    strasse TEXT,
    plz_ort TEXT,
    typ TEXT DEFAULT 'Hausverwaltung',-- Hausverwaltung, WEG, Wohnungsbaugesellschaft, Gewerbe ...
    quelle TEXT,
    einwilligung_email INTEGER DEFAULT 0, -- nur dann darf automatisch gemailt werden (UWG §7)
    status TEXT DEFAULT 'neu',        -- neu, kontaktiert, interessiert, angebot, gewonnen, verloren, kein_interesse
    schritt INTEGER DEFAULT 0,        -- Position in der Kontaktsequenz
    naechster_kontakt TEXT,
    einheiten_geschaetzt INTEGER DEFAULT 0,
    notiz TEXT,
    erstellt TEXT DEFAULT (date('now'))
);
CREATE TABLE IF NOT EXISTS nachrichten (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    mieter_id INTEGER REFERENCES mieter(id) ON DELETE CASCADE,
    sollstellung_id INTEGER REFERENCES sollstellungen(id) ON DELETE CASCADE,
    kanal TEXT NOT NULL,              -- email | brief
    empfaenger TEXT,
    betreff TEXT,
    text TEXT,
    status TEXT DEFAULT 'entwurf',    -- entwurf | gesendet | gedruckt | verworfen
    erstellt TEXT DEFAULT (datetime('now')),
    gesendet TEXT
);
CREATE TABLE IF NOT EXISTS einstellungen (
    schluessel TEXT PRIMARY KEY,
    wert TEXT
);
"""

DEFAULT_SETTINGS = {
    "firma_name": "Hausmeister Helden",
    "firma_inhaber": "Martin Ogur",
    "firma_adresse": "Musterstraße 1, 12345 Musterstadt",
    "firma_telefon": "0123 456789",
    "firma_email": "info@hausmeister-helden.de",
    "firma_web": "www.hausmeister-helden.de",
    "einsatzgebiet": "Musterstadt und Umgebung",
    "vermieter_name": "Martin Ogur",
    "vermieter_iban": "DE00 0000 0000 0000 0000 00",
    "mahnung_tage_1": "7",
    "mahnung_tage_2": "21",
    "followup_tage": "7,14,30",
    "auto_senden": "0",  # 0 = nur Entwürfe, 1 = E-Mails automatisch senden (wenn SMTP konfiguriert)
}


def connect(path=None):
    path = path or DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init(con):
    con.executescript(SCHEMA)
    for k, v in DEFAULT_SETTINGS.items():
        con.execute("INSERT OR IGNORE INTO einstellungen(schluessel, wert) VALUES (?, ?)", (k, v))
    con.commit()


def settings(con):
    return {r["schluessel"]: r["wert"] for r in con.execute("SELECT * FROM einstellungen")}


def add_task(con, bereich, schluessel, titel, faellig=None):
    """Legt eine Aufgabe an, falls es sie (per Schlüssel) noch nicht gibt. Gibt True zurück, wenn neu."""
    cur = con.execute(
        "INSERT OR IGNORE INTO aufgaben(bereich, schluessel, titel, faellig) VALUES (?, ?, ?, ?)",
        (bereich, schluessel, titel, faellig),
    )
    return cur.rowcount > 0
