"""Agenten-Laufzeit: Register, Grenzen, Wiederholung, Eskalation, Delegation, KI-Budget und Kosten."""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from agenten import automatisierung, ki, laufzeit
from agenten.laufzeit import aufgabe
from agenten.models import Agent, AgentenAuftrag, Firmenparameter, Freigabe
from ki.models import KiAufruf

pytestmark = pytest.mark.django_db
B = ZoneInfo("Europe/Berlin")


def test_register_vollstaendig(system):
    codes = set(Agent.objects.values_list("code", flat=True))
    assert codes == {"ceo", "sales", "lead_research", "marketing", "social", "seo", "kundenservice", "angebot",
                     "dispatch", "hr", "finance", "quality", "automation"}
    for d in laufzeit.REGISTER.values():
        assert d.aufgaben, f"{d.code} hat keine Aufgaben"
        assert d.erfolgsmessung and d.verantwortung
    # Betriebswerte aus der DB bleiben bei erneuter Synchronisation erhalten
    Agent.objects.filter(code="sales").update(tagesbudget_cent=7, aktiv=False)
    laufzeit.synchronisieren()
    assert Agent.objects.filter(code="sales", tagesbudget_cent=7, aktiv=False).exists()


@pytest.fixture
def testaufgaben():
    """Zusätzliche Test-Aufgaben am Automations-Agenten (werden danach entfernt)."""
    aufgaben = laufzeit.REGISTER["automation"].aufgaben
    vorher = dict(aufgaben)

    @aufgabe("automation", "test_fehler")
    def _fehler(ctx):
        raise RuntimeError("kaputt")

    @aufgabe("automation", "test_eskalation")
    def _esk(ctx):
        raise laufzeit.Eskalation("Bitte entscheiden", {"option": "A"})

    @aufgabe("automation", "test_viele_schritte")
    def _schritte(ctx):
        for i in range(100):
            ctx.schritt(f"s{i}")

    @aufgabe("automation", "test_ki_dann_fehler")
    def _ki_fehler(ctx):
        ctx.ki(zweck="test", system="s", eingabe="e", schema={"type": "object", "properties": {}, "required": []})
        raise RuntimeError("nach KI-Aufruf")

    yield
    aufgaben.clear()
    aufgaben.update(vorher)


def test_fehler_wiederholen_mit_backoff_dann_eskalation(system, testaufgaben):
    a = laufzeit.beauftragen("automation", "test_fehler", ausgeloest_von="test")
    for versuch in range(1, a.max_versuche + 1):
        AgentenAuftrag.objects.filter(pk=a.pk).update(faellig_ab=timezone.now() - timezone.timedelta(hours=1))
        a = laufzeit.ausfuehren(laufzeit.holen())
        assert a.versuche == versuch
    assert a.status == "fehlgeschlagen" and "kaputt" in a.fehler
    esk = Freigabe.objects.get(art="eskalation", bezug_id=a.id)
    assert esk.prioritaet == "hoch" and esk.status == "offen"
    assert list(a.protokoll.values_list("art", flat=True)).count("fehler") == a.max_versuche


def test_eskalation_und_schrittgrenze(system, testaufgaben):
    e = laufzeit.sofort_ausfuehren(laufzeit.beauftragen("automation", "test_eskalation", ausgeloest_von="test"))
    assert e.status == "eskaliert" and Freigabe.objects.get(bezug_id=e.id).vorschlag["option"] == "A"
    s = laufzeit.sofort_ausfuehren(laufzeit.beauftragen("automation", "test_viele_schritte", ausgeloest_von="test"))
    assert s.status == "fehlgeschlagen" and "Schritte" in s.fehler and s.versuche == 1   # Grenze: keine Wiederholung


def test_delegation_nur_an_erlaubte_agenten_und_idempotent(system):
    wurzel = laufzeit.beauftragen("ceo", "tagesstart", ausgeloest_von="test")
    kind = laufzeit.beauftragen("sales", "wiedervorlagen", ausgeloest_von="agent:ceo", eltern=wurzel, idempotenz="x1")
    assert kind.kette_id == wurzel.id and kind.tiefe == 1
    assert laufzeit.beauftragen("sales", "wiedervorlagen", ausgeloest_von="agent:ceo", eltern=wurzel, idempotenz="x1").pk == kind.pk
    with pytest.raises(laufzeit.DelegationVerboten):
        laufzeit.beauftragen("ceo", "wochenbericht", ausgeloest_von="agent:sales", eltern=kind)
    with pytest.raises(ValueError):
        laufzeit.beauftragen("sales", "gibt_es_nicht", ausgeloest_von="test")


def test_inaktiver_agent_wird_nicht_abgearbeitet(system):
    Agent.objects.filter(code="finance").update(aktiv=False)
    laufzeit.beauftragen("finance", "zahlungen_pruefen", ausgeloest_von="test")
    assert laufzeit.holen() is None


