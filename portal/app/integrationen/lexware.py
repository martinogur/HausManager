"""Lexware Office Public API (``LEXWARE_API_KEY``; laut firma/profil.md erst ab Tarif XL verfügbar).

Verifiziert am 25.11.2026 (developers.lexware.io): Basis ``https://api.lexware.io``,
``Authorization: Bearer``, max. 2 Anfragen/s (429 → später erneut). ``POST /v1/invoices`` legt
standardmäßig einen **Entwurf** an (``?finalize=true`` würde festschreiben – nutzen wir nie).
Pflichtfelder: voucherDate, address (name + countryCode), lineItems (custom: name, quantity,
unitName, unitPrice{currency, netAmount, taxRatePercentage}), totalPrice{currency},
taxConditions{taxType}, shippingConditions{shippingType, shippingDate}.
Status lesen: ``GET /v1/invoices/{id}`` → voucherStatus draft | open | paid | voided.
"""

from django.utils import timezone

from auftraege.models import Rechnung

from .http import IntegrationFehler, anfrage, env, protokollieren

BASIS = "https://api.lexware.io"
STATUS = {"draft": "entwurf", "open": "offen", "paid": "bezahlt", "voided": "storniert"}


def eingerichtet() -> bool:
    return bool(env("LEXWARE_API_KEY"))


def rechnungsdaten(r: Rechnung) -> dict:
    heute = timezone.localdate().isoformat()
    titel = r.auftrag.titel if r.auftrag_id else "Hausmeisterleistungen"
    netto = round(r.summe_netto_cent / 100, 2)
    steuer = round((r.summe_brutto_cent - r.summe_netto_cent) * 100 / r.summe_netto_cent) if r.summe_netto_cent else 19
    return {
        "voucherDate": f"{heute}T00:00:00.000+01:00",
        "address": {"name": r.kunde.name, "street": r.kunde.strasse or "", "zip": r.kunde.plz or "",
                    "city": r.kunde.ort or "", "countryCode": "DE"},
        "lineItems": [{"type": "custom", "name": titel[:255], "quantity": 1, "unitName": "Pauschale",
                       "unitPrice": {"currency": "EUR", "netAmount": netto, "taxRatePercentage": steuer}}],
        "totalPrice": {"currency": "EUR"},
        "taxConditions": {"taxType": "net"},
        "shippingConditions": {"shippingType": "service", "shippingDate": f"{heute}T00:00:00.000+01:00"},
        "title": "Rechnung",
        "introduction": f"Leistungen laut Auftrag {r.auftrag.auftragsnummer}" if r.auftrag_id else "",
    }


def entwurf_anlegen(rechnung_id) -> dict:
    if not eingerichtet():
        return {"hinweis": "Lexware nicht eingerichtet – Rechnung bitte in Lexware Office von Hand anlegen"}
    r = Rechnung.objects.select_related("kunde", "auftrag").get(pk=rechnung_id)
    if r.lexware_invoice_id:
        return {"hinweis": "bereits übertragen"}
    try:
        status, antwort = anfrage("POST", f"{BASIS}/v1/invoices", env("LEXWARE_API_KEY"), rechnungsdaten(r))
    except IntegrationFehler as e:
        protokollieren("lexware", "export", "invoice", lokale_id=r.id, erfolgreich=False, fehler=str(e))
        raise
    r.lexware_invoice_id = antwort["id"]
    r.save(update_fields=["lexware_invoice_id"])
    protokollieren("lexware", "export", "invoice", lokale_id=r.id, externe_id=antwort["id"],
                   schluessel=f"lexware:invoice:{r.id}", erfolgreich=True, http_status=status)
    return {"lexware_id": antwort["id"]}


def status_abgleichen() -> dict:
    """Status übertragener Rechnungen aus Lexware übernehmen (Lexware ist führend)."""
    if not eingerichtet():
        return {"hinweis": "Lexware nicht eingerichtet"}
    geaendert = 0
    for r in Rechnung.objects.filter(lexware_invoice_id__isnull=False).exclude(status__in=["bezahlt", "storniert"])[:50]:
        _, antwort = anfrage("GET", f"{BASIS}/v1/invoices/{r.lexware_invoice_id}", env("LEXWARE_API_KEY"))
        neu = STATUS.get(antwort.get("voucherStatus"))
        if neu and neu != r.status and not (r.status == "ueberfaellig" and neu == "offen"):
            r.status = neu
            if neu == "bezahlt" and not r.bezahlt_am:
                r.bezahlt_am = timezone.localdate()
            if antwort.get("voucherNumber"):
                r.rechnungsnummer = antwort["voucherNumber"]
            r.save()
            geaendert += 1
        protokollieren("lexware", "import", "invoice_status", lokale_id=r.id, externe_id=str(r.lexware_invoice_id),
                       erfolgreich=True, http_status=200)
    return {"geaendert": geaendert}
