from django.contrib import admin

from .models import SocialBeitrag


@admin.register(SocialBeitrag)
class SocialBeitragAdmin(admin.ModelAdmin):
    list_display = ("geplant_fuer", "plattform", "format", "thema", "status", "erstellt_von")
    list_filter = ("plattform", "format", "status")
    search_fields = ("thema", "text")
    date_hierarchy = "geplant_fuer"
    # Freigabe nur über die Freigabe-Ansicht (setzt freigegeben_von/-am)
    readonly_fields = ("freigabe", "freigegeben_von", "freigegeben_am", "veroeffentlicht_am", "externe_id", "kennzahlen",
                       "erstellt_von", "erstellt_am", "geaendert_am")
