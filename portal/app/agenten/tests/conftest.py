import json
from types import SimpleNamespace

import pytest

from agenten import automatisierung, ki, laufzeit


class FakeSDK:
    """Ersetzt das Anthropic-SDK: gibt vorbereitete JSON-Antworten zurück und merkt sich die Anfragen."""

    def __init__(self, antworten=None, stop_reason="end_turn", fehler=None, tokens=(1000, 200)):
        self.antworten, self.stop_reason, self.fehler, self.tokens = list(antworten or []), stop_reason, fehler, tokens
        self.anfragen = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def with_options(self, **_):
        return self

    def _create(self, **kwargs):
        self.anfragen.append(kwargs)
        if self.fehler:
            raise self.fehler
        daten = self.antworten.pop(0) if self.antworten else {}
        return SimpleNamespace(
            model=kwargs["model"], stop_reason=self.stop_reason,
            content=[SimpleNamespace(type="text", text=json.dumps(daten))],
            usage=SimpleNamespace(input_tokens=self.tokens[0], output_tokens=self.tokens[1],
                                  cache_read_input_tokens=0, cache_creation_input_tokens=0),
        )


@pytest.fixture
def system(db):
    """Agenten und Automatisierungen in der Test-DB; KI standardmäßig aus (regelbasiert)."""
    laufzeit.synchronisieren()
    automatisierung.synchronisieren()
    alt = ki.setze_client(ki.KiClient())
    yield
    ki.setze_client(alt)


@pytest.fixture
def fake_ki(system):
    def einrichten(**kwargs):
        sdk = FakeSDK(**kwargs)
        ki.setze_client(ki.KiClient(sdk=sdk))
        return sdk

    return einrichten


@pytest.fixture
def buero(db):
    from stammdaten import testhilfen as th

    return th.benutzer("buero", "buero.agenten@example.org")


def alles_abarbeiten(runden=6):
    for _ in range(runden):
        automatisierung.ereignisse_verarbeiten()
        if not laufzeit.arbeiten(200, 60)["erledigt"] and not automatisierung.ereignisse_verarbeiten()["verarbeitet"]:
            break
