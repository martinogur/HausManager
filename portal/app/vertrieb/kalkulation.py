"""Angebotskalkulation nach der freigegebenen Preisliste (Stand 24.11.2026).

Quelle der Preise und Zeitansätze: ``akquise/angebote/preiskalkulation.md`` und
``preiskalkulation_erzeugen.py`` (Inhaber-Freigabe 24.11.2026, ``firma/profil.md``).
Intern wird nach Aufwand gerechnet (Treppenhaus/Etage, lfm, m², Termine), nach außen
ergibt sich ein fester Monatspreis je Objekt, aufgeteilt nach Betriebskostenarten.

Das Ergebnis ist immer ein **Entwurf**: Ein Angebot wird erst nach Freigabe durch den
Inhaber verbindlich (Datenbank-Regel ``angebote``).
Alle Beträge in Cent (int), gerundet auf ganze Cent.
"""

import json
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

WOCHEN_PRO_MONAT = Decimal(52) / Decimal(12)  # 4,33

# ----------------------------------------------------------------------------- Preisliste (netto, Cent)
# Einzige Quelle: vertrieb/preisliste.json (auch für Webseite und Firmenprofil, siehe werkzeuge/preise.py).
PREISLISTE = json.loads((Path(__file__).with_name("preisliste.json")).read_text(encoding="utf-8"))
PREISE = {k: (Decimal(v) if isinstance(v, str) else v) for k, v in PREISLISTE["preise"].items()}

# ----------------------------------------------------------------------------- Zeitansätze (Minuten) und Material
ZEIT = {
    "th_grund": Decimal(12), "th_etage": Decimal(9), "th_aufzug": Decimal(5),
    "wd_einsaetze": Decimal(20), "wd_kontrollfahrten": Decimal(10), "wd_kontrolle_min": Decimal(10),
    "wd_ruest": Decimal(5), "wd_lfm": Decimal("0.30"), "wd_zuschlag": Decimal("0.25"),
    "ga_ruest": Decimal(15), "ga_rasen_qm": Decimal("0.15"), "ga_beet_qm": Decimal("0.5"),
    "ga_hecke_lfm": Decimal("2.0"), "ga_laub_qm": Decimal("0.05"),
    "mu_anfahrt": Decimal(5), "mu_grund": Decimal(1), "mu_tonne": Decimal("0.75"), "mu_platz": Decimal(5),
    "kontrolle": Decimal(30),
}
MATERIAL_CENT = {
    "th_je_reinigung": Decimal(80),                 # Reinigungsmittel je Treppenhaus
    "wd_je_lfm_einsatz": Decimal("0.20") * 40,      # 0,2 kg × 0,40 €/kg = 8 Cent
    "ga_entsorgung_qm": Decimal(10),
}
# Selbstkosten je produktive Stunde (Preiskalkulation Abschnitt 3)
SELBSTKOSTEN_STUNDE_CENT = {"inhaber": Decimal(4935), "minijob": Decimal(2892)}

GARTEN_STANDARD = {"mahden": 18, "beetgaenge": 7, "heckenschnitte": 2, "laubeinsaetze": 3}


def _cent(wert) -> int:
    return int(Decimal(wert).quantize(Decimal(1), rounding=ROUND_HALF_UP))


@dataclass
class Position:
    bezeichnung: str
    kostenart: str           # Betriebskostenart für die Umlage
    monat_netto_cent: int
    minuten_monat: Decimal
    material_monat_cent: Decimal = Decimal(0)
    hinweis: str = ""


@dataclass
class Objektdaten:
    treppenhaeuser: int = 0
    etagen: int = 0
    aufzug: bool = False
    reinigung: str | None = None          # 'woechentlich' | 'zweiwoechentlich' | None
    winterdienst_lfm: Decimal | None = None
    rasen_qm: Decimal = Decimal(0)
    beet_qm: Decimal = Decimal(0)
    hecke_lfm: Decimal = Decimal(0)
    garten: dict = field(default_factory=dict)   # Abweichungen von GARTEN_STANDARD
    muell_termine_monat: int = 0
    muell_leerungen_monat: int = 0
    muellplatz: bool = False
    kontrollen_monat: int = 0


