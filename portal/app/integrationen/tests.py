import pytest
from django.db import IntegrityError, connection, transaction

from integrationen.models import AuditEintrag, NurLesendFehler, SyncProtokoll
from stammdaten import testhilfen as th

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("modell", [SyncProtokoll, AuditEintrag], ids=lambda m: m.__name__)
def test_schema_abgleich(modell):
    th.pruefe_schema(modell)


def test_sync_protokoll_idempotenz():
    SyncProtokoll.objects.create(system="lexware", richtung="export", objekt_typ="rechnung", idempotenz_schluessel="pytest-1", erfolgreich=True, http_status=201)
    with pytest.raises(IntegrityError), transaction.atomic():
        SyncProtokoll.objects.create(system="lexware", richtung="export", objekt_typ="rechnung", idempotenz_schluessel="pytest-1", erfolgreich=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        SyncProtokoll.objects.create(system="unbekannt", richtung="export", objekt_typ="x", erfolgreich=False)


def test_audit_eintrag_kommt_vom_trigger_und_ist_nur_lesend():
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.benutzer', 'pytest@example.org', true)")
    k = th.kunde()
    eintraege = list(AuditEintrag.objects.fuer(k))
    assert [e.aktion for e in eintraege] == ["INSERT"]
    assert eintraege[0].benutzer == "pytest@example.org"
    assert eintraege[0].neu["kundennummer"] == k.kundennummer
    with pytest.raises(NurLesendFehler):
        eintraege[0].save()
    with pytest.raises(NurLesendFehler):
        eintraege[0].delete()
    with pytest.raises(NurLesendFehler):
        AuditEintrag.objects.all().delete()
    with pytest.raises(NurLesendFehler):
        AuditEintrag.objects.update(benutzer="x")
