"""Automatisierungen: Ereignis → Agentenauftrag (bzw. interne Aktion) und Zeitpläne.

* Ereignisse entstehen per Datenbank-Trigger (Outbox, ``ereignisse``) – kein Programmteil kann sie vergessen.
* ``ereignisse_verarbeiten`` ordnet jedes Ereignis allen passenden, aktiven Automatisierungen zu.
  Jede erfolgreiche Verarbeitung steht in ``automatisierungs_laeufe`` (je Automatisierung + Ereignis höchstens
  einmal erfolgreich → wiederholbar ohne Doppelungen). Fehler: Backoff, nach 5 Versuchen Alarm.
* Zeitpläne (``zeitplan:…``) prüft ``zeitplan_ausfuehren`` jede Minute; je Zeitfenster genau ein Lauf.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from django.db import connection, transaction
from django.utils import timezone

from .models import Automatisierung, AutomatisierungsLauf, Ereignis

MAX_EREIGNIS_VERSUCHE = 5
WOCHENTAGE = {"mo": 0, "di": 1, "mi": 2, "do": 3, "fr": 4, "sa": 5, "so": 6}


@dataclass
class AutomatisierungDefinition:
    code: str
    name: str
    beschreibung: str
    ausloeser: str                     # 'ereignis:<typ>' oder 'zeitplan:<spec>'
    handler: Callable                  # (ereignis | None) -> dict
    bedingung: Callable | None = None  # (ereignis) -> bool


AUTOMATISIERUNGEN: dict[str, AutomatisierungDefinition] = {}


def automatisierung(code: str, name: str, beschreibung: str, ausloeser: str, bedingung: Callable | None = None):
    def decorator(funktion):
        AUTOMATISIERUNGEN[code] = AutomatisierungDefinition(code, name, beschreibung, ausloeser, funktion, bedingung)
        return funktion

    return decorator


def laden():
    from . import automatisierungen_definitionen  # noqa: F401

    return AUTOMATISIERUNGEN


def synchronisieren() -> dict:
    laden()
    neu = 0
    for d in AUTOMATISIERUNGEN.values():
        _, angelegt = Automatisierung.objects.update_or_create(
            code=d.code, defaults={"name": d.name, "beschreibung": d.beschreibung, "ausloeser": d.ausloeser},
        )
        neu += angelegt
    return {"automatisierungen": len(AUTOMATISIERUNGEN), "neu": neu}


# ----------------------------------------------------------------------------- Läufe protokollieren
def _lauf(code: str, ereignis: Ereignis | None, funktion: Callable) -> AutomatisierungsLauf:
    """Führt eine Automatisierung in einem Sicherungspunkt aus und protokolliert das Ergebnis."""
    auto = Automatisierung.objects.select_for_update().get(code=code)
    lauf = AutomatisierungsLauf.objects.create(automatisierung=auto, ereignis=ereignis)
    jetzt = timezone.now()
    try:
        with transaction.atomic():
            ergebnis = funktion() or {}
        lauf.erfolgreich, lauf.ergebnis = True, _json(ergebnis)
        auto.letzter_erfolg, auto.fehler_in_folge, auto.letzter_fehler = jetzt, 0, None
    except Exception as e:  # noqa: BLE001
        lauf.erfolgreich, lauf.fehler = False, f"{type(e).__name__}: {e}"[:2000]
        auto.fehler_in_folge += 1
        auto.letzter_fehler = lauf.fehler
    lauf.beendet_am = timezone.now()
    lauf.save()
    auto.letzter_lauf = jetzt
    auto.save(update_fields=["letzter_lauf", "letzter_erfolg", "fehler_in_folge", "letzter_fehler"])
    return lauf


def _json(wert):
    from .laufzeit import _json as j

    return j(wert)


# ----------------------------------------------------------------------------- Ereignisse
def passende(ereignis: Ereignis) -> list[AutomatisierungDefinition]:
    laden()
    return [d for d in AUTOMATISIERUNGEN.values()
            if d.ausloeser == f"ereignis:{ereignis.typ}" and (d.bedingung is None or d.bedingung(ereignis))]


def ereignisse_verarbeiten(max_anzahl: int = 100) -> dict:
    laden()
    aktiv = set(Automatisierung.objects.filter(aktiv=True).values_list("code", flat=True))
    zaehler = {"verarbeitet": 0, "fehler": 0}
    for _ in range(max_anzahl):
        with transaction.atomic():
            with connection.cursor() as c:
                c.execute("""SELECT id FROM ereignisse WHERE verarbeitet_am IS NULL AND naechster_versuch <= now()
                             ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED""")
                zeile = c.fetchone()
            if not zeile:
                break
            ereignis = Ereignis.objects.get(pk=zeile[0])
            erledigt = set(AutomatisierungsLauf.objects.filter(ereignis=ereignis, erfolgreich=True)
                           .values_list("automatisierung_id", flat=True))
            fehler = []
            for d in passende(ereignis):
                if d.code not in aktiv or d.code in erledigt:
                    continue
                lauf = _lauf(d.code, ereignis, lambda d=d: d.handler(ereignis))
                if not lauf.erfolgreich:
                    fehler.append(f"{d.code}: {lauf.fehler}")
            ereignis.versuche += 1
            if not fehler:
                ereignis.verarbeitet_am, ereignis.fehler = timezone.now(), None
                zaehler["verarbeitet"] += 1
            else:
                zaehler["fehler"] += 1
                ereignis.fehler = "; ".join(fehler)[:2000]
                if ereignis.versuche >= MAX_EREIGNIS_VERSUCHE:
                    ereignis.verarbeitet_am = timezone.now()   # aufgeben – Überwachung meldet es
                    _alarm(f"Ereignis #{ereignis.id} ({ereignis.typ}) nach {ereignis.versuche} Versuchen nicht verarbeitet",
                           ereignis.fehler)
                else:
                    ereignis.naechster_versuch = timezone.now() + timedelta(minutes=2 ** ereignis.versuche)
            ereignis.save(update_fields=["versuche", "verarbeitet_am", "fehler", "naechster_versuch"])
    return zaehler


def _alarm(titel: str, text: str | None) -> None:
    from . import freigaben

    freigaben.anfordern(art="eskalation", titel=titel, begruendung=text, angefordert_von="agent:automation",
                        prioritaet="hoch")


# ----------------------------------------------------------------------------- Zeitpläne
SPEC = re.compile(
    r"^(?:taeglich (?P<t_hm>\d{1,2}:\d{2})"
    r"|woechentlich (?P<w_tag>mo|di|mi|do|fr|sa|so) (?P<w_hm>\d{1,2}:\d{2})"
    r"|stuendlich :(?P<s_min>\d{2})"
    r"|alle (?P<n>\d{1,3}) min)$"
)


def letztes_fenster(spec: str, jetzt: datetime) -> datetime:
    """Beginn des jüngsten Zeitfensters ≤ jetzt (lokale Zeit Europe/Berlin)."""
    m = SPEC.match(spec)
    if not m:
        raise ValueError(f"Unbekannter Zeitplan „{spec}“")
    lokal = timezone.localtime(jetzt)
    if m["t_hm"] or m["w_hm"]:
        stunde, minute = map(int, (m["t_hm"] or m["w_hm"]).split(":"))
        kandidat = lokal.replace(hour=stunde, minute=minute, second=0, microsecond=0)
        if m["w_tag"]:
            kandidat -= timedelta(days=(lokal.weekday() - WOCHENTAGE[m["w_tag"]]) % 7)
            if kandidat > lokal:
                kandidat -= timedelta(days=7)
        elif kandidat > lokal:
            kandidat -= timedelta(days=1)
        return kandidat
    if m["s_min"]:
        kandidat = lokal.replace(minute=int(m["s_min"]), second=0, microsecond=0)
        return kandidat if kandidat <= lokal else kandidat - timedelta(hours=1)
    n = int(m["n"])
    mitternacht = lokal.replace(hour=0, minute=0, second=0, microsecond=0)
    minuten = (lokal - mitternacht).total_seconds() // 60
    return mitternacht + timedelta(minutes=minuten - minuten % n)


def zeitplan_ausfuehren(jetzt: datetime | None = None) -> list[str]:
    """Startet jede fällige Zeitplan-Automatisierung genau einmal je Fenster. Gibt die gestarteten Codes zurück."""
    laden()
    jetzt = jetzt or timezone.now()
    gestartet = []
    for d in AUTOMATISIERUNGEN.values():
        if not d.ausloeser.startswith("zeitplan:"):
            continue
        fenster = letztes_fenster(d.ausloeser.removeprefix("zeitplan:"), jetzt)
        with transaction.atomic():
            auto = Automatisierung.objects.select_for_update().filter(code=d.code, aktiv=True).first()
            if auto is None or (auto.letzter_lauf and auto.letzter_lauf >= fenster):
                continue
            lauf = _lauf(d.code, None, lambda d=d, f=fenster: d.handler(None, f))
            gestartet.append(d.code if lauf.erfolgreich else f"{d.code} (Fehler)")
    return gestartet


def fenster_schluessel(code: str, fenster: datetime) -> str:
    return f"zeitplan:{code}:{timezone.localtime(fenster):%Y-%m-%dT%H:%M}"

