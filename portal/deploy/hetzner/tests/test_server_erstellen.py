"""
Tests für server_erstellen.py gegen eine nachgebaute Hetzner-API (http.server, nur Standardbibliothek).

    python3 -m unittest discover -s portal/deploy/hetzner/tests -v
"""

import contextlib
import io
import json
import re
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server_erstellen as se  # noqa: E402


def preis(ort, netto):
    return {"location": ort, "price_monthly": {"net": f"{netto:.10f}", "gross": f"{netto * 1.19:.10f}"},
            "price_hourly": {"net": "0", "gross": "0"}}


SERVER_TYPES = [
    # zu klein
    {"id": 1, "name": "cx12", "cores": 1, "memory": 2.0, "disk": 20, "architecture": "x86", "cpu_type": "shared",
     "prices": [preis("nbg1", 3.0), preis("fsn1", 3.0)]},
    # ARM – ausgeschlossen, obwohl günstig
    {"id": 2, "name": "cax11", "cores": 2, "memory": 4.0, "disk": 40, "architecture": "arm", "cpu_type": "shared",
     "prices": [preis("nbg1", 3.5), preis("fsn1", 3.5)]},
    # abgekündigt – ausgeschlossen
    {"id": 3, "name": "cx22", "cores": 2, "memory": 4.0, "disk": 40, "architecture": "x86", "cpu_type": "shared",
     "deprecation": {"announced": "2025-01-01T00:00:00Z"}, "prices": [preis("nbg1", 3.79), preis("fsn1", 3.79)]},
    # günstigster passender Typ, aber in nbg1 nicht verfügbar → fsn1
    {"id": 4, "name": "cx23", "cores": 2, "memory": 4.0, "disk": 40, "architecture": "x86", "cpu_type": "shared",
     "prices": [preis("nbg1", 3.99), preis("fsn1", 3.99), preis("hel1", 2.0)]},
    {"id": 5, "name": "cpx22", "cores": 2, "memory": 4.0, "disk": 80, "architecture": "x86", "cpu_type": "shared",
     "prices": [preis("nbg1", 6.49), preis("fsn1", 6.49)]},
]
DATACENTERS = [
    {"name": "nbg1-dc3", "location": {"name": "nbg1"}, "server_types": {"available": [1, 2, 3, 5]}},
    {"name": "fsn1-dc14", "location": {"name": "fsn1"}, "server_types": {"available": [1, 2, 3, 4, 5]}},
    {"name": "hel1-dc2", "location": {"name": "hel1"}, "server_types": {"available": [4]}},
]


