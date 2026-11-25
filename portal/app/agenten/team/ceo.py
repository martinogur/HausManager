"""CEO-Orchestrator: verteilt die Tagesarbeit, prüft Ergebnisse, berichtet an den Geschäftsführer."""

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from agenten.laufzeit import aufgabe
from agenten.models import AgentenAuftrag, Freigabe
from auftraege.models import Einsatz
from berichte import controlling
from vertrieb.models import Lead, OFFENE_STATUS

SCHEMA_BERICHT = {
    "type": "object",
    "properties": {
        "zusammenfassung": {"type": "string"},
        "entscheidungen": {"type": "array", "items": {"type": "string"}},
        "risiken": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["zusammenfassung", "entscheidungen", "risiken"],
    "additionalProperties": False,
}

TAGESARBEIT = (
    ("dispatch", "wiederkehrende_einsaetze", 3),
    ("sales", "wiedervorlagen", 4),
    ("finance", "zahlungen_pruefen", 5),
)


def lagebild() -> dict:
    heute = timezone.localdate()
    freigaben = Freigabe.objects.filter(status="offen")
    alt = freigaben.filter(erstellt_am__lt=timezone.now() - timedelta(hours=48)).count()
    return {
        "datum": heute.isoformat(),
        "freigaben_offen": freigaben.count(),
        "freigaben_aelter_48h": alt,
        "freigaben_nach_art": dict(freigaben.values_list("art").annotate(n=Count("id")).values_list("art", "n")),
        "eskalationen_offen": freigaben.filter(art="eskalation").count(),
        "agenten_fehler_24h": AgentenAuftrag.objects.filter(
            status__in=["fehlgeschlagen", "eskaliert"], beendet_am__gte=timezone.now() - timedelta(days=1)).count(),
        "einsaetze_heute": Einsatz.objects.filter(geplant_von__date=heute).exclude(status="ausgefallen").count(),
        "einsaetze_ohne_personal_48h": Einsatz.objects.filter(
            geplant_von__date__lte=heute + timedelta(days=2), geplant_von__date__gte=heute,
            status="geplant").filter(zuweisungen__isnull=True).count(),
        "wiedervorlagen_heute": Lead.objects.filter(status__in=OFFENE_STATUS, wiedervorlage_am__lte=heute).count(),
        "leads_a_offen": Lead.objects.filter(status__in=OFFENE_STATUS, prioritaet="A").count(),
        "kennzahlen_monat": controlling.kennzahlen(controlling.Zeitraum.monat(heute)),
    }


def _prioritaeten(l: dict) -> list[str]:
    p = []
    if l["eskalationen_offen"]:
        p.append(f"{l['eskalationen_offen']} Eskalation(en) entscheiden")
    if l["einsaetze_ohne_personal_48h"]:
        p.append(f"{l['einsaetze_ohne_personal_48h']} Einsatz/Einsätze in den nächsten 48 h ohne Personal")
    if l["freigaben_aelter_48h"]:
        p.append(f"{l['freigaben_aelter_48h']} Freigabe(n) warten länger als 48 h")
    if l["wiedervorlagen_heute"]:
        p.append(f"{l['wiedervorlagen_heute']} Wiedervorlage(n) im Vertrieb")
    if l["kennzahlen_monat"]["rechnungen_ueberfaellig"]:
        p.append(f"{l['kennzahlen_monat']['rechnungen_ueberfaellig']} überfällige Rechnung(en)")
    return p or ["Keine dringenden Punkte."]


@aufgabe("ceo", "tagesstart")
def tagesstart(ctx):
    """Täglich: Routineaufgaben an die Fachagenten verteilen, danach Lagebild und Prioritäten."""
    heute = timezone.localdate().isoformat()
    verteilt = []
    for agent_code, name, prio in TAGESARBEIT:
        ctx.delegieren(agent_code, name, idempotenz=f"tagesstart:{heute}:{agent_code}:{name}", prioritaet=prio)
        verteilt.append(f"{agent_code}/{name}")
    l = lagebild()
    return {"verteilt": verteilt, "prioritaeten": _prioritaeten(l), "lagebild": l}


@aufgabe("ceo", "wochenbericht")
def wochenbericht(ctx):
    """Montag: Bericht über die Vorwoche + laufenden Monat für den Geschäftsführer."""
    heute = timezone.localdate()
    vorwoche_start = heute - timedelta(days=heute.weekday() + 7)
    woche = controlling.kennzahlen(controlling.Zeitraum(vorwoche_start, vorwoche_start + timedelta(days=7)))
    monat = controlling.kennzahlen(controlling.Zeitraum.monat(heute))
    agenten = list(AgentenAuftrag.objects.filter(erstellt_am__date__gte=vorwoche_start)
                   .values("agent").annotate(gesamt=Count("id"), fehler=Count("id", filter=Q(status__in=["fehlgeschlagen", "eskaliert"])))
                   .order_by("agent"))
    l = lagebild()
    fakten = {"woche_ab": vorwoche_start.isoformat(), "woche": woche, "monat": monat,
              "pipeline": controlling.lead_pipeline(), "agenten": agenten, "prioritaeten": _prioritaeten(l)}

    def regel():
        eur = lambda c: f"{(c or 0) / 100:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
        return {
            "zusammenfassung": (f"Woche ab {vorwoche_start:%d.%m.}: Umsatz {eur(woche['umsatz_cent'])}, "
                                f"{woche['auftraege_abgeschlossen']} Aufträge abgeschlossen, {woche['anfragen_neu']} neue Anfragen, "
                                f"{woche['leads_neu']} neue Leads. Monat bisher: Umsatz {eur(monat['umsatz_cent'])}, "
                                f"Rohertrag {eur(monat['rohertrag_cent'])}, wiederkehrend {eur(monat['wiederkehrend_monat_cent'])}/Monat."),
            "entscheidungen": _prioritaeten(l),
            "risiken": [f"{monat['rechnungen_ueberfaellig']} überfällige Rechnung(en)"] if monat["rechnungen_ueberfaellig"] else [],
        }

    bericht, quelle = ctx.ki_oder_regel(
        regel, zweck="wochenbericht", schema=SCHEMA_BERICHT, effort="medium", max_tokens=3000,
        system=("Du bist der CEO-Orchestrator eines kleinen Hausmeisterbetriebs in Gütersloh und schreibst dem Inhaber "
                "einen kurzen Wochenbericht auf Deutsch: Zusammenfassung (max. 6 Sätze, nur Zahlen aus den Fakten), "
                "offene Entscheidungen, Risiken. Nichts erfinden; fehlende Daten als fehlend benennen."),
        eingabe=str(ctx_json(fakten)),
    )
    return {"bericht": bericht, "quelle": quelle, "fakten": fakten}


def ctx_json(wert):
    from agenten.laufzeit import _json

    return _json(wert)
