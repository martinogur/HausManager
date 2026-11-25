"""
Gemeinsame Test-Hilfen für alle Apps (pytest-django).

Fixtures
--------
benutzer_anlegen(rolle="mitarbeiter", email=None, passwort=TEST_PASSWORT, **felder) -> Benutzer
admin_benutzer, buero_benutzer, mitarbeiter_benutzer                               -> Benutzer
totp_geraet(benutzer) -> bestätigtes TOTPDevice
angemeldet(client, benutzer, zwei_faktor=True) -> client (Sitzung inkl. bestätigtem 2FA)
testdaten_einsatz(benutzer=None) -> dict mit IDs (Kunde, Objekt, Auftrag, Einsatz heute, Mitarbeiter)

Hilfsfunktion
-------------
totp_code(geraet) -> aktueller sechsstelliger Code

Nur Beispieldaten (example.org), keine echten Personen oder Firmen.
"""

from datetime import datetime, time, timedelta

import pytest
from django.db import connection
from django.utils import timezone

# Nur für Tests – erfüllt die Passwortregeln (mind. 12 Zeichen).
TEST_PASSWORT = "Beispiel-Passwort-2026!"


def totp_code(geraet) -> str:
    """Aktueller TOTP-Code eines Geräts (wie ihn die Authenticator-App anzeigen würde)."""
    from django_otp.oath import totp

    return f"{totp(geraet.bin_key, geraet.step, geraet.t0, geraet.digits, geraet.drift):0{geraet.digits}d}"


@pytest.fixture(autouse=True)
def _zwischenspeicher_leeren(db):
    """Anmeldesperren usw. dürfen nicht von einem Test in den nächsten wandern."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def benutzer_anlegen(db):
    from konten.models import Benutzer

    zaehler = {"n": 0}

    def _anlegen(rolle="mitarbeiter", email=None, passwort=TEST_PASSWORT, **felder):
        zaehler["n"] += 1
        email = email or f"{rolle}{zaehler['n']}@example.org"
        felder.setdefault("anzeigename", f"Test {rolle.capitalize()} {zaehler['n']}")
        return Benutzer.objects.create_user(email=email, password=passwort, rolle=rolle, **felder)

    return _anlegen


@pytest.fixture
def admin_benutzer(benutzer_anlegen):
    return benutzer_anlegen("admin", email="admin@example.org", anzeigename="Anna Admin")


@pytest.fixture
def buero_benutzer(benutzer_anlegen):
    return benutzer_anlegen("buero", email="buero@example.org", anzeigename="Bernd Büro")


@pytest.fixture
def mitarbeiter_benutzer(benutzer_anlegen):
    return benutzer_anlegen("mitarbeiter", email="mitarbeiter@example.org", anzeigename="Mia Mitarbeiterin")


@pytest.fixture
def totp_geraet(db):
    from django_otp.plugins.otp_totp.models import TOTPDevice

    def _geraet(benutzer):
        return TOTPDevice.objects.create(user=benutzer, name="Test-App", confirmed=True)

    return _geraet


@pytest.fixture
def angemeldet(totp_geraet):
    """Meldet einen Benutzer im Test-Client an; für admin/buero standardmäßig mit bestätigtem 2FA."""
    from django_otp import DEVICE_ID_SESSION_KEY

    def _anmelden(client, benutzer, zwei_faktor=True):
        client.force_login(benutzer)
        if zwei_faktor:
            geraet = totp_geraet(benutzer)
            sitzung = client.session
            sitzung[DEVICE_ID_SESSION_KEY] = geraet.persistent_id
            sitzung.save()
        return client

    return _anmelden


def _sql_eins(sql, parameter=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, parameter or [])
        return cursor.fetchone()[0]


@pytest.fixture
def testdaten_einsatz(db):
    """
    Legt per SQL (unabhängig von den Fachmodellen) einen Kunden mit Objekt,
    Auftrag und einem Einsatz heute 10–12 Uhr an. Mit ``benutzer`` wird ein
    Mitarbeiter mit diesem Benutzerkonto verknüpft und dem Einsatz zugeteilt.
    """
    zaehler = {"n": 0}

    def _anlegen(benutzer=None, stunde=10, tag=None):
        zaehler["n"] += 1
        n = zaehler["n"]
        tag = tag or timezone.localdate()
        von = timezone.make_aware(datetime.combine(tag, time(stunde, 0)))
        bis = von + timedelta(hours=2)
        kunde = _sql_eins(
            "INSERT INTO kunden (name, typ, status, plz, ort) VALUES (%s, 'hausverwaltung', 'aktiv', '10115', 'Musterstadt') RETURNING id",
            [f"Beispiel Hausverwaltung {n}"],
        )
        objekt = _sql_eins(
            "INSERT INTO objekte (kunde_id, bezeichnung, strasse, hausnummer, plz, ort) "
            "VALUES (%s, %s, 'Musterstraße', %s, '10115', 'Musterstadt') RETURNING id",
            [kunde, f"WEG Musterstraße {n}", str(n)],
        )
        auftrag = _sql_eins(
            "INSERT INTO auftraege (kunde_id, objekt_id, titel, status) VALUES (%s, %s, %s, 'geplant') RETURNING id",
            [kunde, objekt, f"Treppenhausreinigung {n}"],
        )
        einsatz = _sql_eins(
            "INSERT INTO einsaetze (auftrag_id, geplant_von, geplant_bis, status) VALUES (%s, %s, %s, 'zugewiesen') RETURNING id",
            [auftrag, von, bis],
        )
        mitarbeiter = None
        if benutzer is not None:
            # Vorhandenes Mitarbeiterprofil des Benutzers nutzen, sonst anlegen
            if _sql_eins("SELECT count(*) FROM mitarbeiter WHERE benutzer_id = %s", [benutzer.pk]):
                mitarbeiter = _sql_eins("SELECT id FROM mitarbeiter WHERE benutzer_id = %s", [benutzer.pk])
            else:
                mitarbeiter = _sql_eins(
                    "INSERT INTO mitarbeiter (vorname, nachname, beschaeftigung, benutzer_id) "
                    "VALUES ('Mia', %s, 'minijob', %s) RETURNING id",
                    [f"Beispiel{n}", benutzer.pk],
                )
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO einsatz_mitarbeiter (einsatz_id, mitarbeiter_id, zeitraum) VALUES (%s, %s, tstzrange(%s, %s))",
                    [einsatz, mitarbeiter, von, bis],
                )
        return {"kunde": kunde, "objekt": objekt, "auftrag": auftrag, "einsatz": einsatz, "mitarbeiter": mitarbeiter,
                "titel": f"Treppenhausreinigung {n}"}

    return _anlegen
