"""Anmeldung, Abmeldung und Zwei-Faktor-Einrichtung/-Abfrage."""

import base64
import logging
from urllib.parse import urlencode

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django_otp import login as otp_login
from django_otp import match_token, user_has_device
from django_otp.plugins.otp_totp.models import TOTPDevice

from kern.audit import setze_audit_benutzer

from . import sperre
from .forms import AnmeldeFormular, ZweiFaktorCodeFormular

logger = logging.getLogger("konten.sicherheit")

GERAETE_NAME = "Authenticator-App"


def _weiter_ziel(request) -> str:
    """Sicheres Weiterleitungsziel aus ?next= (nur eigene Seiten)."""
    ziel = request.POST.get("next") or request.GET.get("next") or ""
    if ziel and url_has_allowed_host_and_scheme(ziel, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return ziel
    return reverse(settings.LOGIN_REDIRECT_URL)


def _mit_weiter(url_name: str, ziel: str) -> str:
    return f"{reverse(url_name)}?{urlencode({'next': ziel})}"


class AnmeldenAnsicht(LoginView):
    template_name = "konten/anmelden.html"
    authentication_form = AnmeldeFormular
    redirect_authenticated_user = True

    def form_valid(self, form):
        benutzer = form.get_user()
        sperre.zuruecksetzen(benutzer.email)
        # Auch die Aktualisierung von last_login beim Anmelden im Audit-Log zuordnen
        setze_audit_benutzer(benutzer.email)
        logger.info("Anmeldung erfolgreich (Rolle %s)", benutzer.rolle)
        return super().form_valid(form)


class AbmeldenAnsicht(LogoutView):
    """Abmelden nur per POST (CSRF-geschützt)."""


def _qr_svg(daten: str) -> str:
    """QR-Code als eingebettetes SVG (keine externen Dienste, kein Bild-Upload)."""
    bild = qrcode.make(daten, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    svg = bild.to_string(encoding="unicode")
    # Für Screenreader beschriften
    return svg.replace("<svg ", '<svg role="img" aria-label="QR-Code für die Authenticator-App" ', 1)


def _schluessel_lesbar(geraet: TOTPDevice) -> str:
    """Geheimschlüssel in Base32, in Vierergruppen – zum Abtippen, falls Scannen nicht geht."""
    b32 = base64.b32encode(geraet.bin_key).decode("ascii").rstrip("=")
    return " ".join(b32[i : i + 4] for i in range(0, len(b32), 4))


@never_cache
@sensitive_post_parameters("code")
@login_required
def zwei_faktor_einrichten(request):
    """Neues TOTP-Gerät anlegen, QR-Code zeigen und mit einem Code bestätigen."""
    user = request.user
    if user_has_device(user, confirmed=True):
        # Schon eingerichtet: nur noch Code abfragen (bzw. weiter, wenn bestätigt)
        if user.is_verified():
            return redirect(_weiter_ziel(request))
        return redirect(_mit_weiter("konten:zwei_faktor_pruefen", _weiter_ziel(request)))

    # Ein unbestätigtes Gerät wiederverwenden, damit der QR-Code beim Neuladen gleich bleibt
    geraet = TOTPDevice.objects.filter(user=user, confirmed=False).order_by("-id").first()
    if geraet is None:
        geraet = TOTPDevice.objects.create(user=user, name=GERAETE_NAME, confirmed=False)

    formular = ZweiFaktorCodeFormular(request.POST or None)
    if request.method == "POST" and formular.is_valid():
        if sperre.ist_gesperrt(user.email, "2fa"):
            return _zu_viele_versuche(request)
        if geraet.verify_token(formular.cleaned_data["code"]):
            geraet.confirmed = True
            geraet.save(update_fields=["confirmed"])
            # Andere, nie bestätigte Geräte aufräumen
            TOTPDevice.objects.filter(user=user, confirmed=False).delete()
            user.zwei_faktor = True
            user.save(update_fields=["zwei_faktor"])
            otp_login(request, geraet)
            sperre.zuruecksetzen(user.email, "2fa")
            logger.info("Zwei-Faktor eingerichtet (Rolle %s)", user.rolle)
            messages.success(request, "Zwei-Faktor-Anmeldung ist eingerichtet.")
            return redirect(_weiter_ziel(request))
        if sperre.fehlversuch_merken(user.email, "2fa") >= settings.ANMELDUNG_MAX_FEHLVERSUCHE:
            return _zu_viele_versuche(request)
        formular.add_error("code", "Der Code stimmt nicht. Bitte den aktuellen Code eingeben.")

    return render(
        request,
        "konten/zwei_faktor_einrichten.html",
        {
            "formular": formular,
            "qr_svg": mark_safe(_qr_svg(geraet.config_url)),  # noqa: S308 – selbst erzeugtes SVG
            "schluessel": _schluessel_lesbar(geraet),
            "next": _weiter_ziel(request),
        },
    )


@never_cache
@sensitive_post_parameters("code")
@login_required
def zwei_faktor_pruefen(request):
    """Code-Abfrage nach der Passwort-Anmeldung."""
    user = request.user
    if not user_has_device(user, confirmed=True):
        return redirect(_mit_weiter("konten:zwei_faktor_einrichten", _weiter_ziel(request)))
    if user.is_verified():
        return redirect(_weiter_ziel(request))

    formular = ZweiFaktorCodeFormular(request.POST or None)
    if request.method == "POST" and formular.is_valid():
        if sperre.ist_gesperrt(user.email, "2fa"):
            return _zu_viele_versuche(request)
        geraet = match_token(user, formular.cleaned_data["code"])
        if geraet is not None:
            otp_login(request, geraet)
            sperre.zuruecksetzen(user.email, "2fa")
            return redirect(_weiter_ziel(request))
        if sperre.fehlversuch_merken(user.email, "2fa") >= settings.ANMELDUNG_MAX_FEHLVERSUCHE:
            return _zu_viele_versuche(request)
        formular.add_error("code", "Der Code stimmt nicht. Bitte den aktuellen Code eingeben.")

    return render(request, "konten/zwei_faktor_pruefen.html", {"formular": formular, "next": _weiter_ziel(request)})


def _zu_viele_versuche(request):
    """Nach zu vielen falschen Codes: abmelden und zur Anmeldung (dort greift die Sperre)."""
    email = request.user.email
    logout(request)
    # Auch die Passwort-Anmeldung für die Sperrzeit blockieren
    sperre.sperren(email)
    messages.error(
        request,
        f"Zu viele falsche Codes. Die Anmeldung ist für {settings.ANMELDUNG_SPERRE_SEKUNDEN // 60} Minuten gesperrt.",
    )
    return redirect("konten:anmelden")
