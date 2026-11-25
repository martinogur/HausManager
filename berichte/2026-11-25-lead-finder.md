# Bericht lead-finder – 25.11.2026 (zweiter Lauf)

## Was wurde gemacht
- `CLAUDE.md`, `firma/profil.md`, `leads/leads.csv` (L001–L021, E001–E015) und `leads/adressen.csv`
  gelesen. Jeder neue Lead wurde mit Name, Anschrift und Webseite gegen die Liste geprüft.
  Es gibt keine Duplikate, auch keine Firma unter anderem Namen an derselben Adresse.
- Schwerpunkt waren die Segmente, die bisher fehlten:
  - Wohnungsbaugesellschaften und Genossenschaften im Kreis Gütersloh und Umland
  - Hausverwaltungen in Orten ohne Leads (Oelde, Halle/Westf., Bielefeld-Senne)
  - Gewerbe mit Außenflächen (Pflege, Neubauquartier)
- Quellen: immer zuerst Impressum und Webseite der Firma. Kandidaten habe ich über das
  Verzeichnis 11880 gefunden und danach auf der eigenen Webseite geprüft.
- Gesammelt wurden nur öffentliche Geschäftsdaten. Personen stehen nur drin, wenn sie im
  Impressum als Inhaber, Geschäftsführer oder Vorstand genannt sind.
- Objektzahlen stehen nur dort, wo die Firma sie selbst veröffentlicht.
- Die Anschriften aller neuen Leads sind mit PLZ und Quelle in `leads/adressen.csv` ergänzt.

## Ergebnis
- **16 neue, geprüfte Leads** (L022–L037): **3× A, 10× B, 3× C**
  - nach Typ: 5 Wohnungsbau (davon 1 Neubauquartier), 9 Hausverwaltung/WEG, 2 Gewerbe (Pflege)
  - neue Orte: Oelde (3), Halle/Westf. (2), Bielefeld-Senne/Brackwede (3), Schloß Holte-Stukenbrock, Verl
- **Offene Ausschreibungen:** Heute habe ich keine neue Ausschreibungssuche gemacht.
  `leads/ausschreibungen.md` ist unverändert und die Empfehlung vom 24.11. gilt weiter
  (Portale abonnieren, nächster Saison-Check im Februar 2027).

## Top-A-Leads (heute 3) und die besten B-Leads
| # | ID | Firma | Ort | Telefon | Grund |
|---|---|---|---|---|---|
| 1 | L026 | AVENIA Quartier GmbH | Gütersloh-Avenwedde | 0171 2200299 | 168 neue Wohnungen in drei Bauabschnitten (Sommer 2026 bis Ende 2027). Der Bauträger übernimmt nach der Übergabe selbst Hausverwaltung und Facility Management. |
| 2 | L022 | KHW Kommunale Haus und Wohnen GmbH | Rheda-Wiedenbrück | 05242 9259-0 | Ca. 1.200 kommunale Wohnungen im ganzen Kreis. Auf der Webseite gibt es ein eigenes Formular „Partner werden“. |
| 3 | L027 | M. Böcker Hausverwaltungen GmbH | Herzebrock-Clarholz | 05245 92462-0 | Seit 1993 tätig, Kerngebiet Kreise GT und WAF. Holt laut Webseite Angebote ein und vergibt Aufträge selbst. |
| 4 | L023 | KWG Halle (Westf.) eG | Halle (Westf.) | 05201 8157-0 | Mehr als 1.700 Wohnungen in Halle, Werther, Borgholzhausen und Versmold. Hat eigene Hausmeister, daher Angebot als Ergänzung. |
| 5 | L024 | gbb Brackwede eG | Bielefeld-Brackwede | 0521 942740 | Ca. 1.800 Wohnungen. Arbeitet mit nebenberuflichen Hauswarten, Chance bei Winterdienst und Vertretung. |
| 6 | L028 | Junkerkalefeld e.K. | Oelde | 02522 838450 | Nennt „Vertragsabschlüsse und -pflege mit Hausmeistern“ als Leistung. |
| 7 | L025 | Bauverein Oelde GmbH | Oelde | 02522 2280 | Rund 600 Wohnobjekte, Bestandspflege über externe Betriebe. |
| 8 | L035 | HEUTE GmbH | Schloß Holte-Stukenbrock | 05207 956050 | Mehrere Pflege-Wohnstandorte, ab 2028 auch Gütersloh-Spexard. |
| 9 | L033 | EPKE & KOLLEGEN GmbH | Bielefeld-Senne | 0521 95036070 | WEG-Verwalter, prüft für die Gemeinschaften die Verträge für Hausmeister und Reinigung. |
| 10 | L032 | Hausverwaltung Manss | Gütersloh | 05241 24870 | Eigene Mietwohnungen in Gütersloh, Anfahrt unter 10 km. |

