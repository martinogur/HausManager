from django.contrib import admin

from .models import EmailProtokoll


@admin.register(EmailProtokoll)
class EmailProtokollAdmin(admin.ModelAdmin):
    list_display = ("empfangen_am", "richtung", "status", "von", "betreff", "kunde", "anfrage")
    list_filter = ("status", "richtung", "postfach")
    search_fields = ("betreff", "von", "message_id", "kunde__name", "text_auszug")
    raw_id_fields = ("kunde", "ansprechpartner", "anfrage", "bewerbung", "antwort_auf")
    # Freigabe und Versand laufen später über eigene Portal-Aktionen (mit Protokoll), nicht per Formular
    readonly_fields = (
        "message_id",
        "in_reply_to",
        "ki_zusammenfassung",
        "freigegeben_von",
        "freigegeben_am",
        "gesendet_am",
        "fehler",
        "erstellt_am",
        "geaendert_am",
    )
    date_hierarchy = "empfangen_am"
