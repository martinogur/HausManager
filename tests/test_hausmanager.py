import datetime as dt
import io

import pytest

from hausmanager import app as webapp
from hausmanager import automation, db


@pytest.fixture
def con(tmp_path):
    c = db.connect(str(tmp_path / "t.db"))
    db.init(c)
    yield c
    c.close()


def _vertrag(c, name="Max Mustermann", email="max@example.com", beginn="2026-09-01", miete=800, nk=150):
    c.execute("INSERT INTO objekte(name, kaufpreis) VALUES ('MFH Linden', 300000)")
    c.execute("INSERT INTO einheiten(objekt_id, bezeichnung) VALUES (1, 'EG links')")
    c.execute("INSERT INTO mieter(name, email) VALUES (?, ?)", (name, email))
    c.execute("INSERT INTO vertraege(einheit_id, mieter_id, beginn, kaltmiete, nebenkosten) VALUES (1, 1, ?, ?, ?)", (beginn, miete, nk))
    c.commit()


def test_sollstellung_zuordnung_und_mahnung(con):
    _vertrag(con)
    heute = dt.date(2026, 11, 20)
    automation.alles(con, heute)
    assert con.execute("SELECT COUNT(*) FROM sollstellungen").fetchone()[0] == 3  # Sep, Okt, Nov
    # September + Oktober über Bank bezahlt, November offen
    con.execute("INSERT INTO zahlungen(datum, betrag, verwendungszweck, auftraggeber) VALUES ('2026-10-01', 1900, 'Miete', 'MUSTERMANN, MAX')")
    con.commit()
    bericht = automation.alles(con, heute)
    assert bericht["Zahlungen automatisch zugeordnet"] == 1
    offen = con.execute("SELECT monat, betrag - bezahlt AS o, mahnstufe FROM sollstellungen WHERE betrag - bezahlt > 0.01").fetchall()
    assert [(r["monat"], r["o"]) for r in offen] == [("2026-11", 950)]
    # Nov fällig am 3., heute 20. -> 17 Tage Verzug -> Stufe 1
    assert offen[0]["mahnstufe"] == 1
    # Erinnerungen für die inzwischen bezahlten Monate wurden automatisch verworfen
    n = con.execute("SELECT * FROM nachrichten WHERE mieter_id = 1 AND status = 'entwurf'").fetchall()
    assert len(n) == 1 and n[0]["kanal"] == "email" and "950,00" in n[0]["text"]
    # erneuter Lauf erzeugt nichts doppelt; später Stufe 2
    automation.alles(con, heute)
    assert con.execute("SELECT COUNT(*) FROM nachrichten WHERE status = 'entwurf'").fetchone()[0] == 1
    automation.alles(con, dt.date(2026, 11, 25))
    assert con.execute("SELECT COUNT(*) FROM nachrichten WHERE status = 'entwurf'").fetchone()[0] == 2


def test_rueckstand_zwei_monate_erzeugt_warnung(con):
    _vertrag(con)
    automation.alles(con, dt.date(2026, 11, 20))
    titel = [r["titel"] for r in con.execute("SELECT titel FROM aufgaben")]
    assert any("2 Monatsmieten" in t for t in titel)


def test_mieterhoehung_frist(con):
    _vertrag(con, beginn="2025-01-01")
    automation.alles(con, dt.date(2026, 3, 10))
    assert any("Mieterhöhung" in r["titel"] for r in con.execute("SELECT titel FROM aufgaben"))


