import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from kommunikation.models import EmailProtokoll
from stammdaten import testhilfen as th

pytestmark = pytest.mark.django_db

POSTFACH = "pytest@example.org"


@pytest.mark.parametrize("modell", [EmailProtokoll], ids=lambda m: m.__name__)
def test_schema_abgleich(modell):
    th.pruefe_schema(modell)


def test_email_eingang_und_antwortentwurf():
    eingang = EmailProtokoll.objects.create(
        richtung="eingang", message_id="<1@example.org>", postfach=POSTFACH, von="Absender@Example.org", an=[POSTFACH],
        betreff="Pytest", empfangen_am=timezone.now(),
    )
    assert eingang.status == "neu"
    assert list(EmailProtokoll.objects.offen()) == [eingang]
    eingang.refresh_from_db()
    assert eingang.an == [POSTFACH]
    antwort = EmailProtokoll.objects.create(
        richtung="ausgang", postfach=POSTFACH, von=POSTFACH, an=["absender@example.org"], status="entwurf",
        antwort_auf=eingang, entwurf_text="Vielen Dank …",
    )
    assert list(eingang.antworten.all()) == [antwort]
    # Doppelimport derselben Message-ID wird verhindert
    with pytest.raises(IntegrityError), transaction.atomic():
        EmailProtokoll.objects.create(richtung="eingang", message_id="<1@example.org>", postfach=POSTFACH, von="x@example.org", an=[POSTFACH])


def test_ausgehende_mail_nur_mit_freigabe():
    m = EmailProtokoll.objects.create(richtung="ausgang", postfach=POSTFACH, von=POSTFACH, an=["kunde@example.org"], status="entwurf")
    m.status = "freigegeben"
    with pytest.raises(IntegrityError), transaction.atomic():
        m.save()
    m.freigegeben_von = th.benutzer("admin")
    m.freigegeben_am = timezone.now()
    m.save()
    m.refresh_from_db()
    assert m.status == "freigegeben"
