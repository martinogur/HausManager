"""Aufgaben von Dispositions-, Qualitäts- und Finanz-Agent."""

from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from agenten.freigaben import folgeaktion
from agenten.laufzeit import Eskalation, aufgabe
from auftraege import status as auftragsstatus
from auftraege.models import Auftrag, Einsatz, EinsatzMitarbeiter, Rechnung
from berichte import controlling
from personal.models import Abwesenheit, Arbeitszeit, Mitarbeiter, Verfuegbarkeit
from stammdaten.models import Leistungsvereinbarung

STANDARD_BEGINN = time(8, 0)
STANDARD_DAUER_MIN = 60
UST = Decimal("0.19")


# ============================================================================= Disposition
def verfuegbare_mitarbeiter(von: datetime, bis: datetime) -> list[Mitarbeiter]:
    """Aktive Mitarbeiter mit Grundverfügbarkeit im Zeitfenster, ohne Abwesenheit und ohne Überschneidung.
    Sortiert nach geringster Einsatzzeit in derselben Woche (gleichmäßige Auslastung)."""
    lokal_von, lokal_bis = timezone.localtime(von), timezone.localtime(bis)
    tag = lokal_von.date()
    kandidaten = (Mitarbeiter.objects.filter(Q(austritt__isnull=True) | Q(austritt__gte=tag))
                  .filter(Q(eintritt__isnull=True) | Q(eintritt__lte=tag)))
    frei = []
    wochenstart = tag - timedelta(days=tag.weekday())
    for m in kandidaten:
        passt = Verfuegbarkeit.objects.filter(mitarbeiter=m, wochentag=tag.isoweekday(),
                                              von__lte=lokal_von.time(), bis__gte=lokal_bis.time()).exists()
        abwesend = Abwesenheit.objects.filter(mitarbeiter=m, von__lte=tag, bis__gte=tag).exists()
        belegt = EinsatzMitarbeiter.objects.filter(mitarbeiter=m, einsatz__geplant_von__lt=bis,
                                                   einsatz__geplant_bis__gt=von).exists()
        if passt and not abwesend and not belegt:
            einsaetze = EinsatzMitarbeiter.objects.filter(
                mitarbeiter=m, einsatz__geplant_von__date__gte=wochenstart,
                einsatz__geplant_von__date__lt=wochenstart + timedelta(days=7)).count()
            frei.append((einsaetze, m.nachname, m))
    return [m for _, _, m in sorted(frei, key=lambda x: (x[0], x[1]))]


def _naechster_werktag(tag: date) -> date:
    while tag.weekday() >= 5:
        tag += timedelta(days=1)
    return tag


@aufgabe("dispatch", "einsatz_planen")
def einsatz_planen(ctx):
    """Freigegebener Auftrag ohne Einsatz → Einsatz am Fälligkeitstag (sonst nächster Werktag) + Personalvorschlag."""
    auftrag = Auftrag.objects.get(pk=ctx.eingabe["auftrag_id"])
    einsatz = auftrag.einsaetze.exclude(status="ausgefallen").order_by("geplant_von").first()
    if einsatz is None:
        tag = _naechster_werktag(max(auftrag.faellig_am or date.min, timezone.localdate() + timedelta(days=1)))
        von = timezone.make_aware(datetime.combine(tag, STANDARD_BEGINN))
        einsatz = Einsatz.objects.create(auftrag=auftrag, geplant_von=von,
                                         geplant_bis=von + timedelta(minutes=auftrag.geschaetzte_minuten or STANDARD_DAUER_MIN),
                                         notiz_buero="Vom Dispositions-Agenten geplant – Termin bitte bestätigen.")
    if einsatz.zuweisungen.exists():
        return {"einsatz": str(einsatz.id), "hinweis": "bereits zugewiesen"}
    ctx.schritt("Verfügbarkeit prüfen")
    frei = verfuegbare_mitarbeiter(einsatz.geplant_von, einsatz.geplant_bis)
    if not frei:
        raise Eskalation(f"Kein verfügbarer Mitarbeiter für {auftrag.auftragsnummer} am "
                         f"{timezone.localtime(einsatz.geplant_von):%d.%m.%Y %H:%M}", {"einsatz_id": str(einsatz.id)})
    vorschlag = frei[0]
    f = ctx.freigabe_anfordern(
        art="einsatz_zuweisung",
        titel=f"{auftrag.auftragsnummer}: {vorschlag.vorname} {vorschlag.nachname} am {timezone.localtime(einsatz.geplant_von):%d.%m. %H:%M}",
        begruendung=f"Verfügbar und am wenigsten ausgelastet. Alternativen: {', '.join(m.vorname for m in frei[1:4]) or 'keine'}.",
        vorschlag={"einsatz_id": str(einsatz.id), "mitarbeiter_id": str(vorschlag.id),
                   "alternativen": [str(m.id) for m in frei[1:4]]},
        bezug=("einsaetze", einsatz.id),
    )
    return {"einsatz": str(einsatz.id), "vorschlag": f"{vorschlag.vorname} {vorschlag.nachname}", "freigabe": f.freigabenummer}


