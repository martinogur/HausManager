"""Agenten-Register, Agenten-Aufträge, Protokoll, Freigaben, Ereignisse, Automatisierungen, Firmenparameter.

Unmanaged – die Tabellen legt ``portal/db/erweiterungen/0003_betriebssystem.sql`` an
(Migration ``kern.0003_betriebssystem``). Schleifenschutz, Freigabepflicht und
„nur anfügen“ erzwingt die Datenbank.
"""

import uuid

from django.conf import settings
from django.db import models

from stammdaten.felder import DbFelderMixin, erstellt_am_feld, geaendert_am_feld, nummer_feld


class Prioritaet(models.TextChoices):
    NIEDRIG = "niedrig", "Niedrig"
    NORMAL = "normal", "Normal"
    HOCH = "hoch", "Hoch"
    DRINGEND = "dringend", "Dringend"


class Firmenparameter(DbFelderMixin):
    schluessel = models.CharField("Schlüssel", max_length=100, primary_key=True)
    wert = models.JSONField("Wert")
    beschreibung = models.TextField("Beschreibung")
    geaendert_am = geaendert_am_feld()

    db_verwaltete_felder = ("geaendert_am",)

    class Meta:
        managed = False
        db_table = "firmenparameter"
        verbose_name = "Firmenparameter"
        verbose_name_plural = "Firmenparameter"
        ordering = ["schluessel"]

    def __str__(self):
        return self.schluessel


class Agent(DbFelderMixin):
    code = models.CharField("Code", max_length=40, primary_key=True)
    name = models.CharField("Name", max_length=100)
    beschreibung = models.TextField("Beschreibung")
    aktiv = models.BooleanField("Aktiv", default=True)
    modell = models.CharField("KI-Modell", max_length=100, null=True, blank=True)
    tagesbudget_cent = models.IntegerField("Tagesbudget (Cent)", default=50)
    max_schritte = models.SmallIntegerField("Max. Schritte", default=8)
    max_laufzeit_sekunden = models.IntegerField("Max. Laufzeit (s)", default=120)
    max_versuche = models.SmallIntegerField("Max. Versuche", default=3)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "agenten"
        verbose_name = "Agent"
        verbose_name_plural = "Agenten"
        ordering = ["code"]

    def __str__(self):
        return self.name


class Auftragsstatus(models.TextChoices):
    WARTEND = "wartend", "Wartend"
    LAEUFT = "laeuft", "Läuft"
    ERLEDIGT = "erledigt", "Erledigt"
    FEHLGESCHLAGEN = "fehlgeschlagen", "Fehlgeschlagen"
    ABGEBROCHEN = "abgebrochen", "Abgebrochen"
    ESKALIERT = "eskaliert", "Eskaliert"


class AgentenAuftrag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.PROTECT, db_column="agent", related_name="auftraege")
    aufgabe = models.CharField("Aufgabe", max_length=60)
    eingabe = models.JSONField("Eingabe", default=dict)
    ergebnis = models.JSONField("Ergebnis", null=True, blank=True)
    status = models.CharField("Status", max_length=20, choices=Auftragsstatus.choices, default=Auftragsstatus.WARTEND)
    prioritaet = models.SmallIntegerField("Priorität (1 = dringend)", default=5)
    eltern = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="unterauftraege", verbose_name="Eltern"
    )
    # kette_id und tiefe setzt der Trigger agenten_auftraege_kette (Werte hier werden überschrieben).
    kette_id = models.UUIDField("Kette", default=uuid.uuid4, editable=False)
    tiefe = models.SmallIntegerField("Tiefe", default=0, editable=False)
    ausgeloest_von = models.CharField("Ausgelöst von", max_length=200)
    idempotenz_schluessel = models.CharField("Idempotenz-Schlüssel", max_length=200, unique=True, null=True, blank=True)
    versuche = models.SmallIntegerField("Versuche", default=0)
    max_versuche = models.SmallIntegerField("Max. Versuche", default=3)
    faellig_ab = models.DateTimeField("Fällig ab", db_default=models.functions.Now())
    gesperrt_bis = models.DateTimeField("Gesperrt bis", null=True, blank=True)
    gestartet_am = models.DateTimeField("Gestartet", null=True, blank=True)
    beendet_am = models.DateTimeField("Beendet", null=True, blank=True)
    kosten_cent = models.DecimalField("Kosten (Cent)", max_digits=10, decimal_places=4, default=0)
    fehler = models.TextField("Fehler", null=True, blank=True)
    erstellt_am = erstellt_am_feld()

    class Meta:
        managed = False
        db_table = "agenten_auftraege"
        verbose_name = "Agentenauftrag"
        verbose_name_plural = "Agentenaufträge"
        ordering = ["-erstellt_am"]

    def __str__(self):
        return f"{self.agent_id}/{self.aufgabe} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        neu = self._state.adding
        super().save(*args, **kwargs)
        if neu:
            self.refresh_from_db(fields=["kette_id", "tiefe", "faellig_ab"])


class AgentenProtokoll(models.Model):
    id = models.BigAutoField(primary_key=True)
    auftrag = models.ForeignKey(AgentenAuftrag, on_delete=models.CASCADE, related_name="protokoll")
    art = models.CharField("Art", max_length=20)
    inhalt = models.JSONField("Inhalt", default=dict)
    zeitpunkt = erstellt_am_feld("Zeitpunkt")

    class Meta:
        managed = False
        db_table = "agenten_protokoll"
        verbose_name = "Protokolleintrag"
        verbose_name_plural = "Agenten-Protokoll"
        ordering = ["id"]


