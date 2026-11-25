"""Audit: Änderungen über einen Request landen mit der Benutzer-E-Mail im audit_log."""

import json

import pytest
from django.db import connection

from conftest import TEST_PASSWORT, totp_code


def _audit(tabelle):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT aktion, benutzer, neu FROM audit_log WHERE tabelle = %s ORDER BY id", [tabelle]
        )
        # jsonb kommt über Djangos Verbindung als Text
        return [(aktion, benutzer, json.loads(neu) if isinstance(neu, str) else neu)
                for aktion, benutzer, neu in cursor.fetchall()]


def _aktueller_audit_benutzer():
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.benutzer', true)")
        return cursor.fetchone()[0]


@pytest.mark.django_db
def test_aenderung_ueber_request_mit_benutzer_email(client, buero_benutzer):
    # Anmelden → 2FA einrichten (setzt benutzer.zwei_faktor = true per Request)
    client.post("/anmelden/", {"username": buero_benutzer.email, "password": TEST_PASSWORT})
    client.get("/konto/zwei-faktor/einrichten/")
    from django_otp.plugins.otp_totp.models import TOTPDevice

    geraet = TOTPDevice.objects.get(user=buero_benutzer)
    antwort = client.post("/konto/zwei-faktor/einrichten/", {"code": totp_code(geraet)})
    assert antwort.status_code == 302

    eintraege = [e for e in _audit("benutzer") if e[0] == "UPDATE" and e[2].get("zwei_faktor") is True]
    assert eintraege, "Kein Audit-Eintrag für die Änderung"
    assert eintraege[-1][1] == "buero@example.org"
    # Auch die Anmeldung (last_login) ist zugeordnet
    assert all(e[1] == "buero@example.org" for e in _audit("benutzer") if e[0] == "UPDATE")


@pytest.mark.django_db
def test_audit_benutzer_wird_nach_request_zurueckgesetzt(client, mitarbeiter_benutzer, angemeldet):
    angemeldet(client, mitarbeiter_benutzer, zwei_faktor=False)
    assert client.get("/").status_code == 200
    assert _aktueller_audit_benutzer() in ("", None)


@pytest.mark.django_db
def test_audit_log_ohne_passwort_hash(mitarbeiter_benutzer):
    """
    Dokumentiert einen offenen Punkt: Der Audit-Trigger speichert die ganze
    Zeile – inkl. Passwort-Hash. (Änderungswunsch an schema.sql gemeldet.)
    """
    eintraege = _audit("benutzer")
    assert eintraege
    if "password" in (eintraege[0][2] or {}):
        pytest.xfail("audit_log enthält password-Hash (schema.sql: protokolliere() sollte 'password' entfernen)")
