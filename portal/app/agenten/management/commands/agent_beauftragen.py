"""Einen Agenten von Hand beauftragen, z. B.:

    manage.py agent_beauftragen ceo wochenbericht
    manage.py agent_beauftragen angebot angebot_berechnen --eingabe '{"objekt_id": "…", "leistungen": {…}}'
"""

import json

from django.core.management.base import BaseCommand

from agenten import laufzeit


class Command(BaseCommand):
    help = "Legt einen Agentenauftrag an (und führt ihn mit --sofort direkt aus)."

    def add_arguments(self, parser):
        parser.add_argument("agent")
        parser.add_argument("aufgabe")
        parser.add_argument("--eingabe", default="{}")
        parser.add_argument("--sofort", action="store_true")

    def handle(self, *args, **o):
        a = laufzeit.beauftragen(o["agent"], o["aufgabe"], json.loads(o["eingabe"]), ausgeloest_von="befehl:manage.py")
        self.stdout.write(f"Auftrag {a.id} angelegt.")
        if o["sofort"]:
            erg = laufzeit.sofort_ausfuehren(a)
            self.stdout.write(json.dumps({"status": erg.status, "ergebnis": erg.ergebnis, "fehler": erg.fehler},
                                         ensure_ascii=False, indent=2, default=str))