class Freigabeart(models.TextChoices):
    EMAIL_VERSAND = "email_versand", "E-Mail versenden"
    ANGEBOT_VERSAND = "angebot_versand", "Angebot versenden"
    LEAD_KONTAKT = "lead_kontakt", "Akquise-Kontakt"
    SOCIAL_BEITRAG = "social_beitrag", "Social-Media-Beitrag"
    EINSATZ_ZUWEISUNG = "einsatz_zuweisung", "Einsatz zuweisen"
    RECHNUNG_ENTWURF = "rechnung_entwurf", "Rechnungsentwurf"
    ESKALATION = "eskalation", "Entscheidung / Eskalation"
    SONSTIGES = "sonstiges", "Sonstiges"


class Freigabestatus(models.TextChoices):
    OFFEN = "offen", "Offen"
    FREIGEGEBEN = "freigegeben", "Freigegeben"
    ABGELEHNT = "abgelehnt", "Abgelehnt"
    ERLEDIGT = "erledigt", "Erledigt"
    ABGELAUFEN = "abgelaufen", "Abgelaufen"


class Freigabe(DbFelderMixin):
    db_verwaltete_felder = ("freigabenummer", "erstellt_am", "geaendert_am")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    freigabenummer = nummer_feld("FG", verbose_name="Freigabe-Nr.")
    art = models.CharField("Art", max_length=30, choices=Freigabeart.choices)
    titel = models.CharField("Titel", max_length=300)
    begruendung = models.TextField("Begründung", null=True, blank=True)
    vorschlag = models.JSONField("Vorschlag", default=dict)
    bezug_tabelle = models.CharField("Bezug (Tabelle)", max_length=100, null=True, blank=True)
    bezug_id = models.UUIDField("Bezug (ID)", null=True, blank=True)
    angefordert_von = models.CharField("Angefordert von", max_length=200)
    agenten_auftrag = models.ForeignKey(
        AgentenAuftrag, on_delete=models.SET_NULL, null=True, blank=True, related_name="freigaben"
    )
    prioritaet = models.CharField("Priorität", max_length=10, choices=Prioritaet.choices, default=Prioritaet.NORMAL)
    status = models.CharField("Status", max_length=20, choices=Freigabestatus.choices, default=Freigabestatus.OFFEN)
    entschieden_von = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, db_column="entschieden_von",
        related_name="+", verbose_name="Entschieden von",
    )
    entschieden_am = models.DateTimeField("Entschieden am", null=True, blank=True)
    kommentar = models.TextField("Kommentar", null=True, blank=True)
    frist = models.DateField("Frist", null=True, blank=True)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "freigaben"
        verbose_name = "Freigabe"
        verbose_name_plural = "Freigaben"
        ordering = ["-erstellt_am"]

    def __str__(self):
        return f"{self.freigabenummer} {self.titel}"


class Ereignis(models.Model):
    id = models.BigAutoField(primary_key=True)
    typ = models.CharField("Typ", max_length=60)
    bezug_tabelle = models.CharField("Bezug (Tabelle)", max_length=100, null=True, blank=True)
    bezug_id = models.UUIDField("Bezug (ID)", null=True, blank=True)
    daten = models.JSONField("Daten", default=dict)
    idempotenz_schluessel = models.CharField(max_length=200, unique=True, null=True, blank=True)
    erstellt_am = erstellt_am_feld()
    verarbeitet_am = models.DateTimeField("Verarbeitet", null=True, blank=True)
    versuche = models.SmallIntegerField("Versuche", default=0)
    naechster_versuch = models.DateTimeField("Nächster Versuch", db_default=models.functions.Now())
    fehler = models.TextField("Fehler", null=True, blank=True)

    class Meta:
        managed = False
        db_table = "ereignisse"
        verbose_name = "Ereignis"
        verbose_name_plural = "Ereignisse"
        ordering = ["-id"]

    def __str__(self):
        return f"#{self.id} {self.typ}"


class Automatisierung(DbFelderMixin):
    code = models.CharField("Code", max_length=60, primary_key=True)
    name = models.CharField("Name", max_length=200)
    beschreibung = models.TextField("Beschreibung")
    ausloeser = models.CharField("Auslöser", max_length=200)
    aktiv = models.BooleanField("Aktiv", default=True)
    letzter_lauf = models.DateTimeField("Letzter Lauf", null=True, blank=True)
    letzter_erfolg = models.DateTimeField("Letzter Erfolg", null=True, blank=True)
    fehler_in_folge = models.IntegerField("Fehler in Folge", default=0)
    letzter_fehler = models.TextField("Letzter Fehler", null=True, blank=True)
    erstellt_am = erstellt_am_feld()
    geaendert_am = geaendert_am_feld()

    class Meta:
        managed = False
        db_table = "automatisierungen"
        verbose_name = "Automatisierung"
        verbose_name_plural = "Automatisierungen"
        ordering = ["code"]

    def __str__(self):
        return self.name


class AutomatisierungsLauf(models.Model):
    id = models.BigAutoField(primary_key=True)
    automatisierung = models.ForeignKey(
        Automatisierung, on_delete=models.CASCADE, db_column="automatisierung", related_name="laeufe"
    )
    ereignis = models.ForeignKey(Ereignis, on_delete=models.SET_NULL, null=True, blank=True, related_name="laeufe")
    gestartet_am = erstellt_am_feld("Gestartet")
    beendet_am = models.DateTimeField("Beendet", null=True, blank=True)
    erfolgreich = models.BooleanField("Erfolgreich", null=True, blank=True)
    ergebnis = models.JSONField("Ergebnis", null=True, blank=True)
    fehler = models.TextField("Fehler", null=True, blank=True)

    class Meta:
        managed = False
        db_table = "automatisierungs_laeufe"
        verbose_name = "Automatisierungslauf"
        verbose_name_plural = "Automatisierungsläufe"
        ordering = ["-gestartet_am"]
