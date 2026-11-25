from django.contrib import admin

from stammdaten.felder import NurLesendAdminMixin

from .models import KiAufruf


@admin.register(KiAufruf)
class KiAufrufAdmin(NurLesendAdminMixin, admin.ModelAdmin):
    list_display = ("erstellt_am", "zweck", "modell", "erfolgreich", "eingabe_tokens", "ausgabe_tokens", "kosten_cent", "bezug_tabelle")
    list_filter = ("zweck", "modell", "erfolgreich")
    search_fields = ("zweck", "modell", "bezug_tabelle", "fehler")
    date_hierarchy = "erstellt_am"
