"""Claude-API-Zugang für alle Agenten – mit Budget, Protokoll und klaren Fehlern.

Grundsätze
* Die KI liefert nur **Entwürfe und strukturierte Vorschläge** (JSON nach Schema). Entscheidungen,
  Versand und Preise bleiben bei Menschen bzw. deterministischem Code.
* Jeder Aufruf steht in ``ki_aufrufe`` (Zweck, Modell, Tokens, Kosten, Agent, Agentenauftrag).
* Vor jedem Aufruf: Hauptschalter ``ki_aktiv``, Tagesbudget gesamt (``ki_tagesbudget_gesamt_cent``)
  und Tagesbudget des Agenten (``agenten.tagesbudget_cent``). Überschreitung → ``BudgetErschoepft``.
* Ohne API-Schlüssel (``ANTHROPIC_API_KEY``) ist die KI aus: Agenten arbeiten dann regelbasiert.
* Modell: Claude Opus 5.5 (``claude-opus-5-5``) mit serverseitigem Fallback bei Ablehnungen
  (``fallbacks="default"``); Aufwand (``effort``) je Zweck, Standard ``low`` für Routine.
"""

import json
import os
from dataclasses import dataclass
from decimal import Decimal

from django.db import connection

from ki.models import KiAufruf

from .models import Agent, AgentenAuftrag, Firmenparameter

STANDARD_MODELL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"

# US-Dollar je 1 Mio. Tokens (Stand 11/2026) – als Cent gerechnet: 4 $ = 400 Cent.
PREISE_CENT_JE_MTOK = {
    "claude-opus-5-5": {"ein": Decimal(400), "aus": Decimal(2000), "cache_lesen": Decimal(20), "cache_schreiben": Decimal(500)},
    "claude-sonnet-5-5": {"ein": Decimal(200), "aus": Decimal(1000), "cache_lesen": Decimal(10), "cache_schreiben": Decimal(250)},
    "claude-haiku-5-5": {"ein": Decimal(10), "aus": Decimal(50), "cache_lesen": Decimal(1), "cache_schreiben": Decimal("12.5")},
}


class KiFehler(Exception):
    """Aufruf gescheitert (Netz, API, Ablehnung, ungültige Antwort)."""


class KiAus(KiFehler):
    """KI ist abgeschaltet oder nicht eingerichtet – regelbasiert weiterarbeiten."""


class BudgetErschoepft(KiFehler):
    """Tagesbudget erreicht – regelbasiert weiterarbeiten oder morgen erneut versuchen."""


@dataclass
class KiAntwort:
    daten: dict
    modell: str
    eingabe_tokens: int
    ausgabe_tokens: int
    kosten_cent: Decimal


def _parameter(schluessel: str, standard):
    try:
        return Firmenparameter.objects.get(schluessel=schluessel).wert
    except Firmenparameter.DoesNotExist:
        return standard


def kosten_cent(modell: str, nutzung) -> Decimal:
    preise = PREISE_CENT_JE_MTOK.get(modell, PREISE_CENT_JE_MTOK[STANDARD_MODELL])
    ein = Decimal(getattr(nutzung, "input_tokens", 0) or 0)
    aus = Decimal(getattr(nutzung, "output_tokens", 0) or 0)
    lesen = Decimal(getattr(nutzung, "cache_read_input_tokens", 0) or 0)
    schreiben = Decimal(getattr(nutzung, "cache_creation_input_tokens", 0) or 0)
    summe = ein * preise["ein"] + aus * preise["aus"] + lesen * preise["cache_lesen"] + schreiben * preise["cache_schreiben"]
    return (summe / Decimal(1_000_000)).quantize(Decimal("0.0001"))


def heutige_kosten(agent_code: str | None = None) -> Decimal:
    sql = "SELECT coalesce(sum(kosten_cent), 0) FROM ki_aufrufe WHERE (erstellt_am AT TIME ZONE 'Europe/Berlin')::date = (now() AT TIME ZONE 'Europe/Berlin')::date"
    parameter = []
    if agent_code:
        sql += " AND agent = %s"
        parameter.append(agent_code)
    with connection.cursor() as c:
        c.execute(sql, parameter)
        return Decimal(c.fetchone()[0])


def ki_eingerichtet() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY")) and _parameter("ki_aktiv", True) is True


