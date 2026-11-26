"""Texte für alle Kanäle. Vorlagenbasiert (deterministisch, kostenlos) – optional KI-Feinschliff."""
from __future__ import annotations

import random
from dataclasses import dataclass

from app.domain.timeutil import fmt_eur

CATEGORY_HASHTAGS = {
    "technik": ["#technikdeals", "#elektronik", "#gadgets"],
    "haushalt": ["#haushalt", "#haushaltstipps", "#wohnen"],
    "werkzeug": ["#werkzeug", "#heimwerker", "#diy"],
    "garten": ["#garten", "#gartenliebe", "#outdoor"],
    "kueche": ["#küche", "#kochen", "#küchenhelfer"],
    "gaming": ["#gaming", "#gamingdeals", "#zocken"],
    "baby": ["#babyausstattung", "#familie", "#kinder"],
    "auto": ["#autozubehör", "#auto", "#carcare"],
    "sport": ["#sport", "#fitness", "#training"],
    "drogerie": ["#drogerie", "#pflege", "#beauty"],
}
BASE_TAGS = ["#dealfehler", "#angebot", "#schnäppchen", "#sparen", "#deals"]


@dataclass
class CaptionInput:
    title: str
    price_cents: int
    reference_price_cents: int | None
    discount_pct: float | None
    label: str
    category: str
    price_stand: str
    link: str | None = None
    coupon_code: str | None = None
    editorial_note: str | None = None


def _savings(c: CaptionInput) -> str:
    if c.reference_price_cents and c.reference_price_cents > c.price_cents and c.discount_pct:
        return (f"Ø-Preis der letzten 90 Tage: {fmt_eur(c.reference_price_cents)} "
                f"(-{int(c.discount_pct)} %)")
    return ""


HOOKS = {
    "a": "{emoji} {label}: {title}",
    "b": "{emoji} {title} – jetzt {price}",
    "c": "{emoji} Schneller sein lohnt sich: {title}",
}


def _emoji(label: str) -> str:
    return {"Preisfehler-Verdacht": "🚨", "Top-Deal": "🔥"}.get(label, "💚")


def instagram(c: CaptionInput, variant: str | None = None, rng: random.Random | None = None,
              ai_hook: str | None = None, ai_body: str | None = None) -> tuple[str, str]:
    rng = rng or random.Random()
    variant = "ai" if ai_hook else (variant or rng.choice(list(HOOKS)))
    hook = ai_hook or HOOKS[variant].format(emoji=_emoji(c.label), label=c.label, title=c.title[:80],
                                            price=fmt_eur(c.price_cents))
    lines = ["Anzeige | Affiliate-Link", "", hook.strip()[:120], ""]
    if ai_body:
        lines += [ai_body.strip()[:400], ""]
    lines.append(f"👉 Preis: {fmt_eur(c.price_cents)}")
    if s := _savings(c):
        lines.append(f"📉 {s}")
    if c.coupon_code:
        lines.append(f"🏷️ Gutscheincode: {c.coupon_code}")
    if c.label == "Preisfehler-Verdacht":
        lines.append("⚠️ Preisfehler-Verdacht: ungewöhnlich niedriger Preis – ob der Händler zu diesem Preis liefert, ist offen.")
    lines += [
        f"🕒 Preis Stand: {c.price_stand}. Preise können sich jederzeit ändern.",
        "",
        "🔗 Link in der Bio / Story",
        "",
        "Als Amazon-Partner verdiene ich an qualifizierten Verkäufen (Partnerlink, für dich ohne Mehrkosten).",
        "",
        " ".join(BASE_TAGS + CATEGORY_HASHTAGS.get(c.category, [])),
    ]
    return "\n".join(lines), variant


def pinterest(c: CaptionInput) -> tuple[str, str]:
    title = f"{c.label}: {c.title}"[:100]
    parts = [f"Anzeige (Affiliate-Link). {c.title} für {fmt_eur(c.price_cents)}."]
    if s := _savings(c):
        parts.append(s + ".")
    parts.append(f"Preis Stand: {c.price_stand}, Preise können sich ändern.")
    parts.append("Als Amazon-Partner verdiene ich an qualifizierten Verkäufen.")
    kw = {"technik": "Technik Angebote, Elektronik günstig", "kueche": "Küchenhelfer, Küchengeräte Angebot",
          "haushalt": "Haushalt Deals, Wohnen", "werkzeug": "Werkzeug Angebote, Heimwerken",
          "gaming": "Gaming Deals, Konsole Angebot", "garten": "Garten Angebote",
          "baby": "Baby Ausstattung günstig", "auto": "Autozubehör Angebot", "sport": "Sport Angebote",
          "drogerie": "Drogerie Angebote"}.get(c.category, "Deals, Schnäppchen")
    parts.append(f"Mehr {kw} bei DealFehler.")
    return title, " ".join(parts)[:800]


def short_message(c: CaptionInput, link: str) -> str:
    """Telegram / WhatsApp."""
    lines = [f"Anzeige | {_emoji(c.label)} *{c.label}*", "", c.title, "", f"💶 {fmt_eur(c.price_cents)}"]
    if s := _savings(c):
        lines.append(f"📉 {s}")
    if c.coupon_code:
        lines.append(f"🏷️ Code: {c.coupon_code}")
    lines += ["", f"👉 {link}", "", f"Preis Stand: {c.price_stand}. Affiliate-Link – als Amazon-Partner "
              "verdiene ich an qualifizierten Verkäufen."]
    return "\n".join(lines)


def website_text(c: CaptionInput) -> str:
    parts = []
    if c.editorial_note:
        parts.append(c.editorial_note)
    parts.append(f"Aktueller Preis: {fmt_eur(c.price_cents)} (Stand: {c.price_stand}).")
    if s := _savings(c):
        parts.append(s + ". Grundlage ist unsere eigene Preisbeobachtung, nicht die UVP.")
    parts.append("Als Amazon-Partner verdiene ich an qualifizierten Verkäufen.")
    return " ".join(parts)
