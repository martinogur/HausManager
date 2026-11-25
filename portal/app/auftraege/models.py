"""Vertrieb und Ausführung: Anfragen, Angebote, Aufträge, Einsätze, Zuweisungen, Rechnungen.

Unmanaged – die Tabellen legt ``portal/db/schema.sql`` an (Migration ``kern.0001_schema``).
Regeln wie „Objekt gehört zum Kunden“ oder „keine Doppelbelegung“ prüft die Datenbank;
``clean()`` gibt im Formular nur eine freundlichere Meldung vorab.
"""

import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField, DateTimeRangeField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from stammdaten.felder import DbFelderMixin, erstellt_am_feld, geaendert_am_feld, nummer_feld
from stammdaten.models import Intervall


class Anfragestatus(models.TextChoices):
    NEU = "neu", "Neu"
    IN_BEARBEITUNG = "in_bearbeitung", "In Bearbeitung"
    BESICHTIGUNG = "besichtigung", "Besichtigung"
    ANGEBOT = "angebot", "Angebot"
    GEWONNEN = "gewonnen", "Gewonnen"
    VERLOREN = "verloren", "Verloren"


class Kanal(models.TextChoices):
    EMAIL = "email", "E-Mail"
    WEBSEITE = "webseite", "Webseite"
    WHATSAPP = "whatsapp", "WhatsApp"
    TELEFON = "telefon", "Telefon"
    BRIEF = "brief", "Brief"


class Angebotsstatus(models.TextChoices):
    ENTWURF = "entwurf", "Entwurf"
    VERSENDET = "versendet", "Versendet"
    ANGENOMMEN = "angenommen", "Angenommen"
    ABGELEHNT = "abgelehnt", "Abgelehnt"
    ABGELAUFEN = "abgelaufen", "Abgelaufen"


class Auftragsstatus(models.TextChoices):
    ANFRAGE = "anfrage", "Anfrage"
    ANGEBOT = "angebot", "Angebot"
    BESTAETIGT = "bestaetigt", "Bestätigt"
    GEPLANT = "geplant", "Geplant"
    IN_ARBEIT = "in_arbeit", "In Arbeit"
    ERLEDIGT = "erledigt", "Erledigt"
    ABGERECHNET = "abgerechnet", "Abgerechnet"
    STORNIERT = "storniert", "Storniert"


class Einsatzstatus(models.TextChoices):
    GEPLANT = "geplant", "Geplant"
    ZUGEWIESEN = "zugewiesen", "Zugewiesen"
    IN_ARBEIT = "in_arbeit", "In Arbeit"
    ERLEDIGT = "erledigt", "Erledigt"
    AUSGEFALLEN = "ausgefallen", "Ausgefallen"


class Rechnungsstatus(models.TextChoices):
    ENTWURF = "entwurf", "Entwurf"
    OFFEN = "offen", "Offen"
    BEZAHLT = "bezahlt", "Bezahlt"
    UEBERFAELLIG = "ueberfaellig", "Überfällig"
    STORNIERT = "storniert", "Storniert"


def _objekt_passt_zum_kunden(instanz):
    if instanz.objekt_id and instanz.kunde_id and instanz.objekt.kunde_id != instanz.kunde_id:
        raise ValidationError({"objekt": "Dieses Objekt gehört nicht zum gewählten Kunden."})


class Anfrage(DbFelderMixin):
    db_verwaltete_felder = ("anfragenummer", "eingegangen_am", "geaendert_am")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    anfragenummer = nummer_feld("AN", verbose_name="Anfragenummer")
    kunde = models.ForeignKey(
        "stammdaten.Kunde",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anfragen",
        verbose_name="Kunde",
    )
    ansprechpartner = models.ForeignKey(
        "stammdaten.Ansprechpartner",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anfragen",
        verbose_name="Ansprechpartner",
    )
    objekt = models.ForeignKey(
        "stammdaten.Objekt",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anfragen",
        verbose_name="Objekt",
    )
    kanal = models.CharField("Kanal", max_length=20, choices=Kanal.choices)
    betreff = models.CharField("Betreff", max_length=300, null=True, blank=True)
    gewuenschte_leistungen = ArrayField(
        models.CharField(max_length=200), verbose_name="Gewünschte Leistungen", null=True, blank=True
    )
    ki_zusammenfassung = models.TextField("KI-Zusammenfassung", null=True, blank=True)
    fehlende_angaben = ArrayField(
        models.CharField(max_length=200),
        verbose_name="Fehlende Angaben",
        null=True,
        blank=True,
        help_text="Von der KI erkannt, z. B. Adresse, Etagenzahl",
    )
    status = models.CharField("Status", max_length=20, choices=Anfragestatus.choices, default=Anfragestatus.NEU)
    hubspot_deal_id = models.CharField("HubSpot-Deal-ID", max_length=100, unique=True, null=True, blank=True)
    eingegangen_am = erstellt_am_feld("Eingegangen am")
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "anfragen"
        verbose_name = "Anfrage"
        verbose_name_plural = "Anfragen"
        ordering = ["-eingegangen_am"]

    def __str__(self):
        return f"{self.anfragenummer} – {self.betreff or self.get_kanal_display()}"


