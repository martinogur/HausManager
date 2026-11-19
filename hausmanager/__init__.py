"""HausManager – eigene Immobilien verwalten + Hausmeister-Helden-Akquise."""
import os

# Minimaler .env-Loader (ohne Zusatzpaket): KEY=VALUE pro Zeile
_env = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env):
    with open(_env, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
