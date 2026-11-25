from decimal import Decimal

import pytest

from ki.models import KiAufruf
from stammdaten import testhilfen as th

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("modell", [KiAufruf], ids=lambda m: m.__name__)
def test_schema_abgleich(modell):
    th.pruefe_schema(modell)


def test_ki_aufruf_protokollieren():
    a = KiAufruf.objects.create(
        zweck="anfrage_zusammenfassen", modell="test-modell", eingabe_tokens=100, ausgabe_tokens=20,
        kosten_cent=Decimal("0.1234"), erfolgreich=True,
    )
    a.refresh_from_db()
    assert a.kosten_cent == Decimal("0.1234") and a.erstellt_am is not None
