"""Erstellt akquise/angebote/preiskalkulation.xlsx mit echten Excel-Formeln."""
import sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = sys.argv[1]

YELLOW = PatternFill("solid", fgColor="FFF2A8")
HEAD = PatternFill("solid", fgColor="1F4E78")
SUB = PatternFill("solid", fgColor="DDEBF7")
RES = PatternFill("solid", fgColor="E2EFDA")
BOLD = Font(bold=True)
WHITE = Font(bold=True, color="FFFFFF")
thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
EUR = '#,##0.00 "€"'
EUR0 = '#,##0 "€"'
PCT = '0.0%'
NUM = '#,##0.00'

wb = Workbook()

# ------------------------------------------------------------------ Annahmen
ws = wb.active
ws.title = "Annahmen"
A = {}  # key -> absolute reference


def head(ws, row, text, cols=6):
    ws.cell(row=row, column=1, value=text).font = WHITE
    for c in range(1, cols + 1):
        ws.cell(row=row, column=c).fill = HEAD


ws["A1"] = "Hausmeister Helden – Preiskalkulation: Annahmen (alle gelben Felder sind änderbar)"
ws["A1"].font = Font(bold=True, size=14)
ws["A2"] = ("Stand 24.11.2026. Alle Beträge netto (ohne USt.). Gelb = Eingabe/Annahme. "
            "Wer einen Wert ändert, sieht die Wirkung sofort in den Blättern Stundensatz, Einheitspreise und Beispielobjekte.")
ws["A2"].alignment = Alignment(wrap_text=True)
ws.merge_cells("A2:F2")
ws.row_dimensions[2].height = 32
r = 4
for i, t in enumerate(["Nr", "Annahme", "Wert", "Einheit", "Begründung / Quelle", "Art"]):
    c = ws.cell(row=r, column=i + 1, value=t)
    c.font = BOLD
    c.fill = SUB
r += 1

