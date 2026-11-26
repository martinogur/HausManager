"""Eigene Deal-Grafiken (Pillow). Keine Amazon-Produktbilder – nur generierte Layouts.

Design: Schwarz / Weiß / Neon-Grün, große Preise, DealFehler-Wortmarke.
Mehrere Vorlagen, damit Beiträge nicht identisch aussehen.
"""
from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import get_settings
from app.domain.timeutil import fmt_eur

BLACK = (8, 8, 8)
WHITE = (245, 245, 245)
GREY = (150, 150, 150)
NEON = (57, 255, 20)
DARK = (24, 24, 24)

# Alle Layouts sind für Hochformat ausgelegt (4:5 und höher)
SIZES = {"post": (1080, 1350), "story": (1080, 1920), "reel": (1080, 1920), "pin": (1000, 1500)}
TEMPLATES = ["neon_split", "bold_center", "receipt", "badge_grid"]

CATEGORY_LABELS = {
    "technik": "TECHNIK", "haushalt": "HAUSHALT", "werkzeug": "WERKZEUG", "garten": "GARTEN",
    "kueche": "KÜCHE", "gaming": "GAMING", "baby": "BABY & KIND", "auto": "AUTO", "sport": "SPORT",
    "drogerie": "DROGERIE", "sonstiges": "DEAL",
}


@dataclass
class CreativeData:
    title: str
    price_cents: int
    reference_price_cents: int | None
    discount_pct: float | None
    label: str
    category: str
    price_stand: str  # "25.11.2026, 14:05 Uhr"
    brand: str | None = None
    coupon_code: str | None = None


@lru_cache(maxsize=64)
def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    s = get_settings()
    path = s.font_path if bold else s.font_path_regular
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default(size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int, max_lines: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
        if len(lines) == max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and " ".join(lines) != text:
        last = lines[-1]
        while draw.textlength(last + " …", font=font) > max_w and " " in last:
            last = last.rsplit(" ", 1)[0]
        lines[-1] = last + " …"
    return lines


def _fit_font(draw, text: str, max_w: int, start: int, minimum: int = 40):
    size = start
    while size > minimum and draw.textlength(text, font=_font(size)) > max_w:
        size -= 4
    return _font(size)


def _logo(draw: ImageDraw.ImageDraw, x: int, y: int, size: int = 54) -> None:
    f = _font(size)
    draw.text((x, y), "DEAL", font=f, fill=WHITE)
    draw.text((x + draw.textlength("DEAL", font=f), y), "FEHLER", font=f, fill=NEON)


def _pill(draw, x, y, text, font, fg=BLACK, bg=NEON, pad=(22, 10)) -> int:
    w = draw.textlength(text, font=font)
    h = font.size
    draw.rounded_rectangle([x, y, x + w + 2 * pad[0], y + h + 2 * pad[1]], radius=(h + 2 * pad[1]) // 2, fill=bg)
    draw.text((x + pad[0], y + pad[1] - 2), text, font=font, fill=fg)
    return int(w + 2 * pad[0])


def _footer(draw, W, H, d: CreativeData) -> None:
    f = _font(26, bold=False)
    draw.line([60, H - 120, W - 60, H - 120], fill=DARK, width=3)
    draw.text((60, H - 100), "ANZEIGE · Affiliate-Link", font=_font(26), fill=NEON)
    draw.text((60, H - 62), f"Preis Stand: {d.price_stand} · Preise können sich ändern", font=f, fill=GREY)
    if d.coupon_code:
        cf = _font(30)
        t = f"Code: {d.coupon_code}"
        draw.text((W - 60 - draw.textlength(t, font=cf), H - 102), t, font=cf, fill=WHITE)


def _ref_line(d: CreativeData) -> str | None:
    if d.reference_price_cents and d.reference_price_cents > d.price_cents:
        return f"Ø-Preis 90 Tage: {fmt_eur(d.reference_price_cents)}"
    return None


def _neon_split(img, d: CreativeData):
    W, H = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, int(H * 0.52)], fill=BLACK)
    draw.rectangle([0, int(H * 0.52), W, H], fill=(14, 14, 14))
    draw.rectangle([0, int(H * 0.52) - 8, W, int(H * 0.52)], fill=NEON)
    _logo(draw, 60, 60)
    _pill(draw, 60, 160, d.label.upper(), _font(40))
    _pill(draw, 60, 240, CATEGORY_LABELS.get(d.category, "DEAL"), _font(30), fg=WHITE, bg=DARK)
    tf = _font(58)
    y = 340
    for line in _wrap(draw, d.title, tf, W - 120, 4):
        draw.text((60, y), line, font=tf, fill=WHITE)
        y += 72
    py = int(H * 0.52) + 50
    price = fmt_eur(d.price_cents)
    pf = _fit_font(draw, price, W - 120, 190)
    draw.text((60, py), price, font=pf, fill=NEON)
    ref = _ref_line(d)
    if ref:
        draw.text((60, py + pf.size + 30), ref, font=_font(40, bold=False), fill=GREY)
    if d.discount_pct and d.discount_pct >= 5:
        _pill(draw, 60, py + pf.size + 100, f"-{int(d.discount_pct)} %", _font(64), pad=(30, 14))
    _footer(draw, W, H, d)


