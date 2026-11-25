"""Personal: Mitarbeiter, Qualifikationen, Verfügbarkeiten, Abwesenheiten, Stellen, Bewerbungen, Arbeitszeiten.

Unmanaged – die Tabellen legt ``portal/db/schema.sql`` an (Migration ``kern.0001_schema``).
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.expressions import RawSQL
from django.utils import timezone

from stammdaten.felder import (
    DbFelderMixin,
    Wochentag,
    erstellt_am_feld,
    geaendert_am_feld,
    nummer_feld,
)


class Beschaeftigung(models.TextChoices):
    INHABER = "inhaber", "Inhaber"
    MINIJOB = "minijob", "Minijob"
    TEILZEIT = "teilzeit", "Teilzeit"
    VOLLZEIT = "vollzeit", "Vollzeit"
    SUBUNTERNEHMER = "subunternehmer", "Subunternehmer"


class Bewerbungsstatus(models.TextChoices):
    EINGEGANGEN = "eingegangen", "Eingegangen"
    GESICHTET = "gesichtet", "Gesichtet"
    GESPRAECH = "gespraech", "Gespräch"
    PROBEARBEIT = "probearbeit", "Probearbeit"
    ZUSAGE = "zusage", "Zusage"
    ABSAGE = "absage", "Absage"
    ZURUECKGEZOGEN = "zurueckgezogen", "Zurückgezogen"


class Mitarbeiter(DbFelderMixin):
    db_verwaltete_felder = ("personalnummer", "erstellt_am", "geaendert_am")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    personalnummer = nummer_feld("MA", mit_jahr=False, verbose_name="Personalnummer")
    benutzer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mitarbeiter",
        verbose_name="Benutzerkonto",
    )
    vorname = models.CharField("Vorname", max_length=100)
    nachname = models.CharField("Nachname", max_length=100)
    email = models.EmailField("E-Mail", unique=True, null=True, blank=True)
    telefon = models.CharField("Telefon", max_length=50, null=True, blank=True)
    beschaeftigung = models.CharField("Beschäftigung", max_length=20, choices=Beschaeftigung.choices)
    wochenstunden_soll = models.DecimalField(
        "Wochenstunden (Soll)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    stundenlohn_cent = models.PositiveIntegerField(
        "Stundenlohn (Cent)", null=True, blank=True, help_text="Nur für Rolle Admin sichtbar."
    )
    eintritt = models.DateField("Eintritt", null=True, blank=True)
    austritt = models.DateField("Austritt", null=True, blank=True)
    fuehrerschein = models.BooleanField("Führerschein", default=False)
    notizen = models.TextField("Notizen", null=True, blank=True)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "mitarbeiter"
        verbose_name = "Mitarbeiter"
        verbose_name_plural = "Mitarbeiter"
        ordering = ["nachname", "vorname"]

    def __str__(self):
        return f"{self.vorname} {self.nachname}"

    def clean(self):
        if self.eintritt and self.austritt and self.austritt < self.eintritt:
            raise ValidationError({"austritt": "Der Austritt darf nicht vor dem Eintritt liegen."})


class Qualifikation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Bezeichnung", max_length=100, unique=True)

    class Meta:
        managed = False
        db_table = "qualifikationen"
        verbose_name = "Qualifikation"
        verbose_name_plural = "Qualifikationen"
        ordering = ["name"]

    def __str__(self):
        return self.name


class MitarbeiterQualifikation(models.Model):
    pk = models.CompositePrimaryKey("mitarbeiter_id", "qualifikation_id")
    mitarbeiter = models.ForeignKey(
        Mitarbeiter, on_delete=models.CASCADE, related_name="qualifikationen", verbose_name="Mitarbeiter"
    )
    qualifikation = models.ForeignKey(
        Qualifikation, on_delete=models.CASCADE, related_name="mitarbeiter", verbose_name="Qualifikation"
    )
    gueltig_bis = models.DateField("Gültig bis", null=True, blank=True)

    class Meta:
        managed = False
        db_table = "mitarbeiter_qualifikationen"
        verbose_name = "Qualifikation eines Mitarbeiters"
        verbose_name_plural = "Qualifikationen der Mitarbeiter"
        ordering = ["mitarbeiter", "qualifikation"]

    def __str__(self):
        return f"{self.mitarbeiter}: {self.qualifikation}"


class Verfuegbarkeit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mitarbeiter = models.ForeignKey(
        Mitarbeiter, on_delete=models.CASCADE, related_name="verfuegbarkeiten", verbose_name="Mitarbeiter"
    )
    wochentag = models.PositiveSmallIntegerField("Wochentag", choices=Wochentag.choices)
    von = models.TimeField("Von")
    bis = models.TimeField("Bis")

    class Meta:
        managed = False
        db_table = "verfuegbarkeiten"
        verbose_name = "Verfügbarkeit"
        verbose_name_plural = "Verfügbarkeiten"
        ordering = ["mitarbeiter", "wochentag", "von"]

    def __str__(self):
        return f"{self.mitarbeiter}: {self.get_wochentag_display()} {self.von:%H:%M}–{self.bis:%H:%M}"

    def clean(self):
        if self.von and self.bis and self.bis <= self.von:
            raise ValidationError({"bis": "Das Ende muss nach dem Beginn liegen."})


class Abwesenheit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mitarbeiter = models.ForeignKey(
        Mitarbeiter, on_delete=models.CASCADE, related_name="abwesenheiten", verbose_name="Mitarbeiter"
    )
    von = models.DateField("Von")
    bis = models.DateField("Bis")
    grund = models.CharField(
        "Grund", max_length=100, help_text="Urlaub, krank oder sonstiges – keine Diagnosen eintragen!"
    )

    class Meta:
        managed = False
        db_table = "abwesenheiten"
        verbose_name = "Abwesenheit"
        verbose_name_plural = "Abwesenheiten"
        ordering = ["-von"]

    def __str__(self):
        return f"{self.mitarbeiter}: {self.grund} {self.von:%d.%m.%Y}–{self.bis:%d.%m.%Y}"

    def clean(self):
        if self.von and self.bis and self.bis < self.von:
            raise ValidationError({"bis": "Das Ende darf nicht vor dem Beginn liegen."})


class Stelle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titel = models.CharField("Titel", max_length=200)
    beschaeftigung = models.CharField("Beschäftigung", max_length=20, choices=Beschaeftigung.choices)
    offen = models.BooleanField("Offen", default=True)
    erstellt_am = erstellt_am_feld()

    class Meta:
        managed = False
        db_table = "stellen"
        verbose_name = "Stelle"
        verbose_name_plural = "Stellen"
        ordering = ["-offen", "titel"]

    def __str__(self):
        return self.titel


class BewerbungQuerySet(models.QuerySet):
    def loeschfaellig(self, stichtag=None):
        """Bewerbungen, deren Aufbewahrungsfrist (``loeschen_ab``) erreicht ist."""
        return self.filter(loeschen_ab__lte=stichtag or timezone.localdate())


class Bewerbung(DbFelderMixin):
    db_verwaltete_felder = ("bewerbungsnummer", "eingegangen_am", "geaendert_am")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bewerbungsnummer = nummer_feld("BW", verbose_name="Bewerbungsnummer")
    stelle = models.ForeignKey(Stelle, on_delete=models.PROTECT, related_name="bewerbungen", verbose_name="Stelle")
    vorname = models.CharField("Vorname", max_length=100)
    nachname = models.CharField("Nachname", max_length=100)
    email = models.EmailField("E-Mail")
    telefon = models.CharField("Telefon", max_length=50, null=True, blank=True)
    wohnort = models.CharField("Wohnort", max_length=100, null=True, blank=True)
    verfuegbar_ab = models.DateField("Verfügbar ab", null=True, blank=True)
    stunden_pro_woche = models.DecimalField(
        "Stunden pro Woche", max_digits=4, decimal_places=1, null=True, blank=True
    )
    fuehrerschein = models.BooleanField("Führerschein", null=True, blank=True)
    erfahrung = models.TextField("Erfahrung", null=True, blank=True)
    nachricht = models.TextField("Nachricht", null=True, blank=True)
    status = models.CharField(
        "Status", max_length=20, choices=Bewerbungsstatus.choices, default=Bewerbungsstatus.EINGEGANGEN
    )
    ki_zusammenfassung = models.TextField(
        "KI-Zusammenfassung", null=True, blank=True, help_text="Nur Zusammenfassung – keine Bewertung oder Entscheidung."
    )
    datenschutz_ok_am = models.DateTimeField("Datenschutz-Einwilligung am")
    loeschen_ab = models.DateField(
        "Löschen ab",
        editable=False,
        db_default=RawSQL("current_date + 180", [], output_field=models.DateField()),
        help_text="Automatisch 6 Monate nach Eingang (AGG-Frist).",
    )
    eingegangen_am = erstellt_am_feld("Eingegangen am")
    geaendert_am = geaendert_am_feld()

    objects = BewerbungQuerySet.as_manager()

    class Meta:
        managed = False
        db_table = "bewerbungen"
        verbose_name = "Bewerbung"
        verbose_name_plural = "Bewerbungen"
        ordering = ["-eingegangen_am"]

    def __str__(self):
        return f"{self.vorname} {self.nachname} – {self.stelle}"


class Arbeitszeit(DbFelderMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mitarbeiter = models.ForeignKey(
        Mitarbeiter, on_delete=models.PROTECT, related_name="arbeitszeiten", verbose_name="Mitarbeiter"
    )
    einsatz = models.ForeignKey(
        "auftraege.Einsatz",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="arbeitszeiten",
        verbose_name="Einsatz",
    )
    beginn = models.DateTimeField("Beginn")
    ende = models.DateTimeField("Ende", null=True, blank=True)
    pause_minuten = models.PositiveSmallIntegerField("Pause (Minuten)", default=0)
    taetigkeit = models.TextField("Tätigkeit", null=True, blank=True)
    bestaetigt_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="bestaetigt_von",
        related_name="bestaetigte_arbeitszeiten",
        verbose_name="Bestätigt von",
    )
    bestaetigt_am = models.DateTimeField("Bestätigt am", null=True, blank=True)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "arbeitszeiten"
        verbose_name = "Arbeitszeit"
        verbose_name_plural = "Arbeitszeiten"
        ordering = ["-beginn"]

    def __str__(self):
        beginn = timezone.localtime(self.beginn)
        return f"{self.mitarbeiter}: {beginn:%d.%m.%Y %H:%M}"

    @property
    def stunden(self):
        """Gearbeitete Stunden abzüglich Pause (None, solange kein Ende gebucht ist)."""
        if not self.ende:
            return None
        return round((self.ende - self.beginn).total_seconds() / 3600 - self.pause_minuten / 60, 2)

    def clean(self):
        if self.ende and self.beginn:
            if self.ende <= self.beginn:
                raise ValidationError({"ende": "Das Ende muss nach dem Beginn liegen."})
            if self.pause_minuten * 60 >= (self.ende - self.beginn).total_seconds():
                raise ValidationError({"pause_minuten": "Die Pause ist länger als die Arbeitszeit."})
