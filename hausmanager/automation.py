"""Die Automatik: einmal täglich ausführen (Cronjob oder Button im Dashboard).

    python -m hausmanager.automation

Alle Schritte sind idempotent – mehrfaches Ausführen am selben Tag erzeugt keine Duplikate.
"""
import calendar
import datetime as dt
import re

from . import db, mailer, vorlagen


def _d(s):
    return dt.date.fromisoformat(s) if s else None


def _monate(von, bis):
    """Alle Monate (YYYY-MM) von `von` bis `bis` inklusive."""
    y, m = von.year, von.month
    while (y, m) <= (bis.year, bis.month):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def _plus_monate(d, n):
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]


def _monatsname(ym):
    y, m = ym.split("-")
    return f"{MONATE[int(m) - 1]} {y}"


def _eur(x):
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ===========================================================================
# Modul 1: Eigene Immobilien
# ===========================================================================
def sollstellungen_erzeugen(con, heute):
    """Erzeugt für jeden laufenden Vertrag die monatliche Mietforderung (max. 24 Monate rückwirkend)."""
    neu = 0
    frueheste = _plus_monate(heute.replace(day=1), -24)
    for v in con.execute("SELECT * FROM vertraege"):
        beginn, ende = _d(v["beginn"]), _d(v["ende"])
        start = max(beginn.replace(day=1), frueheste)
        for y, m in _monate(start, heute):
            if ende and dt.date(y, m, 1) > ende:
                break
            tag = min(int(v["faellig_tag"] or 3), calendar.monthrange(y, m)[1])
            cur = con.execute(
                "INSERT OR IGNORE INTO sollstellungen(vertrag_id, monat, betrag, faellig_am) VALUES (?,?,?,?)",
                (v["id"], f"{y:04d}-{m:02d}", v["kaltmiete"] + (v["nebenkosten"] or 0), dt.date(y, m, tag).isoformat()),
            )
            neu += cur.rowcount
    return neu


def _norm(s):
    return re.sub(r"[^a-z0-9äöüß ]", " ", (s or "").lower())


def zahlungen_zuordnen(con):
    """Ordnet importierte Bankzahlungen automatisch Verträgen zu (über Mietername im Auftraggeber/Verwendungszweck)."""
    vertraege = con.execute(
        """SELECT v.id, m.name, e.bezeichnung, v.ende FROM vertraege v
           JOIN mieter m ON m.id = v.mieter_id JOIN einheiten e ON e.id = v.einheit_id"""
    ).fetchall()
    zugeordnet = 0
    for z in con.execute("SELECT * FROM zahlungen WHERE vertrag_id IS NULL AND betrag > 0").fetchall():
        text = " " + _norm(f"{z['auftraggeber']} {z['verwendungszweck']}") + " "
        treffer = []
        for v in vertraege:
            nachname = _norm(v["name"]).split()[-1] if v["name"].strip() else ""
            if nachname and len(nachname) > 2 and f" {nachname} " in text:
                treffer.append(v)
        if len(treffer) > 1:  # mehrere Verträge desselben Mieters: Einheit im Text?
            treffer = [v for v in treffer if _norm(v["bezeichnung"]) in text]  # sonst mehrdeutig -> manuell
        if len(treffer) == 1:
            con.execute("UPDATE zahlungen SET vertrag_id = ?, zugeordnet = 1 WHERE id = ?", (treffer[0]["id"], z["id"]))
            zugeordnet += 1
    return zugeordnet


def zahlungen_verbuchen(con):
    """Verteilt alle Zahlungen je Vertrag auf die ältesten offenen Sollstellungen (FIFO). Komplett neu berechnet."""
    con.execute("UPDATE sollstellungen SET bezahlt = 0")
    for v in con.execute("SELECT id FROM vertraege").fetchall():
        rest = con.execute("SELECT COALESCE(SUM(betrag),0) FROM zahlungen WHERE vertrag_id = ?", (v["id"],)).fetchone()[0]
        for s in con.execute("SELECT id, betrag FROM sollstellungen WHERE vertrag_id = ? ORDER BY monat", (v["id"],)).fetchall():
            if rest <= 0:
                break
            anteil = min(rest, s["betrag"])
            con.execute("UPDATE sollstellungen SET bezahlt = ? WHERE id = ?", (anteil, s["id"]))
            rest -= anteil


