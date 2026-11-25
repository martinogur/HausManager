"""Kleine Vorlagen-Hilfen des Portals: {% load portal %}"""

from decimal import Decimal

from django import template
from django.utils.formats import number_format

register = template.Library()


@register.filter
def feld_barrierearm(feld):
    """
    Rendert ein Formularfeld; bei Fehlern mit aria-invalid und Verweis auf die
    Fehlermeldung (id "<feld-id>-fehler"), damit Screenreader sie vorlesen.
    """
    attrs = {}
    beschrieben = []
    if feld.help_text:
        beschrieben.append(f"{feld.auto_id}-hilfe")
    if feld.errors:
        attrs["aria-invalid"] = "true"
        beschrieben.append(f"{feld.auto_id}-fehler")
    bestehend = feld.field.widget.attrs.get("aria-describedby")
    if bestehend:
        beschrieben.insert(0, bestehend)
    if beschrieben:
        attrs["aria-describedby"] = " ".join(beschrieben)
    return feld.as_widget(attrs=attrs)


@register.filter
def euro(wert):
    """Betrag in Euro mit deutschem Format, ohne Cent bei großen Zahlen: 12.345 €"""
    if wert in (None, ""):
        wert = 0
    wert = Decimal(str(wert))
    stellen = 0 if abs(wert) >= 1000 else 2
    return f"{number_format(wert, decimal_pos=stellen, use_l10n=True, force_grouping=True)} €"


@register.filter
def stunden(wert):
    """Stunden mit einer Nachkommastelle: 12,5 Std."""
    wert = Decimal(str(wert or 0))
    return f"{number_format(wert, decimal_pos=1, use_l10n=True, force_grouping=True)} Std."


# Lesbare Texte für Status-Werte aus den Datenbank-Enums
STATUS_TEXTE = {
    "geplant": "geplant", "zugewiesen": "zugewiesen", "in_arbeit": "in Arbeit", "erledigt": "erledigt",
    "ausgefallen": "ausgefallen", "bestaetigt": "bestätigt", "abgerechnet": "abgerechnet", "storniert": "storniert",
}


@register.filter
def status_text(wert):
    """Enum-Wert lesbar machen: in_arbeit → in Arbeit"""
    return STATUS_TEXTE.get(wert, str(wert).replace("_", " "))


@register.filter
def cent(wert):
    """Cent-Betrag als Euro: 15600 → 156,00 €"""
    return euro(Decimal(str(wert or 0)) / 100)


@register.filter
def prozent(wert):
    if wert in (None, ""):
        return "–"
    return f"{number_format(Decimal(str(wert)), decimal_pos=1, use_l10n=True)} %"


@register.filter
def get_item(woerterbuch, schluessel):
    return (woerterbuch or {}).get(schluessel)
