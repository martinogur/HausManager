"""End-to-End: Agenten arbeiten über die gemeinsame Deal-Datenbank zusammen."""
from pathlib import Path

from sqlalchemy import select

from app.agents.base import run_agent
from app.agents.growth import GrowthAgent
from app.agents.master import run_cycle
from app.agents.publishing import PriceWatchAgent, PublisherAgent, mark_manual_published
from app.config import get_settings
from app.domain.settings_store import set_value
from app.models import (
    AgentRun,
    Click,
    ComplianceCheck,
    Deal,
    MediaAsset,
    PlatformState,
    Publication,
    Report,
)
from app.models import (
    DealStatus as S,
)
from app.models import (
    PublicationStatus as PS,
)


def enable(db, *names):
    for n in names:
        db.get(PlatformState, n).enabled = True
    db.commit()


def _setup(db, source):
    source.add("B0AAAAAAA1", "Noise-Cancelling Kopfhörer Over-Ear", 10000, 2000)
    source.add("B0AAAAAAA2", "Gaming-Maus kabellos", 5000, 4800, category="gaming")
    enable(db, "instagram", "pinterest", "telegram", "whatsapp")


def _to_scheduled(db, ctx, clock):
    run_cycle(db, ctx)
    clock.advance(minutes=11)  # zweite unabhängige Preisprüfung erst nach Mindestabstand
    run_cycle(db, ctx)


def test_full_pipeline(db, ctx, source, clock, publishers):
    _setup(db, source)
    r1 = run_cycle(db, ctx)
    assert r1["status"] == "ok"
    deals = {d.product.external_id: d for d in db.scalars(select(Deal))}
    assert deals["B0AAAAAAA2"].status == S.REJECTED
    top = deals["B0AAAAAAA1"]
    assert top.status == S.IN_REVIEW and top.verification_count == 1 and top.score == 89

    clock.advance(minutes=11)
    run_cycle(db, ctx)
    db.refresh(top)
    assert top.verification_count == 2 and top.score >= 90
    assert top.deal_type.value == "preisfehler_verdacht"
    assert top.status == S.SCHEDULED
    # Links: default + Kanal-Tracking-ID
    assert {lk.channel: lk.tracking_id for lk in top.links} == {"default": "dealfehler-21", "instagram": "dealfehler-ig-21"}
    # Medien wirklich erzeugt
    media = db.scalars(select(MediaAsset).where(MediaAsset.deal_id == top.id)).all()
    assert len(media) == 3
    for m in media:
        assert (Path(get_settings().media_dir) / m.storage_key).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    pubs = {p.platform.value: p for p in top.publications}
    assert set(pubs) == {"instagram", "pinterest", "telegram", "whatsapp", "website"}
    assert pubs["whatsapp"].status == PS.PENDING_APPROVAL
    assert all(p.status == PS.SCHEDULED for k, p in pubs.items() if k != "whatsapp")
    assert db.scalar(select(ComplianceCheck).where(ComplianceCheck.passed.is_(False))) is None
    assert "Preisfehler-Verdacht" in pubs["instagram"].caption and pubs["instagram"].caption.startswith("Anzeige")

    run_agent(db, PublisherAgent(), ctx)
    for k in ("instagram", "pinterest", "telegram", "website"):
        db.refresh(pubs[k])
        assert pubs[k].status == PS.PUBLISHED, (k, pubs[k].last_error)
    assert len(publishers["instagram"].requests) == 1
    assert publishers["pinterest"].requests[0].board == "Amazon Preisfehler-Verdacht"
    db.refresh(top)
    assert top.status == S.PUBLISHED

    # WhatsApp: manuelle Veröffentlichung
    mark_manual_published(db, pubs["whatsapp"], clock(), "editor@test")
    db.commit()
    assert pubs["whatsapp"].status == PS.PUBLISHED

    # Kein doppelter Beitrag bei weiteren Zyklen
    run_cycle(db, ctx)
    run_agent(db, PublisherAgent(), ctx)
    assert len(publishers["instagram"].requests) == 1
    assert db.scalar(select(Report).where(Report.kind == "daily")) is not None


def test_price_change_pauses_scheduled_posts(db, ctx, source, clock, publishers):
    _setup(db, source)
    db.get(PlatformState, "telegram").min_interval_minutes = 600
    db.commit()
    _to_scheduled(db, ctx, clock)
    run_agent(db, PublisherAgent(), ctx)
    # zweiter Deal für denselben Kanal würde warten – wir ändern jetzt den Preis
    source.current["B0AAAAAAA1"] = 3500
    clock.advance(minutes=31)
    run = run_agent(db, PriceWatchAgent(), ctx)
    assert run.stats["changed"] == 1
    d = db.scalar(select(Deal).where(Deal.slug.like("noise%")))
    assert d.status == S.PRICE_CHANGED
    assert all(p.status != PS.SCHEDULED for p in d.publications)