sections = [
    ("1. Unternehmer (Einzelunternehmer, ohne Mitarbeiter)", [
        ("lohn", "Unternehmerlohn-Ziel pro Jahr (vor Einkommensteuer)", 36000, "€/Jahr",
         "Annahme: 3.000 €/Monat vor Steuer, Neustart-Niveau. Inhaber entscheidet. [OFFEN]", "Annahme", EUR0),
        ("kv", "Kranken- und Pflegeversicherung (freiwillig gesetzlich)", 650, "€/Monat",
         "Annahme ca. 21 % von ~3.000 € Gewinn. Mindestbemessung 2026: 1.318,33 €/Monat (BMG). Eigenen Bescheid prüfen.", "Annahme", EUR),
        ("rente", "Altersvorsorge", 300, "€/Monat", "Annahme (keine Pflicht für Hausmeister-Einzelunternehmer; Empfehlung)", "Annahme", EUR),
        ("bu", "Berufsunfähigkeit / Unfallversicherung", 60, "€/Monat", "Annahme, Angebot einholen", "Annahme", EUR),
    ]),
    ("2. Firmenfahrzeug (z. B. gebrauchter Kastenwagen / Caddy mit Anhängerkupplung)", [
        ("kfz_afa", "Leasing bzw. Abschreibung", 280, "€/Monat", "Annahme", "Annahme", EUR),
        ("kfz_vers", "Kfz-Versicherung + Kfz-Steuer", 1100, "€/Jahr", "Annahme, Angebot einholen", "Annahme", EUR0),
        ("kfz_km", "Fahrleistung", 18000, "km/Jahr", "Annahme: Touren im Umkreis 25 km um Gütersloh", "Annahme", '#,##0'),
        ("kfz_verbr", "Verbrauch", 7.5, "l/100 km", "Annahme Diesel-Transporter", "Annahme", NUM),
        ("kfz_preis", "Kraftstoffpreis", 1.75, "€/l", "Annahme, Tagespreis prüfen", "Annahme", EUR),
        ("kfz_wart", "Wartung, Reifen, Reparaturen", 900, "€/Jahr", "Annahme", "Annahme", EUR0),
    ]),
    ("3. Betriebskosten", [
        ("bhv", "Betriebshaftpflicht inkl. Winterdienst + Schlüsselverlust", 450, "€/Jahr",
         "Allgemeine Spanne 100–300 €/Jahr (tarifcheck), Winterdienst und Schlüsselschäden erhöhen den Beitrag. Angebot einholen [OFFEN]", "Annahme", EUR0),
        ("ger_ansch", "Geräte-Anschaffung (Mäher, Freischneider, Heckenschere, Laubbläser, Reinigungswagen, Werkzeug, Schneeschieber/Streuwagen)", 6000, "€ einmalig",
         "Annahme", "Annahme", EUR0),
        ("ger_jahre", "Nutzungsdauer Geräte", 4, "Jahre", "Annahme", "Annahme", '0'),
        ("ger_rep", "Geräte-Reparatur, Akkus, Messer, Ersatzteile", 400, "€/Jahr", "Annahme", "Annahme", EUR0),
        ("kleinmat", "Kleinmaterial / Verbrauch allgemein (Säcke, Handschuhe, Schrauben)", 600, "€/Jahr", "Annahme (Reinigungsmittel und Streugut stehen bei den Leistungen)", "Annahme", EUR0),
        ("tel", "Telefon, Handy, Internet", 600, "€/Jahr", "Annahme", "Annahme", EUR0),
        ("software", "Software (Rechnungen, Objektprotokolle, Cloud)", 360, "€/Jahr", "Annahme", "Annahme", EUR0),
        ("werbung", "Webseite (IONOS), Briefe, Flyer, Werbung", 1500, "€/Jahr", "Annahme; Akquise per Brief kostet Porto", "Annahme", EUR0),
        ("stb", "Steuerberater / Buchhaltung", 1800, "€/Jahr", "Annahme, Angebot einholen", "Annahme", EUR0),
        ("ihk", "IHK-Beitrag, freiwillige Berufsgenossenschaft, Gebühren", 400, "€/Jahr", "Annahme", "Annahme", EUR0),
        ("kleidung", "Arbeitskleidung, Schutzausrüstung", 300, "€/Jahr", "Annahme", "Annahme", EUR0),
        ("sonst", "Bank, Büro, Sonstiges", 500, "€/Jahr", "Annahme", "Annahme", EUR0),
    ]),
    ("4. Arbeitszeit des Inhabers", [
        ("wstd", "Wochenarbeitszeit (bezahlbare + nicht bezahlbare Arbeit)", 40, "h/Woche", "Annahme. Mehr Stunden senken den Satz, sind aber auf Dauer kaum durchzuhalten.", "Annahme", '0'),
        ("tage", "Arbeitstage pro Woche", 5, "Tage", "Annahme (Samstag nur Winterdienst/Notfälle)", "Annahme", '0'),
        ("feiertage", "Feiertage an Werktagen (NRW)", 10, "Tage/Jahr", "NRW hat 11 gesetzliche Feiertage, ca. 10 fallen auf Werktage", "Annahme", '0'),
        ("urlaub", "Urlaub", 25, "Tage/Jahr", "Annahme", "Annahme", '0'),
        ("krank", "Krankheit", 8, "Tage/Jahr", "Annahme", "Annahme", '0'),
        ("fahrt", "Anteil Fahrzeit zwischen Objekten", 0.12, "% der Arbeitszeit", "Annahme; gilt nur bei dichten Touren. Einzelaufträge bekommen eine Anfahrtspauschale.", "Annahme", PCT),
        ("buero", "Anteil Büro, Angebote, Akquise, Einkauf", 0.13, "% der Arbeitszeit", "Annahme", "Annahme", PCT),
    ]),
    ("5. Wagnis und Gewinn", [
        ("wagnis", "Wagnis (Leerlauf, Zahlungsausfall, Schäden)", 0.03, "%", "Annahme", "Annahme", PCT),
        ("gewinn", "Gewinn (Rücklagen, Investitionen)", 0.05, "%", "Annahme; Unternehmerlohn ist schon in den Kosten", "Annahme", PCT),
        ("ust", "Umsatzsteuer", 0.19, "%", "Regelsatz. 0 % nur bei Kleinunternehmerregelung § 19 UStG", "Recht", PCT),
    ]),
    ("6. Variante mit 1 Minijobber (für Reinigung, Mülltonnen, einfache Gartenarbeit)", [
        ("mj_lohn", "Stundenlohn Minijobber", 15.00, "€/h",
         "Gebäudereiniger-Mindestlohn Lohngruppe 1 ab 01.01.2026: 15,00 €/h (gilt, wenn der Betrieb überwiegend reinigt). Gesetzlicher Mindestlohn 2026: 13,90 €/h. Vorsichtig mit 15,00 € rechnen.", "Recht", EUR),
        ("mj_std", "Stunden pro Monat", 40, "h/Monat", "Minijob-Grenze 2026: 603 €/Monat → bei 15,00 € max. 40,2 h", "Annahme", '0'),
        ("mj_ag", "Arbeitgeber-Abgaben Minijob (KV 13 %, RV 15 %, Steuer 2 %, Umlagen U1 0,8 %, U2 0,22 %, Insolvenz 0,15 %, Unfallvers. ca. 1,6 %)", 0.3277, "% vom Lohn",
         "Minijob-Zentrale 2026: max. 31,17 % + Unfallversicherung ca. 1,6 %", "Recht", PCT),
        ("mj_ausfall", "Bezahlte, nicht gearbeitete Zeit (Urlaub, Krankheit, Feiertage)", 0.12, "%", "Annahme; Minijobber haben Anspruch auf Urlaub und Lohnfortzahlung (U1 erstattet 80 % bei Krankheit)", "Annahme", PCT),
        ("mj_fahrt", "Anteil Fahrzeit Minijobber", 0.10, "%", "Annahme", "Annahme", PCT),
        ("mj_gk", "Zuschlag Gemeinkosten auf Minijob-Kosten (Anleitung, Kontrolle, Fahrzeuganteil, Lohnabrechnung)", 0.15, "%", "Annahme", "Annahme", PCT),
    ]),
    ("7. Zeitansätze Treppenhausreinigung", [
        ("th_grund", "Grundzeit je Treppenhaus und Reinigung (Rüsten, Eingang, Haustür, Briefkästen, Klingel, Matte)", 12, "min", "Annahme; vor Ort beim ersten Objekt stoppen", "Annahme", '0.0'),
        ("th_etage", "Zeit je Etage (Treppenlauf + Podest/Flur kehren und feucht wischen, Handlauf, Schalter)", 9, "min", "Annahme; Forum-Erfahrungswerte privat 10–15 min/Etage, Profis schneller", "Annahme", '0.0'),
        ("th_aufzug", "Zuschlag Aufzug je Reinigung", 5, "min", "Annahme", "Annahme", '0.0'),
        ("th_mat", "Reinigungsmittel und Verschleiß je Treppenhaus und Reinigung", 0.80, "€", "Annahme", "Annahme", EUR),
        ("monat", "Einsätze pro Monat bei wöchentlicher Reinigung", "=52/12", "Einsätze", "52 Wochen / 12 Monate = 4,33", "Rechnung", NUM),
        ("th_14", "Zuschlag je Reinigung bei 14-täglicher Reinigung", 0.15, "%", "Annahme: mehr Schmutz je Einsatz", "Annahme", PCT),
    ]),
    ("8. Zeitansätze Winterdienst (Saison 01.11.–31.03.)", [
        ("wd_monate", "Saisonmonate", 5, "Monate", "Viele Satzungen/Verträge: Nov–März. Webseite: Okt–März. Gütersloher Satzung prüfen [OFFEN]", "Annahme", '0'),
        ("wd_eins", "Erwartete Räum-/Streueinsätze je Saison", 20, "Einsätze", "Annahme für das milde Ostwestfalen; strenge Winter deutlich mehr (Risiko → Wagnis)", "Annahme", '0'),
        ("wd_kontr", "Kontrollfahrten ohne Einsatz je Saison (Grenzwetter)", 10, "Fahrten", "Annahme", "Annahme", '0'),
        ("wd_kontr_min", "Zeit je Kontrollfahrt und Objekt", 10, "min", "Annahme", "Annahme", '0'),
        ("wd_ruest", "Rüstzeit je Objekt und Einsatz", 5, "min", "Annahme", "Annahme", '0'),
        ("wd_lfm", "Räumen + Streuen je laufender Meter (Breite ca. 1,5 m, von Hand/Schieber)", 0.30, "min/lfm", "Annahme", "Annahme", '0.00'),
        ("wd_kg", "Streugut je lfm und Einsatz (abstumpfend, Splitt/Granulat)", 0.20, "kg/lfm", "Annahme ca. 130 g/m² bei 1,5 m Breite", "Annahme", '0.00'),
        ("wd_kgpreis", "Preis Streugut", 0.40, "€/kg", "Annahme (Sackware), Einkaufspreis prüfen", "Annahme", EUR),
        ("wd_zuschl", "Zuschlag Frühdienst / Wochenende auf Einsatzzeit", 0.25, "%", "Marktübliche Zuschläge Nacht 25–50 %, So/Feiertag 50–75 % (passau-hausmeisterservice.de)", "Annahme", PCT),
        ("wd_haft", "Zuschlag Haftungsrisiko Winterdienst", 0.10, "%", "Annahme: Verkehrssicherungspflicht geht vertraglich auf uns über", "Annahme", PCT),
        ("wd_breite", "Gehwegbreite für Umrechnung m² ↔ lfm", 1.5, "m", "Annahme, nur für den Marktvergleich", "Annahme", '0.0'),
    ]),
    ("9. Zeitansätze Gartenpflege", [
        ("ga_ruest", "Rüstzeit je Gartengang (Geräte laden, ausladen, Schnittgut laden, Fahrt Grünabfall)", 15, "min", "Annahme", "Annahme", '0'),
        ("ga_mahd", "Mähgänge pro Jahr (April–Oktober 14-täglich + Extras)", 18, "Gänge", "Laut Leistungsverzeichnis 14-täglich Apr–Okt", "Annahme", '0'),
        ("ga_rasen", "Rasen mähen inkl. Kanten trimmen, Schnittgut aufnehmen", 0.15, "min/m²", "Annahme ≈ 400 m²/h (kleine, verwinkelte Flächen)", "Annahme", '0.000'),
        ("ga_beet", "Beete/Pflaster: Unkraut, Pflegeschnitt", 0.5, "min/m²", "Annahme", "Annahme", '0.00'),
        ("ga_beetg", "Beetpflege-Gänge pro Jahr", 7, "Gänge", "Leistungsverzeichnis: monatlich in der Saison (mit Mähgang kombiniert)", "Annahme", '0'),
        ("ga_hecke", "Heckenschnitt bis 2,5 m inkl. Schnittgut", 2.0, "min/lfm", "Annahme", "Annahme", '0.0'),
        ("ga_heckeg", "Heckenschnitte pro Jahr", 2, "Schnitte", "Leistungsverzeichnis: Juni + September", "Annahme", '0'),
        ("ga_laubg", "Laub-Einsätze pro Jahr", 3, "Einsätze", "Leistungsverzeichnis: 2–4 Einsätze", "Annahme", '0'),
        ("ga_laub", "Laub entfernen je m² Grünfläche und Einsatz", 0.05, "min/m²", "Annahme", "Annahme", '0.000'),
        ("ga_entsorg", "Grünschnitt-Entsorgung je m² Grünfläche und Jahr", 0.10, "€/m²/Jahr", "Annahme; Gebühren Grünabfall Kreis Gütersloh prüfen [OFFEN]", "Annahme", EUR),
    ]),
    ("10. Zeitansätze Mülltonnen-Service und Objektkontrolle", [
        ("mu_besuche", "Besuche je Abfuhrtermin (raus + rein)", 2, "Besuche", "Rausstellen und Zurückstellen sind zwei getrennte Wege", "Annahme", '0'),
        ("mu_eigen", "davon Besuche mit eigener Anfahrt (der andere Weg wird mit Treppenhaus-/Tourtermin kombiniert)", 1, "Besuche", "Annahme: Reinigung auf den Abfuhrtag legen. 2 eintragen, wenn nicht kombinierbar", "Annahme", '0'),
        ("mu_anfahrt", "Anfahrtsanteil je Besuch mit eigener Anfahrt (Tour, Objekte nah beieinander)", 5, "min", "Annahme; bei Einzelobjekt deutlich mehr", "Annahme", '0'),
        ("mu_grund", "Grundzeit je Besuch am Objekt", 1, "min", "Annahme", "Annahme", '0'),
        ("mu_tonne", "je Behälter-Leerung und Weg", 0.75, "min", "Annahme (1.100-l-Container eher 1,5 min)", "Annahme", '0.00'),
        ("mu_platz", "Müllplatz kehren, Beifang aufsammeln je Woche", 5, "min", "Leistungsverzeichnis: wöchentlich", "Annahme", '0'),
        ("ko_min", "Objektbegehung (Licht, Türen, Fluchtwege, Keller, Dach von unten)", 20, "min", "Annahme für 6–12 WE", "Annahme", '0'),
        ("ko_prot", "Fotoprotokoll schreiben und an Verwaltung senden", 10, "min", "Annahme", "Annahme", '0'),
    ]),
    ("11. Kleinreparaturen und Anfahrt", [
        ("rep_takt", "Abrechnungstakt", 15, "min", "je angefangene 15 Minuten", "Annahme", '0'),
        ("rep_min", "Mindestberechnung Arbeitszeit je Einzelauftrag", 30, "min", "Annahme; marktüblich oft 1 h Mindestabnahme", "Annahme", '0'),
        ("z1_min", "Zone 1 (Gütersloh bis 10 km): Fahrzeit hin + zurück", 20, "min", "Annahme", "Annahme", '0'),
        ("z1_km", "Zone 1: Kilometer hin + zurück", 12, "km", "Annahme", "Annahme", '0'),
        ("z2_min", "Zone 2 (10–25 km, z. B. Verl, Rheda, Harsewinkel, Bielefeld-Süd): Fahrzeit hin + zurück", 40, "min", "Annahme", "Annahme", '0'),
        ("z2_km", "Zone 2: Kilometer hin + zurück", 40, "km", "Annahme", "Annahme", '0'),
        ("anf_ant", "Anteil Fahrzeit, der zusätzlich berechnet wird", 0.5, "%", "Annahme: die andere Hälfte steckt schon im Stundensatz (Fahrzeitanteil)", "Annahme", PCT),
    ]),
    ("12. Aktuelle Webseitenpreise (zum Vergleich; netto/brutto [OFFEN])", [
        ("web_th", "Treppenhausreinigung", 8, "€/WE/Woche", "www.haus-meister-helden.de (firma/profil.md)", "Webseite", EUR),
        ("web_rab", "Treuerabatt bei wöchentlicher Reinigung", 0.10, "%", "Webseite", "Webseite", PCT),
        ("web_wd", "Winterdienst", 8, "€/WE/Woche", "Webseite, Saison Okt–März", "Webseite", EUR),
        ("web_wdw", "Wochen Winterdienst-Saison", 26, "Wochen", "Okt–März (preisrechner.md)", "Webseite", '0'),
        ("web_ga", "Gartenarbeit", 30, "€/WE/Monat", "Webseite (ganzjährig gerechnet wie preisrechner.md)", "Webseite", EUR),
        ("web_mu", "Mülltonnen-Service", 5, "€/WE/Monat", "Webseite", "Webseite", EUR),
        ("web_rep", "Kleinreparaturen", 35, "€/h", "Webseite", "Webseite", EUR),
    ]),
]

