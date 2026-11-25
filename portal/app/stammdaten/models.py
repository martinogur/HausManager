"""Stammdaten: Kunden, Ansprechpartner, Objekte, Leistungskatalog, Leistungsvereinbarungen.

Unmanaged – die Tabellen legt ``portal/db/schema.sql`` an (Migration ``kern.0001_schema``).
"""

import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from .felder import (
    DbFelderMixin,
    Wochentag,
    erstellt_am_feld,
    geaendert_am_feld,
    nummer_feld,
    plz_validator,
)


class Kundentyp(models.TextChoices):
    HAUSVERWALTUNG = "hausverwaltung", "Hausverwaltung"
    WEG = "weg", "WEG"
    WOHNUNGSUNTERNEHMEN = "wohnungsunternehmen", "Wohnungsunternehmen"
    GEWERBE = "gewerbe", "Gewerbe"
    PRIVAT = "privat", "Privat"
    PARTNER = "partner", "Partner"


class Kundenstatus(models.TextChoices):
    INTERESSENT = "interessent", "Interessent"
    AKTIV = "aktiv", "Aktiv"
    PAUSIERT = "pausiert", "Pausiert"
    BEENDET = "beendet", "Beendet"


class Intervall(models.TextChoices):
    EINMALIG = "einmalig", "Einmalig"
    WOECHENTLICH = "woechentlich", "Wöchentlich"
    ZWEIWOECHENTLICH = "zweiwoechentlich", "Zweiwöchentlich"
    MONATLICH = "monatlich", "Monatlich"
    SAISONAL = "saisonal", "Saisonal"
    NACH_BEDARF = "nach_bedarf", "Nach Bedarf"


class Kunde(DbFelderMixin):
    db_verwaltete_felder = ("kundennummer", "erstellt_am", "geaendert_am")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kundennummer = nummer_feld("K", mit_jahr=False, verbose_name="Kundennummer")
    name = models.CharField("Name", max_length=200)
    typ = models.CharField("Kundentyp", max_length=30, choices=Kundentyp.choices)
    status = models.CharField(
        "Status", max_length=20, choices=Kundenstatus.choices, default=Kundenstatus.INTERESSENT
    )
    strasse = models.CharField("Straße", max_length=200, null=True, blank=True)
    plz = models.CharField("PLZ", max_length=5, null=True, blank=True, validators=[plz_validator])
    ort = models.CharField("Ort", max_length=100, null=True, blank=True)
    telefon = models.CharField("Telefon", max_length=50, null=True, blank=True)
    email = models.EmailField("E-Mail", null=True, blank=True)
    webseite = models.CharField("Webseite", max_length=200, null=True, blank=True)
    quelle = models.CharField(
        "Quelle", max_length=200, null=True, blank=True, help_text="z. B. Webseite, Brief L002, Empfehlung"
    )
    notizen = models.TextField("Notizen", null=True, blank=True)
    hubspot_company_id = models.CharField("HubSpot-Firmen-ID", max_length=100, unique=True, null=True, blank=True)
    lexware_contact_id = models.UUIDField("Lexware-Kontakt-ID", unique=True, null=True, blank=True)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "kunden"
        verbose_name = "Kunde"
        verbose_name_plural = "Kunden"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.kundennummer})" if isinstance(self.kundennummer, str) else self.name


