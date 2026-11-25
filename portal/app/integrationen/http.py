"""Gemeinsame HTTP-Hilfe für Integrationen (nur Standardbibliothek) mit Protokoll in ``sync_protokoll``.

Zugangsdaten kommen ausschließlich aus Umgebungsvariablen (SOPS → Container). Fehlt ein Token,
gilt die Integration als „nicht eingerichtet“ – das ist kein Fehler, die Automatisierung meldet es nur.
"""

import json
import os
import urllib.error
import urllib.request

from .models import SyncProtokoll


class IntegrationFehler(Exception):
    pass


def env(name: str) -> str | None:
    wert = os.environ.get(name, "").strip()
    return wert or None


def anfrage(methode: str, url: str, token: str, daten: dict | None = None, timeout: float = 20) -> tuple[int, dict]:
    body = json.dumps(daten).encode() if daten is not None else None
    req = urllib.request.Request(url, data=body, method=methode, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/json",
        **({"Content-Type": "application/json"} if body else {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as antwort:
            text = antwort.read().decode() or "{}"
            return antwort.status, json.loads(text)
    except urllib.error.HTTPError as e:
        inhalt = e.read().decode(errors="replace")[:1000]
        raise IntegrationFehler(f"HTTP {e.code}: {inhalt}") from e
    except urllib.error.URLError as e:
        raise IntegrationFehler(f"Verbindung fehlgeschlagen: {e.reason}") from e


def protokollieren(system: str, richtung: str, objekt_typ: str, *, lokale_id=None, externe_id=None,
                   schluessel=None, erfolgreich: bool, http_status=None, fehler=None) -> None:
    SyncProtokoll.objects.create(system=system, richtung=richtung, objekt_typ=objekt_typ, lokale_id=lokale_id,
                                 externe_id=externe_id, idempotenz_schluessel=schluessel, erfolgreich=erfolgreich,
                                 http_status=http_status, fehler=fehler)
