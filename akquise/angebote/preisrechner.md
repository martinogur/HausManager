# Preisrechner – Hausmeister Helden

> Grundlage: Preisliste vom 24.11.2026, freigegeben vom Inhaber (siehe `firma/profil.md`, Abschnitt „Preise“,
> und `preiskalkulation.md`). **Alle Preise netto zzgl. 19 % MwSt.**
> Abgerechnet wird nach Aufwand (Treppenhaus/Etage, laufender Meter Gehweg, m² Grünfläche, Abfuhrtermin),
> nicht pro Wohneinheit. Der Hausverwaltung nennen wir daraus einen festen Monatspreis pro Objekt.
> Die Tabellenversion mit Formeln liegt in `preisrechner.csv`. Öffnen in Excel oder LibreOffice:
> Trennzeichen Semikolon, Formeln werden beim Import berechnet. Eingaben stehen in Spalte C, Zeilen 2–17.

## 1. Eingaben (vor Ort messen)
| Eingabe | Werte |
|---|---|
| Treppenhäuser | Anzahl |
| Etagen je Treppenhaus | Anzahl |
| Aufzugkabinen | Anzahl |
| Intervall Treppenhausreinigung | wöchentlich oder 14-täglich |
| Gehweg + Zuwege Winterdienst | lfd. m |
| Rasen / Beete / Hecke | m² / m² / lfd. m |
| Abfuhrtermine und Tonnen-Leerungen | je Monat laut Abfuhrkalender |
| Objektkontrollen mit Fotoprotokoll | je Monat (0 = nur Sichtkontrolle) |
| Bausteine | Treppenhaus / Mülltonnen / Garten / Winterdienst ja oder nein |

## 2. Sätze und Formeln (netto)
| Baustein | Satz | Formel |
|---|---|---|
| Treppenhausreinigung | 12 € je Treppenhaus und Reinigung + 8 € je Etage, Aufzug + 4,45 € | (Treppenhäuser × (12 € + Etagen × 8 €) + Aufzüge × 4,45 €) × Reinigungen pro Monat (wöchentlich 52/12 = 4,33; 14-täglich 26/12 = 2,17) |
| … 14-täglich | + 15 % je Reinigung | Preis je Reinigung × 1,15 |
| Mülltonnen-Service | 6,50 € je Abfuhrtermin + 1,34 € je Leerung, Müllplatz kehren 4,45 €/Woche | Termine × 6,50 € + Leerungen × 1,34 € + 4,45 € × 4,33 |
| Gartenpflege | 13,50 € je Einsatz + Rasen 0,14 €/m²/Mahd, Beet 0,45 €/m², Hecke 1,78 €/m, Laub 0,05 €/m², Grünschnitt 0,11 €/m²/Jahr | Jahressumme / 12 (Annahme: 18 Mähgänge, 7 Beetgänge, 2 Heckenschnitte, 3 Laub-Einsätze; Faustregel 0,30–0,40 € je m² Grünfläche und Monat) |
| Winterdienst (Saison Nov–März) | 220 € Grundpauschale je Objekt + 9,50 € je lfd. Meter, inkl. Streugut und Einsatzprotokoll | Saison = 220 € + Meter × 9,50 €; zahlbar in 5 Raten (Nov–März) oder verteilt auf 12 Monate |
| Winterdienst Einzeleinsatz ohne Vertrag | 43,50 € | je Einsatz |
| Sichtkontrolle bei jedem Einsatz | inklusive | 0 € |
| Objektkontrolle mit Fotoprotokoll (eigener Termin) | 27 € | je Begehung |
| Kleinreparaturen / Sonderarbeiten | 53,50 €/h, je angefangene 15 Min. 13,50 €, mindestens 30 Min. (27 €) | nach Aufwand, **immer getrennt von der Pauschale** (meist nicht auf Mieter umlegbar) |
| Anfahrt (Einzelaufträge) | Gütersloh bis 10 km 14,50 €, Umland 10–25 km 36,50 € | je Fahrt |
| USt. | 19 % | Netto × 0,19 |

Die Beispielpreise sind Richtwerte. Den Festpreis legt der Inhaber nach der kostenlosen Besichtigung fest.

