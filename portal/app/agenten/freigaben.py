"""Freigabe-Warteschlange: Agenten schlagen vor, Menschen entscheiden.

Nach einer Entscheidung führt ``entscheiden`` die vereinbarte Folgeaktion **intern** aus
(Status setzen, Entwurf übernehmen). Externer Versand (E-Mail, Instagram, Lexware) geschieht
nur über die jeweilige Integration und nur für freigegebene Datensätze.
"""

from typing import Callable

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.utils import timezone

from konten.rechte import ist_buero

from .models import Freigabe, Freigabestatus

#: art → Funktion(freigabe, benutzer) nach „freigegeben“
FOLGEAKTIONEN: dict[str, Callable] = {}
#: art → Funktion(freigabe, benutzer) nach „abgelehnt“
ABLEHNUNGSAKTIONEN: dict[str, Callable] = {}


def folgeaktion(art: str, bei: str = "freigegeben"):
    def decorator(funktion):
        (FOLGEAKTIONEN if bei == "freigegeben" else ABLEHNUNGSAKTIONEN)[art] = funktion
        return funktion

    return decorator


def anfordern(*, art: str, titel: str, angefordert_von: str, vorschlag: dict | None = None, begruendung: str | None = None,
              bezug: tuple[str, object] | None = None, agenten_auftrag=None, prioritaet: str = "normal",
              frist=None) -> Freigabe:
    """Neue Freigabe – oder die bereits offene zum selben Bezug (keine Dubletten)."""
    tabelle, bezug_id = bezug if bezug else (None, None)
    if bezug_id:
        offen = Freigabe.objects.filter(art=art, bezug_tabelle=tabelle, bezug_id=bezug_id, status=Freigabestatus.OFFEN).first()
        if offen:
            return offen
    try:
        with transaction.atomic():
            return Freigabe.objects.create(
                art=art, titel=titel[:300], begruendung=begruendung, vorschlag=vorschlag or {}, bezug_tabelle=tabelle,
                bezug_id=bezug_id, angefordert_von=angefordert_von, agenten_auftrag=agenten_auftrag,
                prioritaet=prioritaet, frist=frist,
            )
    except IntegrityError:
        return Freigabe.objects.get(art=art, bezug_tabelle=tabelle, bezug_id=bezug_id, status=Freigabestatus.OFFEN)


@transaction.atomic
def entscheiden(freigabe: Freigabe, benutzer, *, freigeben: bool, kommentar: str = "", vorschlag: dict | None = None) -> Freigabe:
    """Entscheidung durch Büro/Admin. ``vorschlag`` erlaubt, den Entwurf vor der Freigabe zu ändern."""
    if not ist_buero(benutzer):
        raise PermissionDenied("Nur Büro oder Geschäftsführung dürfen freigeben.")
    freigabe = Freigabe.objects.select_for_update().get(pk=freigabe.pk)
    if freigabe.status != Freigabestatus.OFFEN:
        raise ValueError(f"Freigabe {freigabe.freigabenummer} ist bereits entschieden.")
    if vorschlag is not None:
        freigabe.vorschlag = {**freigabe.vorschlag, **vorschlag}
    freigabe.status = Freigabestatus.FREIGEGEBEN if freigeben else Freigabestatus.ABGELEHNT
    freigabe.entschieden_von, freigabe.entschieden_am, freigabe.kommentar = benutzer, timezone.now(), kommentar or None
    freigabe.save()
    aktion = (FOLGEAKTIONEN if freigeben else ABLEHNUNGSAKTIONEN).get(freigabe.art)
    if aktion:
        aktion(freigabe, benutzer)
    return freigabe
