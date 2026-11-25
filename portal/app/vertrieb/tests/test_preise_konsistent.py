"""Alle Preis-Stellen passen zur einen Preisliste (Firmenprofil, Webseite inkl. Preisrechner)."""

import importlib.util
from pathlib import Path

import pytest

WERKZEUG = Path(__file__).resolve().parents[4] / "werkzeuge" / "preise.py"


@pytest.mark.skipif(not WERKZEUG.exists(), reason="nur im vollständigen Repository")
def test_profil_und_webseite_passen_zur_preisliste(capsys):
    spec = importlib.util.spec_from_file_location("preise", WERKZEUG)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    assert modul.main(["--pruefen"]) == 0, capsys.readouterr().out