class Angebot(DbFelderMixin):
    db_verwaltete_felder = ("angebotsnummer", "summe_netto_cent", "erstellt_am", "geaendert_am")
    db_nach_update_laden = ("summe_netto_cent", "geaendert_am")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    angebotsnummer = nummer_feld("AG", verbose_name="Angebotsnummer")
    # In der Datenbank kein eigener FK auf kunden, sondern (objekt_id, kunde_id) → objekte.
    kunde = models.ForeignKey(
        "stammdaten.Kunde", on_delete=models.PROTECT, related_name="angebote", verbose_name="Kunde"
    )
    objekt = models.ForeignKey(
        "stammdaten.Objekt", on_delete=models.PROTECT, related_name="angebote", verbose_name="Objekt"
    )
    anfrage = models.ForeignKey(
        Anfrage, on_delete=models.SET_NULL, null=True, blank=True, related_name="angebote", verbose_name="Anfrage"
    )
    status = models.CharField(
        "Status", max_length=20, choices=Angebotsstatus.choices, default=Angebotsstatus.ENTWURF
    )
    gueltig_bis = models.DateField("Gültig bis", null=True, blank=True)
    laufzeit_monate = models.SmallIntegerField("Laufzeit (Monate)", null=True, blank=True)
    summe_netto_cent = models.IntegerField(
        "Summe netto (Cent)", db_default=0, editable=False, help_text="Wird aus den Positionen berechnet."
    )
    freigegeben_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="freigegeben_von",
        related_name="freigegebene_angebote",
        verbose_name="Freigegeben von",
    )
    freigegeben_am = models.DateTimeField("Freigegeben am", null=True, blank=True)
    versendet_am = models.DateTimeField("Versendet am", null=True, blank=True)
    lexware_quotation_id = models.UUIDField("Lexware-Angebots-ID", unique=True, null=True, blank=True)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "angebote"
        verbose_name = "Angebot"
        verbose_name_plural = "Angebote"
        ordering = ["-erstellt_am"]

    def __str__(self):
        return f"{self.angebotsnummer} – {self.kunde.name}"

    def clean(self):
        _objekt_passt_zum_kunden(self)
        if self.status != Angebotsstatus.ENTWURF and not self.freigegeben_am:
            raise ValidationError(
                {"status": "Ein Angebot kann erst nach Freigabe durch den Inhaber versendet werden."}
            )


class Angebotsposition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    angebot = models.ForeignKey(Angebot, on_delete=models.CASCADE, related_name="positionen", verbose_name="Angebot")
    pos = models.SmallIntegerField("Pos.")
    leistung = models.ForeignKey(
        "stammdaten.Leistung",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="angebotspositionen",
        verbose_name="Leistung",
    )
    beschreibung = models.TextField("Beschreibung")
    menge = models.DecimalField("Menge", max_digits=10, decimal_places=2)
    einheit = models.CharField("Einheit", max_length=60)
    einzelpreis_netto_cent = models.PositiveIntegerField("Einzelpreis netto (Cent)")
    intervall = models.CharField("Intervall", max_length=20, choices=Intervall.choices, default=Intervall.EINMALIG)

    class Meta:
        managed = False
        db_table = "angebotspositionen"
        verbose_name = "Angebotsposition"
        verbose_name_plural = "Angebotspositionen"
        ordering = ["angebot", "pos"]
        constraints = [
            models.UniqueConstraint(fields=["angebot", "pos"], name="angebotspositionen_angebot_id_pos_key")
        ]

    def __str__(self):
        return f"Pos. {self.pos}: {self.beschreibung}"

    @property
    def gesamt_netto_cent(self):
        return round(self.menge * self.einzelpreis_netto_cent)

    def clean(self):
        if self.menge is not None and self.menge <= 0:
            raise ValidationError({"menge": "Die Menge muss größer als 0 sein."})


