"""Agenten-Laufzeit: Register, Beauftragung, Warteschlange, Ausführung mit Grenzen.

Jeder Agent hat einen Verantwortungsbereich, eigene Aufgaben (Python-Funktionen), erlaubte
Delegationsziele, ein Tagesbudget, eine maximale Laufzeit, maximale Schritte und Versuche.

Ablauf eines Agentenauftrags
    wartend ──holen()──▶ laeuft ──Erfolg──▶ erledigt
                           │──Fehler, Versuche übrig──▶ wartend (Backoff 2^n Min.)
                           │──Fehler, keine Versuche──▶ fehlgeschlagen + Eskalation an den Inhaber
                           │──Eskalation (Entscheidung nötig)──▶ eskaliert + Freigabe „Eskalation“
                           └──Budget erschöpft──▶ wartend bis morgen 06:00 (zählt als Versuch)

Schutz vor Endlosschleifen: Tiefe ≤ 3, keine Wiederholung von Agent+Aufgabe in derselben Kette,
max. 20 Aufträge je Kette (Datenbank-Trigger) und nur erlaubte Delegationsziele (hier).
"""

import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Callable

from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from . import ki
from .models import Agent, AgentenAuftrag, AgentenProtokoll, Auftragsstatus

log = logging.getLogger(__name__)


class Eskalation(Exception):
    """Der Agent braucht eine Entscheidung des Inhabers (kein technischer Fehler)."""

    def __init__(self, grund: str, vorschlag: dict | None = None):
        super().__init__(grund)
        self.grund, self.vorschlag = grund, vorschlag or {}


class GrenzeErreicht(Exception):
    """Schritt- oder Zeitgrenze des Agenten überschritten."""


class DelegationVerboten(Exception):
    pass


@dataclass
class AgentDefinition:
    code: str
    name: str
    beschreibung: str
    verantwortung: str
    darf_delegieren_an: frozenset[str] = frozenset()
    werkzeuge: tuple[str, ...] = ()        # nur Dokumentation/Oberfläche; Zugriff regeln die Aufgaben-Funktionen
    modell: str | None = ki.STANDARD_MODELL
    tagesbudget_cent: int = 50
    max_schritte: int = 8
    max_laufzeit_sekunden: int = 120
    max_versuche: int = 3
    erfolgsmessung: str = ""
    aufgaben: dict[str, Callable] = field(default_factory=dict)


REGISTER: dict[str, AgentDefinition] = {}


def agent(**kwargs) -> AgentDefinition:
    definition = AgentDefinition(**kwargs)
    REGISTER[definition.code] = definition
    return definition


def aufgabe(agent_code: str, name: str):
    """Registriert eine Aufgabe: ``def handler(ctx: Kontext) -> dict``."""

    def decorator(funktion):
        if agent_code not in REGISTER:   # Team-Modul direkt importiert → Register zuerst laden
            register_laden()
        REGISTER[agent_code].aufgaben[name] = funktion
        return funktion

    return decorator


def register_laden():
    """Importiert alle Agenten-Module (Registrierung per Decorator)."""
    from . import agenten_definitionen  # noqa: F401

    return REGISTER


def synchronisieren() -> dict:
    """Legt fehlende Agenten in der DB an. Vorhandene Einstellungen (aktiv, Budget, Grenzen) bleiben –
    die Datenbank ist für Betriebswerte führend, der Code für Name/Beschreibung."""
    register_laden()
    neu = 0
    for d in REGISTER.values():
        _, angelegt = Agent.objects.update_or_create(
            code=d.code,
            defaults={"name": d.name, "beschreibung": d.beschreibung},
            create_defaults={"name": d.name, "beschreibung": d.beschreibung, "modell": d.modell,
                             "tagesbudget_cent": d.tagesbudget_cent, "max_schritte": d.max_schritte,
                             "max_laufzeit_sekunden": d.max_laufzeit_sekunden, "max_versuche": d.max_versuche},
        )
        neu += angelegt
    return {"agenten": len(REGISTER), "neu": neu}


