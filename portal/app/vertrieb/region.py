"""Einsatzgebiet: Gütersloh + Umkreis (Luftlinie).

Ohne Geocoding-Dienst (keine Datenweitergabe, keine Kosten): Orte werden über eine
Liste der Orte im und am Rand des Einsatzgebiets mit ungefähren Ortsmitte-Koordinaten
erkannt (Genauigkeit ca. ±2 km). Orte nahe der Grenze (Radius ± 3 km) und unbekannte
Orte werden als „prüfen“ gemeldet, nie stillschweigend ausgeschlossen.
"""

import math
import re
import unicodedata
from dataclasses import dataclass

# Ortsmitte (Breite, Länge), gerundet. Quelle: allgemein bekannte Ortslagen; bei Bedarf ergänzen.
ORTE: dict[str, tuple[float, float]] = {
    "gütersloh": (51.9069, 8.3786),
    "rheda-wiedenbrück": (51.8455, 8.3000),
    "rheda": (51.8486, 8.3008),
    "wiedenbrück": (51.8350, 8.3150),
    "verl": (51.8836, 8.5125),
    "harsewinkel": (51.9622, 8.2297),
    "herzebrock-clarholz": (51.8833, 8.2333),
    "herzebrock": (51.8833, 8.2333),
    "clarholz": (51.8960, 8.1980),
    "steinhagen": (52.0094, 8.4122),
    "halle": (52.0597, 8.3594),
    "halle (westf.)": (52.0597, 8.3594),
    "schloß holte-stukenbrock": (51.8958, 8.6194),
    "schloss holte-stukenbrock": (51.8958, 8.6194),
    "rietberg": (51.8000, 8.4278),
    "oelde": (51.8264, 8.1467),
    "langenberg": (51.7728, 8.3175),
    "werther": (52.0750, 8.4167),
    "borgholzhausen": (52.1000, 8.3000),
    "versmold": (52.0436, 8.1500),
    "hövelhof": (51.8167, 8.6500),
    "delbrück": (51.7667, 8.5667),
    "bielefeld": (52.0302, 8.5325),
    "bielefeld-brackwede": (51.9970, 8.4980),
    "brackwede": (51.9970, 8.4980),
    "bielefeld-sennestadt": (51.9450, 8.5880),
    "sennestadt": (51.9450, 8.5880),
    "oerlinghausen": (51.9550, 8.6630),
    "leopoldshöhe": (52.0130, 8.7000),
    "spenge": (52.1400, 8.4830),
    "bad rothenfelde": (52.1100, 8.1600),
    "warendorf": (51.9539, 7.9933),
    "sassenberg": (51.9900, 8.0400),
    "beckum": (51.7553, 8.0411),
    "ennigerloh": (51.8370, 8.0310),
    "wadersloh": (51.7330, 8.2500),
    "lippstadt": (51.6739, 8.3444),
    "herford": (52.1150, 8.6700),
    "paderborn": (51.7189, 8.7575),
}

GRENZBEREICH_KM = 3.0


@dataclass(frozen=True)
class Gebietspruefung:
    ort_erkannt: str | None
    entfernung_km: float | None
    im_einsatzgebiet: bool | None  # None = von Hand prüfen
    hinweis: str


def _normal(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def ort_erkennen(text: str | None) -> str | None:
    """Findet den Ort in Freitext wie „Gütersloh (Strengerstraße 12)“ oder „33378 Rheda-Wiedenbrück“."""
    t = _normal(text or "")
    if not t:
        return None
    t = re.sub(r"^\d{5}\s*", "", t)
    # längste Treffer zuerst, damit „bielefeld-brackwede“ vor „bielefeld“ gewinnt
    for name in sorted(ORTE, key=len, reverse=True):
        if re.search(rf"(^|[\s,(/]){re.escape(name)}($|[\s,)/.-])", t) or t.startswith(name):
            return name
    return None


def luftlinie_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Haversine-Entfernung in km."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def pruefe_gebiet(ort_text: str | None, zentrum: tuple[float, float] = ORTE["gütersloh"], radius_km: float = 30) -> Gebietspruefung:
    ort = ort_erkennen(ort_text)
    if ort is None:
        return Gebietspruefung(None, None, None, "Ort nicht erkannt – bitte Entfernung von Hand prüfen.")
    km = round(luftlinie_km(zentrum, ORTE[ort]), 1)
    if km <= radius_km - GRENZBEREICH_KM:
        return Gebietspruefung(ort, km, True, f"{km:.1f} km Luftlinie – im Einsatzgebiet.")
    if km > radius_km + GRENZBEREICH_KM:
        return Gebietspruefung(ort, km, False, f"{km:.1f} km Luftlinie – außerhalb des Einsatzgebiets ({radius_km:.0f} km).")
    return Gebietspruefung(ort, km, None, f"{km:.1f} km Luftlinie – Grenzbereich, Anfahrt im Einzelfall prüfen.")


def anfahrtszone(entfernung_km: float | None) -> int | None:
    """Zone 1 bis 10 km, Zone 2 10–25 km (Preisliste); darüber Einzelfall (None)."""
    if entfernung_km is None:
        return None
    if entfernung_km <= 10:
        return 1
    if entfernung_km <= 25:
        return 2
    return None
