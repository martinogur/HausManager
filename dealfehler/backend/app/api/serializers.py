from app.agents.pipeline import deal_label
from app.models import Deal, Publication


def iso(dt):
    return dt.isoformat() if dt else None


def deal_out(d: Deal, full: bool = False) -> dict:
    p = d.product
    out = {
        "id": d.id, "slug": d.slug, "status": d.status.value, "deal_type": d.deal_type.value, "label": deal_label(d),
        "title": p.title, "brand": p.brand, "category": p.category, "merchant": p.merchant,
        "external_id": p.external_id, "source": p.source,
        "price_cents": d.current_price_cents, "reference_price_cents": d.reference_price_cents,
        "reference_kind": d.reference_kind, "discount_pct": d.discount_pct, "score": d.score,
        "priority": d.priority, "verification_count": d.verification_count,
        "confirmed_price_error": d.confirmed_price_error, "coupon_code": d.coupon_code,
        "price_checked_at": iso(d.price_checked_at), "valid_until": iso(d.valid_until),
        "created_at": iso(d.created_at), "updated_at": iso(d.updated_at),
    }
    if full:
        out["score_breakdown"] = d.score_breakdown
        out["editorial_note"] = d.editorial_note
        out["links"] = [{"id": lk.id, "network": lk.network, "channel": lk.channel, "url": lk.url,
                         "tracking_id": lk.tracking_id, "is_valid": lk.is_valid, "check_error": lk.check_error}
                        for lk in d.links]
        out["media"] = [{"id": m.id, "kind": m.kind, "template": m.template, "url": m.public_url,
                         "price_cents": m.price_cents_rendered} for m in d.media]
        out["publications"] = [pub_out(x) for x in d.publications]
        out["events"] = [{"from": e.from_status, "to": e.to_status, "actor": e.actor, "note": e.note,
                          "at": iso(e.created_at)} for e in sorted(d.events, key=lambda e: e.id)]
    return out


def pub_out(p: Publication) -> dict:
    return {
        "id": p.id, "deal_id": p.deal_id, "platform": p.platform.value, "format": p.format, "status": p.status.value,
        "caption": p.caption, "title": p.title, "link_url": p.link_url, "board": p.board, "template": p.template,
        "media_url": p.media.public_url if p.media else None, "price_cents": p.price_cents_at_creation,
        "scheduled_at": iso(p.scheduled_at), "published_at": iso(p.published_at), "external_id": p.external_id,
        "external_url": p.external_url, "attempts": p.attempts, "last_error": p.last_error,
        "dry_run": bool((p.metrics or {}).get("dry_run")), "deal_title": p.deal.product.title if p.deal else None,
    }
