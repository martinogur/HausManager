"""
Legt das komplette Datenbankschema ``hh`` aus ``portal/db/schema.sql`` an.

Die Datei wird zur Laufzeit gelesen (nicht kopiert) – ``schema.sql`` bleibt die
einzige Quelle. Rückwärts wird das ganze Schema gelöscht.

``run_before`` sorgt dafür, dass das Schema existiert, bevor Djangos eigene
Tabellen (Sessions, Berechtigungen, Inhaltstypen) angelegt werden – so landen
auch diese im Schema ``hh`` (search_path = hh, public).
Hinweis: Die Verwaltungstabelle ``django_migrations`` entsteht schon vor jeder
Migration und liegt deshalb in ``public``.
"""

from pathlib import Path

from django.db import migrations

SCHEMA_DATEI = (Path(__file__).resolve().parent / "../../../db/schema.sql").resolve()


def schema_sql() -> str:
    return SCHEMA_DATEI.read_text(encoding="utf-8")


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    run_before = [
        ("contenttypes", "0001_initial"),
        ("sessions", "0001_initial"),
        ("auth", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            # Als Liste mit einem Eintrag: Die Datei wird in einem Stück
            # ausgeführt (nicht von sqlparse zerlegt – wichtig für $$-Blöcke).
            sql=[schema_sql()],
            reverse_sql=["DROP SCHEMA IF EXISTS hh CASCADE"],
        ),
    ]
