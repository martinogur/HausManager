"""Tests für posten.py mit einem Fake-HTTP-Server (keine echten Aufrufe an Instagram oder GitHub).

Aufruf: python3 -m unittest discover -s marketing/instagram/tests -v
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import posten  # noqa: E402

TOKEN = "GEHEIM-TEST-TOKEN-123"


class FakeMeta:
    """Zustand des Fake-Servers: simuliert graph.instagram.com und raw.githubusercontent.com."""

    def __init__(self, repo):
        self.repo = repo
        self.anfragen = []          # (methode, pfad, params, auth)
        self.container = {}         # id -> params
        self.status_folge = {}      # id -> Liste von Statuswerten (wird abgearbeitet)
        self.standard_status = "FINISHED"
        self.zaehler = 100
        self.quota = (0, 50)
        self.fehler = {}            # pfad-endung -> (http, json)
        self.raw_fehlt = set()      # Repo-Pfade, die "noch nicht gepusht" sind
        self.veroeffentlicht = []

    def neue_id(self):
        self.zaehler += 1
        return str(self.zaehler)


def handler_fuer(meta):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _antwort(self, code, daten):
            body = json.dumps(daten).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _raw(self, mit_body):
            rel = urllib.parse.unquote(self.path[len("/raw/"):])
            datei = meta.repo / rel
            if rel in meta.raw_fehlt or not datei.exists():
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(datei.stat().st_size))
            self.end_headers()
            if mit_body:
                self.wfile.write(datei.read_bytes())

        def do_HEAD(self):
            if self.path.startswith("/raw/"):
                return self._raw(False)
            self.send_response(405)
            self.end_headers()

        def do_GET(self):
            if self.path.startswith("/raw/"):
                return self._raw(True)
            self._api("GET")

        def do_POST(self):
            self._api("POST")

        def _api(self, methode):
            teile = urllib.parse.urlsplit(self.path)
            pfad = teile.path[len("/api/"):]
            if methode == "POST":
                laenge = int(self.headers.get("Content-Length", 0))
                params = dict(urllib.parse.parse_qsl(self.rfile.read(laenge).decode()))
            else:
                params = dict(urllib.parse.parse_qsl(teile.query))
            meta.anfragen.append((methode, pfad, params, self.headers.get("Authorization")))
            for endung, (code, daten) in meta.fehler.items():
                if pfad.endswith(endung):
                    return self._antwort(code, daten)
            if pfad == "me":
                return self._antwort(200, {"user_id": "17841400000000001", "username": "hausmeister_helden_test"})
            uid, _, rest = pfad.partition("/")
            if rest == "content_publishing_limit":
                return self._antwort(200, {"data": [{"quota_usage": meta.quota[0], "config": {"quota_total": meta.quota[1]}}]})
            if methode == "POST" and rest == "media":
                cid = meta.neue_id()
                meta.container[cid] = params
                return self._antwort(200, {"id": cid})
            if methode == "POST" and rest == "media_publish":
                cid = params.get("creation_id")
                if cid not in meta.container:
                    return self._antwort(400, {"error": {"message": "Invalid creation_id", "code": 100}})
                mid = "9" + cid
                meta.veroeffentlicht.append((mid, cid))
                return self._antwort(200, {"id": mid})
            if methode == "GET" and pfad in meta.container:
                folge = meta.status_folge.get(pfad)
                status = folge.pop(0) if folge else meta.standard_status
                return self._antwort(200, {"status_code": status, "id": pfad})
            if methode == "GET" and pfad.startswith("9"):
                return self._antwort(200, {"permalink": f"https://www.instagram.com/p/TEST{pfad}/"})
            return self._antwort(404, {"error": {"message": f"unbekannt: {pfad}", "code": 100}})
    return H


def png(pfad, groesse=(1080, 1350)):
    from PIL import Image
    pfad.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", groesse, (13, 16, 14, 255)).save(pfad)


class PostenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.meta = FakeMeta(self.repo)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_fuer(self.meta))
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        basis = f"http://127.0.0.1:{self.server.server_port}"
        self.env_alt = dict(os.environ)
        os.environ.update(HH_REPO=str(self.repo), IG_API_BASE=basis + "/api", IG_RAW_BASE=basis + "/raw",
                          IG_STATUS_PAUSE="0", IG_STATUS_MAX="2", IG_TOKEN=TOKEN)
        g = "marketing/instagram/grafiken/test"
        for i in range(1, 4):
            png(self.repo / f"{g}/karussell/folie-0{i}.png")
        png(self.repo / f"{g}/story-1/folie-01.png", (1080, 1920))
        (self.repo / f"{g}/reel").mkdir(parents=True)
        (self.repo / f"{g}/reel/reel.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
        self.plan = self.repo / "marketing/instagram/plan.json"
        self.g = g

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        os.environ.clear()
        os.environ.update(self.env_alt)
        self.tmp.cleanup()

    # -------------------------------------------------------------- Hilfen
    def eintrag(self, id_, typ, dateien, status="freigegeben", zeit="2026-11-25T18:00:00+01:00", caption="Hallo Gütersloh"):
        return {"id": id_, "zeitpunkt": zeit, "typ": typ, "dateien": dateien, "caption": caption,
                "status": status, "media_id": None, "gepostet_am": None, "fehler": None}

    def schreibe(self, *eintraege):
        self.plan.write_text(json.dumps(list(eintraege), ensure_ascii=False), encoding="utf-8")

    def lauf(self, *args, jetzt="2026-11-25T18:05:00+01:00"):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = posten.main(list(args) + ["--jetzt", jetzt])
        return code, out.getvalue()

    def lese(self):
        return {e["id"]: e for e in json.loads(self.plan.read_text(encoding="utf-8"))}

    def posts(self, endung):
        return [a for a in self.meta.anfragen if a[0] == "POST" and a[1].endswith(endung)]

    # -------------------------------------------------------------- Tests
    def test_konto(self):
        code, out = self.lauf("--konto")
        self.assertEqual(code, 0)
        self.assertIn("@hausmeister_helden_test", out)
        self.assertIn("17841400000000001", out)
        self.assertIn("0 von 50", out)
        self.assertEqual(self.meta.anfragen[0][2], {"fields": "user_id,username"})
        self.assertEqual(self.meta.anfragen[0][3], f"Bearer {TOKEN}")
        self.assertNotIn(TOKEN, out)

    def test_platzhalter_ohne_token(self):
        del os.environ["IG_TOKEN"]
        self.lauf("--konto")
        self.assertEqual(self.meta.anfragen[0][3], "Bearer proxy-injiziert")

    def test_karussell_kompletter_ablauf(self):
        dateien = [f"{self.g}/karussell/folie-0{i}.png" for i in range(1, 4)]
        self.schreibe(self.eintrag("k1", "karussell", dateien, caption="Winterdienst in Gütersloh"))
        self.meta.status_folge["104"] = ["IN_PROGRESS", "IN_PROGRESS", "FINISHED"]  # Karussell-Container
        code, out = self.lauf("--faellige")
        self.assertEqual(code, 0, out)
        medien = self.posts("/media")
        self.assertEqual(len(medien), 4)
        for _, _, p, _ in medien[:3]:
            self.assertEqual(p["is_carousel_item"], "true")
            self.assertTrue(p["image_url"].endswith(".jpg"))
            self.assertNotIn("caption", p)
        eltern = medien[3][2]
        self.assertEqual(eltern["media_type"], "CAROUSEL")
        self.assertEqual(eltern["children"], "101,102,103")
        self.assertEqual(eltern["caption"], "Winterdienst in Gütersloh")
        self.assertEqual(self.posts("/media_publish")[0][2], {"creation_id": "104"})
        # Status vor dem Veröffentlichen abgefragt (3 Kinder + 3x Eltern)
        status_abfragen = [a for a in self.meta.anfragen if a[0] == "GET" and a[2].get("fields", "").startswith("status_code")]
        self.assertEqual(len(status_abfragen), 6)
        e = self.lese()["k1"]
        self.assertEqual(e["status"], "gepostet")
        self.assertEqual(e["media_id"], "9104")
        self.assertTrue(e["gepostet_am"])
        self.assertIsNone(e["fehler"])
        self.assertIn("instagram.com/p/", e["permalink"])
        jpgs = sorted((self.repo / "marketing/instagram/veroeffentlicht/k1").glob("*.jpg"))
        self.assertEqual([p.name for p in jpgs], ["01-folie-01.jpg", "02-folie-02.jpg", "03-folie-03.jpg"])
        self.assertEqual(jpgs[0].read_bytes()[:2], b"\xff\xd8")  # echtes JPEG
        self.assertNotIn(TOKEN, out + self.plan.read_text())

    def test_story_ohne_caption(self):
        self.schreibe(self.eintrag("s1", "story", [f"{self.g}/story-1/folie-01.png"], caption="ignoriert"))
        code, out = self.lauf("--faellige")
        self.assertEqual(code, 0, out)
        p = self.posts("/media")[0][2]
        self.assertEqual(p["media_type"], "STORIES")
        self.assertTrue(p["image_url"].endswith("veroeffentlicht/s1/story-1-folie-01.jpg"))
        self.assertNotIn("caption", p)
        self.assertEqual(self.lese()["s1"]["status"], "gepostet")

    def test_bild_und_reel(self):
        self.schreibe(self.eintrag("b1", "bild", [f"{self.g}/karussell/folie-01.png"]),
                      self.eintrag("r1", "reel", [f"{self.g}/reel/reel.mp4"], zeit="2026-11-25T18:01:00+01:00"))
        code, out = self.lauf("--faellige")
        self.assertEqual(code, 0, out)
        b, r = [a[2] for a in self.posts("/media")]
        self.assertNotIn("media_type", b)
        self.assertIn("image_url", b)
        self.assertEqual(r["media_type"], "REELS")
        self.assertTrue(r["video_url"].endswith("reel/reel.mp4"))
        self.assertEqual({e["status"] for e in self.lese().values()}, {"gepostet"})

    def test_nur_freigegeben_und_faellig(self):
        s = f"{self.g}/story-1/folie-01.png"
        self.schreibe(self.eintrag("geplant", "story", [s], status="geplant"),
                      self.eintrag("zukunft", "story", [s], zeit="2026-11-25T20:00:00+01:00"),
                      self.eintrag("schon", "story", [s], status="gepostet"))
        code, out = self.lauf("--faellige")
        self.assertEqual(code, 0)
        self.assertIn("Nichts fällig", out)
        self.assertEqual(self.meta.anfragen, [])
        self.assertEqual(self.lese()["geplant"]["status"], "geplant")

    def test_zeit_ohne_zone_ist_berlin(self):
        self.schreibe(self.eintrag("s", "story", [f"{self.g}/story-1/folie-01.png"], zeit="2026-11-25T18:06:00"))
        self.lauf("--faellige", jetzt="2026-11-25T17:05:00+00:00")  # = 18:05 Berlin -> noch nicht fällig
        self.assertEqual(self.posts("/media"), [])
        self.lauf("--faellige", jetzt="2026-11-25T17:07:00+00:00")
        self.assertEqual(self.lese()["s"]["status"], "gepostet")

    def test_url_nicht_gepusht(self):
        self.schreibe(self.eintrag("s1", "story", [f"{self.g}/story-1/folie-01.png"]))
        self.meta.raw_fehlt.add("marketing/instagram/veroeffentlicht/s1/story-1-folie-01.jpg")
        code, out = self.lauf("--faellige")
        self.assertEqual(code, 1)
        self.assertIn("erst committen + pushen", out)
        self.assertEqual(self.posts("/media"), [])
        e = self.lese()["s1"]
        self.assertEqual(e["status"], "freigegeben")  # wird beim nächsten Lauf erneut versucht
        self.assertIn("committen", e["fehler"])
        self.meta.raw_fehlt.clear()
        code, _ = self.lauf("--faellige", jetzt="2026-11-25T18:20:00+01:00")
        self.assertEqual(code, 0)
        self.assertEqual(self.lese()["s1"]["status"], "gepostet")

    def test_container_error(self):
        self.schreibe(self.eintrag("s1", "story", [f"{self.g}/story-1/folie-01.png"]),
                      self.eintrag("s2", "story", [f"{self.g}/story-1/folie-01.png"], zeit="2026-11-25T18:02:00+01:00"))
        self.meta.status_folge["101"] = ["ERROR"]
        code, out = self.lauf("--faellige")
        self.assertEqual(code, 1)
        p = self.lese()
        self.assertEqual(p["s1"]["status"], "fehler")
        self.assertIn("nicht verarbeiten", p["s1"]["fehler"])
        self.assertEqual(p["s2"]["status"], "gepostet")  # nächster Eintrag läuft weiter
        self.assertEqual(self.posts("/media_publish")[0][2]["creation_id"], "102")

    def test_container_haengt(self):
        self.schreibe(self.eintrag("s1", "story", [f"{self.g}/story-1/folie-01.png"]))
        self.meta.standard_status = "IN_PROGRESS"
        os.environ["IG_STATUS_MAX"] = "0"
        code, _ = self.lauf("--faellige")
        self.assertEqual(code, 1)
        self.assertIn("noch nicht fertig", self.lese()["s1"]["fehler"])
        self.assertEqual(self.posts("/media_publish"), [])

    def test_token_abgelaufen(self):
        self.schreibe(self.eintrag("s1", "story", [f"{self.g}/story-1/folie-01.png"]))
        self.meta.fehler["me"] = (400, {"error": {"message": f"Error validating access token {TOKEN}",
                                                  "type": "OAuthException", "code": 190}})
        code, out = self.lauf("--faellige")
        self.assertEqual(code, 1)
        self.assertIn("Zugriffstoken ungültig oder abgelaufen", out)
        self.assertNotIn(TOKEN, out)
        e = self.lese()["s1"]
        self.assertEqual(e["status"], "freigegeben")
        self.assertNotIn(TOKEN, json.dumps(e))

    def test_rate_limit_bricht_lauf_ab(self):
        s = f"{self.g}/story-1/folie-01.png"
        self.schreibe(self.eintrag("s1", "story", [s]), self.eintrag("s2", "story", [s], zeit="2026-11-25T18:02:00+01:00"))
        self.meta.fehler["/media"] = (400, {"error": {"message": "Application request limit reached", "code": 4}})
        code, out = self.lauf("--faellige")
        self.assertEqual(code, 1)
        self.assertIn("Rate-Limit", out)
        p = self.lese()
        self.assertEqual(p["s1"]["status"], "freigegeben")
        self.assertEqual(p["s2"]["status"], "freigegeben")
        self.assertEqual(len(self.posts("/media")), 1)  # s2 nicht mehr versucht

    def test_tageslimit_voll(self):
        self.schreibe(self.eintrag("s1", "story", [f"{self.g}/story-1/folie-01.png"]))
        self.meta.quota = (50, 50)
        code, out = self.lauf("--faellige")
        self.assertEqual(code, 1)
        self.assertIn("Tageslimit", out)
        self.assertEqual(self.posts("/media"), [])
        self.assertEqual(self.lese()["s1"]["status"], "freigegeben")

    def test_publish_wird_nicht_wiederholt(self):
        self.schreibe(self.eintrag("s1", "story", [f"{self.g}/story-1/folie-01.png"]))
        self.meta.fehler["media_publish"] = (500, {"error": {"message": "Service temporarily unavailable", "code": 2}})
        code, _ = self.lauf("--faellige")
        self.assertEqual(code, 1)
        self.assertEqual(len(self.posts("/media_publish")), 1)
        self.assertEqual(self.lese()["s1"]["status"], "fehler")

    def test_verpasst(self):
        self.schreibe(self.eintrag("s1", "story", [f"{self.g}/story-1/folie-01.png"]))
        code, out = self.lauf("--faellige", jetzt="2026-11-25T23:00:00+01:00")
        self.assertEqual(code, 1)
        self.assertIn("VERPASST", out)
        self.assertEqual(self.posts("/media"), [])
        self.assertEqual(self.lese()["s1"]["status"], "fehler")

    def test_ungueltiger_eintrag(self):
        self.schreibe(self.eintrag("k", "karussell", [f"{self.g}/karussell/folie-01.png"]))
        code, out = self.lauf("--faellige")
        self.assertEqual(self.lese()["k"]["status"], "fehler")
        self.assertIn("2 bis 20", self.lese()["k"]["fehler"])

    def test_trockenlauf_sendet_nichts(self):
        dateien = [f"{self.g}/karussell/folie-0{i}.png" for i in range(1, 3)]
        self.schreibe(self.eintrag("k1", "karussell", dateien),
                      self.eintrag("s1", "story", [f"{self.g}/story-1/folie-01.png"], status="geplant"))
        vorher = self.plan.read_text()
        code, out = self.lauf("--trockenlauf", "--alle")
        self.assertEqual(code, 0)
        self.assertIn("k1 · karussell", out)
        self.assertIn("WÜRDE JETZT GEPOSTET", out)
        self.assertIn("status=geplant", out)
        self.assertIn("lokal FEHLT", out)
        self.assertEqual(self.meta.anfragen, [])  # keine API-Aufrufe
        self.assertEqual(self.plan.read_text(), vorher)
        self.assertFalse((self.repo / "marketing/instagram/veroeffentlicht").exists())

    def test_vorbereiten(self):
        self.schreibe(self.eintrag("s1", "story", [f"{self.g}/story-1/folie-01.png"], status="geplant"))
        code, out = self.lauf("--vorbereiten")
        self.assertEqual(code, 0)
        self.assertTrue((self.repo / "marketing/instagram/veroeffentlicht/s1/story-1-folie-01.jpg").exists())
        self.assertEqual(self.meta.anfragen, [])


if __name__ == "__main__":
    unittest.main()
