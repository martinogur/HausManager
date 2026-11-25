"""Kalkulation, Scoring und Einsatzgebiet – reine Logik, keine Datenbank."""

from decimal import Decimal

import pytest

from vertrieb import kalkulation as k
from vertrieb import region, scoring


def _beispiel(th, et, wd, rasen, beet, hecke, termine, leerungen):
    return k.Objektdaten(treppenhaeuser=th, etagen=et, reinigung="woechentlich", winterdienst_lfm=Decimal(wd),
                         rasen_qm=Decimal(rasen), beet_qm=Decimal(beet), hecke_lfm=Decimal(hecke),
                         muell_termine_monat=termine, muell_leerungen_monat=leerungen, muellplatz=True, kontrollen_monat=1)


@pytest.mark.parametrize(
    "objekt, erwartet_eur",
    [
        (_beispiel(1, 3, 25, 150, 20, 15, 6, 9), 360),     # MFH 6 WE  (Preiskalkulation Abschnitt 4)
        (_beispiel(1, 4, 45, 300, 40, 30, 7, 16), 471),    # Wohnanlage 12 WE
        (_beispiel(2, 4, 90, 600, 80, 50, 8, 22), 799),    # Anlage 24 WE
    ],
    ids=["6WE", "12WE", "24WE"],
)
def test_beispielobjekte_aus_preiskalkulation(objekt, erwartet_eur):
    ergebnis = k.kalkuliere(objekt)
    assert round(ergebnis.monat_netto_cent / 100) == erwartet_eur
    assert ergebnis.monat_brutto_cent == round(ergebnis.monat_netto_cent * 1.19)
    assert {p.kostenart for p in ergebnis.positionen} == {"Gebäudereinigung", "Müllbeseitigung", "Gartenpflege", "Hauswart", "Winterdienst"}


def test_einzelpositionen_exakt():
    o = _beispiel(1, 3, 25, 150, 20, 15, 6, 9)
    assert k.treppenhaus(o).monat_netto_cent == 15600
    assert k.muelltonnen(o).monat_netto_cent == 7034
    assert k.garten(o).monat_netto_cent == 6851
    assert k.winterdienst(o).monat_netto_cent == 3813  # 457,50 € / 12 kaufmännisch gerundet


def test_vierzehntaegig_mit_zuschlag():
    o = k.Objektdaten(treppenhaeuser=1, etagen=3, reinigung="zweiwoechentlich")
    # 36 € × 1,15 × 2,1667 = 89,70 €
    assert k.treppenhaus(o).monat_netto_cent == 8970


def test_minijob_senkt_selbstkosten_und_warnung_bei_unterdeckung():
    o = _beispiel(1, 3, 25, 150, 20, 15, 6, 9)
    inhaber, minijob = k.kalkuliere(o, "inhaber"), k.kalkuliere(o, "minijob")
    assert minijob.selbstkosten_monat_cent < inhaber.selbstkosten_monat_cent
    assert inhaber.marge_cent > 0 and not any("unter den Selbstkosten" in w for w in inhaber.warnungen)
    leer = k.kalkuliere(k.Objektdaten())
    assert leer.monat_netto_cent == 0 and "Keine Leistung ausgewählt." in leer.warnungen


def test_einzelauftrag_takt_minimum_und_anfahrt():
    assert k.einzelauftrag(10, 1) == {"arbeit_cent": 2700, "anfahrt_cent": 1450, "netto_cent": 4150, "hinweis": ""}
    assert k.einzelauftrag(50, 2)["arbeit_cent"] == 4 * 1350
    assert k.einzelauftrag(50, None)["netto_cent"] is None
    with pytest.raises(ValueError):
        k.einzelauftrag(0, 1)


@pytest.mark.parametrize(
    "text, ort, im_gebiet",
    [
        ("Gütersloh (Strengerstraße 12)", "gütersloh", True),
        ("33378 Rheda-Wiedenbrück", "rheda-wiedenbrück", True),
        ("Bielefeld-Brackwede", "bielefeld-brackwede", True),
        ("Beckum", "beckum", None),                # ~29 km: Grenzbereich
        ("Paderborn", "paderborn", False),
        ("Laer (Kreis Steinfurt)", None, None),
    ],
)
def test_einsatzgebiet(text, ort, im_gebiet):
    p = region.pruefe_gebiet(text)
    assert p.ort_erkannt == ort
    assert p.im_einsatzgebiet is im_gebiet


