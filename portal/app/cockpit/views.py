"""Steuerungsoberfläche: Freigaben, KI-Agenten, Automatisierungen, Akquise, Angebotsrechner, Aufträge,
Controlling, Marketing und die mobile Einsatzansicht der Mitarbeiter.

Rechte: Büro/Admin für alles außer der Einsatzansicht; Mitarbeiter sehen nur eigene Einsätze
(``Einsatz.objects.fuer_benutzer``). Admin-only: Agenten/Automatisierungen ein- und ausschalten.
"""

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, connection, transaction
from django.db.models import Count, Q, Sum
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from agenten import automatisierung, freigaben, ki, laufzeit
from agenten.models import Agent, AgentenAuftrag, Automatisierung, Freigabe
from auftraege import status as auftragsstatus
from auftraege.models import Auftrag, Auftragsstatus, Einsatz
from berichte import controlling
from dokumente.models import Foto
from konten.rechte import ist_admin, rolle_erforderlich
from marketing.models import Beitragsstatus, SocialBeitrag
from personal.models import Arbeitszeit, Mitarbeiter
from stammdaten.models import Objekt
from vertrieb import dienste, kalkulation
from vertrieb.models import Kontaktkanal, Lead, Leadprioritaet, Leadstatus, Zielgruppe

from . import fotos

#: Aufgaben, die das Büro von Hand starten darf (alles andere läuft über Ereignisse/Zeitpläne)
MANUELLE_AUFGABEN = [
    ("ceo", "tagesstart", "Tagesstart jetzt ausführen"),
    ("ceo", "wochenbericht", "Wochenbericht erstellen"),
    ("social", "wochenplan", "Instagram-Wochenplan erstellen"),
    ("seo", "google_beitraege", "Google-Beitrag planen"),
    ("marketing", "monatsplan", "Marketing-Monatsplan"),
    ("lead_research", "bestand_importieren", "Lead-Bestand importieren"),
    ("sales", "wiedervorlagen", "Wiedervorlagen prüfen"),
    ("dispatch", "wiederkehrende_einsaetze", "Wiederkehrende Einsätze planen"),
    ("finance", "zahlungen_pruefen", "Zahlungen prüfen"),
    ("automation", "ueberwachung", "Systemprüfung"),
]


def _seite(request, qs, pro_seite=25):
    return Paginator(qs, pro_seite).get_page(request.GET.get("seite"))


# ============================================================================= Menü (Handy)
@rolle_erforderlich("buero")
def menue(request):
    return render(request, "cockpit/menue.html")


# ============================================================================= Freigaben
@rolle_erforderlich("buero")
def freigaben_liste(request):
    status = request.GET.get("status", "offen")
    art = request.GET.get("art", "")
    qs = Freigabe.objects.select_related("entschieden_von", "agenten_auftrag").order_by(
        "-prioritaet" if status == "offen" else "-erstellt_am", "erstellt_am")
    if status:
        qs = qs.filter(status=status)
    if art:
        qs = qs.filter(art=art)
    reihenfolge = {"dringend": 0, "hoch": 1, "normal": 2, "niedrig": 3}
    seite = _seite(request, sorted(qs, key=lambda f: (reihenfolge[f.prioritaet], f.erstellt_am)) if status == "offen" else qs)
    zaehler = dict(Freigabe.objects.filter(status="offen").values_list("art").annotate(n=Count("id")))
    return render(request, "cockpit/freigaben.html", {
        "seite": seite, "status": status, "art": art, "arten": Freigabe._meta.get_field("art").choices,
        "zaehler": zaehler,
    })


@rolle_erforderlich("buero")
def freigaben_detail(request, pk):
    f = get_object_or_404(Freigabe, pk=pk)
    if request.method == "POST":
        entscheidung = request.POST.get("entscheidung")
        if entscheidung not in ("freigeben", "ablehnen"):
            raise PermissionDenied("Ungültige Entscheidung")
        aenderung = {"text": request.POST["text"]} if "text" in request.POST and "text" in f.vorschlag else None
        try:
            freigaben.entscheiden(f, request.user, freigeben=entscheidung == "freigeben",
                                  kommentar=request.POST.get("kommentar", "").strip(), vorschlag=aenderung)
        except (ValueError, IntegrityError) as e:
            messages.error(request, f"Nicht möglich: {e}")
            return redirect("cockpit:freigaben_detail", pk=f.pk)
        messages.success(request, f"{f.freigabenummer} {'freigegeben' if entscheidung == 'freigeben' else 'abgelehnt'}.")
        naechste = Freigabe.objects.filter(status="offen").order_by("erstellt_am").first()
        return redirect("cockpit:freigaben_detail", pk=naechste.pk) if naechste else redirect("cockpit:freigaben")
    return render(request, "cockpit/freigabe_detail.html", {"f": f, "vorschlag_text": f.vorschlag.get("text")})


