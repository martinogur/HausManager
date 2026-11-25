#!/usr/bin/env python3
"""Instagram-Beiträge und Storys automatisch veröffentlichen (Instagram API with Instagram Login).

Nur Standardbibliothek (+ Pillow für PNG -> JPEG, aus /tmp/hh-venv oder systemweit).

Posting-Plan: marketing/instagram/plan.json – eine JSON-Liste von Einträgen:
  {
    "id": "2026-11-25-feed-winterdienst-preis",        # eindeutig, wird Ordnername unter veroeffentlicht/
    "zeitpunkt": "2026-11-25T18:30:00+01:00",           # ISO; ohne Zeitzone = Europe/Berlin
    "typ": "bild" | "karussell" | "story" | "reel",
    "dateien": ["marketing/instagram/grafiken/…/folie-01.png", …],   # Repo-Pfade (PNG/JPEG; Reel/Story-Video: MP4)
    "caption": "…",                                      # bei Storys ignoriert (API kennt keine Story-Caption)
    "status": "geplant" | "freigegeben" | "gepostet" | "fehler",
    "media_id": null, "gepostet_am": null, "fehler": null  # schreibt das Skript
  }
Gepostet wird NUR status=freigegeben. "geplant" -> "freigegeben" setzt Claude erst nach der Freigabe des Inhabers.

Ablauf je Eintrag (Meta Content Publishing, 2 Schritte):
  1. POST /{ig-user-id}/media           -> Container (Karussell: erst je Bild ein Container mit is_carousel_item=true,
                                           dann Container media_type=CAROUSEL mit children=id1,id2,…)
  2. GET  /{container-id}?fields=status_code  bis FINISHED
  3. POST /{ig-user-id}/media_publish   (creation_id=<container-id>) -> media_id
Bilder müssen öffentlich erreichbar sein: PNG wird in JPEG umgewandelt und unter
marketing/instagram/veroeffentlicht/<id>/ abgelegt; öffentliche Adresse =
https://raw.githubusercontent.com/martinogur/HausManager/<branch>/<pfad>  -> vorher committen + pushen!

Aufrufe:
  python3 marketing/instagram/posten.py --konto                 # verbundenes Konto + Tageslimit anzeigen
  python3 marketing/instagram/posten.py --vorbereiten           # JPEGs für alle geplanten/freigegebenen Einträge erzeugen
  python3 marketing/instagram/posten.py --trockenlauf [--alle]  # zeigt, was jetzt gepostet würde (sendet nichts an Instagram)
  python3 marketing/instagram/posten.py --faellige              # postet alle freigegebenen, fälligen Einträge
Optionen: --plan <pfad>, --jetzt <ISO-Zeit> (zum Testen), --max-verspaetung <Minuten> (Standard 120).

Umgebung (optional):
  IG_TOKEN        Zugriffstoken. Fehlt er, wird der Platzhalter "proxy-injiziert" gesendet (der Sitzungs-Proxy ersetzt ihn).
  IG_API_BASE     Standard https://graph.instagram.com/v27.0
  IG_RAW_BASE     Standard https://raw.githubusercontent.com/martinogur/HausManager/claude/ecstatic-euler-92wew4
  IG_STATUS_PAUSE Sekunden zwischen Status-Abfragen (Standard 15), IG_STATUS_MAX Sekunden bis Abbruch (Standard 300)
  HH_REPO         Repo-Wurzel (Standard: zwei Ebenen über dieser Datei)
Tokens werden nie ausgegeben oder in plan.json geschrieben.
"""
import argparse
import datetime as dt
import fcntl
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
STANDARD_API = "https://graph.instagram.com/v27.0"
STANDARD_RAW = "https://raw.githubusercontent.com/martinogur/HausManager/claude/ecstatic-euler-92wew4"
PLATZHALTER = "proxy-injiziert"
TYPEN = ("bild", "karussell", "story", "reel")
STATUS = ("geplant", "freigegeben", "gepostet", "fehler")
RATE_CODES = {4, 17, 32, 613}  # Meta: Anfrage-/Nutzungslimits erreicht
VIDEO_ENDUNGEN = (".mp4", ".mov")


