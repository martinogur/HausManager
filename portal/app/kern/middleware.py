"""Middleware des Kerns: Audit-Benutzer und zusätzliche Sicherheits-Header."""

from .audit import loesche_audit_benutzer, setze_audit_benutzer


class AuditBenutzerMiddleware:
    """
    Setzt pro Request ``app.benutzer`` = E-Mail des angemeldeten Benutzers in der
    Datenbank-Sitzung und nach dem Request wieder auf ``''``. So steht in jedem
    ``audit_log``-Eintrag, wer die Änderung ausgelöst hat.

    Muss nach ``AuthenticationMiddleware`` stehen.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            setze_audit_benutzer(user.email)
        try:
            return self.get_response(request)
        finally:
            loesche_audit_benutzer()


# Nur Inhalte vom eigenen Server; keine CDNs, keine Einbettung in fremde Seiten.
# 'unsafe-inline' nur für Stile (Django-Admin nutzt vereinzelt style-Attribute).
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"


class SicherheitsHeaderMiddleware:
    """Ergänzt Content-Security-Policy und Permissions-Policy (falls nicht gesetzt)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        response.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        return response
