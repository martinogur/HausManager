from datetime import UTC, datetime, timedelta

import pytest

from app.creative import captions as cap
from app.domain import compliance as comp
from app.domain.affiliate import AffiliateError, amazon_link, awin_deeplink, validate_amazon_link

NOW = datetime(2026, 11, 25, 12, tzinfo=UTC)


def ci(**kw):
    base = dict(title="Akku-Bohrschrauber 18V", price_cents=4999, reference_price_cents=9999, discount_pct=50.0,
                label="Top-Deal", category="werkzeug", price_stand="25.11.2026, 13:00 Uhr")
    return cap.CaptionInput(**(base | kw))


def inp(caption, **kw):
    base = dict(platform="instagram", caption=caption, link_url="https://dealfehler.de/deals/x?src=instagram",
                link_valid=True, network="amazon", price_cents=4999, price_checked_at=NOW - timedelta(minutes=5),
                discount_pct=50.0, product_source="keepa", media_license="generated", media_price_cents=4999,
                expected_tag="dealfehler-21")
    return comp.ComplianceInput(**(base | kw))


def test_amazon_link():
    url = amazon_link("b0abc12345", "dealfehler-21")
    assert url == "https://www.amazon.de/dp/B0ABC12345?tag=dealfehler-21"
    assert validate_amazon_link(url, "dealfehler-21") == []
    assert validate_amazon_link("https://amzn.evil.com/dp/B0ABC12345?tag=dealfehler-21")
    with pytest.raises(AffiliateError):
        amazon_link("B0ABC12345", "badtag")
    assert "awinaffid=1&" in awin_deeplink("1", "2", "https://shop.de/p")


def test_generated_captions_pass_compliance():
    text, _ = cap.instagram(ci())
    assert comp.check(inp(text), NOW).passed, comp.check(inp(text), NOW).issues
    title, desc = cap.pinterest(ci())
    assert comp.check(inp(desc, platform="pinterest"), NOW).passed
    msg = cap.short_message(ci(label="Preisfehler-Verdacht"), "https://dealfehler.de/deals/x")
    assert comp.check(inp(msg, platform="telegram", media_license=None, media_price_cents=None), NOW).passed
    web = cap.website_text(ci())
    assert comp.check(inp(web, platform="website", media_license=None, media_price_cents=None), NOW).passed


@pytest.mark.parametrize("mutate,code", [
    (lambda t: t.replace("Anzeige | Affiliate-Link", "Hallo"), "AD_MARKER_MISSING"),
    (lambda t: t + " Preisfehler!", "PRICE_ERROR_UNCONFIRMED"),
    (lambda t: t + " -70 %", "DISCOUNT_OVERSTATED"),
    (lambda t: t + " garantiert", "MISLEADING_PHRASE"),
    (lambda t: t + " nur heute", "UNVERIFIED_URGENCY"),
    (lambda t: t.replace("Stand", "Zeit"), "PRICE_TIMESTAMP_MISSING"),
])
def test_violations(mutate, code):
    text, _ = cap.instagram(ci())
    res = comp.check(inp(mutate(text)), NOW)
    assert not res.passed and code in {i.code for i in res.issues}


def test_stale_price_demo_and_media_mismatch():
    text, _ = cap.instagram(ci())
    codes = lambda **kw: {i.code for i in comp.check(inp(text, **kw), NOW).issues}  # noqa: E731
    assert "PRICE_STALE" in codes(price_checked_at=NOW - timedelta(hours=3))
    assert "DEMO_DATA" in codes(product_source="demo")
    assert "MEDIA_PRICE_MISMATCH" in codes(media_price_cents=5999)
    assert "MEDIA_LICENSE" in codes(media_license="amazon_image")
    assert "PRICE_ERROR_UNCONFIRMED" not in codes()


def test_ai_caption_variant_and_guard(db):
    from app.llm.client import polish_hook

    assert polish_hook(db, {"titel": "x"}) is None  # ohne API-Key: Vorlagentexte
    text, var = cap.instagram(ci(), ai_hook="🔥 Leiser Akkuschrauber für Heimwerker", ai_body="Zwei Akkus, Koffer dabei.")
    assert var == "ai" and text.startswith("Anzeige") and comp.check(inp(text), NOW).passed