class PostenFehler(Exception):
    """Verständlicher Fehler zu einem Eintrag."""


class LimitFehler(PostenFehler):
    """Rate-Limit / Tageslimit erreicht – weitere Einträge in diesem Lauf nicht versuchen."""


class NichtOeffentlich(PostenFehler):
    """Datei noch nicht unter der öffentlichen Adresse – erst committen + pushen (später erneut versuchen)."""


# ---------------------------------------------------------------- Konfiguration

class Konfig:
    def __init__(self, plan=None):
        self.repo = Path(os.environ.get("HH_REPO") or Path(__file__).resolve().parents[2])
        self.plan = Path(plan) if plan else self.repo / "marketing" / "instagram" / "plan.json"
        self.api = (os.environ.get("IG_API_BASE") or STANDARD_API).rstrip("/")
        self.raw = (os.environ.get("IG_RAW_BASE") or STANDARD_RAW).rstrip("/")
        self.token = os.environ.get("IG_TOKEN") or PLATZHALTER
        self.pause = float(os.environ.get("IG_STATUS_PAUSE", "15"))
        self.status_max = float(os.environ.get("IG_STATUS_MAX", "300"))


def schwaerzen(text, k):
    """Token aus Texten entfernen, bevor sie ausgegeben/gespeichert werden."""
    text = str(text)
    if k.token and k.token != PLATZHALTER:
        text = text.replace(k.token, "***")
    return text


# ---------------------------------------------------------------- Plan lesen/schreiben

def plan_laden(k):
    if not k.plan.exists():
        raise SystemExit(f"Plan fehlt: {k.plan}")
    daten = json.loads(k.plan.read_text(encoding="utf-8"))
    if not isinstance(daten, list):
        raise SystemExit("plan.json muss eine JSON-Liste von Einträgen sein.")
    return daten


def plan_speichern(k, eintraege):
    tmp = k.plan.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(eintraege, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, k.plan)


def zeit_lesen(text):
    t = dt.datetime.fromisoformat(text)
    if t.tzinfo is None:
        t = t.replace(tzinfo=BERLIN)
    return t


def jetzt_berlin():
    return dt.datetime.now(BERLIN)


def eintrag_pruefen(e):
    fehlt = [f for f in ("id", "zeitpunkt", "typ", "dateien", "status") if not e.get(f)]
    if fehlt:
        raise PostenFehler(f"Eintrag unvollständig, es fehlt: {', '.join(fehlt)}")
    if e["typ"] not in TYPEN:
        raise PostenFehler(f"Unbekannter typ '{e['typ']}' (erlaubt: {', '.join(TYPEN)})")
    if e["status"] not in STATUS:
        raise PostenFehler(f"Unbekannter status '{e['status']}' (erlaubt: {', '.join(STATUS)})")
    n = len(e["dateien"])
    if e["typ"] == "karussell" and not 2 <= n <= 20:
        raise PostenFehler(f"Karussell braucht 2 bis 20 Dateien, hat {n}")
    if e["typ"] in ("bild", "story", "reel") and n != 1:
        raise PostenFehler(f"Typ {e['typ']} braucht genau 1 Datei, hat {n}")
    if e["typ"] == "reel" and not e["dateien"][0].lower().endswith(VIDEO_ENDUNGEN):
        raise PostenFehler("Reel braucht eine Videodatei (.mp4)")
    if "/" in e["id"] or e["id"].startswith("."):
        raise PostenFehler("id darf keinen Schrägstrich enthalten")
    zeit_lesen(e["zeitpunkt"])


# ---------------------------------------------------------------- Dateien / öffentliche Adressen

def ist_video(pfad):
    return pfad.lower().endswith(VIDEO_ENDUNGEN)


def jpeg_pfad(e, i, quelle):
    stem = Path(quelle).stem
    if e["typ"] == "story" or len(e["dateien"]) == 1:
        name = f"{Path(quelle).parent.name}-{stem}.jpg" if stem.startswith("folie") else f"{stem}.jpg"
    else:
        name = f"{i:02d}-{stem}.jpg"
    return f"marketing/instagram/veroeffentlicht/{e['id']}/{name}"


