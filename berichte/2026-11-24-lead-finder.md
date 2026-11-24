# Bericht lead-finder – 24.11.2026 (erster Lauf)

## Was wurde gemacht
- `firma/profil.md` und `leads/leads.csv` gelesen. Die Liste war leer, Duplikate gab es also keine.
- Region: Gütersloh plus ca. 25 km (Rheda-Wiedenbrück, Verl, Harsewinkel, Herzebrock-Clarholz,
  Steinhagen, Halle, Schloß Holte-Stukenbrock, Bielefeld-Süd).
- Quellen: Impressum und Webseite der Firmen (immer zuerst), ergänzend Branchenverzeichnisse
  (golocal, 11880, Gelbe Seiten, jacasa). Bei Ausschreibungen: TED-Such-API sowie die
  Vergabeseiten von Kommune und Kreis.
- Gesammelt wurden nur öffentliche Geschäftsdaten. Personen stehen nur drin, wenn sie im
  Impressum als Inhaber, Geschäftsführer oder Vorstand genannt sind. Was ich nicht gefunden
  habe, ist leer geblieben. Objektzahlen stehen nur dort, wo die Firma sie selbst veröffentlicht.

## Ergebnis
- **21 neue, geprüfte Leads** in `leads/leads.csv` (L001–L021): **9× A, 7× B, 5× C**
  - nach Typ: 15 Hausverwaltung/WEG, 4 Wohnungsbau/Bestandshalter, 2 Bielefelder Wohnungsunternehmen (C)
  - 20 Leads sind über Impressum oder Webseite geprüft. L017 (HVG Rheda) steht nur im Verzeichnis.
- **Offene Ausschreibungen:** Im Kreis Gütersloh ist derzeit keine passende offen. Drei
  Verfahren in der Umgebung habe ich geprüft und als ungeeignet bewertet. Details stehen in
  `leads/ausschreibungen.md`.

## Top-10 A-Leads (es gibt 9 A-Leads, Platz 10 ist der beste B-Lead)
| # | Firma | Ort | Telefon | Grund |
|---|---|---|---|---|
| 1 | Gemeinnütziger Bauverein Gütersloh eG | Gütersloh | 05241 9037-0 | Über 1.600 eigene Mietwohnungen mit Grünanlagen in GT, Harsewinkel, Rheda-Wiedenbrück, Rietberg |
| 2 | SKW Hausverwaltung GmbH | Gütersloh | 05241 5046250 | Sparkassen-Tochter, WEG-, Miet- und SE-Verwaltung im ganzen Kreis Gütersloh |
| 3 | Geno immobilien GmbH – immoEINS | Gütersloh | 05241 23488-0 | WEG-Anlagen von 10 bis 500 Einheiten, eigenes Team in Gütersloh |
| 4 | HVG Hausverwaltungsgesellschaft Oesterhelweg mbH | Gütersloh | 05241 5352-0 | Etablierter Verwalter (laut Verzeichnis seit 1971) für WEG, Miet- und Gewerbeobjekte |
| 5 | LH Miet- und Hausverwaltungs GmbH | Gütersloh | 05241 13060 | Seit 1973 WEG- und Mietverwaltung in der Innenstadt, kurze Wege |
| 6 | Golücke GmbH Hausverwaltung | Gütersloh | 05241 2101818 | Objekte in GT, Harsewinkel, Steinhagen, Rheda. Bewertungen bemängeln Erreichbarkeit (Wechselsignal) |
| 7 | HVW Lüke Hausverwaltung | Verl | 05246 7017817 | Nennt auf der Webseite externe Dienstleister für Reinigung und Grünschnitt |
| 8 | Hausverwaltung S. Stephan GbR | Rheda-Wiedenbrück | 05242 982655 | WEG-, Miet- und SE-Verwaltung mit Online-Schadensmeldung |
| 9 | Hausverwaltung Santak | Rheda-Wiedenbrück | 05242 404641 | WEG-Verwaltung seit 1996. Bewertung bemängelt langsame Rückmeldung (Wechselsignal) |
| 10 (B) | Kai Wackermann Immobilien und Hausverwaltung | Rheda-Wiedenbrück | 05242 9859769 | Koordiniert die Pflege der Objekte selbst und braucht dafür ausführende Partner |

## Offene Ausschreibungen mit Frist
Keine geeignete. Geprüft und verworfen:
- 11.12.2026 – Universität Bielefeld, Baureinigung Neubau R7 (TED 783012-2026): einmalige Großbaureinigung
- 21.12.2026 – BImA, Unterhalts- und Glasreinigung, u. a. ein Objekt in Bielefeld (TED 756514-2026): EU-Verfahren, Büroreinigung
- 14.01.2027 – Stadt Gütersloh, Sinkkästenreinigung (TED 809380-2026): Kanaltechnik

