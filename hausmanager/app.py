"""HausManager – Web-Oberfläche.

Start:  python -m hausmanager.app   ->  http://localhost:5000
"""
import csv
import datetime as dt
import io
import os
import secrets

from flask import Flask, Response, abort, flash, g, redirect, render_template, request, url_for

from . import automation, db, mailer, vorlagen

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(16)

OEFFENTLICH = {"landing", "anfrage", "danke", "static"}


# ---------------------------------------------------------------------------
# Infrastruktur
# ---------------------------------------------------------------------------
def con():
    if "con" not in g:
        g.con = db.connect(app.config.get("DB_PATH"))
        db.init(g.con)
    return g.con


@app.teardown_appcontext
def _close(_exc):
    c = g.pop("con", None)
    if c is not None:
        c.close()


@app.before_request
def _auth():
    """Verwaltungsbereich per Passwort schützen (ADMIN_PASSWORT in .env). Landingpage bleibt öffentlich."""
    pw = os.environ.get("ADMIN_PASSWORT")
    if not pw or request.endpoint in OEFFENTLICH:
        return None
    a = request.authorization
    if a and secrets.compare_digest(a.password or "", pw):
        return None
    return Response("Login erforderlich", 401, {"WWW-Authenticate": 'Basic realm="HausManager"'})


@app.template_filter("eur")
def eur(x):
    return automation._eur(x or 0) + " €"


@app.template_filter("datum")
def datum(s):
    try:
        return dt.date.fromisoformat(s[:10]).strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return s or ""


@app.context_processor
def _ctx():
    return {"cfg": db.settings(con()), "heute": dt.date.today().isoformat(), "smtp_ok": mailer.konfiguriert()}


def _f(name, default=""):
    return (request.form.get(name) or default).strip()


def _zahl(s):
    s = (s or "").strip().replace("€", "").replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s or 0)


def _csv_rows(datei):
    text = datei.read().decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:2000], delimiters=";,\t")
    except csv.Error:
        dialect = "excel"
    return list(csv.DictReader(io.StringIO(text), dialect=dialect))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/")
def dashboard():
    c = con()
    monat = dt.date.today().strftime("%Y-%m")
    k = {
        "soll": c.execute("SELECT COALESCE(SUM(betrag),0) FROM sollstellungen WHERE monat=?", (monat,)).fetchone()[0],
        "ist": c.execute("SELECT COALESCE(SUM(bezahlt),0) FROM sollstellungen WHERE monat=?", (monat,)).fetchone()[0],
        "offen": c.execute("SELECT COALESCE(SUM(betrag-bezahlt),0) FROM sollstellungen WHERE faellig_am <= date('now')").fetchone()[0],
        "einheiten": c.execute("SELECT COUNT(*) FROM einheiten").fetchone()[0],
        "vermietet": c.execute(
            "SELECT COUNT(DISTINCT einheit_id) FROM vertraege WHERE beginn <= date('now') AND (ende IS NULL OR ende = '' OR ende >= date('now'))"
        ).fetchone()[0],
        "jahresmiete": c.execute(
            "SELECT COALESCE(SUM(kaltmiete),0)*12 FROM vertraege WHERE beginn <= date('now') AND (ende IS NULL OR ende = '' OR ende >= date('now'))"
        ).fetchone()[0],
        "kaufpreis": c.execute("SELECT COALESCE(SUM(kaufpreis),0) FROM objekte").fetchone()[0],
        "tickets": c.execute("SELECT COUNT(*) FROM tickets WHERE status != 'erledigt'").fetchone()[0],
        "entwuerfe": c.execute("SELECT COUNT(*) FROM nachrichten WHERE status='entwurf'").fetchone()[0],
    }
    k["rendite"] = (k["jahresmiete"] / k["kaufpreis"] * 100) if k["kaufpreis"] else 0
    pipeline = {r["status"]: r["n"] for r in c.execute("SELECT status, COUNT(*) n FROM leads GROUP BY status")}
    aufgaben = c.execute("SELECT * FROM aufgaben WHERE erledigt=0 ORDER BY COALESCE(faellig,'9999'), id").fetchall()
    return render_template("dashboard.html", k=k, pipeline=pipeline, aufgaben=aufgaben)


