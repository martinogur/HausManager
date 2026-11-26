"""Pinterest über die offizielle API v5.

POST /v5/pins  {board_id, title, description, link, media_source}
GET  /v5/boards, POST /v5/boards
Rate-Limits werden über HTTP 429 + Header erkannt → automatische Pause.
"""
from __future__ import annotations

import base64

import httpx

from app.config import get_settings
from app.publishers.base import Publisher, PublishRequest, PublishResult

BOARDS = [
    "Amazon Preisfehler-Verdacht", "Technik Deals", "Haushalt Deals", "Werkzeug Angebote", "Gaming Deals",
    "Küche und Wohnen", "Baby und Kinder", "Tagesangebote",
]
CATEGORY_BOARD = {
    "technik": "Technik Deals", "haushalt": "Haushalt Deals", "werkzeug": "Werkzeug Angebote",
    "gaming": "Gaming Deals", "kueche": "Küche und Wohnen", "baby": "Baby und Kinder", "garten": "Haushalt Deals",
}


def board_for(category: str, label: str) -> str:
    if label == "Preisfehler-Verdacht":
        return "Amazon Preisfehler-Verdacht"
    return CATEGORY_BOARD.get(category, "Tagesangebote")


class PinterestPublisher(Publisher):
    platform = "pinterest"

    def __init__(self, client: httpx.Client | None = None):
        s = get_settings()
        self.token = s.pinterest_access_token
        self.client = client or httpx.Client(base_url=s.pinterest_api_base, timeout=60)
        self._board_ids: dict[str, str] | None = None

    def is_configured(self) -> bool:
        return bool(self.token)

    @property
    def _h(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def boards(self) -> dict[str, str]:
        if self._board_ids is None:
            out, bookmark = {}, None
            while True:
                params = {"page_size": 100, **({"bookmark": bookmark} if bookmark else {})}
                r = self.client.get("/boards", headers=self._h, params=params)
                r.raise_for_status()
                d = r.json()
                out.update({b["name"]: b["id"] for b in d.get("items", [])})
                bookmark = d.get("bookmark")
                if not bookmark:
                    break
            self._board_ids = out
        return self._board_ids

    def ensure_boards(self) -> dict[str, str]:
        ids = self.boards()
        for name in BOARDS:
            if name not in ids:
                r = self.client.post("/boards", headers=self._h, json={
                    "name": name, "description": f"{name} – ausgewählte Angebote von DealFehler. Enthält Affiliate-Links.",
                    "privacy": "PUBLIC"})
                r.raise_for_status()
                ids[name] = r.json()["id"]
        return ids

    def publish(self, req: PublishRequest) -> PublishResult:
        board_id = self.ensure_boards().get(req.board or "Tagesangebote")
        if req.media_url and req.media_url.startswith("https://"):
            media = {"source_type": "image_url", "url": req.media_url}
        elif req.media_bytes:
            media = {"source_type": "image_base64", "content_type": req.media_content_type or "image/png",
                     "data": base64.b64encode(req.media_bytes).decode()}
        else:
            return PublishResult(False, error="Kein Bild", retryable=False)
        r = self.client.post("/pins", headers=self._h, json={
            "board_id": board_id, "title": (req.title or "")[:100], "description": req.caption[:800],
            "link": req.link_url, "media_source": media, "alt_text": (req.title or "")[:500]})
        if r.status_code == 429:
            ra = r.headers.get("retry-after")
            return PublishResult(False, error="Pinterest Rate-Limit", rate_limited=True,
                                 retry_after_s=int(ra) if ra and ra.isdigit() else 3600)
        if not r.is_success:
            return PublishResult(False, error=f"HTTP {r.status_code}: {r.text[:300]}", retryable=r.status_code >= 500)
        pid = r.json()["id"]
        return PublishResult(True, external_id=pid, external_url=f"https://www.pinterest.com/pin/{pid}/")

    def health(self) -> dict:
        if not self.is_configured():
            return {"configured": False}
        try:
            r = self.client.get("/user_account", headers=self._h)
            return {"configured": True, "ok": r.is_success, "detail": r.json() if r.is_success else r.text[:300]}
        except httpx.HTTPError as e:
            return {"configured": True, "ok": False, "detail": str(e)}

    def analytics(self, pin_id: str, start: str, end: str) -> dict:
        r = self.client.get(f"/pins/{pin_id}/analytics", headers=self._h, params={
            "start_date": start, "end_date": end, "metric_types": "IMPRESSION,OUTBOUND_CLICK,SAVE"})
        return r.json() if r.is_success else {}