@folgeaktion("einsatz_zuweisung")
def _zuweisung_freigegeben(freigabe, benutzer):
    einsatz = Einsatz.objects.select_related("auftrag").get(pk=freigabe.vorschlag["einsatz_id"])
    EinsatzMitarbeiter.objects.create(einsatz=einsatz, mitarbeiter_id=freigabe.vorschlag["mitarbeiter_id"])
    if einsatz.status == "geplant":
        einsatz.status = "zugewiesen"
        einsatz.save()
    if einsatz.auftrag.status == "bestaetigt":
        auftragsstatus.status_wechseln(einsatz.auftrag, "geplant")


def termine(v: Leistungsvereinbarung, von: date, bis: date) -> list[date]:
    """Ausführungstage einer Vereinbarung im Zeitraum [von, bis]. Saisonal/nach Bedarf: keine festen Termine."""
    tage, tag = [], von
    while tag <= bis:
        gueltig = v.gueltig_von <= tag and (v.gueltig_bis is None or tag <= v.gueltig_bis)
        if gueltig:
            if v.intervall == "woechentlich" and tag.isoweekday() == v.wochentag:
                tage.append(tag)
            elif v.intervall == "zweiwoechentlich" and tag.isoweekday() == v.wochentag \
                    and ((tag - v.gueltig_von).days // 7) % 2 == 0:
                tage.append(tag)
            elif v.intervall == "monatlich":
                if v.monatstag and tag.day == v.monatstag:
                    tage.append(tag)
                elif not v.monatstag and v.wochentag and tag.isoweekday() == v.wochentag and tag.day <= 7:
                    tage.append(tag)   # erster <Wochentag> im Monat
            elif v.intervall == "einmalig" and tag == v.gueltig_von:
                tage.append(tag)
        tag += timedelta(days=1)
    return tage


@aufgabe("dispatch", "wiederkehrende_einsaetze")
def wiederkehrende_einsaetze(ctx):
    """Erzeugt Einsätze der nächsten 14 Tage aus Leistungsvereinbarungen (DB verhindert Doppelte je Tag)."""
    heute = timezone.localdate()
    bis = heute + timedelta(days=int(ctx.eingabe.get("tage", 14)))
    neu = 0
    vereinbarungen = Leistungsvereinbarung.objects.filter(Q(gueltig_bis__isnull=True) | Q(gueltig_bis__gte=heute),
                                                          gueltig_von__lte=bis).select_related("objekt", "leistung")
    for v in vereinbarungen:
        tage = termine(v, heute + timedelta(days=1), bis)
        if not tage:
            continue
        auftrag = (Auftrag.objects.filter(leistungsvereinbarung=v).exclude(status__in=["storniert", "abgerechnet"]).first()
                   or Auftrag.objects.create(kunde_id=v.objekt.kunde_id, objekt=v.objekt, leistungsvereinbarung=v,
                                             titel=f"Dauerauftrag {v.leistung.name}", status="bestaetigt"))
        for tag in tage:
            von = timezone.make_aware(datetime.combine(tag, STANDARD_BEGINN))
            try:
                with transaction.atomic():
                    e = Einsatz.objects.create(auftrag=auftrag, geplant_von=von, geplant_bis=von + timedelta(minutes=STANDARD_DAUER_MIN),
                                               erzeugt_aus=v)
                    neu += 1
                    if v.standard_mitarbeiter_id:   # fest im Vertrag hinterlegte Person = vorab freigegeben
                        try:
                            with transaction.atomic():
                                EinsatzMitarbeiter.objects.create(einsatz=e, mitarbeiter_id=v.standard_mitarbeiter_id)
                                e.status = "zugewiesen"
                                e.save()
                        except IntegrityError:
                            pass   # Überschneidung → bleibt „geplant“, Büro sieht es im Kalender
            except IntegrityError:
                continue   # existiert schon (eindeutiger Index je Vereinbarung und Tag)
    return {"neue_einsaetze": neu, "bis": bis.isoformat()}


# ============================================================================= Qualität
@aufgabe("quality", "auftrag_pruefen")
def auftrag_pruefen(ctx):
    auftrag = Auftrag.objects.get(pk=ctx.eingabe["auftrag_id"])
    maengel = []
    einsaetze = list(auftrag.einsaetze.exclude(status="ausgefallen"))
    if not einsaetze:
        maengel.append("Kein Einsatz dokumentiert.")
    for e in einsaetze:
        name = f"Einsatz {timezone.localtime(e.geplant_von):%d.%m.}"
        if e.status != "erledigt":
            maengel.append(f"{name}: Status „{e.get_status_display()}“")
        typen = set(e.fotos.values_list("typ", flat=True))
        for typ in ("vorher", "nachher"):
            if typ not in typen:
                maengel.append(f"{name}: {typ.capitalize()}-Foto fehlt")
        if not (e.bericht_mitarbeiter or "").strip():
            maengel.append(f"{name}: Arbeitsbericht fehlt")
        zeiten = Arbeitszeit.objects.filter(einsatz=e)
        if not zeiten.exists():
            maengel.append(f"{name}: keine Arbeitszeit erfasst")
        elif zeiten.filter(bestaetigt_am__isnull=True).exists():
            maengel.append(f"{name}: Arbeitszeit nicht bestätigt")
    w = next((z for z in controlling.auftragsrentabilitaet(500) if z["auftrag_id"] == auftrag.id), None)
    ziel = 30
    if w and w["deckungsbeitrag_prozent"] is not None and float(w["deckungsbeitrag_prozent"]) < ziel:
        maengel.append(f"Deckungsbeitrag {w['deckungsbeitrag_prozent']} % unter Ziel {ziel} %")
    if maengel:
        ctx.freigabe_anfordern(art="sonstiges", titel=f"Qualitätsprüfung {auftrag.auftragsnummer}: {len(maengel)} Hinweis(e)",
                               begruendung="\n".join(maengel), vorschlag={"auftrag_id": str(auftrag.id), "maengel": maengel},
                               bezug=("auftraege", auftrag.id))
    return {"auftrag": auftrag.auftragsnummer, "maengel": maengel, "ok": not maengel}


# ============================================================================= Finanzen
def _cent(wert) -> int:
    return int(Decimal(wert).quantize(Decimal(1), rounding=ROUND_HALF_UP))


@aufgabe("finance", "abrechnung_vorbereiten")
def abrechnung_vorbereiten(ctx):
    auftrag = Auftrag.objects.select_related("angebot").get(pk=ctx.eingabe["auftrag_id"])
    if Rechnung.objects.filter(auftrag=auftrag).exclude(status="storniert").exists():
        return {"hinweis": "Rechnung existiert bereits"}
    netto = auftrag.verkaufspreis_netto_cent or (auftrag.angebot.summe_netto_cent if auftrag.angebot_id else None)
    if not netto:
        raise Eskalation(f"{auftrag.auftragsnummer}: kein Verkaufspreis und kein Angebot – Betrag festlegen.",
                         {"auftrag_id": str(auftrag.id)})
    rechnung = Rechnung.objects.create(kunde_id=auftrag.kunde_id, auftrag=auftrag, status="entwurf",
                                       summe_netto_cent=netto, summe_brutto_cent=_cent(Decimal(netto) * (1 + UST)))
    f = ctx.freigabe_anfordern(
        art="rechnung_entwurf", titel=f"Rechnung zu {auftrag.auftragsnummer}: {netto / 100:.2f} € netto",
        begruendung="Entwurf mit 19 % USt. Kleinunternehmerregelung ist noch offen (Steuerberater). "
                    "Festschreiben erfolgt in Lexware Office durch den Inhaber.",
        vorschlag={"rechnung_id": str(rechnung.id), "auftrag_id": str(auftrag.id), "netto_cent": netto},
        bezug=("rechnungen", rechnung.id),
    )
    return {"rechnung": str(rechnung.id), "freigabe": f.freigabenummer}


@folgeaktion("rechnung_entwurf")
def _rechnung_freigegeben(freigabe, benutzer):
    """Freigabe = Inhaber hat den Entwurf geprüft; Übertragung an Lexware übernimmt die Integration (wenn eingerichtet).
    Der Auftrag gilt als abgerechnet, sobald die Rechnung existiert und freigegeben ist."""
    auftrag = Auftrag.objects.get(pk=freigabe.vorschlag["auftrag_id"])
    if auftrag.status == "erledigt":
        auftragsstatus.status_wechseln(auftrag, "abgerechnet")


@folgeaktion("rechnung_entwurf", bei="abgelehnt")
def _rechnung_abgelehnt(freigabe, benutzer):
    Rechnung.objects.filter(pk=freigabe.vorschlag["rechnung_id"], status="entwurf").update(status="storniert")


@aufgabe("finance", "zahlungen_pruefen")
def zahlungen_pruefen(ctx):
    """Offene Rechnungen nach Fälligkeit überwachen (Spiegel; führend für Zahlungen ist Lexware Office)."""
    heute = timezone.localdate()
    neu_ueberfaellig = list(Rechnung.objects.filter(status="offen", faellig_am__lt=heute))
    for r in neu_ueberfaellig:
        r.status = "ueberfaellig"
        r.save()
    offen = Rechnung.objects.filter(status__in=["offen", "ueberfaellig"]).aggregate(s=Sum("summe_netto_cent"))["s"] or 0
    if neu_ueberfaellig:
        ctx.freigabe_anfordern(
            art="sonstiges", titel=f"{len(neu_ueberfaellig)} Rechnung(en) überfällig – Zahlungserinnerung?",
            begruendung="Bitte Zahlungseingang in Lexware prüfen und ggf. Erinnerung freigeben.",
            vorschlag={"rechnungen": [str(r.id) for r in neu_ueberfaellig]},
        )
    return {"neu_ueberfaellig": len(neu_ueberfaellig), "offen_netto_cent": offen}