def pillow():
    try:
        from PIL import Image  # noqa: WPS433
        return Image
    except ImportError:
        for sp in glob.glob("/tmp/hh-venv/lib/python3*/site-packages"):
            sys.path.insert(0, sp)
        try:
            from PIL import Image  # noqa: WPS433
            return Image
        except ImportError:
            raise PostenFehler("Pillow fehlt (weder /tmp/hh-venv noch systemweit) – PNG kann nicht in JPEG umgewandelt werden")


def veroeffentlichungs_dateien(k, e, schreiben=True):
    """Liefert die Repo-Pfade, die öffentlich erreichbar sein müssen (JPEG bzw. Video). Erzeugt JPEGs bei Bedarf."""
    ergebnis = []
    for i, quelle in enumerate(e["dateien"], 1):
        q = k.repo / quelle
        if ist_video(quelle):
            if not q.exists():
                raise PostenFehler(f"Datei fehlt: {quelle}")
            ergebnis.append(quelle)
            continue
        ziel_rel = jpeg_pfad(e, i, quelle)
        ziel = k.repo / ziel_rel
        if schreiben:
            if not q.exists():
                raise PostenFehler(f"Datei fehlt: {quelle}")
            if not ziel.exists() or ziel.stat().st_mtime < q.stat().st_mtime:
                Image = pillow()
                ziel.parent.mkdir(parents=True, exist_ok=True)
                with Image.open(q) as bild:
                    bild.convert("RGB").save(ziel, "JPEG", quality=92, optimize=True)
        ergebnis.append(ziel_rel)
    return ergebnis


def oeffentliche_url(k, rel):
    return k.raw + "/" + urllib.parse.quote(rel)


def url_erreichbar(url):
    """True, wenn die Adresse mit HTTP 200 antwortet (HEAD, notfalls GET mit Range)."""
    for methode in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=methode, headers={"User-Agent": "hh-instagram-poster"})
        if methode == "GET":
            req.add_header("Range", "bytes=0-0")
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status in (200, 206):
                    return True
        except urllib.error.HTTPError as fehler:
            if fehler.code == 404:
                return False
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
    return False


# ---------------------------------------------------------------- Instagram-Schnittstelle

