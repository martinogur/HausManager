"""Modelle passen exakt zu den Tabellen aus 0003_betriebssystem.sql."""

import pytest

from agenten.models import (
    Agent, AgentenAuftrag, AgentenProtokoll, Automatisierung, AutomatisierungsLauf, Ereignis, Firmenparameter, Freigabe,
)
from auftraege.models import Auftrag
from ki.models import KiAufruf
from marketing.models import SocialBeitrag
from stammdaten import testhilfen as th
from vertrieb.models import Lead, LeadKontakt

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "modell",
    [Agent, AgentenAuftrag, AgentenProtokoll, Automatisierung, AutomatisierungsLauf, Ereignis, Firmenparameter,
     Freigabe, Lead, LeadKontakt, SocialBeitrag, Auftrag, KiAufruf],
    ids=lambda m: m.__name__,
)
def test_schema_abgleich(modell):
    th.pruefe_schema(modell)


def test_firmenparameter_vorbelegt():
    assert Firmenparameter.objects.get(schluessel="einsatzgebiet_radius_km").wert == 30
    assert Firmenparameter.objects.get(schluessel="einsatzgebiet_zentrum").wert["ort"] == "Gütersloh"
