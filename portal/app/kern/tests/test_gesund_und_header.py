"""Gesundheitsprüfung und Sicherheits-Header."""

import pytest
from django.test import override_settings


@pytest.mark.django_db
def test_gesund_antwortet_200_ohne_interna(client):
    antwort = client.get("/gesund")
    assert antwort.status_code == 200
    assert antwort.json() == {"status": "ok"}
    assert "no-cache" in antwort["Cache-Control"] or "max-age=0" in antwort["Cache-Control"]


@pytest.mark.django_db
def test_gesund_ohne_anmeldung_und_ohne_https_umleitung(client):
    with override_settings(SECURE_SSL_REDIRECT=True):
        assert client.get("/gesund").status_code == 200
        # Andere Seiten werden auf https umgeleitet
        antwort = client.get("/anmelden/")
        assert antwort.status_code == 301
        assert antwort["Location"].startswith("https://")


@pytest.mark.django_db
def test_sicherheits_header_gesetzt(client):
    antwort = client.get("/anmelden/")
    assert antwort.status_code == 200
    assert antwort["X-Frame-Options"] == "DENY"
    assert antwort["X-Content-Type-Options"] == "nosniff"
    assert antwort["Referrer-Policy"] == "same-origin"
    assert antwort["Cross-Origin-Opener-Policy"] == "same-origin"
    csp = antwort["Content-Security-Policy"]
    assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp and "script-src 'self'" in csp
    assert "Permissions-Policy" in antwort


@pytest.mark.django_db
def test_hsts_bei_https(client, settings):
    if not settings.SECURE_HSTS_SECONDS:
        pytest.skip("HSTS ist nur ohne DEBUG aktiv")
    antwort = client.get("/anmelden/", secure=True)
    assert antwort["Strict-Transport-Security"].startswith("max-age=31536000")


@pytest.mark.django_db
def test_sitzungs_cookie_sicher(client, mitarbeiter_benutzer, settings):
    from conftest import TEST_PASSWORT

    antwort = client.post("/anmelden/", {"username": mitarbeiter_benutzer.email, "password": TEST_PASSWORT})
    assert antwort.status_code == 302
    cookie = antwort.cookies[settings.SESSION_COOKIE_NAME]
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"
    assert cookie["max-age"] == 8 * 60 * 60
    if not settings.DEBUG:
        assert cookie["secure"]


@pytest.mark.django_db
def test_eigene_404_seite(client):
    antwort = client.get("/gibt-es-nicht/")
    assert antwort.status_code == 404
    assert "Seite nicht gefunden" in antwort.content.decode()