# ============================================================================= KI-Agenten
@rolle_erforderlich("buero")
def agenten(request):
    laufzeit.register_laden()
    seit = timezone.now() - timedelta(days=7)
    statistik = {z["agent"]: z for z in AgentenAuftrag.objects.filter(erstellt_am__gte=seit).values("agent").annotate(
        gesamt=Count("id"), erledigt=Count("id", filter=Q(status="erledigt")),
        fehler=Count("id", filter=Q(status__in=["fehlgeschlagen", "eskaliert"])), kosten=Sum("kosten_cent"))}
    zeilen = []
    for a in Agent.objects.all():
        d = laufzeit.REGISTER.get(a.code)
        zeilen.append({"agent": a, "def": d, "stat": statistik.get(a.code, {}), "kosten_heute": ki.heutige_kosten(a.code)})
    return render(request, "cockpit/agenten.html", {
        "zeilen": zeilen, "manuell": MANUELLE_AUFGABEN, "ki_aktiv": ki.ki_eingerichtet(),
        "kosten_heute": ki.heutige_kosten(), "letzte": AgentenAuftrag.objects.select_related("agent")[:30],
        "ist_admin": ist_admin(request.user),
    })


@require_POST
@rolle_erforderlich("buero")
def agenten_starten(request):
    agent_code, aufgabe_name = request.POST.get("agent"), request.POST.get("aufgabe")
    if (agent_code, aufgabe_name) not in {(a, b) for a, b, _ in MANUELLE_AUFGABEN}:
        raise PermissionDenied("Diese Aufgabe kann nicht von Hand gestartet werden.")
    a = laufzeit.beauftragen(agent_code, aufgabe_name, {}, ausgeloest_von=f"benutzer:{request.user.email}", prioritaet=2)
    a = laufzeit.sofort_ausfuehren(a)
    automatisierung.ereignisse_verarbeiten(50)
    stufe = messages.success if a.status == "erledigt" else messages.warning
    stufe(request, f"{a.agent.name} / {aufgabe_name}: {a.get_status_display()}")
    return redirect("cockpit:agenten_auftrag", pk=a.pk)


@require_POST
@rolle_erforderlich("admin")
def agenten_schalten(request, code):
    a = get_object_or_404(Agent, code=code)
    a.aktiv = not a.aktiv
    a.save()
    messages.success(request, f"{a.name} ist jetzt {'aktiv' if a.aktiv else 'pausiert'}.")
    return redirect("cockpit:agenten")


@rolle_erforderlich("buero")
def agenten_auftrag(request, pk):
    a = get_object_or_404(AgentenAuftrag.objects.select_related("agent", "eltern"), pk=pk)
    return render(request, "cockpit/agenten_auftrag.html", {
        "a": a, "protokoll": a.protokoll.all(), "kinder": a.unterauftraege.select_related("agent"),
        "freigaben": a.freigaben.all(), "ki_aufrufe": a.ki_aufrufe.all(),
    })


# ============================================================================= Automatisierungen
@rolle_erforderlich("buero")
def automatisierungen(request):
    automatisierung.laden()
    zeilen = []
    for a in Automatisierung.objects.all():
        laeufe = a.laeufe.order_by("-gestartet_am")[:5]
        zeilen.append({"a": a, "laeufe": laeufe, "zeitplan": a.ausloeser.startswith("zeitplan:")})
    offene = connection.cursor()
    with offene as c:
        c.execute("SELECT count(*), min(erstellt_am) FROM ereignisse WHERE verarbeitet_am IS NULL")
        anzahl, aelteste = c.fetchone()
    return render(request, "cockpit/automatisierungen.html", {
        "zeilen": zeilen, "ereignisse_offen": anzahl, "aelteste": aelteste, "ist_admin": ist_admin(request.user),
    })


