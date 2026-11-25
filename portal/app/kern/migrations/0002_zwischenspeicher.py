"""
Tabelle für Djangos Datenbank-Zwischenspeicher (``hh.django_cache``).

Wird u. a. für die Anmeldesperre genutzt, damit sie über alle
Gunicorn-Prozesse hinweg gilt. Struktur wie ``manage.py createcachetable``.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("kern", "0001_schema")]

    operations = [
        migrations.RunSQL(
            sql=[
                """
                CREATE TABLE IF NOT EXISTS hh.django_cache (
                    cache_key varchar(255) NOT NULL PRIMARY KEY,
                    value     text NOT NULL,
                    expires   timestamptz NOT NULL
                )
                """,
                "CREATE INDEX IF NOT EXISTS django_cache_expires ON hh.django_cache (expires)",
            ],
            reverse_sql=["DROP TABLE IF EXISTS hh.django_cache"],
        ),
    ]
