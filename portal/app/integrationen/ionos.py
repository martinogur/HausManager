"""IONOS-Postfach: Abruf per IMAP (imap.ionos.de:993, SSL) und Versand freigegebener Mails per SMTP
(smtp.ionos.de:465, SSL). Zugang: ``IONOS_MAIL_BENUTZER`` und ``IONOS_MAIL_PASSWORT`` (nur Umgebung).

* Abruf: liest die letzten 7 Tage mit BODY.PEEK (Mails bleiben ungelesen), Doppelimport verhindert die
  Datenbank über (postfach, message_id). Jeder Import erzeugt per Trigger das Ereignis ``email.eingang``.
* Versand: ausschließlich Datensätze mit Status „freigegeben“ (die Datenbank erlaubt diesen Status nur mit
  Freigabe durch eine Person).
"""

import email
import imaplib
import smtplib
import ssl
from datetime import timedelta
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import getaddresses, make_msgid, parsedate_to_datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from kommunikation.models import EmailProtokoll

from .http import env, protokollieren

IMAP_HOST, IMAP_PORT = "imap.ionos.de", 993
SMTP_HOST, SMTP_PORT = "smtp.ionos.de", 465
AUSZUG_ZEICHEN = 8000


def eingerichtet() -> bool:
    return bool(env("IONOS_MAIL_BENUTZER") and env("IONOS_MAIL_PASSWORT"))


def _text(nachricht: email.message.Message) -> str:
    teile = nachricht.walk() if nachricht.is_multipart() else [nachricht]
    for teil in teile:
        if teil.get_content_type() == "text/plain" and "attachment" not in str(teil.get("Content-Disposition", "")):
            roh = teil.get_payload(decode=True) or b""
            return roh.decode(teil.get_content_charset() or "utf-8", errors="replace")
    return ""


def _kopf(wert) -> str:
    return str(make_header(decode_header(wert))) if wert else ""


def nachricht_speichern(roh: bytes, postfach: str) -> EmailProtokoll | None:
    """Eine RFC-822-Nachricht als Eingang speichern; None bei Dublette."""
    n = email.message_from_bytes(roh)
    von = getaddresses([n.get("From", "")])[0][1].lower() or "unbekannt@invalid"
    an = [a.lower() for _, a in getaddresses(n.get_all("To", []) + n.get_all("Cc", [])) if a] or [postfach]
    try:
        empfangen = parsedate_to_datetime(n["Date"]) if n.get("Date") else timezone.now()
    except (TypeError, ValueError):
        empfangen = timezone.now()
    try:
        with transaction.atomic():
            return EmailProtokoll.objects.create(
                richtung="eingang", message_id=(n.get("Message-ID") or "").strip() or None,
                in_reply_to=(n.get("In-Reply-To") or "").strip() or None, postfach=postfach, von=von, an=an,
                betreff=_kopf(n.get("Subject"))[:500], text_auszug=_text(n)[:AUSZUG_ZEICHEN], empfangen_am=empfangen,
            )
    except IntegrityError:
        return None


def abrufen(imap_klasse=imaplib.IMAP4_SSL) -> dict:
    if not eingerichtet():
        return {"hinweis": "IONOS-Postfach nicht eingerichtet"}
    benutzer = env("IONOS_MAIL_BENUTZER")
    seit = (timezone.localdate() - timedelta(days=7)).strftime("%d-%b-%Y")
    neu = 0
    with imap_klasse(IMAP_HOST, IMAP_PORT, ssl_context=ssl.create_default_context()) as imap:
        imap.login(benutzer, env("IONOS_MAIL_PASSWORT"))
        imap.select("INBOX", readonly=True)
        _, daten = imap.uid("search", None, f"(SINCE {seit})")
        for uid in (daten[0] or b"").split():
            _, teile = imap.uid("fetch", uid, "(BODY.PEEK[])")
            roh = next((t[1] for t in teile if isinstance(t, tuple)), None)
            if roh and nachricht_speichern(roh, benutzer):
                neu += 1
    protokollieren("ionos", "import", "email", erfolgreich=True)
    return {"neu": neu}


def freigegebene_senden(smtp_klasse=smtplib.SMTP_SSL) -> dict:
    if not eingerichtet():
        return {"hinweis": "IONOS-Postfach nicht eingerichtet"}
    offen = list(EmailProtokoll.objects.filter(richtung="ausgang", status="freigegeben", freigegeben_von__isnull=False)[:20])
    if not offen:
        return {"gesendet": 0}
    benutzer = env("IONOS_MAIL_BENUTZER")
    gesendet = 0
    with smtp_klasse(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context()) as smtp:
        smtp.login(benutzer, env("IONOS_MAIL_PASSWORT"))
        for mail in offen:
            m = EmailMessage()
            m["From"], m["To"], m["Subject"] = benutzer, ", ".join(mail.an), mail.betreff or ""
            m["Message-ID"] = make_msgid(domain=benutzer.split("@")[-1])
            if mail.in_reply_to:
                m["In-Reply-To"] = m["References"] = mail.in_reply_to
            m.set_content(mail.entwurf_text or "")
            try:
                smtp.send_message(m)
            except smtplib.SMTPException as e:
                mail.status, mail.fehler = "fehler", f"{type(e).__name__}: {e}"[:2000]
                mail.save()
                protokollieren("ionos", "export", "email", lokale_id=mail.id, erfolgreich=False, fehler=mail.fehler)
                continue
            mail.status, mail.gesendet_am, mail.message_id = "gesendet", timezone.now(), m["Message-ID"]
            mail.save()
            protokollieren("ionos", "export", "email", lokale_id=mail.id, externe_id=m["Message-ID"], erfolgreich=True)
            gesendet += 1
    return {"gesendet": gesendet}
