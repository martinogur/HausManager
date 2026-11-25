"""Steuerungsoberfläche: alle Seiten erreichbar, Rechte, Freigaben, Akquise, Angebotsrechner, Aufträge, Einsatz mobil."""

import io
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from agenten import automatisierung, freigaben, laufzeit
from agenten.models import Freigabe
from auftraege.models import EinsatzMitarbeiter
from dokumente.models import Foto
from personal.models import Arbeitszeit
from stammdaten import testhilfen as th
from vertrieb.models import Lead, LeadKontakt

pytestmark = pytest.mark.django_db

SEITEN = ["cockpit:menue", "cockpit:freigaben", "cockpit:agenten", "cockpit:automatisierungen", "cockpit:akquise",
          "cockpit:angebot_rechner", "cockpit:auftraege", "cockpit:controlling", "cockpit:marketing", "berichte:dashboard"]


@pytest.fixture
def registriert(db):
    laufzeit.synchronisieren()
    automatisierung.synchronisieren()


@pytest.mark.parametrize("name", SEITEN)
def test_buero_sieht_alle_seiten(client, buero_benutzer, angemeldet, registriert, name):
    angemeldet(client, buero_benutzer)
    antwort = client.get(reverse(name))
    assert antwort.status_code == 200, name
    inhalt = antwort.content.decode()
    for titel in ("Kunden", "Objekte", "Aufträge", "Mitarbeiter", "Bewerbungen", "Akquise", "Angebote", "Rechnungen",
                  "E-Mails", "Marketing", "KI-Agenten", "Automatisierungen", "Controlling", "Einstellungen", "Freigaben"):
        assert f"<span>{titel}</span>" in inhalt, titel


@pytest.mark.parametrize("name", SEITEN[:-1])
def test_mitarbeiter_kein_zugriff(client, mitarbeiter_benutzer, angemeldet, name):
    angemeldet(client, mitarbeiter_benutzer, zwei_faktor=False)
    assert client.get(reverse(name)).status_code == 403


def test_nicht_angemeldet_wird_umgeleitet(client):
    assert client.get(reverse("cockpit:freigaben")).status_code == 302


def test_freigabe_entscheiden_ueber_oberflaeche(client, buero_benutzer, angemeldet, registriert):
    lead = Lead.objects.create(firma="UI Verwaltung GmbH", zielgruppe="hausverwaltung", quelle="Test", plz="33330",
                               strasse="Weg 1", ort="Gütersloh")
    f = freigaben.anfordern(art="lead_kontakt", titel="Brief", angefordert_von="agent:sales", bezug=("leads", lead.id),
                            vorschlag={"lead_id": str(lead.id), "kanal": "brief", "text": "Alt"})
    angemeldet(client, buero_benutzer)
    seite = client.get(reverse("cockpit:freigaben_detail", args=[f.pk]))
    assert "Alt" in seite.content.decode()
    antwort = client.post(reverse("cockpit:freigaben_detail", args=[f.pk]), {"entscheidung": "freigeben", "text": "Neu"})
    assert antwort.status_code == 302
    f.refresh_from_db()
    assert f.status == "freigegeben" and f.vorschlag["text"] == "Neu" and f.entschieden_von == buero_benutzer
    # Danach: Kontakt mit Freigabe dokumentieren
    client.post(reverse("cockpit:akquise_lead", args=[lead.pk]),
                {"aktion": "kontakt", "kanal": "brief", "zusammenfassung": "Brief versendet", "freigabe": str(f.pk)})
    assert LeadKontakt.objects.get(lead=lead).freigabe == f


def test_lead_anlegen_und_uwg_schutz_in_oberflaeche(client, buero_benutzer, angemeldet):
    angemeldet(client, buero_benutzer)
    antwort = client.post(reverse("cockpit:akquise_neu"), {
        "firma": "Neue Verwaltung KG", "zielgruppe": "hausverwaltung", "plz": "33378", "ort": "Rheda-Wiedenbrück",
        "strasse": "Hauptstr. 1", "email": "info@example.org", "quelle": "Impressum (Test)", "bedarf": "ja", "umsatz": "600"})
    lead = Lead.objects.get(firma="Neue Verwaltung KG")
    assert antwort.status_code == 302 and lead.prioritaet in ("A", "B") and lead.geschaetzter_monatsumsatz_cent == 60000
    # Werbe-E-Mail ohne Einwilligung → Datenbank lehnt ab, Meldung statt Fehlerseite
    antwort = client.post(reverse("cockpit:akquise_lead", args=[lead.pk]),
                          {"aktion": "kontakt", "kanal": "email", "zusammenfassung": "Mail"}, follow=True)
    assert "Nicht zulässig" in antwort.content.decode() and not LeadKontakt.objects.exists()
    # Ohne Quelle kein Lead
    client.post(reverse("cockpit:akquise_neu"), {"firma": "Ohne Quelle", "zielgruppe": "buero", "quelle": ""})
    assert not Lead.objects.filter(firma="Ohne Quelle").exists()


