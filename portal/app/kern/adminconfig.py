"""
Ersetzt die Standard-Admin-App, damit ``admin.site`` unsere Site-Klasse mit
Pflicht-2FA ist. Fach-Apps registrieren ihre Modelle weiterhin ganz normal
mit ``admin.site.register(...)`` oder ``@admin.register(...)``.

Diese Datei darf nichts importieren, was Modelle lädt (sie wird beim Start
vor der App-Registrierung gelesen).
"""

from django.contrib.admin.apps import AdminConfig


class PortalAdminConfig(AdminConfig):
    default_site = "kern.admin_site.PortalAdminSite"
