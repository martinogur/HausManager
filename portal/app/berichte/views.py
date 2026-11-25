"""Startseite (Dashboard) nach der Anmeldung."""

from datetime import timedelta

from django.shortcuts import render
from django.views.decorators.cache import never_cache

from konten.rechte import ist_buero, rolle_erforderlich

from . import kennzahlen as kz


@never_cache
@rolle_erforderlich()
def dashboard(request):
    """Büro/Admin: Kennzahlen + „Heute zu tun“. Mitarbeiter: nur eigene Einsätze."""
    zeitraum = kz.Zeitraum.aktuell()
    if ist_buero(request.user):
        return render(
            request,
            "berichte/dashboard.html",
            {"k": kz.kennzahlen(zeitraum), "zu_tun": kz.heute_zu_tun(zeitraum), "zeitraum": zeitraum},
        )

    morgen = zeitraum.heute + timedelta(days=1)
    return render(
        request,
        "berichte/dashboard_mitarbeiter.html",
        {
            "zeitraum": zeitraum,
            "einsaetze_heute": kz.eigene_einsaetze(request.user, zeitraum.heute),
            "einsaetze_morgen": kz.eigene_einsaetze(request.user, morgen),
            "verknuepft": kz.ist_als_mitarbeiter_verknuepft(request.user),
        },
    )


@never_cache
@rolle_erforderlich("buero")
def kennzahlen(request):
    """HTMX-Teilansicht: nur der Kennzahlen-Block (für die automatische Aktualisierung)."""
    zeitraum = kz.Zeitraum.aktuell()
    return render(request, "berichte/_kennzahlen.html", {"k": kz.kennzahlen(zeitraum), "zeitraum": zeitraum})
