"""
Benutzer-Modell (Tabelle ``hh.benutzer`` aus schema.sql, managed=False).

Ergänzt die Spalten, die Djangos Anmeldung braucht: ``password`` und
``last_login``. Bestehende Zeilen bekommen ein unbrauchbares Passwort ("!"),
können sich also erst nach dem Setzen eines Passworts anmelden.
"""

import uuid

import django.utils.timezone
from django.db import migrations, models

import konten.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [("kern", "0001_schema")]

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE hh.benutzer ADD COLUMN IF NOT EXISTS password varchar(128) NOT NULL DEFAULT '!'",
                "ALTER TABLE hh.benutzer ADD COLUMN IF NOT EXISTS last_login timestamptz NULL",
            ],
            reverse_sql=[
                "ALTER TABLE hh.benutzer DROP COLUMN IF EXISTS last_login",
                "ALTER TABLE hh.benutzer DROP COLUMN IF EXISTS password",
            ],
        ),
        migrations.CreateModel(
            name="Benutzer",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254, unique=True, verbose_name="E-Mail")),
                ("anzeigename", models.CharField(max_length=200, verbose_name="Anzeigename")),
                (
                    "rolle",
                    models.CharField(
                        choices=[("admin", "Administrator"), ("buero", "Büro"), ("mitarbeiter", "Mitarbeiter")],
                        default="mitarbeiter",
                        max_length=20,
                        verbose_name="Rolle",
                    ),
                ),
                ("aktiv", models.BooleanField(default=True, verbose_name="Aktiv")),
                (
                    "zwei_faktor",
                    models.BooleanField(
                        default=False,
                        help_text="Wird bei der 2FA-Einrichtung automatisch gesetzt.",
                        verbose_name="Zwei-Faktor eingerichtet",
                    ),
                ),
                (
                    "erstellt_am",
                    models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="Erstellt am"),
                ),
                (
                    "geaendert_am",
                    models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="Geändert am"),
                ),
            ],
            options={
                "verbose_name": "Benutzer",
                "verbose_name_plural": "Benutzer",
                "db_table": "benutzer",
                "ordering": ["anzeigename"],
                "managed": False,
            },
            managers=[("objects", konten.models.BenutzerManager())],
        ),
    ]