nr = 1
for title, items in sections:
    head(ws, r, title)
    r += 1
    for key, label, val, unit, note, art, fmt in items:
        ws.cell(row=r, column=1, value=nr)
        ws.cell(row=r, column=2, value=label).alignment = Alignment(wrap_text=True)
        c = ws.cell(row=r, column=3, value=val)
        c.number_format = fmt
        if art != "Rechnung":
            c.fill = YELLOW
        c.border = BORDER
        ws.cell(row=r, column=4, value=unit)
        ws.cell(row=r, column=5, value=note).alignment = Alignment(wrap_text=True)
        ws.cell(row=r, column=6, value=art)
        A[key] = f"Annahmen!$C${r}"
        r += 1
        nr += 1
    r += 1

ws.column_dimensions["A"].width = 5
ws.column_dimensions["B"].width = 62
ws.column_dimensions["C"].width = 13
ws.column_dimensions["D"].width = 16
ws.column_dimensions["E"].width = 80
ws.column_dimensions["F"].width = 11
ws.freeze_panes = "A5"

# ------------------------------------------------------------------ Stundensatz
st = wb.create_sheet("Stundensatz")
S = {}
st["A1"] = "Stundensatz-Kalkulation (Formeln, verweisen auf Annahmen)"
st["A1"].font = Font(bold=True, size=14)
r = 3


def srow(key, label, formula, fmt=EUR, bold=False, fill=None, note=""):
    global r
    st.cell(row=r, column=1, value=label).alignment = Alignment(wrap_text=True)
    c = st.cell(row=r, column=2, value=formula)
    c.number_format = fmt
    c.border = BORDER
    if bold:
        st.cell(row=r, column=1).font = BOLD
        c.font = BOLD
    if fill:
        st.cell(row=r, column=1).fill = fill
        c.fill = fill
    if note:
        st.cell(row=r, column=3, value=note).alignment = Alignment(wrap_text=True)
    if key:
        S[key] = f"Stundensatz!$B${r}"
    r += 1


def shead(text):
    global r
    head(st, r, text, 3)
    r += 1


shead("A) Kosten Inhaber pro Jahr")
srow("p_lohn", "Unternehmerlohn", f"={A['lohn']}")
srow("p_kv", "Kranken-/Pflegeversicherung", f"={A['kv']}*12")
srow("p_rente", "Altersvorsorge", f"={A['rente']}*12")
srow("p_bu", "BU / Unfall", f"={A['bu']}*12")
srow("P", "Summe persönliche Kosten", f"=SUM({S['p_lohn'].split('!')[1]}:{S['p_bu'].split('!')[1]})", bold=True)
r += 1
shead("B) Fahrzeug pro Jahr")
srow("f1", "Leasing / Abschreibung", f"={A['kfz_afa']}*12")
srow("f2", "Versicherung + Steuer", f"={A['kfz_vers']}")
srow("f3", "Kraftstoff", f"={A['kfz_km']}*{A['kfz_verbr']}/100*{A['kfz_preis']}")
srow("f4", "Wartung / Reifen", f"={A['kfz_wart']}")
srow("F", "Summe Fahrzeug", f"=SUM({S['f1'].split('!')[1]}:{S['f4'].split('!')[1]})", bold=True)
srow("kmk", "Fahrzeugkosten je km (für Anfahrtspauschale)", f"={S['F']}/{A['kfz_km']}", fmt='0.00 "€/km"')
r += 1
shead("C) Betriebskosten pro Jahr")
first = r
srow("b1", "Betriebshaftpflicht", f"={A['bhv']}")
srow("b2", "Geräte (Abschreibung)", f"={A['ger_ansch']}/{A['ger_jahre']}")
srow("b3", "Geräte-Reparatur", f"={A['ger_rep']}")
srow("b4", "Kleinmaterial", f"={A['kleinmat']}")
srow("b5", "Telefon / Internet", f"={A['tel']}")
srow("b6", "Software", f"={A['software']}")
srow("b7", "Webseite / Werbung", f"={A['werbung']}")
srow("b8", "Steuerberater", f"={A['stb']}")
srow("b9", "IHK / BG / Gebühren", f"={A['ihk']}")
srow("b10", "Arbeitskleidung", f"={A['kleidung']}")
srow("b11", "Sonstiges", f"={A['sonst']}")
srow("B", "Summe Betriebskosten", f"=SUM(B{first}:B{r-1})", bold=True)
r += 1
srow("K", "GESAMTKOSTEN PRO JAHR (A+B+C)", f"={S['P']}+{S['F']}+{S['B']}", bold=True, fill=RES)
srow("Km", "… pro Monat", f"={S['K']}/12")
r += 1
shead("D) Produktive (verrechenbare) Stunden des Inhabers")
srow("tage", "Arbeitstage pro Jahr", f"=52*{A['tage']}-{A['feiertage']}-{A['urlaub']}-{A['krank']}", fmt='0')
srow("stdtag", "Stunden pro Arbeitstag", f"={A['wstd']}/{A['tage']}", fmt='0.0')
srow("anw", "Arbeitsstunden pro Jahr", f"={S['tage']}*{S['stdtag']}", fmt='#,##0')
srow("nicht", "davon nicht verrechenbar (Fahrzeit + Büro)", f"={S['anw']}*({A['fahrt']}+{A['buero']})", fmt='#,##0')
srow("prod", "PRODUKTIVE STUNDEN PRO JAHR", f"={S['anw']}-{S['nicht']}", fmt='#,##0', bold=True, fill=RES)
srow("prodw", "… pro Woche (bei 46 Arbeitswochen)", f"={S['prod']}/46", fmt='0.0')
r += 1
shead("E) Stundensatz Inhaber")
srow("SK", "Selbstkosten je produktive Stunde = UNTERGRENZE", f"={S['K']}/{S['prod']}", bold=True, fill=RES,
     note="Darunter arbeitet der Inhaber unter seinem Lohnziel bzw. mit Verlust.")