@app.post("/automatik")
def automatik():
    bericht = automation.alles(con())
    flash("Automatik ausgeführt – " + ", ".join(f"{k}: {v}" for k, v in bericht.items()))
    return redirect(request.referrer or url_for("dashboard"))


@app.post("/aufgabe/<int:aid>/erledigt")
def aufgabe_erledigt(aid):
    con().execute("UPDATE aufgaben SET erledigt=1 WHERE id=?", (aid,))
    con().commit()
    return redirect(request.referrer or url_for("dashboard"))


@app.post("/aufgabe/neu")
def aufgabe_neu():
    con().execute("INSERT INTO aufgaben(bereich, titel, faellig) VALUES (?,?,?)",
                  (_f("bereich", "immobilien"), _f("titel"), _f("faellig") or None))
    con().commit()
    return redirect(request.referrer or url_for("dashboard"))


# ---------------------------------------------------------------------------
# Modul 1: Immobilien
# ---------------------------------------------------------------------------
@app.route("/immobilien")
def immobilien():
    c = con()
    objekte = c.execute("SELECT * FROM objekte ORDER BY name").fetchall()
    einheiten = c.execute(
        """SELECT e.*, o.name AS objekt,
                  (SELECT m.name FROM vertraege v JOIN mieter m ON m.id=v.mieter_id
                   WHERE v.einheit_id=e.id AND v.beginn <= date('now') AND (v.ende IS NULL OR v.ende='' OR v.ende >= date('now'))
                   ORDER BY v.beginn DESC LIMIT 1) AS mieter
           FROM einheiten e JOIN objekte o ON o.id=e.objekt_id ORDER BY o.name, e.bezeichnung"""
    ).fetchall()
    vertraege = c.execute(
        """SELECT v.*, m.name, m.email, m.telefon, e.bezeichnung, o.name AS objekt,
                  (SELECT COALESCE(SUM(betrag-bezahlt),0) FROM sollstellungen s WHERE s.vertrag_id=v.id AND s.faellig_am <= date('now')) AS offen
           FROM vertraege v JOIN mieter m ON m.id=v.mieter_id JOIN einheiten e ON e.id=v.einheit_id
           JOIN objekte o ON o.id=e.objekt_id ORDER BY o.name, e.bezeichnung"""
    ).fetchall()
    return render_template("immobilien.html", objekte=objekte, einheiten=einheiten, vertraege=vertraege)


@app.post("/objekt/neu")
def objekt_neu():
    con().execute("INSERT INTO objekte(name, adresse, kaufpreis, notiz) VALUES (?,?,?,?)",
                  (_f("name"), _f("adresse"), _zahl(_f("kaufpreis")), _f("notiz")))
    con().commit()
    return redirect(url_for("immobilien"))


@app.post("/einheit/neu")
def einheit_neu():
    con().execute("INSERT INTO einheiten(objekt_id, bezeichnung, flaeche) VALUES (?,?,?)",
                  (int(_f("objekt_id")), _f("bezeichnung"), _zahl(_f("flaeche"))))
    con().commit()
    return redirect(url_for("immobilien"))


