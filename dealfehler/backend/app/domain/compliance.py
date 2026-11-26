"""Compliance-Regeln. Ein Inhalt mit mindestens einem Fehler (severity=error) wird NICHT veröffentlicht."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.domain.affiliate import validate_amazon_link
from app.domain.timeutil import aware

AD_MARKERS = ("#anzeige", "anzeige", "werbung", "#werbung")
AMAZON_DISCLOSURE = "Als Amazon-Partner verdiene ich an qualifizierten Verkäufen."
ALLOWED_IMAGE_LICENSES = {"generated", "licensed", "api_licensed"}
FORBIDDEN_PHRASES = [
    (re.compile(r"\bgarantiert\b", re.I), "Unbelegtes Versprechen 'garantiert'"),
    (re.compile(r"100\s*%\s*sicher", re.I), "Unbelegtes Versprechen '100 % sicher'"),
    (re.compile(r"\bgratis\b|\bkostenlos\b", re.I), "'gratis/kostenlos' nur bei Preis 0 erlaubt"),
]
PRICE_ERROR_RE = re.compile(r"preisfehler(?!-?verdacht)", re.I)
PCT_RE = re.compile(r"-\s?(\d{1,2})\s?%")


@dataclass
class Issue:
    code: str
    message: str
    severity: str = "error"  # error | warning

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "severity": self.severity}


@dataclass
class ComplianceInput:
    platform: str
    caption: str
    link_url: str | None
    link_valid: bool
    network: str | None
    price_cents: int
    price_checked_at: datetime | None
    discount_pct: float | None
    product_source: str
    confirmed_price_error: bool = False
    media_license: str | None = None
    media_price_cents: int | None = None
    valid_until: datetime | None = None
    expected_tag: str | None = None
    website_page: bool = False


@dataclass
class ComplianceResult:
    issues: list[Issue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)


def check(inp: ComplianceInput, now: datetime, max_price_age_minutes: int = 60) -> ComplianceResult:
    r = ComplianceResult()
    add = lambda code, msg, sev="error": r.issues.append(Issue(code, msg, sev))  # noqa: E731
    text = inp.caption or ""
    low = text.lower()

    # 1) Werbekennzeichnung – auf Social Media am Anfang sichtbar (vor "mehr anzeigen")
    if inp.platform in {"instagram", "pinterest", "telegram", "whatsapp", "newsletter"}:
        head = low[:125]
        if not any(m in head for m in AD_MARKERS):
            add("AD_MARKER_MISSING", "Werbekennzeichnung ('Anzeige'/'Werbung') fehlt am Textanfang")
    if inp.network == "amazon":
        if inp.website_page:
            if AMAZON_DISCLOSURE.lower() not in low:
                add("AMAZON_DISCLOSURE_MISSING", "Amazon-Partner-Hinweis fehlt auf der Seite")
        elif not any(k in low for k in ("affiliate", "partnerlink", "amazon-partner", "provision")):
            add("AFFILIATE_HINT_MISSING", "Hinweis auf Affiliate-/Partnerlink fehlt")

    # 2) Link
    if not inp.link_url:
        add("LINK_MISSING", "Kein Link zugeordnet")
    elif not inp.link_valid:
        add("LINK_INVALID", "Link wurde nicht erfolgreich geprüft")
    elif inp.network == "amazon" and "/go/" not in inp.link_url and "/deals/" not in inp.link_url:
        for msg in validate_amazon_link(inp.link_url, inp.expected_tag):
            add("AMAZON_LINK_RULE", msg)

    # 3) Preisaktualität + Zeitstempel
    checked = aware(inp.price_checked_at)
    if checked is None:
        add("PRICE_NOT_CHECKED", "Preis wurde nie verifiziert")
    elif now - checked > timedelta(minutes=max_price_age_minutes):
        add("PRICE_STALE", f"Preisprüfung älter als {max_price_age_minutes} Minuten")
    if "stand" not in low and inp.platform != "website":
        add("PRICE_TIMESTAMP_MISSING", "Zeitstempel der Preisangabe ('Stand: …') fehlt")
    if inp.media_price_cents is not None and inp.media_price_cents != inp.price_cents:
        add("MEDIA_PRICE_MISMATCH", "Preis in der Grafik weicht vom aktuellen Preis ab")

    # 4) Irreführende Angaben
    if PRICE_ERROR_RE.search(text) and not inp.confirmed_price_error:
        add("PRICE_ERROR_UNCONFIRMED", "'Preisfehler' ohne Nachweis – 'Preisfehler-Verdacht' verwenden")
    for rx, msg in FORBIDDEN_PHRASES:
        if rx.search(text) and not (inp.price_cents == 0 and "gratis" in msg):
            add("MISLEADING_PHRASE", msg)
    for m in PCT_RE.finditer(text):
        stated = int(m.group(1))
        if inp.discount_pct is None or stated > inp.discount_pct + 1:
            add("DISCOUNT_OVERSTATED", f"Angegebener Rabatt -{stated} % ist nicht belegt")
    if re.search(r"nur (noch )?heute|endet (heute|bald)", low) and inp.valid_until is None:
        add("UNVERIFIED_URGENCY", "Zeitliche Dringlichkeit ohne bekanntes Enddatum", "error")

    # 5) Bilder / Urheberrecht
    if inp.platform != "website" or inp.media_license:
        if inp.media_license is None and inp.platform in {"instagram", "pinterest"}:
            add("MEDIA_MISSING", "Kein Bild vorhanden")
        elif inp.media_license and inp.media_license not in ALLOWED_IMAGE_LICENSES:
            add("MEDIA_LICENSE", f"Bildlizenz '{inp.media_license}' nicht zulässig")

    # 6) Datenquelle
    if inp.product_source == "demo":
        add("DEMO_DATA", "Demo-Daten dürfen nie veröffentlicht werden")

    # 7) Plattform-Längen
    limits = {"instagram": 2200, "pinterest": 800, "telegram": 1024, "whatsapp": 1500}
    if inp.platform in limits and len(text) > limits[inp.platform]:
        add("TEXT_TOO_LONG", f"Text länger als {limits[inp.platform]} Zeichen")
    if inp.platform == "instagram" and text.count("#") > 30:
        add("TOO_MANY_HASHTAGS", "Instagram erlaubt max. 30 Hashtags")
    return r
