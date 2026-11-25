"""
Verbindung zwischen Anwendung und Audit-Trigger der Datenbank.

Die Trigger in ``schema.sql`` (Funktion ``protokolliere``) lesen
``current_setting('app.benutzer')`` und schreiben den Wert in
``audit_log.benutzer``. Diese Hilfen setzen bzw. löschen den Wert für die
aktuelle Datenbank-Sitzung.
"""

import logging

from django.db import DatabaseError, connection

logger = logging.getLogger(__name__)

# Merker an der Verbindung, damit nur zurückgesetzt wird, wenn etwas gesetzt war
_MERKER = "hh_audit_benutzer"


def setze_audit_benutzer(email: str | None) -> None:
    """Setzt den Benutzer (E-Mail) für alle folgenden Änderungen dieser DB-Sitzung."""
    wert = email or ""
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.benutzer', %s, false)", [wert])
    setattr(connection, _MERKER, wert)


def loesche_audit_benutzer() -> None:
    """Setzt den Benutzer zurück (nach dem Request), falls vorher einer gesetzt war."""
    if not getattr(connection, _MERKER, ""):
        return
    try:
        setze_audit_benutzer("")
    except DatabaseError:
        # Verbindung kaputt oder Transaktion abgebrochen: Eine neue Verbindung
        # beginnt ohnehin ohne Wert. Sicherheitshalber schließen.
        logger.warning("Audit-Benutzer konnte nicht zurückgesetzt werden; Verbindung wird geschlossen.")
        setattr(connection, _MERKER, "")
        connection.close()