@dataclass
class Kalkulation:
    positionen: list[Position]
    ausfuehrung: str
    monat_netto_cent: int
    monat_brutto_cent: int
    minuten_monat: Decimal
    selbstkosten_monat_cent: int
    marge_cent: int
    marge_prozent: Decimal | None
    warnungen: list[str]


def treppenhaus(o: Objektdaten) -> Position | None:
    if not o.treppenhaeuser or not o.reinigung:
        return None
    if o.reinigung not in ("woechentlich", "zweiwoechentlich"):
        raise ValueError("Treppenhausreinigung: 'woechentlich' oder 'zweiwoechentlich'")
    je_reinigung = o.treppenhaeuser * (PREISE["th_grund"] + o.etagen * PREISE["th_etage"]) + (PREISE["th_aufzug"] if o.aufzug else 0)
    reinigungen = WOCHEN_PRO_MONAT if o.reinigung == "woechentlich" else WOCHEN_PRO_MONAT / 2
    if o.reinigung == "zweiwoechentlich":
        je_reinigung = Decimal(je_reinigung) * (1 + PREISE["th_zuschlag_14taegig"])
    minuten = (o.treppenhaeuser * (ZEIT["th_grund"] + o.etagen * ZEIT["th_etage"]) + (ZEIT["th_aufzug"] if o.aufzug else 0)) * reinigungen
    return Position(
        f"Treppenhausreinigung {'wöchentlich' if o.reinigung == 'woechentlich' else '14-täglich'}: "
        f"{o.treppenhaeuser} Treppenhaus/-häuser × {o.etagen} Etagen{' + Aufzug' if o.aufzug else ''}",
        "Gebäudereinigung", _cent(Decimal(je_reinigung) * reinigungen), minuten,
        MATERIAL_CENT["th_je_reinigung"] * o.treppenhaeuser * reinigungen,
    )


def winterdienst(o: Objektdaten) -> Position | None:
    if not o.winterdienst_lfm:
        return None
    lfm = Decimal(o.winterdienst_lfm)
    saison = PREISE["wd_grund"] + lfm * PREISE["wd_lfm"]
    minuten_saison = (ZEIT["wd_kontrollfahrten"] * ZEIT["wd_kontrolle_min"]
                      + ZEIT["wd_einsaetze"] * (ZEIT["wd_ruest"] + lfm * ZEIT["wd_lfm"]) * (1 + ZEIT["wd_zuschlag"]))
    return Position(
        f"Winterdienst Saison Nov–März: Grundpauschale + {lfm:.0f} lfm (Saisonpreis {_cent(saison) / 100:.2f} €, auf 12 Monate verteilt)",
        "Winterdienst", _cent(saison / 12), minuten_saison / 12,
        MATERIAL_CENT["wd_je_lfm_einsatz"] * lfm * ZEIT["wd_einsaetze"] / 12,
        "Saisonpreis gilt für die Saison; die Monatsangabe dient dem Vergleich.",
    )


def garten(o: Objektdaten) -> Position | None:
    if not (o.rasen_qm or o.beet_qm or o.hecke_lfm):
        return None
    g = {**GARTEN_STANDARD, **o.garten}
    gruen = Decimal(o.rasen_qm) + Decimal(o.beet_qm)
    # Gartengänge: Mähgänge + Laub-Einsätze; Beet und Hecke werden mit Mähgängen kombiniert (Preiskalkulation Abschnitt 4)
    gaenge = Decimal(g["mahden"] + g["laubeinsaetze"]) if o.rasen_qm else Decimal(g["beetgaenge"] + g["laubeinsaetze"])
    jahr = (gaenge * PREISE["ga_gang"]
            + Decimal(o.rasen_qm) * PREISE["ga_rasen_qm"] * g["mahden"]
            + Decimal(o.beet_qm) * PREISE["ga_beet_qm"] * g["beetgaenge"]
            + Decimal(o.hecke_lfm) * PREISE["ga_hecke_lfm"] * g["heckenschnitte"]
            + gruen * PREISE["ga_laub_qm"] * g["laubeinsaetze"]
            + gruen * PREISE["ga_entsorgung_qm"])
    minuten_jahr = (gaenge * ZEIT["ga_ruest"]
                    + Decimal(o.rasen_qm) * ZEIT["ga_rasen_qm"] * g["mahden"]
                    + Decimal(o.beet_qm) * ZEIT["ga_beet_qm"] * g["beetgaenge"]
                    + Decimal(o.hecke_lfm) * ZEIT["ga_hecke_lfm"] * g["heckenschnitte"]
                    + gruen * ZEIT["ga_laub_qm"] * g["laubeinsaetze"])
    return Position(
        f"Gartenpflege: Rasen {o.rasen_qm} m² ({g['mahden']} Mahden), Beete {o.beet_qm} m², Hecke {o.hecke_lfm} lfm "
        f"({g['heckenschnitte']} Schnitte), Laub ({g['laubeinsaetze']} Einsätze) – Jahrespreis / 12",
        "Gartenpflege", _cent(jahr / 12), minuten_jahr / 12, MATERIAL_CENT["ga_entsorgung_qm"] * gruen / 12,
    )


