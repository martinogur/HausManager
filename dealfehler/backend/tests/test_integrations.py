"""Protokoll-Tests der Plattform-Clients gegen simulierte HTTP-Antworten (httpx.MockTransport).

Diese Tests prüfen Request-Aufbau und Fehlerbehandlung. Sie ersetzen KEINEN Live-Test mit echten
Zugangsdaten – siehe TASKS.md / docs/SETUP_ACCESS.md.
"""
import json

import httpx

from app.publishers.base import PublishRequest
from app.publishers.instagram import InstagramPublisher
from app.publishers.messaging import TelegramPublisher
from app.publishers.pinterest import BOARDS, PinterestPublisher
from app.sources.feed import parse_feed, parse_price
from app.sources.keepa import KeepaSource, keepa_time, parse_product


def client(handler, base):
    return httpx.Client(transport=httpx.MockTransport(handler), base_url=base)


def test_instagram_publish_flow(monkeypatch):
    monkeypatch.setattr("app.config.get_settings", lambda: None, raising=False)
    calls = []

    def h(req: httpx.Request):
        calls.append((req.method, req.url.path))
        if req.url.path.endswith("/media") and req.method == "POST":
            body = dict(x.split("=", 1) for x in req.content.decode().split("&"))
            assert "image_url" in body and "caption" in body
            return httpx.Response(200, json={"id": "C1"})
        if req.url.path.endswith("/C1"):
            return httpx.Response(200, json={"status_code": "FINISHED"})
        if req.url.path.endswith("/media_publish"):
            return httpx.Response(200, json={"id": "M1"})
        if req.url.path.endswith("/M1"):
            return httpx.Response(200, json={"permalink": "https://instagram.com/p/abc"})
        return httpx.Response(404)

    pub = InstagramPublisher(client=client(h, "https://graph.facebook.com/v23.0"), poll_interval=0)
    pub.user_id, pub.token = "17841", "tok"
    r = pub.publish(PublishRequest(caption="Anzeige …", format="post", media_url="https://cdn.x/p.png"))
    assert r.ok and r.external_id == "M1" and r.external_url.endswith("/abc")
    assert [c[1].split("/")[-1] for c in calls] == ["media", "C1", "media_publish", "M1"]
    # http-URL wird abgelehnt (Instagram lädt Medien selbst herunter)
    assert not pub.publish(PublishRequest(caption="x", format="post", media_url="http://localhost/p.png")).ok


def test_instagram_rate_limit_mapping():
    def h(req):
        return httpx.Response(400, json={"error": {"code": 9, "message": "Application request limit reached"}})

    pub = InstagramPublisher(client=client(h, "https://graph.facebook.com/v23.0"), poll_interval=0)
    pub.user_id, pub.token = "1", "t"
    r = pub.publish(PublishRequest(caption="x", format="post", media_url="https://cdn.x/p.png"))
    assert not r.ok and r.rate_limited


def test_pinterest_boards_and_pin():
    created, pins = [], []

    def h(req):
        if req.url.path == "/v5/boards" and req.method == "GET":
            return httpx.Response(200, json={"items": [{"name": "Technik Deals", "id": "b1"}], "bookmark": None})
        if req.url.path == "/v5/boards" and req.method == "POST":
            created.append(json.loads(req.content)["name"])
            return httpx.Response(201, json={"id": f"b{len(created) + 1}"})
        if req.url.path == "/v5/pins":
            assert req.headers["authorization"] == "Bearer tok"
            pins.append(json.loads(req.content))
            return httpx.Response(201, json={"id": "999"})
        return httpx.Response(404)

    pub = PinterestPublisher(client=client(h, "https://api.pinterest.com/v5"))
    pub.token = "tok"
    r = pub.publish(PublishRequest(caption="Anzeige …", format="pin", media_bytes=b"png", title="T", board="Technik Deals",
                                   link_url="https://dealfehler.de/deals/x"))
    assert r.ok and r.external_id == "999"
    assert len(created) == len(BOARDS) - 1
    assert pins[0]["board_id"] == "b1" and pins[0]["media_source"]["source_type"] == "image_base64"


def test_pinterest_429():
    def h(req):
        if req.url.path == "/v5/boards":
            return httpx.Response(200, json={"items": [{"name": n, "id": n} for n in BOARDS]})
        return httpx.Response(429, headers={"retry-after": "120"})

    pub = PinterestPublisher(client=client(h, "https://api.pinterest.com/v5"))
    pub.token = "t"
    r = pub.publish(PublishRequest(caption="x", format="pin", media_url="https://c/x.png"))
    assert r.rate_limited and r.retry_after_s == 120


def test_telegram_send_photo():
    def h(req):
        assert req.url.path == "/botTOKEN/sendPhoto"
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})

    pub = TelegramPublisher(client=client(h, "https://api.telegram.org"))
    pub.token, pub.chat = "TOKEN", "@dealfehler"
    r = pub.publish(PublishRequest(caption="Anzeige", format="message", media_bytes=b"png"))
    assert r.ok and r.external_url == "https://t.me/dealfehler/42"


def test_keepa_parse_and_client():
    t0 = 7_000_000  # Keepa-Minuten
    prod = {"asin": "B0KEEPA001", "title": "Akkuschrauber", "brand": "X",
            "categoryTree": [{"name": "Baumarkt"}, {"name": "Werkzeug"}],
            "csv": [[t0, 9999, t0 + 1440, 10499, t0 + 2880, 3999], [t0, 9800, t0 + 2880, 9500], None, None,
                    [t0, 14999]]}
    it = parse_product(prod)
    assert it.price_cents == 3999 and it.category == "werkzeug" and len(it.history) == 2
    assert it.other_source_prices == [9500] and it.list_price_cents == 14999
    assert keepa_time(0).year == 2011

    def h(req):
        if req.url.path == "/deal":
            return httpx.Response(200, json={"deals": {"dr": [{"asin": "B0KEEPA001"}]}, "tokensLeft": 50})
        assert req.url.params["domain"] == "3"
        return httpx.Response(200, json={"products": [prod], "tokensLeft": 40})

    src = KeepaSource(client=client(h, "https://api.keepa.com"))
    src.key = "k"
    items = src.fetch_candidates()
    assert items[0].external_id == "B0KEEPA001" and src.tokens_left == 40


def test_feed_parsing():
    csv_text = "asin;title;price;url;category\nB0FEED0001;Heißluftfritteuse 5L;49,99;https://www.amazon.de/dp/B0FEED0001;Küche\n;fehlt;1;x;y\n"
    items, errors = parse_feed(csv_text)
    assert len(items) == 1 and items[0].price_cents == 4999 and items[0].category == "kueche"
    assert len(errors) == 1
    assert parse_price("1.299,00 €") == 129900 and parse_price("12.5") == 1250
