from django.contrib import admin
from django.utils import timezone

from dokumente.models import Foto
from stammdaten.felder import euro

from .models import Anfrage, Angebot, Angebotsposition, Auftrag, Einsatz, Rechnung

ZEITSTEMPEL = ("erstellt_am", "geaendert_am")


@admin.register(Anfrage)
class AnfrageAdmin(admin.ModelAdmin):
    list_display = ("anfragenummer", "eingegangen_am", "kanal", "betreff", "kunde", "status")
    list_filter = ("status", "kanal")
    search_fields = ("anfragenummer", "betreff", "kunde__name", "ki_zusammenfassung")
    autocomplete_fields = ("kunde", "ansprechpartner", "objekt")
    readonly_fields = ("anfragenummer", "eingegangen_am", "geaendert_am")
    date_hierarchy = "eingegangen_am"


class AngebotspositionInline(admin.TabularInline):
    model = Angebotsposition
    extra = 0
    fields = ("pos", "leistung", "beschreibung", "menge", "einheit", "einzelpreis_netto_cent", "intervall", "gesamt")
    readonly_fields = ("gesamt",)
    autocomplete_fields = ("leistung",)

    @admin.display(description="Gesamt netto")
    def gesamt(self, obj):
        return euro(obj.gesamt_netto_cent) if obj.pk else "–"


@admin.register(Angebot)
class AngebotAdmin(admin.ModelAdmin):
    list_display = ("angebotsnummer", "kunde", "objekt", "status", "summe", "gueltig_bis", "freigegeben_am")
    list_filter = ("status",)
    search_fields = ("angebotsnummer", "kunde__name", "objekt__bezeichnung")
    autocomplete_fields = ("kunde", "objekt", "anfrage")
    readonly_fields = ("angebotsnummer", "summe", "freigegeben_von", "freigegeben_am") + ZEITSTEMPEL
    list_select_related = ("kunde", "objekt")
    fieldsets = (
        (None, {"fields": ("angebotsnummer", "kunde", "objekt", "anfrage", "status")}),
        ("Konditionen", {"fields": ("gueltig_bis", "laufzeit_monate", "summe")}),
        ("Freigabe & Versand", {"fields": ("freigegeben_von", "freigegeben_am", "versendet_am")}),
        ("Schnittstellen", {"fields": ("lexware_quotation_id",), "classes": ("collapse",)}),
        ("Protokoll", {"fields": ZEITSTEMPEL, "classes": ("collapse",)}),
    )
    inlines = (AngebotspositionInline,)

    @admin.display(description="Summe netto", ordering="summe_netto_cent")
    def summe(self, obj):
        return euro(obj.summe_netto_cent) if obj.pk else "–"


class EinsatzInline(admin.TabularInline):
    model = Einsatz
    extra = 0
    fields = ("geplant_von", "geplant_bis", "status")
    show_change_link = True


@admin.register(Auftrag)
class AuftragAdmin(admin.ModelAdmin):
    list_display = ("auftragsnummer", "titel", "kunde", "objekt", "status", "faellig_am")
    list_filter = ("status",)
    search_fields = ("auftragsnummer", "titel", "kunde__name", "objekt__bezeichnung", "objekt__strasse")
    autocomplete_fields = ("kunde", "objekt", "angebot", "leistungsvereinbarung")
    readonly_fields = ("auftragsnummer",) + ZEITSTEMPEL
    list_select_related = ("kunde", "objekt")
    inlines = (EinsatzInline,)


class FotoInline(admin.TabularInline):
    model = Foto
    extra = 0
    fields = ("dokument", "typ", "aufgenommen_am", "beschreibung")
    raw_id_fields = ("dokument",)


@admin.register(Einsatz)
class EinsatzAdmin(admin.ModelAdmin):
    list_display = ("geplant_von", "geplant_bis", "auftrag", "objekt", "status", "mitarbeiter_liste")
    list_filter = ("status", "zuweisungen__mitarbeiter")
    search_fields = ("auftrag__auftragsnummer", "auftrag__titel", "auftrag__objekt__bezeichnung", "auftrag__objekt__strasse")
    autocomplete_fields = ("auftrag", "erzeugt_aus")
    readonly_fields = ("mitarbeiter_liste", "ki_auswertung") + ZEITSTEMPEL
    date_hierarchy = "geplant_von"
    list_select_related = ("auftrag__objekt",)
    inlines = (FotoInline,)

    def get_queryset(self, request):
        return (
            Einsatz.objects.fuer_benutzer(request.user)
            .select_related("auftrag__objekt")
            .prefetch_related("zuweisungen__mitarbeiter")
        )

    @admin.display(description="Objekt", ordering="auftrag__objekt__bezeichnung")
    def objekt(self, obj):
        return obj.auftrag.objekt

    @admin.display(description="Mitarbeiter")
    def mitarbeiter_liste(self, obj):
        # Zuweisungen haben einen zusammengesetzten Primärschlüssel; Djangos Admin kann sie
        # (Stand 5.2) nicht bearbeiten. Pflege daher später über die Einsatzplanung im Portal.
        return ", ".join(str(z.mitarbeiter) for z in obj.zuweisungen.all()) or "–"


@admin.register(Rechnung)
class RechnungAdmin(admin.ModelAdmin):
    list_display = ("rechnungsnummer", "kunde", "auftrag", "status", "rechnungsdatum", "faellig_am", "netto", "brutto", "ueberfaellig")
    list_filter = ("status",)
    search_fields = ("rechnungsnummer", "kunde__name", "auftrag__auftragsnummer")
    autocomplete_fields = ("kunde", "auftrag")
    readonly_fields = ZEITSTEMPEL
    date_hierarchy = "rechnungsdatum"
    list_select_related = ("kunde", "auftrag")

    @admin.display(description="Netto", ordering="summe_netto_cent")
    def netto(self, obj):
        return euro(obj.summe_netto_cent)

    @admin.display(description="Brutto", ordering="summe_brutto_cent")
    def brutto(self, obj):
        return euro(obj.summe_brutto_cent)

    @admin.display(boolean=True, description="Überfällig")
    def ueberfaellig(self, obj):
        return bool(obj.faellig_am and not obj.bezahlt_am and obj.faellig_am < timezone.localdate())