@require_POST
@rolle_erforderlich("admin")
def automatisierungen_schalten(request, code):
    a = get_object_or_404(Automatisierung, code=code)
    a.aktiv = not a.aktiv
    a.save()
    messages.success(request, f"„{a.name}“ ist jetzt {'aktiv' if a.aktiv else 'pausiert'}.")
    return redirect("cockpit:automatisierungen")


# ============================================================================= Akquise
@rolle_erforderlich("buero")
def akquise(request):
    qs = Lead.objects.all()
    status, prio, suche = request.GET.get("status", "offen"), request.GET.get("prio", ""), request.GET.get("q", "").strip()
    if status == "offen":
        qs = qs.exclude(status__in=["gewonnen", "verloren", "gesperrt"])
    elif status:
        qs = qs.filter(status=status)
    if prio:
        qs = qs.filter(prioritaet=prio)
    if suche:
        qs = qs.filter(Q(firma__icontains=suche) | Q(ort__icontains=suche) | Q(leadnummer__icontains=suche) |
                       Q(ansprechpartner__icontains=suche))
    pipeline = {s: 0 for s, _ in Leadstatus.choices}
    for zeile in Lead.objects.values("status").annotate(n=Count("id")):
        pipeline[zeile["status"]] = zeile["n"]
    return render(request, "cockpit/akquise.html", {
        "seite": _seite(request, qs.order_by("prioritaet", "-score", "firma")),
        "status": status, "prio": prio, "q": suche, "stati": Leadstatus.choices, "prios": Leadprioritaet.choices,
        "pipeline": [(Leadstatus(s).label, n, s) for s, n in pipeline.items()],
        "faellig": Lead.objects.filter(wiedervorlage_am__lte=timezone.localdate()).exclude(
            status__in=["gewonnen", "verloren", "gesperrt"]).count(),
        "zielgruppen": Zielgruppe.choices,
    })


def _euro_cent(text: str) -> int | None:
    text = (text or "").strip().replace("€", "").replace(".", "").replace(",", ".")
    if not text:
        return None
    try:
        return int(Decimal(text) * 100)
    except InvalidOperation:
        raise ValueError("Betrag nicht lesbar")


@require_POST
@rolle_erforderlich("buero")
def akquise_neu(request):
    p = request.POST
    try:
        with transaction.atomic():
            lead = Lead.objects.create(
                firma=p["firma"].strip(), zielgruppe=p["zielgruppe"], strasse=p.get("strasse") or None,
                plz=p.get("plz") or None, ort=p.get("ort") or None, telefon=p.get("telefon") or None,
                email=p.get("email") or None, ansprechpartner=p.get("ansprechpartner") or None,
                quelle=p.get("quelle", "").strip(), regelmaessiger_bedarf={"ja": True, "nein": False}.get(p.get("bedarf")),
                geschaetzter_monatsumsatz_cent=_euro_cent(p.get("umsatz")),
            )
    except (IntegrityError, ValueError, KeyError) as e:
        messages.error(request, f"Lead nicht angelegt: Pflichtfelder (Firma, Zielgruppe, Quelle) prüfen oder Dublette ({e.__class__.__name__}).")
        return redirect("cockpit:akquise")
    dienste.pruefen_und_bewerten(lead)
    messages.success(request, f"{lead.leadnummer} angelegt – Priorität {lead.prioritaet}.")
    return redirect("cockpit:akquise_lead", pk=lead.pk)


