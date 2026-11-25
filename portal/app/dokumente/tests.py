import pytest
from django.db import IntegrityError, transaction

from dokumente.models import Dokument, Foto
from stammdaten import testhilfen as th

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("modell", [Dokument, Foto], ids=lambda m: m.__name__)
def test_schema_abgleich(modell):
    th.pruefe_schema(modell)


def _dokument(**bezug):
    return Dokument.objects.create(
        dateiname="vorher.jpg", mime_typ="image/jpeg", groesse_bytes=1234, sha256="a" * 64,
        speicher_schluessel=f"pytest/{len(bezug)}/{list(bezug)}", kategorie="foto", **bezug,
    )


def test_dokument_und_foto_zum_einsatz():
    e = th.einsatz()
    d = _dokument(einsatz=e)
    f = Foto.objects.create(dokument=d, einsatz=e, typ="vorher")
    assert list(e.fotos.all()) == [f] and d.foto == f and d.erstellt_am is not None
    e.delete()  # Fotos und Dokumente des Einsatzes werden mitgelöscht
    assert not Dokument.objects.filter(pk=d.pk).exists()


def test_dokument_braucht_bezug():
    with pytest.raises(IntegrityError), transaction.atomic():
        _dokument()


def test_gleicher_inhalt_am_gleichen_ort_nur_einmal():
    k = th.kunde()
    _dokument(kunde=k)
    with pytest.raises(IntegrityError), transaction.atomic():
        Dokument.objects.create(
            dateiname="kopie.jpg", mime_typ="image/jpeg", groesse_bytes=1234, sha256="a" * 64,
            speicher_schluessel="pytest/kopie", kategorie="foto", kunde=k,
        )
