"""Benutzerverwaltung in der Verwaltungsoberfläche – nur für die Rolle admin."""

from django import forms
from django.contrib import admin, messages
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django_otp.plugins.otp_totp.models import TOTPDevice

from .models import Benutzer


class _PasswortFelder(forms.ModelForm):
    """Gemeinsame Passwort-Felder (zweimal eingeben, Regeln prüfen)."""

    passwort1 = forms.CharField(
        label="Passwort", strip=False, required=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )
    passwort2 = forms.CharField(
        label="Passwort wiederholen",
        strip=False,
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    passwort_pflicht = False

    def clean(self):
        daten = super().clean()
        p1, p2 = daten.get("passwort1"), daten.get("passwort2")
        if self.passwort_pflicht and not p1:
            self.add_error("passwort1", "Bitte ein Passwort vergeben.")
        if p1 or p2:
            if p1 != p2:
                self.add_error("passwort2", "Die Passwörter stimmen nicht überein.")
            else:
                kandidat = self.instance
                kandidat.email = daten.get("email", kandidat.email)
                kandidat.anzeigename = daten.get("anzeigename", kandidat.anzeigename)
                try:
                    password_validation.validate_password(p1, kandidat)
                except ValidationError as fehler:
                    self.add_error("passwort1", fehler)
        return daten

    def save(self, commit=True):
        benutzer = super().save(commit=False)
        if self.cleaned_data.get("passwort1"):
            benutzer.set_password(self.cleaned_data["passwort1"])
        elif benutzer._state.adding:
            benutzer.set_unusable_password()
        if commit:
            benutzer.save()
        return benutzer


class BenutzerAnlegenFormular(_PasswortFelder):
    passwort_pflicht = True

    class Meta:
        model = Benutzer
        fields = ("email", "anzeigename", "rolle", "aktiv")


class BenutzerAendernFormular(_PasswortFelder):
    class Meta:
        model = Benutzer
        fields = ("email", "anzeigename", "rolle", "aktiv")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["passwort1"].label = "Neues Passwort (leer lassen = unverändert)"


@admin.register(Benutzer)
class BenutzerAdmin(admin.ModelAdmin):
    list_display = ("anzeigename", "email", "rolle", "aktiv", "zwei_faktor", "last_login")
    list_filter = ("rolle", "aktiv", "zwei_faktor")
    search_fields = ("anzeigename", "email")
    ordering = ("anzeigename",)
    readonly_fields = ("zwei_faktor", "last_login", "erstellt_am", "geaendert_am")
    actions = ("zwei_faktor_zuruecksetzen",)

    def get_form(self, request, obj=None, **kwargs):
        kwargs["form"] = BenutzerAnlegenFormular if obj is None else BenutzerAendernFormular
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return ((None, {"fields": ("email", "anzeigename", "rolle", "aktiv", "passwort1", "passwort2")}),)
        return (
            (None, {"fields": ("email", "anzeigename", "rolle", "aktiv")}),
            ("Passwort", {"fields": ("passwort1", "passwort2"), "classes": ("collapse",)}),
            ("Status", {"fields": ("zwei_faktor", "last_login", "erstellt_am", "geaendert_am")}),
        )

    # Nur Administratoren (has_perm liefert für buero bei "konten" ohnehin False)
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        # Benutzer werden deaktiviert, nicht gelöscht (Audit-Log, Fremdschlüssel)
        return False

    @admin.action(description="Zwei-Faktor zurücksetzen (z. B. Handy verloren)")
    def zwei_faktor_zuruecksetzen(self, request, queryset):
        anzahl = 0
        for benutzer in queryset:
            TOTPDevice.objects.filter(user=benutzer).delete()
            benutzer.zwei_faktor = False
            benutzer.save(update_fields=["zwei_faktor"])
            anzahl += 1
        self.message_user(
            request,
            f"Zwei-Faktor bei {anzahl} Benutzer(n) zurückgesetzt. Beim nächsten Anmelden wird neu eingerichtet.",
            messages.SUCCESS,
        )
