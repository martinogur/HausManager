import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agents.base import run_agent
from app.agents.master import run_cycle
from app.agents.publishing import PublisherAgent
from app.main import create_app
from app.models import Click, Deal, PlatformState, Publication, Role, User
from app.models import PublicationStatus as PS
from app.security import hash_password


@pytest.fixture
def api(db):
    for email, role in [("admin@df.de", Role.ADMIN), ("editor@df.de", Role.EDITOR), ("viewer@df.de", Role.VIEWER)]:
        db.add(User(email=email, password_hash=hash_password("passwort1234"), role=role))
    db.commit()
    with TestClient(create_app()) as c:
        yield c


def tok(api, email):
    r = api.post("/api/auth/login", json={"email": email, "password": "passwort1234"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_auth_and_roles(api):
    assert api.get("/api/deals").status_code == 401
    assert api.post("/api/auth/login", json={"email": "admin@df.de", "password": "falsch"}).status_code == 401
    v, e, a = tok(api, "viewer@df.de"), tok(api, "editor@df.de"), tok(api, "admin@df.de")
    assert api.get("/api/deals", headers=v).status_code == 200
    assert api.post("/api/platforms/instagram/kill", headers=v).status_code == 403
    assert api.post("/api/platforms/instagram/kill", headers=e).json()["kill_switch"] is True
    assert api.post("/api/platforms/instagram/resume", headers=e).status_code == 403
    assert api.post("/api/platforms/instagram/resume", headers=a).json()["kill_switch"] is False
    assert api.get("/api/users", headers=e).status_code == 403
    assert len(api.get("/api/users", headers=a).json()) == 3
    r = api.post("/api/system/kill-switch", json={"active": True}, headers=e)
    assert r.json()["global_kill_switch"] is True
    assert api.post("/api/system/kill-switch", json={"active": False}, headers=e).status_code == 403
    assert api.get("/api/dashboard/overview", headers=v).json()["global_kill_switch"] is True


def test_platform_patch_validation(api):
    a = tok(api, "admin@df.de")
    r = api.patch("/api/platforms/telegram", json={"daily_limit": 50, "daily_limit_max": 20}, headers=a)
    assert r.status_code == 200 and r.json()["daily_limit"] == 20
    assert api.patch("/api/platforms/telegram", json={"min_score": 10}, headers=a).status_code == 422


def test_feed_import_manual_confirm_and_public_site(api, db, clock, publishers):
    from app.agents.base import AgentContext

    e, a = tok(api, "editor@df.de"), tok(api, "admin@df.de")
    csv_text = "asin,title,price,url,category\nB0FEED0001,Heißluftfritteuse 5 L,49.99,https://www.amazon.de/dp/B0FEED0001,Küche\n"
    r = api.post("/api/products/import", files={"file": ("f.csv", io.BytesIO(csv_text.encode()), "text/csv")}, headers=e)
    assert r.json()["deals_created"] == 1
    deal = db.scalar(select(Deal))
    # Historie ergänzen, damit der Score belastbar ist
    from datetime import timedelta

    from app.models import PricePoint

    for d in range(4, 40, 3):
        db.add(PricePoint(product_id=deal.product_id, price_cents=9999, source="feed", observed_at=clock() - timedelta(days=d)))
    db.commit()
    ctx = AgentContext(sources={}, publisher_factory=lambda p: publishers[p], clock=clock)
    run_cycle(db, ctx)
    db.refresh(deal)
    assert deal.status.value == "in_pruefung"  # Feed ohne Live-Preis → wartet auf manuelle Bestätigung
    r = api.post(f"/api/deals/{deal.id}/confirm-price", json={"price": "49,99"}, headers=e)
    assert r.json()["outcome"] == "verified", r.json()
    # Preisbestätigung erfolgt mit Echtzeit – Agenten-Uhr angleichen
    from app.domain.timeutil import now

    clock.t = now()
    run_cycle(db, ctx)
    run_agent(db, PublisherAgent(), ctx)
    web = db.scalar(select(Publication).where(Publication.platform == "website"))
    assert web.status == PS.PUBLISHED, web.last_error

    lst = api.get("/api/public/deals").json()
    assert lst["total"] == 1 and "Amazon-Partner" in lst["disclosure"]
    slug = lst["items"][0]["slug"]
    detail = api.get(f"/api/public/deals/{slug}?src=instagram").json()
    assert detail["affiliate_url"].endswith("tag=dealfehler-ig-21")
    assert detail["price_history"] and "Median" in detail["reference_explanation"]
    assert api.post("/api/public/click", json={"slug": slug, "src": "instagram"}).status_code == 204
    assert api.post("/api/public/click", json={"slug": slug, "src": "instagram"}).status_code == 204  # Dublette
    assert len(db.scalars(select(Click)).all()) == 1
    assert api.get("/api/stats/clicks", headers=a).json()["by_channel"] == {"instagram": 1}
    assert api.get("/api/public/sitemap").json()[0]["slug"] == slug

    # Detail + Audit + Übersicht
    d = api.get(f"/api/deals/{deal.id}", headers=e).json()
    assert d["events"] and d["links"] and d["media"]
    ov = api.get("/api/dashboard/overview?days=7", headers=e).json()
    assert ov["clicks"] == 1 and len(ov["series"]) == 7
    assert any(x["action"] == "deal.confirm_price" for x in api.get("/api/audit", headers=a).json())
    # Editor darf keinen Preisfehler bestätigen
    assert api.patch(f"/api/deals/{deal.id}", json={"confirmed_price_error": True}, headers=e).status_code == 403


def test_commission_import_and_revenue(api, db):
    e = tok(api, "editor@df.de")
    csv_text = "id;asin;date;revenue;commission;status\nA1;B0X0000001;2026-11-20;99,00;6,93;confirmed\nA2;;2026-11-21;10;0,70;\n"
    r = api.post("/api/commissions/import", files={"file": ("c.csv", io.BytesIO(csv_text.encode()), "text/csv")}, headers=e)
    assert r.json()["added"] == 2
    again = api.post("/api/commissions/import", files={"file": ("c.csv", io.BytesIO(csv_text.encode()), "text/csv")},
                     headers=e)
    assert again.json()["added"] == 0
    rows = api.get("/api/stats/revenue?days=3650", headers=e).json()["rows"]
    assert {r["status"]: r["commission_cents"] for r in rows} == {"confirmed": 693, "estimated": 70}


def test_agents_connections_health(api, db):
    a = tok(api, "admin@df.de")
    names = {x["name"] for x in api.get("/api/agents", headers=a).json()}
    assert {"master", "deal_hunter", "price_checker", "affiliate", "creative", "compliance", "scheduler",
            "publisher", "price_watch", "growth"} <= names
    assert api.patch("/api/agents/growth", json={"enabled": False}, headers=a).json()["enabled"] is False
    r = api.post("/api/agents/growth/run", headers=a).json()
    assert r["status"] == "skipped"
    con = api.get("/api/connections", headers=a).json()
    amazon = next(i for i in con["items"] if i["key"] == "amazon")
    assert amazon["configured"] and "secret" not in str(con).lower()
    assert api.get("/healthz").json()["db"] is True
    assert "dealfehler_dry_run" in api.get("/metrics").text
    db.get(PlatformState, "website")


def test_channel_kit(api, monkeypatch):
    from app.config import get_settings

    v = tok(api, "viewer@df.de")
    kit = api.get("/api/channel-kit/whatsapp", headers=v).json()
    assert "Anzeige" in kit["description"] or "Affiliate" in kit["description"]
    assert api.get("/api/channel-kit/profile.png").content[:4] == b"\x89PNG"
    assert api.get("/api/channel-kit/whatsapp/qr.png").status_code == 404
    monkeypatch.setattr(get_settings(), "whatsapp_channel_invite_url", "https://whatsapp.com/channel/TEST")
    assert api.get("/api/channel-kit/whatsapp/qr.png").content[:4] == b"\x89PNG"
