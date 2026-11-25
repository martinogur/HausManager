"""Dokumente (Dateiablage-Metadaten) und Fotos zu Einsätzen.

Unmanaged – die Tabellen legt ``portal/db/schema.sql`` an (Migration ``kern.0001_schema``).
Die Dateien selbst liegen im verschlüsselten Dateispeicher (``speicher_schluessel``).
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from stammdaten.felder import erstellt_am_feld


class Dokumentkategorie(models.TextChoices):
    VERTRAG = "vertrag", "Vertrag"
    ANGEBOT = "angebot", "Angebot"
    RECHNUNG = "rechnung", "Rechnung"
    FOTO = "foto", "Foto"
    BEWERBUNG = "bewerbung", "Bewerbung"
    NACHWEIS = "nachweis", "Nachweis"
    EMAIL = "email", "E-Mail"
    SONSTIGES = "sonstiges", "Sonstiges"


class Fototyp(models.TextChoices):
    VORHER = "vorher", "Vorher"
    NACHHER = "nachher", "Nachher"
    SCHADEN = "schaden", "Schaden"
    PROTOKOLL = "protokoll", "Protokoll"
    SONSTIGES = "sonstiges", "Sonstiges"


BEZUGSFELDER = ("kunde", "objekt", "auftrag", "einsatz", "mitarbeiter", "bewerbung")


class Dokument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dateiname = models.CharField("Dateiname", max_length=255)
    mime_typ = models.CharField("Dateityp (MIME)", max_length=100)
    groesse_bytes = models.PositiveBigIntegerField("Größe (Bytes)")
    sha256 = models.CharField("SHA-256-Prüfsumme", max_length=64)
    speicher_schluessel = models.CharField("Speicherpfad", max_length=500, unique=True)
    kategorie = models.CharField(
        "Kategorie", max_length=30, choices=Dokumentkategorie.choices, default=Dokumentkategorie.SONSTIGES
    )
    kunde = models.ForeignKey(
        "stammdaten.Kunde", on_delete=models.CASCADE, null=True, blank=True, related_name="dokumente",
        verbose_name="Kunde",
    )
    objekt = models.ForeignKey(
        "stammdaten.Objekt", on_delete=models.CASCADE, null=True, blank=True, related_name="dokumente",
        verbose_name="Objekt",
    )
    auftrag = models.ForeignKey(
        "auftraege.Auftrag", on_delete=models.CASCADE, null=True, blank=True, related_name="dokumente",
        verbose_name="Auftrag",
    )
    einsatz = models.ForeignKey(
        "auftraege.Einsatz", on_delete=models.CASCADE, null=True, blank=True, related_name="dokumente",
        verbose_name="Einsatz",
    )
    mitarbeiter = models.ForeignKey(
        "personal.Mitarbeiter", on_delete=models.CASCADE, null=True, blank=True, related_name="dokumente",
        verbose_name="Mitarbeiter",
    )
    bewerbung = models.ForeignKey(
        "personal.Bewerbung", on_delete=models.CASCADE, null=True, blank=True, related_name="dokumente",
        verbose_name="Bewerbung",
    )
    hochgeladen_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="hochgeladen_von",
        related_name="hochgeladene_dokumente",
        verbose_name="Hochgeladen von",
    )
    loeschen_ab = models.DateField("Löschen ab", null=True, blank=True)
    erstellt_am = erstellt_am_feld("Hochgeladen am")

    class Meta:
        managed = False
        db_table = "dokumente"
        verbose_name = "Dokument"
        verbose_name_plural = "Dokumente"
        ordering = ["-erstellt_am"]

    def __str__(self):
        return self.dateiname

    def clean(self):
        if not any(getattr(self, f"{f}_id") for f in BEZUGSFELDER):
            raise ValidationError(
                "Bitte das Dokument mindestens einem Kunden, Objekt, Auftrag, Einsatz, Mitarbeiter "
                "oder einer Bewerbung zuordnen."
            )


class Foto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dokument = models.OneToOneField(Dokument, on_delete=models.CASCADE, related_name="foto", verbose_name="Datei")
    einsatz = models.ForeignKey("auftraege.Einsatz", on_delete=models.CASCADE, related_name="fotos", verbose_name="Einsatz")
    typ = models.CharField("Art", max_length=20, choices=Fototyp.choices)
    aufgenommen_am = models.DateTimeField("Aufgenommen am", null=True, blank=True)
    beschreibung = models.TextField("Beschreibung", null=True, blank=True)

    class Meta:
        managed = False
        db_table = "fotos"
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"
        ordering = ["einsatz", "aufgenommen_am"]

    def __str__(self):
        return f"{self.get_typ_display()}: {self.dokument.dateiname}"
