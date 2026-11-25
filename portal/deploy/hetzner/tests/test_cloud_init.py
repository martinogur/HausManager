"""
Statische Prüfung von cloud-init.yaml: Schema (falls cloud-init installiert), YAML, eingebettete
Skripte (bash -n, shellcheck falls vorhanden), .env-Variablen passend zu docker-compose.yml.

    python3 -m unittest discover -s portal/deploy/hetzner/tests -v
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # PyYAML fehlt → Tests überspringen
    raise unittest.SkipTest("PyYAML nicht installiert") from None

HIER = Path(__file__).resolve().parents[1]
CLOUD_INIT = HIER / "cloud-init.yaml"
COMPOSE = HIER.parent / "docker-compose.yml"


def dateien():
    return {f["path"]: f for f in yaml.safe_load(CLOUD_INIT.read_text())["write_files"]}


def skripte():
    return {p: f["content"] for p, f in dateien().items() if f["content"].startswith("#!")}


class CloudInitTest(unittest.TestCase):
    def test_kopfzeile_und_yaml(self):
        text = CLOUD_INIT.read_text()
        self.assertTrue(text.startswith("#cloud-config\n"))
        daten = yaml.safe_load(text)
        self.assertEqual(daten["runcmd"], [["bash", "/usr/local/sbin/hh-einrichten"]])
        for paket in ("git", "ufw", "unattended-upgrades"):
            self.assertIn(paket, daten["packages"])

    @unittest.skipUnless(shutil.which("cloud-init"), "cloud-init nicht installiert")
    def test_cloud_init_schema(self):
        ergebnis = subprocess.run(["cloud-init", "schema", "-c", str(CLOUD_INIT)], capture_output=True, text=True)
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout + ergebnis.stderr)

    def test_skripte_bash_n_und_shellcheck(self):
        erwartet = {"/usr/local/sbin/hh-einrichten", "/usr/local/bin/hh-compose", "/usr/local/bin/hh-update",
                    "/usr/local/bin/hh-backup", "/usr/local/bin/hh-admin-anlegen", "/usr/local/bin/hh-status"}
        self.assertEqual(set(skripte()), erwartet)
        with tempfile.TemporaryDirectory() as ordner:
            for pfad, inhalt in skripte().items():
                datei = Path(ordner) / Path(pfad).name
                datei.write_text(inhalt)
                ergebnis = subprocess.run(["bash", "-n", str(datei)], capture_output=True, text=True)
                self.assertEqual(ergebnis.returncode, 0, f"{pfad}: {ergebnis.stderr}")
                self.assertEqual(dateien()[pfad]["permissions"], "0755")
                if shutil.which("shellcheck"):
                    ergebnis = subprocess.run(["shellcheck", "-S", "warning", "-e", "SC1090", str(datei)],
                                              capture_output=True, text=True)
                    self.assertEqual(ergebnis.returncode, 0, f"{pfad}:\n{ergebnis.stdout}")

    def test_env_enthaelt_alle_pflichtvariablen_der_compose_datei(self):
        pflicht = set(re.findall(r"\$\{([A-Z_]+):\?", COMPOSE.read_text()))
        self.assertTrue({"DJANGO_SECRET_KEY", "POSTGRES_PASSWORD", "DATABASE_URL", "ACME_EMAIL"} <= pflicht)
        einrichten = skripte()["/usr/local/sbin/hh-einrichten"]
        env_block = einrichten.split('cat > "$tmp" <<EOF', 1)[1].split("\nEOF", 1)[0]
        gesetzt = set(re.findall(r"^([A-Z_]+)=", env_block, re.M))
        self.assertTrue(pflicht <= gesetzt, f"fehlt: {pflicht - gesetzt}")
        for name in ("DJANGO_DEBUG", "DJANGO_ALLOWED_HOSTS", "DJANGO_CSRF_TRUSTED_ORIGINS", "PORTAL_DOMAIN",
                     "ACME_EMAIL", "DJANGO_MEDIA_ROOT", "RESTIC_PASSWORD"):
            self.assertIn(name, gesetzt)
        self.assertIn("DJANGO_DEBUG=0", env_block)
        self.assertIn("openssl rand", env_block)
        self.assertNotIn("PLATZHALTER", env_block)

    def test_keine_geheimnisse_und_kein_ssh(self):
        text = CLOUD_INIT.read_text()
        self.assertNotRegex(text, r"(?i)(password|passwort|secret_key)\s*[:=]\s*['\"]?[A-Za-z0-9]{16,}")
        self.assertNotIn("ssh_authorized_keys", text)
        einrichten = skripte()["/usr/local/sbin/hh-einrichten"]
        self.assertIn("ufw default deny incoming", einrichten)
        erlaubt = re.findall(r"^\s*ufw allow (\S+)", einrichten, re.M)
        self.assertEqual(sorted(erlaubt), ["443/tcp", "443/udp", "80/tcp"])

    def test_systemd_units(self):
        d = dateien()
        self.assertIn("OnUnitInactiveSec=15min", d["/etc/systemd/system/hh-update.timer"]["content"])
        self.assertIn("OnCalendar=", d["/etc/systemd/system/hh-backup.timer"]["content"])
        self.assertIn("WantedBy=multi-user.target", d["/etc/systemd/system/hh-portal.service"]["content"])
        if shutil.which("systemd-analyze"):
            with tempfile.TemporaryDirectory() as ordner:
                for pfad, f in d.items():
                    if pfad.startswith("/etc/systemd/system/"):
                        (Path(ordner) / Path(pfad).name).write_text(f["content"])
                einheiten = sorted(str(p) for p in Path(ordner).iterdir())
                ergebnis = subprocess.run(["systemd-analyze", "verify", *einheiten], capture_output=True, text=True)
                # Fehlende Programme (/usr/local/bin/hh-*) im Testsystem sind erwartbar
                fehler = [z for z in ergebnis.stderr.splitlines()
                          if z.strip() and "/usr/local/bin/hh-" not in z and "docker.service" not in z
                          and "Command" not in z]
                self.assertEqual(fehler, [], ergebnis.stderr)


if __name__ == "__main__":
    unittest.main()