class Api:
    def __init__(self, k):
        self.k = k

    def _anfrage(self, methode, pfad, params=None, wiederholen=True):
        url = f"{self.k.api}/{pfad.lstrip('/')}"
        daten = None
        if methode == "GET" and params:
            url += "?" + urllib.parse.urlencode(params)
        elif params:
            daten = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(url, data=daten, method=methode)
        req.add_header("Authorization", f"Bearer {self.k.token}")
        req.add_header("User-Agent", "hh-instagram-poster")
        if daten is not None:
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
        for versuch in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.loads(r.read().decode() or "{}")
            except urllib.error.HTTPError as fehler:
                koerper = fehler.read().decode(errors="replace")
                if fehler.code >= 500 and versuch < 2 and wiederholen:
                    time.sleep(min(2 ** versuch, 5) if self.k.pause else 0)
                    continue
                raise self._fehler(fehler.code, koerper)
            except (urllib.error.URLError, TimeoutError) as fehler:
                if versuch < 2 and wiederholen:
                    time.sleep(min(2 ** versuch, 5) if self.k.pause else 0)
                    continue
                hinweis = "" if wiederholen else " – bitte im Profil prüfen, ob der Beitrag trotzdem erschienen ist"
                raise PostenFehler(f"Instagram nicht erreichbar ({schwaerzen(getattr(fehler, 'reason', fehler), self.k)}){hinweis}")
        raise PostenFehler("Instagram nicht erreichbar")

    def _fehler(self, http, koerper):
        try:
            err = json.loads(koerper).get("error", {})
        except ValueError:
            err = {}
        code = err.get("code")
        sub = err.get("error_subcode")
        msg = schwaerzen(err.get("error_user_msg") or err.get("message") or koerper[:300], self.k)
        info = f"(HTTP {http}, Code {code}{'/' + str(sub) if sub else ''}): {msg}"
        if http == 429 or code in RATE_CODES:
            return LimitFehler(f"Rate-Limit von Instagram erreicht – später erneut versuchen {info}")
        if code == 190 or http == 401:
            return PostenFehler(f"Zugriffstoken ungültig oder abgelaufen – Inhaber muss neuen Token erzeugen {info}")
        if code in (10, 200) or http == 403:
            return PostenFehler(f"Fehlende Berechtigung (instagram_business_content_publish?) {info}")
        return PostenFehler(f"Instagram-Fehler {info}")

    def konto(self):
        return self._anfrage("GET", "me", {"fields": "user_id,username"})

    def limit(self, uid):
        antwort = self._anfrage("GET", f"{uid}/content_publishing_limit", {"fields": "quota_usage,config"})
        daten = (antwort.get("data") or [{}])[0]
        gesamt = (daten.get("config") or {}).get("quota_total")
        return daten.get("quota_usage"), gesamt

    def container(self, uid, params):
        antwort = self._anfrage("POST", f"{uid}/media", params)
        if not antwort.get("id"):
            raise PostenFehler(f"Instagram hat keinen Container angelegt: {schwaerzen(antwort, self.k)}")
        return antwort["id"]

    def warten(self, cid):
        start = time.monotonic()
        while True:
            antwort = self._anfrage("GET", cid, {"fields": "status_code,status"})
            code = antwort.get("status_code")
            if code in ("FINISHED", "PUBLISHED"):
                return
            if code in ("ERROR", "EXPIRED"):
                detail = antwort.get("status") or ""
                raise PostenFehler(f"Instagram konnte die Datei nicht verarbeiten (Container {cid}: {code} {detail}).".strip()
                                   + " Häufige Ursachen: kein JPEG, falsches Seitenverhältnis, Datei nicht öffentlich.")
            if time.monotonic() - start >= self.k.status_max:
                raise PostenFehler(f"Container {cid} nach {int(self.k.status_max)} s noch nicht fertig (Status {code})")
            time.sleep(self.k.pause)

    def veroeffentlichen(self, uid, cid):
        # nicht automatisch wiederholen: sonst droht doppeltes Posten
        antwort = self._anfrage("POST", f"{uid}/media_publish", {"creation_id": cid}, wiederholen=False)
        if not antwort.get("id"):
            raise PostenFehler(f"Veröffentlichen fehlgeschlagen: {schwaerzen(antwort, self.k)}")
        return antwort["id"]

    def permalink(self, mid):
        try:
            return self._anfrage("GET", mid, {"fields": "permalink"}).get("permalink")
        except PostenFehler:
            return None


def eintrag_posten(api, uid, e, urls):
    typ, caption = e["typ"], (e.get("caption") or "").strip()
    if typ == "karussell":
        kinder = []
        for url in urls:
            p = {"is_carousel_item": "true"}
            p.update({"media_type": "VIDEO", "video_url": url} if ist_video(url) else {"image_url": url})
            kinder.append(api.container(uid, p))
        for cid in kinder:
            api.warten(cid)
        p = {"media_type": "CAROUSEL", "children": ",".join(kinder)}
        if caption:
            p["caption"] = caption
        cid = api.container(uid, p)
    elif typ == "story":
        p = {"media_type": "STORIES"}
        p.update({"video_url": urls[0]} if ist_video(urls[0]) else {"image_url": urls[0]})
        cid = api.container(uid, p)
    elif typ == "reel":
        p = {"media_type": "REELS", "video_url": urls[0]}
        if caption:
            p["caption"] = caption
        cid = api.container(uid, p)
    else:  # bild
        p = {"image_url": urls[0]}
        if caption:
            p["caption"] = caption
        cid = api.container(uid, p)
    api.warten(cid)
    return api.veroeffentlichen(uid, cid)


# ---------------------------------------------------------------- Modi

def faellig(e, jetzt):
    return e.get("status") == "freigegeben" and zeit_lesen(e["zeitpunkt"]) <= jetzt


