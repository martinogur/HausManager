"""Auftragsstatus-Dienst: Python-Regeln = Datenbank-Regeln."""

import pytest
from django.db import connection

from auftraege import status as st
from auftraege.models import Auftragsstatus, Rechnung
from stammdaten import testhilfen as th

pytestmark = pytest.mark.django_db


def test_python_tabelle_entspricht_dem_trigger():
    with connection.cursor() as c:
        c.execute("SELECT pg_get_functiondef('hh.auftrag_statuswechsel_pruefen'::regproc)")
        quelltext = c.fetchone()[0]
    for alt, neue in st.ERLAUBT.items():
        erwartet = "ARRAY[" + ", ".join(f"'{n}'" for n in neue) + "]" if neue else "ARRAY[]::text[]"
        assert f"WHEN '{alt}'" in quelltext and erwartet in quelltext.split(f"WHEN '{alt}'")[1].split("\n")[0], alt


def test_ablauf_bis_abgerechnet():
    a = th.auftrag(status=Auftragsstatus.ANFRAGE)
    for neu in ("zu_pruefen", "angebot", "bestaetigt", "geplant", "in_arbeit", "erledigt"):
        a = st.status_wechseln(a, neu)
    assert a.status == "erledigt" and a.bestaetigt_am is not None
    with pytest.raises(st.StatuswechselFehler, match="Rechnung"):
        st.status_wechseln(a, "abgerechnet")
    Rechnung.objects.create(kunde=a.kunde, auftrag=a, summe_netto_cent=1000, summe_brutto_cent=1190)
    a = st.status_wechseln(a, "abgerechnet")
    assert a.status == "abgerechnet" and st.moegliche_wechsel(a) == []


def test_verbotener_sprung_mit_klarer_meldung():
    a = th.auftrag(status=Auftragsstatus.ANFRAGE)
    with pytest.raises(st.StatuswechselFehler, match="nicht direkt"):
        st.status_wechseln(a, "erledigt")
    assert ("zu_pruefen", "Zu prüfen") in st.moegliche_wechsel(a)
