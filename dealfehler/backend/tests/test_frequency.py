from datetime import timedelta

from app.domain import frequency as freq
from app.domain.settings_store import set_value
from app.models import Deal, PlatformState, Product, Publication
from app.models import PublicationStatus as PS


def _published(db, platform, t, n=1):
    ext = f"B0T{int(t.timestamp()) % 10**7:07d}"
    p = Product(merchant="amazon_de", external_id=ext, title="x", product_url=f"https://www.amazon.de/dp/{ext}",
                source="fake")
    db.add(p)
    db.flush()
    d = Deal(product_id=p.id, slug=f"x-{t.timestamp()}", current_price_cents=100, fingerprint="f")
    db.add(d)
    db.flush()
    for i in range(n):
        db.add(Publication(deal_id=d.id, platform=platform, caption="c", status=PS.PUBLISHED, published_at=t,
                           price_cents_at_creation=100, content_hash=f"h{i}{t.timestamp()}"))
    db.flush()


def test_disabled_kill_and_global(db, clock):
    t = clock()
    assert not freq.can_publish(db, "instagram", t).allowed  # Standard: deaktiviert
    st = db.get(PlatformState, "instagram")
    st.enabled = True
    assert freq.can_publish(db, "instagram", t).allowed
    st.kill_switch = True
    assert "Not-Aus" in freq.can_publish(db, "instagram", t).reason
    st.kill_switch = False
    set_value(db, "global_kill_switch", True)
    assert "Globaler" in freq.can_publish(db, "instagram", t).reason


def test_limits_interval_quiet(db, clock):
    t = clock()
    st = db.get(PlatformState, "telegram")
    st.enabled, st.daily_limit, st.min_interval_minutes = True, 2, 60
    _published(db, "telegram", t - timedelta(minutes=10))
    dec = freq.can_publish(db, "telegram", t)
    assert not dec.allowed and dec.next_possible_at == t + timedelta(minutes=50)
    _published(db, "telegram", t - timedelta(hours=3))
    assert "Tageslimit" in freq.can_publish(db, "telegram", t + timedelta(hours=2)).reason
    st.daily_limit = 10
    night = t.replace(hour=23)  # 00:00 Berlin
    assert freq.can_publish(db, "telegram", night).reason == "Ruhezeit"
    slot = freq.next_slot(db, "telegram", night)
    assert freq.local(slot).hour >= 7


def test_auto_pause_and_ramp(db, clock):
    t = clock()
    st = db.get(PlatformState, "pinterest")
    st.enabled = True
    for _ in range(3):
        freq.register_error(db, "pinterest", "500", t)
    assert st.paused_until is not None and not freq.can_publish(db, "pinterest", t).allowed
    freq.register_error(db, "pinterest", "429", t, rate_limited=True, retry_after_s=60)
    assert st.paused_until == t + timedelta(seconds=60)
    before = st.daily_limit
    assert freq.maybe_ramp_up(db, st, t, error_rate=0, engagement_ok=True)
    assert st.daily_limit == before + st.ramp_step
    assert not freq.maybe_ramp_up(db, st, t + timedelta(days=1), error_rate=0, engagement_ok=True)
    assert not freq.maybe_ramp_up(db, st, t + timedelta(days=8), error_rate=0.1, engagement_ok=True)
