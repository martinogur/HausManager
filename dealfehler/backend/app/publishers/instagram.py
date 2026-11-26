"""Instagram über die offizielle Instagram Graph API (Content Publishing).

Ablauf: 1) Container anlegen  POST /{ig-user-id}/media
        2) Status prüfen      GET  /{container-id}?fields=status_code   (bei Video/Reel)
        3) Veröffentlichen    POST /{ig-user-id}/media_publish
Voraussetzung: Professional-Konto, Facebook-App mit instagram_content_publish,
öffentlich erreichbare Medien-URL (S3/CDN).
Limit-Abfrage: GET /{ig-user-id}/content_publishing_limit
"""
from __future__ import annotations

import time

import httpx

from app.config import get_settings
from app.publishers.base import Publisher, PublishRequest, PublishResult


class InstagramPublisher(Publisher):
    platform = "instagram"

    def __init__(self, client: httpx.Client | None = None, poll_interval: float = 3.0, max_polls: int = 40):
        s = get_settings()
        self.user_id = s.instagram_user_id
        self.token = s.instagram_access_token
        self.client = client or httpx.Client(base_url=f"https://graph.facebook.com/{s.meta_graph_version}", timeout=60)
        self.poll_interval = poll_interval
        self.max_polls = max_polls

    def is_configured(self) -> bool:
        return bool(self.user_id and self.token)

    @staticmethod
    def _err(r: httpx.Response) -> PublishResult:
        try:
            err = r.json().get("error", {})
        except ValueError:
            err = {}
        code = err.get("code")
        # 4/17/32/613 = Rate-Limits laut Graph-API-Fehlercodes; 9 = Publishing-Limit erreicht
        rate = r.status_code == 429 or code in (4, 9, 17, 32, 613)
        return PublishResult(False, error=f"HTTP {r.status_code}: {err.get('message', r.text[:300])}",
                             rate_limited=rate, retryable=rate or r.status_code >= 500)

    def publishing_limit(self) -> dict:
        r = self.client.get(f"/{self.user_id}/content_publishing_limit",
                            params={"fields": "config,quota_usage", "access_token": self.token})
        r.raise_for_status()
        return r.json()

    def publish(self, req: PublishRequest) -> PublishResult:
        if not req.media_url or not req.media_url.startswith("https://"):
            return PublishResult(False, error="Instagram benötigt eine öffentliche https-Medien-URL", retryable=False)
        params: dict = {"access_token": self.token}
        if req.format == "story":
            params.update(media_type="STORIES", image_url=req.media_url)
        elif req.format == "reel":
            params.update(media_type="REELS", video_url=req.media_url, caption=req.caption)
        else:
            params.update(image_url=req.media_url, caption=req.caption)
        r = self.client.post(f"/{self.user_id}/media", data=params)
        if not r.is_success:
            return self._err(r)
        container = r.json()["id"]
        for _ in range(self.max_polls):
            s = self.client.get(f"/{container}", params={"fields": "status_code", "access_token": self.token})
            if not s.is_success:
                return self._err(s)
            code = s.json().get("status_code")
            if code == "FINISHED" or code is None:
                break
            if code in ("ERROR", "EXPIRED"):
                return PublishResult(False, error=f"Container-Status {code}", retryable=False)
            time.sleep(self.poll_interval)
        else:
            return PublishResult(False, error="Container nicht rechtzeitig fertig", retryable=True)
        p = self.client.post(f"/{self.user_id}/media_publish", data={"creation_id": container, "access_token": self.token})
        if not p.is_success:
            return self._err(p)
        media_id = p.json()["id"]
        link = None
        q = self.client.get(f"/{media_id}", params={"fields": "permalink", "access_token": self.token})
        if q.is_success:
            link = q.json().get("permalink")
        return PublishResult(True, external_id=media_id, external_url=link)

    def health(self) -> dict:
        if not self.is_configured():
            return {"configured": False}
        try:
            r = self.client.get(f"/{self.user_id}", params={"fields": "username", "access_token": self.token})
            return {"configured": True, "ok": r.is_success, "detail": r.json() if r.is_success else r.text[:300]}
        except httpx.HTTPError as e:
            return {"configured": True, "ok": False, "detail": str(e)}

    def insights(self, media_id: str) -> dict:
        r = self.client.get(f"/{media_id}/insights",
                            params={"metric": "reach,likes,saved,shares", "access_token": self.token})
        if not r.is_success:
            return {}
        return {m["name"]: (m.get("values") or [{}])[0].get("value") for m in r.json().get("data", [])}