def muelltonnen(o: Objektdaten) -> Position | None:
    if not (o.muell_termine_monat or o.muellplatz):
        return None
    monat = (o.muell_termine_monat * PREISE["mu_termin"] + o.muell_leerungen_monat * PREISE["mu_leerung"]
             + (WOCHEN_PRO_MONAT * PREISE["mu_platz_woche"] if o.muellplatz else 0))
    # 2 Wege je Termin, davon 1 mit eigener Anfahrt; je Leerung und Weg 0,75 min
    minuten = (o.muell_termine_monat * (ZEIT["mu_anfahrt"] + 2 * ZEIT["mu_grund"])
               + o.muell_leerungen_monat * 2 * ZEIT["mu_tonne"]
               + (WOCHEN_PRO_MONAT * ZEIT["mu_platz"] if o.muellplatz else 0))
    return Position(
        f"Mülltonnen-Service: {o.muell_termine_monat} Abfuhrtermine, {o.muell_leerungen_monat} Leerungen"
        f"{', Müllplatz wöchentlich' if o.muellplatz else ''}",
        "Müllbeseitigung", _cent(monat), minuten,
    )


def kontrolle(o: Objektdaten) -> Position | None:
    if not o.kontrollen_monat:
        return None
    return Position(f"Objektkontrolle mit Fotoprotokoll: {o.kontrollen_monat}× im Monat", "Hauswart",
                    o.kontrollen_monat * PREISE["kontrolle"], ZEIT["kontrolle"] * o.kontrollen_monat)


def kalkuliere(o: Objektdaten, ausfuehrung: str = "inhaber", ziel_marge_prozent: Decimal = Decimal(8)) -> Kalkulation:
    """Monatspreis netto/brutto, Arbeitszeit, Selbstkosten und Marge eines Objekts."""
    if ausfuehrung not in SELBSTKOSTEN_STUNDE_CENT:
        raise ValueError("ausfuehrung: 'inhaber' oder 'minijob'")
    positionen = [p for p in (treppenhaus(o), muelltonnen(o), garten(o), kontrolle(o), winterdienst(o)) if p]
    netto = sum(p.monat_netto_cent for p in positionen)
    minuten = sum((p.minuten_monat for p in positionen), Decimal(0))
    material = sum((p.material_monat_cent for p in positionen), Decimal(0))
    selbstkosten = _cent(minuten / 60 * SELBSTKOSTEN_STUNDE_CENT[ausfuehrung] + material)
    marge = netto - selbstkosten
    marge_prozent = (Decimal(marge) * 100 / netto).quantize(Decimal("0.1")) if netto else None
    warnungen = []
    if not positionen:
        warnungen.append("Keine Leistung ausgewählt.")
    if marge < 0:
        warnungen.append("Preis liegt unter den Selbstkosten – so nicht anbieten.")
    elif marge_prozent is not None and marge_prozent < ziel_marge_prozent:
        warnungen.append(f"Marge {marge_prozent} % liegt unter dem Ziel von {ziel_marge_prozent} %.")
    return Kalkulation(positionen, ausfuehrung, netto, _cent(Decimal(netto) * Decimal("1.19")), minuten.quantize(Decimal("0.1")),
                       selbstkosten, marge, marge_prozent, warnungen)


