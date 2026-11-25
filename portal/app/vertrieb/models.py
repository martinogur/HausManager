"""Akquise-Pipeline: Leads und Kontaktprotokoll.

Unmanaged – Tabellen aus ``portal/db/erweiterungen/0003_betriebssystem.sql``.
UWG/DSGVO-Regeln (Quelle Pflicht, keine Werbe-E-Mail ohne Einwilligung/Einladung,
kein Kontakt nach Widerspruch, Agenten nur mit Freigabe) prüft die Datenbank.
"""

import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models

from stammdaten.felder import DbFelderMixin, erstellt_am_feld, geaendert_am_feld, nummer_feld


class Leadstatus(models.TextChoices):
    NEU = "neu", "Neu"
    QUALIFIZIERT = "qualifiziert", "Qualifiziert"
    KONTAKT_GEPLANT = "kontakt_geplant", "Kontakt geplant"
    KONTAKTIERT = "kontaktiert", "Kontaktiert"
    IM_GESPRAECH = "im_gespraech", "Im Gespräch"
    ANGEBOT = "angebot", "Angebot"
    GEWONNEN = "gewonnen", "Gewonnen"
    VERLOREN = "verloren", "Verloren"
    GESPERRT = "gesperrt", "Gesperrt (Widerspruch)"


OFFENE_STATUS = (
    Leadstatus.NEU, Leadstatus.QUALIFIZIERT, Leadstatus.KONTAKT_GEPLANT, Leadstatus.KONTAKTIERT,
    Leadstatus.IM_GESPRAECH, Leadstatus.ANGEBOT,
)


class Leadprioritaet(models.TextChoices):
    A = "A", "A – hoher Umsatz, regelmäßiger Bedarf"
    B = "B", "B – interessanter Einzelauftrag"
    C = "C", "C – geringes Potenzial"


class Zielgruppe(models.TextChoices):
    HAUSVERWALTUNG = "hausverwaltung", "Hausverwaltung"
    WOHNUNGSUNTERNEHMEN = "wohnungsunternehmen", "Wohnungsunternehmen/Genossenschaft"
    GEWERBEIMMOBILIE = "gewerbeimmobilie", "Gewerbeimmobilie"
    EINZELHANDEL = "einzelhandel", "Einzelhandelsfiliale"
    BUERO = "buero", "Bürogebäude"
    INVESTOR = "investor", "Immobilieninvestor"
    EIGENTUEMER = "eigentuemer", "Eigentümer (größerer Bestand)"
    UNTERNEHMEN = "unternehmen", "Unternehmen mit Pflegebedarf"
    PARTNERNETZ = "partnernetz", "Partnernetz / Nachunternehmer"
    PRIVAT = "privat", "Privat"
    SONSTIGE = "sonstige", "Sonstige"


class Kontaktkanal(models.TextChoices):
    BRIEF = "brief", "Brief"
    TELEFON = "telefon", "Telefon"
    EMAIL = "email", "E-Mail"
    KONTAKTFORMULAR = "kontaktformular", "Kontaktformular"
    PORTAL = "portal", "Portal / Plattform"
    PERSOENLICH = "persoenlich", "Persönlich"
    LINKEDIN = "linkedin", "LinkedIn"


