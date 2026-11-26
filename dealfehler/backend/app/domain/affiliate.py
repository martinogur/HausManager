"""Affiliate-Links regelkonform erzeugen und prüfen.

* Keine Verschleierung: Ziel ist immer die direkte Händler-URL mit Partner-Tag.
* Amazon: nur offizielle Domains, Tag als Query-Parameter "tag".
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

AMAZON_DOMAINS = {"www.amazon.de", "amazon.de"}
ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,60}-21$")


class AffiliateError(ValueError):
    pass


def amazon_link(asin: str, partner_tag: str, marketplace: str = "www.amazon.de") -> str:
    asin = asin.strip().upper()
    if not ASIN_RE.match(asin):
        raise AffiliateError(f"Ungültige ASIN: {asin!r}")
    if not TAG_RE.match(partner_tag or ""):
        raise AffiliateError(f"Ungültige Partner-ID (erwartet z.B. 'dealfehler-21'): {partner_tag!r}")
    if marketplace not in AMAZON_DOMAINS:
        raise AffiliateError(f"Marketplace nicht unterstützt: {marketplace}")
    return f"https://{marketplace}/dp/{asin}?tag={partner_tag}"


def validate_amazon_link(url: str, expected_tag: str | None = None) -> list[str]:
    issues: list[str] = []
    p = urlparse(url)
    if p.scheme != "https":
        issues.append("Link muss https verwenden")
    if p.netloc not in AMAZON_DOMAINS:
        issues.append(f"Keine offizielle Amazon.de-Domain: {p.netloc}")
    tags = parse_qs(p.query).get("tag", [])
    if len(tags) != 1:
        issues.append("Genau ein Partner-Tag erforderlich")
    elif expected_tag and tags[0] != expected_tag:
        issues.append("Partner-Tag stimmt nicht mit Konfiguration überein")
    if not re.search(r"/dp/[A-Z0-9]{10}", p.path):
        issues.append("Link zeigt nicht auf eine Produktseite (/dp/ASIN)")
    return issues


def generic_link(product_url: str, params: dict[str, str]) -> str:
    """Für Netzwerke mit Deeplink-Parametern (z.B. Awin-Deeplinks werden separat gebaut)."""
    p = urlparse(product_url)
    q = parse_qs(p.query)
    for k, v in params.items():
        q[k] = [v]
    return urlunparse(p._replace(query=urlencode({k: v[0] for k, v in q.items()})))


def awin_deeplink(publisher_id: str, advertiser_id: str, destination_url: str, clickref: str | None = None) -> str:
    """Offizielles Awin-Deeplink-Format (cread.php)."""
    q = {"awinmid": advertiser_id, "awinaffid": publisher_id, "ued": destination_url}
    if clickref:
        q["clickref"] = clickref
    return "https://www.awin1.com/cread.php?" + urlencode(q)
