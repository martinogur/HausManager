"""Anmeldung, Abmeldung und Anmeldesperre."""

import pytest
from django.urls import reverse

from conftest import TEST_PASSWORT


def _anmelden(client, email, passwort=TEST_PASSWORT, **extra):
    return client.post(reverse("konten:anmelden"), {"username": email, "password": passwort}, **extra)


@pytest.mark.django_db
def test_anmeldeseite_erreichbar(client):
    antwort = client.get(reverse("konten:anmelden"))
    assert antwort.status_code == 200
    inhalt = antwort.content.decode()
    assert '<label for="id_username">E-Mail</label>' in inhalt
    assert '<html lang="de">' in inhalt


@pytest.mark.django_db
def test_dashboard_ohne_anmeldung_leitet_um(client):
    antwort = client.get("/")
    assert antwort.status_code == 302
    assert antwort["Location"].startswith(reverse("konten:anmelden"))


@pytest.mark.django_db
def test_anmeldung_funktioniert(client, mitarbeiter_benutzer):
    antwort = _anmelden(client, mitarbeiter_benutzer.email)
    assert antwort.status_code == 302
    assert antwort["Location"] == reverse("berichte:dashboard")
    assert client.get("/").status_code == 200
    mitarbeiter_benutzer.refresh_from_db()
    assert mitarbeiter_benutzer.last_login is not None


@pytest.mark.django_db
def test_email_ohne_beachtung_der_schreibweise(client, mitarbeiter_benutzer):
    assert _anmelden(client, "MITARBEITER@Example.org").status_code == 302


@pytest.mark.django_db
def test_falsches_passwort(client, mitarbeiter_benutzer):
    antwort = _anmelden(client, mitarbeiter_benutzer.email, "falsch-falsch-falsch")
    assert antwort.status_code == 200
    assert "E-Mail oder Passwort ist falsch." in antwort.content.decode()


@pytest.mark.django_db
def test_deaktivierter_benutzer_kann_sich_nicht_anmelden(client, benutzer_anlegen):
    benutzer = benutzer_anlegen("mitarbeiter", aktiv=False)
    assert _anmelden(client, benutzer.email).status_code == 200
    assert client.get("/").status_code == 302


@pytest.mark.django_db
def test_passwort_mit_argon2_gespeichert(mitarbeiter_benutzer):
    assert mitarbeiter_benutzer.password.startswith("argon2$")


@pytest.mark.django_db
def test_sperre_nach_fuenf_fehlversuchen(client, mitarbeiter_benutzer):
    for _ in range(4):
        antwort = _anmelden(client, mitarbeiter_benutzer.email, "falsches-passwort")
        assert "gesperrt" not in antwort.content.decode()
    antwort = _anmelden(client, mitarbeiter_benutzer.email, "falsches-passwort")
    assert "gesperrt" in antwort.content.decode()
    # Auch mit richtigem Passwort jetzt gesperrt
    antwort = _anmelden(client, mitarbeiter_benutzer.email)
    assert antwort.status_code == 200
    assert "15 Minuten gesperrt" in antwort.content.decode()
    assert client.get("/").status_code == 302


@pytest.mark.django_db
def test_sperre_laeuft_ab(client, mitarbeiter_benutzer):
    from django.core.cache import cache

    for _ in range(5):
        _anmelden(client, mitarbeiter_benutzer.email, "falsches-passwort")
    assert _anmelden(client, mitarbeiter_benutzer.email).status_code == 200
    cache.clear()  # entspricht dem Ablauf der 15 Minuten
    assert _anmelden(client, mitarbeiter_benutzer.email).status_code == 302


@pytest.mark.django_db
def test_sperre_auch_fuer_unbekannte_konten(client):
    """Die Sperre verrät nicht, ob ein Konto existiert."""
    for _ in range(5):
        antwort = _anmelden(client, "unbekannt@example.org", "x" * 12)
    assert "gesperrt" in antwort.content.decode()


@pytest.mark.django_db
def test_erfolg_setzt_zaehler_zurueck(client, mitarbeiter_benutzer):
    for _ in range(4):
        _anmelden(client, mitarbeiter_benutzer.email, "falsches-passwort")
    assert _anmelden(client, mitarbeiter_benutzer.email).status_code == 302
    client.post(reverse("konten:abmelden"))
    for _ in range(4):
        _anmelden(client, mitarbeiter_benutzer.email, "falsches-passwort")
    assert _anmelden(client, mitarbeiter_benutzer.email).status_code == 302


@pytest.mark.django_db
def test_abmelden_nur_per_post(client, mitarbeiter_benutzer, angemeldet):
    angemeldet(client, mitarbeiter_benutzer, zwei_faktor=False)
    assert client.get(reverse("konten:abmelden")).status_code == 405
    antwort = client.post(reverse("konten:abmelden"))
    assert antwort.status_code == 302
    assert client.get("/").status_code == 302


@pytest.mark.django_db
def test_offene_weiterleitung_verhindert(client, mitarbeiter_benutzer):
    antwort = client.post(
        reverse("konten:anmelden"),
        {"username": mitarbeiter_benutzer.email, "password": TEST_PASSWORT, "next": "https://boese.example.com/"},
    )
    assert antwort["Location"] == reverse("berichte:dashboard")