# ----------------------------------------------------------------------------- Beauftragen
def beauftragen(agent_code: str, aufgabe_name: str, eingabe: dict | None = None, *, ausgeloest_von: str,
                eltern: AgentenAuftrag | None = None, idempotenz: str | None = None, prioritaet: int = 5,
                faellig_ab: datetime | None = None) -> AgentenAuftrag:
    """Legt einen Agentenauftrag an (idempotent über ``idempotenz``)."""
    register_laden()
    definition = REGISTER.get(agent_code)
    if definition is None or aufgabe_name not in definition.aufgaben:
        raise ValueError(f"Unbekannte Aufgabe {agent_code}/{aufgabe_name}")
    if eltern is not None:
        erlaubt = REGISTER[eltern.agent_id].darf_delegieren_an
        if agent_code not in erlaubt:
            raise DelegationVerboten(f"{eltern.agent_id} darf nicht an {agent_code} delegieren")
    if idempotenz:
        vorhanden = AgentenAuftrag.objects.filter(idempotenz_schluessel=idempotenz).first()
        if vorhanden:
            return vorhanden
    agent_obj = Agent.objects.filter(code=agent_code).first()
    if agent_obj is None:
        synchronisieren()
        agent_obj = Agent.objects.get(code=agent_code)
    werte = dict(agent=agent_obj, aufgabe=aufgabe_name, eingabe=eingabe or {}, ausgeloest_von=ausgeloest_von,
                 eltern=eltern, idempotenz_schluessel=idempotenz, prioritaet=prioritaet,
                 max_versuche=agent_obj.max_versuche)
    if faellig_ab:
        werte["faellig_ab"] = faellig_ab
    try:
        with transaction.atomic():
            return AgentenAuftrag.objects.create(**werte)
    except IntegrityError:
        if idempotenz:  # gleichzeitig angelegt
            return AgentenAuftrag.objects.get(idempotenz_schluessel=idempotenz)
        raise


# ----------------------------------------------------------------------------- Kontext für Aufgaben
class Kontext:
    """Wird jeder Aufgabe übergeben: Eingabe, Protokoll, KI mit Budget, Delegation, Freigaben, Grenzen."""

    def __init__(self, auftrag: AgentenAuftrag, agent_obj: Agent):
        self.auftrag, self.agent = auftrag, agent_obj
        self.eingabe = auftrag.eingabe or {}
        self.schritte = 0
        self.ki_mitschnitt: list[dict] = []
        self.frist = timezone.now() + timedelta(seconds=agent_obj.max_laufzeit_sekunden)

    def schritt(self, beschreibung: str) -> None:
        self.schritte += 1
        if self.schritte > self.agent.max_schritte:
            raise GrenzeErreicht(f"Mehr als {self.agent.max_schritte} Schritte ({beschreibung})")
        if timezone.now() > self.frist:
            raise GrenzeErreicht(f"Laufzeit über {self.agent.max_laufzeit_sekunden} s ({beschreibung})")

    def protokoll(self, art: str, /, **inhalt) -> None:
        AgentenProtokoll.objects.create(auftrag=self.auftrag, art=art, inhalt=_json(inhalt))

    def ki(self, **kwargs) -> ki.KiAntwort:
        """KI-Aufruf (zählt als Schritt, Budget wird geprüft, Restlaufzeit als Timeout)."""
        self.schritt(f"KI: {kwargs.get('zweck')}")
        rest = max(5.0, (self.frist - timezone.now()).total_seconds())
        antwort = ki.client().strukturiert(agent=self.agent, auftrag=self.auftrag, timeout_s=rest,
                                           mitschnitt=self.ki_mitschnitt, **kwargs)
        self.protokoll("ki_aufruf", zweck=kwargs.get("zweck"), modell=antwort.modell,
                       tokens=[antwort.eingabe_tokens, antwort.ausgabe_tokens], kosten_cent=str(antwort.kosten_cent))
        return antwort

    def ki_oder_regel(self, regel: Callable[[], dict], **kwargs) -> tuple[dict, str]:
        """KI versuchen; ist sie aus, erschöpft oder gescheitert, das regelbasierte Ergebnis nehmen."""
        try:
            return self.ki(**kwargs).daten, "ki"
        except ki.KiFehler as fehler:
            self.protokoll("fehler", hinweis="KI nicht genutzt – regelbasiert", grund=str(fehler))
            return regel(), "regel"

    def delegieren(self, agent_code: str, aufgabe_name: str, eingabe: dict | None = None, idempotenz: str | None = None,
                   prioritaet: int | None = None) -> AgentenAuftrag:
        self.schritt(f"Delegation an {agent_code}/{aufgabe_name}")
        neu = beauftragen(agent_code, aufgabe_name, eingabe, ausgeloest_von=f"agent:{self.agent.code}",
                          eltern=self.auftrag, idempotenz=idempotenz, prioritaet=prioritaet or self.auftrag.prioritaet)
        self.protokoll("delegation", an=agent_code, aufgabe=aufgabe_name, auftrag_id=str(neu.id))
        return neu

    def freigabe_anfordern(self, **kwargs):
        from . import freigaben

        self.schritt("Freigabe anfordern")
        f = freigaben.anfordern(angefordert_von=f"agent:{self.agent.code}", agenten_auftrag=self.auftrag, **kwargs)
        self.protokoll("freigabe", freigabe=f.freigabenummer, art=f.art, titel=f.titel)
        return f


