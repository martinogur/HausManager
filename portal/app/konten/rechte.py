"""
Rechte-Hilfen für alle Apps.

Rollen: admin (alles), buero (Büro-Rechte), mitarbeiter (nur Eigenes).
Ein admin erfüllt immer jede Rollen-Anforderung.

Beispiele::

    from konten.rechte import rolle_erforderlich, RolleErforderlichMixin, ist_buero

    @rolle_erforderlich("buero")            # buero oder admin
    def kundenliste(request): ...

    class KundenAnsicht(RolleErforderlichMixin, ListView):
        erlaubte_rollen = ("buero",)

    if ist_buero(request.user): ...
"""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django_htmx.http import HttpResponseClientRedirect

from .models import Rolle


def hat_rolle(user, *rollen) -> bool:
    """True, wenn der Benutzer angemeldet, aktiv und in einer der Rollen ist (admin immer)."""
    if user is None or not user.is_authenticated or not user.is_active:
        return False
    return user.rolle == Rolle.ADMIN or user.rolle in rollen


def ist_admin(user) -> bool:
    return hat_rolle(user, Rolle.ADMIN)


def ist_buero(user) -> bool:
    """Büro-Rechte: Rolle buero oder admin."""
    return hat_rolle(user, Rolle.BUERO)


def ist_mitarbeiter(user) -> bool:
    """Nur die Rolle mitarbeiter (ohne Büro-/Admin-Rechte)."""
    return user is not None and user.is_authenticated and user.is_active and user.rolle == Rolle.MITARBEITER


def _nicht_angemeldet(request):
    """Weiterleitung zur Anmeldung; bei HTMX-Anfragen als ganze Seite (HX-Redirect)."""
    antwort = redirect_to_login(request.get_full_path())
    if getattr(request, "htmx", False):
        return HttpResponseClientRedirect(antwort["Location"])
    return antwort


def pruefe_rolle(request, rollen):
    """Gibt eine Antwort (Weiterleitung) zurück oder wirft PermissionDenied; None = erlaubt."""
    if not request.user.is_authenticated:
        return _nicht_angemeldet(request)
    if rollen and not hat_rolle(request.user, *rollen):
        raise PermissionDenied("Für diese Seite fehlt die Berechtigung.")
    return None


def rolle_erforderlich(*rollen):
    """
    Decorator für Funktions-Ansichten. Ohne Rollen genügt "angemeldet".
    Nicht angemeldet → Anmeldung; falsche Rolle → 403.
    """

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            antwort = pruefe_rolle(request, rollen)
            if antwort is not None:
                return antwort
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


class RolleErforderlichMixin:
    """Mixin für klassenbasierte Ansichten. ``erlaubte_rollen = ("buero",)``; leer = nur angemeldet."""

    erlaubte_rollen: tuple[str, ...] = ()

    def dispatch(self, request, *args, **kwargs):
        antwort = pruefe_rolle(request, self.erlaubte_rollen)
        if antwort is not None:
            return antwort
        return super().dispatch(request, *args, **kwargs)
