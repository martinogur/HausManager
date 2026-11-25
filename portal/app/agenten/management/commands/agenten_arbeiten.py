"""Worker: Zeitpläne prüfen, Ereignisse verarbeiten, Agentenaufträge abarbeiten.

Betrieb: jede Minute per systemd-Timer (``hh-agenten.timer``) mit ``--einmal`` – ein Lauf dauert
höchstens ``--max-sekunden``. Mehrere gleichzeitige Läufe sind sicher (SKIP LOCKED).
"""

from django.core.management.base import BaseCommand

from agenten import automatisierung, laufzeit


class Command(BaseCommand):
    help = "Ein Arbeitslauf der Agenten (Zeitplan → Ereignisse → Aufträge → Ereignisse)."

    def add_arguments(self, parser):
        parser.add_argument("--max-auftraege", type=int, default=50)
        parser.add_argument("--max-sekunden", type=int, default=240)
        parser.add_argument("--ohne-zeitplan", action="store_true")

    def handle(self, *args, **o):
        if not o["ohne_zeitplan"]:
            gestartet = automatisierung.zeitplan_ausfuehren()
            if gestartet:
                self.stdout.write(f"Zeitplan: {', '.join(gestartet)}")
        e1 = automatisierung.ereignisse_verarbeiten()
        a = laufzeit.arbeiten(o["max_auftraege"], o["max_sekunden"])
        e2 = automatisierung.ereignisse_verarbeiten()   # Folgeereignisse der Aufträge gleich mitnehmen
        self.stdout.write(f"Ereignisse: {e1['verarbeitet'] + e2['verarbeitet']} verarbeitet, "
                          f"{e1['fehler'] + e2['fehler']} mit Fehler · Aufträge: {a}")