class Ansprechpartner(DbFelderMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kunde = models.ForeignKey(
        Kunde, on_delete=models.CASCADE, related_name="ansprechpartner", verbose_name="Kunde"
    )
    anrede = models.CharField("Anrede", max_length=30, null=True, blank=True)
    vorname = models.CharField("Vorname", max_length=100, null=True, blank=True)
    nachname = models.CharField("Nachname", max_length=100)
    funktion = models.CharField("Funktion", max_length=100, null=True, blank=True)
    email = models.EmailField("E-Mail", null=True, blank=True)
    telefon = models.CharField("Telefon", max_length=50, null=True, blank=True)
    mobil = models.CharField("Mobil", max_length=50, null=True, blank=True)
    ist_hauptkontakt = models.BooleanField("Hauptkontakt", default=False)
    email_einwilligung = models.DateTimeField(
        "E-Mail-Einwilligung am",
        null=True,
        blank=True,
        help_text="Nachweis für Werbe-E-Mails (§ 7 UWG). Leer = keine Einwilligung.",
    )
    einwilligung_quelle = models.CharField(
        "Nachweis der Einwilligung",
        max_length=300,
        null=True,
        blank=True,
        help_text="z. B. „Telefonat 03.12.2026, Notiz MO“ – Pflicht, wenn eine Einwilligung eingetragen ist.",
    )
    hubspot_contact_id = models.CharField("HubSpot-Kontakt-ID", max_length=100, unique=True, null=True, blank=True)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "ansprechpartner"
        verbose_name = "Ansprechpartner"
        verbose_name_plural = "Ansprechpartner"
        ordering = ["nachname", "vorname"]

    def __str__(self):
        name = " ".join(t for t in (self.anrede, self.vorname, self.nachname) if t)
        return name

    def clean(self):
        if self.email_einwilligung and not self.einwilligung_quelle:
            raise ValidationError({"einwilligung_quelle": "Bitte angeben, wie die Einwilligung erteilt wurde."})


class Objekt(DbFelderMixin):
    db_verwaltete_felder = ("objektnummer", "erstellt_am", "geaendert_am")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    objektnummer = nummer_feld("OB", mit_jahr=False, verbose_name="Objektnummer")
    kunde = models.ForeignKey(Kunde, on_delete=models.PROTECT, related_name="objekte", verbose_name="Kunde")
    bezeichnung = models.CharField("Bezeichnung", max_length=200, help_text="z. B. WEG Musterstraße 10")
    strasse = models.CharField("Straße", max_length=200)
    hausnummer = models.CharField("Hausnummer", max_length=20)
    plz = models.CharField("PLZ", max_length=5, validators=[plz_validator])
    ort = models.CharField("Ort", max_length=100)
    wohneinheiten = models.PositiveSmallIntegerField("Wohneinheiten", null=True, blank=True)
    gewerbeeinheiten = models.PositiveSmallIntegerField("Gewerbeeinheiten", null=True, blank=True)
    treppenhaeuser = models.PositiveSmallIntegerField("Treppenhäuser", null=True, blank=True)
    etagen = models.PositiveSmallIntegerField("Etagen", null=True, blank=True)
    aufzug = models.BooleanField("Aufzug", default=False)
    gehweg_meter = models.DecimalField(
        "Gehweg (lfd. Meter)", max_digits=6, decimal_places=1, null=True, blank=True
    )
    gruenflaeche_qm = models.DecimalField("Grünfläche (m²)", max_digits=8, decimal_places=1, null=True, blank=True)
    zugang_hinweise = models.TextField(
        "Hinweise zum Zugang",
        null=True,
        blank=True,
        help_text="Keine Schlüssel- oder Türcodes hier speichern!",
    )
    entfernung_km = models.DecimalField("Entfernung (km)", max_digits=5, decimal_places=1, null=True, blank=True)
    craftnote_project_id = models.CharField(
        "Craftnote-Projekt-ID", max_length=100, unique=True, null=True, blank=True
    )
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "objekte"
        verbose_name = "Objekt"
        verbose_name_plural = "Objekte"
        ordering = ["plz", "strasse", "hausnummer"]

    def __str__(self):
        return self.bezeichnung

    @property
    def adresse(self):
        return f"{self.strasse} {self.hausnummer}, {self.plz} {self.ort}"


class Leistung(DbFelderMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField("Code", max_length=40, unique=True, help_text="z. B. TH-REINIGUNG")
    name = models.CharField("Bezeichnung", max_length=200)
    einheit = models.CharField("Einheit", max_length=60, help_text="z. B. je Reinigung, je Etage, Std.")
    preis_netto_cent = models.PositiveIntegerField("Preis netto (Cent)")
    ust_satz = models.DecimalField("USt.-Satz (%)", max_digits=4, decimal_places=2, default=Decimal("19.00"))
    betriebskostenart = models.CharField(
        "Betriebskostenart",
        max_length=100,
        null=True,
        blank=True,
        help_text="Für die Umlage, z. B. Gebäudereinigung, Gartenpflege, Hauswart, Winterdienst",
    )
    aktiv = models.BooleanField("Aktiv", default=True)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "leistungen"
        verbose_name = "Leistung"
        verbose_name_plural = "Leistungen (Katalog)"
        ordering = ["code"]

    def __str__(self):
        return f"{self.name} ({self.preis_netto_cent / 100:.2f} € {self.einheit})".replace(".", ",", 1)


class Leistungsvereinbarung(DbFelderMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    objekt = models.ForeignKey(
        Objekt, on_delete=models.CASCADE, related_name="leistungsvereinbarungen", verbose_name="Objekt"
    )
    leistung = models.ForeignKey(
        Leistung, on_delete=models.PROTECT, related_name="vereinbarungen", verbose_name="Leistung"
    )
    intervall = models.CharField("Intervall", max_length=20, choices=Intervall.choices)
    wochentag = models.PositiveSmallIntegerField("Wochentag", choices=Wochentag.choices, null=True, blank=True)
    monatstag = models.PositiveSmallIntegerField(
        "Tag im Monat", null=True, blank=True, help_text="1–28"
    )
    menge = models.DecimalField("Menge", max_digits=8, decimal_places=2, default=Decimal("1"))
    preis_netto_cent = models.PositiveIntegerField("Preis netto (Cent)")
    gueltig_von = models.DateField("Gültig von")
    gueltig_bis = models.DateField("Gültig bis", null=True, blank=True)
    saison_von_monat = models.PositiveSmallIntegerField("Saison von (Monat)", null=True, blank=True)
    saison_bis_monat = models.PositiveSmallIntegerField("Saison bis (Monat)", null=True, blank=True)
    standard_mitarbeiter = models.ForeignKey(
        "personal.Mitarbeiter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="standard_vereinbarungen",
        verbose_name="Standard-Mitarbeiter",
    )
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "leistungsvereinbarungen"
        verbose_name = "Leistungsvereinbarung"
        verbose_name_plural = "Leistungsvereinbarungen"
        ordering = ["objekt", "gueltig_von"]

    def __str__(self):
        return f"{self.leistung.name} – {self.objekt} ({self.get_intervall_display()})"

    def clean(self):
        fehler = {}
        if self.gueltig_bis and self.gueltig_von and self.gueltig_bis < self.gueltig_von:
            fehler["gueltig_bis"] = "Das Ende darf nicht vor dem Beginn liegen."
        if self.intervall in (Intervall.WOECHENTLICH, Intervall.ZWEIWOECHENTLICH) and not self.wochentag:
            fehler["wochentag"] = "Bei wöchentlichem Intervall bitte einen Wochentag wählen."
        if self.intervall == Intervall.MONATLICH and not (self.monatstag or self.wochentag):
            fehler["monatstag"] = "Bei monatlichem Intervall bitte Tag im Monat oder Wochentag angeben."
        if self.intervall == Intervall.SAISONAL and not (self.saison_von_monat and self.saison_bis_monat):
            fehler["saison_von_monat"] = "Bei saisonalem Intervall bitte Saisonbeginn und -ende angeben."
        if self.monatstag is not None and not 1 <= self.monatstag <= 28:
            fehler["monatstag"] = "Bitte einen Tag zwischen 1 und 28 angeben."
        for feld in ("saison_von_monat", "saison_bis_monat"):
            wert = getattr(self, feld)
            if wert is not None and not 1 <= wert <= 12:
                fehler[feld] = "Bitte einen Monat zwischen 1 und 12 angeben."
        if fehler:
            raise ValidationError(fehler)
