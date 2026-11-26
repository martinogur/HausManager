from datetime import UTC, datetime, timedelta

from app.domain.scoring import PriceObs, score_price

NOW = datetime(2026, 11, 25, 12, tzinfo=UTC)


def hist(base, days=60, step=2):
    return [PriceObs(base + (i % 3 - 1) * 100, NOW - timedelta(days=d)) for i, d in enumerate(range(days, 1, -step))]


def test_big_drop_needs_two_verifications_for_90():
    r = score_price(2000, hist(10000), NOW, verification_count=0, other_source_prices=[9500])
    assert r.score == 89 and r.label == "Top-Deal"
    r2 = score_price(2000, hist(10000), NOW, verification_count=2, other_source_prices=[9500])
    assert r2.score >= 90 and r2.label == "Preisfehler-Verdacht"
    assert r2.reference_kind == "median_90d" and r2.reference_price_cents == 10000
    assert r2.discount_pct == 80.0


def test_small_discount_not_publishable():
    r = score_price(9300, hist(10000), NOW)
    assert r.score < 50 and not r.publishable


def test_medium_deal():
    r = score_price(5500, hist(10000), NOW, verification_count=1)
    assert 50 <= r.score < 90 and r.publishable


def test_insufficient_history_capped():
    short = [PriceObs(10000, NOW - timedelta(days=d)) for d in (3, 4, 5)]
    r = score_price(1000, short, NOW, verification_count=2)
    assert r.score <= 74 and r.breakdown["capped"] == "insufficient_history"


def test_list_price_only_capped():
    r = score_price(1000, [], NOW, list_price_cents=10000, verification_count=2)
    assert r.score <= 55 and r.reference_kind == "list_price"


def test_recent_drop_excluded_from_reference():
    h = hist(10000) + [PriceObs(2000, NOW - timedelta(hours=2)) for _ in range(20)]
    r = score_price(2000, h, NOW)
    assert r.reference_price_cents == 10000


def test_no_reference():
    assert score_price(1000, [], NOW).score == 0
