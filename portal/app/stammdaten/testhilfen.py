"""Hilfen für die Tests der Fach-Apps (nur fiktive Daten, keine Netzaufrufe)."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import connection

BERLIN = ZoneInfo("Europe/Berlin")


# ---------------------------------------------------------------- Schema-Abgleich
def db_spalten(tabelle: str) -> dict:
    """Spalten der Tabelle im Schema hh: Name → FieldInfo (aus Djangos Introspection)."""
    with connection.cursor() as cursor:
        return {spalte.name: spalte for spalte in connection.introspection.get_table_description(cursor, tabelle)}


def enum_werte(tabelle: str, spalte: str) -> list[str] | None:
    """Werte des PostgreSQL-ENUM-Typs einer Spalte (None, wenn die Spalte kein ENUM ist)."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT e.enumlabel
            FROM information_schema.columns c
            JOIN pg_type t ON t.typname = c.udt_name
            JOIN pg_enum e ON e.enumtypid = t.oid
            WHERE c.table_schema = 'hh' AND c.table_name = %s AND c.column_name = %s
            ORDER BY e.enumsortorder
            """,
            [tabelle, spalte],
        )
        werte = [zeile[0] for zeile in cursor.fetchall()]
    return werte or None


def modellfelder(modell):
    """Konkrete Felder mit eigener Spalte (ohne CompositePrimaryKey)."""
    return [f for f in modell._meta.concrete_fields if f.column]


def pruefe_schema(modell):
    """Jede Modellspalte existiert in der DB, jede DB-Spalte ist im Modell, NULL und ENUMs passen."""
    tabelle = modell._meta.db_table
    db = db_spalten(tabelle)
    assert db, f"Tabelle {tabelle} fehlt in der Datenbank"
    felder = {f.column: f for f in modellfelder(modell)}

    nur_modell = sorted(set(felder) - set(db))
    nur_db = sorted(set(db) - set(felder))
    assert not nur_modell, f"{tabelle}: Spalten nur im Modell: {nur_modell}"
    assert not nur_db, f"{tabelle}: Spalten nur in der Datenbank (fehlen im Modell): {nur_db}"

    for spalte, feld in felder.items():
        assert feld.null == bool(db[spalte].null_ok), (
            f"{tabelle}.{spalte}: NULL im Modell={feld.null}, in der DB={bool(db[spalte].null_ok)}"
        )
        werte = enum_werte(tabelle, spalte)
        if werte is not None:
            assert feld.choices, f"{tabelle}.{spalte} ist ein ENUM, das Modellfeld hat keine choices"
            assert [wert for wert, _ in feld.choices] == werte, f"{tabelle}.{spalte}: choices ≠ ENUM {werte}"


# ---------------------------------------------------------------- Testobjekte
def zeitpunkt(tag, stunde, minute=0):
    return datetime.combine(tag, time(stunde, minute), tzinfo=BERLIN)


def morgen_um(stunde, minute=0, tage=1):
    from django.utils import timezone

    return zeitpunkt(timezone.localdate() + timedelta(days=tage), stunde, minute)


def benutzer(rolle="mitarbeiter", email=None):
    email = email or f"{rolle}.pytest@example.org"
    return get_user_model().objects.create_user(email=email, anzeigename=f"Test {rolle}", rolle=rolle)


def kunde(name="Pytest Hausverwaltung GmbH", plz="33330", **mehr):
    from stammdaten.models import Kunde, Kundentyp

    return Kunde.objects.create(name=name, typ=mehr.pop("typ", Kundentyp.HAUSVERWALTUNG), plz=plz, **mehr)


def objekt(kunde_obj, strasse="Musterstraße", nr="99", plz="33330", **mehr):
    from stammdaten.models import Objekt

    return Objekt.objects.create(
        kunde=kunde_obj, bezeichnung=f"{strasse} {nr}", strasse=strasse, hausnummer=nr, plz=plz, ort="Gütersloh", **mehr
    )


def mitarbeiter(vorname="Pia", nachname="Pytest", konto=None, **mehr):
    from personal.models import Beschaeftigung, Mitarbeiter

    return Mitarbeiter.objects.create(
        vorname=vorname,
        nachname=nachname,
        beschaeftigung=mehr.pop("beschaeftigung", Beschaeftigung.TEILZEIT),
        benutzer=konto,
        **mehr,
    )


def auftrag(kunde_obj=None, objekt_obj=None, **mehr):
    from auftraege.models import Auftrag

    kunde_obj = kunde_obj or kunde()
    objekt_obj = objekt_obj or objekt(kunde_obj)
    return Auftrag.objects.create(kunde=kunde_obj, objekt=objekt_obj, titel=mehr.pop("titel", "Pytest-Auftrag"), **mehr)


def einsatz(auftrag_obj=None, von=None, bis=None, **mehr):
    from auftraege.models import Einsatz

    von = von or morgen_um(8)
    return Einsatz.objects.create(auftrag=auftrag_obj or auftrag(), geplant_von=von, geplant_bis=bis or von + timedelta(hours=2), **mehr)
