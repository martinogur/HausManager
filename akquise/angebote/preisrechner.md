# Preisrechner – Hausmeister Helden

> Grundlage: Preise von der Webseite (siehe `firma/profil.md`). **Ob diese Preise netto oder brutto sind,
> ist noch [OFFEN].** Bis zur Klärung rechnet der Rechner sie als **netto** und schlägt die USt. auf.
> Unten steht zum Vergleich auch die Rechnung, falls die Webseitenpreise brutto gemeint sind.
> Die Tabellenversion mit Formeln liegt in `preisrechner.csv`. Öffnen in Excel oder LibreOffice:
> Trennzeichen Semikolon, Formeln werden beim Import berechnet. Eingaben stehen in Spalte C, Zeilen 2–10.

## 1. Eingaben
| Eingabe | Werte |
|---|---|
| Wohneinheiten (WE) | Anzahl |
| Treppenhäuser | Anzahl (ab dem 2. greift ein Zuschlag, [OFFEN]) |
| Grünfläche | m² (Zuschlag je m² [OFFEN], aktuell 0) |
| Gehwege Winterdienst | lfd. m (Zuschlag je m [OFFEN], aktuell 0) |
| Intervall Treppenhausreinigung | wöchentlich oder 14-täglich |
| Bausteine | Treppenhaus / Mülltonnen / Garten / Winterdienst ja oder nein |

## 2. Sätze und Formeln
| Baustein | Satz (laut Webseite) | Formel Monat |
|---|---|---|
| Treppenhausreinigung | ab 8 € / Einheit / Einsatz | WE × 8 € × Einsätze pro Monat (wöchentlich 52/12 = 4,33; 14-täglich 26/12 = 2,17) |
| Treuerabatt | 10 % | nur bei wöchentlicher Reinigung, nur auf die Treppenhausreinigung [OFFEN: auch auf andere Bausteine?] |
| Mülltonnen-Service | 5 € / Einheit / Monat | WE × 5 € |
| Gartenpflege | 30 € / Einheit / Monat | WE × 30 € (+ m² × Zuschlag [OFFEN]) |
| Winterdienst | ab 8 € / Einheit / Woche, 26 Wochen | Saison = WE × 8 € × 26, zahlbar in 6 Raten (Okt–März) oder verteilt auf 12 Monate |
| Gebäudekontrolle | inklusive | 0 € |
| Kleinreparaturen | 35 € / h | nach Aufwand, nicht in der Pauschale |
| Anfahrt | [OFFEN] | Platzhalter 0 € |
| USt. | [OFFEN] 19 % oder 0 % (§ 19 UStG) | Netto × Satz |

„ab“-Preise sind Mindestpreise. Bei großen oder stark verschmutzten Objekten, schwierigem Zugang oder
großen Flächen setzt der Inhaber nach der Besichtigung einen Zuschlag fest.

## 3. Beispielrechnung: 12 Wohneinheiten, 1 Treppenhaus, wöchentliche Reinigung, alle Bausteine

| Position | Rechnung | Monat netto |
|---|---|---|
| Treppenhausreinigung wöchentlich | 12 WE × 8 € × 52/12 Einsätze | 416,00 € |
| Treuerabatt 10 % | –10 % von 416,00 € | –41,60 € |
| Mülltonnen-Service | 12 WE × 5 € | 60,00 € |
| Gartenpflege | 12 WE × 30 € | 360,00 € |
| Gebäudekontrolle mit Protokoll | inklusive | 0,00 € |
| Anfahrt | [OFFEN] | 0,00 € |
| **Monatspauschale ganzjährig netto** | | **794,40 €** |
| zzgl. 19 % USt. | | 150,94 € |
| **Monatspauschale brutto** | | **945,34 €** |

**Winterdienst (eigener Saisonvertrag)**
| Position | Rechnung | Betrag netto |
|---|---|---|
| Saisonpreis 01.10.–31.03. | 12 WE × 8 € × 26 Wochen | 2.496,00 € |
| als 6 Monatsraten (Okt–März) | 2.496 € / 6 | 416,00 € / Monat |
| alternativ verteilt auf 12 Monate | 2.496 € / 12 | 208,00 € / Monat |

**Alles zusammen, Winterdienst auf 12 Monate verteilt**
| | Betrag |
|---|---|
| Gesamt pro Monat netto | **1.002,40 €** |
| zzgl. 19 % USt. | 190,46 € |
| Gesamt pro Monat brutto | **1.192,86 €** |
| Jahreswert netto | 12.028,80 € |

### Varianten derselben 12 WE
| Variante | Monat netto | Monat brutto (19 %) |
|---|---|---|
| Nur Treppenhaus wöchentlich + Mülltonnen (typisches Einstiegspaket) | 434,40 € | 516,94 € |
| Treppenhaus **14-täglich** (kein Rabatt: 12 × 8 × 26/12 = 208 €) + Müll + Garten | 628,00 € | 747,32 € |
| wie oben + Winterdienst verteilt (208 €) | 836,00 € | 994,84 € |

### Falls die Webseitenpreise **brutto** gemeint sind
Dann wäre das Beispiel „alle Bausteine“ nicht 1.002,40 € netto, sondern 1.002,40 € **brutto**.
Das entspricht 842,35 € netto zzgl. 160,05 € USt. Bei einem Kleinunternehmer (§ 19 UStG) gilt der
Betrag ohne USt. Unterschied für den Betrieb: rund 160 € pro Monat bei diesem einen Objekt.
**Diese Frage sollte der Inhaber vor dem ersten Angebot klären.**

## 4. Plausibilitäts-Hinweise für den Inhaber
- **Garten:** 30 € pro Einheit und Monat ergibt bei 12 WE 4.320 € netto im Jahr. Bei kleinen
  Grünflächen ist das teuer und könnte Hausverwaltungen abschrecken. Bei großen Anlagen mit vielen WE
  und wenig Grün passt der Preis nicht zum Aufwand. Vorschlag: Preis an die m² Grünfläche koppeln oder
  eine Mindestpauschale mit m²-Staffel festlegen. [OFFEN]
- **Winterdienst:** Der Preis nach Einheiten passt bei Reihenhaus-Anlagen nicht gut zu den Gehweglängen.
  Vorschlag: Mindestpauschale plus Zuschlag je lfd. m. [OFFEN]
- **Einsätze pro Monat:** 4,33 (52/12) ist genau. Wenn die Webseite mit 4 rechnet, sind das 8 % weniger.
  Bitte einheitlich festlegen. [OFFEN]
