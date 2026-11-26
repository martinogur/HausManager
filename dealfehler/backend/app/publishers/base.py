from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PublishRequest:
    caption: str
    format: str  # post | story | reel | pin | message
    media_url: str | None = None
    media_bytes: bytes | None = None
    media_content_type: str | None = None
    link_url: str | None = None
    title: str | None = None
    board: str | None = None


@dataclass
class PublishResult:
    ok: bool
    external_id: str | None = None
    external_url: str | None = None
    error: str | None = None
    rate_limited: bool = False
    retry_after_s: int | None = None
    retryable: bool = True
    manual: bool = False  # wartet auf manuelle Veröffentlichung


class Publisher:
    platform: str = "base"

    def is_configured(self) -> bool:
        return False

    def publish(self, req: PublishRequest) -> PublishResult:
        raise NotImplementedError

    def health(self) -> dict:
        """Token-/Verbindungsprüfung für das Dashboard."""
        return {"configured": self.is_configured()}
