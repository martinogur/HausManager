"""
Benutzer des Portals.

Die Tabelle ``hh.benutzer`` stammt aus ``portal/db/schema.sql`` (managed=False).
Die Login-Spalten ``password`` und ``last_login`` ergänzt die Migration
``konten.0001_initial``. Rechte ergeben sich ausschließlich aus ``rolle``:

* admin       – alles, auch Benutzerverwaltung
* buero       – Verwaltungsoberfläche (lesen/schreiben) außer Benutzer- und 2FA-Verwaltung
* mitarbeiter – keine Verwaltungsoberfläche, später nur eigene Einsätze
"""

import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone


class Rolle(models.TextChoices):
    ADMIN = "admin", "Administrator"
    BUERO = "buero", "Büro"
    MITARBEITER = "mitarbeiter", "Mitarbeiter"


# Apps, deren Daten das Büro in der Verwaltungsoberfläche NICHT sehen darf
NUR_ADMIN_APPS = frozenset({"konten", "auth", "otp_totp", "django_otp", "sessions", "admin", "contenttypes"})


class BenutzerManager(BaseUserManager):
    """Legt Benutzer an; die Rolle bestimmt alle Rechte."""

    use_in_migrations = True

    def _anlegen(self, email, password, **felder):
        if not email:
            raise ValueError("Eine E-Mail-Adresse ist erforderlich.")
        email = self.normalize_email(email)
        felder.setdefault("anzeigename", email.split("@")[0])
        benutzer = self.model(email=email, **felder)
        # Ohne Passwort wird ein unbrauchbares gesetzt (Anmeldung unmöglich).
        benutzer.set_password(password)
        benutzer.save(using=self._db)
        return benutzer

    def create_user(self, email, password=None, **felder):
        felder.setdefault("rolle", Rolle.MITARBEITER)
        return self._anlegen(email, password, **felder)

    def create_superuser(self, email, password=None, **felder):
        felder["rolle"] = Rolle.ADMIN
        felder.setdefault("aktiv", True)
        return self._anlegen(email, password, **felder)


class Benutzer(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField("E-Mail", unique=True)  # citext in der DB
    anzeigename = models.CharField("Anzeigename", max_length=200)
    rolle = models.CharField("Rolle", max_length=20, choices=Rolle.choices, default=Rolle.MITARBEITER)
    aktiv = models.BooleanField("Aktiv", default=True)
    zwei_faktor = models.BooleanField(
        "Zwei-Faktor eingerichtet", default=False, help_text="Wird bei der 2FA-Einrichtung automatisch gesetzt."
    )
    erstellt_am = models.DateTimeField("Erstellt am", default=timezone.now, editable=False)
    # Setzt der Datenbank-Trigger bei jeder Änderung
    geaendert_am = models.DateTimeField("Geändert am", default=timezone.now, editable=False)

    objects = BenutzerManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["anzeigename"]

    class Meta:
        managed = False
        db_table = "benutzer"
        verbose_name = "Benutzer"
        verbose_name_plural = "Benutzer"
        ordering = ["anzeigename"]

    def __str__(self):
        return f"{self.anzeigename} <{self.email}>"

    # ------------------------------------------------------------------ Django-Schnittstelle
    @property
    def is_active(self):
        return self.aktiv

    @property
    def is_staff(self):
        """Zugang zur Verwaltungsoberfläche: admin und buero."""
        return self.aktiv and self.rolle in (Rolle.ADMIN, Rolle.BUERO)

    @property
    def is_superuser(self):
        return self.aktiv and self.rolle == Rolle.ADMIN

    def has_perm(self, perm, obj=None):
        """admin: alles; buero: alles außer Benutzer/2FA/Technik; mitarbeiter: nichts."""
        if not self.aktiv:
            return False
        if self.rolle == Rolle.ADMIN:
            return True
        if self.rolle == Rolle.BUERO:
            app_label = perm.split(".", 1)[0]
            return app_label not in NUR_ADMIN_APPS
        return False

    def has_perms(self, perm_list, obj=None):
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        if not self.aktiv:
            return False
        if self.rolle == Rolle.ADMIN:
            return True
        return self.rolle == Rolle.BUERO and app_label not in NUR_ADMIN_APPS

    def get_full_name(self):
        return self.anzeigename

    def get_short_name(self):
        return self.anzeigename

    # ------------------------------------------------------------------ Rollen-Hilfen
    def hat_rolle(self, *rollen):
        return self.aktiv and self.rolle in rollen

    @property
    def braucht_zwei_faktor(self):
        """Ist der zweite Faktor für diese Rolle Pflicht?"""
        from django.conf import settings

        return self.rolle in settings.ZWEI_FAKTOR_PFLICHT_ROLLEN
