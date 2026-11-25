#!/usr/bin/env python3
"""
Legt den Portal-Server bei Hetzner Cloud an (API v1) – nur Python-Standardbibliothek.

Idempotent: vorhandene Objekte mit gleichem Namen werden wiederverwendet, nichts doppelt angelegt.
  * Firewall  "hh-portal"    eingehend nur TCP 80/443, UDP 443 (HTTP/3) und ICMP – kein SSH
  * Server    "hh-portal-1"  günstigster verfügbarer x86-Typ mit >= 2 vCPU und >= 4 GB RAM
                             in nbg1 oder fsn1, Image ubuntu-24.04, user_data = cloud-init.yaml,
                             Label app=hh-portal, ohne SSH-Key (Root-Passwort per Hetzner-Konsole)
  * Hetzner-Backups für den Server einschalten

Aufrufe:
  python3 server_erstellen.py --trockenlauf          # nur lesen: Plan + Monatspreis, ändert nichts
  python3 server_erstellen.py                        # anlegen bzw. vorhandene Objekte prüfen
  python3 server_erstellen.py --loeschen             # zeigt nur, was gelöscht würde
  python3 server_erstellen.py --loeschen --ja-wirklich

Token: Umgebungsvariable HCLOUD_TOKEN (Projekt-Token mit Lesen+Schreiben). Ist sie nicht
gesetzt, wird der Platzhalter "proxy-injiziert" gesendet (ein Sitzungs-Proxy ersetzt ihn).
Der Token wird nie ausgegeben. HCLOUD_API_URL ändert die API-Adresse (nur für Tests).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_URL = os.environ.get("HCLOUD_API_URL", "https://api.hetzner.cloud/v1").rstrip("/")
PLATZHALTER_TOKEN = "proxy-injiziert"

FIREWALL_NAME = "hh-portal"
SERVER_NAME = "hh-portal-1"
LABELS = {"app": "hh-portal"}
IMAGE = "ubuntu-24.04"
STANDORTE = ("nbg1", "fsn1")
MIN_KERNE = 2
MIN_RAM_GB = 4.0
USER_DATA_MAX = 32 * 1024  # Grenze der Hetzner-API für user_data
CLOUD_INIT = Path(__file__).with_name("cloud-init.yaml")

ALLE = ["0.0.0.0/0", "::/0"]
FIREWALL_REGELN = [
    {"direction": "in", "protocol": "tcp", "port": "80", "source_ips": ALLE, "description": "HTTP (Let's Encrypt, Umleitung)"},
    {"direction": "in", "protocol": "tcp", "port": "443", "source_ips": ALLE, "description": "HTTPS"},
    {"direction": "in", "protocol": "udp", "port": "443", "source_ips": ALLE, "description": "HTTP/3"},
    {"direction": "in", "protocol": "icmp", "source_ips": ALLE, "description": "Ping"},
]


class ApiFehler(Exception):
    def __init__(self, status: int, code: str, nachricht: str):
        super().__init__(f"HTTP {status} {code}: {nachricht}")
        self.status, self.code, self.nachricht = status, code, nachricht


class Hetzner:
    def __init__(self, basis: str = API_URL, token: str | None = None, warte=time.sleep):
        self.basis = basis.rstrip("/")
        self._token = token or os.environ.get("HCLOUD_TOKEN") or PLATZHALTER_TOKEN
        self.warte = warte
        self.schreibzugriffe: list[str] = []  # für Tests und den Trockenlauf-Nachweis

    def anfrage(self, methode: str, pfad: str, daten: dict | None = None, versuche: int = 5) -> dict:
        url = self.basis + pfad
        koerper = None if daten is None else json.dumps(daten).encode()
        for versuch in range(1, versuche + 1):
            req = urllib.request.Request(url, data=koerper, method=methode)
            req.add_header("Authorization", f"Bearer {self._token}")
            req.add_header("Accept", "application/json")
            req.add_header("User-Agent", "hh-portal-server-erstellen/1")
            if koerper is not None:
                req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=60) as antwort:
                    inhalt = antwort.read()
                if methode != "GET":
                    self.schreibzugriffe.append(f"{methode} {pfad}")
                return json.loads(inhalt) if inhalt else {}
            except urllib.error.HTTPError as fehler:
                try:
                    info = json.loads(fehler.read() or b"{}").get("error", {})
                except ValueError:
                    info = {}
                code = info.get("code", "")
                # Wiederholen bei Rate-Limit, gesperrter Ressource oder kurzfristigen Serverfehlern
                if versuch < versuche and (fehler.code in (429, 502, 503, 504) or code in ("locked", "conflict")):
                    self.warte(min(2 ** versuch, 30))
                    continue
                if fehler.code == 401:
                    raise ApiFehler(401, "unauthorized",
                                    "Hetzner lehnt den API-Token ab. Bitte in der Hetzner Console unter "
                                    "Projekt hh-portal → Sicherheit → API-Tokens einen Token mit "
                                    "'Lesen & Schreiben' erzeugen und als HCLOUD_TOKEN setzen "
                                    "(bzw. im Sitzungs-Proxy hinterlegen).") from None
                raise ApiFehler(fehler.code, code, info.get("message", fehler.reason)) from None
            except urllib.error.URLError as fehler:
                if versuch < versuche:
                    self.warte(min(2 ** versuch, 30))
                    continue
                raise ApiFehler(0, "netzwerk", f"API nicht erreichbar: {fehler.reason}") from None
        raise AssertionError("unerreichbar")

    def liste(self, pfad: str, schluessel: str, **filter_) -> list[dict]:
        ergebnis, seite = [], 1
        while seite:
            query = urllib.parse.urlencode({**filter_, "page": seite, "per_page": 50})
            daten = self.anfrage("GET", f"{pfad}?{query}")
            ergebnis.extend(daten.get(schluessel, []))
            seite = ((daten.get("meta") or {}).get("pagination") or {}).get("next_page")
        return ergebnis

    def nach_name(self, pfad: str, schluessel: str, name: str) -> dict | None:
        treffer = [o for o in self.liste(pfad, schluessel, name=name) if o.get("name") == name]
        return treffer[0] if treffer else None


# ----------------------------------------------------------------------------- Auswahl & Preise
def zahl(text) -> float:
    return float(text) if text not in (None, "") else 0.0


def verfuegbare_typen(api: Hetzner) -> dict[str, set[int]]:
    """Standort → IDs der Servertypen, die dort aktuell bestellbar sind."""
    verfuegbar: dict[str, set[int]] = {}
    for dc in api.liste("/datacenters", "datacenters"):
        ort = (dc.get("location") or {}).get("name")
        if ort in STANDORTE:
            verfuegbar.setdefault(ort, set()).update((dc.get("server_types") or {}).get("available", []))
    return verfuegbar


def ist_abgekuendigt(typ: dict, ort: str) -> bool:
    if typ.get("deprecated") or typ.get("deprecation"):
        return True
    for eintrag in typ.get("locations") or []:
        if eintrag.get("name") == ort and eintrag.get("deprecation"):
            return True
    return False


def kandidaten(api: Hetzner) -> list[dict]:
    verfuegbar = verfuegbare_typen(api)
    liste = []
    for typ in api.liste("/server_types", "server_types"):
        if typ.get("architecture", "x86") != "x86":
            continue
        if typ.get("cores", 0) < MIN_KERNE or zahl(typ.get("memory")) < MIN_RAM_GB:
            continue
        for preis in typ.get("prices", []):
            ort = preis.get("location")
            if ort not in STANDORTE or typ["id"] not in verfuegbar.get(ort, set()) or ist_abgekuendigt(typ, ort):
                continue
            liste.append({
                "typ": typ["name"], "ort": ort, "kerne": typ["cores"], "ram": zahl(typ["memory"]),
                "platte": typ.get("disk"), "cpu": typ.get("cpu_type", ""),
                "netto": zahl(preis["price_monthly"]["net"]), "brutto": zahl(preis["price_monthly"]["gross"]),
            })
    # günstigster zuerst; bei Gleichstand nbg1 vor fsn1, dann Name
    return sorted(liste, key=lambda k: (k["netto"], STANDORTE.index(k["ort"]), k["typ"]))


def zusatzkosten(api: Hetzner, ort: str) -> dict:
    """Backup-Aufschlag (%) und Preis der öffentlichen IPv4 laut /pricing (falls abrufbar)."""
    ergebnis = {"backup_prozent": 20.0, "ipv4_netto": None, "ipv4_brutto": None}
    try:
        preise = api.anfrage("GET", "/pricing").get("pricing", {})
    except ApiFehler as fehler:
        if fehler.status == 401:
            raise
        return ergebnis
    ergebnis["backup_prozent"] = zahl((preise.get("server_backup") or {}).get("percentage") or 20)
    for ip in preise.get("primary_ips") or []:
        if ip.get("type") == "ipv4":
            for p in ip.get("prices", []):
                if p.get("location") == ort:
                    ergebnis["ipv4_netto"] = zahl(p["price_monthly"]["net"])
                    ergebnis["ipv4_brutto"] = zahl(p["price_monthly"]["gross"])
    return ergebnis


def euro(betrag: float | None) -> str:
    return "–" if betrag is None else f"{betrag:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def kosten_ausgeben(wahl: dict, extra: dict) -> None:
    faktor = extra["backup_prozent"] / 100
    netto = wahl["netto"] * (1 + faktor) + (extra["ipv4_netto"] or 0)
    brutto = wahl["brutto"] * (1 + faktor) + (extra["ipv4_brutto"] or 0)
    print(f"  Server {wahl['typ']} ({wahl['kerne']} vCPU, {wahl['ram']:g} GB RAM, {wahl['platte']} GB, "
          f"{wahl['cpu']}) in {wahl['ort']}: {euro(wahl['netto'])} netto / {euro(wahl['brutto'])} brutto pro Monat")
    print(f"  Hetzner-Backups (+{extra['backup_prozent']:g} %): {euro(wahl['netto'] * faktor)} netto")
    print(f"  Öffentliche IPv4: {euro(extra['ipv4_netto'])} netto")
    print(f"  Summe ca. {euro(netto)} netto / {euro(brutto)} brutto pro Monat (Preise laut Hetzner-API, "
          "brutto mit der USt. des Kontos)")


# ----------------------------------------------------------------------------- Firewall
def regeln_normal(regeln: list[dict]) -> list[tuple]:
    return sorted((r.get("direction"), r.get("protocol"), r.get("port") or "", tuple(sorted(r.get("source_ips") or [])))
                  for r in regeln)


def firewall_sicherstellen(api: Hetzner, trocken: bool) -> dict | None:
    fw = api.nach_name("/firewalls", "firewalls", FIREWALL_NAME)
    if fw is None:
        print(f"Firewall {FIREWALL_NAME}: wird angelegt (TCP 80/443, UDP 443, ICMP; kein SSH)")
        if trocken:
            return None
        return api.anfrage("POST", "/firewalls", {"name": FIREWALL_NAME, "labels": LABELS, "rules": FIREWALL_REGELN})["firewall"]
    if regeln_normal(fw.get("rules", [])) != regeln_normal(FIREWALL_REGELN):
        print(f"Firewall {FIREWALL_NAME} (id {fw['id']}): vorhanden, Regeln weichen ab → werden gesetzt")
        if not trocken:
            api.anfrage("POST", f"/firewalls/{fw['id']}/actions/set_rules", {"rules": FIREWALL_REGELN})
    else:
        print(f"Firewall {FIREWALL_NAME} (id {fw['id']}): vorhanden, Regeln stimmen")
    return fw


# ----------------------------------------------------------------------------- Server
def user_data_lesen() -> str:
    text = CLOUD_INIT.read_text(encoding="utf-8")
    if not text.startswith("#cloud-config"):
        raise SystemExit(f"{CLOUD_INIT} beginnt nicht mit #cloud-config.")
    if len(text.encode()) > USER_DATA_MAX:
        raise SystemExit(f"{CLOUD_INIT} ist größer als {USER_DATA_MAX} Bytes (Hetzner-Grenze).")
    return text


def warte_auf_running(api: Hetzner, server_id: int, sekunden: int = 600) -> dict:
    ende = time.monotonic() + sekunden
    while True:
        server = api.anfrage("GET", f"/servers/{server_id}")["server"]
        if server["status"] == "running":
            return server
        if time.monotonic() > ende:
            raise SystemExit(f"Server {server_id} ist nach {sekunden} s noch '{server['status']}'.")
        print(f"  … Status {server['status']}, warte")
        api.warte(5)


def adressen_ausgeben(server: dict) -> None:
    netz = server.get("public_net") or {}
    v4 = (netz.get("ipv4") or {}).get("ip")
    v6 = (netz.get("ipv6") or {}).get("ip")
    print(f"  IPv4: {v4 or '–'}")
    print(f"  IPv6: {v6 or '–'}  (Adresse des Servers: Netz-Präfix mit ::1)")
    if v4:
        print(f"  DNS: A-Record  portal.haus-meister-helden.de → {v4}")


def anlegen(api: Hetzner, trocken: bool) -> int:
    print(f"Hetzner Cloud API: {api.basis}" + ("  [TROCKENLAUF – es wird nichts geändert]" if trocken else ""))
    user_data = user_data_lesen()
    fw = firewall_sicherstellen(api, trocken)
    server = api.nach_name("/servers", "servers", SERVER_NAME)

    if server is None:
        liste = kandidaten(api)
        if not liste:
            raise SystemExit(f"Kein passender Servertyp (x86, >= {MIN_KERNE} vCPU, >= {MIN_RAM_GB:g} GB) "
                             f"in {'/'.join(STANDORTE)} verfügbar.")
        wahl = liste[0]
        print(f"Server {SERVER_NAME}: wird angelegt – {wahl['typ']} in {wahl['ort']}, {IMAGE}, "
              f"Label app=hh-portal, ohne SSH-Key, Backups an")
        kosten_ausgeben(wahl, zusatzkosten(api, wahl["ort"]))
        if len(liste) > 1:
            weitere = ", ".join(f"{k['typ']}/{k['ort']} {euro(k['netto'])}" for k in liste[1:4])
            print(f"  (nächste Alternativen netto: {weitere})")
        if trocken:
            print("Trockenlauf beendet – nichts wurde angelegt.")
            return 0
        antwort = api.anfrage("POST", "/servers", {
            "name": SERVER_NAME,
            "server_type": wahl["typ"],
            "location": wahl["ort"],
            "image": IMAGE,
            "user_data": user_data,
            "labels": LABELS,
            "firewalls": [{"firewall": fw["id"]}],
            "public_net": {"enable_ipv4": True, "enable_ipv6": True},
            "start_after_create": True,
        })
        # antwort["root_password"] wird bewusst NICHT ausgegeben (kein SSH-Key → Passwort-Reset in der Konsole).
        server = antwort["server"]
        print(f"  angelegt (id {server['id']})")
    else:
        print(f"Server {SERVER_NAME} (id {server['id']}): vorhanden, Typ {server['server_type']['name']}, "
              f"Status {server['status']} – wird wiederverwendet (user_data wirkt nur beim Neuanlegen)")
        typ = server["server_type"]
        ort = ((server.get("datacenter") or {}).get("location") or {}).get("name", "")
        for preis in typ.get("prices", []):
            if preis.get("location") == ort:
                kosten_ausgeben({"typ": typ["name"], "ort": ort, "kerne": typ.get("cores"), "ram": zahl(typ.get("memory")),
                                 "platte": typ.get("disk"), "cpu": typ.get("cpu_type", ""),
                                 "netto": zahl(preis["price_monthly"]["net"]),
                                 "brutto": zahl(preis["price_monthly"]["gross"])}, zusatzkosten(api, ort))
        if fw is not None:
            angewendet = {f.get("id") for f in (server.get("public_net") or {}).get("firewalls", [])}
            if fw["id"] not in angewendet:
                print(f"  Firewall {FIREWALL_NAME} ist nicht zugewiesen → wird zugewiesen")
                if not trocken:
                    api.anfrage("POST", f"/firewalls/{fw['id']}/actions/apply_to_resources",
                                {"apply_to": [{"type": "server", "server": {"id": server["id"]}}]})

    if trocken:
        print("Trockenlauf beendet – nichts wurde geändert.")
        return 0

    server = warte_auf_running(api, server["id"])
    if not server.get("backup_window"):
        print("  Hetzner-Backups werden eingeschaltet")
        api.anfrage("POST", f"/servers/{server['id']}/actions/enable_backup")
    else:
        print(f"  Hetzner-Backups aktiv (Fenster {server['backup_window']})")
    print(f"Server {SERVER_NAME} läuft.")
    adressen_ausgeben(server)
    print("Die Einrichtung im Server dauert ca. 5–10 Minuten (Protokoll: /var/log/hh-einrichtung.log).")
    print("Root-Zugang: Hetzner Console → Server → Rescue → 'Root-Passwort zurücksetzen', dann Web-Konsole.")
    return 0


def loeschen(api: Hetzner, wirklich: bool) -> int:
    server = api.nach_name("/servers", "servers", SERVER_NAME)
    fw = api.nach_name("/firewalls", "firewalls", FIREWALL_NAME)
    if server is None and fw is None:
        print("Nichts zu löschen.")
        return 0
    for name, obj in ((f"Server {SERVER_NAME}", server), (f"Firewall {FIREWALL_NAME}", fw)):
        if obj:
            print(f"{name} (id {obj['id']}) wird gelöscht" + ("" if wirklich else " – NUR mit --ja-wirklich"))
    if not wirklich:
        print("Abbruch: Löschen vernichtet den Server mit allen Daten. Zum Ausführen: --loeschen --ja-wirklich")
        return 2
    if server:
        api.anfrage("DELETE", f"/servers/{server['id']}")
        for _ in range(60):  # die Firewall lässt sich erst löschen, wenn der Server weg ist
            if api.nach_name("/servers", "servers", SERVER_NAME) is None:
                break
            api.warte(5)
    if fw:
        api.anfrage("DELETE", f"/firewalls/{fw['id']}")
    print("Gelöscht.")
    return 0


def main(argv: list[str] | None = None, api: Hetzner | None = None) -> int:
    parser = argparse.ArgumentParser(description="Portal-Server bei Hetzner Cloud anlegen (idempotent).")
    parser.add_argument("--trockenlauf", action="store_true", help="nur anzeigen, nichts ändern")
    parser.add_argument("--loeschen", action="store_true", help="Server und Firewall löschen")
    parser.add_argument("--ja-wirklich", action="store_true", help="Bestätigung für --loeschen")
    args = parser.parse_args(argv)
    api = api or Hetzner()
    try:
        if args.loeschen:
            if args.trockenlauf:
                return loeschen(api, False)
            return loeschen(api, args.ja_wirklich)
        return anlegen(api, args.trockenlauf)
    except ApiFehler as fehler:
        print(f"FEHLER: {fehler}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