srow("WG", "Zuschlag Wagnis + Gewinn", f"={A['wagnis']}+{A['gewinn']}", fmt=PCT)
srow("VS", "Verrechnungssatz (Selbstkosten + Wagnis + Gewinn)", f"={S['SK']}*(1+{S['WG']})", bold=True)
srow("VSr", "EMPFOHLENER STUNDENSATZ netto (aufgerundet auf 0,50 €)", f"=ROUNDUP({S['VS']}*2,0)/2", bold=True, fill=RES)
srow("VSb", "… brutto (inkl. USt.)", f"={S['VSr']}*(1+{A['ust']})")
srow("UZ", "Umsatzziel pro Jahr bei voller Auslastung", f"={S['VSr']}*{S['prod']}", fmt=EUR0)
srow("UZm", "… pro Monat", f"={S['UZ']}/12", fmt=EUR0)
r += 1
shead("F) Gegenprobe: Was bleibt beim Webseiten-Stundensatz?")
srow("w_ums", "Umsatz pro Jahr mit Webseiten-Satz bei voller Auslastung", f"={A['web_rep']}*{S['prod']}", fmt=EUR0)
srow("w_rest", "minus Fahrzeug und Betriebskosten = bleibt für Lohn, KV, Rente", f"={S['w_ums']}-{S['F']}-{S['B']}", fmt=EUR0)
srow("w_restm", "… pro Monat", f"={S['w_rest']}/12", fmt=EUR0)
srow("w_lohn", "… nach KV, Rente, BU (vor Einkommensteuer) pro Monat", f"=({S['w_rest']}-{S['p_kv']}-{S['p_rente']}-{S['p_bu']})/12", fmt=EUR0,
     note="Vergleich: Lohnziel laut Annahmen pro Monat siehe nächste Zeile")
srow("w_ziel", "Lohnziel pro Monat (Annahme)", f"={A['lohn']}/12", fmt=EUR0)
r += 1
shead("G) Variante 2: Inhaber + 1 Minijobber")
srow("mj_brutto", "Lohn Minijobber pro Monat", f"={A['mj_lohn']}*{A['mj_std']}")
srow("mj_check", "Prüfung Minijob-Grenze 603 €", f"=IF({S['mj_brutto']}<=603,\"OK – innerhalb 603 €\",\"ACHTUNG: über 603 € → kein Minijob\")", fmt='@')
srow("mj_k", "Arbeitgeberkosten Minijob pro Jahr", f"={S['mj_brutto']}*12*(1+{A['mj_ag']})", fmt=EUR0)
srow("mj_kgk", "… inkl. Gemeinkosten-Zuschlag", f"={S['mj_k']}*(1+{A['mj_gk']})", fmt=EUR0)
srow("mj_prod", "Produktive Stunden Minijobber pro Jahr", f"={A['mj_std']}*12*(1-{A['mj_ausfall']})*(1-{A['mj_fahrt']})", fmt='#,##0')
srow("SKmj", "Selbstkosten je produktive Minijob-Stunde = UNTERGRENZE für Routinearbeit", f"={S['mj_kgk']}/{S['mj_prod']}", bold=True, fill=RES)
srow("SKmix", "Mischsatz Selbstkosten (Inhaber + Minijobber)", f"=({S['K']}+{S['mj_kgk']})/({S['prod']}+{S['mj_prod']})", bold=True)
srow("VSmix", "Mischsatz inkl. Wagnis + Gewinn", f"={S['SKmix']}*(1+{S['WG']})")
srow("mj_plus", "Zusätzlicher Deckungsbeitrag pro Jahr, wenn Minijob-Stunden zum empfohlenen Satz verkauft werden", f"=({S['VSr']}-{S['SKmj']})*{S['mj_prod']}", fmt=EUR0,
     note="Voraussetzung: der Minijobber ist voll mit Aufträgen ausgelastet.")
srow("mj_plusm", "… pro Monat", f"={S['mj_plus']}/12", fmt=EUR0)

st.column_dimensions["A"].width = 70
st.column_dimensions["B"].width = 22
st.column_dimensions["C"].width = 60

# ------------------------------------------------------------------ Marktvergleich
mv = wb.create_sheet("Marktvergleich")
M = {}
mv["A1"] = "Marktvergleich mit Quellen (abgerufen 24.11.2026). Regional = Kreis Gütersloh/OWL, bundesweit = Ratgeber/Portale."
mv["A1"].font = Font(bold=True, size=13)
mv["A2"] = ("Die Zahlen stammen von Anbieter- und Ratgeberseiten, nicht von amtlichen Stellen. Netto/brutto ist oft nicht angegeben. "
            "Nur zur internen Orientierung, nicht in Anschreiben verwenden.")
mv.merge_cells("A2:J2")
hdr = ["ID", "Leistung", "Einheit", "Min", "Max", "Regional / bundesweit", "Quelle", "URL", "Stand der Seite", "netto/brutto"]
for i, t in enumerate(hdr):
    c = mv.cell(row=4, column=i + 1, value=t)
    c.font = WHITE
    c.fill = HEAD