@app.post("/vertrag/neu")
def vertrag_neu():
    c = con()
    cur = c.execute("INSERT INTO mieter(name, email, telefon) VALUES (?,?,?)", (_f("name"), _f("email"), _f("telefon")))
    c.execute(
        """INSERT INTO vertraege(einheit_id, mieter_id, beginn, ende, kaltmiete, nebenkosten, kaution, faellig_tag, letzte_erhoehung)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (int(_f("einheit_id")), cur.lastrowid, _f("beginn"), _f("ende") or None, _zahl(_f("kaltmiete")),
         _zahl(_f("nebenkosten")), _zahl(_f("kaution")), int(_f("faellig_tag", "3")), _f("letzte_erhoehung") or None),
    )
    c.commit()
    automation.alles(c)
    flash("Mietvertrag angelegt – Mietforderungen wurden automatisch erzeugt.")
    return redirect(url_for("immobilien"))


@app.post("/vertrag/<int:vid>/beenden")
def vertrag_beenden(vid):
    con().execute("UPDATE vertraege SET ende=? WHERE id=?", (_f("ende"), vid))
    con().commit()
    return redirect(url_for("immobilien"))


@app.post("/vertrag/<int:vid>/erhoehung")
def vertrag_erhoehung(vid):
    con().execute("UPDATE vertraege SET kaltmiete=?, letzte_erhoehung=? WHERE id=?", (_zahl(_f("kaltmiete")), _f("ab"), vid))
    con().commit()
    flash("Miete angepasst. Bereits erzeugte Monate bleiben unverändert.")
    return redirect(url_for("immobilien"))


@app.route("/zahlungen")
def zahlungen():
    c = con()
    offene = c.execute(
        """SELECT s.*, m.name, e.bezeichnung, o.name AS objekt FROM sollstellungen s
           JOIN vertraege v ON v.id=s.vertrag_id JOIN mieter m ON m.id=v.mieter_id
           JOIN einheiten e ON e.id=v.einheit_id JOIN objekte o ON o.id=e.objekt_id
           WHERE s.betrag - s.bezahlt > 0.01 ORDER BY s.faellig_am"""
    ).fetchall()
    liste = c.execute(
        """SELECT z.*, m.name FROM zahlungen z LEFT JOIN vertraege v ON v.id=z.vertrag_id
           LEFT JOIN mieter m ON m.id=v.mieter_id ORDER BY (z.vertrag_id IS NOT NULL), z.datum DESC LIMIT 300"""
    ).fetchall()
    vertraege = c.execute(
        """SELECT v.id, m.name, e.bezeichnung FROM vertraege v JOIN mieter m ON m.id=v.mieter_id
           JOIN einheiten e ON e.id=v.einheit_id ORDER BY m.name"""
    ).fetchall()
    return render_template("zahlungen.html", offene=offene, liste=liste, vertraege=vertraege)


@app.post("/zahlung/neu")
def zahlung_neu():
    c = con()
    c.execute("INSERT INTO zahlungen(vertrag_id, datum, betrag, verwendungszweck, auftraggeber, zugeordnet) VALUES (?,?,?,?,?,1)",
              (int(_f("vertrag_id")), _f("datum"), _zahl(_f("betrag")), _f("verwendungszweck"), _f("auftraggeber")))
    c.commit()
    automation.alles(c)
    return redirect(url_for("zahlungen"))


@app.post("/zahlung/<int:zid>/zuordnen")
def zahlung_zuordnen(zid):
    c = con()
    c.execute("UPDATE zahlungen SET vertrag_id=?, zugeordnet=1 WHERE id=?", (int(_f("vertrag_id")) if _f("vertrag_id") else None, zid))
    c.commit()
    automation.alles(c)
    return redirect(url_for("zahlungen"))


@app.post("/zahlungen/import")
def zahlungen_import():
    """Kontoauszug als CSV (Export aus dem Online-Banking) importieren."""
    datei = request.files.get("datei")
    if not datei:
        abort(400)
    c = con()
    n = 0
    for r in _csv_rows(datei):
        low = {k.lower().strip(): (v or "").strip() for k, v in r.items() if k}

        def col(*namen):
            for key, val in low.items():
                if any(nm in key for nm in namen):
                    return val
            return ""

        try:
            betrag = _zahl(col("betrag", "amount"))
        except ValueError:
            continue
        if betrag <= 0:
            continue  # nur Eingänge
        roh = col("buchungstag", "buchungsdatum", "datum", "date", "valuta")
        try:
            datum_iso = dt.datetime.strptime(roh[:10], "%d.%m.%Y").date().isoformat() if "." in roh else roh[:10]
        except ValueError:
            datum_iso = roh
        zweck = col("verwendungszweck", "purpose", "buchungstext")
        name = col("auftraggeber", "zahlungspflichtige", "name", "beguenstigter", "begünstigter", "empfänger")
        if c.execute("SELECT 1 FROM zahlungen WHERE datum=? AND betrag=? AND verwendungszweck=? AND auftraggeber=?",
                     (datum_iso, betrag, zweck, name)).fetchone():
            continue  # schon importiert
        c.execute("INSERT INTO zahlungen(datum, betrag, verwendungszweck, auftraggeber) VALUES (?,?,?,?)", (datum_iso, betrag, zweck, name))
        n += 1
    c.commit()
    bericht = automation.alles(c)
    flash(f"{n} Zahlungseingänge importiert, {bericht['Zahlungen automatisch zugeordnet']} automatisch zugeordnet.")
    return redirect(url_for("zahlungen"))


@app.route("/tickets", methods=["GET", "POST"])
def tickets():
    c = con()
    if request.method == "POST":
        c.execute("INSERT INTO tickets(objekt_id, titel, beschreibung, prioritaet) VALUES (?,?,?,?)",
                  (int(_f("objekt_id")) if _f("objekt_id") else None, _f("titel"), _f("beschreibung"), _f("prioritaet", "normal")))
        c.commit()
        return redirect(url_for("tickets"))
    liste = c.execute(
        """SELECT t.*, o.name AS objekt FROM tickets t LEFT JOIN objekte o ON o.id=t.objekt_id
           ORDER BY t.status='erledigt', CASE t.prioritaet WHEN 'hoch' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, t.erstellt"""
    ).fetchall()
    return render_template("tickets.html", tickets=liste, objekte=c.execute("SELECT * FROM objekte ORDER BY name").fetchall())


@app.post("/ticket/<int:tid>/status")
def ticket_status(tid):
    con().execute("UPDATE tickets SET status=? WHERE id=?", (_f("status"), tid))
    con().commit()
    return redirect(url_for("tickets"))


# ---------------------------------------------------------------------------
# Modul 2: Hausmeister Helden – Akquise
# ---------------------------------------------------------------------------
LEAD_STATUS = ["neu", "kontaktiert", "interessiert", "angebot", "gewonnen", "verloren", "kein_interesse"]
LEAD_FELDER = ["firma", "ansprechpartner", "anrede", "email", "telefon", "strasse", "plz_ort", "typ", "quelle", "einheiten_geschaetzt", "notiz"]


@app.route("/akquise")
def akquise():
    status = request.args.get("status")
    sql, args = "SELECT * FROM leads", []
    if status:
        sql, args = sql + " WHERE status=?", [status]
    leads = con().execute(sql + " ORDER BY CASE status WHEN 'interessiert' THEN 0 WHEN 'angebot' THEN 1 ELSE 2 END, naechster_kontakt", args).fetchall()
    zahlen = {r["status"]: r["n"] for r in con().execute("SELECT status, COUNT(*) n FROM leads GROUP BY status")}
    return render_template("akquise.html", leads=leads, zahlen=zahlen, status_liste=LEAD_STATUS, aktiv=status)


def _lead_speichern(lid=None):
    werte = [_f(k) for k in LEAD_FELDER]
    werte[LEAD_FELDER.index("einheiten_geschaetzt")] = int(_zahl(_f("einheiten_geschaetzt")) or 0)
    einw = 1 if request.form.get("einwilligung_email") else 0
    c = con()
    if lid:
        c.execute(f"UPDATE leads SET {', '.join(k + '=?' for k in LEAD_FELDER)}, einwilligung_email=? WHERE id=?", (*werte, einw, lid))
    else:
        cur = c.execute(f"INSERT INTO leads({', '.join(LEAD_FELDER)}, einwilligung_email) VALUES ({', '.join('?' * (len(LEAD_FELDER) + 1))})", (*werte, einw))
        lid = cur.lastrowid
    c.commit()
    return lid


@app.post("/lead/neu")
def lead_neu():
    lid = _lead_speichern()
    return redirect(url_for("lead", lid=lid))


@app.route("/lead/<int:lid>", methods=["GET", "POST"])
def lead(lid):
    c = con()
    if request.method == "POST":
        _lead_speichern(lid)
        flash("Gespeichert.")
        return redirect(url_for("lead", lid=lid))
    l = c.execute("SELECT * FROM leads WHERE id=?", (lid,)).fetchone() or abort(404)
    nachrichten = c.execute("SELECT * FROM nachrichten WHERE lead_id=? ORDER BY erstellt DESC", (lid,)).fetchall()
    return render_template("lead.html", l=l, nachrichten=nachrichten, status_liste=LEAD_STATUS)


@app.post("/lead/<int:lid>/status")
def lead_status(lid):
    c = con()
    status = _f("status")
    c.execute("UPDATE leads SET status=? WHERE id=?", (status, lid))
    if status in ("interessiert", "angebot", "gewonnen", "verloren", "kein_interesse"):
        # Reaktion erhalten -> automatische Sequenz stoppen, offene Entwürfe verwerfen
        c.execute("UPDATE nachrichten SET status='verworfen' WHERE lead_id=? AND status='entwurf'", (lid,))
    if status == "interessiert":
        db.add_task(c, "akquise", f"angebot-{lid}", "Objekt-Check terminieren & Angebot erstellen", dt.date.today().isoformat())
    c.commit()
    return redirect(request.referrer or url_for("lead", lid=lid))


@app.post("/leads/import")
def leads_import():
    """CSV mit Spalten: firma;ansprechpartner;anrede;email;telefon;strasse;plz_ort;typ;quelle;einwilligung_email;einheiten_geschaetzt"""
    datei = request.files.get("datei")
    if not datei:
        abort(400)
    c = con()
    n = dup = 0
    for r in _csv_rows(datei):
        r = {k.lower().strip(): (v or "").strip() for k, v in r.items() if k}
        if not r.get("firma"):
            continue
        if c.execute("SELECT 1 FROM leads WHERE lower(firma)=lower(?) AND COALESCE(plz_ort,'')=?", (r["firma"], r.get("plz_ort", ""))).fetchone():
            dup += 1
            continue
        c.execute(
            """INSERT INTO leads(firma, ansprechpartner, anrede, email, telefon, strasse, plz_ort, typ, quelle, einwilligung_email, einheiten_geschaetzt)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (r["firma"], r.get("ansprechpartner"), r.get("anrede"), r.get("email"), r.get("telefon"), r.get("strasse"), r.get("plz_ort"),
             r.get("typ") or "Hausverwaltung", r.get("quelle") or "CSV-Import",
             1 if r.get("einwilligung_email", "").lower() in ("1", "ja", "yes", "x", "true") else 0,
             int(_zahl(r.get("einheiten_geschaetzt")) or 0)),
        )
        n += 1
    c.commit()
    flash(f"{n} Leads importiert, {dup} Duplikate übersprungen. Klicke „Automatik ausführen“, um die Anschreiben zu erzeugen.")
    return redirect(url_for("akquise"))