@rolle_erforderlich("buero")
def akquise_lead(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if request.method == "POST":
        aktion = request.POST.get("aktion")
        try:
            if aktion == "kontakt":
                freigabe = Freigabe.objects.filter(pk=request.POST.get("freigabe") or None).first()
                dienste.kontakt_dokumentieren(lead, kanal=request.POST["kanal"], richtung=request.POST.get("richtung", "ausgehend"),
                                              zusammenfassung=request.POST["zusammenfassung"].strip(),
                                              ergebnis=request.POST.get("ergebnis") or None, durch=request.user.email,
                                              freigabe=freigabe)
                messages.success(request, "Kontakt dokumentiert, Wiedervorlage in 7 Tagen.")
            elif aktion == "widerspruch":
                dienste.widerspruch_erfassen(lead, request.POST.get("quelle") or f"erfasst von {request.user.email}")
                messages.warning(request, "Widerspruch erfasst – keine weiteren Werbekontakte.")
            elif aktion == "bewerten":
                b = dienste.pruefen_und_bewerten(lead)
                messages.success(request, f"Neu bewertet: {b.prioritaet} ({b.score} Punkte).")
            elif aktion == "gewonnen":
                kunde = dienste.in_kunden_umwandeln(lead)
                messages.success(request, f"Gewonnen – Kunde {kunde.kundennummer} angelegt.")
            elif aktion == "verloren":
                lead.status, lead.wiedervorlage_am = "verloren", None
                lead.notizen = ((lead.notizen or "") + f"\nVerloren: {request.POST.get('grund', '')}").strip()
                lead.save()
                messages.info(request, "Als verloren markiert.")
            elif aktion == "wiedervorlage":
                lead.wiedervorlage_am = date.fromisoformat(request.POST["datum"])
                lead.save()
                messages.success(request, "Wiedervorlage gesetzt.")
            else:
                raise PermissionDenied("Unbekannte Aktion")
        except IntegrityError as e:
            messages.error(request, f"Nicht zulässig: {str(e).splitlines()[0]}")
        except (KeyError, ValueError) as e:
            messages.error(request, f"Angaben unvollständig: {e}")
        return redirect("cockpit:akquise_lead", pk=lead.pk)
    return render(request, "cockpit/akquise_lead.html", {
        "lead": lead, "wege": dienste.kontaktwege(lead), "kontakte": lead.kontakte.all(),
        "kanaele": Kontaktkanal.choices,
        "freigaben": Freigabe.objects.filter(bezug_tabelle="leads", bezug_id=lead.id).order_by("-erstellt_am"),
        "freigegeben": Freigabe.objects.filter(bezug_tabelle="leads", bezug_id=lead.id, status="freigegeben"),
    })


# ============================================================================= Angebotsrechner
ZAHLFELDER = ["treppenhaeuser", "etagen", "muell_termine_monat", "muell_leerungen_monat", "kontrollen_monat"]
DEZIMALFELDER = ["winterdienst_lfm", "rasen_qm", "beet_qm", "hecke_lfm"]


def _leistungen(post) -> dict:
    l = {}
    for f in ZAHLFELDER:
        if post.get(f):
            l[f] = int(post[f])
    for f in DEZIMALFELDER:
        if post.get(f):
            l[f] = str(Decimal(post[f].replace(",", ".")))
    for f in ("aufzug", "muellplatz"):
        l[f] = post.get(f) == "on"
    if post.get("reinigung"):
        l["reinigung"] = post["reinigung"]
    return l


@rolle_erforderlich("buero")
def angebot_rechner(request):
    objekte = Objekt.objects.select_related("kunde").order_by("kunde__name", "bezeichnung")
    kontext = {"objekte": objekte, "eingabe": request.POST, "ergebnis": None}
    if request.method == "POST":
        try:
            leistungen = _leistungen(request.POST)
            from agenten.team.vertrieb import _objektdaten

            objekt = objekte.filter(pk=request.POST.get("objekt") or None).first()
            ausfuehrung = request.POST.get("ausfuehrung", "inhaber")
            kontext["ergebnis"] = kalkulation.kalkuliere(_objektdaten({"leistungen": leistungen}, objekt), ausfuehrung)
            if request.POST.get("anlegen") and objekt:
                a = laufzeit.sofort_ausfuehren(laufzeit.beauftragen(
                    "angebot", "angebot_berechnen", {"objekt_id": str(objekt.id), "leistungen": leistungen, "ausfuehrung": ausfuehrung},
                    ausgeloest_von=f"benutzer:{request.user.email}", prioritaet=2))
                if a.status == "erledigt":
                    messages.success(request, f"Angebotsentwurf {a.ergebnis['angebot']} angelegt – Freigabe {a.ergebnis['freigabe']}.")
                    return redirect("cockpit:freigaben")
                messages.error(request, f"Nicht angelegt: {a.fehler or a.ergebnis}")
            elif request.POST.get("anlegen"):
                messages.error(request, "Für einen Angebotsentwurf bitte ein Objekt wählen.")
        except (ValueError, InvalidOperation) as e:
            messages.error(request, f"Eingabe prüfen: {e}")
    return render(request, "cockpit/angebot_rechner.html", kontext)


# ============================================================================= Aufträge
@rolle_erforderlich("buero")
def auftraege(request):
    qs = Auftrag.objects.select_related("kunde", "objekt")
    status, prio, suche = request.GET.get("status", "offen"), request.GET.get("prio", ""), request.GET.get("q", "").strip()
    if status == "offen":
        qs = qs.exclude(status__in=["erledigt", "abgerechnet", "storniert"])
    elif status:
        qs = qs.filter(status=status)
    if prio:
        qs = qs.filter(prioritaet=prio)
    if suche:
        qs = qs.filter(Q(auftragsnummer__icontains=suche) | Q(titel__icontains=suche) | Q(kunde__name__icontains=suche) |
                       Q(objekt__strasse__icontains=suche))
    zaehler = dict(Auftrag.objects.values_list("status").annotate(n=Count("id")))
    return render(request, "cockpit/auftraege.html", {
        "seite": _seite(request, qs.order_by("faellig_am", "-erstellt_am")), "status": status, "prio": prio, "q": suche,
        "stati": [(s, l, zaehler.get(s, 0)) for s, l in Auftragsstatus.choices],
        "prios": Auftrag._meta.get_field("prioritaet").choices,
    })


@rolle_erforderlich("buero")
def auftraege_detail(request, pk):
    a = get_object_or_404(Auftrag.objects.select_related("kunde", "objekt", "angebot"), pk=pk)
    if request.method == "POST":
        try:
            auftragsstatus.status_wechseln(a, request.POST["status"])
            messages.success(request, f"Status: {Auftragsstatus(request.POST['status']).label}")
        except auftragsstatus.StatuswechselFehler as e:
            messages.error(request, str(e))
        return redirect("cockpit:auftraege_detail", pk=a.pk)
    w = next((z for z in controlling.auftragsrentabilitaet(10000) if z["auftrag_id"] == a.id), None)
    einsaetze = a.einsaetze.prefetch_related("zuweisungen__mitarbeiter", "fotos__dokument").order_by("geplant_von")
    return render(request, "cockpit/auftrag_detail.html", {
        "a": a, "wechsel": auftragsstatus.moegliche_wechsel(a), "w": w, "einsaetze": einsaetze,
        "ist_minuten": sum((z.ende - z.beginn).total_seconds() / 60 - z.pause_minuten
                           for z in Arbeitszeit.objects.filter(einsatz__auftrag=a, ende__isnull=False)),
    })


# ============================================================================= Controlling
def _balken(werte: list[dict], breite=640, hoehe=200) -> dict:
    hoechst = max([w["umsatz_cent"] for w in werte] + [1])
    schritt = breite / max(len(werte), 1)
    balken = []
    for i, w in enumerate(werte):
        h = round((hoehe - 30) * w["umsatz_cent"] / hoechst)
        balken.append({"x": round(i * schritt + schritt * .15), "y": hoehe - 20 - h, "b": round(schritt * .7), "h": h,
                       "monat": w["monat"], "wert": w["umsatz_cent"], "tx": round(i * schritt + schritt / 2)})
    return {"balken": balken, "breite": breite, "hoehe": hoehe, "leer": hoechst == 1}


@rolle_erforderlich("buero")
def controlling_ansicht(request):
    heute = timezone.localdate()
    with connection.cursor() as c:
        c.execute("""SELECT coalesce(agent, '–'), sum(aufrufe), sum(kosten_cent), sum(fehler) FROM v_ki_kosten_tag
                     WHERE tag >= %s GROUP BY 1 ORDER BY 3 DESC""", [heute - timedelta(days=30)])
        ki_kosten = c.fetchall()
    bericht = AgentenAuftrag.objects.filter(agent="ceo", aufgabe="wochenbericht", status="erledigt").order_by("-beendet_am").first()
    return render(request, "cockpit/controlling.html", {
        "monat": controlling.kennzahlen(controlling.Zeitraum.monat(heute)),
        "jahr": controlling.kennzahlen(controlling.Zeitraum.jahr(heute)),
        "diagramm": _balken(controlling.umsatz_je_monat(heute.year)), "rentabilitaet": controlling.auftragsrentabilitaet(15),
        "pipeline": controlling.lead_pipeline(), "ki_kosten": ki_kosten, "bericht": bericht, "heute": heute,
    })


# ============================================================================= Marketing
@rolle_erforderlich("buero")
def marketing(request):
    von = timezone.localdate() - timedelta(days=1)
    beitraege = SocialBeitrag.objects.filter(geplant_fuer__date__gte=von, geplant_fuer__date__lte=von + timedelta(days=21)) \
        .exclude(status="verworfen").order_by("geplant_fuer")
    tage = {}
    for b in beitraege:
        tage.setdefault(timezone.localtime(b.geplant_fuer).date(), []).append(b)
    plan = AgentenAuftrag.objects.filter(agent="marketing", aufgabe="monatsplan", status="erledigt").order_by("-beendet_am").first()
    from agenten.team.marketing import saisonthemen

    return render(request, "cockpit/marketing.html", {
        "tage": sorted(tage.items()), "plan": plan, "themen": saisonthemen(timezone.localdate().month),
        "zaehler": {Beitragsstatus(s).label: n for s, n in SocialBeitrag.objects.values_list("status").annotate(n=Count("id"))},
    })


# ============================================================================= Mitarbeiter: Einsatz (mobil)
def _eigener_einsatz(request, pk) -> Einsatz:
    e = Einsatz.objects.fuer_benutzer(request.user).select_related("auftrag__objekt", "auftrag__kunde").filter(pk=pk).first()
    if e is None:
        raise Http404("Einsatz nicht gefunden")
    return e


def _ich(request) -> Mitarbeiter | None:
    return Mitarbeiter.objects.filter(benutzer=request.user).first()


@rolle_erforderlich()
def einsatz(request, pk):
    e = _eigener_einsatz(request, pk)
    ich = _ich(request)
    offen = Arbeitszeit.objects.filter(einsatz=e, mitarbeiter=ich, ende__isnull=True).first() if ich else None
    if request.method == "POST":
        aktion = request.POST.get("aktion")
        darf_zeit = ich is not None and e.zuweisungen.filter(mitarbeiter=ich).exists()
        try:
            with transaction.atomic():
                if aktion == "start" and darf_zeit and not offen:
                    Arbeitszeit.objects.create(mitarbeiter=ich, einsatz=e, beginn=timezone.now(), taetigkeit=e.auftrag.titel)
                    if e.status in ("geplant", "zugewiesen"):
                        e.status = "in_arbeit"
                        e.save()
                    if e.auftrag.status in ("bestaetigt", "geplant"):
                        auftragsstatus.status_wechseln(e.auftrag, "in_arbeit")
                    messages.success(request, "Arbeitszeit läuft.")
                elif aktion == "stopp" and offen:
                    offen.ende = timezone.now()
                    offen.pause_minuten = max(0, int(request.POST.get("pause") or 0))
                    offen.save()
                    messages.success(request, "Arbeitszeit gespeichert.")
                elif aktion == "bericht":
                    e.bericht_mitarbeiter = request.POST.get("bericht", "").strip()[:5000]
                    e.save()
                    messages.success(request, "Bericht gespeichert.")
                elif aktion == "foto":
                    fotos.speichern(e, request.FILES["foto"], request.POST.get("typ", "sonstiges"), request.user,
                                    request.POST.get("beschreibung", ""))
                    messages.success(request, "Foto gespeichert (ohne Standortdaten).")
                elif aktion == "erledigt":
                    if offen:
                        raise ValueError("Bitte zuerst die Arbeitszeit stoppen.")
                    e.status = "erledigt"
                    e.save()   # Ereignis einsatz.erledigt → Auftragsstatus, Qualitätsprüfung, Abrechnung
                    messages.success(request, "Einsatz erledigt – danke!")
                else:
                    raise ValueError("Aktion nicht möglich.")
        except (ValueError, KeyError, fotos.FotoFehler, IntegrityError, auftragsstatus.StatuswechselFehler) as fehler:
            messages.error(request, str(fehler).splitlines()[0] if str(fehler) else "Nicht möglich.")
        return redirect("cockpit:einsatz", pk=e.pk)
    return render(request, "cockpit/einsatz.html", {
        "e": e, "offen": offen, "fotos": e.fotos.select_related("dokument").order_by("aufgenommen_am"),
        "zeiten": Arbeitszeit.objects.filter(einsatz=e).select_related("mitarbeiter").order_by("beginn"),
        "fototypen": Foto._meta.get_field("typ").choices, "darf_zeit": ich is not None and e.zuweisungen.filter(mitarbeiter=ich).exists(),
    })


@rolle_erforderlich()
def foto(request, pk):
    f = get_object_or_404(Foto.objects.select_related("dokument"), pk=pk)
    _eigener_einsatz(request, f.einsatz_id)   # gleiche Sichtbarkeit wie der Einsatz
    try:
        return FileResponse(fotos.datei_pfad(f).open("rb"), content_type="image/jpeg")
    except (FileNotFoundError, fotos.FotoFehler):
        raise Http404("Datei fehlt")
