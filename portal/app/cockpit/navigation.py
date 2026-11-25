"""Hauptnavigation (15 Bereiche + Freigaben). Eigene Seiten, wo Steuerung nötig ist; reine Stammdatenpflege
(Suche, Filter, Detailansicht, Bearbeiten) läuft über die Verwaltungsoberfläche – keine doppelte Oberfläche."""

from django.urls import NoReverseMatch, reverse

from konten.rechte import ist_buero

# (Schlüssel, Titel, URL-Name, SVG-Pfad)
PUNKTE = [
    ("dashboard", "Dashboard", "berichte:dashboard", '<path d="M3 11 12 3l9 8"/><path d="M5 10v10h5v-6h4v6h5V10"/>'),
    ("freigaben", "Freigaben", "cockpit:freigaben", '<path d="M9 12l2 2 4-4"/><rect x="3" y="4" width="18" height="16" rx="2"/>'),
    ("kunden", "Kunden", "admin:stammdaten_kunde_changelist", '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3 3-5 6-5s6 2 6 5"/><path d="M16 11a3 3 0 1 0 0-6M21 20c0-2-1.5-4-4-4.7"/>'),
    ("objekte", "Objekte", "admin:stammdaten_objekt_changelist", '<path d="M4 21V8l8-5 8 5v13"/><path d="M9 21v-6h6v6"/>'),
    ("auftraege", "Aufträge", "cockpit:auftraege", '<path d="M8 4h8l1 3H7z"/><rect x="4" y="7" width="16" height="14" rx="2"/><path d="M8 12h8M8 16h5"/>'),
    ("mitarbeiter", "Mitarbeiter", "admin:personal_mitarbeiter_changelist", '<circle cx="12" cy="7" r="3.5"/><path d="M5 21c0-4 3-6.5 7-6.5s7 2.5 7 6.5"/>'),
    ("bewerbungen", "Bewerbungen", "admin:personal_bewerbung_changelist", '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h4"/>'),
    ("akquise", "Akquise", "cockpit:akquise", '<path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/>'),
    ("angebote", "Angebote", "cockpit:angebot_rechner", '<path d="M6 3h9l4 4v14H6z"/><path d="M9 13h6M9 17h6M9 9h3"/>'),
    ("rechnungen", "Rechnungen", "admin:auftraege_rechnung_changelist", '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6"/>'),
    ("emails", "E-Mails", "admin:kommunikation_emailprotokoll_changelist", '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>'),
    ("marketing", "Marketing", "cockpit:marketing", '<path d="M3 11v2a1 1 0 0 0 1 1h3l5 4V6L7 10H4a1 1 0 0 0-1 1z"/><path d="M16 8a5 5 0 0 1 0 8"/>'),
    ("agenten", "KI-Agenten", "cockpit:agenten", '<rect x="5" y="8" width="14" height="11" rx="3"/><path d="M12 4v4M9 13h.01M15 13h.01"/>'),
    ("automatisierungen", "Automatisierungen", "cockpit:automatisierungen", '<path d="M13 3 4 14h7l-1 7 9-11h-7z"/>'),
    ("controlling", "Controlling", "cockpit:controlling", '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>'),
    ("einstellungen", "Einstellungen", "admin:agenten_firmenparameter_changelist", '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/>'),
]
MOBIL = ("dashboard", "freigaben", "auftraege")


def _url(name: str) -> str | None:
    try:
        return reverse(name)
    except NoReverseMatch:
        return None


def navigation(request) -> dict:
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated and ist_buero(user)):
        return {"nav_punkte": [], "nav_mobil": [], "freigaben_offen": 0}
    from agenten.models import Freigabe

    aktuell = getattr(getattr(request, "resolver_match", None), "view_name", "") or ""
    punkte = []
    for schluessel, titel, name, svg in PUNKTE:
        url = _url(name)
        if url:
            aktiv = aktuell == name or aktuell.startswith(name + "_")   # Detailseiten: cockpit:akquise_lead …
            punkte.append({"schluessel": schluessel, "titel": titel, "url": url, "svg": svg, "aktiv": aktiv})
    return {"nav_punkte": punkte, "nav_mobil": [p for p in punkte if p["schluessel"] in MOBIL],
            "freigaben_offen": Freigabe.objects.filter(status="offen").count()}