def _json(wert):
    """Macht Werte JSON-tauglich (UUID, Datum, Decimal → Text)."""
    if isinstance(wert, dict):
        return {str(k): _json(v) for k, v in wert.items()}
    if isinstance(wert, (list, tuple, set)):
        return [_json(v) for v in wert]
    if isinstance(wert, (str, int, float, bool)) or wert is None:
        return wert
    return str(wert)


# ----------------------------------------------------------------------------- Warteschlange
def holen() -> AgentenAuftrag | None:
    """Nächsten fälligen Auftrag sperren (mehrere Worker parallel möglich: SKIP LOCKED).
    Hängengebliebene Aufträge (Sperre abgelaufen) werden erneut aufgenommen."""
    with transaction.atomic():
        with connection.cursor() as c:
            c.execute(
                """SELECT a.id FROM agenten_auftraege a JOIN agenten g ON g.code = a.agent
                   WHERE g.aktiv AND a.faellig_ab <= now()
                     AND (a.status = 'wartend' OR (a.status = 'laeuft' AND a.gesperrt_bis < now()))
                   ORDER BY a.prioritaet, a.faellig_ab LIMIT 1 FOR UPDATE OF a SKIP LOCKED"""
            )
            zeile = c.fetchone()
        if not zeile:
            return None
        auftrag = AgentenAuftrag.objects.select_related("agent").get(pk=zeile[0])
        if auftrag.versuche >= auftrag.max_versuche:   # hängengebliebener letzter Versuch
            _beenden(auftrag, Auftragsstatus.FEHLGESCHLAGEN, fehler="Abgebrochen: Sperrzeit abgelaufen, keine Versuche mehr")
            _eskalieren(auftrag, "Agentenauftrag hing und hat keine Versuche mehr.")
            return None
        auftrag.status = Auftragsstatus.LAEUFT
        auftrag.versuche += 1
        auftrag.gestartet_am = timezone.now()
        auftrag.gesperrt_bis = timezone.now() + timedelta(seconds=auftrag.agent.max_laufzeit_sekunden + 60)
        auftrag.save(update_fields=["status", "versuche", "gestartet_am", "gesperrt_bis"])
        return auftrag


def sofort_ausfuehren(auftrag: AgentenAuftrag) -> AgentenAuftrag:
    """Genau diesen Auftrag jetzt ausführen (Oberfläche „Jetzt ausführen“, manage.py --sofort)."""
    with transaction.atomic():
        a = AgentenAuftrag.objects.select_for_update(skip_locked=True).select_related("agent").filter(
            pk=auftrag.pk, status=Auftragsstatus.WARTEND).first()
        if a is None:
            return AgentenAuftrag.objects.get(pk=auftrag.pk)
        a.status, a.versuche, a.gestartet_am = Auftragsstatus.LAEUFT, a.versuche + 1, timezone.now()
        a.gesperrt_bis = timezone.now() + timedelta(seconds=a.agent.max_laufzeit_sekunden + 60)
        a.save(update_fields=["status", "versuche", "gestartet_am", "gesperrt_bis"])
    return ausfuehren(a)


def _beenden(auftrag: AgentenAuftrag, status: str, *, ergebnis: dict | None = None, fehler: str | None = None) -> None:
    auftrag.status, auftrag.beendet_am, auftrag.gesperrt_bis = status, timezone.now(), None
    auftrag.ergebnis, auftrag.fehler = _json(ergebnis) if ergebnis is not None else auftrag.ergebnis, fehler
    auftrag.save(update_fields=["status", "beendet_am", "gesperrt_bis", "ergebnis", "fehler"])


def _zuruecklegen(auftrag: AgentenAuftrag, faellig_ab: datetime, fehler: str) -> None:
    auftrag.status, auftrag.faellig_ab, auftrag.gesperrt_bis, auftrag.fehler = Auftragsstatus.WARTEND, faellig_ab, None, fehler
    auftrag.save(update_fields=["status", "faellig_ab", "gesperrt_bis", "fehler"])


def _eskalieren(auftrag: AgentenAuftrag, grund: str, vorschlag: dict | None = None) -> None:
    from . import freigaben

    freigaben.anfordern(
        art="eskalation", titel=f"{auftrag.agent.name}: {grund}"[:300], begruendung=grund,
        vorschlag=_json({"aufgabe": auftrag.aufgabe, "eingabe": auftrag.eingabe, **(vorschlag or {})}),
        bezug=("agenten_auftraege", auftrag.id), angefordert_von=f"agent:{auftrag.agent_id}", agenten_auftrag=auftrag,
        prioritaet="hoch",
    )


