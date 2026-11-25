"""Verwaltungsoberfläche (Django-Admin) mit Pflicht-2FA und eigener Anmeldung."""

from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse
from django_otp.admin import OTPAdminSite


class PortalAdminSite(OTPAdminSite):
    """
    Zugang nur für Rollen admin/buero mit bestätigtem zweiten Faktor
    (``is_staff`` leitet sich aus der Rolle ab, ``is_verified`` aus django-otp).
    """

    site_header = "Hausmeister Helden – Verwaltung"
    site_title = "HH Verwaltung"
    index_title = "Datenpflege"
    site_url = "/"
    enable_nav_sidebar = True

    def __init__(self, name="admin"):
        # Der Name "admin" hält die URL-Namen (admin:index usw.) wie gewohnt.
        super().__init__(name)

    def login(self, request, extra_context=None):
        """
        Keine eigene Admin-Anmeldung: Wer nicht angemeldet ist, landet auf der
        Portal-Anmeldung (mit Sperre und 2FA). Angemeldete ohne Admin-Recht
        (z. B. Rolle mitarbeiter) bekommen 403 statt einer Anmeldeschleife.
        """
        if request.user.is_authenticated:
            if self.has_permission(request):
                return HttpResponseRedirect(request.GET.get("next") or reverse("admin:index"))
            raise PermissionDenied("Kein Zugang zur Verwaltung.")
        ziel = request.GET.get("next") or reverse("admin:index")
        return HttpResponseRedirect(f"{reverse('konten:anmelden')}?{urlencode({'next': ziel})}")
