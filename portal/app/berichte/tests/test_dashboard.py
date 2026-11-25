"""Dashboard: Kennzahlen für Büro/Admin, reduzierte Startseite für Mitarbeiter."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_buero_sieht_kennzahlen_und_heute_zu_tun(client, buero_benutzer, mitarbeiter_benutzer, angemeldet,
                                                  testdaten_einsatz):
    daten = testdaten_einsatz(benutzer=mitarbeiter_benutzer)
    testdaten_einsatz(stunde=14)  # zweiter Einsatz heute, ohne Mitarbeiter
    angemeldet(client, buero_benutzer)
    antwort = client.get("/")
    assert antwort.status_code == 200
    inhalt = antwort.content.decode()
    assert "Kennzahlen" in inhalt and "Heute zu tun" in inhalt
    assert daten["titel"] in inhalt
    assert "Einsätze heute ohne Mitarbeiter" in inhalt
    k = antwort.context["k"]
    assert k["einsaetze_heute"] == 2
    assert k["kunden_aktiv"] == 2
    assert k["objekte"] == 2
    assert k["auftraege_offen"] == 2


@pytest.mark.django_db
def test_kennzahlen_per_htmx(client, admin_benutzer, angemeldet):
    angemeldet(client, admin_benutzer)
    antwort = client.get(reverse("berichte:kennzahlen"), headers={"HX-Request": "true"})
    assert antwort.status_code == 200
    inhalt = antwort.content.decode()
    assert 'id="kennzahlen"' in inhalt
    assert "<html" not in inhalt
    assert 'hx-trigger="every 60s"' in inhalt


@pytest.mark.django_db
def test_mitarbeiter_sieht_reduziertes_dashboard(client, mitarbeiter_benutzer, angemeldet, testdaten_einsatz):
    eigener = testdaten_einsatz(benutzer=mitarbeiter_benutzer)
    fremder = testdaten_einsatz(stunde=15)
    angemeldet(client, mitarbeiter_benutzer, zwei_faktor=False)
    antwort = client.get("/")
    assert antwort.status_code == 200
    inhalt = antwort.content.decode()
    assert "Meine Einsätze heute" in inhalt
    assert eigener["titel"] in inhalt
    assert fremder["titel"] not in inhalt
    assert "Kennzahlen" not in inhalt and "Umsatz" not in inhalt
    assert "Verwaltung" not in inhalt  # kein Link in die Verwaltungsoberfläche
    assert "k" not in antwort.context


@pytest.mark.django_db
def test_mitarbeiter_darf_kennzahlen_nicht_abrufen(client, mitarbeiter_benutzer, angemeldet):
    angemeldet(client, mitarbeiter_benutzer, zwei_faktor=False)
    antwort = client.get(reverse("berichte:kennzahlen"))
    assert antwort.status_code == 403
    assert "Kein Zugriff" in antwort.content.decode()


@pytest.mark.django_db
def test_kennzahlen_ohne_anmeldung_htmx(client):
    antwort = client.get(reverse("berichte:kennzahlen"), headers={"HX-Request": "true"})
    assert antwort["HX-Redirect"].startswith(reverse("konten:anmelden"))