def mahnwesen(con, heute, cfg):
    """Erstellt Zahlungserinnerungen (Stufe 1) und Mahnungen (Stufe 2) als Entwürfe."""
    tage1, tage2 = int(cfg.get("mahnung_tage_1", 7)), int(cfg.get("mahnung_tage_2", 21))
    erstellt = 0
    # Inzwischen bezahlt? -> noch nicht verschickte Erinnerungen verwerfen
    con.execute(
        """UPDATE nachrichten SET status = 'verworfen' WHERE status = 'entwurf' AND sollstellung_id IN
           (SELECT id FROM sollstellungen WHERE betrag - bezahlt <= 0.01)"""
    )
    rows = con.execute(
        """SELECT s.*, m.id AS mieter_id, m.name AS mieter_name, m.email, e.bezeichnung, o.name AS objekt, o.adresse
           FROM sollstellungen s JOIN vertraege v ON v.id = s.vertrag_id
           JOIN mieter m ON m.id = v.mieter_id JOIN einheiten e ON e.id = v.einheit_id
           JOIN objekte o ON o.id = e.objekt_id
           WHERE s.betrag - s.bezahlt > 0.01 ORDER BY s.faellig_am"""
    ).fetchall()
    for s in rows:
        verzug = (heute - _d(s["faellig_am"])).days
        stufe = 2 if verzug >= tage2 else 1 if verzug >= tage1 else 0
        if stufe <= s["mahnstufe"]:
            continue
        daten = dict(cfg)
        daten.update(
            mieter_name=s["mieter_name"], monat=_monatsname(s["monat"]), einheit=f"{s['objekt']} – {s['bezeichnung']}",
            offen=_eur(s["betrag"] - s["bezahlt"]), faellig_am=_d(s["faellig_am"]).strftime("%d.%m.%Y"),
            frist=(heute + dt.timedelta(days=10)).strftime("%d.%m.%Y"),
        )
        v = vorlagen.ZAHLUNGSERINNERUNG[stufe]
        if s["email"]:
            kanal, empfaenger = "email", s["email"]
        else:  # Brief an die Mietwohnung
            kanal, empfaenger = "brief", f"{s['mieter_name']}\n" + (s["adresse"] or s["objekt"]).replace(", ", "\n")
        con.execute(
            "INSERT INTO nachrichten(mieter_id, sollstellung_id, kanal, empfaenger, betreff, text) VALUES (?,?,?,?,?,?)",
            (s["mieter_id"], s["id"], kanal, empfaenger, vorlagen.fuellen(v["betreff"], daten), vorlagen.fuellen(v["text"], daten)),
        )
        con.execute("UPDATE sollstellungen SET mahnstufe = ? WHERE id = ?", (stufe, s["id"]))
        erstellt += 1

    # Rückstand >= 2 Monatsmieten -> Hinweis auf fristlose Kündigungsmöglichkeit (§ 543 Abs. 2 Nr. 3 BGB)
    for r in con.execute(
        """SELECT v.id, m.name, v.kaltmiete + v.nebenkosten AS miete, SUM(s.betrag - s.bezahlt) AS offen
           FROM vertraege v JOIN mieter m ON m.id = v.mieter_id JOIN sollstellungen s ON s.vertrag_id = v.id
           WHERE s.faellig_am <= ? GROUP BY v.id HAVING offen >= 2 * miete - 0.01""",
        (heute.isoformat(),),
    ):
        db.add_task(con, "immobilien", f"rueckstand2-{r['id']}-{heute:%Y-%m}",
                    f"⚠ {r['name']}: Rückstand {_eur(r['offen'])} € (≥ 2 Monatsmieten) – Kündigung/Anwalt prüfen", heute.isoformat())
    return erstellt