@app.route("/lead/<int:lid>/angebot", methods=["GET", "POST"])
def angebot(lid):
    l = con().execute("SELECT * FROM leads WHERE id=?", (lid,)).fetchone() or abort(404)
    standard = ("Objektbetreuung inkl. monatlicher Begehung mit Fotoprotokoll;1;89\n"
                "Treppenhausreinigung (wöchentlich), je Hauseingang;1;120\n"
                "Grünpflege & Außenanlagen (saisonal, Monatspauschale);1;95\n"
                "Winterdienst inkl. Räumprotokoll (Monatspauschale Nov–März);1;110\n"
                "Mülltonnenservice (Bereitstellung/Rückholung);1;45")
    zeilen_text = request.form.get("positionen", standard)
    positionen = []
    for z in zeilen_text.splitlines():
        teile = [t.strip() for t in z.split(";")]
        if len(teile) == 3 and teile[0]:
            try:
                menge, preis = _zahl(teile[1]), _zahl(teile[2])
            except ValueError:
                continue
            positionen.append({"text": teile[0], "menge": menge, "preis": preis, "summe": menge * preis})
    netto = sum(p["summe"] for p in positionen)
    if request.method == "POST" and request.form.get("drucken"):
        c = con()
        c.execute("UPDATE leads SET status='angebot' WHERE id=?", (lid,))
        c.execute("UPDATE nachrichten SET status='verworfen' WHERE lead_id=? AND status='entwurf'", (lid,))
        db.add_task(c, "akquise", f"angebot-nachfassen-{lid}-{dt.date.today()}", f"Angebot bei {l['firma']} nachfassen",
                    (dt.date.today() + dt.timedelta(days=7)).isoformat())
        c.commit()
        return render_template("angebot_druck.html", l=l, positionen=positionen, netto=netto,
                               nr=f"AN-{dt.date.today():%Y%m%d}-{lid}", briefanrede=vorlagen.briefanrede(l["anrede"], l["ansprechpartner"]))
    return render_template("angebot.html", l=l, zeilen_text=zeilen_text, positionen=positionen, netto=netto)


