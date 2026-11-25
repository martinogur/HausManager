"""Werte, die in allen Vorlagen zur Verfügung stehen."""

from django.conf import settings


def portal(request):
    user = getattr(request, "user", None)
    return {
        "PORTAL_NAME": "Hausmeister Helden",
        "PORTAL_DEBUG": settings.DEBUG,
        # Darf der Benutzer die Verwaltungsoberfläche sehen? (admin/buero)
        "zeige_verwaltung": bool(user is not None and user.is_authenticated and user.is_staff),
    }
