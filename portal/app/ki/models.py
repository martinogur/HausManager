"""KI-Protokoll: jeder KI-Aufruf mit Zweck, Modell, Tokens und Kosten (Transparenz).

Unmanaged – die Tabelle legt ``portal/db/schema.sql`` an (Migration ``kern.0001_schema``).
"""

import uuid

from django.db import models

from stammdaten.felder import erstellt_am_feld


class KiAufruf(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zweck = models.CharField(
        "Zweck", max_length=100, help_text="z. B. anfrage_zusammenfassen, antwort_entwurf, wochenbericht"
    )
    modell = models.CharField("Modell", max_length=100)
    bezug_tabelle = models.CharField("Bezug (Tabelle)", max_length=100, null=True, blank=True)
    bezug_id = models.UUIDField("Bezug (ID)", null=True, blank=True)
    eingabe_tokens = models.IntegerField("Eingabe-Tokens", null=True, blank=True)
    ausgabe_tokens = models.IntegerField("Ausgabe-Tokens", null=True, blank=True)
    kosten_cent = models.DecimalField("Kosten (Cent)", max_digits=10, decimal_places=4, null=True, blank=True)
    erfolgreich = models.BooleanField("Erfolgreich")
    agent = models.ForeignKey(
        "agenten.Agent", on_delete=models.SET_NULL, null=True, blank=True, db_column="agent",
        related_name="ki_aufrufe", verbose_name="Agent",
    )
    agenten_auftrag = models.ForeignKey(
        "agenten.AgentenAuftrag", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ki_aufrufe", verbose_name="Agentenauftrag",
    )
    fehler = models.TextField("Fehler", null=True, blank=True)
    erstellt_am = erstellt_am_feld("Zeitpunkt")

    class Meta:
        managed = False
        db_table = "ki_aufrufe"
        verbose_name = "KI-Aufruf"
        verbose_name_plural = "KI-Aufrufe"
        ordering = ["-erstellt_am"]

    def __str__(self):
        return f"{self.zweck} ({self.modell})"