# ---------------------------------------------------------------------------
# Postausgang (E-Mails & Briefe aus beiden Modulen)
# ---------------------------------------------------------------------------
@app.route("/postausgang")
def postausgang():
    status = request.args.get("status", "entwurf")
    liste = con().execute(
        """SELECT n.*, l.firma, m.name AS mieter FROM nachrichten n LEFT JOIN leads l ON l.id=n.lead_id
           LEFT JOIN mieter m ON m.id=n.mieter_id WHERE n.status=? ORDER BY n.erstellt DESC LIMIT 500""",
        (status,),
    ).fetchall()
    return render_template("postausgang.html", liste=liste, status=status)


@app.post("/nachricht/<int:nid>/<aktion>")
def nachricht_aktion(nid, aktion):
    c = con()
    n = c.execute("SELECT * FROM nachrichten WHERE id=?", (nid,)).fetchone() or abort(404)
    if aktion == "senden":
        try:
            mailer.senden(n["empfaenger"], n["betreff"], n["text"])
            c.execute("UPDATE nachrichten SET status='gesendet', gesendet=datetime('now') WHERE id=?", (nid,))
            flash(f"E-Mail an {n['empfaenger']} gesendet.")
        except Exception as e:  # noqa: BLE001
            flash(f"Senden fehlgeschlagen: {e}")
    elif aktion == "gedruckt":
        c.execute("UPDATE nachrichten SET status='gedruckt', gesendet=datetime('now') WHERE id=?", (nid,))
    elif aktion == "verwerfen":
        c.execute("UPDATE nachrichten SET status='verworfen' WHERE id=?", (nid,))
    elif aktion == "bearbeiten":
        c.execute("UPDATE nachrichten SET betreff=?, text=? WHERE id=?", (_f("betreff"), request.form.get("text", ""), nid))
    c.commit()
    return redirect(request.referrer or url_for("postausgang"))