## 3. Beispielrechnung: Mehrfamilienhaus (6 WE), 1 Treppenhaus mit 3 Etagen, wöchentliche Reinigung, alle Bausteine

Objektdaten wie in `preiskalkulation.md` (Beispiel „MFH 6 WE“): 25 m Gehweg, 150 m² Rasen, 20 m² Beete,
15 m Hecke, 6 Abfuhrtermine und 9 Leerungen pro Monat, 1 Objektkontrolle mit Fotoprotokoll pro Monat.

| Position | Rechnung | Monat netto |
|---|---|---|
| Treppenhausreinigung wöchentlich | (12 € + 3 × 8 €) × 52/12 | 156,00 € |
| Mülltonnen-Service inkl. Müllplatz | 6 × 6,50 € + 9 × 1,34 € + 4,45 € × 52/12 | 70,34 € |
| Gartenpflege | 822,10 € Jahrespreis / 12 | 68,51 € |
| Objektkontrolle mit Fotoprotokoll | 1 × 27 € | 27,00 € |
| **Monatspauschale ganzjährig netto** | | **321,85 €** |

**Winterdienst (eigener Saisonvertrag)**
| Position | Rechnung | Betrag netto |
|---|---|---|
| Saisonpreis 01.11.–31.03. | 220 € + 25 m × 9,50 € | 457,50 € |
| als 5 Monatsraten (Nov–März) | 457,50 € / 5 | 91,50 € / Monat |
| alternativ verteilt auf 12 Monate | 457,50 € / 12 | 38,13 € / Monat |

**Alles zusammen, Winterdienst auf 12 Monate verteilt**
| | Betrag |
|---|---|
| Gesamt pro Monat netto | **359,98 €** (rund 360 €) |
| zzgl. 19 % USt. | 68,40 € |
| Gesamt pro Monat brutto | **428,37 €** |
| Jahreswert netto | 4.319,72 € |

### Varianten desselben Objekts
| Variante | Monat netto | Monat brutto (19 %) |
|---|---|---|
| Nur Treppenhaus wöchentlich + Mülltonnen (typisches Einstiegspaket) | 226,34 € | 269,35 € |
| Treppenhaus **14-täglich**: (12 € + 3 × 8 €) × 1,15 × 26/12 = 89,70 € | 89,70 € | 106,74 € |
| Kleinreparatur 45 Min. in Gütersloh: 3 × 13,50 € + 14,50 € Anfahrt (einmalig) | 55,00 € | 65,45 € |

### Weitere Richtwerte aus der Preiskalkulation (Monat netto, alle Bausteine, Winterdienst verteilt)
| Objekt | Empfehlung netto |
|---|---|
| Wohnanlage 12 WE (1 Treppenhaus × 4 Etagen, 45 m Gehweg) | ca. 471 € |
| Anlage 24 WE (2 Treppenhäuser × 4 Etagen, 90 m Gehweg) | ca. 799 € |

## 4. Hinweise für den Inhaber
- **Festpreis nach Kostenarten:** Im Angebot die Positionen getrennt nach Gebäudereinigung, Gartenpflege,
  Hauswart/Objektkontrolle, Müll und Winterdienst ausweisen. So übernimmt die Verwaltung sie direkt in die
  Betriebskostenabrechnung.
- **Kleinreparaturen** nie in die Pauschale packen, sondern nach Aufwand getrennt abrechnen.
- **Mülltonnen:** Der Preis setzt voraus, dass ein Weg (raus oder rein) mit einem anderen Termin am Objekt
  zusammenfällt. Sonst nach der Besichtigung anpassen.
- **Winterdienst:** Der Preis rechnet mit rund 20 Einsätzen pro Saison. Nur so viele Objekte annehmen, wie
  vor der Räumzeit zu schaffen sind.
- **Rabatte:** Kein Treue- oder Mengenrabatt. Ein Einführungsangebot ist nicht freigegeben und wird nicht verwendet.
- **Kleinunternehmerregelung (§ 19 UStG):** mit dem Steuerberater klären [OFFEN]. Bis dahin gilt: netto zzgl. 19 % MwSt.