def test_anfahrtszone():
    assert [region.anfahrtszone(x) for x in (None, 3, 10, 18, 26)] == [None, 1, 1, 2, None]


def _merkmale(**kw):
    basis = dict(zielgruppe="hausverwaltung", regelmaessiger_bedarf=True, geschaetzter_monatsumsatz_cent=90000,
                 entfernung_km=2.0, im_einsatzgebiet=True, hat_postanschrift=True, hat_telefon=True)
    return scoring.LeadMerkmale(**{**basis, **kw})


def test_scoring_prioritaeten():
    a = scoring.bewerte(_merkmale())
    assert a.prioritaet == "A" and a.score >= 70
    b = scoring.bewerte(_merkmale(regelmaessiger_bedarf=False, zielgruppe="einzelhandel", geschaetzter_monatsumsatz_cent=50000))
    assert b.prioritaet == "B"
    c = scoring.bewerte(_merkmale(zielgruppe="privat", regelmaessiger_bedarf=False, geschaetzter_monatsumsatz_cent=5000, entfernung_km=20))
    assert c.prioritaet == "C"
    weit = scoring.bewerte(_merkmale(im_einsatzgebiet=False, entfernung_km=45))
    assert weit.prioritaet == "C"
    gesperrt = scoring.bewerte(_merkmale(widerspruch=True))
    assert (gesperrt.score, gesperrt.prioritaet) == (0, "C")
    assert sum(p for _, p in a.gruende) == a.score and a.als_json()["gruende"]


def test_kontaktwege_nach_uwg():
    ohne = scoring.zulaessige_kontaktwege("hausverwaltung", hat_postanschrift=True, hat_telefon=True, hat_email=True,
                                          email_einwilligung=False, einladung_beleg=False, widerspruch=False)
    assert [w for w, _ in ohne] == ["brief", "telefon"]          # keine Werbe-E-Mail ohne Einwilligung
    privat = scoring.zulaessige_kontaktwege("privat", hat_postanschrift=True, hat_telefon=True, hat_email=True,
                                            email_einwilligung=False, einladung_beleg=False, widerspruch=False)
    assert [w for w, _ in privat] == ["brief"]                     # kein Werbeanruf bei Privatpersonen
    einladung = scoring.zulaessige_kontaktwege("partnernetz", hat_postanschrift=False, hat_telefon=False, hat_email=True,
                                               email_einwilligung=False, einladung_beleg=True, widerspruch=False)
    assert [w for w, _ in einladung] == ["kontaktformular", "email"]
    assert scoring.zulaessige_kontaktwege("hausverwaltung", hat_postanschrift=True, hat_telefon=True, hat_email=True,
                                          email_einwilligung=True, einladung_beleg=False, widerspruch=True) == []


@pytest.mark.parametrize("lfm", [18, 25, 40])
def test_winterdienst_einsatzmodell_entspricht_saisonpreis_bei_20_einsaetzen(lfm):
    m = k.winterdienst_einsatzmodell(lfm)
    assert abs(m["saison_bei_20_cent"] - (k.PREISE["wd_grund"] + lfm * k.PREISE["wd_lfm"])) <= 20   # Cent-Rundung je Einsatz
    assert m["einsatz_cent"] > m["einsatz_selbstkosten_cent"]   # jeder Einsatz deckt seine Kosten
    assert k.winterdienst_einsatzmodell(18)["einsatz_cent"] == 1355


def test_winterdienst_staffel_und_hecke():
    kurz, lang = k.winterdienst_staffel(18), k.winterdienst_staffel(40)
    assert (kurz["bereitstellung_cent"], kurz["streu_cent"], kurz["raeum_cent"]) == (12500, 2500, 5300)
    assert (lang["streu_cent"], lang["raeum_cent"]) == (3250, 7100)   # 15 m über 25 m
    assert kurz["streu_cent"] > kurz["selbstkosten_einsatz_cent"] and lang["streu_cent"] > lang["selbstkosten_einsatz_cent"]
    assert k.heckenschnitt(2.5) == 14875   # 2,5 h × 53,50 € + 15 € Entsorgung
