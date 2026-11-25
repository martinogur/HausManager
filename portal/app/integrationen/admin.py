from django.contrib import admin

from stammdaten.felder import NurLesendAdminMixin

from .models import AuditEintrag, SyncProtokoll


@admin.register(SyncProtokoll)
class SyncProtokollAdmin(NurLesendAdminMixin, admin.ModelAdmin):
    list_display = ("erstellt_am", "system", "richtung", "objekt_typ", "erfolgreich", "http_status", "externe_id")
    list_filter = ("system", "richtung", "erfolgreich")
    search_fields = ("objekt_typ", "externe_id", "idempotenz_schluessel", "fehler")
    date_hierarchy = "erstellt_am"


@admin.register(AuditEintrag)
class AuditEintragAdmin(NurLesendAdminMixin, admin.ModelAdmin):
    list_display = ("zeitpunkt", "aktion", "tabelle", "datensatz_id", "benutzer")
    list_filter = ("aktion", "tabelle")
    search_fields = ("tabelle", "benutzer")
    date_hierarchy = "zeitpunkt"
    show_full_result_count = False