def _bold_center(img, d: CreativeData):
    W, H = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, H], fill=BLACK)
    for i in range(0, W + H, 90):  # dezente Diagonalen
        draw.line([i, 0, i - H, H], fill=(18, 18, 18), width=30)
    _logo(draw, (W - 470) // 2, 70)
    lf = _font(48)
    lw = draw.textlength(d.label.upper(), font=lf)
    _pill(draw, int((W - lw) / 2 - 22), 170, d.label.upper(), lf)
    price = fmt_eur(d.price_cents)
    pf = _fit_font(draw, price, W - 100, 230)
    pw = draw.textlength(price, font=pf)
    cy = int(H * 0.30)
    draw.text(((W - pw) / 2, cy), price, font=pf, fill=NEON)
    ref = _ref_line(d)
    if ref:
        rf = _font(42, bold=False)
        draw.text(((W - draw.textlength(ref, font=rf)) / 2, cy + pf.size + 30), ref, font=rf, fill=GREY)
    if d.discount_pct and d.discount_pct >= 5:
        t = f"-{int(d.discount_pct)} %"
        f = _font(120)
        draw.text(((W - draw.textlength(t, font=f)) / 2, cy + pf.size + 110), t, font=f, fill=WHITE)
    tf = _font(54)
    y = int(H * 0.66)
    for line in _wrap(draw, d.title, tf, W - 140, 3):
        draw.text(((W - draw.textlength(line, font=tf)) / 2, y), line, font=tf, fill=WHITE)
        y += 68
    _footer(draw, W, H, d)


def _receipt(img, d: CreativeData):
    W, H = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, H], fill=NEON)
    m = 70
    draw.rounded_rectangle([m, m, W - m, H - 150], radius=36, fill=BLACK)
    _logo(draw, m + 50, m + 50, 50)
    mono = _font(34, bold=False)
    draw.text((m + 50, m + 140), "— KASSENBON —", font=mono, fill=GREY)
    tf = _font(50)
    y = m + 210
    for line in _wrap(draw, d.title, tf, W - 2 * m - 100, 4):
        draw.text((m + 50, y), line, font=tf, fill=WHITE)
        y += 64
    y += 30
    draw.line([m + 50, y, W - m - 50, y], fill=GREY, width=2)
    rows = []
    if d.reference_price_cents and d.reference_price_cents > d.price_cents:
        rows.append(("Ø 90 Tage", fmt_eur(d.reference_price_cents)))
        rows.append(("Ersparnis", fmt_eur(d.reference_price_cents - d.price_cents)))
    for k, v in rows:
        y += 30
        draw.text((m + 50, y), k, font=mono, fill=GREY)
        draw.text((W - m - 50 - draw.textlength(v, font=mono), y), v, font=mono, fill=WHITE)
        y += 30
    y += 50
    draw.text((m + 50, y), "JETZT", font=_font(44), fill=GREY)
    price = fmt_eur(d.price_cents)
    pf = _fit_font(draw, price, W - 2 * m - 100, 170)
    draw.text((m + 50, y + 60), price, font=pf, fill=NEON)
    _pill(draw, m + 50, H - 150 - 110, d.label.upper(), _font(36))
    f = _font(26, bold=False)
    draw.text((m, H - 120), "ANZEIGE · Affiliate-Link", font=_font(28), fill=BLACK)
    draw.text((m, H - 80), f"Preis Stand: {d.price_stand} · Preise können sich ändern", font=f, fill=BLACK)
    if d.coupon_code:
        t = f"Code: {d.coupon_code}"
        draw.text((W - m - draw.textlength(t, font=_font(30)), H - 122), t, font=_font(30), fill=BLACK)


