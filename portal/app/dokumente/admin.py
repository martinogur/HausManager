from django.contrib import admin

from .models import Dokument, Foto


@admin.register(Dokument)
class DokumentAdmin(admin.ModelAdmin):
    list_display = ("dateiname", "kategorie", "mime_typ", "groesse", "kunde", "objekt", "einsatz", "erstellt_am", "loeschen_ab")
    list_filter = ("kategorie", "mime_typ")
    search_fields = ("dateiname", "sha256", "kunde__name", "objekt__bezeichnung")
    raw_id_fields = ("kunde", "objekt", "auftrag", "einsatz", "mitarbeiter", "bewerbung")
    readonly_fields = ("sha256", "speicher_schluessel", "groesse_bytes", "hochgeladen_von", "erstellt_am")
    date_hierarchy = "erstellt_am"

    @admin.display(description="Größe", ordering="groesse_bytes")
    def groesse(self, obj):
        kb = obj.groesse_bytes / 1024
        return f"{kb / 1024:.1f} MB".replace(".", ",") if kb >= 1024 else f"{kb:.0f} KB"


@admin.register(Foto)
class FotoAdmin(admin.ModelAdmin):
    list_display = ("dokument", "typ", "einsatz", "aufgenommen_am")
    list_filter = ("typ",)
    search_fields = ("dokument__dateiname", "beschreibung")
    raw_id_fields = ("dokument", "einsatz")