class Lead(DbFelderMixin):
    db_verwaltete_felder = ("leadnummer", "erstellt_am", "geaendert_am")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    leadnummer = nummer_feld("LD", mit_jahr=False, verbose_name="Lead-Nr.")
    externe_ref = models.CharField("Ref. (CSV)", max_length=20, unique=True, null=True, blank=True)
    firma = models.CharField("Firma", max_length=300)
    zielgruppe = models.CharField("Zielgruppe", max_length=30, choices=Zielgruppe.choices)
    strasse = models.CharField("Straße", max_length=200, null=True, blank=True)
    plz = models.CharField("PLZ", max_length=5, null=True, blank=True)
    ort = models.CharField("Ort", max_length=200, null=True, blank=True)
    entfernung_km = models.DecimalField("Entfernung (km)", max_digits=5, decimal_places=1, null=True, blank=True)
    im_einsatzgebiet = models.BooleanField("Im Einsatzgebiet", null=True, blank=True)
    webseite = models.CharField("Webseite", max_length=300, null=True, blank=True)
    telefon = models.CharField("Telefon", max_length=100, null=True, blank=True)
    email = models.EmailField("E-Mail (geschäftlich)", null=True, blank=True)
    ansprechpartner = models.CharField("Ansprechpartner", max_length=300, null=True, blank=True)
    position = models.CharField("Position", max_length=300, null=True, blank=True)
    quelle = models.TextField("Quelle (Pflicht, DSGVO)")
    objekte_geschaetzt = models.CharField("Objekte (geschätzt)", max_length=300, null=True, blank=True)
    regelmaessiger_bedarf = models.BooleanField("Regelmäßiger Bedarf", null=True, blank=True)
    geschaetzter_monatsumsatz_cent = models.IntegerField("Geschätzter Monatsumsatz (Cent)", null=True, blank=True)
    leistungsinteresse = ArrayField(models.TextField(), verbose_name="Leistungsinteresse", null=True, blank=True)
    score = models.SmallIntegerField("Score", null=True, blank=True)
    prioritaet = models.CharField("Priorität", max_length=1, choices=Leadprioritaet.choices, null=True, blank=True)
    score_begruendung = models.JSONField("Score-Begründung", null=True, blank=True)
    status = models.CharField("Status", max_length=20, choices=Leadstatus.choices, default=Leadstatus.NEU)
    naechste_aktion = models.TextField("Nächste Aktion", null=True, blank=True)
    wiedervorlage_am = models.DateField("Wiedervorlage", null=True, blank=True)
    email_einwilligung = models.DateTimeField("E-Mail-Einwilligung", null=True, blank=True)
    einwilligung_quelle = models.TextField("Nachweis Einwilligung", null=True, blank=True)
    einladung_beleg = models.TextField("Beleg öffentliche Einladung", null=True, blank=True)
    widerspruch_am = models.DateTimeField("Widerspruch am", null=True, blank=True)
    kunde = models.ForeignKey(
        "stammdaten.Kunde", on_delete=models.SET_NULL, null=True, blank=True, related_name="leads", verbose_name="Kunde"
    )
    hubspot_company_id = models.CharField("HubSpot-ID", max_length=50, unique=True, null=True, blank=True)
    notizen = models.TextField("Notizen", null=True, blank=True)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "leads"
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
        ordering = ["prioritaet", "-score", "firma"]

    def __str__(self):
        return f"{self.leadnummer} {self.firma}"

    @property
    def email_werbung_erlaubt(self) -> bool:
        """§ 7 UWG: Werbe-E-Mail nur mit Einwilligung oder als Antwort auf eine öffentliche Einladung."""
        return self.widerspruch_am is None and (self.email_einwilligung is not None or bool(self.einladung_beleg))


class LeadKontakt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="kontakte")
    kanal = models.CharField("Kanal", max_length=20, choices=Kontaktkanal.choices)
    richtung = models.CharField(
        "Richtung", max_length=10, choices=[("ausgehend", "Ausgehend"), ("eingehend", "Eingehend")]
    )
    zeitpunkt = models.DateTimeField("Zeitpunkt", db_default=models.functions.Now())
    zusammenfassung = models.TextField("Zusammenfassung")
    ergebnis = models.TextField("Ergebnis", null=True, blank=True)
    durch = models.CharField("Durch", max_length=200)
    freigabe = models.ForeignKey(
        "agenten.Freigabe", on_delete=models.SET_NULL, null=True, blank=True, related_name="lead_kontakte"
    )
    erstellt_am = erstellt_am_feld()

    class Meta:
        managed = False
        db_table = "lead_kontakte"
        verbose_name = "Kontakt"
        verbose_name_plural = "Kontaktprotokoll"
        ordering = ["-zeitpunkt"]

    def __str__(self):
        return f"{self.get_kanal_display()} {self.zeitpunkt:%d.%m.%Y}"
