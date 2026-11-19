"""Beispieldaten zum Ausprobieren:  python -m hausmanager.demo"""
import datetime as dt

from . import automation, db


def main():
    c = db.connect()
    db.init(c)
    if c.execute("SELECT COUNT(*) FROM objekte").fetchone()[0]:
        print("Datenbank enthält bereits Daten – Demo wird nicht erneut angelegt.")
        return
    heute = dt.date.today()
    c.execute("INSERT INTO objekte(name, adresse, kaufpreis) VALUES ('MFH Lindenstraße', 'Lindenstr. 8, 12345 Musterstadt', 420000)")
    c.execute("INSERT INTO objekte(name, adresse, kaufpreis) VALUES ('ETW Parkblick', 'Parkweg 3, 12345 Musterstadt', 189000)")
    for o, b, f in [(1, "EG links", 68), (1, "EG rechts", 72), (1, "OG links", 68), (2, "WE 12", 54)]:
        c.execute("INSERT INTO einheiten(objekt_id, bezeichnung, flaeche) VALUES (?,?,?)", (o, b, f))
    start = (heute.replace(day=1) - dt.timedelta(days=75)).replace(day=1).isoformat()
    for e, name, mail, kalt, nk in [(1, "Max Mustermann", "max@example.com", 620, 180), (2, "Erika Beispiel", "", 650, 190), (4, "Jonas Probe", "jonas@example.com", 540, 140)]:
        cur = c.execute("INSERT INTO mieter(name, email) VALUES (?,?)", (name, mail))
        c.execute("INSERT INTO vertraege(einheit_id, mieter_id, beginn, kaltmiete, nebenkosten, kaution) VALUES (?,?,?,?,?,?)",
                  (e, cur.lastrowid, "2024-06-01" if e == 1 else start, kalt, nk, kalt * 3))
    automation.sollstellungen_erzeugen(c, heute)
    # Mustermann zahlt alles, Beispiel nur teilweise, Probe gar nicht im aktuellen Monat
    for v, monate in [(1, 99), (2, 2), (3, 2)]:
        for s in c.execute("SELECT * FROM sollstellungen WHERE vertrag_id=? ORDER BY monat LIMIT ?", (v, monate)).fetchall():
            c.execute("INSERT INTO zahlungen(vertrag_id, datum, betrag, verwendungszweck, zugeordnet) VALUES (?,?,?,?,1)",
                      (v, s["faellig_am"], s["betrag"], f"Miete {s['monat']}"))
    c.execute("INSERT INTO zahlungen(datum, betrag, verwendungszweck, auftraggeber) VALUES (?, 300, 'Ueberweisung', 'Unbekannt GmbH')", (heute.isoformat(),))
    c.execute("INSERT INTO tickets(objekt_id, titel, beschreibung, prioritaet) VALUES (1, 'Heizung EG rechts kalt', 'Frau Beispiel, Tel. 0123 4567', 'hoch')")
    leads = [
        ("Musterstadt Immobilienverwaltung GmbH", "Frau", "Sabine Kraus", "", "0123 987654", "Marktplatz 2", "12345 Musterstadt", 0, 320),
        ("WEG-Verwaltung Huber & Partner", "Herr", "Thomas Huber", "t.huber@huber-weg.example", "0123 555111", "Ringstr. 40", "12346 Nachbarort", 1, 140),
        ("Wohnbau Genossenschaft Süd eG", "", "", "", "0123 777000", "Südallee 1", "12347 Südstadt", 0, 900),
    ]
    for f, an, ap, em, tel, st, po, einw, we in leads:
        c.execute("INSERT INTO leads(firma, anrede, ansprechpartner, email, telefon, strasse, plz_ort, einwilligung_email, einheiten_geschaetzt, quelle) VALUES (?,?,?,?,?,?,?,?,?, 'Demo')",
                  (f, an, ap, em, tel, st, po, einw, we))
    c.commit()
    for k, v in automation.alles(c).items():
        print(f"{k}: {v}")
    print("Demo-Daten angelegt. Starten mit:  python -m hausmanager.app")


if __name__ == "__main__":
    main()