def test_ki_aufruf_protokolliert_kosten_und_schema(fake_ki):
    sdk = fake_ki(antworten=[{"zusammenfassung": "x", "entscheidungen": [], "risiken": []}])
    a = laufzeit.sofort_ausfuehren(laufzeit.beauftragen("ceo", "wochenbericht", ausgeloest_von="test"))
    assert a.status == "erledigt" and a.ergebnis["quelle"] == "ki"
    anfrage = sdk.anfragen[0]
    assert anfrage["model"] == "claude-opus-5-5" and anfrage["fallbacks"] == "default"
    assert anfrage["output_config"]["format"]["type"] == "json_schema" and anfrage["output_config"]["effort"] == "medium"
    aufruf = KiAufruf.objects.get(agenten_auftrag=a)
    # 1000 × 4 $/MTok + 200 × 20 $/MTok = 0,008 $ = 0,8 Cent
    assert aufruf.erfolgreich and aufruf.kosten_cent == Decimal("0.8000") and aufruf.agent_id == "ceo"
    assert a.kosten_cent == Decimal("0.8000")


def test_budget_erschoepft_faellt_auf_regel_zurueck(fake_ki):
    fake_ki(antworten=[{"zusammenfassung": "x", "entscheidungen": [], "risiken": []}])
    Agent.objects.filter(code="ceo").update(tagesbudget_cent=0)
    a = laufzeit.sofort_ausfuehren(laufzeit.beauftragen("ceo", "wochenbericht", ausgeloest_von="test"))
    assert a.status == "erledigt" and a.ergebnis["quelle"] == "regel"
    assert not KiAufruf.objects.exists()
    Agent.objects.filter(code="ceo").update(tagesbudget_cent=100)
    Firmenparameter.objects.filter(schluessel="ki_aktiv").update(wert=False)
    b = laufzeit.sofort_ausfuehren(laufzeit.beauftragen("ceo", "wochenbericht", ausgeloest_von="test2"))
    assert b.ergebnis["quelle"] == "regel"


def test_ki_ablehnung_und_ungueltiges_json_werden_erkannt(fake_ki):
    fake_ki(stop_reason="refusal")
    with pytest.raises(ki.KiFehler, match="abgelehnt"):
        ki.client().strukturiert(zweck="t", system="s", eingabe="e", schema={"type": "object", "required": ["a"]})
    fake_ki(antworten=[{"b": 1}])
    with pytest.raises(ki.KiFehler, match="Schema"):
        ki.client().strukturiert(zweck="t", system="s", eingabe="e", schema={"type": "object", "required": ["a"]})
    assert KiAufruf.objects.filter(erfolgreich=False).count() == 2


def test_ki_kosten_bleiben_nach_rollback_erhalten(fake_ki, testaufgaben):
    fake_ki(antworten=[{}])
    Agent.objects.filter(code="automation").update(tagesbudget_cent=100)
    a = laufzeit.sofort_ausfuehren(laufzeit.beauftragen("automation", "test_ki_dann_fehler", ausgeloest_von="test"))
    assert a.status == "wartend", a.fehler   # Fehler → neuer Versuch geplant
    aufruf = KiAufruf.objects.get()
    assert aufruf.kosten_cent == Decimal("0.8000") and a.kosten_cent == Decimal("0.8000")


def test_ohne_api_schluessel_ist_ki_aus(system, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ki.KiAus):
        ki.KiClient().strukturiert(zweck="t", system="s", eingabe="e", schema={})


@pytest.mark.parametrize("spec, jetzt, erwartet", [
    ("taeglich 06:30", datetime(2026, 11, 25, 7, 0, tzinfo=B), datetime(2026, 11, 25, 6, 30, tzinfo=B)),
    ("taeglich 06:30", datetime(2026, 11, 25, 6, 0, tzinfo=B), datetime(2026, 11, 24, 6, 30, tzinfo=B)),
    ("woechentlich mo 07:00", datetime(2026, 11, 25, 8, 0, tzinfo=B), datetime(2026, 11, 23, 7, 0, tzinfo=B)),
    ("woechentlich mi 09:00", datetime(2026, 11, 25, 8, 0, tzinfo=B), datetime(2026, 11, 18, 9, 0, tzinfo=B)),
    ("stuendlich :05", datetime(2026, 11, 25, 8, 3, tzinfo=B), datetime(2026, 11, 25, 7, 5, tzinfo=B)),
    ("alle 3 min", datetime(2026, 11, 25, 8, 8, 30, tzinfo=B), datetime(2026, 11, 25, 8, 6, tzinfo=B)),
])
def test_zeitfenster(spec, jetzt, erwartet):
    assert automatisierung.letztes_fenster(spec, jetzt) == erwartet


def test_zeitplan_genau_einmal_je_fenster(system):
    jetzt = timezone.now()
    erst = automatisierung.zeitplan_ausfuehren(jetzt)
    assert "tagesstart" in erst and "wochenbericht" in erst
    assert automatisierung.zeitplan_ausfuehren(jetzt) == []
    assert AgentenAuftrag.objects.filter(agent="ceo", aufgabe="tagesstart").count() == 1
    with pytest.raises(ValueError):
        automatisierung.letztes_fenster("monatlich", jetzt)
