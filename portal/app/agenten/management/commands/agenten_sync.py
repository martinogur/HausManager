"""Agenten und Automatisierungen aus dem Code in die Datenbank übernehmen (nach jedem Deployment)."""

from django.core.management.base import BaseCommand

from agenten import automatisierung, laufzeit


class Command(BaseCommand):
    help = "Legt fehlende Agenten und Automatisierungen an (Betriebswerte in der DB bleiben erhalten)."

    def handle(self, *args, **options):
        self.stdout.write(f"Agenten: {laufzeit.synchronisieren()}")
        self.stdout.write(f"Automatisierungen: {automatisierung.synchronisieren()}")
