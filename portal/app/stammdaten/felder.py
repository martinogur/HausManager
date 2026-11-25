"""Gemeinsame Bausteine für die Fachmodelle (unmanaged, Schema aus portal/db/schema.sql).

* Felder mit Datenbank-Default (Nummern, Zeitstempel) bekommen ``db_default`` und
  ``editable=False``: Django sendet beim INSERT das Schlüsselwort ``DEFAULT`` und liest
  den Wert per ``RETURNING`` zurück. Der Ausdruck in ``db_default`` spiegelt nur den
  Default aus schema.sql (die Tabellen legt Django nicht an).
* Felder, die Trigger pflegen (``geaendert_am``, Angebotssumme), werden bei UPDATE nicht
  mitgesendet und nach dem Speichern neu geladen (``DbFelderMixin``).
"""

from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Now


def naechste_nummer(praefix: str, mit_jahr: bool = True):
    """Spiegel von ``DEFAULT naechste_nummer('<praefix>'[, false])`` aus schema.sql."""
    args = [models.Value(praefix)]
    if not mit_jahr:
        args.append(models.Value(False))
    return models.Func(*args, function="naechste_nummer", output_field=models.TextField())


def nummer_feld(praefix: str, mit_jahr: bool = True, verbose_name: str = "Nummer"):
    return models.CharField(
        verbose_name,
        max_length=20,
        unique=True,
        editable=False,
        db_default=naechste_nummer(praefix, mit_jahr),
    )


def erstellt_am_feld(verbose_name: str = "Erstellt am"):
    return models.DateTimeField(verbose_name, db_default=Now(), editable=False)


def geaendert_am_feld():
    return models.DateTimeField("Geändert am", db_default=Now(), editable=False)


plz_validator = RegexValidator(r"^[0-9]{5}$", "Bitte eine fünfstellige Postleitzahl eingeben.")


class Wochentag(models.IntegerChoices):
    MONTAG = 1, "Montag"
    DIENSTAG = 2, "Dienstag"
    MITTWOCH = 3, "Mittwoch"
    DONNERSTAG = 4, "Donnerstag"
    FREITAG = 5, "Freitag"
    SAMSTAG = 6, "Samstag"
    SONNTAG = 7, "Sonntag"


class DbFelderMixin(models.Model):
    """Sendet von der Datenbank gepflegte Felder nie per UPDATE und lädt sie danach neu."""

    #: Felder, die nur die Datenbank schreibt (Default, Trigger).
    db_verwaltete_felder: tuple[str, ...] = ("erstellt_am", "geaendert_am")
    #: Davon diejenigen, die sich bei einem UPDATE in der Datenbank ändern können.
    db_nach_update_laden: tuple[str, ...] = ("geaendert_am",)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        aktualisierung = not self._state.adding and not kwargs.get("force_insert")
        if aktualisierung and kwargs.get("update_fields") is None:
            vorhanden = {f.name for f in self._meta.concrete_fields}
            kwargs["update_fields"] = [
                f.name
                for f in self._meta.concrete_fields
                if not f.primary_key and f.name not in self.db_verwaltete_felder
            ]
            neu_laden = [n for n in self.db_nach_update_laden if n in vorhanden]
        else:
            neu_laden = []
        super().save(*args, **kwargs)
        if neu_laden:
            self.refresh_from_db(fields=neu_laden)


def euro(cent) -> str:
    """Cent-Betrag deutsch formatiert, z. B. 123456 → „1.234,56 €“."""
    if cent is None:
        return "–"
    text = f"{cent / 100:,.2f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".") + " €"


class NurLesendAdminMixin:
    """Für Protokolle: ansehen ja, anlegen/ändern/löschen nein."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
