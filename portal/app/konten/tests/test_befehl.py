"""Management-Befehl admin_anlegen."""

import pytest
from django.core.management import CommandError, call_command

from konten.models import Benutzer


@pytest.mark.django_db
def test_admin_anlegen_mit_umgebungsvariable(monkeypatch):
    monkeypatch.setenv("HH_ADMIN_PASSWORT", "Sehr-geheimes-Testpasswort-1")
    call_command("admin_anlegen", "--email", "inhaber@example.org", "--name", "Inhaber Beispiel")
    benutzer = Benutzer.objects.get(email="inhaber@example.org")
    assert benutzer.rolle == "admin"
    assert benutzer.check_password("Sehr-geheimes-Testpasswort-1")
    assert benutzer.is_superuser


@pytest.mark.django_db
def test_admin_anlegen_schwaches_passwort(monkeypatch):
    monkeypatch.setenv("HH_ADMIN_PASSWORT", "12345678")
    with pytest.raises(CommandError):
        call_command("admin_anlegen", "--email", "inhaber@example.org", "--name", "Inhaber")
    assert not Benutzer.objects.exists()


@pytest.mark.django_db
def test_admin_anlegen_ohne_passwort_und_ohne_terminal(monkeypatch):
    monkeypatch.delenv("HH_ADMIN_PASSWORT", raising=False)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False, raising=False)
    with pytest.raises(CommandError):
        call_command("admin_anlegen", "--email", "inhaber@example.org", "--name", "Inhaber")


@pytest.mark.django_db
def test_admin_anlegen_doppelt(monkeypatch, admin_benutzer):
    monkeypatch.setenv("HH_ADMIN_PASSWORT", "Sehr-geheimes-Testpasswort-1")
    with pytest.raises(CommandError):
        call_command("admin_anlegen", "--email", "ADMIN@example.org", "--name", "Doppelt")
