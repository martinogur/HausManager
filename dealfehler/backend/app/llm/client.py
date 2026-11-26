"""KI-Anbindung (Claude) mit hartem Kostenlimit.

Die KI ist OPTIONAL: Ohne API-Key oder bei erreichtem Budget arbeitet das System mit den
Vorlagentexten weiter. KI-Texte durchlaufen immer zusätzlich den Compliance-Agenten.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.timeutil import now
from app.models import CostEntry

log = logging.getLogger(__name__)

# USD pro 1 Mio. Tokens (input, output) – bei Modellwechsel anpassen
PRICING = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}


class BudgetExceeded(RuntimeError):
    pass


def spent_usd(db: Session, provider: str, days: int) -> float:
    since = now() - timedelta(days=days)
    return float(db.scalar(
        select(func.coalesce(func.sum(CostEntry.cost_usd), 0.0)).where(
            CostEntry.provider == provider, CostEntry.created_at >= since)
    ) or 0.0)


def check_budget(db: Session) -> None:
    s = get_settings()
    if spent_usd(db, "anthropic", 1) >= s.llm_daily_budget_usd:
        raise BudgetExceeded("Tagesbudget für KI erreicht")
    if spent_usd(db, "anthropic", 30) >= s.llm_monthly_budget_usd:
        raise BudgetExceeded("Monatsbudget für KI erreicht")


def record_cost(db: Session, model: str, operation: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = PRICING.get(model, (4.0, 20.0))
    cost = input_tokens / 1e6 * pin + output_tokens / 1e6 * pout
    db.add(CostEntry(provider="anthropic", operation=operation,
                     units={"model": model, "input_tokens": input_tokens, "output_tokens": output_tokens},
                     cost_usd=round(cost, 6)))
    return cost


class PolishedCaption(BaseModel):
    hook: str = Field(description="Eine prägnante erste Zeile (max. 90 Zeichen), ohne Werbekennzeichnung")
    body: str = Field(description="2–4 kurze Zeilen mit sachlichem Mehrwert zum Produkt, keine Preise erfinden")


SYSTEM = (
    "Du schreibst kurze, sachliche deutsche Social-Media-Texte für den Deal-Kanal DealFehler. "
    "Regeln: Keine Preise, Rabatte oder Fristen erfinden – nur die gelieferten Fakten verwenden. "
    "Nie 'Preisfehler' ohne den Zusatz 'Verdacht'. Keine Wörter wie 'garantiert', 'gratis', '100 % sicher'. "
    "Keine künstliche Dringlichkeit. Du-Form, freundlich, maximal zwei Emojis."
)


def polish_hook(db: Session, facts: dict) -> PolishedCaption | None:
    s = get_settings()
    if not s.anthropic_api_key:
        return None
    try:
        check_budget(db)
    except BudgetExceeded as e:
        log.info("KI übersprungen: %s", e)
        return None
    import anthropic

    client = anthropic.Anthropic(api_key=s.anthropic_api_key, max_retries=2, timeout=60)
    try:
        resp = client.beta.messages.parse(
            model=s.llm_model,
            max_tokens=2000,
            system=SYSTEM,
            messages=[{"role": "user", "content": f"Produktfakten (JSON): {facts}"}],
            output_format=PolishedCaption,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.RateLimitError:
        log.warning("KI Rate-Limit – Vorlagentext wird verwendet")
        return None
    except anthropic.APIStatusError as e:
        log.warning("KI-Fehler %s – Vorlagentext wird verwendet", e.status_code)
        return None
    except anthropic.APIConnectionError:
        log.warning("KI nicht erreichbar – Vorlagentext wird verwendet")
        return None
    record_cost(db, s.llm_model, "caption_hook", resp.usage.input_tokens, resp.usage.output_tokens)
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        return None
    return resp.parsed_output