def einzelauftrag(minuten: int, zone: int | None) -> dict:
    """Kleinreparatur/Sonderarbeit: je angefangene 15 Min., mindestens 30 Min., plus Anfahrt."""
    if minuten <= 0:
        raise ValueError("Arbeitszeit muss positiv sein")
    viertel = -(-minuten // 15)
    arbeit = max(viertel * PREISE["viertelstunde"], PREISE["mindestauftrag"])
    if zone not in (1, 2):
        return {"arbeit_cent": arbeit, "anfahrt_cent": None, "netto_cent": None,
                "hinweis": "Anfahrt außerhalb Zone 1/2 – Einzelfall, Inhaber entscheidet."}
    anfahrt = PREISE[f"anfahrt_zone{zone}"]
    return {"arbeit_cent": arbeit, "anfahrt_cent": anfahrt, "netto_cent": arbeit + anfahrt, "hinweis": ""}


# ----------------------------------------------------------------------------- Winterdienst: Bereitstellung + je Einsatz
# Abgeleitet aus der freigegebenen Saisonpreisliste (220 € + 9,50 €/lfm bei 20 erwarteten Einsätzen):
#   Bereitstellung 120 € je Objekt und Saison (Bereitschaft, Wetterkontrolle, Kontrollfahrten, Einsatzprotokoll)
#   + je Einsatz 5,00 € + 0,475 € je lfd. Meter (Räumen und Streuen inkl. Streugut).
# Bei 20 Einsätzen ergibt das exakt den Saisonpreis; milde Winter werden günstiger, harte teurer.
WD_BEREITSTELLUNG_CENT = 12000
WD_EINSATZ_GRUND_CENT = Decimal(500)
WD_EINSATZ_JE_LFM_CENT = Decimal("47.5")
WD_ERWARTETE_EINSAETZE = 20


def winterdienst_einsatzmodell(lfm) -> dict:
    lfm = Decimal(str(lfm))
    einsatz = _cent(WD_EINSATZ_GRUND_CENT + WD_EINSATZ_JE_LFM_CENT * lfm)
    selbstkosten = _cent((ZEIT["wd_ruest"] + lfm * ZEIT["wd_lfm"]) * (1 + ZEIT["wd_zuschlag"]) / 60
                         * SELBSTKOSTEN_STUNDE_CENT["inhaber"] + MATERIAL_CENT["wd_je_lfm_einsatz"] * lfm)
    return {"bereitstellung_cent": WD_BEREITSTELLUNG_CENT, "einsatz_cent": einsatz,
            "saison_bei_20_cent": WD_BEREITSTELLUNG_CENT + WD_ERWARTETE_EINSAETZE * einsatz,
            "einsatz_selbstkosten_cent": selbstkosten}


# ----------------------------------------------------------------------------- Winterdienst-Staffel (Marktmodell)
# Aufbau nach marktüblichem Angebot (Vergleichsangebot GaLaBau OWL, 03/2026: 125 € / 25 € / 53 € / 58 €/h):
#   Bereitstellung je Saison · Streueinsatz (Glätte, Schnee bis 3 cm) · Räumen + Streuen (bis 15 cm)
#   · darüber nach Aufwand (Stundensatz). Grundpreise gelten bis 25 lfd. Meter, darüber Meterzuschlag.
WD_STAFFEL = PREISLISTE["winterdienst_staffel"]


def winterdienst_staffel(lfm) -> dict:
    mehr = max(Decimal(0), Decimal(str(lfm)) - WD_STAFFEL["grund_meter"])
    streu = _cent(WD_STAFFEL["streu_bis_25m"] + WD_STAFFEL["streu_je_weiterer_m"] * mehr)
    raeum = _cent(WD_STAFFEL["raeum_bis_25m"] + WD_STAFFEL["raeum_je_weiterer_m"] * mehr)
    return {"bereitstellung_cent": WD_STAFFEL["bereitstellung"], "streu_cent": streu, "raeum_cent": raeum,
            "stunde_cent": PREISE["stunde"], "selbstkosten_einsatz_cent": winterdienst_einsatzmodell(lfm)["einsatz_selbstkosten_cent"]}


def heckenschnitt(stunden, entsorgung_cent: int = PREISLISTE["hecke"]["entsorgung_cent"]) -> int:
    """Heckenschnitt nach Aufwand (Höhe > 1,5 m, beidseitig + oben): Stunden × Stundensatz + Entsorgung Schnittgut."""
    return _cent(Decimal(str(stunden)) * PREISE["stunde"] + entsorgung_cent)