market = [
    ("m_std", "Hausmeister-Stundensatz", "€/h", 30, 50, "bundesweit", "11880.com Preisvergleich (35–50); clean-invoice (30–50 netto, Stand 11.02.2026)", "https://www.11880.com/preisvergleich/hausmeisterservice ; https://www.clean-invoice.com/hausmeisterservice/kosten-und-kalkulation-hausmeisterservice", "11880: ohne Datum; clean-invoice 11.02.2026", "clean-invoice netto"),
    ("m_std_ez", "Stundensatz Einzelunternehmer", "€/h", 15, 35, "bundesweit", "trustlocal (Einzelunternehmer 15–35, regionale Anbieter 25–45, große 35–60)", "https://trustlocal.de/kosten/hausmeisterservice-kosten/", "aktualisiert 23.11.2026", "nicht angegeben"),
    ("m_std_pb", "Stundensatz Anbieter Paderborn (OWL)", "€/h", 50.59, 50.59, "regional (OWL)", "Suchergebnis: Paderborner Anbieter „ab 50,59 € netto pro Stunde und Mitarbeiter“; Ratgeber 2026: 39–55 € netto", "https://wertvoll-hausmeisterservice.de/ratgeber/hausmeisterservice-kosten", "2026", "netto"),
    ("m_th_et", "Treppenhausreinigung je Etage und Reinigung", "€/Etage", 10, 30, "bundesweit", "meister-job.de (10–30 €/Etage oder 5–25 €/Mietpartei je Reinigungsgang); 11880: 25–35 €/Etage bzw. Einsatz", "https://meister-job.de/was-kosten-treppenhaus-reinigen/ ; https://www.11880.com/preisvergleich/hausmeisterservice", "2026", "nicht angegeben"),
    ("m_th_gt", "Treppenhausreinigung wöchentlich, Gütersloh (Hausmeisterei Jäger)", "€/Monat ab", 79, 79, "regional (Gütersloh)", "hausmeisterservice-jaeger.de – „Treppenhausreinigung wöchentlich ab 79 €/Monat“ (an anderer Stelle „ab 29 €“)", "https://hausmeisterservice-jaeger.de/", "© 2026", "zzgl. MwSt."),
    ("m_th_jov", "Treppenhaus- und Gebäudereinigung, Gütersloh (JovanoV)", "€/Monat/Gebäude ab", 90, 90, "regional (Gütersloh)", "Gelbe Seiten (siehe marketing/seo/konkurrenz.md)", "https://www.gelbeseiten.de/gsbiz/c2466b3a-d1c7-4f2a-9b8d-e51f7255daf9", "laut konkurrenz.md 24.11.2026", "nicht angegeben"),
    ("m_th_fix", "Treppenhausreinigung Gütersloh (fixklar, Beispielrechnung)", "€/Etage + 10 € Anfahrt je Reinigung", 12, 12, "regional (Gütersloh)", "fixklar.de – nur über Suchmaschinen-Auszug, Seite beim Abruf 404 → unsicher", "https://www.fixklar.de/preise-treppenhausreinigung-in-guetersloh-buerogebaeude-mit-4-etagen/", "nicht prüfbar", "netto (laut Auszug)"),
    ("m_th_mon", "Treppenhausreinigung wöchentlich je Etage und Monat", "€/Etage/Monat", 35, 97, "bundesweit", "trustlocal Preisliste", "https://trustlocal.de/kosten/hausmeisterservice-kosten/", "23.11.2026", "nicht angegeben"),
    ("m_wd_m2", "Winterdienst Gehweg je m² und Saison (Krüger & Krüger, Seite für Gütersloh)", "€/m²/Saison", 3, 5, "regional (Seite Gütersloh, Firma Dortmund)", "krueger-services.de, Saison 01.11.–31.03., Streugut-Beseitigung 0,10–0,20 €/m²", "https://www.krueger-services.de/dienstleistungen/winterdienst/guetersloh", "© 2003–2026, ohne Gewähr", "nicht angegeben"),
    ("m_wd_bereit", "Winterdienst Bereitschaft Gütersloh (Jäger, Rechner)", "€/Monat Nov–März", 48, 48, "regional (Gütersloh)", "hausmeisterservice-jaeger.de Kostenrechner", "https://hausmeisterservice-jaeger.de/", "© 2026", "netto"),
    ("m_wd_eins", "Winterdienst je Räum-/Streueinsatz Gütersloh (Jäger)", "€/Einsatz", 21.01, 21.01, "regional (Gütersloh)", "hausmeisterservice-jaeger.de", "https://hausmeisterservice-jaeger.de/", "© 2026", "netto"),
    ("m_wd_gt_eins", "Winterdienst Einzeleinsatz privat Gütersloh (wertvoll-gartenservice)", "€/Einsatz", 35, 95, "regional (Gütersloh)", "wertvoll-gartenservice.de: bis 50 m² 35–45, über 100 m² 65–95 €; Saisonvertrag 80–150 €/Monat", "https://www.wertvoll-gartenservice.de/guetersloh/winterdienst-kosten-guetersloh", "© 2026", "nicht angegeben"),
    ("m_wd_mfh", "Winterdienst Saisonpauschale Mehrfamilienhaus", "€/Monat", 80, 200, "bundesweit", "passau-hausmeisterservice.de (MFH 6 WE: 500–900 €/Saison)", "https://www.passau-hausmeisterservice.de/ratgeber/winterdienst-kosten/", "„Preise 2026“", "netto"),
    ("m_ga_m2", "Rasen mähen je m² und Mahd", "€/m²", 0.10, 0.25, "bundesweit", "clean-invoice / hausjournal (0,10–0,25 inkl. Kanten + Entsorgung); andere Quellen bis 0,30", "https://www.clean-invoice.com/wissen/gewerke/gartenpflege-kosten ; https://www.hausjournal.net/rasenmaehen-kosten", "2026", "nicht einheitlich"),
    ("m_ga_std", "Gartenpflege Stundensatz", "€/h", 30, 45, "bundesweit", "trustlocal (30–45); 11880 (35–45)", "https://trustlocal.de/kosten/hausmeisterservice-kosten/ ; https://www.11880.com/preisvergleich/hausmeisterservice", "23.11.2026", "nicht angegeben"),
    ("m_ga_hecke", "Heckenschnitt", "€/lfm", 4.5, 4.5, "bundesweit", "greenox-group.de: 45 € je 10 m (Basis 45 €/h, inkl. MwSt.)", "https://greenox-group.de/hausmeisterservice-preisliste/", "13.08.2023 (alt)", "brutto"),
    ("m_mu", "Mülltonnen rausstellen", "€/Monat je Objekt", 15, 35, "bundesweit", "trustlocal Preisliste", "https://trustlocal.de/kosten/hausmeisterservice-kosten/", "23.11.2026", "nicht angegeben"),
    ("m_mu_gt", "Mülltonnenservice Gütersloh (Jäger)", "€/Monat ab", 59, 59, "regional (Gütersloh)", "hausmeisterservice-jaeger.de (an anderer Stelle „9 €“)", "https://hausmeisterservice-jaeger.de/", "© 2026", "zzgl. MwSt."),
    ("m_ko", "Kontrolldienst je Begehung", "€/Begehung", 15, 30, "bundesweit", "clean-invoice", "https://www.clean-invoice.com/hausmeisterservice/kosten-und-kalkulation-hausmeisterservice", "11.02.2026", "netto"),
    ("m_rep", "Kleinreparaturen", "€/h", 30, 50, "bundesweit", "clean-invoice (30–50); 11880 (35–50 zzgl. Material)", "https://www.clean-invoice.com/hausmeisterservice/kosten-und-kalkulation-hausmeisterservice", "11.02.2026", "netto"),
    ("m_anf1", "Anfahrt 0–10 km", "€/Fahrt", 10, 20, "bundesweit", "trustlocal", "https://trustlocal.de/kosten/hausmeisterservice-kosten/", "23.11.2026", "nicht angegeben"),
    ("m_anf2", "Anfahrt 10–25 km", "€/Fahrt", 20, 35, "bundesweit", "trustlocal", "https://trustlocal.de/kosten/hausmeisterservice-kosten/", "23.11.2026", "nicht angegeben"),
    ("m_we_6", "Hausmeister-Pauschale je WE, Objekt 6 WE", "€/WE/Monat", 40, 60, "bundesweit", "clean-invoice (Basis ca. 25 €/WE, Vollservice 50–60 €/WE)", "https://www.clean-invoice.com/hausmeisterservice/kosten-und-kalkulation-hausmeisterservice", "11.02.2026", "netto"),
    ("m_we_20", "Hausmeister-Pauschale je WE, Objekt 20 WE", "€/WE/Monat", 25, 40, "bundesweit", "clean-invoice", "https://www.clean-invoice.com/hausmeisterservice/kosten-und-kalkulation-hausmeisterservice", "11.02.2026", "netto"),
    ("m_pak_gt", "Hausmeister-Paket Gütersloh (Jäger): Basis bis 10 WE / Werterhalt ab 10 WE / Rundum inkl. Winterdienst", "€/Objekt/Monat ab", 149, 500, "regional (Gütersloh)", "hausmeisterservice-jaeger.de: 149 / 299 / 500 € (zzgl. MwSt., Rahmenvertrag)", "https://hausmeisterservice-jaeger.de/", "© 2026", "zzgl. MwSt."),
    ("m_pak", "Hausmeister-Paket nach Gebäudegröße (bis 6 WE / 7–20 WE / über 20 WE)", "€/Monat", 150, 500, "bundesweit", "trustlocal: 150–300 / 250–400 / 350–500 €", "https://trustlocal.de/kosten/hausmeisterservice-kosten/", "23.11.2026", "nicht angegeben"),
    ("m_bks", "Betriebskostenspiegel: Hauswart / Gebäudereinigung / Gartenpflege", "€/m² Wohnfläche/Monat", 0.15, 0.21, "bundesweit (DMB, Abrechnungsjahr 2024)", "Mieterbund-Betriebskostenspiegel (Hauswart 0,21, Gebäudereinigung 0,21, Garten 0,15) laut nebenkosten-verstehen.de; NRW-Einzelwerte nicht prüfbar", "https://www.nebenkosten-verstehen.de/betriebskostenspiegel", "2026", "brutto (Mieter)"),
    ("m_mlohn", "Gesetzlicher Mindestlohn 2026 (2027: 14,60 €)", "€/h", 13.90, 13.90, "bundesweit (Gesetz)", "Bundesregierung", "https://www.bundesregierung.de/breg-de/aktuelles/mindestlohn-2026-2364720", "2026", "brutto Lohn"),
    ("m_glohn", "Mindestlohn Gebäudereinigung Lohngruppe 1 ab 01.01.2026", "€/h", 15.00, 15.00, "bundesweit (Tarif/AEntG)", "Deutsche Handwerks Zeitung; die-gebaeudedienstleister.de; IG BAU Lohn-Check 2026", "https://www.deutsche-handwerks-zeitung.de/tariflohn-gebaeudereinigung-2025-2026-337962/", "2025/2026", "brutto Lohn"),
]
r = 5
for row in market:
    key = row[0]
    for i, v in enumerate(row):
        c = mv.cell(row=r, column=i + 1, value=v)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if i in (3, 4):
            c.number_format = EUR
    M[key + "_min"] = f"Marktvergleich!$D${r}"
    M[key + "_max"] = f"Marktvergleich!$E${r}"
    r += 1
for col, w in zip("ABCDEFGHIJ", [12, 44, 18, 10, 10, 20, 50, 55, 18, 14]):
    mv.column_dimensions[col].width = w
mv.freeze_panes = "A5"

# ------------------------------------------------------------------ Einheitspreise
ep = wb.create_sheet("Einheitspreise")
E = {}
ep["A1"] = "Einheitspreise je Tätigkeit (Formeln; alle Werte netto)"
ep["A1"].font = Font(bold=True, size=14)
ep["A2"] = ("Untergrenze = Selbstkosten (Zeit × Selbstkosten-Stundensatz + Material) × Faktor. Empfehlung = Untergrenze × (1 + Wagnis + Gewinn), "
            "aufgerundet auf 0,50 € (Beträge unter 5 € auf 1 Cent). Spalte G zeigt die Untergrenze, wenn der Minijobber die Arbeit macht (nur Routinearbeiten).")
ep.merge_cells("A2:M2")
ep.row_dimensions[2].height = 30
hdr = ["Leistung", "Einheit", "Zeit (min)", "Material (€)", "Faktor", "Untergrenze Inhaber", "Untergrenze mit Minijobber",
       "EMPFEHLUNG netto", "Empfehlung brutto 19 %", "Markt min", "Markt max", "Markt-Hinweis", "Webseite heute"]
for i, t in enumerate(hdr):
    c = ep.cell(row=4, column=i + 1, value=t)
    c.font = WHITE
    c.fill = HEAD
    c.alignment = Alignment(wrap_text=True)
ep.row_dimensions[4].height = 30

