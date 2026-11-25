"""E-Mail-Protokoll (Ein- und Ausgang).

Unmanaged – die Tabelle legt ``portal/db/schema.sql`` an (Migration ``kern.0001_schema``).
Ausgehende Mails dürfen nur nach Freigabe gesendet werden – das prüft die Datenbank.
"""

import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models

from stammdaten.felder import DbFelderMixin, erstellt_am_feld, geaendert_am_feld


class Mailrichtung(models.TextChoices):
    EINGANG = "eingang", "Eingang"
    AUSGANG = "ausgang", "Ausgang"


class Mailstatus(models.TextChoices):
    NEU = "neu", "Neu"
    ZUGEORDNET = "zugeordnet", "Zugeordnet"
    ENTWURF = "entwurf", "Entwurf"
    FREIGEGEBEN = "freigegeben", "Freigegeben"
    GESENDET = "gesendet", "Gesendet"
    VERWORFEN = "verworfen", "Verworfen"
    FEHLER = "fehler", "Fehler"


class EmailProtokollQuerySet(models.QuerySet):
    def offen(self):
        """Neue Eingänge und Antwortentwürfe, die noch jemand ansehen muss."""
        return self.filter(status__in=(Mailstatus.NEU, Mailstatus.ENTWURF))


class EmailProtokoll(DbFelderMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    richtung = models.CharField("Richtung", max_length=10, choices=Mailrichtung.choices)
    message_id = models.CharField("Message-ID", max_length=500, null=True, blank=True)
    in_reply_to = models.CharField("Antwort auf (Message-ID)", max_length=500, null=True, blank=True)
    postfach = models.CharField("Postfach", max_length=254)
    von = models.EmailField("Von")
    an = ArrayField(models.EmailField(), verbose_name="An")
    betreff = models.CharField("Betreff", max_length=500, null=True, blank=True)
    text_auszug = models.TextField("Textauszug", null=True, blank=True)
    empfangen_am = models.DateTimeField("Empfangen am", null=True, blank=True)
    status = models.CharField("Status", max_length=20, choices=Mailstatus.choices, default=Mailstatus.NEU)
    kunde = models.ForeignKey(
        "stammdaten.Kunde", on_delete=models.SET_NULL, null=True, blank=True, related_name="emails",
        verbose_name="Kunde",
    )
    ansprechpartner = models.ForeignKey(
        "stammdaten.Ansprechpartner", on_delete=models.SET_NULL, null=True, blank=True, related_name="emails",
        verbose_name="Ansprechpartner",
    )
    anfrage = models.ForeignKey(
        "auftraege.Anfrage", on_delete=models.SET_NULL, null=True, blank=True, related_name="emails",
        verbose_name="Anfrage",
    )
    bewerbung = models.ForeignKey(
        "personal.Bewerbung", on_delete=models.SET_NULL, null=True, blank=True, related_name="emails",
        verbose_name="Bewerbung",
    )
    antwort_auf = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="antworten",
        verbose_name="Antwort auf",
    )
    ki_zusammenfassung = models.TextField("KI-Zusammenfassung", null=True, blank=True)
    entwurf_text = models.TextField(
        "Antwortentwurf", null=True, blank=True, help_text="KI-Vorschlag – wird nie ohne Freigabe gesendet."
    )
    freigegeben_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="freigegeben_von",
        related_name="freigegebene_emails",
        verbose_name="Freigegeben von",
    )
    freigegeben_am = models.DateTimeField("Freigegeben am", null=True, blank=True)
    gesendet_am = models.DateTimeField("Gesendet am", null=True, blank=True)
    fehler = models.TextField("Fehler", null=True, blank=True)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    objects = EmailProtokollQuerySet.as_manager()

    class Meta:
        managed = False
        db_table = "email_protokolle"
        verbose_name = "E-Mail"
        verbose_name_plural = "E-Mail-Protokoll"
        ordering = ["-empfangen_am", "-erstellt_am"]

    def __str__(self):
        return f"{self.get_richtung_display()}: {self.betreff or '(ohne Betreff)'}"

    def clean(self):
        if (
            self.richtung == Mailrichtung.AUSGANG
            and self.status in (Mailstatus.FREIGEGEBEN, Mailstatus.GESENDET)
            and not (self.freigegeben_von_id and self.freigegeben_am)
        ):
            raise ValidationError({"status": "Ausgehende E-Mails brauchen vor dem Versand eine Freigabe."})
        if self.status == Mailstatus.GESENDET and not self.gesendet_am:
            raise ValidationError({"gesendet_am": "Bitte den Sendezeitpunkt angeben."})
