"""Make-Webhook: Token, Idempotenz, Anfrage + Ereignis."""

import json

import pytest

from agenten.models import Ereignis
from auftraege.models import Anfrage

pytestmark = pytest.mark.django_db
URL = "/api/make/anfrage"
DATEN = {"name": "Erika Beispiel", "email": "erika@example.org", "plz": "33330", "ort": "Gütersloh",
         "nachricht": "Bitte Angebot Heckenschnitt", "leistungen": ["Heckenschnitt"], "referenz": "make-123"}


def _post(client, daten, token="geheim-test"):
    return client.post(URL, json.dumps(daten), content_type="application/json", headers={"X-HH-Token": token})


def test_ohne_token_abgeschaltet(client, monkeypatch):
    monkeypatch.delenv("MAKE_WEBHOOK_TOKEN", raising=False)
    assert _post(client, DATEN).status_code == 404


def test_falscher_token_und_ungueltige_daten(client, monkeypatch):
    monkeypatch.setenv("MAKE_WEBHOOK_TOKEN", "geheim-test")
    assert _post(client, DATEN, token="falsch").status_code == 401
    assert _post(client, {"x": 1}).status_code == 400
    assert client.get(URL).status_code == 405


def test_anfrage_wird_angelegt_und_ist_wiederholbar(client, monkeypatch):
    monkeypatch.setenv("MAKE_WEBHOOK_TOKEN", "geheim-test")
    erst = _post(client, DATEN)
    assert erst.status_code == 201
    a = Anfrage.objects.get()
    assert a.kunde.email == "erika@example.org" and a.gewuenschte_leistungen == ["Heckenschnitt"]
    assert Ereignis.objects.filter(typ="anfrage.neu", bezug_id=a.id).exists()
    zweit = _post(client, DATEN)
    assert zweit.json()["doppelt"] is True and Anfrage.objects.count() == 1
