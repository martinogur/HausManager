"""Technische Ansichten des Kerns."""

import logging

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@never_cache
@require_GET
def gesund(request):
    """
    Gesundheitsprüfung für Docker/Caddy/Monitoring: prüft die Datenbank.

    Liefert bewusst keine Interna (keine Versionen, Hosts oder Fehlertexte).
    200 {"status": "ok"} oder 503 {"status": "fehler"}.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        logger.exception("Gesundheitsprüfung: Datenbank nicht erreichbar")
        return JsonResponse({"status": "fehler"}, status=503)
    return JsonResponse({"status": "ok"})
