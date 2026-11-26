"""Keepa API (zugelassener Datenanbieter für Amazon-Preishistorien).

Doku: https://keepa.com/#!discuss/t/product-object/116 und /deal
* Preise in Cent, -1 = kein Angebot.
* Keepa-Zeit = Minuten seit 2011-01-01 → Unix = (keepa + 21564000) * 60
* csv[0] = Amazon-Preis, csv[1] = Neu (Drittanbieter), csv[4] = Listenpreis
"""
from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.config import get_settings
from app.sources.base import DealSource, SourceItem, SourcePrice, map_category

KEEPA_BASE = "https://api.keepa.com"
KEEPA_EPOCH_OFFSET_MIN = 21564000


def keepa_time(minutes: int) -> datetime:
    return datetime.fromtimestamp((minutes + KEEPA_EPOCH_OFFSET_MIN) * 60, tz=UTC)


def parse_csv_series(series: list[int] | None) -> list[SourcePrice]:
    if not series:
        return []
    out = []
    for i in range(0, len(series) - 1, 2):
        t, p = series[i], series[i + 1]
        out.append(SourcePrice(price_cents=max(p, 0), observed_at=keepa_time(t), available=p > 0))
    return out


def parse_product(prod: dict, marketplace: str = "www.amazon.de") -> SourceItem | None:
    csv = prod.get("csv") or []
    amazon = parse_csv_series(csv[0] if len(csv) > 0 else None)
    new3p = parse_csv_series(csv[1] if len(csv) > 1 else None)
    listp = parse_csv_series(csv[4] if len(csv) > 4 else None)
    series = amazon if amazon and amazon[-1].available else new3p
    if not series:
        return None
    cur = series[-1]
    others = []
    if series is amazon and new3p and new3p[-1].available:
        others.append(new3p[-1].price_cents)
    cats = " ".join(str(c.get("name", "")) for c in (prod.get("categoryTree") or []))
    asin = prod["asin"]
    stats = prod.get("stats") or {}
    rating = None
    if prod.get("csv") and len(csv) > 16 and csv[16]:
        rating = csv[16][-1] / 10 if csv[16][-1] > 0 else None
    reviews = csv[17][-1] if len(csv) > 17 and csv[17] else None
    return SourceItem(
        merchant="amazon_de",
        external_id=asin,
        title=prod.get("title") or asin,
        brand=prod.get("brand"),
        product_url=f"https://{marketplace}/dp/{asin}",
        category=map_category(cats, prod.get("productGroup")),
        price_cents=cur.price_cents,
        observed_at=cur.observed_at,
        available=cur.available,
        list_price_cents=listp[-1].price_cents if listp and listp[-1].available else None,
        history=series[:-1],
        other_source_prices=others,
        rating=rating,
        review_count=reviews if reviews and reviews > 0 else None,
        sales_rank=(stats.get("current") or [None] * 4)[3] if isinstance(stats.get("current"), list) else None,
        source="keepa",
    )


class KeepaSource(DealSource):
    name = "keepa"

    def __init__(self, client: httpx.Client | None = None):
        s = get_settings()
        self.key = s.keepa_api_key
        self.domain = s.keepa_domain
        self.marketplace = s.amazon_marketplace
        self.client = client or httpx.Client(base_url=KEEPA_BASE, timeout=30)
        self.tokens_left: int | None = None

    def is_configured(self) -> bool:
        return bool(self.key)

    def _get(self, path: str, params: dict) -> dict:
        r = self.client.get(path, params={"key": self.key, **params})
        r.raise_for_status()
        data = r.json()
        self.tokens_left = data.get("tokensLeft")
        if data.get("error"):
            raise RuntimeError(f"Keepa: {data['error']}")
        return data

    def deal_asins(self, min_drop_pct: int = 30, categories: list[int] | None = None) -> list[str]:
        """Keepa-Deals-Endpunkt: Produkte mit starkem Preissturz (letzte 24h, Amazon + Neu)."""
        import json

        selection = {
            "page": 0,
            "domainId": self.domain,
            "priceTypes": [0],
            "dateRange": 0,  # 24h
            "deltaPercentRange": [min_drop_pct, 100],
            "isRangeEnabled": True,
            "isFilterEnabled": True,
            "filterErotic": True,
            "sortType": 4,  # nach prozentualem Preissturz
        }
        if categories:
            selection["includeCategories"] = categories
        data = self._get("/deal", {"selection": json.dumps(selection)})
        return [d["asin"] for d in (data.get("deals") or {}).get("dr", []) if d.get("asin")]

    def products(self, asins: list[str]) -> list[SourceItem]:
        items: list[SourceItem] = []
        for i in range(0, len(asins), 100):
            chunk = asins[i:i + 100]
            data = self._get("/product", {"domain": self.domain, "asin": ",".join(chunk), "stats": 90,
                                          "history": 1, "rating": 1})
            for p in data.get("products") or []:
                it = parse_product(p, self.marketplace)
                if it:
                    items.append(it)
        return items

    def fetch_candidates(self) -> list[SourceItem]:
        return self.products(self.deal_asins()[:50])

    def fetch_current(self, external_ids: list[str]) -> dict[str, SourceItem]:
        return {it.external_id: it for it in self.products(external_ids)}
