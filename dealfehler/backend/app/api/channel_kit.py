"""WhatsApp-Kanal-Paket: Texte, Profilbild und QR-Code für den Einladungslink."""
import io

import qrcode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from PIL import Image, ImageDraw

from app.api.deps import viewer
from app.config import get_settings
from app.creative.render import BLACK, NEON, WHITE, _font

router = APIRouter(prefix="/api/channel-kit")

KIT = {
    "name": "DealFehler – Deals & Preisfehler-Verdacht",
    "description": (
        "Gute Deals. Schlechte Preise. Dein Vorteil. 💚\n"
        "Geprüfte Angebote und auffällig günstige Preise (Preisfehler-Verdacht) – max. 3–5 Beiträge am Tag, "
        "keine Werbeflut.\n"
        "Alle Preise mit Zeitstempel, Angaben ohne Gewähr. Enthält Affiliate-Links (Anzeige): Als Amazon-Partner "
        "verdiene ich an qualifizierten Verkäufen – für dich ohne Mehrkosten."
    ),
    "welcome": (
        "Willkommen bei DealFehler! 👋\n\n"
        "Hier bekommst du nur Deals, die unser System gegen die echte Preishistorie geprüft hat. "
        "🚨 = Preisfehler-Verdacht (ungewöhnlich niedrig, Lieferung nicht sicher), 🔥 = Top-Deal, 💚 = guter Deal.\n\n"
        "Tipp: Kanal stummschalten und nur bei 🚨 reinschauen. Alle Links sind Affiliate-Links (Anzeige)."
    ),
    "promotion": [
        "Link zum Kanal in Instagram-Bio, Story-Highlight 'WhatsApp' und am Ende jedes Reels.",
        "QR-Code auf Pinterest-Pins der Board-Beschreibung und auf der Website (Footer + Deal-Seiten).",
        "Exklusiv-Mehrwert kommunizieren: Preisfehler-Verdacht zuerst im Kanal, dann auf anderen Plattformen.",
        "Wöchentlicher Rückblick 'Top 5 der Woche' als Grund zum Bleiben.",
        "Keine Kauf-Follower, keine Spam-Einladungen in fremden Gruppen.",
    ],
    "posting_rules": [
        "Nur Deals mit Score ≥ 75, Preis vor dem Posten im Dashboard erneut bestätigen.",
        "Erste Zeile immer 'Anzeige', Preis mit 'Stand'-Zeitstempel.",
        "Maximal 3 Beiträge am Tag in der Startphase.",
    ],
}


@router.get("/whatsapp")
def whatsapp_kit(_=Depends(viewer)):
    s = get_settings()
    return {**KIT, "invite_url": s.whatsapp_channel_invite_url,
            "qr_available": bool(s.whatsapp_channel_invite_url)}


@router.get("/whatsapp/qr.png")
def whatsapp_qr():
    url = get_settings().whatsapp_channel_invite_url
    if not url:
        raise HTTPException(404, "WHATSAPP_CHANNEL_INVITE_URL nicht gesetzt")
    img = qrcode.make(url, box_size=12, border=2).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return Response(buf.getvalue(), media_type="image/png")


@router.get("/profile.png")
def profile_image():
    """Profilbild 640×640 (WhatsApp/Telegram/Instagram)."""
    size = 640
    img = Image.new("RGB", (size, size), BLACK)
    d = ImageDraw.Draw(img)
    d.ellipse([20, 20, size - 20, size - 20], outline=NEON, width=18)
    f = _font(96)
    for text, y, color in (("DEAL", 200, WHITE), ("FEHLER", 300, NEON)):
        d.text(((size - d.textlength(text, font=f)) / 2, y), text, font=f, fill=color)
    sf = _font(34)
    t = "% PREISALARM"
    d.text(((size - d.textlength(t, font=sf)) / 2, 430), t, font=sf, fill=WHITE)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return Response(buf.getvalue(), media_type="image/png")