class KiClient:
    """Dünne Schicht über dem Anthropic-SDK. ``sdk`` ist für Tests austauschbar (gleiche Schnittstelle)."""

    def __init__(self, sdk=None):
        self._sdk = sdk

    @property
    def sdk(self):
        if self._sdk is None:
            if not ki_eingerichtet():
                raise KiAus("KI ist aus (kein ANTHROPIC_API_KEY oder Firmenparameter ki_aktiv = false).")
            import anthropic

            # Schlüssel nur aus der Umgebung (SOPS → Container-Umgebung), nie aus dem Code.
            self._sdk = anthropic.Anthropic(max_retries=2)
        return self._sdk

    def budget_pruefen(self, agent: Agent | None) -> None:
        if self._sdk is None and not ki_eingerichtet():
            raise KiAus("KI ist aus.")
        if _parameter("ki_aktiv", True) is not True:
            raise KiAus("KI ist per Firmenparameter abgeschaltet.")
        gesamt = Decimal(str(_parameter("ki_tagesbudget_gesamt_cent", 200)))
        if heutige_kosten() >= gesamt:
            raise BudgetErschoepft(f"Tagesbudget aller Agenten ({gesamt} Cent) erreicht.")
        if agent is not None and heutige_kosten(agent.code) >= agent.tagesbudget_cent:
            raise BudgetErschoepft(f"Tagesbudget von {agent.name} ({agent.tagesbudget_cent} Cent) erreicht.")

    def strukturiert(self, *, zweck: str, system: str, eingabe: str, schema: dict, agent: Agent | None = None,
                     auftrag: AgentenAuftrag | None = None, max_tokens: int = 4000, effort: str = "low",
                     timeout_s: float = 90, bezug: tuple[str, object] | None = None,
                     mitschnitt: list | None = None) -> KiAntwort:
        """Ein Aufruf mit erzwungenem JSON-Schema (Structured Outputs). Gibt geprüftes dict zurück.

        ``mitschnitt``: Liste, in die jede Protokollzeile (Felder) zusätzlich geschrieben wird – damit die
        Laufzeit Kosten auch dann nachträgt, wenn die Transaktion der Aufgabe zurückgerollt wird."""

        def protokollieren(**felder):
            zeile = KiAufruf.objects.create(**felder)
            if mitschnitt is not None:
                mitschnitt.append({"id": zeile.id, **felder})

        self.budget_pruefen(agent)
        modell = (agent.modell if agent and agent.modell else STANDARD_MODELL)
        protokoll = dict(zweck=zweck, modell=modell, agent=agent, agenten_auftrag=auftrag,
                         bezug_tabelle=bezug[0] if bezug else None, bezug_id=bezug[1] if bezug else None)
        try:
            antwort = self.sdk.with_options(timeout=timeout_s).beta.messages.create(
                model=modell,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": eingabe}],
                output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except KiFehler:
            raise
        except Exception as fehler:  # SDK-Fehler (Netz, 4xx/5xx) – protokollieren, als KiFehler weitergeben
            protokollieren(erfolgreich=False, fehler=f"{type(fehler).__name__}: {fehler}"[:2000], **protokoll)
            raise KiFehler(f"Claude-API: {type(fehler).__name__}") from fehler

        modell_ist = getattr(antwort, "model", modell) or modell
        nutzung = getattr(antwort, "usage", None)
        kosten = kosten_cent(modell_ist, nutzung)
        ein, aus = getattr(nutzung, "input_tokens", 0) or 0, getattr(nutzung, "output_tokens", 0) or 0
        protokoll["modell"] = modell_ist

        def scheitern(text: str):
            protokollieren(erfolgreich=False, fehler=text, eingabe_tokens=ein, ausgabe_tokens=aus,
                           kosten_cent=kosten, **protokoll)
            raise KiFehler(text)

        if antwort.stop_reason == "refusal":
            scheitern("Anfrage von der KI abgelehnt (refusal).")
        if antwort.stop_reason == "max_tokens":
            scheitern("Antwort abgeschnitten (max_tokens).")
        text = next((b.text for b in antwort.content if getattr(b, "type", None) == "text"), None)
        try:
            daten = json.loads(text or "")
        except (TypeError, ValueError):
            scheitern("Antwort ist kein gültiges JSON.")
        if not isinstance(daten, dict) or any(k not in daten for k in schema.get("required", [])):
            scheitern("Antwort passt nicht zum Schema.")
        protokollieren(erfolgreich=True, eingabe_tokens=ein, ausgabe_tokens=aus, kosten_cent=kosten, **protokoll)
        if auftrag is not None:
            AgentenAuftrag.objects.filter(pk=auftrag.pk).update(kosten_cent=auftrag.kosten_cent + kosten)
            auftrag.kosten_cent += kosten
        return KiAntwort(daten, modell_ist, ein, aus, kosten)


#: Gemeinsamer Client (Tests ersetzen ihn über ``setze_client``).
_client = KiClient()


def client() -> KiClient:
    return _client


def setze_client(neu: KiClient) -> KiClient:
    global _client
    alt, _client = _client, neu
    return alt
