from django.contrib import admin

from .felder import euro
from .models import Ansprechpartner, Kunde, Leistung, Leistungsvereinbarung, Objekt

ZEITSTEMPEL = ("erstellt_am", "geaendert_am")


class AnsprechpartnerInline(admin.StackedInline):
    model = Ansprechpartner
    extra = 0
    fields = (
        ("anrede", "vorname", "nachname"),
        ("funktion", "ist_hauptkontakt"),
        ("email", "telefon", "mobil"),
        ("email_einwilligung", "einwilligung_quelle"),
    )


class ObjektInline(admin.TabularInline):
    model = Objekt
    extra = 0
    fields = ("objektnummer", "bezeichnung", "strasse", "hausnummer", "plz", "ort")
    readonly_fields = ("objektnummer",)
    show_change_link = True


@admin.register(Kunde)
class KundeAdmin(admin.ModelAdmin):
    list_display = ("kundennummer", "name", "typ", "status", "plz", "ort", "telefon")
    list_filter = ("status", "typ")
    search_fields = ("kundennummer", "name", "ort", "plz", "email", "ansprechpartner__nachname")
    readonly_fields = ("kundennummer",) + ZEITSTEMPEL
    fieldsets = (
        (None, {"fields": ("kundennummer", "name", ("typ", "status"))}),
        ("Adresse & Kontakt", {"fields": ("strasse", ("plz", "ort"), ("telefon", "email"), "webseite")}),
        ("Sonstiges", {"fields": ("quelle", "notizen")}),
        (
            "Schnittstellen",
            {"fields": ("hubspot_company_id", "lexware_contact_id"), "classes": ("collapse",)},
        ),
        ("Protokoll", {"fields": ZEITSTEMPEL, "classes": ("collapse",)}),
    )
    inlines = (AnsprechpartnerInline, ObjektInline)


@admin.register(Ansprechpartner)
class AnsprechpartnerAdmin(admin.ModelAdmin):
    list_display = ("nachname", "vorname", "kunde", "funktion", "email", "telefon", "ist_hauptkontakt", "hat_einwilligung")
    list_filter = ("ist_hauptkontakt",)
    search_fields = ("nachname", "vorname", "email", "kunde__name")
    autocomplete_fields = ("kunde",)
    readonly_fields = ZEITSTEMPEL

    @admin.display(boolean=True, description="E-Mail-Einwilligung")
    def hat_einwilligung(self, obj):
        return obj.email_einwilligung is not None


class LeistungsvereinbarungInline(admin.TabularInline):
    model = Leistungsvereinbarung
    extra = 0
    fields = ("leistung", "intervall", "wochentag", "menge", "preis_netto_cent", "gueltig_von", "gueltig_bis")
    autocomplete_fields = ("leistung",)
    show_change_link = True


@admin.register(Objekt)
class ObjektAdmin(admin.ModelAdmin):
    list_display = ("objektnummer", "bezeichnung", "kunde", "strasse", "hausnummer", "plz", "ort", "wohneinheiten")
    list_filter = ("ort", "aufzug")
    search_fields = ("objektnummer", "bezeichnung", "strasse", "plz", "ort", "kunde__name")
    autocomplete_fields = ("kunde",)
    readonly_fields = ("objektnummer",) + ZEITSTEMPEL
    fieldsets = (
        (None, {"fields": ("objektnummer", "kunde", "bezeichnung")}),
        ("Adresse", {"fields": (("strasse", "hausnummer"), ("plz", "ort"), "entfernung_km")}),
        (
            "Gebäude",
            {
                "fields": (
                    ("wohneinheiten", "gewerbeeinheiten"),
                    ("treppenhaeuser", "etagen", "aufzug"),
                    ("gehweg_meter", "gruenflaeche_qm"),
                    "zugang_hinweise",
                )
            },
        ),
        ("Schnittstellen", {"fields": ("craftnote_project_id",), "classes": ("collapse",)}),
        ("Protokoll", {"fields": ZEITSTEMPEL, "classes": ("collapse",)}),
    )
    inlines = (LeistungsvereinbarungInline,)


@admin.register(Leistung)
class LeistungAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "einheit", "preis", "ust_satz", "betriebskostenart", "aktiv")
    list_filter = ("aktiv", "betriebskostenart")
    search_fields = ("code", "name")
    readonly_fields = ZEITSTEMPEL

    @admin.display(description="Preis netto", ordering="preis_netto_cent")
    def preis(self, obj):
        return euro(obj.preis_netto_cent)


@admin.register(Leistungsvereinbarung)
class LeistungsvereinbarungAdmin(admin.ModelAdmin):
    list_display = ("objekt", "leistung", "intervall", "wochentag", "preis", "gueltig_von", "gueltig_bis", "standard_mitarbeiter")
    list_filter = ("intervall", "leistung")
    search_fields = ("objekt__bezeichnung", "objekt__objektnummer", "leistung__name", "leistung__code")
    autocomplete_fields = ("objekt", "leistung", "standard_mitarbeiter")
    readonly_fields = ZEITSTEMPEL

    @admin.display(description="Preis netto", ordering="preis_netto_cent")
    def preis(self, obj):
        return euro(obj.preis_netto_cent)
