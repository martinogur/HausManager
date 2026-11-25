"""Auftragsstatus: erlaubte Wechsel (Spiegel des DB-Triggers ``auftraege_statuswechsel``).

Die Datenbank ist die verbindliche Regel. Diese Tabelle dient der Oberfläche (nur gültige
Schaltflächen anzeigen) und liefert verständliche Fehlermeldungen vor dem Speichern.
"""

from django.db import transaction

from .models import Auftrag, Auftragsstatus, Rechnung

S = Auftragsstatus

ERLAUBT: dict[str, tuple[str, ...]] = {
    S.ANFRAGE: (S.ZU_PRUEFEN, S.ANGEBOT, S.BESTAETIGT, S.STORNIERT),
    S.ZU_PRUEFEN: (S.ANFRAGE, S.ANGEBOT, S.BESTAETIGT, S.STORNIERT),
    S.ANGEBOT: (S.ZU_PRUEFEN, S.BESTAETIGT, S.STORNIERT),
    S.BESTAETIGT: (S.ANGEBOT, S.GEPLANT, S.IN_ARBEIT, S.STORNIERT),
    S.GEPLANT: (S.BESTAETIGT, S.IN_ARBEIT, S.ERLEDIGT, S.STORNIERT),
    S.IN_ARBEIT: (S.GEPLANT, S.ERLEDIGT),
    S.ERLEDIGT: (S.IN_ARBEIT, S.ABGERECHNET),
    S.ABGERECHNET: (),
    S.STORNIERT: (S.ANFRAGE,),
}

#: Status, die ein Mitarbeiter (mobil) selbst setzen darf – alles andere macht das Büro.
MITARBEITER_DARF = {S.IN_ARBEIT, S.ERLEDIGT}


class StatuswechselFehler(ValueError):
    pass


def moegliche_wechsel(auftrag: Auftrag) -> list[tuple[str, str]]:
    return [(s, S(s).label) for s in ERLAUBT[auftrag.status]]


def pruefe_wechsel(auftrag: Auftrag, neu: str) -> None:
    if neu not in S.values:
        raise StatuswechselFehler(f"Unbekannter Status „{neu}“.")
    if neu == auftrag.status:
        return
    if neu not in ERLAUBT[auftrag.status]:
        raise StatuswechselFehler(f"Von „{S(auftrag.status).label}“ geht es nicht direkt zu „{S(neu).label}“.")
    if neu == S.ABGERECHNET and not Rechnung.objects.filter(auftrag=auftrag).exclude(status="storniert").exists():
        raise StatuswechselFehler("Erst eine Rechnung anlegen (bzw. aus Lexware übernehmen), dann „abgerechnet“.")


@transaction.atomic
def status_wechseln(auftrag: Auftrag, neu: str) -> Auftrag:
    """Setzt den Status (Ereignis ``auftrag.status`` erzeugt der DB-Trigger)."""
    auftrag = Auftrag.objects.select_for_update().get(pk=auftrag.pk)
    pruefe_wechsel(auftrag, neu)
    auftrag.status = neu
    auftrag.save(update_fields=["status"])
    auftrag.refresh_from_db(fields=["status", "bestaetigt_am", "geaendert_am"])
    return auftrag