Ein früherer Suchtreffer „Winterdienst Kreis 2026–2030“ (TED 383107-2026) gehört zum **Kreis Soest**
und ist abgelaufen.

## Empfehlung für den `akquise-texter`
1. **Kanal:** Für alle A-Leads einen **Brief**, keine E-Mail (§ 7 UWG). Die E-Mail-Adressen in der CSV
   sind nur für später, wenn der Kontakt zugestimmt hat. Eine Woche nach dem Brief anrufen
   (B2B mit mutmaßlichem Interesse). Bei Santak (L009) sofort anrufen, weil das Büro in der Nähe ist.
2. **Drei Briefvarianten:**
   - *Wohnungsgenossenschaft* (L001 Bauverein): Entlastung bei Spitzen (Winterdienst ab sofort,
     Laub, Grünpflege im Frühjahr) für einzelne Wohnanlagen, als Ergänzung zu den eigenen Leuten.
     Pilotobjekt anbieten.
   - *Große Verwaltungen* (L002, L003, L004, L006): Rahmenvereinbarung für mehrere Objekte,
     Gebäudekontrolle mit Protokoll inklusive, ein fester Ansprechpartner (Martin Ogur),
     Reaktion binnen 24 h. Kostenlose Objektbesichtigung als Einstieg.
   - *Inhabergeführte Verwaltungen* (L005, L007, L008, L009, L010, L015): von Inhaber zu Inhaber.
     Betonen, dass Schäden gemeldet werden, bevor Mieter anrufen. Bei HVW Lüke (L008) an deren
     eigene Webseite anknüpfen: dort werden externe Dienstleister für Reinigung und Grünschnitt genannt.
3. **Wechselsignale vorsichtig nutzen:** Bei Golücke (L005) und Santak (L009) **nicht** auf die
   schlechten Bewertungen hinweisen. Positiv formulieren: „Wir halten Ihnen den Rücken frei,
   melden proaktiv und sind binnen 24 h vor Ort.“
4. **Timing:** Der Winter beginnt. Winterdienst als „sofort startklar“ in den Betreff, mit
   Preis ab 8 € pro Einheit und Woche laut Webseite (vorher klären, ob netto oder brutto).

## Was braucht Freigabe
- Nichts wird verschickt. Die Leadliste ist eine Arbeitsgrundlage, Anschreiben folgen über den `akquise-texter`.

## Fragen an den Inhaber
1. Umkreis bestätigen: Sind 25 km in Ordnung? Gehören Bielefeld-Mitte (L014, L019, L020) und Oelde/Rietberg dazu?
2. Gibt es Kapazität für große Anlagen (Bauverein, immoEINS mit bis zu 500 Einheiten) oder erst einmal nur kleine WEGs?
3. Wären Kooperationen mit Firmen denkbar, die selbst einen Hausmeisterservice haben (E+S Harsewinkel L018), z. B. als Vertretung im Winterdienst?
4. Für Ausschreibungen: Gibt es Betriebshaftpflicht, Gewerbeanmeldung, Unbedenklichkeitsbescheinigungen und Referenzen? [OFFEN]
5. Soll ich die Firma auf dem Vergabeportal OWL und dem Vergabemarktplatz NRW registrieren? Das muss der Inhaber selbst tun (Firmendaten, AGB).
6. Sind die Preise netto oder brutto? Ist Hausmeister Helden Kleinunternehmer? Das ist für Anschreiben und Angebote wichtig.

## Lücken / nächster Lauf
- Für **Schloß Holte-Stukenbrock** und **Halle (Westf.)** habe ich keine Verwaltung mit eigener
  Webseite gefunden. Oekenpöhler Immobilien (Schloß Holte-Stukenbrock) ist nur im Verzeichnis
  ohne Telefon gelistet und deshalb nicht aufgenommen.
- Nicht aufgenommen: Baugenossenschaft Freie Scholle (Bielefeld-Nord, eigene Haus-Service-GmbH),
  Haselhorst Immoservice (Bielefeld-Nord, außerhalb des Umkreises), Krause Hausverwaltung
  Steinhagen (nur Verzeichnis, keine Webseite).
- Nächster Lauf: Gewerbe mit Außenflächen (Arztzentren, Supermärkte, Autohäuser, Hotels in GT
  und Rheda), Neubauprojekte (Bauträger mit neuen WEGs in GT, Verl, Rheda), Gebäudemanagement
  der Kommunen für die Bieterlisten.