def test_angebotsrechner_berechnet_und_legt_entwurf_an(client, buero_benutzer, angemeldet, registriert):
    o = th.objekt(th.kunde(), treppenhaeuser=1, etagen=3)
    angemeldet(client, buero_benutzer)
    antwort = client.post(reverse("cockpit:angebot_rechner"), {"objekt": str(o.pk), "reinigung": "woechentlich"})
    assert antwort.context["ergebnis"].monat_netto_cent == 15600
    antwort = client.post(reverse("cockpit:angebot_rechner"), {"objekt": str(o.pk), "reinigung": "woechentlich", "anlegen": "1"})
    assert antwort.status_code == 302 and Freigabe.objects.filter(art="angebot_versand").exists()


def test_auftrag_status_ueber_oberflaeche(client, buero_benutzer, angemeldet, registriert):
    a = th.auftrag(status="anfrage")
    angemeldet(client, buero_benutzer)
    seite = client.get(reverse("cockpit:auftraege_detail", args=[a.pk])).content.decode()
    assert "Zu prüfen" in seite
    client.post(reverse("cockpit:auftraege_detail", args=[a.pk]), {"status": "zu_pruefen"})
    a.refresh_from_db()
    assert a.status == "zu_pruefen"
    antwort = client.post(reverse("cockpit:auftraege_detail", args=[a.pk]), {"status": "abgerechnet"}, follow=True)
    assert "nicht direkt" in antwort.content.decode()


def _jpeg_mit_gps() -> bytes:
    bild = Image.new("RGB", (40, 30), "green")
    exif = Image.Exif()
    exif[0x010F] = "Testkamera"          # Make
    exif[0x8825] = {2: (51.0, 54.0, 25.0)}  # GPSInfo
    puffer = io.BytesIO()
    bild.save(puffer, "JPEG", exif=exif)
    return puffer.getvalue()


def test_mitarbeiter_einsatz_mobil(client, mitarbeiter_benutzer, angemeldet, registriert, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    from django.core.files.uploadedfile import SimpleUploadedFile

    ma = th.mitarbeiter(konto=mitarbeiter_benutzer)
    a = th.auftrag(status="geplant")
    e = th.einsatz(a, von=timezone.now() - timedelta(hours=1), bis=timezone.now() + timedelta(hours=1), status="zugewiesen")
    EinsatzMitarbeiter.objects.create(einsatz=e, mitarbeiter=ma)
    k2 = th.kunde(name="Fremd GmbH")
    fremd = th.einsatz(th.auftrag(kunde_obj=k2, objekt_obj=th.objekt(k2, strasse="Andere Straße"), status="geplant"))
    angemeldet(client, mitarbeiter_benutzer, zwei_faktor=False)
    assert client.get(reverse("cockpit:einsatz", args=[fremd.pk])).status_code == 404
    url = reverse("cockpit:einsatz", args=[e.pk])
    assert "Start" in client.get(url).content.decode()
    client.post(url, {"aktion": "start"})
    e.refresh_from_db()
    a.refresh_from_db()
    assert e.status == "in_arbeit" and a.status == "in_arbeit"
    client.post(url, {"aktion": "foto", "typ": "vorher", "foto": SimpleUploadedFile("v.jpg", _jpeg_mit_gps(), "image/jpeg")})
    foto = Foto.objects.get(einsatz=e)
    gespeichert = Image.open(tmp_path / foto.dokument.speicher_schluessel)
    assert not gespeichert.getexif(), "EXIF/GPS muss entfernt sein"
    assert client.get(reverse("cockpit:foto", args=[foto.pk])).status_code == 200
    antwort = client.post(url, {"aktion": "erledigt"}, follow=True)
    assert "Arbeitszeit stoppen" in antwort.content.decode()
    client.post(url, {"aktion": "stopp", "pause": "0"})
    client.post(url, {"aktion": "bericht", "bericht": "Treppenhaus gereinigt"})
    client.post(url, {"aktion": "erledigt"})
    e.refresh_from_db()
    assert e.status == "erledigt" and e.bericht_mitarbeiter == "Treppenhaus gereinigt"
    assert Arbeitszeit.objects.get(einsatz=e).ende is not None


def test_foto_eines_fremden_einsatzes_nicht_abrufbar(client, mitarbeiter_benutzer, benutzer_anlegen, angemeldet, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    from django.core.files.uploadedfile import SimpleUploadedFile

    from cockpit import fotos

    e = th.einsatz()
    f = fotos.speichern(e, SimpleUploadedFile("x.jpg", _jpeg_mit_gps()), "nachher", None)
    angemeldet(client, mitarbeiter_benutzer, zwei_faktor=False)
    assert client.get(reverse("cockpit:foto", args=[f.pk])).status_code == 404


def test_agenten_aufgabe_von_hand_und_nur_erlaubte(client, buero_benutzer, angemeldet, registriert):
    angemeldet(client, buero_benutzer)
    antwort = client.post(reverse("cockpit:agenten_starten"), {"agent": "automation", "aufgabe": "ueberwachung"})
    assert antwort.status_code == 302
    assert client.post(reverse("cockpit:agenten_starten"), {"agent": "finance", "aufgabe": "abrechnung_vorbereiten"}).status_code == 403
    # Ein- und Ausschalten nur für Admin
    assert client.post(reverse("cockpit:agenten_schalten", args=["sales"])).status_code == 403
