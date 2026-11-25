"""
Anmeldesperre nach zu vielen Fehlversuchen (ohne Zusatzpaket).

Zähler liegen im Django-Zwischenspeicher (Datenbank-Cache, gilt für alle
Prozesse). Schlüssel ist ein Hash der kleingeschriebenen E-Mail – so steht
keine Adresse im Klartext im Cache, und die Sperre greift unabhängig davon,
ob das Konto existiert (verrät also nichts über vorhandene Konten).

Dieselbe Sperre gilt für falsche 2FA-Codes (Bereich "2fa").
"""

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("konten.sicherheit")


def _schluessel(bereich: str, kennung: str) -> str:
    digest = hashlib.sha256(kennung.strip().lower().encode("utf-8")).hexdigest()[:40]
    return f"anmeldesperre:{bereich}:{digest}"


def _maskiert(kennung: str) -> str:
    """E-Mail für Protokolle kürzen: m***@example.org"""
    name, _, domain = kennung.partition("@")
    return f"{name[:1]}***@{domain}" if domain else "***"


def ist_gesperrt(kennung: str, bereich: str = "login") -> bool:
    return (cache.get(_schluessel(bereich, kennung)) or 0) >= settings.ANMELDUNG_MAX_FEHLVERSUCHE


def fehlversuch_merken(kennung: str, bereich: str = "login") -> int:
    """Zählt einen Fehlversuch. Die Frist beginnt mit dem ersten Fehlversuch neu."""
    schluessel = _schluessel(bereich, kennung)
    anzahl = (cache.get(schluessel) or 0) + 1
    cache.set(schluessel, anzahl, timeout=settings.ANMELDUNG_SPERRE_SEKUNDEN)
    if anzahl >= settings.ANMELDUNG_MAX_FEHLVERSUCHE:
        logger.warning("Anmeldung gesperrt (%s) für %s nach %d Fehlversuchen", bereich, _maskiert(kennung), anzahl)
    else:
        logger.info("Fehlversuch %d (%s) für %s", anzahl, bereich, _maskiert(kennung))
    return anzahl


def zuruecksetzen(kennung: str, bereich: str = "login") -> None:
    cache.delete(_schluessel(bereich, kennung))


def sperren(kennung: str, bereich: str = "login") -> None:
    """Sperrt sofort für die volle Sperrzeit (z. B. nach zu vielen falschen 2FA-Codes)."""
    cache.set(
        _schluessel(bereich, kennung), settings.ANMELDUNG_MAX_FEHLVERSUCHE, timeout=settings.ANMELDUNG_SPERRE_SEKUNDEN
    )
    logger.warning("Anmeldung gesperrt (%s) für %s", bereich, _maskiert(kennung))
