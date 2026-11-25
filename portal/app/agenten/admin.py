from django.contrib import admin

from stammdaten.felder import NurLesendAdminMixin

from .models import Agent, AgentenAuftrag, AgentenProtokoll, Automatisierung, Ereignis, Firmenparameter, Freigabe


@admin.register(Firmenparameter)
class FirmenparameterAdmin(admin.ModelAdmin):
    list_display = ("schluessel", "wert", "beschreibung", "geaendert_am")
    search_fields = ("schluessel", "beschreibung")
    readonly_fields = ("geaendert_am",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "aktiv", "modell", "tagesbudget_cent", "max_schritte", "max_laufzeit_sekunden", "max_versuche")
    list_editable = ("aktiv", "tagesbudget_cent")
    readonly_fields = ("code", "erstellt_am", "geaendert_am")

    def has_add_permission(self, request):
        return False   # Agenten entstehen im Code (agenten_sync)

    def has_delete_permission(self, request, obj=None):
        return False


class ProtokollInline(NurLesendAdminMixin, admin.TabularInline):
    model = AgentenProtokoll
    extra = 0


@admin.register(AgentenAuftrag)
class AgentenAuftragAdmin(NurLesendAdminMixin, admin.ModelAdmin):
    list_display = ("erstellt_am", "agent", "aufgabe", "status", "versuche", "tiefe", "kosten_cent", "ausgeloest_von")
    list_filter = ("status", "agent")
    search_fields = ("aufgabe", "ausgeloest_von", "fehler")
    inlines = [ProtokollInline]


@admin.register(Freigabe)
class FreigabeAdmin(NurLesendAdminMixin, admin.ModelAdmin):
    """Nur ansehen – entschieden wird in der Freigabe-Ansicht (mit Folgeaktion)."""
    list_display = ("freigabenummer", "titel", "art", "status", "prioritaet", "erstellt_am", "entschieden_von")
    list_filter = ("status", "art", "prioritaet")
    search_fields = ("freigabenummer", "titel")


@admin.register(Ereignis)
class EreignisAdmin(NurLesendAdminMixin, admin.ModelAdmin):
    list_display = ("id", "typ", "bezug_tabelle", "erstellt_am", "verarbeitet_am", "versuche", "fehler")
    list_filter = ("typ",)


@admin.register(Automatisierung)
class AutomatisierungAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "ausloeser", "aktiv", "letzter_lauf", "fehler_in_folge")
    list_editable = ("aktiv",)
    readonly_fields = ("code", "name", "beschreibung", "ausloeser", "letzter_lauf", "letzter_erfolg", "fehler_in_folge",
                       "letzter_fehler", "erstellt_am", "geaendert_am")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
