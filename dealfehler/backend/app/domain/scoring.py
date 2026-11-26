"""Preisfehler-Erkennung: Score 0–100 auf Basis EIGENER Preishistorie.

Grundsätze
* Ein ungewöhnlicher Preis ist kein bestätigter Preisfehler → Label "Preisfehler-Verdacht".
* Referenz ist der Median der gemessenen Historie (nicht die UVP / Streichpreis des Händlers),
  damit keine irreführenden Rabattangaben entstehen.
* Ohne ausreichende Historie wird der Score gedeckelt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from statistics import median

from app.domain.timeutil import aware

MIN_HISTORY_POINTS = 5
MIN_HISTORY_DAYS = 14


@dataclass
class PriceObs:
    price_cents: int
    observed_at: datetime
    available: bool = True


@dataclass
class ScoreResult:
    score: int
    label: str
    deal_type: str  # siehe models.DealType values
    reference_price_cents: int | None
    reference_kind: str | None
    discount_pct: float | None
    breakdown: dict = field(default_factory=dict)
    publishable: bool = False


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def score_price(
    current_cents: int,
    history: list[PriceObs],
    now: datetime,
    *,
    list_price_cents: int | None = None,
    other_source_prices: list[int] | None = None,
    verification_count: int = 0,
    rating: float | None = None,
    review_count: int | None = None,
) -> ScoreResult:
    now = aware(now)
    # Historie OHNE die letzten 24h (sonst zieht der aktuelle Preissturz die Referenz mit)
    cutoff = now - timedelta(hours=24)
    window_start = now - timedelta(days=90)
    hist = [
        h for h in history
        if h.available and h.price_cents > 0 and window_start <= aware(h.observed_at) < cutoff
    ]
    prices = [h.price_cents for h in hist]
    bd: dict = {"history_points": len(prices)}

    span_days = 0.0
    if hist:
        times = [aware(h.observed_at) for h in hist]
        span_days = (max(times) - min(times)).total_seconds() / 86400
    bd["history_span_days"] = round(span_days, 1)
    sufficient = len(prices) >= MIN_HISTORY_POINTS and span_days >= MIN_HISTORY_DAYS

    ref: int | None = None
    ref_kind: str | None = None
    if prices:
        ref = int(median(prices))
        ref_kind = "median_90d"
    elif list_price_cents and list_price_cents > current_cents:
        ref = list_price_cents
        ref_kind = "list_price"

    if not ref or ref <= 0:
        return ScoreResult(0, "Kein Referenzpreis", "deal", None, None, None, bd | {"reason": "no_reference"})

    drop = 1 - current_cents / ref
    bd["drop_pct"] = round(drop * 100, 1)

    # 1) Preissturz relativ zur Referenz: 15 % → 0 Punkte, 75 % → 45 Punkte
    drop_pts = _clamp((drop - 0.15) / 0.60, 0, 1) * 45
    # 2) Robuste Anomalie (Median-Abweichung, MAD)
    anomaly_pts = 0.0
    if len(prices) >= MIN_HISTORY_POINTS:
        m = median(prices)
        mad = median([abs(p - m) for p in prices]) or max(1.0, m * 0.01)
        robust_z = (m - current_cents) / (1.4826 * mad)
        bd["robust_z"] = round(robust_z, 2)
        anomaly_pts = _clamp((robust_z - 2) / 8, 0, 1) * 20
    # 3) Unter dem 90-Tage-Tiefstpreis
    low_pts = 0.0
    if prices:
        lowest = min(prices)
        bd["lowest_90d_cents"] = lowest
        if current_cents < lowest:
            low_pts = _clamp((1 - current_cents / lowest) / 0.3, 0, 1) * 10 + 2
            low_pts = min(low_pts, 10)
    # 4) Abgleich mit unabhängigen Quellen
    cross_pts = 0.0
    if other_source_prices:
        valid = [p for p in other_source_prices if p > 0]
        if valid:
            other_med = median(valid)
            cross_drop = 1 - current_cents / other_med
            bd["cross_source_drop_pct"] = round(cross_drop * 100, 1)
            cross_pts = _clamp((cross_drop - 0.10) / 0.50, 0, 1) * 15
    # 5) Mehrfache Verifikation (erneute Preisprüfungen)
    verify_pts = min(verification_count, 2) * 5
    # 6) Produktqualität als kleiner Bonus/Malus (Kaufinteresse)
    quality_pts = 0.0
    if rating is not None and review_count:
        if rating >= 4.2 and review_count >= 100:
            quality_pts = 3
        elif rating < 3.5:
            quality_pts = -8

    raw = drop_pts + anomaly_pts + low_pts + cross_pts + verify_pts + quality_pts
    # Kleine Rabatte, die nur aus Rauschen bestehen, nicht künstlich hochziehen
    if drop < 0.10:
        raw = min(raw, 30)
    # Ohne ausreichende Historie kein "Preisfehler-Verdacht" möglich
    if not sufficient:
        raw = min(raw, 74)
        bd["capped"] = "insufficient_history"
    # Nur UVP als Referenz → stark deckeln (Streichpreise sind oft nicht aussagekräftig)
    if ref_kind == "list_price":
        raw = min(raw, 55)
        bd["capped"] = "list_price_reference"
    # 90+ nur bei mindestens zweifacher Verifikation
    if raw >= 90 and verification_count < 2:
        raw = 89
        bd["capped_90"] = "needs_2_verifications"

    score = int(round(_clamp(raw, 0, 100)))
    bd["components"] = {
        "drop": round(drop_pts, 1),
        "anomaly": round(anomaly_pts, 1),
        "below_low": round(low_pts, 1),
        "cross_source": round(cross_pts, 1),
        "verification": verify_pts,
        "quality": quality_pts,
    }

    if score >= 90:
        label, dtype = "Preisfehler-Verdacht", "preisfehler_verdacht"
    elif score >= 75:
        label, dtype = "Top-Deal", "top_deal"
    elif score >= 50:
        label, dtype = "Deal", "deal"
    else:
        label, dtype = "Nicht veröffentlichen", "deal"

    return ScoreResult(
        score=score,
        label=label,
        deal_type=dtype,
        reference_price_cents=ref,
        reference_kind=ref_kind,
        discount_pct=round(drop * 100, 1) if drop > 0 else 0.0,
        breakdown=bd,
        publishable=score >= 50,
    )