class FakeHetzner:
    """Zustand der nachgebauten API."""

    def __init__(self):
        self.firewalls, self.servers, self.anfragen = {}, {}, []
        self.naechste_id = 100
        self.token_erwartet = "test-token"
        self.auth_gesehen = set()

    def neue_id(self):
        self.naechste_id += 1
        return self.naechste_id

    def behandeln(self, methode, pfad, query, koerper, auth):
        self.anfragen.append((methode, pfad))
        self.auth_gesehen.add(auth)
        if auth != f"Bearer {self.token_erwartet}":
            return 401, {"error": {"code": "unauthorized", "message": "unable to authenticate"}}
        name = (query.get("name") or [None])[0]
        if methode == "GET" and pfad == "/server_types":
            return 200, {"server_types": SERVER_TYPES, "meta": {"pagination": {"next_page": None}}}
        if methode == "GET" and pfad == "/datacenters":
            # zwei Seiten, damit die Paginierung getestet wird
            seite = int((query.get("page") or ["1"])[0])
            teile = [DATACENTERS[:2], DATACENTERS[2:]]
            return 200, {"datacenters": teile[seite - 1], "meta": {"pagination": {"next_page": 2 if seite == 1 else None}}}
        if methode == "GET" and pfad == "/pricing":
            return 200, {"pricing": {"server_backup": {"percentage": "20.0000000000"},
                                     "primary_ips": [{"type": "ipv4", "prices": [preis("fsn1", 0.5), preis("nbg1", 0.5)]}]}}
        if methode == "GET" and pfad == "/firewalls":
            return 200, {"firewalls": [f for f in self.firewalls.values() if name in (None, f["name"])]}
        if methode == "POST" and pfad == "/firewalls":
            fw = {"id": self.neue_id(), "name": koerper["name"], "labels": koerper["labels"], "rules": koerper["rules"]}
            self.firewalls[fw["id"]] = fw
            return 201, {"firewall": fw, "actions": []}
        m = re.fullmatch(r"/firewalls/(\d+)(/actions/(\w+))?", pfad)
        if m:
            fw = self.firewalls[int(m.group(1))]
            if methode == "DELETE":
                if any(fw["id"] in [f["id"] for f in s["public_net"]["firewalls"]] for s in self.servers.values()):
                    return 422, {"error": {"code": "resource_in_use", "message": "firewall in use"}}
                del self.firewalls[fw["id"]]
                return 204, None
            if m.group(3) == "set_rules":
                fw["rules"] = koerper["rules"]
            return 201, {"actions": [{"id": 1, "status": "running"}]}
        if methode == "GET" and pfad == "/servers":
            return 200, {"servers": [s for s in self.servers.values() if name in (None, s["name"])]}
        if methode == "POST" and pfad == "/servers":
            typ = next(t for t in SERVER_TYPES if t["name"] == koerper["server_type"])
            s = {"id": self.neue_id(), "name": koerper["name"], "status": "initializing", "server_type": typ,
                 "labels": koerper["labels"], "backup_window": None, "user_data": koerper["user_data"],
                 "datacenter": {"location": {"name": koerper["location"]}},
                 "public_net": {"ipv4": {"ip": "203.0.113.10"}, "ipv6": {"ip": "2001:db8:1::/64"},
                                "firewalls": [{"id": f["firewall"], "status": "applied"} for f in koerper["firewalls"]]},
                 "abfragen": 0}
            self.servers[s["id"]] = s
            return 201, {"server": s, "action": {"id": 2}, "root_password": "GEHEIM-root-pw"}
        m = re.fullmatch(r"/servers/(\d+)(/actions/(\w+))?", pfad)
        if m:
            s = self.servers[int(m.group(1))]
            if methode == "GET":
                s["abfragen"] += 1
                if s["abfragen"] >= 2:
                    s["status"] = "running"
                return 200, {"server": s}
            if methode == "DELETE":
                del self.servers[s["id"]]
                return 200, {"action": {"id": 3}}
            if m.group(3) == "enable_backup":
                s["backup_window"] = "22-02"
                return 201, {"action": {"id": 4}}
        return 404, {"error": {"code": "not_found", "message": pfad}}


def handler_fuer(fake):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _antworten(self):
            teile = urlsplit(self.path)
            pfad = teile.path.removeprefix("/v1")
            laenge = int(self.headers.get("Content-Length") or 0)
            koerper = json.loads(self.rfile.read(laenge)) if laenge else None
            status, daten = fake.behandeln(self.command, pfad, parse_qs(teile.query), koerper,
                                           self.headers.get("Authorization"))
            inhalt = b"" if daten is None else json.dumps(daten).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(inhalt)))
            self.end_headers()
            self.wfile.write(inhalt)

        do_GET = do_POST = do_DELETE = do_PUT = _antworten

    return Handler