ONE = "1"
units = [
    # key, label, unit, time, material, factor, minijob?, mmin, mmax, hint, web
    ("th_g", "Treppenhaus: Grundpreis je Treppenhaus und Reinigung", "€/Treppenhaus/Reinigung",
     f"={A['th_grund']}", f"={A['th_mat']}", ONE, True, None, None, "zusammen mit Etagenpreis vergleichen", "8 € je WE und Woche"),
    ("th_e", "Treppenhaus: je Etage und Reinigung", "€/Etage/Reinigung",
     f"={A['th_etage']}", "=0", ONE, True, M["m_th_et_min"], M["m_th_et_max"], "bundesweit 10–30 €/Etage; Gütersloh fixklar ca. 12 €/Etage + 10 € Anfahrt (unsicher)", ""),
    ("th_a", "Treppenhaus: Aufzugkabine je Reinigung", "€/Aufzug/Reinigung",
     f"={A['th_aufzug']}", "=0", ONE, True, None, None, "", ""),
    ("wd_g", "Winterdienst: Grundpauschale je Objekt und Saison (Bereitschaft, Wetterkontrolle, Kontrollfahrten, Rüstzeiten, Protokoll)", "€/Objekt/Saison",
     f"={A['wd_kontr']}*{A['wd_kontr_min']}+{A['wd_eins']}*{A['wd_ruest']}*(1+{A['wd_zuschl']})", "=0", f"=1+{A['wd_haft']}", False,
     None, None, "Gütersloh Jäger: Bereitschaft 48 €/Monat = 240 €/Saison + 21,01 €/Einsatz", "8 € je WE und Woche, 26 Wochen"),
    ("wd_l", "Winterdienst: je laufender Meter Gehweg/Zuweg und Saison (inkl. Streugut)", "€/lfm/Saison",
     f"={A['wd_eins']}*{A['wd_lfm']}*(1+{A['wd_zuschl']})", f"={A['wd_eins']}*{A['wd_kg']}*{A['wd_kgpreis']}", f"=1+{A['wd_haft']}", False,
     f"={M['m_wd_m2_min']}*{A['wd_breite']}", f"={M['m_wd_m2_max']}*{A['wd_breite']}", "Krüger 3–5 €/m² Saison × 1,5 m Breite", ""),
    ("wd_e", "Winterdienst: Einzeleinsatz auf Abruf ohne Vertrag (bis 25 lfm, Zone 1, inkl. Anfahrt)", "€/Einsatz",
     f"=({A['wd_ruest']}+25*{A['wd_lfm']})*(1+{A['wd_zuschl']})+{A['z1_min']}", f"=25*{A['wd_kg']}*{A['wd_kgpreis']}+{A['z1_km']}*{S['kmk']}", f"=1+{A['wd_haft']}", False,
     M["m_wd_gt_eins_min"], M["m_wd_gt_eins_max"], "Gütersloh privat 35–95 €/Einsatz", ""),
    ("ga_r", "Garten: Rüstzeit je Gartengang und Objekt", "€/Gang",
     f"={A['ga_ruest']}", "=0", ONE, True, None, None, "", "30 € je WE und Monat"),
    ("ga_m", "Garten: Rasen mähen inkl. Kanten und Schnittgut, je m² und Mahd", "€/m²/Mahd",
     f"={A['ga_rasen']}", "=0", ONE, True, M["m_ga_m2_min"], M["m_ga_m2_max"], "bundesweit 0,10–0,25 €/m²", ""),
    ("ga_b", "Garten: Beet-/Pflasterpflege je m² und Gang", "€/m²/Gang",
     f"={A['ga_beet']}", "=0", ONE, True, None, None, "", ""),
    ("ga_h", "Garten: Heckenschnitt je lfm und Schnitt (bis 2,5 m)", "€/lfm/Schnitt",
     f"={A['ga_hecke']}", "=0", ONE, False, M["m_ga_hecke_min"], M["m_ga_hecke_max"], "nur 1 Quelle (2023, brutto)", ""),
    ("ga_l", "Garten: Laub je m² Grünfläche und Einsatz", "€/m²/Einsatz",
     f"={A['ga_laub']}", "=0", ONE, True, None, None, "", ""),
    ("ga_e", "Garten: Grünschnitt-Entsorgung je m² Grünfläche und Jahr", "€/m²/Jahr",
     "=0", f"={A['ga_entsorg']}", ONE, True, None, None, "", ""),
    ("ga_s", "Garten: Stundensatz nach Aufwand (Sonderarbeiten)", "€/h",
     "=60", "=0", ONE, False, M["m_ga_std_min"], M["m_ga_std_max"], "bundesweit 30–45 €/h", ""),
    ("mu_t", "Mülltonnen: Grundpreis je Abfuhrtermin (raus + rein)", "€/Termin",
     f"={A['mu_eigen']}*{A['mu_anfahrt']}+{A['mu_besuche']}*{A['mu_grund']}", "=0", ONE, True, None, None, "", "5 € je WE und Monat"),
    ("mu_b", "Mülltonnen: je Behälter-Leerung (raus + rein)", "€/Leerung",
     f"={A['mu_besuche']}*{A['mu_tonne']}", "=0", ONE, True, None, None, "", ""),
    ("mu_p", "Müllplatz kehren je Woche", "€/Woche",
     f"={A['mu_platz']}", "=0", ONE, True, None, None, "", ""),
    ("ko", "Objektkontrolle mit Fotoprotokoll je Begehung (eigener Termin)", "€/Begehung",
     f"={A['ko_min']}+{A['ko_prot']}", "=0", ONE, False, M["m_ko_min"], M["m_ko_max"], "bundesweit 15–30 €", "kostenlos inklusive"),
    ("rep", "Kleinreparaturen je Stunde (Material nach Beleg)", "€/h",
     "=60", "=0", ONE, False, M["m_rep_min"], M["m_rep_max"], "bundesweit 30–50 €; OWL-Anbieter ab 50,59 €", f"={A['web_rep']}"),
    ("rep_t", "Kleinreparaturen je angefangene 15 Minuten", "€/15 min",
     f"={A['rep_takt']}", "=0", ONE, False, None, None, "", ""),
    ("rep_m", "Kleinreparaturen Mindestberechnung Arbeitszeit je Einzelauftrag", "€/Auftrag",
     f"={A['rep_min']}", "=0", ONE, False, None, None, "oft 1 h Mindestabnahme am Markt", ""),
    ("anf1", "Anfahrtspauschale Zone 1 (Gütersloh, bis 10 km)", "€/Fahrt",
     f"={A['z1_min']}*{A['anf_ant']}", f"={A['z1_km']}*{S['kmk']}", ONE, False, M["m_anf1_min"], M["m_anf1_max"], "bundesweit 10–20 €", "[OFFEN]"),
    ("anf2", "Anfahrtspauschale Zone 2 (10–25 km)", "€/Fahrt",
     f"={A['z2_min']}*{A['anf_ant']}", f"={A['z2_km']}*{S['kmk']}", ONE, False, M["m_anf2_min"], M["m_anf2_max"], "bundesweit 20–35 €", "[OFFEN]"),
]
r = 5
for key, label, unit, t, mat, fac, mj, mmin, mmax, hint, web in units:
    ep.cell(row=r, column=1, value=label).alignment = Alignment(wrap_text=True)
    ep.cell(row=r, column=2, value=unit)
    ep.cell(row=r, column=3, value=t).number_format = '0.00'
    ep.cell(row=r, column=4, value=mat).number_format = EUR
    ep.cell(row=r, column=5, value=(fac if fac != ONE else 1)).number_format = '0.00'
    ep.cell(row=r, column=6, value=f"=(C{r}/60*{S['SK']}+D{r})*E{r}").number_format = EUR
    if mj:
        ep.cell(row=r, column=7, value=f"=(C{r}/60*{S['SKmj']}+D{r})*E{r}").number_format = EUR
    else:
        ep.cell(row=r, column=7, value="– (Inhaber)")
    c = ep.cell(row=r, column=8, value=f"=IF(F{r}*(1+{S['WG']})<5,ROUNDUP(F{r}*(1+{S['WG']})*100,0)/100,ROUNDUP(F{r}*(1+{S['WG']})*2,0)/2)")
    c.number_format = EUR
    c.fill = RES
    c.font = BOLD
    ep.cell(row=r, column=9, value=f"=H{r}*(1+{A['ust']})").number_format = EUR
    if mmin:
        ep.cell(row=r, column=10, value=(mmin if mmin.startswith("=") else "=" + mmin)).number_format = EUR
        ep.cell(row=r, column=11, value=(mmax if mmax.startswith("=") else "=" + mmax)).number_format = EUR
    ep.cell(row=r, column=12, value=hint).alignment = Alignment(wrap_text=True)
    ep.cell(row=r, column=13, value=web)
    for col in range(1, 14):
        ep.cell(row=r, column=col).border = BORDER
    E[key] = r
    r += 1
r += 1
ep.cell(row=r, column=1, value="Hinweis 14-tägliche Reinigung: Treppenhauspreise je Reinigung + Zuschlag laut Annahmen (Zeile th_14).").font = Font(italic=True)
r += 1
ep.cell(row=r, column=1, value="Stundensatz Inhaber (Empfehlung, aus Blatt Stundensatz)")
ep.cell(row=r, column=8, value=f"={S['VSr']}").number_format = EUR
for col, w in zip("ABCDEFGHIJKLM", [62, 22, 10, 11, 8, 13, 14, 14, 13, 10, 10, 44, 22]):
    ep.column_dimensions[col].width = w