## Geprüft und bewusst NICHT aufgenommen
- **GSWG Senne eG** (Bielefeld, über 1.500 Wohnungen): Die Tochter OWIS GmbH bietet Hausmeister-,
  Reinigungs- und Winterdienst selbst an, auch für Dritte. Sie ist also **Wettbewerber**, kein Lead.
- **Baugenossenschaft Freie Scholle eG** (Bielefeld): Sie hat eine eigene Haus-Service-GmbH und
  dürfte kaum Bedarf haben.
- **Stephanswerk Wohnungsbau GmbH**: Sitz in Osnabrück, außerhalb des Einsatzgebiets.
- **Sahle Wohnen**: Der Bielefelder Bestand liegt in Baumheide (Norden) und wird aus Lüdenscheid verwaltet.
- **Rieländer (Rietberg)**: Hinter dem Verzeichniseintrag steht eine private Familienseite, kein Unternehmen.
- **Hausverwaltung Krüger (Versmold)**, **KESPA Immobilien (Schloß Holte-Stukenbrock)** und
  **Dirk Lechthoff (Steinhagen)**: Es gibt nur einen Verzeichniseintrag, aber keine eigene Webseite und
  kein Impressum. Sie wurden nicht aufgenommen (Qualität vor Menge). Bei Bedarf kann man telefonisch prüfen.
- **Ärztehäuser**: Bei keinem Ärztehaus ließ sich der Eigentümer oder Verwalter öffentlich klären.
  Diese Objekte laufen meist über Hausverwaltungen, die schon auf der Liste stehen.

## Hinweise
- L026 (AVENIA), L030 (Kuhlmann) und L037 (KF Hausverwaltung) geben im Impressum nur eine
  **Mobilnummer** an. Es ist die veröffentlichte Geschäftsnummer und daher zulässig.
- L028 und L030: Das Verzeichnis 11880 nennt andere Anschriften als das Impressum. Eingetragen ist die
  Anschrift aus dem Impressum.
- L023 (KWG): Im Impressum steht keine E-Mail-Adresse, sie wird nur verschlüsselt angezeigt. Das Feld
  ist leer geblieben. Kontakt per Brief oder Telefon.

## Empfehlung für den `akquise-texter`
1. **AVENIA (L026):** Brief als Partner für Facility-Leistungen nach der Übergabe (Winterdienst,
   Treppenhaus, Tiefgaragen-Zufahrt, Grün, Müll), mit Bezug auf die Bauabschnitte 2026/2027. Danach
   einen Anruf und einen Besuch der Musterwohnung einplanen. Der Brief sollte möglichst noch vor dem
   ersten Winter der fertigen Häuser rausgehen.
2. **KHW (L022):** Brief und ein individueller Text für das Formular „Partner werden“ (nur nach
   Freigabe durch den Inhaber). Ansatz: Pilotobjekt in Gütersloh oder Verl.
3. **KWG (L023) und gbb (L024):** Diese Genossenschaften haben eigene Hausmeister. Deshalb nicht
   „Ersatz“ anbieten, sondern **Ergänzung**: Winterdienst-Spitzen, Urlaubs- und Krankheitsvertretung,
   Grünpflege-Spitzen.
4. **Oelde-Paket (L025, L028, L029):** Drei Briefe gleichzeitig verschicken, damit eine Tour nach Oelde
   wirtschaftlich wird. Anfahrt dabei mit dem Umland-Tarif rechnen.
5. **HEUTE GmbH (L035):** Winterdienst mit Protokoll betonen, wegen der Haftung bei Pflege-Standorten.
6. Kein Kontakt per E-Mail (§ 7 UWG). Nur Brief, Telefon oder Kontaktformular mit individuellem Bezug.

## Fragen an den Inhaber
- Ist Oelde (ca. 23 km, Kreis Warendorf) noch im gewünschten Einsatzgebiet? Laut Profil ist der
  Umkreis noch `[OFFEN]`.
- Dürfen Formulare wie „Partner werden“ bei KHW nach Freigabe des Textes genutzt werden?
- Sollen Wettbewerber wie die GSWG-Tochter OWIS in einer eigenen Liste beobachtet werden?