def fristen(con, heute):
    """Vertragsende, mögliche Mieterhöhungen, dringende Tickets -> Aufgaben."""
    neu = 0
    for v in con.execute(
        """SELECT v.*, m.name, e.bezeichnung FROM vertraege v JOIN mieter m ON m.id = v.mieter_id
           JOIN einheiten e ON e.id = v.einheit_id"""
    ).fetchall():
        ende = _d(v["ende"])
        if ende and heute <= ende <= heute + dt.timedelta(days=90):
            neu += db.add_task(con, "immobilien", f"vertragsende-{v['id']}",
                               f"Vertrag {v['name']} ({v['bezeichnung']}) endet am {ende:%d.%m.%Y} – Übergabe/Nachvermietung planen",
                               (ende - dt.timedelta(days=60)).isoformat())
        if ende and ende < heute:
            continue
        basis = _d(v["letzte_erhoehung"]) or _d(v["beginn"])
        # § 558 BGB: Erhöhung auf ortsübliche Vergleichsmiete frühestens 15 Monate nach letzter Erhöhung
        moeglich_ab = _plus_monate(basis, 15)
        if moeglich_ab <= heute + dt.timedelta(days=30):
            neu += db.add_task(con, "immobilien", f"mieterhoehung-{v['id']}-{basis}",
                               f"Mieterhöhung prüfen: {v['name']} ({v['bezeichnung']}) – möglich ab {moeglich_ab:%d.%m.%Y} "
                               f"(Mietspiegel, Kappungsgrenze 15/20 % in 3 Jahren)", moeglich_ab.isoformat())
    for t in con.execute(
        "SELECT * FROM tickets WHERE status != 'erledigt' AND prioritaet = 'hoch' AND erstellt <= ?",
        ((heute - dt.timedelta(days=2)).isoformat(),),
    ):
        neu += db.add_task(con, "immobilien", f"ticket-{t['id']}", f"Dringendes Ticket seit {t['erstellt']} offen: {t['titel']}", heute.isoformat())
    return neu


# ===========================================================================
# Modul 2: Hausmeister Helden – Akquise
# ===========================================================================
def akquise_nachricht(lead, schritt, cfg):
    daten = dict(cfg)
    daten.update({k: (lead[k] or "") for k in lead.keys()})
    daten["briefanrede"] = vorlagen.briefanrede(lead["anrede"], lead["ansprechpartner"])
    v = vorlagen.AKQUISE[schritt]
    return vorlagen.fuellen(v["betreff"], daten), vorlagen.fuellen(v["text"], daten)


