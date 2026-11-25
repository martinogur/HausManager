"""Pflicht zum zweiten Faktor (TOTP) für Rollen admin und buero."""

from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django_htmx.http import HttpResponseClientRedirect
from django_otp import user_has_device


class ZweiFaktorPflichtMiddleware:
    """
    Angemeldete Benutzer ohne bestätigten zweiten Faktor in dieser Sitzung werden
    umgeleitet:

    * Rolle admin/buero ohne eingerichtetes Gerät → Einrichtung (QR-Code)
    * Benutzer mit eingerichtetem Gerät (jede Rolle) → Code-Abfrage

    Muss nach ``django_otp.middleware.OTPMiddleware`` stehen.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _ausgenommen(self, pfad: str) -> bool:
        frei = (
            reverse("konten:zwei_faktor_einrichten"),
            reverse("konten:zwei_faktor_pruefen"),
            reverse("konten:abmelden"),
            reverse("kern:gesund"),
        )
        return pfad in frei or pfad.startswith(settings.STATIC_URL)

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and not user.is_verified()
            and not self._ausgenommen(request.path)
        ):
            hat_geraet = user_has_device(user, confirmed=True)
            if hat_geraet or user.braucht_zwei_faktor:
                ziel = "konten:zwei_faktor_pruefen" if hat_geraet else "konten:zwei_faktor_einrichten"
                weiter = request.get_full_path() if request.method == "GET" else reverse(settings.LOGIN_REDIRECT_URL)
                url = f"{reverse(ziel)}?{urlencode({'next': weiter})}"
                if getattr(request, "htmx", False):
                    return HttpResponseClientRedirect(url)
                return redirect(url)
        return self.get_response(request)