class AuftragQuerySet(models.QuerySet):
    OFFENE_STATUS = (
        Auftragsstatus.ANFRAGE,
        Auftragsstatus.ANGEBOT,
        Auftragsstatus.BESTAETIGT,
        Auftragsstatus.GEPLANT,
        Auftragsstatus.IN_ARBEIT,
    )

    def offen(self):
        """Aufträge, die noch nicht erledigt, abgerechnet oder storniert sind."""
        return self.filter(status__in=self.OFFENE_STATUS)


class Auftrag(DbFelderMixin):
    db_verwaltete_felder = ("auftragsnummer", "erstellt_am", "geaendert_am")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auftragsnummer = nummer_feld("AU", verbose_name="Auftragsnummer")
    # In der Datenbank kein eigener FK auf kunden, sondern (objekt_id, kunde_id) → objekte.
    kunde = models.ForeignKey(
        "stammdaten.Kunde", on_delete=models.PROTECT, related_name="auftraege", verbose_name="Kunde"
    )
    objekt = models.ForeignKey(
        "stammdaten.Objekt", on_delete=models.PROTECT, related_name="auftraege", verbose_name="Objekt"
    )
    angebot = models.OneToOneField(
        Angebot, on_delete=models.PROTECT, null=True, blank=True, related_name="auftrag", verbose_name="Angebot"
    )
    leistungsvereinbarung = models.ForeignKey(
        "stammdaten.Leistungsvereinbarung",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auftraege",
        verbose_name="Leistungsvereinbarung",
    )
    titel = models.CharField("Titel", max_length=200)
    beschreibung = models.TextField("Beschreibung", null=True, blank=True)
    status = models.CharField(
        "Status", max_length=20, choices=Auftragsstatus.choices, default=Auftragsstatus.BESTAETIGT
    )
    bestaetigt_am = models.DateTimeField("Bestätigt am", null=True, blank=True)
    faellig_am = models.DateField("Fällig am", null=True, blank=True)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    objects = AuftragQuerySet.as_manager()

    class Meta:
        managed = False
        db_table = "auftraege"
        verbose_name = "Auftrag"
        verbose_name_plural = "Aufträge"
        ordering = ["-erstellt_am"]

    def __str__(self):
        return f"{self.auftragsnummer} – {self.titel}"

    def clean(self):
        _objekt_passt_zum_kunden(self)


class EinsatzQuerySet(models.QuerySet):
    def fuer_benutzer(self, user):
        """Admin und Büro sehen alle Einsätze, Mitarbeiter nur die ihnen zugewiesenen."""
        if user is None or not getattr(user, "is_authenticated", False) or not getattr(user, "aktiv", True):
            return self.none()
        rolle = getattr(user, "rolle", None)
        if rolle in ("admin", "buero"):
            return self.all()
        if rolle == "mitarbeiter":
            return self.filter(
                pk__in=EinsatzMitarbeiter.objects.filter(mitarbeiter__benutzer_id=user.pk).values("einsatz_id")
            )
        return self.none()

    def am_tag(self, tag):
        return self.filter(geplant_von__date=tag)