@app.route("/briefe/druck")
def briefe_druck():
    """Alle Brief-Entwürfe als druckfertige Seiten (DIN-A4, Fensterkuvert) – Serienbrief."""
    ids = request.args.getlist("id", type=int)
    sql = "SELECT * FROM nachrichten WHERE kanal='brief' AND "
    liste = con().execute(sql + (f"id IN ({','.join('?' * len(ids))})" if ids else "status='entwurf'"), ids).fetchall()
    return render_template("brief_druck.html", liste=liste, datum=dt.date.today().strftime("%d.%m.%Y"))


@app.post("/briefe/alle-gedruckt")
def briefe_alle_gedruckt():
    con().execute("UPDATE nachrichten SET status='gedruckt', gesendet=datetime('now') WHERE kanal='brief' AND status='entwurf'")
    con().commit()
    return redirect(url_for("postausgang"))


# ---------------------------------------------------------------------------
# Öffentliche Landingpage + Anfrageformular (Hausmeister Helden)
# ---------------------------------------------------------------------------
@app.route("/helden")
def landing():
    return render_template("landing.html")


@app.post("/anfrage")
def anfrage():
    if request.form.get("website"):  # Honeypot gegen Spam-Bots
        return redirect(url_for("danke"))
    if not _f("firma") and not _f("ansprechpartner") or not (_f("email") or _f("telefon")):
        flash("Bitte Name und E-Mail oder Telefon angeben.")
        return redirect(url_for("landing") + "#anfrage")
    c = con()
    cur = c.execute(
        """INSERT INTO leads(firma, ansprechpartner, email, telefon, plz_ort, typ, quelle, status, einheiten_geschaetzt, notiz, schritt)
           VALUES (?,?,?,?,?,?,'Website-Anfrage','interessiert',?,?,3)""",
        (_f("firma") or _f("ansprechpartner"), _f("ansprechpartner"), _f("email"), _f("telefon"), _f("plz_ort"),
         _f("typ", "Hausverwaltung"), int(_zahl(_f("einheiten")) or 0), _f("nachricht")),
    )
    lid = cur.lastrowid
    db.add_task(c, "akquise", f"anfrage-{lid}", f"🔥 NEUE ANFRAGE: {_f('firma') or _f('ansprechpartner')} – {_f('telefon') or _f('email')} (innerhalb 24 h melden!)",
                dt.date.today().isoformat())
    if _f("email"):
        daten = dict(db.settings(c))
        daten.update(briefanrede=f"Guten Tag {_f('ansprechpartner')}".strip() if _f("ansprechpartner") else "Guten Tag", telefon=_f("telefon") or "Ihre Telefonnummer", nachricht=_f("nachricht"))
        betreff = vorlagen.fuellen(vorlagen.ANFRAGE_AUTOANTWORT["betreff"], daten)
        text = vorlagen.fuellen(vorlagen.ANFRAGE_AUTOANTWORT["text"], daten)
        cur = c.execute("INSERT INTO nachrichten(lead_id, kanal, empfaenger, betreff, text) VALUES (?,?,?,?,?)",
                        (lid, "email", _f("email"), betreff, text))
        if mailer.konfiguriert():  # Eingangsbestätigung ist keine Werbung -> sofort senden
            try:
                mailer.senden(_f("email"), betreff, text)
                c.execute("UPDATE nachrichten SET status='gesendet', gesendet=datetime('now') WHERE id=?", (cur.lastrowid,))
            except Exception:  # noqa: BLE001
                pass
        benachrichtigung = os.environ.get("BENACHRICHTIGUNG_EMAIL")
        if benachrichtigung and mailer.konfiguriert():
            try:
                mailer.senden(benachrichtigung, f"Neue Anfrage: {_f('firma') or _f('ansprechpartner')}",
                              "\n".join(f"{k}: {v}" for k, v in request.form.items() if k != "website"))
            except Exception:  # noqa: BLE001
                pass
    c.commit()
    return redirect(url_for("danke"))


@app.route("/helden/danke")
def danke():
    return render_template("danke.html")


# ---------------------------------------------------------------------------
# Einstellungen
# ---------------------------------------------------------------------------
@app.route("/einstellungen", methods=["GET", "POST"])
def einstellungen():
    c = con()
    if request.method == "POST":
        for k in db.DEFAULT_SETTINGS:
            if k == "auto_senden":
                c.execute("UPDATE einstellungen SET wert=? WHERE schluessel=?", ("1" if request.form.get(k) else "0", k))
            elif k in request.form:
                c.execute("UPDATE einstellungen SET wert=? WHERE schluessel=?", (request.form[k].strip(), k))
        c.commit()
        flash("Einstellungen gespeichert.")
        return redirect(url_for("einstellungen"))
    return render_template("einstellungen.html")


def main():
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")), debug=bool(os.environ.get("DEBUG")))


if __name__ == "__main__":
    main()
