"""CSV-Feeds: manuelle Listen oder Produkt-Feeds zugelassener Netzwerke (z.B. Awin-Produktfeed).

Spalten (Header, Groß-/Kleinschreibung egal), Aliase in COLUMN_ALIASES:
merchant, external_id, title, url, price, list_price, category, brand, coupon_code, valid_until
"""
from __future__ import annotations

import csv
import io
from datetime import datetime

from app.domain.timeutil import now
from app.sources.base import DealSource, SourceItem, map_category

COLUMN_ALIASES = {
    "external_id": ["external_id", "asin", "aw_product_id", "sku", "id"],
    "title": ["title", "product_name", "name"],
    "url": ["url", "product_url", "merchant_deep_link", "aw_deep_link", "link"],
    "price": ["price", "search_price", "store_price", "preis"],
    "list_price": ["list_price", "rrp_price", "uvp"],
    "category": ["category", "category_name", "merchant_category", "kategorie"],
    "brand": ["brand", "brand_name", "marke"],
    "merchant": ["merchant", "merchant_name", "haendler"],
    "coupon_code": ["coupon_code", "gutschein"],
    "valid_until": ["valid_until", "gueltig_bis"],
}


def parse_price(v: str | None) -> int | None:
    if v is None or str(v).strip() == "":
        return None
    s = str(v).replace("€", "").replace("EUR", "").strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    return int(round(float(s) * 100))


def parse_feed(text: str, source: str = "feed", default_merchant: str = "amazon_de") -> tuple[list[SourceItem], list[str]]:
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    header = {h.lower().strip(): h for h in (reader.fieldnames or [])}

    def col(row, key):
        for alias in COLUMN_ALIASES[key]:
            if alias in header:
                return row.get(header[alias])
        return None

    items, errors = [], []
    t = now()
    for n, row in enumerate(reader, start=2):
        try:
            ext, title, url, price = col(row, "external_id"), col(row, "title"), col(row, "url"), parse_price(col(row, "price"))
            if not (ext and title and url and price is not None):
                errors.append(f"Zeile {n}: Pflichtfeld fehlt (id/title/url/price)")
                continue
            vu = col(row, "valid_until")
            items.append(SourceItem(
                merchant=(col(row, "merchant") or default_merchant).strip().lower().replace(" ", "_"),
                external_id=ext.strip(), title=title.strip(), product_url=url.strip(),
                category=map_category(col(row, "category"), title),
                price_cents=price, list_price_cents=parse_price(col(row, "list_price")),
                brand=col(row, "brand"), observed_at=t, source=source,
                coupon_code=(col(row, "coupon_code") or None),
                valid_until=datetime.fromisoformat(vu) if vu else None,
            ))
        except (ValueError, TypeError) as e:
            errors.append(f"Zeile {n}: {e}")
    return items, errors


class FeedSource(DealSource):
    """Hält zuletzt importierte Feed-Items (Upload über das Dashboard)."""

    name = "feed"

    def __init__(self, items: list[SourceItem] | None = None):
        self.items = items or []

    def is_configured(self) -> bool:
        return True

    def fetch_candidates(self) -> list[SourceItem]:
        return list(self.items)

    def fetch_current(self, external_ids: list[str]) -> dict[str, SourceItem]:
        return {}  # Feeds liefern keine Live-Preise → Nachprüfung über Keepa oder manuell
