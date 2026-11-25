"""
Legt klar erkennbare, FIKTIVE Testdaten an (Firmen „Beispiel …“, Adressen „Muster…“,
E-Mails @example.org). Mehrfach ausführbar ohne Dubletten.

    python manage.py testdaten            # anlegen bzw. ergänzen
    python manage.py testdaten --loeschen # nur die Testdaten wieder entfernen

Der Leistungskatalog verwendet die freigegebenen Preise aus ``firma/profil.md``
(Abschnitt „Preise“, netto in Cent). Er ist kein Testdatensatz und bleibt bei
``--loeschen`` erhalten.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from auftraege.models import (
    Anfrage,
    Angebot,
    Angebotsposition,
    Auftrag,
    Auftragsstatus,
    Einsatz,
    EinsatzMitarbeiter,
    Einsatzstatus,
    Kanal,
    Rechnung,
    Rechnungsstatus,
)
from kommunikation.models import EmailProtokoll, Mailrichtung, Mailstatus
from personal.models import (
    Arbeitszeit,
    Beschaeftigung,
    Bewerbung,
    Mitarbeiter,
    MitarbeiterQualifikation,
    Qualifikation,
    Stelle,
    Verfuegbarkeit,
)
from stammdaten.models import (
    Ansprechpartner,
    Intervall,
    Kunde,
    Kundenstatus,
    Kundentyp,
    Leistung,
    Leistungsvereinbarung,
    Objekt,
)

MARKE = "Testdaten (fiktiv)"
STELLEN_MARKE = " [Testdaten]"
POSTFACH = "postfach.test@example.org"
BERLIN = ZoneInfo("Europe/Berlin")

# Leistungskatalog – Preise laut firma/profil.md (freigegeben 24.11.2026), netto in Cent
LEISTUNGEN = [
    # code, name, einheit, preis_netto_cent, betriebskostenart
    ("STD", "Arbeitsstunde (Kleinreparaturen, Sonderarbeiten)", "Std.", 5350, "Hauswart"),
    ("STD-15", "Arbeitszeit je angefangene 15 Min. (mind. 30 Min.)", "je 15 Min.", 1350, "Hauswart"),
    ("ANF-NAH", "Anfahrt Gütersloh bis 10 km", "je Anfahrt", 1450, None),
    ("ANF-UMLAND", "Anfahrt Umland 10–25 km", "je Anfahrt", 3650, None),
    ("TH-REINIGUNG", "Treppenhausreinigung", "je Treppenhaus und Reinigung", 1200, "Gebäudereinigung"),
    ("TH-ETAGE", "Treppenhausreinigung je Etage", "je Etage und Reinigung", 800, "Gebäudereinigung"),
    ("TH-AUFZUG", "Aufzugsreinigung", "je Reinigung", 445, "Gebäudereinigung"),
    ("WD-GRUND", "Winterdienst Grundpauschale (Nov–März)", "je Objekt und Saison", 22000, "Winterdienst"),
    ("WD-LFM", "Winterdienst je lfd. Meter inkl. Streugut und Protokoll", "je lfm und Saison", 950, "Winterdienst"),
    ("WD-EINZEL", "Winterdienst Einzeleinsatz ohne Vertrag", "je Einsatz", 4350, "Winterdienst"),
    ("GP-EINSATZ", "Gartenpflege Einsatzpauschale", "je Einsatz", 1350, "Gartenpflege"),
    ("GP-RASEN", "Rasenmähen", "je m² und Mahd", 14, "Gartenpflege"),
    ("GP-BEET", "Beetpflege", "je m²", 45, "Gartenpflege"),
    ("GP-HECKE", "Heckenschnitt", "je lfd. Meter", 178, "Gartenpflege"),
    ("GP-LAUB", "Laubentfernung", "je m²", 5, "Gartenpflege"),
    ("GP-GRUENSCHNITT", "Grünschnitt-Entsorgung", "je m² und Jahr", 11, "Gartenpflege"),
    ("MT-TERMIN", "Mülltonnen-Service je Abfuhrtermin", "je Abfuhrtermin", 650, "Müllbeseitigung"),
    ("MT-LEERUNG", "Mülltonnen-Service je Leerung", "je Leerung", 134, "Müllbeseitigung"),
    ("MT-MUELLPLATZ", "Müllplatz kehren", "je Woche", 445, "Müllbeseitigung"),
    ("OK-KONTROLLE", "Objektkontrolle mit Fotoprotokoll (eigener Termin)", "je Termin", 2700, "Hauswart"),
]

KUNDEN = [
    {
        "name": "Beispiel Hausverwaltung GmbH",
        "typ": Kundentyp.HAUSVERWALTUNG,
        "status": Kundenstatus.AKTIV,
        "strasse": "Musterstraße 1",
        "plz": "33330",
        "ort": "Gütersloh",
        "telefon": "05241 000000",
        "email": "kontakt@hausverwaltung.example.org",
        "webseite": "https://hausverwaltung.example.org",
    },
    {
        "name": "Muster-WEG Musterweg 5",
        "typ": Kundentyp.WEG,
        "status": Kundenstatus.AKTIV,
        "strasse": "Musterweg 5",
        "plz": "33332",
        "ort": "Gütersloh",
        "email": "beirat@muster-weg.example.org",
    },
    {
        "name": "Beispiel Gewerbepark KG",
        "typ": Kundentyp.GEWERBE,
        "status": Kundenstatus.INTERESSENT,
        "strasse": "Musterallee 1",
        "plz": "33378",
        "ort": "Rheda-Wiedenbrück",
        "email": "info@gewerbepark.example.org",
    },
]

MITARBEITER = [
    {
        "email": "mia.muster@example.org",
        "vorname": "Mia",
        "nachname": "Muster",
        "beschaeftigung": Beschaeftigung.MINIJOB,
        "wochenstunden_soll": Decimal("8.0"),
        "stundenlohn_cent": 1500,
        "fuehrerschein": False,
    },
    {
        "email": "tom.beispiel@example.org",
        "vorname": "Tom",
        "nachname": "Beispiel",
        "beschaeftigung": Beschaeftigung.TEILZEIT,
        "wochenstunden_soll": Decimal("20.0"),
        "stundenlohn_cent": 1800,
        "fuehrerschein": True,
    },
]
# Benutzerkonto (Rolle mitarbeiter, ohne nutzbares Passwort) für den Teilzeit-Hausmeister
TEST_BENUTZER_EMAIL = "tom.beispiel.login@example.org"


def zeitpunkt(tag, stunde, minute=0):
    return datetime.combine(tag, time(stunde, minute), tzinfo=BERLIN)


class Command(BaseCommand):
    help = "Legt fiktive Testdaten an (idempotent) oder entfernt sie mit --loeschen."

    def add_arguments(self, parser):
        parser.add_argument("--loeschen", action="store_true", help="Nur die Testdaten entfernen.")

    def handle(self, *args, **optionen):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('app.benutzer', 'befehl:testdaten', true)")
            if optionen["loeschen"]:
                self.loeschen()
            else:
                self.anlegen()

    # ------------------------------------------------------------------ Löschen
    def loeschen(self):
        kunden = Kunde.objects.filter(quelle=MARKE)
        mitarbeiter = Mitarbeiter.objects.filter(notizen=MARKE)
        stellen = Stelle.objects.filter(titel__endswith=STELLEN_MARKE)
        anzahl = {
            "E-Mails": EmailProtokoll.objects.filter(postfach=POSTFACH).delete()[0],
            "Rechnungen": Rechnung.objects.filter(kunde__in=kunden).delete()[0],
            "Arbeitszeiten": Arbeitszeit.objects.filter(mitarbeiter__in=mitarbeiter).delete()[0],
            "Aufträge (inkl. Einsätze)": Auftrag.objects.filter(kunde__in=kunden).delete()[0],
            "Angebote": Angebot.objects.filter(kunde__in=kunden).delete()[0],
            "Anfragen": Anfrage.objects.filter(kunde__in=kunden).delete()[0],
            "Objekte": Objekt.objects.filter(kunde__in=kunden).delete()[0],
            "Kunden": kunden.delete()[0],
            "Bewerbungen": Bewerbung.objects.filter(stelle__in=stellen).delete()[0],
            "Stellen": stellen.delete()[0],
            "Mitarbeiter": mitarbeiter.delete()[0],
            "Benutzer": get_user_model().objects.filter(email=TEST_BENUTZER_EMAIL).delete()[0],
        }
        for was, n in anzahl.items():
            self.stdout.write(f"  {was}: {n} Datensätze entfernt")
        self.stdout.write(self.style.SUCCESS("Testdaten entfernt (Leistungskatalog bleibt erhalten)."))

    # ------------------------------------------------------------------ Anlegen
    def anlegen(self):
        heute = timezone.localdate()
        jetzt = timezone.now()

        leistungen = {}
        for code, name, einheit, preis, bk in LEISTUNGEN:
            leistungen[code], _ = Leistung.objects.update_or_create(
                code=code,
                defaults={"name": name, "einheit": einheit, "preis_netto_cent": preis, "betriebskostenart": bk},
            )

        kunden = []
        for daten in KUNDEN:
            daten = dict(daten)
            kunde, _ = Kunde.objects.get_or_create(name=daten.pop("name"), defaults={**daten, "quelle": MARKE})
            kunden.append(kunde)
        hv, weg, gewerbe = kunden

        erika, _ = Ansprechpartner.objects.get_or_create(
            email="erika.mustermann@example.org",
            defaults={
                "kunde": hv,
                "anrede": "Frau",
                "vorname": "Erika",
                "nachname": "Mustermann",
                "funktion": "Objektbetreuung",
                "telefon": "05241 000001",
                "ist_hauptkontakt": True,
            },
        )
        Ansprechpartner.objects.get_or_create(
            email="max.beispiel@example.org",
            defaults={"kunde": weg, "anrede": "Herr", "vorname": "Max", "nachname": "Beispiel", "funktion": "Verwaltungsbeirat", "ist_hauptkontakt": True},
        )
        Ansprechpartner.objects.get_or_create(
            email="einkauf@gewerbepark.example.org",
            defaults={"kunde": gewerbe, "nachname": "Einkauf", "funktion": "Facility Management", "ist_hauptkontakt": True},
        )

        def objekt(kunde, bezeichnung, strasse, nr, plz, ort, **mehr):
            o, _ = Objekt.objects.get_or_create(
                strasse=strasse, hausnummer=nr, plz=plz,
                defaults={"kunde": kunde, "bezeichnung": bezeichnung, "ort": ort, **mehr},
            )
            return o

        ob10 = objekt(hv, "Wohnanlage Musterstraße 10", "Musterstraße", "10", "33330", "Gütersloh",
                      wohneinheiten=12, treppenhaeuser=2, etagen=4, aufzug=True,
                      gehweg_meter=Decimal("25.0"), gruenflaeche_qm=Decimal("300.0"), entfernung_km=Decimal("3.5"))
        ob12 = objekt(hv, "Wohnhaus Musterstraße 12", "Musterstraße", "12", "33330", "Gütersloh",
                      wohneinheiten=6, treppenhaeuser=1, etagen=3, gruenflaeche_qm=Decimal("450.0"), entfernung_km=Decimal("3.6"))
        ob_weg = objekt(weg, "WEG Musterweg 5", "Musterweg", "5", "33332", "Gütersloh",
                        wohneinheiten=8, treppenhaeuser=1, etagen=3, gehweg_meter=Decimal("15.0"), entfernung_km=Decimal("5.0"))
        ob_gew = objekt(gewerbe, "Gewerbepark Musterallee 1", "Musterallee", "1", "33378", "Rheda-Wiedenbrück",
                        gewerbeeinheiten=4, gehweg_meter=Decimal("40.0"), entfernung_km=Decimal("14.0"))

        # Mitarbeiter, Qualifikationen, Verfügbarkeiten, Benutzerkonto
        ma = {}
        for daten in MITARBEITER:
            daten = dict(daten)
            m, _ = Mitarbeiter.objects.get_or_create(
                email=daten.pop("email"), defaults={**daten, "eintritt": heute.replace(month=1, day=1), "notizen": MARKE}
            )
            ma[m.vorname] = m
        mia, tom = ma["Mia"], ma["Tom"]

        Benutzer = get_user_model()
        if not tom.benutzer_id:
            konto = Benutzer.objects.filter(email=TEST_BENUTZER_EMAIL).first() or Benutzer.objects.create_user(
                email=TEST_BENUTZER_EMAIL, anzeigename="Tom Beispiel (Test)", rolle="mitarbeiter"
            )
            tom.benutzer = konto
            tom.save()

        for name, leute in (("Reinigung", (mia, tom)), ("Winterdienst", (tom,)), ("Gartengeräte", (tom,))):
            q, _ = Qualifikation.objects.get_or_create(name=name)
            for m in leute:
                MitarbeiterQualifikation.objects.get_or_create(mitarbeiter=m, qualifikation=q)
        for m, tage, von, bis in ((mia, (2, 4), time(8), time(13)), (tom, (1, 2, 3, 4, 5), time(7), time(13))):
            if not m.verfuegbarkeiten.exists():
                Verfuegbarkeit.objects.bulk_create(
                    [Verfuegbarkeit(mitarbeiter=m, wochentag=t, von=von, bis=bis) for t in tage]
                )

        # Stellen & Bewerbungen
        aushilfe, _ = Stelle.objects.get_or_create(
            titel="Aushilfe Reinigung (Minijob)" + STELLEN_MARKE, defaults={"beschaeftigung": Beschaeftigung.MINIJOB}
        )
        hausmeister, _ = Stelle.objects.get_or_create(
            titel="Hausmeister Teilzeit" + STELLEN_MARKE, defaults={"beschaeftigung": Beschaeftigung.TEILZEIT}
        )
        for stelle, vorname, nachname, email in (
            (aushilfe, "Lena", "Probe", "lena.probe@example.org"),
            (hausmeister, "Jan", "Test", "jan.test@example.org"),
        ):
            Bewerbung.objects.get_or_create(
                email=email,
                stelle=stelle,
                defaults={
                    "vorname": vorname,
                    "nachname": nachname,
                    "wohnort": "Gütersloh",
                    "verfuegbar_ab": heute + timedelta(days=14),
                    "stunden_pro_woche": Decimal("10.0"),
                    "fuehrerschein": stelle == hausmeister,
                    "nachricht": "Fiktive Testbewerbung – keine echte Person.",
                    "datenschutz_ok_am": jetzt,
                },
            )

        # Vereinbarung: Treppenhausreinigung wöchentlich (dienstags) für Musterstraße 10
        th_vereinbarung, _ = Leistungsvereinbarung.objects.get_or_create(
            objekt=ob10,
            leistung=leistungen["TH-REINIGUNG"],
            defaults={
                "intervall": Intervall.WOECHENTLICH,
                "wochentag": 2,
                "menge": Decimal("2"),
                "preis_netto_cent": leistungen["TH-REINIGUNG"].preis_netto_cent,
                "gueltig_von": heute.replace(month=1, day=1),
                "standard_mitarbeiter": tom,
            },
        )

        # Anfrage + offenes Angebot (Entwurf, wartet auf Freigabe des Inhabers)
        anfrage, _ = Anfrage.objects.get_or_create(
            kunde=gewerbe,
            betreff="Testanfrage: Winterdienst Musterallee 1",
            defaults={
                "objekt": ob_gew,
                "kanal": Kanal.WEBSEITE,
                "gewuenschte_leistungen": ["Winterdienst"],
                "fehlende_angaben": ["Länge der Parkplatzflächen"],
            },
        )
        angebot, neu = Angebot.objects.get_or_create(
            kunde=gewerbe,
            objekt=ob_gew,
            defaults={"anfrage": anfrage, "gueltig_bis": heute + timedelta(days=30), "laufzeit_monate": 12},
        )
        if neu:
            for pos, code, menge in ((1, "WD-GRUND", Decimal("1")), (2, "WD-LFM", Decimal("40"))):
                lst = leistungen[code]
                Angebotsposition.objects.create(
                    angebot=angebot, pos=pos, leistung=lst, beschreibung=lst.name, menge=menge,
                    einheit=lst.einheit, einzelpreis_netto_cent=lst.preis_netto_cent, intervall=Intervall.SAISONAL,
                )

        # Aufträge mit Einsätzen (heute / diese Woche) und Zuweisungen
        def auftrag(kunde, obj, titel, status, einsaetze, **mehr):
            a, neu = Auftrag.objects.get_or_create(
                kunde=kunde, objekt=obj, titel=titel, defaults={"status": status, **mehr}
            )
            if neu:
                for von, bis, leute, est, aus in einsaetze:
                    e = Einsatz.objects.create(auftrag=a, geplant_von=von, geplant_bis=bis, status=est, erzeugt_aus=aus)
                    for m in leute:
                        EinsatzMitarbeiter.objects.create(einsatz=e, mitarbeiter=m)
            return a

        a_th = auftrag(
            hv, ob10, "Treppenhausreinigung Musterstraße 10 (wöchentlich)", Auftragsstatus.GEPLANT,
            [
                (zeitpunkt(heute, 8), zeitpunkt(heute, 10), [tom], Einsatzstatus.ZUGEWIESEN, th_vereinbarung),
                (zeitpunkt(heute + timedelta(days=2), 8), zeitpunkt(heute + timedelta(days=2), 10), [tom],
                 Einsatzstatus.ZUGEWIESEN, th_vereinbarung),
            ],
            leistungsvereinbarung=th_vereinbarung,
            bestaetigt_am=jetzt,
        )
        auftrag(
            weg, ob_weg, "Kleinreparatur Briefkastenanlage", Auftragsstatus.IN_ARBEIT,
            [(zeitpunkt(heute, 11), zeitpunkt(heute, 12, 30), [tom, mia], Einsatzstatus.ZUGEWIESEN, None)],
            bestaetigt_am=jetzt,
            faellig_am=heute + timedelta(days=3),
        )
        a_laub = auftrag(
            hv, ob12, "Laubentfernung Musterstraße 12", Auftragsstatus.ERLEDIGT,
            [(zeitpunkt(heute - timedelta(days=1), 9), zeitpunkt(heute - timedelta(days=1), 11), [mia],
              Einsatzstatus.ERLEDIGT, None)],
            bestaetigt_am=jetzt - timedelta(days=7),
        )

        # Arbeitszeiten (je Einsatz höchstens einmal)
        for a, m, beginn_h, ende_h, taetigkeit in (
            (a_th, tom, (8, 0), (9, 50), "Treppenhäuser gereinigt (Testeintrag)"),
            (a_laub, mia, (9, 0), (11, 15), "Laub entfernt und entsorgt (Testeintrag)"),
        ):
            einsatz = a.einsaetze.order_by("geplant_von").first()
            tag = timezone.localtime(einsatz.geplant_von).date()
            Arbeitszeit.objects.get_or_create(
                mitarbeiter=m,
                einsatz=einsatz,
                defaults={
                    "beginn": zeitpunkt(tag, *beginn_h),
                    "ende": zeitpunkt(tag, *ende_h),
                    "pause_minuten": 0,
                    "taetigkeit": taetigkeit,
                },
            )

        # Rechnung (Spiegel, wie sie aus Lexware käme) für den erledigten Auftrag
        netto = 2 * leistungen["STD"].preis_netto_cent + leistungen["ANF-NAH"].preis_netto_cent
        Rechnung.objects.get_or_create(
            rechnungsnummer="TEST-RE-0001",
            defaults={
                "kunde": hv,
                "auftrag": a_laub,
                "status": Rechnungsstatus.OFFEN,
                "rechnungsdatum": heute,
                "faellig_am": heute + timedelta(days=14),
                "summe_netto_cent": netto,
                "summe_brutto_cent": round(netto * Decimal("1.19")),
            },
        )

        # E-Mails: eine neue (noch nicht zugeordnet), eine zugeordnete
        EmailProtokoll.objects.get_or_create(
            postfach=POSTFACH,
            message_id="<testdaten-1@example.org>",
            defaults={
                "richtung": Mailrichtung.EINGANG,
                "von": "anfrage.test@example.org",
                "an": [POSTFACH],
                "betreff": "Testmail: Angebot für Gartenpflege gewünscht",
                "text_auszug": "Guten Tag, wir suchen jemanden für die Gartenpflege … (fiktive Testmail)",
                "empfangen_am": jetzt - timedelta(hours=1),
                "status": Mailstatus.NEU,
            },
        )
        EmailProtokoll.objects.get_or_create(
            postfach=POSTFACH,
            message_id="<testdaten-2@example.org>",
            defaults={
                "richtung": Mailrichtung.EINGANG,
                "von": erika.email,
                "an": [POSTFACH],
                "betreff": "Testmail: Rückfrage Treppenhausreinigung",
                "text_auszug": "Hallo, können Sie diese Woche auch den Keller fegen? (fiktive Testmail)",
                "empfangen_am": jetzt - timedelta(days=1),
                "status": Mailstatus.ZUGEORDNET,
                "kunde": hv,
                "ansprechpartner": erika,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Testdaten bereit: {Kunde.objects.filter(quelle=MARKE).count()} Kunden, "
                f"{Objekt.objects.filter(kunde__quelle=MARKE).count()} Objekte, "
                f"{len(LEISTUNGEN)} Leistungen, {Mitarbeiter.objects.filter(notizen=MARKE).count()} Mitarbeiter, "
                f"{Auftrag.objects.filter(kunde__quelle=MARKE).count()} Aufträge, "
                f"{Einsatz.objects.filter(auftrag__kunde__quelle=MARKE).count()} Einsätze."
            )
        )
