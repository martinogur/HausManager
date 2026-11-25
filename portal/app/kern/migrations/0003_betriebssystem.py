"""
Erweiterung „Betriebssystem“: Akquise, Agenten, Freigaben, Ereignisse, Automatisierungen,
Redaktionskalender, Firmenparameter und Auftragssteuerung.

SQL-Quelle: ``portal/db/erweiterungen/0003_betriebssystem.sql`` (zur Laufzeit gelesen, wie 0001).
Rückweg: ``0003_betriebssystem_zurueck.sql``.
"""

from pathlib import Path

from django.db import migrations

ORDNER = (Path(__file__).resolve().parent / "../../../db/erweiterungen").resolve()


def _sql(name: str) -> str:
    return (ORDNER / name).read_text(encoding="utf-8")


class Migration(migrations.Migration):
    # ALTER TYPE … ADD VALUE ist in einer Transaktion erlaubt, der Wert ist aber erst danach nutzbar.
    # Die Datei verwendet ihn nur in PL/pgSQL (Laufzeit), daher reicht eine Transaktion.
    dependencies = [("kern", "0002_zwischenspeicher")]

    operations = [
        migrations.RunSQL(
            sql=[_sql("0003_betriebssystem.sql")],
            reverse_sql=[_sql("0003_betriebssystem_zurueck.sql")],
        ),
    ]