def test_recheck_before_publish_detects_change(db, ctx, source, clock, publishers):
    _setup(db, source)
    _to_scheduled(db, ctx, clock)
    clock.advance(minutes=61)  # Preisprüfung zu alt → Publisher prüft erneut
    source.current["B0AAAAAAA1"] = 4000
    run_agent(db, PublisherAgent(), ctx)
    assert publishers["instagram"].requests == []
    d = db.scalar(select(Deal).where(Deal.slug.like("noise%")))
    assert d.status == S.PRICE_CHANGED


def test_expired_offer_cancels(db, ctx, source, clock, publishers):
    _setup(db, source)
    _to_scheduled(db, ctx, clock)
    source.current["B0AAAAAAA1"] = None
    clock.advance(minutes=31)
    run_agent(db, PriceWatchAgent(), ctx)
    d = db.scalar(select(Deal).where(Deal.slug.like("noise%")))
    assert d.status == S.EXPIRED
    assert {p.status for p in d.publications if p.platform.value != "website"} <= {PS.CANCELLED}


def test_kill_switches_block_publishing(db, ctx, source, clock, publishers):
    _setup(db, source)
    _to_scheduled(db, ctx, clock)
    db.get(PlatformState, "instagram").kill_switch = True
    db.commit()
    run_agent(db, PublisherAgent(), ctx)
    assert publishers["instagram"].requests == [] and len(publishers["telegram"].requests) == 1
    # globaler Not-Aus stoppt auch den Master-Zyklus
    set_value(db, "global_kill_switch", True)
    db.commit()
    assert run_cycle(db, ctx)["skipped"]
    source.add("B0AAAAAAA3", "Neues Produkt", 10000, 1000)
    run_agent(db, PublisherAgent(), ctx)
    assert len(publishers["pinterest"].requests) == 1


def test_api_errors_pause_platform(db, ctx, source, clock, publishers):
    _setup(db, source)
    publishers["telegram"].behaviour = "error"
    _to_scheduled(db, ctx, clock)
    for _ in range(3):
        run_agent(db, PublisherAgent(), ctx)
        clock.advance(minutes=46)
        # Preis frisch halten, damit nur der API-Fehler zählt
        d = db.scalar(select(Deal).where(Deal.slug.like("noise%")))
        d.price_checked_at = clock()
        db.commit()
    st = db.get(PlatformState, "telegram")
    assert st.paused_until is not None and st.consecutive_errors >= 3
    p = db.scalar(select(Publication).where(Publication.platform == "telegram"))
    assert p.status == PS.FAILED and p.attempts == 3


def test_rate_limit_pauses(db, ctx, source, clock, publishers):
    _setup(db, source)
    publishers["pinterest"].behaviour = "ratelimit"
    _to_scheduled(db, ctx, clock)
    run_agent(db, PublisherAgent(), ctx)
    st = db.get(PlatformState, "pinterest")
    assert st.pause_reason.startswith("Rate-Limit")


def test_demo_data_never_published(db, clock, publishers):
    from app.agents.base import AgentContext
    from app.sources.demo import DemoSource

    set_value(db, "demo_mode", True)
    enable(db, "telegram")
    ctx = AgentContext(sources={"demo": DemoSource(seed=1)}, publisher_factory=lambda p: publishers[p], clock=clock)
    run_cycle(db, ctx)
    clock.advance(minutes=11)
    run_cycle(db, ctx)
    run_agent(db, PublisherAgent(), ctx)
    assert publishers["telegram"].requests == []
    failed = db.scalars(select(Publication).where(Publication.status == PS.FAILED)).all()
    assert failed and all("Demo" in p.last_error for p in failed)


def test_failing_agent_is_isolated(db, ctx, source, clock, monkeypatch):
    from app.agents import pipeline

    _setup(db, source)

    def boom(self, db, ctx):
        raise RuntimeError("kaputt")

    monkeypatch.setattr(pipeline.AffiliateAgent, "run", boom)
    res = run_cycle(db, ctx)
    assert res["affiliate"]["status"] == "error" and res["creative"]["status"] == "ok"
    assert db.scalar(select(AgentRun).where(AgentRun.agent == "affiliate", AgentRun.status == "error"))


def test_growth_learns_from_clicks(db, ctx, source, clock):
    _setup(db, source)
    _to_scheduled(db, ctx, clock)
    run_agent(db, PublisherAgent(), ctx)
    d = db.scalar(select(Deal).where(Deal.slug.like("noise%")))
    lk = d.links[0]
    for _ in range(5):
        db.add(Click(link_id=lk.id, deal_id=d.id, channel="instagram", created_at=clock()))
    from app.models import Commission

    db.add(Commission(network="amazon", external_ref="o1", deal_id=d.id, commission_cents=150, status="confirmed",
                      occurred_at=clock()))
    db.commit()
    run = run_agent(db, GrowthAgent(), ctx)
    assert run.status == "ok" and run.stats["clicks"] == 5
    rep = db.scalar(select(Report).where(Report.kind == "growth"))
    assert rep.content["clicks_by_channel"] == {"instagram": 5}
    assert any("zu wenige" in s for s in rep.content["suggestions"])
    assert rep.content["commission_by_category"]["technik"]["confirmed_cents"] == 150
