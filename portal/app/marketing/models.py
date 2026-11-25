"""Redaktionskalender (Instagram, Facebook, Google-Profil).

Unmanaged – Tabelle aus ``portal/db/erweiterungen/0003_betriebssystem.sql``.
Veröffentlichen ist nur mit Freigabe möglich (Datenbank-Regel).
"""

import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from stammdaten.felder import DbFelderMixin, erstellt_am_feld, geaendert_am_feld


class Plattform(models.TextChoices):
    INSTAGRAM = "instagram", "Instagram"
    FACEBOOK = "facebook", "Facebook"
    GOOGLE = "google", "Google-Unternehmensprofil"


class Beitragsformat(models.TextChoices):
    POST = "post", "Post"
    KARUSSELL = "karussell", "Karussell"
    REEL = "reel", "Reel"
    STORY = "story", "Story"


class Beitragsstatus(models.TextChoices):
    IDEE = "idee", "Idee"
    ENTWURF = "entwurf", "Entwurf"
    ZUR_FREIGABE = "zur_freigabe", "Zur Freigabe"
    FREIGEGEBEN = "freigegeben", "Freigegeben"
    VEROEFFENTLICHT = "veroeffentlicht", "Veröffentlicht"
    VERWORFEN = "verworfen", "Verworfen"


class SocialBeitrag(DbFelderMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plattform = models.CharField("Plattform", max_length=20, choices=Plattform.choices)
    format = models.CharField("Format", max_length=20, choices=Beitragsformat.choices)
    geplant_fuer = models.DateTimeField("Geplant für")
    thema = models.CharField("Thema", max_length=300)
    text = models.TextField("Text", null=True, blank=True)
    hashtags = ArrayField(models.TextField(), verbose_name="Hashtags", null=True, blank=True)
    bildidee = models.TextField("Bildidee", null=True, blank=True)
    medien_pfad = models.CharField("Medien", max_length=500, null=True, blank=True)
    status = models.CharField("Status", max_length=20, choices=Beitragsstatus.choices, default=Beitragsstatus.IDEE)
    freigabe = models.ForeignKey(
        "agenten.Freigabe", on_delete=models.SET_NULL, null=True, blank=True, related_name="social_beitraege"
    )
    freigegeben_von = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, db_column="freigegeben_von",
        related_name="+",
    )
    freigegeben_am = models.DateTimeField("Freigegeben am", null=True, blank=True)
    veroeffentlicht_am = models.DateTimeField("Veröffentlicht am", null=True, blank=True)
    externe_id = models.CharField("Medien-ID", max_length=100, unique=True, null=True, blank=True)
    kennzahlen = models.JSONField("Kennzahlen", null=True, blank=True)
    erstellt_von = models.CharField("Erstellt von", max_length=200)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "social_beitraege"
        verbose_name = "Beitrag"
        verbose_name_plural = "Redaktionskalender"
        ordering = ["geplant_fuer"]

    def __str__(self):
        return f"{self.get_plattform_display()} {self.get_format_display()} {self.geplant_fuer:%d.%m.%Y}: {self.thema}"
