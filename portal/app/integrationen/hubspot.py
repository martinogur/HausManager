"""HubSpot CRM (Private-App-Token, ``HUBSPOT_TOKEN``): neue Anfragen als Deal exportieren.

Endpunkt (verifiziert 25.11.2026): ``POST https://api.hubapi.com/crm/v3/objects/deals`` mit
``properties.dealname``, ``properties.dealstage`` (interne Stage-ID) und ``pipeline``.
Führend für die Vertriebs-Pipeline ist laut Architektur HubSpot; das Portal legt Deals an,
übernimmt aber keine HubSpot-Änderungen zurück, solange kein Webhook eingerichtet ist.
"""

from auftraege.models import Anfrage

from .http import IntegrationFehler, anfrage, env, protokollieren

BASIS = "https://api.hubapi.com"


def eingerichtet() -> bool:
    return bool(env("HUBSPOT_TOKEN"))


def anfrage_exportieren(anfrage_id) -> dict:
    if not eingerichtet():
        return {"hinweis": "HubSpot nicht eingerichtet (HUBSPOT_TOKEN fehlt)"}
    a = Anfrage.objects.select_related("kunde").get(pk=anfrage_id)
    if a.hubspot_deal_id:
        return {"hinweis": "bereits exportiert", "deal": a.hubspot_deal_id}
    daten = {"properties": {
        "dealname": f"{a.anfragenummer} {a.kunde.name if a.kunde else (a.betreff or 'Anfrage')}"[:250],
        "pipeline": env("HUBSPOT_PIPELINE") or "default",
        "dealstage": env("HUBSPOT_DEALSTAGE_NEU") or "appointmentscheduled",
        "description": (a.ki_zusammenfassung or "")[:5000],
    }}
    schluessel = f"hubspot:deal:{a.id}"
    try:
        status, antwort = anfrage("POST", f"{BASIS}/crm/v3/objects/deals", env("HUBSPOT_TOKEN"), daten)
    except IntegrationFehler as e:
        protokollieren("hubspot", "export", "deal", lokale_id=a.id, erfolgreich=False, fehler=str(e))
        raise
    a.hubspot_deal_id = str(antwort["id"])
    a.save(update_fields=["hubspot_deal_id"])
    protokollieren("hubspot", "export", "deal", lokale_id=a.id, externe_id=a.hubspot_deal_id, schluessel=schluessel,
                   erfolgreich=True, http_status=status)
    return {"deal": a.hubspot_deal_id}
