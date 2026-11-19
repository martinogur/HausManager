"""E-Mail-Versand über SMTP. Zugangsdaten kommen aus Umgebungsvariablen (.env)."""
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid


def konfiguriert():
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER"))


def senden(empfaenger, betreff, text):
    """Sendet eine E-Mail. Wirft eine Exception bei Fehlern."""
    if not konfiguriert():
        raise RuntimeError("SMTP ist nicht konfiguriert (SMTP_HOST/SMTP_USER/SMTP_PASS in .env setzen).")
    absender = os.environ.get("SMTP_FROM") or os.environ["SMTP_USER"]
    msg = EmailMessage()
    msg["From"] = absender
    msg["To"] = empfaenger
    msg["Subject"] = betreff
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.set_content(text)

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASS", ""))
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASS", ""))
            s.send_message(msg)
