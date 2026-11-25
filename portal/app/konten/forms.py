"""Formulare für Anmeldung und Zwei-Faktor."""

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from . import sperre

SPERR_TEXT = (
    "Zu viele Fehlversuche. Die Anmeldung ist für {minuten} Minuten gesperrt. "
    "Bitte später erneut versuchen."
)


def _sperr_fehler():
    return ValidationError(
        SPERR_TEXT.format(minuten=settings.ANMELDUNG_SPERRE_SEKUNDEN // 60), code="gesperrt"
    )


class AnmeldeFormular(AuthenticationForm):
    """E-Mail + Passwort, mit Anmeldesperre nach zu vielen Fehlversuchen."""

    error_messages = {
        "invalid_login": "E-Mail oder Passwort ist falsch.",
        "inactive": "Dieses Konto ist deaktiviert.",
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"].label = "E-Mail"
        self.fields["username"].widget = forms.EmailInput(
            attrs={"autocomplete": "email", "autofocus": True, "inputmode": "email", "autocapitalize": "none"}
        )
        self.fields["password"].label = "Passwort"

    def clean(self):
        email = (self.cleaned_data.get("username") or "").strip()
        if email and sperre.ist_gesperrt(email):
            raise _sperr_fehler()
        try:
            return super().clean()
        except ValidationError:
            if email:
                anzahl = sperre.fehlversuch_merken(email)
                if anzahl >= settings.ANMELDUNG_MAX_FEHLVERSUCHE:
                    raise _sperr_fehler() from None
            raise


class ZweiFaktorCodeFormular(forms.Form):
    """Sechsstelliger Code aus der Authenticator-App."""

    code = forms.CharField(
        label="Code aus der Authenticator-App",
        min_length=6,
        max_length=8,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9 ]*",
                "autofocus": True,
                "aria-describedby": "code-hilfe",
                "class": "code-eingabe",
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].replace(" ", "")
        if not code.isdigit():
            raise ValidationError("Bitte nur Ziffern eingeben.")
        return code