def test_akquise_sequenz_brief_ohne_einwilligung_email_mit(con):
    con.execute("INSERT INTO leads(firma, anrede, ansprechpartner, strasse, plz_ort, telefon, email) VALUES ('HV Nord', 'Frau', 'Anna Beispiel', 'Weg 1', '12345 Stadt', '0123', 'a@hv.example')")
    con.execute("INSERT INTO leads(firma, email, einwilligung_email) VALUES ('HV Süd', 'info@sued.example', 1)")
    con.execute("INSERT INTO leads(firma) VALUES ('HV ohne Adresse')")
    con.commit()
    heute = dt.date(2026, 11, 19)
    automation.alles(con, heute)
    msgs = {r["lead_id"]: r for r in con.execute("SELECT * FROM nachrichten")}
    assert msgs[1]["kanal"] == "brief" and "Sehr geehrte Frau Beispiel" in msgs[1]["text"]
    assert msgs[2]["kanal"] == "email" and "Abmelden" in msgs[2]["text"]
    assert 3 not in msgs
    assert any("Postadresse" in r["titel"] for r in con.execute("SELECT titel FROM aufgaben"))
    assert any("Anrufen" in r["titel"] for r in con.execute("SELECT titel FROM aufgaben"))
    # Nachfassen erst nach 7 Tagen, dann Schritt 3 nach weiteren 14
    automation.alles(con, heute + dt.timedelta(days=3))
    assert con.execute("SELECT COUNT(*) FROM nachrichten").fetchone()[0] == 2
    automation.alles(con, heute + dt.timedelta(days=7))
    automation.alles(con, heute + dt.timedelta(days=21))
    assert con.execute("SELECT schritt FROM leads WHERE id = 1").fetchone()[0] == 3
    assert con.execute("SELECT COUNT(*) FROM nachrichten WHERE lead_id = 1").fetchone()[0] == 3
    # Reaktion stoppt Sequenz
    con.execute("UPDATE leads SET status='interessiert' WHERE id = 2")
    con.commit()
    automation.alles(con, heute + dt.timedelta(days=60))
    assert con.execute("SELECT COUNT(*) FROM nachrichten WHERE lead_id = 2").fetchone()[0] == 3


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORT", raising=False)
    webapp.app.config.update(TESTING=True, DB_PATH=str(tmp_path / "w.db"))
    return webapp.app.test_client()


def test_web_seiten_und_ablauf(client):
    for url in ["/", "/immobilien", "/zahlungen", "/tickets", "/akquise", "/postausgang", "/einstellungen", "/helden"]:
        assert client.get(url).status_code == 200, url
    client.post("/objekt/neu", data={"name": "MFH", "kaufpreis": "250.000"})
    client.post("/einheit/neu", data={"objekt_id": "1", "bezeichnung": "OG"})
    r = client.post("/vertrag/neu", data={"einheit_id": "1", "name": "Erika Muster", "beginn": "2026-01-01", "kaltmiete": "700", "nebenkosten": "100"}, follow_redirects=True)
    assert "Erika Muster" in r.get_data(as_text=True)
    csv = "Buchungstag;Auftraggeber;Verwendungszweck;Betrag\n01.02.2026;Erika Muster;Miete;1.600,00\n".encode()
    r = client.post("/zahlungen/import", data={"datei": (io.BytesIO(csv), "k.csv")}, content_type="multipart/form-data", follow_redirects=True)
    assert "1 Zahlungseingänge importiert, 1 automatisch zugeordnet" in r.get_data(as_text=True)
    leads = "firma;ansprechpartner;anrede;strasse;plz_ort\nHV Test;Paul Probe;Herr;Str 1;11111 Ort\n".encode()
    client.post("/leads/import", data={"datei": (io.BytesIO(leads), "l.csv")}, content_type="multipart/form-data")
    client.post("/automatik")
    r = client.get("/briefe/druck")
    assert "Sehr geehrter Herr Probe" in r.get_data(as_text=True)
    assert client.get("/lead/1/angebot").status_code == 200
    r = client.post("/lead/1/angebot", data={"positionen": "Reinigung;2;100", "drucken": "1"})
    assert "238,00" in r.get_data(as_text=True)


def test_anfrage_formular(client):
    r = client.post("/anfrage", data={"ansprechpartner": "Frau Test", "telefon": "0123", "email": "t@example.com", "nachricht": "3 Häuser"})
    assert r.status_code == 302
    assert "NEUE ANFRAGE" in client.get("/").get_data(as_text=True)


def test_passwortschutz(client, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORT", "geheim")
    assert client.get("/").status_code == 401
    assert client.get("/helden").status_code == 200
    import base64
    h = {"Authorization": "Basic " + base64.b64encode(b"x:geheim").decode()}
    assert client.get("/", headers=h).status_code == 200