def _badge_grid(img, d: CreativeData):
    W, H = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, H], fill=(12, 12, 12))
    for x in range(0, W, 60):
        draw.line([x, 0, x, H], fill=(22, 22, 22), width=1)
    for y in range(0, H, 60):
        draw.line([0, y, W, y], fill=(22, 22, 22), width=1)
    _logo(draw, 60, 60, 50)
    r = 190
    cx, cy = W - r - 60, 60 + r
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=NEON)
    big = f"-{int(d.discount_pct)}%" if d.discount_pct and d.discount_pct >= 5 else "DEAL"
    bf = _fit_font(draw, big, 2 * r - 50, 130)
    draw.text((cx - draw.textlength(big, font=bf) / 2, cy - bf.size / 2 - 10), big, font=bf, fill=BLACK)
    _pill(draw, 60, 160, CATEGORY_LABELS.get(d.category, "DEAL"), _font(30), fg=BLACK, bg=WHITE)
    tf = _font(60)
    y = int(H * 0.40)
    for line in _wrap(draw, d.title, tf, W - 120, 3):
        draw.text((60, y), line, font=tf, fill=WHITE)
        y += 74
    price = fmt_eur(d.price_cents)
    pf = _fit_font(draw, price, W - 120, 200)
    draw.text((60, y + 40), price, font=pf, fill=NEON)
    ref = _ref_line(d)
    if ref:
        draw.text((60, y + 60 + pf.size), ref, font=_font(40, bold=False), fill=GREY)
    _pill(draw, 60, H - 210, d.label.upper(), _font(36))
    _footer(draw, W, H, d)


RENDERERS = {"neon_split": _neon_split, "bold_center": _bold_center, "receipt": _receipt, "badge_grid": _badge_grid}


def render_png(d: CreativeData, kind: str = "post", template: str = "neon_split") -> bytes:
    if template not in RENDERERS:
        raise ValueError(f"Unbekannte Vorlage {template}")
    img = Image.new("RGB", SIZES[kind], BLACK)
    RENDERERS[template](img, d)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _frame_hook(d: CreativeData, size) -> Image.Image:
    img = Image.new("RGB", size, BLACK)
    draw = ImageDraw.Draw(img)
    W, H = size
    _logo(draw, (W - 470) // 2, 120)
    t = d.label.upper() + "?" if "Verdacht" in d.label else d.label.upper()
    f = _fit_font(draw, t, W - 100, 120)
    draw.text(((W - draw.textlength(t, font=f)) / 2, H * 0.40), t, font=f, fill=NEON)
    sub = CATEGORY_LABELS.get(d.category, "DEAL")
    sf = _font(60)
    draw.text(((W - draw.textlength(sub, font=sf)) / 2, H * 0.40 + 170), sub, font=sf, fill=WHITE)
    draw.text((60, H - 100), "ANZEIGE · Affiliate-Link", font=_font(30), fill=NEON)
    return img


def _frame_cta(d: CreativeData, size) -> Image.Image:
    img = Image.new("RGB", size, NEON)
    draw = ImageDraw.Draw(img)
    W, H = size
    for i, line in enumerate(["LINK IN BIO", "& IM KANAL"]):
        f = _font(110)
        draw.text(((W - draw.textlength(line, font=f)) / 2, H * 0.38 + i * 140), line, font=f, fill=BLACK)
    small = f"Preis Stand: {d.price_stand}"
    sf = _font(34, bold=False)
    draw.text(((W - draw.textlength(small, font=sf)) / 2, H - 140), small, font=sf, fill=BLACK)
    return img


def render_reel_mp4(d: CreativeData, template: str = "bold_center", seconds_per_frame: float = 2.5) -> bytes:
    """Kurzes Slideshow-Reel (9:16, 3 Szenen) via ffmpeg. Ohne Musik (Lizenzfragen)."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg nicht installiert")
    size = SIZES["reel"]
    main = Image.open(io.BytesIO(render_png(d, "reel", template)))
    frames = [_frame_hook(d, size), main, _frame_cta(d, size)]
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        for i, f in enumerate(frames):
            f.save(tp / f"f{i}.png")
        n = len(frames)
        inputs = []
        for i in range(n):
            inputs += ["-loop", "1", "-t", str(seconds_per_frame), "-i", str(tp / f"f{i}.png")]
        # Crossfades zwischen den Szenen
        fd = 0.4
        filt, last = [], "[0:v]"
        for i in range(1, n):
            off = i * seconds_per_frame - i * fd
            out = f"[v{i}]"
            filt.append(f"{last}[{i}:v]xfade=transition=fade:duration={fd}:offset={off:.2f}{out}")
            last = out
        cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt),
               "-map", last, "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
               str(tp / "out.mp4")]
        subprocess.run(cmd, check=True, timeout=120)
        return (tp / "out.mp4").read_bytes()