ep.freeze_panes = "B5"


def EPc(key, col):  # Spalte F=Untergrenze, H=Empfehlung
    return f"Einheitspreise!${col}${E[key]}"


# ------------------------------------------------------------------ Beispielobjekte
bo = wb.create_sheet("Beispielobjekte")
bo["A1"] = "Drei Beispielobjekte: Webseite heute vs. Untergrenze vs. Empfehlung vs. Markt (alle Werte netto pro Monat, wenn nicht anders angegeben)"
bo["A1"].font = Font(bold=True, size=13)
cols = ["C", "D", "E"]
names = ["MFH 6 WE, 3 Etagen", "Wohnanlage 12 WE", "Anlage 24 WE, 2 Treppenhäuser"]
for i, n in enumerate(names):
    c = bo[f"{cols[i]}3"]
    c.value = n
    c.font = WHITE
    c.fill = HEAD
    c.alignment = Alignment(wrap_text=True)
bo["A3"] = "Objektdaten (gelb = änderbar)"
bo["A3"].font = WHITE
bo["A3"].fill = HEAD
bo["B3"].fill = HEAD
bo.row_dimensions[3].height = 30
inputs = [
    ("we", "Wohneinheiten", "WE", [6, 12, 24]),
    ("th", "Treppenhäuser", "Anzahl", [1, 1, 2]),
    ("et", "Etagen je Treppenhaus (EG + OGs; Kellerabgang zählt als Etage, wenn gereinigt)", "Anzahl", [3, 4, 4]),
    ("auf", "Aufzüge", "Anzahl", [0, 0, 0]),
    ("rw", "Treppenhausreinigungen pro Woche", "1 = wöchentlich", [1, 1, 1]),
    ("geh", "Gehweg vor dem Grundstück (Winterdienst)", "lfm", [15, 25, 50]),
    ("zu", "Zuwege: Hauseingang, Mülltonnen, Fahrradraum", "lfm", [10, 20, 40]),
    ("ras", "Rasenfläche", "m²", [150, 300, 600]),
    ("beet", "Beete / Pflasterflächen mit Unkraut", "m²", [20, 40, 80]),
    ("hec", "Hecke", "lfm", [15, 30, 50]),
    ("lee", "Behälter-Leerungen pro Monat (Summe aller Tonnen, z. B. 2 Rest × 2 + Bio 2 + Papier 1 + Gelb 2)", "Leerungen", [9, 16, 22]),
    ("abf", "Abfuhrtermine pro Monat (alle Tonnenarten, verschiedene Tage)", "Termine", [6, 7, 8]),
    ("kon", "Objektkontrollen mit Protokoll pro Monat", "Anzahl", [1, 1, 1]),
]
O = {}
r = 4
for key, label, unit, vals in inputs:
    bo.cell(row=r, column=1, value=label).alignment = Alignment(wrap_text=True)
    bo.cell(row=r, column=2, value=unit)
    for i, v in enumerate(vals):
        c = bo.cell(row=r, column=3 + i, value=v)
        c.fill = YELLOW
        c.border = BORDER
    O[key] = r
    r += 1
bo.cell(row=r, column=1, value="Annahme Flächen: realistische Werte für typische Objekte im Kreis Gütersloh, nicht gemessen. Vor Angebot vor Ort messen.").font = Font(italic=True)
r += 2


def o(key, col):
    return f"{col}${O[key]}"


R = {}


def brow(key, label, ftpl, fmt=EUR, bold=False, fill=None, unit="€/Monat"):
    """ftpl: function(col) -> formula string"""
    global r
    bo.cell(row=r, column=1, value=label).alignment = Alignment(wrap_text=True)
    bo.cell(row=r, column=2, value=unit)
    for col in cols:
        c = bo[f"{col}{r}"]
        c.value = ftpl(col)
        c.number_format = fmt
        c.border = BORDER
        if bold:
            c.font = BOLD
        if fill:
            c.fill = fill
    if bold:
        bo.cell(row=r, column=1).font = BOLD
    if fill:
        bo.cell(row=r, column=1).fill = fill
    R[key] = r
    r += 1


def bhead(text):
    global r
    for cc in range(1, 6):
        bo.cell(row=r, column=cc).fill = SUB
    bo.cell(row=r, column=1, value=text).font = BOLD
    r += 1


def block(prefix, pc, title):
    """Preisblock mit Einheitspreisen aus Spalte pc (F = Untergrenze, H = Empfehlung)."""
    bhead(title)
    brow(prefix + "th", "Treppenhausreinigung",
         lambda c: f"=({o('th',c)}*{EPc('th_g',pc)}+{o('th',c)}*{o('et',c)}*{EPc('th_e',pc)}+{o('auf',c)}*{EPc('th_a',pc)})*{o('rw',c)}*{A['monat']}*IF({o('rw',c)}<1,1+{A['th_14']},1)")
    brow(prefix + "mu", "Mülltonnen-Service inkl. Müllplatz",
         lambda c: f"={o('abf',c)}*{EPc('mu_t',pc)}+{o('lee',c)}*{EPc('mu_b',pc)}+{A['monat']}*{EPc('mu_p',pc)}")
    brow(prefix + "ga", "Gartenpflege (Jahrespreis / 12)",
         lambda c: (f"=(({A['ga_mahd']}+{A['ga_laubg']})*{EPc('ga_r',pc)}"
                    f"+{o('ras',c)}*{A['ga_mahd']}*{EPc('ga_m',pc)}"
                    f"+{o('beet',c)}*{A['ga_beetg']}*{EPc('ga_b',pc)}"
                    f"+{o('hec',c)}*{A['ga_heckeg']}*{EPc('ga_h',pc)}"
                    f"+({o('ras',c)}+{o('beet',c)})*{A['ga_laubg']}*{EPc('ga_l',pc)}"
                    f"+({o('ras',c)}+{o('beet',c)})*{EPc('ga_e',pc)})/12"))
    brow(prefix + "ko", "Objektkontrolle mit Protokoll",
         lambda c: f"={o('kon',c)}*{EPc('ko',pc)}")
    brow(prefix + "sum", "Monatspauschale ganzjährig (ohne Winterdienst)",
         lambda c: f"={c}{R[prefix+'th']}+{c}{R[prefix+'mu']}+{c}{R[prefix+'ga']}+{c}{R[prefix+'ko']}", bold=True)
    brow(prefix + "wd", "Winterdienst Saisonpreis",
         lambda c: f"={EPc('wd_g',pc)}+({o('geh',c)}+{o('zu',c)})*{EPc('wd_l',pc)}", unit="€/Saison")
    brow(prefix + "wd12", "Winterdienst auf 12 Monate verteilt",
         lambda c: f"={c}{R[prefix+'wd']}/12")
    brow(prefix + "tot", "GESAMT pro Monat (Winterdienst auf 12 Monate verteilt)",
         lambda c: f"={c}{R[prefix+'sum']}+{c}{R[prefix+'wd12']}", bold=True, fill=RES)
    brow(prefix + "we", "… je Wohneinheit und Monat",
         lambda c: f"={c}{R[prefix+'tot']}/{o('we',c)}", unit="€/WE/Monat")
    brow(prefix + "jahr", "Jahreswert",
         lambda c: f"={c}{R[prefix+'tot']}*12", fmt=EUR0, unit="€/Jahr")
    global r
    r += 1


# Zeitbedarf
bhead("A) Zeitbedarf pro Jahr (aus den Zeitansätzen)")
brow("h_th", "Treppenhausreinigung",
     lambda c: f"=({o('th',c)}*{A['th_grund']}+{o('th',c)}*{o('et',c)}*{A['th_etage']}+{o('auf',c)}*{A['th_aufzug']})*{o('rw',c)}*52/60", fmt='0.0', unit="h/Jahr")
brow("h_mu", "Mülltonnen-Service",
     lambda c: f"=(({o('abf',c)}*({A['mu_eigen']}*{A['mu_anfahrt']}+{A['mu_besuche']}*{A['mu_grund']})+{o('lee',c)}*{A['mu_besuche']}*{A['mu_tonne']})*12+52*{A['mu_platz']})/60", fmt='0.0', unit="h/Jahr")
brow("h_ga", "Gartenpflege",
     lambda c: (f"=(({A['ga_mahd']}+{A['ga_laubg']})*{A['ga_ruest']}+{o('ras',c)}*{A['ga_mahd']}*{A['ga_rasen']}"
                f"+{o('beet',c)}*{A['ga_beetg']}*{A['ga_beet']}+{o('hec',c)}*{A['ga_heckeg']}*{A['ga_hecke']}"
                f"+({o('ras',c)}+{o('beet',c)})*{A['ga_laubg']}*{A['ga_laub']})/60"), fmt='0.0', unit="h/Jahr")
