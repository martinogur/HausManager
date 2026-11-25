from django.contrib import admin

from .models import Lead, LeadKontakt


class KontaktInline(admin.TabularInline):
    model = LeadKontakt
    extra = 0
    readonly_fields = ("kanal", "richtung", "zeitpunkt", "zusammenfassung", "ergebnis", "durch", "freigabe")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False   # Kontakte werden über die Akquise-Ansicht dokumentiert (Rechtsprüfung)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("leadnummer", "firma", "zielgruppe", "ort", "prioritaet", "score", "status", "wiedervorlage_am")
    list_filter = ("status", "prioritaet", "zielgruppe", "im_einsatzgebiet")
    search_fields = ("leadnummer", "firma", "ort", "ansprechpartner", "externe_ref")
    readonly_fields = ("leadnummer", "score", "prioritaet", "score_begruendung", "widerspruch_am", "erstellt_am", "geaendert_am")
    inlines = [KontaktInline]
