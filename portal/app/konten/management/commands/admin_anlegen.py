"""
Legt einen Benutzer mit Rolle admin (oder buero/mitarbeiter) an.

Das Passwort steht nie im Code oder in der Befehlszeile:
* interaktiv: wird zweimal verdeckt abgefragt
* automatisiert: aus der Umgebungsvariable HH_ADMIN_PASSWORT

Beispiel:
    python manage.py admin_anlegen --email inhaber@example.org --name "Inhaber"
"""

import getpass
import os
import sys

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from konten.models import Rolle

UMGEBUNGSVARIABLE = "HH_ADMIN_PASSWORT"


class Command(BaseCommand):
    help = "Legt einen Portal-Benutzer an (Standard: Rolle admin). Passwort interaktiv oder aus HH_ADMIN_PASSWORT."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Anmelde-E-Mail")
        parser.add_argument("--name", required=True, help="Anzeigename")
        parser.add_argument("--rolle", default=Rolle.ADMIN, choices=[r.value for r in Rolle], help="Standard: admin")

    def handle(self, *args, email, name, rolle, **optionen):
        Benutzer = get_user_model()
        email = Benutzer.objects.normalize_email(email.strip())
        if Benutzer.objects.filter(email__iexact=email).exists():
            raise CommandError(f"Es gibt bereits einen Benutzer mit {email}.")

        passwort = os.environ.get(UMGEBUNGSVARIABLE)
        if passwort:
            self.stdout.write(f"Passwort wird aus {UMGEBUNGSVARIABLE} gelesen.")
        else:
            if not sys.stdin.isatty():
                raise CommandError(f"Kein Terminal: Passwort bitte über {UMGEBUNGSVARIABLE} übergeben.")
            passwort = getpass.getpass("Passwort: ")
            if passwort != getpass.getpass("Passwort wiederholen: "):
                raise CommandError("Die Passwörter stimmen nicht überein.")

        kandidat = Benutzer(email=email, anzeigename=name, rolle=rolle)
        try:
            password_validation.validate_password(passwort, kandidat)
        except ValidationError as fehler:
            raise CommandError("Passwort ungeeignet: " + " ".join(fehler.messages)) from None

        if rolle == Rolle.ADMIN:
            benutzer = Benutzer.objects.create_superuser(email=email, password=passwort, anzeigename=name)
        else:
            benutzer = Benutzer.objects.create_user(email=email, password=passwort, anzeigename=name, rolle=rolle)
        self.stdout.write(
            self.style.SUCCESS(
                f"Benutzer {benutzer.email} (Rolle {benutzer.rolle}) angelegt. "
                "Beim ersten Anmelden wird die Zwei-Faktor-Anmeldung eingerichtet."
            )
        )
