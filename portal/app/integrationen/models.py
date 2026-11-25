"""Integrations-Protokoll (HubSpot, Make, Craftnote, Lexware, IONOS) und Änderungsprotokoll (Audit).

Unmanaged – die Tabellen legt ``portal/db/schema.sql`` an (Migration ``kern.0001_schema``).
``audit_log`` schreiben ausschließlich die Datenbank-Trigger; das Modell ist nur lesend.
"""

import uuid

from django.db import models

from stammdaten.felder import erstellt_am_feld


class System(models.TextChoices):
    HUBSPOT = "hubspot", "HubSpot"
    MAKE = "make", "Make"
    CRAFTNOTE = "craftnote", "Craftnote"
    LEXWARE = "lexware", "Lexware Office"
    IONOS = "ionos", "IONOS"


class Syncrichtung(models.TextChoices):
    IMPORT = "import", "Import"
    EXPORT = "export", "Export"


class SyncProtokoll(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    system = models.CharField("System", max_length=20, choices=System.choices)
    richtung = models.CharField("Richtung", max_length=10, choices=Syncrichtung.choices)
    objekt_typ = models.CharField("Objekttyp", max_length=100)
    lokale_id = models.UUIDField("Lokale ID", null=True, blank=True)
    externe_id = models.CharField("Externe ID", max_length=200, null=True, blank=True)
    idempotenz_schluessel = models.CharField(
        "Idempotenz-Schlüssel", max_length=200, unique=True, null=True, blank=True
    )
    erfolgreich = models.BooleanField("Erfolgreich")
    http_status = models.SmallIntegerField("HTTP-Status", null=True, blank=True)
    fehler = models.TextField("Fehler", null=True, blank=True)
    erstellt_am = erstellt_am_feld("Zeitpunkt")

    class Meta:
        managed = False
        db_table = "sync_protokoll"
        verbose_name = "Synchronisation"
        verbose_name_plural = "Synchronisations-Protokoll"
        ordering = ["-erstellt_am"]

    def __str__(self):
        ergebnis = "ok" if self.erfolgreich else "Fehler"
        return f"{self.get_system_display()} {self.get_richtung_display()} {self.objekt_typ} ({ergebnis})"


class Auditaktion(models.TextChoices):
    INSERT = "INSERT", "Angelegt"
    UPDATE = "UPDATE", "Geändert"
    DELETE = "DELETE", "Gelöscht"


class NurLesendFehler(Exception):
    """Das Änderungsprotokoll wird nur von Datenbank-Triggern geschrieben."""


class AuditQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise NurLesendFehler("Das Änderungsprotokoll kann nicht geändert werden.")

    def delete(self):
        raise NurLesendFehler("Das Änderungsprotokoll kann nicht gelöscht werden.")

    def fuer(self, instanz):
        """Alle Einträge zu einem Datensatz (Modellinstanz mit UUID-Primärschlüssel)."""
        return self.filter(tabelle=instanz._meta.db_table, datensatz_id=instanz.pk)


class AuditEintrag(models.Model):
    id = models.BigAutoField(primary_key=True)
    tabelle = models.CharField("Tabelle", max_length=100)
    datensatz_id = models.UUIDField("Datensatz-ID", null=True, blank=True)
    aktion = models.CharField("Aktion", max_length=10, choices=Auditaktion.choices)
    alt = models.JSONField("Vorher", null=True, blank=True)
    neu = models.JSONField("Nachher", null=True, blank=True)
    benutzer = models.CharField("Benutzer", max_length=254, null=True, blank=True)
    zeitpunkt = erstellt_am_feld("Zeitpunkt")

    objects = AuditQuerySet.as_manager()

    class Meta:
        managed = False
        db_table = "audit_log"
        verbose_name = "Änderung"
        verbose_name_plural = "Änderungsprotokoll"
        ordering = ["-zeitpunkt", "-id"]

    def __str__(self):
        return f"{self.zeitpunkt:%d.%m.%Y %H:%M} {self.get_aktion_display()} {self.tabelle}"

    def save(self, *args, **kwargs):
        raise NurLesendFehler("Das Änderungsprotokoll schreibt nur die Datenbank.")

    def delete(self, *args, **kwargs):
        raise NurLesendFehler("Das Änderungsprotokoll kann nicht gelöscht werden.")
