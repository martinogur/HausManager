import os
import tempfile
from datetime import UTC, datetime, timedelta

_media = tempfile.mkdtemp(prefix="df-media-")
os.environ.update({
    "APP_ENV": "test",
    "DATABASE_URL": os.environ.get("TEST_DATABASE_URL",
                                   "postgresql+psycopg://dealfehler:dealfehler@localhost:5432/dealfehler_test"),
    "MEDIA_DIR": _media,
    "AMAZON_PARTNER_TAG": "dealfehler-21",
    "AMAZON_CHANNEL_TRACKING_IDS": "instagram=dealfehler-ig-21",
    "SECRET_KEY": "test-secret-key-0123456789-abcdefghij",
    "DRY_RUN": "false",
    "TIMEZONE": "Europe/Berlin",
    "KEEPA_API_KEY": "",
    "ANTHROPIC_API_KEY": "",
    "BOOTSTRAP_ADMIN_EMAIL": "",
    "BOOTSTRAP_ADMIN_PASSWORD": "",
    "TELEGRAM_BOT_TOKEN": "",
    "INSTAGRAM_ACCESS_TOKEN": "",
    "PINTEREST_ACCESS_TOKEN": "",
    "WHATSAPP_CHANNEL_INVITE_URL": "",
    "STORAGE_BACKEND": "local",
})

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.agents.base import AgentContext  # noqa: E402
from app.db import Base, SessionLocal, get_engine  # noqa: E402
from app.domain.frequency import ensure_platform_states  # noqa: E402
from app.publishers.base import Publisher, PublishResult  # noqa: E402
from app.sources.base import DealSource, SourceItem, SourcePrice  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    eng = get_engine()
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield


@pytest.fixture
def db():
    eng = get_engine()
    with eng.begin() as c:
        names = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
        if eng.dialect.name == "postgresql":
            c.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
        else:
            for t in reversed(Base.metadata.sorted_tables):
                c.execute(t.delete())
    s = SessionLocal()
    ensure_platform_states(s)
    s.commit()
    yield s
    s.close()


class Clock:
    def __init__(self, t: datetime):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, **kw):
        self.t += timedelta(**kw)


class FakeSource(DealSource):
    """Steuerbare Datenquelle: Kandidaten mit Historie + aktuelle Preise für Nachprüfungen."""

    name = "fake"

    def __init__(self, clock: Clock):
        self.clock = clock
        self.products: dict[str, dict] = {}
        self.current: dict[str, int | None] = {}
        self.calls = 0

    def add(self, asin, title, base_cents, now_cents, category="technik", days=60):
        self.products[asin] = dict(title=title, base=base_cents, category=category, days=days)
        self.current[asin] = now_cents

    def is_configured(self):
        return True

    def _item(self, asin) -> SourceItem | None:
        p, cur = self.products[asin], self.current[asin]
        t = self.clock()
        hist = [SourcePrice(p["base"] + (i % 3 - 1) * 100, t - timedelta(days=d)) for i, d in enumerate(range(p["days"], 1, -2))]
        return SourceItem(merchant="amazon_de", external_id=asin, title=p["title"], category=p["category"],
                          product_url=f"https://www.amazon.de/dp/{asin}", price_cents=cur or 0, observed_at=t,
                          available=cur is not None, source="fake", history=hist, rating=4.5, review_count=900,
                          other_source_prices=[p["base"] - 500])

    def fetch_candidates(self):
        return [i for a in self.products if (i := self._item(a))]

    def fetch_current(self, ids):
        self.calls += 1
        return {a: self._item(a) for a in ids if a in self.products}


class FakePublisher(Publisher):
    def __init__(self, platform, behaviour="ok"):
        self.platform = platform
        self.behaviour = behaviour
        self.requests = []

    def is_configured(self):
        return True

    def publish(self, req):
        self.requests.append(req)
        if self.platform == "whatsapp":
            return PublishResult(False, manual=True, retryable=False)
        if self.behaviour == "error":
            return PublishResult(False, error="HTTP 500: boom", retryable=True)
        if self.behaviour == "ratelimit":
            return PublishResult(False, error="rate", rate_limited=True, retry_after_s=1800)
        return PublishResult(True, external_id=f"{self.platform}-{len(self.requests)}", external_url="https://x.test/p")


@pytest.fixture
def clock():
    # Mittwoch 12:00 Berlin = 11:00 UTC (außerhalb der Ruhezeiten)
    return Clock(datetime(2026, 11, 25, 11, 0, tzinfo=UTC))


@pytest.fixture
def source(clock):
    return FakeSource(clock)


@pytest.fixture
def publishers():
    return {p: FakePublisher(p) for p in ("instagram", "pinterest", "telegram", "whatsapp", "website", "newsletter")}


@pytest.fixture
def ctx(source, clock, publishers):
    return AgentContext(sources={"fake": source}, publisher_factory=lambda p: publishers[p], clock=clock)
