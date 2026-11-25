"""Automations-Agent: Überwachung von Automatisierungen, Ereignissen, Agenten und KI-Kosten."""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from agenten import ki
from agenten.laufzeit import aufgabe
from agenten.models import AgentenAuftrag, Automatisierung, Ereignis, Firmenparameter


@aufgabe("automation", "ueberwachung")
def ueberwachung(ctx):
    jetzt = timezone.now()
    probleme = []
    for a in Automatisierung.objects.filter(aktiv=True, fehler_in_folge__gte=3):
        probleme.append(("automatisierungen", None, f"Automatisierung „{a.name}“: {a.fehler_in_folge} Fehler in Folge – {a.letzter_fehler}"))
    stau = Ereignis.objects.filter(verarbeitet_am__isnull=True, erstellt_am__lt=jetzt - timedelta(minutes=30)).count()
    if stau:
        probleme.append(("ereignisse", None, f"{stau} Ereignis(se) seit über 30 Minuten unverarbeitet – läuft der Worker?"))
    haengt = AgentenAuftrag.objects.filter(status="laeuft", gesperrt_bis__lt=jetzt - timedelta(minutes=10)).count()
    if haengt:
        probleme.append(("agenten_auftraege", None, f"{haengt} Agentenauftrag/-aufträge hängen"))
    wartet = AgentenAuftrag.objects.filter(status="wartend", faellig_ab__lt=jetzt - timedelta(hours=1)).count()
    if wartet:
        probleme.append(("agenten_auftraege", None, f"{wartet} Agentenauftrag/-aufträge warten seit über 1 h"))
    try:
        budget = Decimal(str(Firmenparameter.objects.get(schluessel="ki_tagesbudget_gesamt_cent").wert))
    except Firmenparameter.DoesNotExist:
        budget = Decimal(200)
    verbraucht = ki.heutige_kosten()
    if budget and verbraucht >= budget * Decimal("0.8"):
        probleme.append(("ki_aufrufe", None, f"KI-Kosten heute {verbraucht:.2f} von {budget} Cent (≥ 80 %)"))
    for tabelle, _, text in probleme:
        ctx.freigabe_anfordern(art="eskalation", titel=text[:300], begruendung=text, prioritaet="hoch",
                               vorschlag={"quelle": tabelle, "zeit": jetzt.isoformat()})
    return {"ok": not probleme, "probleme": [p[2] for p in probleme], "ki_kosten_heute_cent": str(verbraucht)}
