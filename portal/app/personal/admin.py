from django.contrib import admin

from .models import Abwesenheit, Arbeitszeit, Bewerbung, Mitarbeiter, Qualifikation, Stelle, Verfuegbarkeit

ZEITSTEMPEL = ("erstellt_am", "geaendert_am")


def _ist_admin(request):
    return getattr(request.user, "rolle", None) == "admin"


class VerfuegbarkeitInline(admin.TabularInline):
    model = Verfuegbarkeit
    extra = 0


class AbwesenheitInline(admin.TabularInline):
    model = Abwesenheit
    extra = 0


@admin.register(Mitarbeiter)
class MitarbeiterAdmin(admin.ModelAdmin):
    list_display = ("personalnummer", "nachname", "vorname", "beschaeftigung", "wochenstunden_soll", "telefon", "aktiv_jetzt", "qualifikationen_liste")
    list_filter = ("beschaeftigung", "fuehrerschein")
    search_fields = ("personalnummer", "vorname", "nachname", "email")
    readonly_fields = ("personalnummer", "einsaetze_heute") + ZEITSTEMPEL
    inlines = (VerfuegbarkeitInline, AbwesenheitInline)

    # Stundenlohn: nur Rolle admin (auch nicht im Formular oder in der Ansicht)
    def get_exclude(self, request, obj=None):
        exclude = list(super().get_exclude(request, obj) or [])
        if not _ist_admin(request):
            exclude.append("stundenlohn_cent")
        return exclude

    def get_fields(self, request, obj=None):
        felder = list(super().get_fields(request, obj))
        if not _ist_admin(request) and "stundenlohn_cent" in felder:
            felder.remove("stundenlohn_cent")
        return felder

    def get_readonly_fields(self, request, obj=None):
        # Benutzerkonten verknüpfen darf nur admin (Benutzerverwaltung)
        felder = tuple(super().get_readonly_fields(request, obj))
        return felder if _ist_admin(request) else felder + ("benutzer",)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("qualifikationen__qualifikation")

    @admin.display(boolean=True, description="Aktiv")
    def aktiv_jetzt(self, obj):
        return obj.austritt is None

    @admin.display(description="Qualifikationen")
    def qualifikationen_liste(self, obj):
        return ", ".join(q.qualifikation.name for q in obj.qualifikationen.all()) or "–"

    @admin.display(description="Einsätze heute")
    def einsaetze_heute(self, obj):
        from django.utils import timezone

        if not obj.pk:
            return "–"
        heute = timezone.localdate()
        zuweisungen = obj.einsatz_zuweisungen.filter(einsatz__geplant_von__date=heute).select_related("einsatz__auftrag")
        return "; ".join(str(z.einsatz) for z in zuweisungen) or "keine"


@admin.register(Qualifikation)
class QualifikationAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Stelle)
class StelleAdmin(admin.ModelAdmin):
    list_display = ("titel", "beschaeftigung", "offen", "erstellt_am")
    list_filter = ("offen", "beschaeftigung")
    search_fields = ("titel",)
    readonly_fields = ("erstellt_am",)


@admin.register(Bewerbung)
class BewerbungAdmin(admin.ModelAdmin):
    list_display = ("bewerbungsnummer", "nachname", "vorname", "stelle", "status", "eingegangen_am", "loeschen_ab")
    list_filter = ("status", "stelle")
    search_fields = ("bewerbungsnummer", "vorname", "nachname", "email", "wohnort")
    readonly_fields = ("bewerbungsnummer", "eingegangen_am", "loeschen_ab", "geaendert_am", "ki_zusammenfassung")
    date_hierarchy = "eingegangen_am"


@admin.register(Arbeitszeit)
class ArbeitszeitAdmin(admin.ModelAdmin):
    list_display = ("mitarbeiter", "beginn", "ende", "pause_minuten", "stunden", "einsatz", "bestaetigt")
    list_filter = ("mitarbeiter",)
    search_fields = ("mitarbeiter__nachname", "mitarbeiter__vorname", "taetigkeit")
    autocomplete_fields = ("mitarbeiter", "einsatz")
    readonly_fields = ("bestaetigt_von", "bestaetigt_am") + ZEITSTEMPEL
    date_hierarchy = "beginn"
    list_select_related = ("mitarbeiter", "einsatz__auftrag")

    @admin.display(boolean=True, description="Bestätigt")
    def bestaetigt(self, obj):
        return obj.bestaetigt_am is not None