def akquise_sequenz(con, heute, cfg):
    """Schickt jeden aktiven Lead automatisch durch die 3-stufige Kontaktsequenz.

    Rechtlicher Rahmen (UWG § 7): Werbe-E-Mails nur mit Einwilligung -> sonst Brief (erlaubt)
    plus Anruf-Aufgabe (bei Gewerbetreibenden mit mutmaßlicher Einwilligung zulässig).
    """
    abstaende = [int(x) for x in cfg.get("followup_tage", "7,14,30").split(",")]
    erstellt = 0
    leads = con.execute(
        """SELECT * FROM leads WHERE status IN ('neu', 'kontaktiert') AND schritt < 3
           AND (naechster_kontakt IS NULL OR naechster_kontakt <= ?)""",
        (heute.isoformat(),),
    ).fetchall()
    for lead in leads:
        schritt = lead["schritt"] + 1
        if lead["einwilligung_email"] and lead["email"]:
            kanal, empfaenger = "email", lead["email"]
        elif lead["strasse"] and lead["plz_ort"]:
            zhd = f"z. Hd. {lead['anrede'] or ''} {lead['ansprechpartner']}".replace("  ", " ") if lead["ansprechpartner"] else ""
            kanal, empfaenger = "brief", "\n".join(x for x in [lead["firma"], zhd, lead["strasse"], lead["plz_ort"]] if x)
        else:
            db.add_task(con, "akquise", f"adresse-{lead['id']}", f"Postadresse für {lead['firma']} recherchieren (für Anschreiben nötig)", heute.isoformat())
            continue
        betreff, text = akquise_nachricht(lead, schritt, cfg)
        if kanal == "email":
            text += vorlagen.ABMELDE_HINWEIS
        con.execute(
            "INSERT INTO nachrichten(lead_id, kanal, empfaenger, betreff, text) VALUES (?,?,?,?,?)",
            (lead["id"], kanal, empfaenger, betreff, text),
        )
        naechster = heute + dt.timedelta(days=abstaende[min(schritt - 1, len(abstaende) - 1)])
        con.execute("UPDATE leads SET schritt = ?, status = 'kontaktiert', naechster_kontakt = ? WHERE id = ?",
                    (schritt, naechster.isoformat(), lead["id"]))
        if lead["telefon"] and schritt in (1, 2):
            db.add_task(con, "akquise", f"anruf-{lead['id']}-{schritt}",
                        f"Anrufen: {lead['firma']} ({lead['ansprechpartner'] or 'Zentrale'}) {lead['telefon']} – Bezug auf Schreiben, Objekt-Check anbieten",
                        (heute + dt.timedelta(days=5)).isoformat())
        erstellt += 1

    # Sequenz durchlaufen ohne Reaktion -> Wiedervorlage in 6 Monaten
    for lead in con.execute(
        "SELECT * FROM leads WHERE status = 'kontaktiert' AND schritt >= 3 AND naechster_kontakt <= ?", (heute.isoformat(),)
    ).fetchall():
        con.execute("UPDATE leads SET status = 'neu', schritt = 0, naechster_kontakt = ? WHERE id = ?",
                    (_plus_monate(heute, 6).isoformat(), lead["id"]))
    return erstellt


def emails_senden(con, cfg):
    """Versendet E-Mail-Entwürfe automatisch, wenn in den Einstellungen aktiviert und SMTP konfiguriert ist."""
    if cfg.get("auto_senden") != "1" or not mailer.konfiguriert():
        return 0
    gesendet = 0
    for n in con.execute("SELECT * FROM nachrichten WHERE kanal = 'email' AND status = 'entwurf'").fetchall():
        try:
            mailer.senden(n["empfaenger"], n["betreff"], n["text"])
        except Exception as e:  # noqa: BLE001 – einzelner Fehler soll den Lauf nicht stoppen
            db.add_task(con, "akquise" if n["lead_id"] else "immobilien", f"mailfehler-{n['id']}", f"E-Mail an {n['empfaenger']} fehlgeschlagen: {e}")
            continue
        con.execute("UPDATE nachrichten SET status = 'gesendet', gesendet = datetime('now') WHERE id = ?", (n["id"],))
        gesendet += 1
    return gesendet


def alles(con, heute=None):
    heute = heute or dt.date.today()
    cfg = db.settings(con)
    bericht = {
        "Neue Mietforderungen": sollstellungen_erzeugen(con, heute),
        "Zahlungen automatisch zugeordnet": zahlungen_zuordnen(con),
    }
    zahlungen_verbuchen(con)
    bericht["Zahlungserinnerungen/Mahnungen erstellt"] = mahnwesen(con, heute, cfg)
    bericht["Neue Fristen-Aufgaben"] = fristen(con, heute)
    bericht["Akquise-Anschreiben erstellt"] = akquise_sequenz(con, heute, cfg)
    bericht["E-Mails versendet"] = emails_senden(con, cfg)
    con.commit()
    return bericht


if __name__ == "__main__":
    c = db.connect()
    db.init(c)
    for k, v in alles(c).items():
        print(f"{k}: {v}")