def _ki_kosten_nachtragen(ctx: "Kontext") -> None:
    """Nach einem Rollback: KI-Aufrufe (und Kosten) wieder eintragen – Budget bleibt korrekt."""
    from decimal import Decimal

    from ki.models import KiAufruf

    summe = Decimal(0)
    for felder in ctx.ki_mitschnitt:
        if not KiAufruf.objects.filter(pk=felder["id"]).exists():
            KiAufruf.objects.create(**felder)
        summe += Decimal(felder.get("kosten_cent") or 0)
    if summe:
        AgentenAuftrag.objects.filter(pk=ctx.auftrag.pk).update(kosten_cent=summe)


def ausfuehren(auftrag: AgentenAuftrag) -> AgentenAuftrag:
    register_laden()
    definition = REGISTER[auftrag.agent_id]
    handler = definition.aufgaben[auftrag.aufgabe]
    ctx = Kontext(auftrag, auftrag.agent)
    ctx.protokoll("start", aufgabe=auftrag.aufgabe, versuch=auftrag.versuche)
    kosten_vorher = auftrag.kosten_cent
    try:
        with transaction.atomic():
            ergebnis = handler(ctx) or {}
    except BaseException:
        auftrag.kosten_cent = kosten_vorher
        _ki_kosten_nachtragen(ctx)
        auftrag.refresh_from_db(fields=["kosten_cent"])
        try:
            raise
        except Eskalation as e:
            return _nach_eskalation(auftrag, ctx, e)
        except ki.BudgetErschoepft as e:
            return _nach_budget(auftrag, ctx, e)
        except Exception as e:  # noqa: BLE001 – jeder Fehler wird protokolliert und gezählt
            return _nach_fehler(auftrag, ctx, e)
    ctx.protokoll("ergebnis", **_json(ergebnis))
    _beenden(auftrag, Auftragsstatus.ERLEDIGT, ergebnis=ergebnis)
    auftrag.refresh_from_db()
    return auftrag


def _nach_eskalation(auftrag, ctx, e: Eskalation) -> AgentenAuftrag:
    ctx.protokoll("eskalation", grund=e.grund)
    _beenden(auftrag, Auftragsstatus.ESKALIERT, ergebnis={"eskalation": e.grund}, fehler=None)
    _eskalieren(auftrag, e.grund, e.vorschlag)
    auftrag.refresh_from_db()
    return auftrag


def _nach_budget(auftrag, ctx, e: Exception) -> AgentenAuftrag:
    ctx.protokoll("abbruch", grund=str(e))
    if auftrag.versuche >= auftrag.max_versuche:
        _beenden(auftrag, Auftragsstatus.FEHLGESCHLAGEN, fehler=str(e))
        _eskalieren(auftrag, f"Budget dauerhaft erschöpft: {e}")
    else:
        morgen = timezone.localdate() + timedelta(days=1)
        _zuruecklegen(auftrag, timezone.make_aware(datetime.combine(morgen, time(6, 0))), str(e))
    auftrag.refresh_from_db()
    return auftrag


def _nach_fehler(auftrag, ctx, e: Exception) -> AgentenAuftrag:
    text = f"{type(e).__name__}: {e}"
    ctx.protokoll("fehler", fehler=text, verlauf=traceback.format_exc(limit=5)[-3000:])
    log.warning("Agentenauftrag %s fehlgeschlagen: %s", auftrag.id, text)
    if auftrag.versuche < auftrag.max_versuche and not isinstance(e, GrenzeErreicht):
        _zuruecklegen(auftrag, timezone.now() + timedelta(minutes=2 ** auftrag.versuche), text)
    else:
        _beenden(auftrag, Auftragsstatus.FEHLGESCHLAGEN, fehler=text)
        _eskalieren(auftrag, f"Fehlgeschlagen nach {auftrag.versuche} Versuch(en): {text}"[:280])
    auftrag.refresh_from_db()
    return auftrag


def arbeiten(max_auftraege: int = 50, max_sekunden: int = 240) -> dict:
    """Arbeitet fällige Aufträge ab (ein Lauf des Workers; per systemd-Timer/Cron jede Minute)."""
    ende = timezone.now() + timedelta(seconds=max_sekunden)
    zaehler = {"erledigt": 0, "fehlgeschlagen": 0, "eskaliert": 0, "wartend": 0}
    for _ in range(max_auftraege):
        if timezone.now() > ende:
            break
        auftrag = holen()
        if auftrag is None:
            break
        ergebnis = ausfuehren(auftrag)
        zaehler[ergebnis.status if ergebnis.status in zaehler else "wartend"] += 1
    return zaehler
