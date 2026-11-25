"""
Zentrale URL-Tabelle.

URL-Namen (für {% url %} / reverse):
  berichte:dashboard, berichte:kennzahlen
  konten:anmelden, konten:abmelden, konten:zwei_faktor_einrichten, konten:zwei_faktor_pruefen
  kern:gesund
  admin:index (Pfad über DJANGO_ADMIN_PFAD, Standard /admin/)
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("berichte.urls")),
    path("", include("konten.urls")),
    path("", include("kern.urls")),
    path("", include("cockpit.urls")),
    path(settings.ADMIN_PFAD, admin.site.urls),
]

# Eigene Fehlerseiten (Vorlagen 403.html, 404.html, 500.html) nutzt Django automatisch.
