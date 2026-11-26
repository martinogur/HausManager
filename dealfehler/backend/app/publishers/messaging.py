"""Telegram (offizielle Bot API) und WhatsApp-Kanal (manuelle Freigabe).

WhatsApp-Kanäle haben derzeit keine offiziell freigegebene Veröffentlichungs-API für Dritte.
Deshalb: Der Agent bereitet Text + Bild vor, die Veröffentlichung erfolgt per Klick im Dashboard
("Kopieren & in WhatsApp posten" → "Als veröffentlicht markieren"). Keine WhatsApp-Web-Bots.
"""
from __future__ import annotations

import httpx

from app.config import get_settings
from app.publishers.base import Publisher, PublishRequest, PublishResult


class TelegramPublisher(Publisher):
    platform = "telegram"

    def __init__(self, client: httpx.Client | None = None):
        s = get_settings()
        self.token = s.telegram_bot_token
        self.chat = s.telegram_channel_id
        self.client = client or httpx.Client(base_url="https://api.telegram.org", timeout=30)

    def is_configured(self) -> bool:
        return bool(self.token and self.chat)

    def publish(self, req: PublishRequest) -> PublishResult:
        path = f"/bot{self.token}/sendPhoto" if req.media_bytes or req.media_url else f"/bot{self.token}/sendMessage"
        if req.media_bytes:
            r = self.client.post(path, data={"chat_id": self.chat, "caption": req.caption[:1024], "parse_mode": "Markdown"},
                                 files={"photo": ("deal.png", req.media_bytes, req.media_content_type or "image/png")})
        elif req.media_url:
            r = self.client.post(path, json={"chat_id": self.chat, "photo": req.media_url,
                                             "caption": req.caption[:1024], "parse_mode": "Markdown"})
        else:
            r = self.client.post(path, json={"chat_id": self.chat, "text": req.caption, "parse_mode": "Markdown"})
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code == 429:
            ra = (data.get("parameters") or {}).get("retry_after", 60)
            return PublishResult(False, error="Telegram Rate-Limit", rate_limited=True, retry_after_s=int(ra))
        if not data.get("ok"):
            return PublishResult(False, error=f"HTTP {r.status_code}: {data.get('description', r.text[:200])}",
                                 retryable=r.status_code >= 500)
        mid = str(data["result"]["message_id"])
        url = f"https://t.me/{self.chat.lstrip('@')}/{mid}" if self.chat.startswith("@") else None
        return PublishResult(True, external_id=mid, external_url=url)

    def health(self) -> dict:
        if not self.is_configured():
            return {"configured": False}
        try:
            r = self.client.get(f"/bot{self.token}/getMe")
            return {"configured": True, "ok": r.is_success}
        except httpx.HTTPError as e:
            return {"configured": True, "ok": False, "detail": str(e)}


class WhatsAppManualPublisher(Publisher):
    platform = "whatsapp"

    def is_configured(self) -> bool:
        return True

    def publish(self, req: PublishRequest) -> PublishResult:
        return PublishResult(False, manual=True, error=None, retryable=False)

    def health(self) -> dict:
        return {"configured": bool(get_settings().whatsapp_channel_invite_url), "mode": "manuelle Freigabe"}


class WebsitePublisher(Publisher):
    """Website: Veröffentlichen = Deal-Seite sichtbar schalten (lokal, keine externe API)."""

    platform = "website"

    def is_configured(self) -> bool:
        return True

    def publish(self, req: PublishRequest) -> PublishResult:
        return PublishResult(True, external_url=req.link_url)


def get_publisher(platform: str) -> Publisher:
    from app.publishers.instagram import InstagramPublisher
    from app.publishers.pinterest import PinterestPublisher

    return {
        "instagram": InstagramPublisher, "pinterest": PinterestPublisher, "telegram": TelegramPublisher,
        "whatsapp": WhatsAppManualPublisher, "website": WebsitePublisher, "newsletter": WhatsAppManualPublisher,
    }[platform]()