class Einsatz(DbFelderMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auftrag = models.ForeignKey(Auftrag, on_delete=models.CASCADE, related_name="einsaetze", verbose_name="Auftrag")
    geplant_von = models.DateTimeField("Geplant von")
    geplant_bis = models.DateTimeField("Geplant bis")
    status = models.CharField(
        "Status", max_length=20, choices=Einsatzstatus.choices, default=Einsatzstatus.GEPLANT
    )
    erzeugt_aus = models.ForeignKey(
        "stammdaten.Leistungsvereinbarung",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="erzeugt_aus",
        related_name="einsaetze",
        verbose_name="Erzeugt aus Vereinbarung",
    )
    notiz_buero = models.TextField("Notiz vom Büro", null=True, blank=True)
    bericht_mitarbeiter = models.TextField("Bericht des Mitarbeiters", null=True, blank=True)
    ki_auswertung = models.TextField("KI-Auswertung", null=True, blank=True)
    craftnote_task_id = models.CharField("Craftnote-Aufgaben-ID", max_length=100, unique=True, null=True, blank=True)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    objects = EinsatzQuerySet.as_manager()

    class Meta:
        managed = False
        db_table = "einsaetze"
        verbose_name = "Einsatz"
        verbose_name_plural = "Einsätze"
        ordering = ["geplant_von"]

    def __str__(self):
        von = timezone.localtime(self.geplant_von)
        return f"{von:%d.%m.%Y %H:%M} – {self.auftrag.titel}"

    def clean(self):
        if self.geplant_von and self.geplant_bis and self.geplant_bis <= self.geplant_von:
            raise ValidationError({"geplant_bis": "Das Ende muss nach dem Beginn liegen."})


class EinsatzMitarbeiter(models.Model):
    """Zuweisung eines Mitarbeiters zu einem Einsatz (keine Doppelbelegung – prüft die Datenbank)."""

    pk = models.CompositePrimaryKey("einsatz_id", "mitarbeiter_id")
    einsatz = models.ForeignKey(Einsatz, on_delete=models.CASCADE, related_name="zuweisungen", verbose_name="Einsatz")
    mitarbeiter = models.ForeignKey(
        "personal.Mitarbeiter",
        on_delete=models.PROTECT,
        related_name="einsatz_zuweisungen",
        verbose_name="Mitarbeiter",
    )
    # Füllt der Trigger einsatz_zeitraum_uebernehmen aus dem Einsatz; Django sendet hier nur NULL.
    zeitraum = DateTimeRangeField("Zeitraum", editable=False, blank=True)

    class Meta:
        managed = False
        db_table = "einsatz_mitarbeiter"
        verbose_name = "Einsatz-Zuweisung"
        verbose_name_plural = "Einsatz-Zuweisungen"
        ordering = ["einsatz", "mitarbeiter"]

    def __str__(self):
        return f"{self.mitarbeiter} → {self.einsatz}"

    def save(self, *args, **kwargs):
        self.zeitraum = None  # immer aus dem Einsatz übernehmen (Trigger)
        super().save(*args, **kwargs)
        self.refresh_from_db(fields=["zeitraum"])


class Rechnung(DbFelderMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kunde = models.ForeignKey(
        "stammdaten.Kunde", on_delete=models.PROTECT, related_name="rechnungen", verbose_name="Kunde"
    )
    auftrag = models.ForeignKey(
        Auftrag, on_delete=models.SET_NULL, null=True, blank=True, related_name="rechnungen", verbose_name="Auftrag"
    )
    lexware_invoice_id = models.UUIDField("Lexware-Rechnungs-ID", unique=True, null=True, blank=True)
    rechnungsnummer = models.CharField(
        "Rechnungsnummer", max_length=50, unique=True, null=True, blank=True, help_text="Vergibt Lexware beim Festschreiben."
    )
    status = models.CharField(
        "Status", max_length=20, choices=Rechnungsstatus.choices, default=Rechnungsstatus.ENTWURF
    )
    rechnungsdatum = models.DateField("Rechnungsdatum", null=True, blank=True)
    faellig_am = models.DateField("Fällig am", null=True, blank=True)
    summe_netto_cent = models.PositiveIntegerField("Summe netto (Cent)")
    summe_brutto_cent = models.PositiveIntegerField("Summe brutto (Cent)")
    bezahlt_am = models.DateField("Bezahlt am", null=True, blank=True)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "rechnungen"
        verbose_name = "Rechnung"
        verbose_name_plural = "Rechnungen"
        ordering = ["-rechnungsdatum", "-erstellt_am"]

    def __str__(self):
        return f"{self.rechnungsnummer or 'Rechnungsentwurf'} – {self.kunde.name}"

    def clean(self):
        fehler = {}
        if (
            self.summe_netto_cent is not None
            and self.summe_brutto_cent is not None
            and self.summe_brutto_cent < self.summe_netto_cent
        ):
            fehler["summe_brutto_cent"] = "Der Bruttobetrag darf nicht kleiner als der Nettobetrag sein."
        if self.status == Rechnungsstatus.BEZAHLT and not self.bezahlt_am:
            fehler["bezahlt_am"] = "Bitte das Zahlungsdatum eintragen."
        if fehler:
            raise ValidationError(fehler)
