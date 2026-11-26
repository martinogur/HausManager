"""Demo-Daten für lokale Entwicklung. Compliance blockiert jede Veröffentlichung (source=demo)."""
from __future__ import annotations

import random
from datetime import timedelta

from app.domain.timeutil import now
from app.sources.base import DealSource, SourceItem, SourcePrice

DEMO_PRODUCTS = [
    ("B0DEMO0001", "Akku-Bohrschrauber 18V mit 2 Akkus und Koffer", "werkzeug", 12999),
    ("B0DEMO0002", "Kabellose Noise-Cancelling Kopfhörer, 40h Akku", "technik", 19999),
    ("B0DEMO0003", "Heißluftfritteuse 5,5 L mit Sichtfenster", "kueche", 8999),
    ("B0DEMO0004", "Gaming-Maus kabellos, 26.000 DPI", "gaming", 6999),
    ("B0DEMO0005", "Akku-Rasentrimmer 36V", "garten", 14999),
    ("B0DEMO0006", "Babyphone mit Kamera und Nachtsicht", "baby", 9999),
    ("B0DEMO0007", "Kompressor für Autoreifen, digital", "auto", 4999),
    ("B0DEMO0008", "Saugroboter mit Wischfunktion", "haushalt", 29999),
]


class DemoSource(DealSource):
    name = "demo"

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self._last: dict[str, SourceItem] = {}

    def is_configured(self) -> bool:
        return True

    def _item(self, asin, title, cat, base, drop: float) -> SourceItem:
        t = now()
        hist = [SourcePrice(int(base * self.rng.uniform(0.95, 1.05)), t - timedelta(days=d)) for d in range(60, 1, -3)]
        return SourceItem(
            merchant="amazon_de", external_id=asin, title=title, product_url=f"https://www.amazon.de/dp/{asin}",
            category=cat, price_cents=int(base * (1 - drop)), observed_at=t, source="demo", history=hist,
            list_price_cents=int(base * 1.3), rating=4.4, review_count=1200,
        )

    def fetch_candidates(self) -> list[SourceItem]:
        items = [self._item(a, ti, c, b, self.rng.choice([0.12, 0.3, 0.45, 0.7, 0.85])) for a, ti, c, b in DEMO_PRODUCTS]
        self._last = {i.external_id: i for i in items}
        return items

    def fetch_current(self, external_ids: list[str]) -> dict[str, SourceItem]:
        """Simuliert eine stabile Nachprüfung (gleicher Preis, neuer Zeitstempel)."""
        out = {}
        for e in external_ids:
            if e in self._last:
                it = self._last[e]
                it.observed_at = now()
                out[e] = it
        return out