brow("h_ko", "Objektkontrolle",
     lambda c: f"={o('kon',c)}*12*({A['ko_min']}+{A['ko_prot']})/60", fmt='0.0', unit="h/Jahr")
brow("h_wd", "Winterdienst (ohne Zuschläge)",
     lambda c: f"=({A['wd_kontr']}*{A['wd_kontr_min']}+{A['wd_eins']}*({A['wd_ruest']}+({o('geh',c)}+{o('zu',c)})*{A['wd_lfm']}))/60", fmt='0.0', unit="h/Jahr")
brow("h_sum", "Summe Stunden pro Jahr",
     lambda c: f"=SUM({c}{R['h_th']}:{c}{R['h_wd']})", fmt='0.0', bold=True, unit="h/Jahr")
brow("h_ant", "Anteil an der Jahreskapazität des Inhabers",
     lambda c: f"={c}{R['h_sum']}/{S['prod']}", fmt=PCT, unit="%")
brow("h_obj", "So viele Objekte dieser Art füllen den Inhaber voll aus",
     lambda c: f"={S['prod']}/{c}{R['h_sum']}", fmt='0.0', unit="Objekte")
r += 1

# Webseite
bhead("B) Nach Webseite heute (Webseitenpreise als NETTO gelesen)")
brow("w_th", "Treppenhausreinigung (WE × 8 € × 4,33, minus 10 % Treuerabatt bei wöchentlich)",
     lambda c: f"={o('we',c)}*{A['web_th']}*{o('rw',c)}*{A['monat']}*IF({o('rw',c)}>=1,1-{A['web_rab']},1)")
brow("w_mu", "Mülltonnen-Service (WE × 5 €)", lambda c: f"={o('we',c)}*{A['web_mu']}")
brow("w_ga", "Gartenarbeit (WE × 30 €, ganzjährig)", lambda c: f"={o('we',c)}*{A['web_ga']}")
brow("w_ko", "Gebäudekontrolle (inklusive)", lambda c: "=0")
brow("w_sum", "Monatspauschale ganzjährig (ohne Winterdienst)",
     lambda c: f"={c}{R['w_th']}+{c}{R['w_mu']}+{c}{R['w_ga']}+{c}{R['w_ko']}", bold=True)
brow("w_wd", "Winterdienst Saisonpreis (WE × 8 € × 26 Wochen)", lambda c: f"={o('we',c)}*{A['web_wd']}*{A['web_wdw']}", unit="€/Saison")
brow("w_wd12", "Winterdienst auf 12 Monate verteilt", lambda c: f"={c}{R['w_wd']}/12")
brow("w_tot", "GESAMT pro Monat (Winterdienst auf 12 Monate verteilt)",
     lambda c: f"={c}{R['w_sum']}+{c}{R['w_wd12']}", bold=True, fill=RES)
brow("w_we", "… je Wohneinheit und Monat", lambda c: f"={c}{R['w_tot']}/{o('we',c)}", unit="€/WE/Monat")
brow("w_jahr", "Jahreswert", lambda c: f"={c}{R['w_tot']}*12", fmt=EUR0, unit="€/Jahr")
brow("w_br", "Falls die Webseitenpreise BRUTTO gemeint sind: Gesamt netto pro Monat",
     lambda c: f"={c}{R['w_tot']}/(1+{A['ust']})")
r += 1

block("u_", "F", "C) Untergrenze (Selbstkosten Inhaber, ohne Gewinn)")
block("e_", "H", "D) EMPFEHLUNG (Einheitspreise aus Blatt Einheitspreise)")

bhead("E) Markt: niedrig")
brow("ml_th", "Treppenhaus (Etagen × 10 €/Etage × 4,33)",
     lambda c: f"={o('th',c)}*{o('et',c)}*{M['m_th_et_min']}*{o('rw',c)}*{A['monat']}")
brow("ml_mu", "Mülltonnen (15 €/Monat je Objekt)", lambda c: f"={M['m_mu_min']}")
brow("ml_ga", "Garten (eigene Stunden × 30 €/h)", lambda c: f"={c}{R['h_ga']}*{M['m_ga_std_min']}/12")
brow("ml_ko", "Kontrolle (15 € je Begehung)", lambda c: f"={o('kon',c)}*{M['m_ko_min']}")
brow("ml_wd", "Winterdienst Saison (kleinster Wert: Krüger 3 €/m² oder MFH 80 €/Monat)",
     lambda c: f"=MIN(({o('geh',c)}+{o('zu',c)})*{A['wd_breite']}*{M['m_wd_m2_min']},{M['m_wd_mfh_min']}*{A['wd_monate']})", unit="€/Saison")
brow("ml_tot", "GESAMT pro Monat (Winterdienst auf 12 Monate)",
     lambda c: f"={c}{R['ml_th']}+{c}{R['ml_mu']}+{c}{R['ml_ga']}+{c}{R['ml_ko']}+{c}{R['ml_wd']}/12", bold=True, fill=RES)
r += 1
bhead("F) Markt: hoch")
brow("mh_th", "Treppenhaus (Etagen × 30 €/Etage × 4,33)",
     lambda c: f"={o('th',c)}*{o('et',c)}*{M['m_th_et_max']}*{o('rw',c)}*{A['monat']}")
brow("mh_mu", "Mülltonnen (größter Wert: 35 €/Monat bundesweit oder Gütersloh ab 59 €)", lambda c: f"=MAX({M['m_mu_max']},{M['m_mu_gt_min']})")
brow("mh_ga", "Garten (eigene Stunden × 45 €/h)", lambda c: f"={c}{R['h_ga']}*{M['m_ga_std_max']}/12")
brow("mh_ko", "Kontrolle (30 € je Begehung)", lambda c: f"={o('kon',c)}*{M['m_ko_max']}")
brow("mh_wd", "Winterdienst Saison (größter Wert: Krüger 5 €/m², Jäger-Modell, MFH 200 €/Monat)",
     lambda c: (f"=MAX(({o('geh',c)}+{o('zu',c)})*{A['wd_breite']}*{M['m_wd_m2_max']},"
                f"{M['m_wd_bereit_min']}*{A['wd_monate']}+{M['m_wd_eins_min']}*{A['wd_eins']},{M['m_wd_mfh_max']}*{A['wd_monate']})"), unit="€/Saison")
brow("mh_tot", "GESAMT pro Monat (Winterdienst auf 12 Monate)",
     lambda c: f"={c}{R['mh_th']}+{c}{R['mh_mu']}+{c}{R['mh_ga']}+{c}{R['mh_ko']}+{c}{R['mh_wd']}/12", bold=True, fill=RES)
r += 1

bhead("G) Vergleich")
brow("v_eff_w", "Tatsächlich verdienter Stundensatz mit Webseitenpreisen",
     lambda c: f"={c}{R['w_jahr']}/{c}{R['h_sum']}", unit="€/h")
brow("v_eff_e", "Tatsächlich verdienter Stundensatz mit Empfehlung",
     lambda c: f"={c}{R['e_jahr']}/{c}{R['h_sum']}", unit="€/h")
brow("v_tot", "Webseite gesamt im Verhältnis zur Empfehlung",
     lambda c: f"={c}{R['w_tot']}/{c}{R['e_tot']}", fmt='0%', unit="%")
brow("v_th", "… Treppenhaus Webseite / Empfehlung",
     lambda c: f"={c}{R['w_th']}/{c}{R['e_th']}", fmt='0%', unit="%")
brow("v_mu", "… Mülltonnen Webseite / Empfehlung",
     lambda c: f"={c}{R['w_mu']}/{c}{R['e_mu']}", fmt='0%', unit="%")
brow("v_ga", "… Garten Webseite / Empfehlung",
     lambda c: f"={c}{R['w_ga']}/{c}{R['e_ga']}", fmt='0%', unit="%")
brow("v_wd", "… Winterdienst Webseite / Empfehlung",
     lambda c: f"={c}{R['w_wd']}/{c}{R['e_wd']}", fmt='0%', unit="%")
brow("v_mark", "Empfehlung liegt im Markt? (gesamt)",
     lambda c: f"=IF({c}{R['e_tot']}<{c}{R['ml_tot']},\"unter Markt\",IF({c}{R['e_tot']}>{c}{R['mh_tot']},\"über Markt\",\"im Markt\"))", fmt='@', unit="")

bo.column_dimensions["A"].width = 70
bo.column_dimensions["B"].width = 14
for col in cols:
    bo.column_dimensions[col].width = 18
bo.freeze_panes = "C4"

wb.save(OUT)

import json
json.dump({"R": R, "O": O, "E": E, "S": S}, open(OUT + ".map.json", "w"), indent=1)
print("ok", OUT)