class ServerErstellenTest(unittest.TestCase):
    def setUp(self):
        self.fake = FakeHetzner()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler_fuer(self.fake))
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def lauf(self, *argv, token="test-token"):
        api = se.Hetzner(self.url, token=token, warte=lambda s: None)
        aus, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(aus), contextlib.redirect_stderr(err):
            rc = se.main(list(argv), api=api)
        return rc, aus.getvalue() + err.getvalue(), api

    def schreibend(self):
        return [a for a in self.fake.anfragen if a[0] != "GET"]

    def test_trockenlauf_aendert_nichts_und_zeigt_preis(self):
        rc, aus, api = self.lauf("--trockenlauf")
        self.assertEqual(rc, 0)
        self.assertEqual(self.schreibend(), [])
        self.assertEqual(api.schreibzugriffe, [])
        self.assertIn("cx23 in fsn1", aus)  # günstigster verfügbarer x86-Typ, nbg1 nicht verfügbar
        self.assertIn("3,99 €", aus)
        self.assertIn("4,75 €", aus)        # brutto 3,99 * 1,19
        self.assertIn("5,29 €", aus)        # Summe netto: 3,99 * 1,2 + 0,50
        self.assertIn("TROCKENLAUF", aus)

    def test_anlegen_und_idempotenz(self):
        rc, aus, _ = self.lauf()
        self.assertEqual(rc, 0, aus)
        self.assertEqual(len(self.fake.firewalls), 1)
        self.assertEqual(len(self.fake.servers), 1)
        server = next(iter(self.fake.servers.values()))
        fw = next(iter(self.fake.firewalls.values()))
        self.assertEqual(server["name"], "hh-portal-1")
        self.assertEqual(server["labels"], {"app": "hh-portal"})
        self.assertEqual(server["server_type"]["name"], "cx23")
        self.assertEqual(server["backup_window"], "22-02")
        self.assertTrue(server["user_data"].startswith("#cloud-config"))
        self.assertEqual(server["public_net"]["firewalls"][0]["id"], fw["id"])
        self.assertEqual({(r["protocol"], r.get("port")) for r in fw["rules"]},
                         {("tcp", "80"), ("tcp", "443"), ("udp", "443"), ("icmp", None)})
        self.assertNotIn("22", [r.get("port") for r in fw["rules"]])
        self.assertIn("203.0.113.10", aus)
        self.assertNotIn("GEHEIM-root-pw", aus)
        self.assertNotIn("test-token", aus)

        vorher = len(self.schreibend())
        rc, aus2, _ = self.lauf()
        self.assertEqual(rc, 0, aus2)
        self.assertEqual(len(self.fake.firewalls), 1)
        self.assertEqual(len(self.fake.servers), 1)
        self.assertEqual(len(self.schreibend()), vorher, "zweiter Lauf darf nichts schreiben")
        self.assertIn("wiederverwendet", aus2)
        self.assertIn("Regeln stimmen", aus2)

    def test_abweichende_firewall_regeln_werden_korrigiert(self):
        self.lauf()
        fw = next(iter(self.fake.firewalls.values()))
        fw["rules"].append({"direction": "in", "protocol": "tcp", "port": "22", "source_ips": ["0.0.0.0/0"]})
        rc, aus, _ = self.lauf()
        self.assertEqual(rc, 0)
        self.assertIn(("POST", f"/firewalls/{fw['id']}/actions/set_rules"), self.fake.anfragen)
        self.assertNotIn("22", [r.get("port") for r in fw["rules"]])

    def test_401_verstaendliche_meldung_ohne_token(self):
        rc, aus, _ = self.lauf("--trockenlauf", token="falsch-geheim")
        self.assertEqual(rc, 1)
        self.assertIn("API-Token", aus)
        self.assertIn("Lesen & Schreiben", aus)
        self.assertNotIn("falsch-geheim", aus)

    def test_platzhalter_token_ohne_umgebungsvariable(self):
        import os
        alt = os.environ.pop("HCLOUD_TOKEN", None)
        try:
            api = se.Hetzner(self.url, warte=lambda s: None)
            self.fake.token_erwartet = "proxy-injiziert"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(se.main(["--trockenlauf"], api=api), 0)
            self.assertEqual(self.fake.auth_gesehen, {"Bearer proxy-injiziert"})
        finally:
            if alt is not None:
                os.environ["HCLOUD_TOKEN"] = alt

    def test_loeschen_nur_mit_bestaetigung(self):
        self.lauf()
        rc, aus, _ = self.lauf("--loeschen")
        self.assertEqual(rc, 2)
        self.assertIn("--ja-wirklich", aus)
        self.assertEqual(len(self.fake.servers), 1)
        rc, aus, _ = self.lauf("--loeschen", "--ja-wirklich")
        self.assertEqual(rc, 0, aus)
        self.assertEqual(self.fake.servers, {})
        self.assertEqual(self.fake.firewalls, {})
        rc, aus, _ = self.lauf("--loeschen", "--ja-wirklich")
        self.assertIn("Nichts zu löschen", aus)

    def test_user_data_unter_hetzner_grenze(self):
        self.assertLess(len(se.user_data_lesen().encode()), se.USER_DATA_MAX)


if __name__ == "__main__":
    unittest.main()
