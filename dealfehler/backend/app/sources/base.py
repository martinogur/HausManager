from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SourcePrice:
    price_cents: int
    observed_at: datetime
    available: bool = True


@dataclass
class SourceItem:
    merchant: str
    external_id: str
    title: str
    product_url: str
    category: str
    price_cents: int
    observed_at: datetime
    source: str
    list_price_cents: int | None = None
    brand: str | None = None
    available: bool = True
    history: list[SourcePrice] = field(default_factory=list)
    other_source_prices: list[int] = field(default_factory=list)
    rating: float | None = None
    review_count: int | None = None
    sales_rank: int | None = None
    coupon_code: str | None = None
    deal_hint: str | None = None  # tagesangebot | blitzangebot | gutschein
    valid_until: datetime | None = None


class DealSource:
    name: str = "base"

    def is_configured(self) -> bool:
        return False

    def fetch_candidates(self) -> list[SourceItem]:
        """Neue Deal-Kandidaten (inkl. Historie, soweit verfügbar)."""
        raise NotImplementedError

    def fetch_current(self, external_ids: list[str]) -> dict[str, SourceItem]:
        """Aktueller Preis für die Nachprüfung vor Veröffentlichung."""
        raise NotImplementedError


# Kategorie-Mapping (Keywords → interne Kategorie)
CATEGORY_KEYWORDS = {
    "technik": ["elektronik", "computer", "electronics", "kamera", "foto", "handy", "audio", "tv", "pc"],
    "haushalt": ["haushalt", "home", "wohnen", "staubsauger", "reinigung"],
    "werkzeug": ["werkzeug", "baumarkt", "tools", "diy", "heimwerk"],
    "garten": ["garten", "garden", "outdoor", "terrasse"],
    "kueche": ["küche", "kueche", "kitchen", "kochen", "backen"],
    "gaming": ["games", "gaming", "konsole", "videospiele", "playstation", "xbox", "nintendo"],
    "baby": ["baby", "kinder", "spielzeug", "toys"],
    "auto": ["auto", "motorrad", "automotive", "kfz"],
    "sport": ["sport", "fitness", "freizeit"],
    "drogerie": ["drogerie", "körperpflege", "beauty", "kosmetik", "gesundheit"],
}


def map_category(*texts: str | None) -> str:
    blob = " ".join(t.lower() for t in texts if t)
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(k in blob for k in kws):
            return cat
    return "sonstiges"