def modus_konto(k):
    api = Api(k)
    me = api.konto()
    uid = me.get("user_id") or me.get("id")
    print(f"Verbundenes Konto: @{me.get('username')} (ig-user-id {uid})")
    try:
        genutzt, gesamt = api.limit(uid)
        print(f"Veröffentlichungen letzte 24 h: {genutzt} von {gesamt if gesamt is not None else '?'}")
    except PostenFehler as fehler:
        print(f"Tageslimit nicht abrufbar: {fehler}")
    return 0


def modus_vorbereiten(k):
    eintraege = plan_laden(k)
    fehler = 0
    for e in eintraege:
        if e.get("status") not in ("geplant", "freigegeben"):
            continue
        try:
            eintrag_pruefen(e)
            for rel in veroeffentlichungs_dateien(k, e):
                print(f"{e['id']}: {rel}")
        except PostenFehler as f:
            fehler += 1
            print(f"{e.get('id')}: FEHLER {f}")
    print("Jetzt committen und pushen, damit die Dateien öffentlich erreichbar sind.")
    return 1 if fehler else 0


def modus_trockenlauf(k, jetzt, alle, max_versp):
    eintraege = plan_laden(k)
    print(f"Trockenlauf {jetzt:%d.%m.%Y %H:%M} – es wird nichts an Instagram gesendet.")
    n = 0
    for e in eintraege:
        try:
            eintrag_pruefen(e)
        except PostenFehler as f:
            print(f"- {e.get('id')}: UNGÜLTIG {f}")
            continue
        ist_faellig = faellig(e, jetzt)
        if not (alle or ist_faellig):
            continue
        n += 1
        t = zeit_lesen(e["zeitpunkt"])
        if ist_faellig and jetzt - t > dt.timedelta(minutes=max_versp):
            hinweis = f"WÜRDE NICHT GEPOSTET (mehr als {max_versp} Min. verspätet)"
        elif ist_faellig:
            hinweis = "WÜRDE JETZT GEPOSTET"
        else:
            hinweis = f"status={e['status']}" + (" (noch nicht fällig)" if e["status"] == "freigegeben" else "")
        print(f"- {e['id']} · {e['typ']} · {t:%d.%m. %H:%M} · {hinweis}")
        for rel in veroeffentlichungs_dateien(k, e, schreiben=False):
            vorhanden = "lokal da" if (k.repo / rel).exists() else "lokal FEHLT (--vorbereiten)"
            url = oeffentliche_url(k, rel)
            online = "online" if url_erreichbar(url) else "NICHT online (committen+pushen)"
            print(f"    {url}  [{vorhanden}, {online}]")
        if e["typ"] != "story" and e.get("caption"):
            erste = e["caption"].strip().splitlines()[0]
            print(f"    Caption: {erste[:80]}{'…' if len(erste) > 80 else ''} ({len(e['caption'])} Zeichen)")
    if not n:
        print("Nichts fällig." if not alle else "Plan ist leer.")
    return 0


def modus_faellige(k, jetzt, max_versp):
    sperre = open(k.plan.with_suffix(".lock"), "w")
    try:
        fcntl.flock(sperre, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Ein anderer Lauf postet gerade – abgebrochen.")
        return 1
    try:
        return _faellige(k, jetzt, max_versp)
    finally:
        fcntl.flock(sperre, fcntl.LOCK_UN)
        sperre.close()


def _faellige(k, jetzt, max_versp):
    eintraege = plan_laden(k)
    offen = []
    for e in eintraege:
        try:
            eintrag_pruefen(e)
        except PostenFehler as f:
            if e.get("status") == "freigegeben":
                e.update(status="fehler", fehler=str(f))
                print(f"{e.get('id')}: FEHLER {f}")
            continue
        if faellig(e, jetzt):
            offen.append(e)
    offen.sort(key=lambda e: zeit_lesen(e["zeitpunkt"]))
    if not offen:
        plan_speichern(k, eintraege)
        print("Nichts fällig.")
        return 0

    api = Api(k)
    ergebnis = 0
    try:
        me = api.konto()
        uid = me.get("user_id") or me.get("id")
        if not uid:
            raise PostenFehler("Konto-ID nicht ermittelbar (Antwort von /me ohne user_id)")
        print(f"Konto: @{me.get('username')}")
        genutzt, gesamt = api.limit(uid)
        frei = None if gesamt is None or genutzt is None else gesamt - genutzt
    except PostenFehler as f:
        for e in offen:
            e["fehler"] = str(f)
        plan_speichern(k, eintraege)
        print(f"ABBRUCH: {f}")
        return 1

    for e in offen:
        t = zeit_lesen(e["zeitpunkt"])
        if jetzt - t > dt.timedelta(minutes=max_versp):
            e.update(status="fehler", fehler=f"Zeitpunkt um mehr als {max_versp} Min. verpasst – nicht automatisch nachgeholt")
            print(f"{e['id']}: VERPASST – nicht gepostet")
            ergebnis = 1
            plan_speichern(k, eintraege)
            continue
        if frei is not None and frei <= 0:
            e["fehler"] = f"Tageslimit erreicht ({genutzt}/{gesamt}) – wird beim nächsten Lauf versucht"
            print(f"{e['id']}: Tageslimit erreicht, übersprungen")
            ergebnis = 1
            continue
        try:
            rels = veroeffentlichungs_dateien(k, e)
            urls = [oeffentliche_url(k, r) for r in rels]
            fehlend = [u for u in urls if not url_erreichbar(u)]
            if fehlend:
                raise NichtOeffentlich("Datei(en) noch nicht öffentlich erreichbar – erst committen + pushen: "
                                       + ", ".join(fehlend))
            mid = eintrag_posten(api, uid, e, urls)
            e.update(status="gepostet", media_id=mid, gepostet_am=jetzt_berlin().isoformat(timespec="seconds"),
                     fehler=None)
            link = api.permalink(mid)
            if link:
                e["permalink"] = link
            if frei is not None:
                frei -= 1
            print(f"{e['id']}: GEPOSTET (media_id {mid}){' ' + link if link else ''}")
        except LimitFehler as f:
            e["fehler"] = str(f)  # Status bleibt freigegeben -> nächster Lauf
            print(f"{e['id']}: {f}")
            plan_speichern(k, eintraege)
            print("Weitere Einträge in diesem Lauf ausgelassen (Rate-Limit).")
            return 1
        except NichtOeffentlich as f:
            e["fehler"] = str(f)  # Status bleibt freigegeben -> nach dem Push erneut
            print(f"{e['id']}: {f}")
            ergebnis = 1
        except PostenFehler as f:
            e.update(status="fehler", fehler=str(f))
            print(f"{e['id']}: FEHLER {f}")
            ergebnis = 1
        plan_speichern(k, eintraege)
    plan_speichern(k, eintraege)
    return ergebnis


def main(argv=None):
    ap = argparse.ArgumentParser(description="Instagram-Plan automatisch veröffentlichen")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--faellige", action="store_true", help="freigegebene, fällige Einträge posten")
    g.add_argument("--trockenlauf", action="store_true", help="nur anzeigen, nichts senden")
    g.add_argument("--konto", action="store_true", help="verbundenes Konto anzeigen")
    g.add_argument("--vorbereiten", action="store_true", help="JPEGs unter veroeffentlicht/ erzeugen")
    ap.add_argument("--alle", action="store_true", help="beim Trockenlauf auch nicht fällige Einträge zeigen")
    ap.add_argument("--plan", help="Pfad zu plan.json")
    ap.add_argument("--jetzt", help="aktuelle Zeit überschreiben (ISO, zum Testen)")
    ap.add_argument("--max-verspaetung", type=int, default=120, help="Minuten; ältere Einträge werden nicht nachgeholt")
    a = ap.parse_args(argv)
    k = Konfig(a.plan)
    jetzt = zeit_lesen(a.jetzt) if a.jetzt else jetzt_berlin()
    try:
        if a.konto:
            return modus_konto(k)
        if a.vorbereiten:
            return modus_vorbereiten(k)
        if a.trockenlauf:
            return modus_trockenlauf(k, jetzt, a.alle, a.max_verspaetung)
        return modus_faellige(k, jetzt, a.max_verspaetung)
    except PostenFehler as f:
        print(f"FEHLER: {f}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
