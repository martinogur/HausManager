# Bericht akquise-texter – 24.11.2026 (erster Lauf)

## Was wurde gemacht
- `CLAUDE.md`, `firma/profil.md`, `leads/leads.csv` und `berichte/2026-11-24-lead-finder.md` gelesen. Die Empfehlungen des Lead-Finders habe ich umgesetzt:
  - Bauverein (L001): Aushilfe bei Spitzen und Pilotobjekt
  - große Verwaltungen (L002, L003, L004, L006): Rahmenvereinbarung, Kontrollprotokoll, Reaktion binnen 24 h
  - inhabergeführte Verwaltungen (L005, L007, L008, L009, L010, L015): von Inhaber zu Inhaber
  - Lüke (L008): Anknüpfung an die Aussage auf der Webseite zu externen Dienstleistern
  - Golücke (L005) und Santak (L009): Bewertungen werden nirgends erwähnt, alles positiv formuliert
  - Kooperation bzw. Nachunternehmer bei E+S (L018) und BGW (L020), Neubau-Signal bei Sennestadt GmbH (L021)
- Bearbeitet wurden **alle 21 Leads** (`status = neu`), in der Reihenfolge A (9), B (7), C (5).
- In `leads/leads.csv` steht bei allen 21 jetzt `status = entwurf_fertig`, und `naechster_schritt` ist pro Lead konkret ausgefüllt.
- Nichts ist verschickt worden, und nichts ist committet.

## Entwürfe zur Freigabe

| Art | Anzahl | Ablage |
|---|---|---|
| Persönliche Briefe (je mit LinkedIn-Text ≤ 300 Zeichen und Nachfassplan) | 21 | `akquise/briefe/L001-…md` bis `L021-…md` |
| E-Mail-Vorlagen (je Fassung A „nach Telefonat“ und Fassung B „nach Antwort auf Brief“, Kopf mit an, voraussetzung und status) | 21 Dateien, 42 Fassungen | `akquise/emails/L001-…md` bis `L021-…md` |
| Telefonleitfaden (Einstieg in 15 s, Bedarfsfragen, Einwände, Terminabschluss, Einwilligung zur E-Mail mit Dokumentation) | 1 | `akquise/telefonleitfaden.md` |
| Anrufliste (21 Leads, A zuerst, mit Telefon, Ansprechpartner, Aufhänger, Spalten für Ergebnis und Einwilligung) | 1 | `akquise/anrufliste.md` |
| Nachfass-Serie (Postkarten Winter, Laub/Frühjahr, Eigentümerversammlung, Saisonbrief Tag 30) | 1 | `akquise/nachfass-serie.md` |

Briefe: L001 Bauverein · L002 SKW · L003 immoEINS · L004 LH · L005 Golücke · L006 HVG Oesterhelweg · L007 Stephan · L008 Lüke · L009 Santak · L010 Dari · L011 Müller · L012 Rasspe · L013 Buske · L014 Haus & Grund Bielefeld · L015 Wackermann · L016 LMK · L017 HVG Rheda · L018 E+S · L019 Knoop · L020 BGW · L021 Sennestadt GmbH.

Bei L009, L010, L011, L017 und L018 (Kanal laut Leadliste: Anruf) gibt es im Brief zwei Varianten für den ersten Satz: „nach Telefonat“ und „niemand erreicht“.

## Rechtliches
- Keine Kalt-E-Mails. Jede E-Mail-Vorlage nennt ihre Voraussetzung: dokumentierte Einwilligung im Telefonat oder eine Antwort des Kontakts. Sie enthält außerdem einen Hinweis, wie man weitere E-Mails abbestellt.
- Der Telefonleitfaden enthält die Frage nach der Einwilligung zur E-Mail und sagt, was dazu notiert werden muss (Datum, Uhrzeit, Name, Adresse, Zweck).
- Verwendet wurden nur Fakten aus `firma/profil.md`: Leistungen, Preise ab 8 € / 30 € / 35 € / 5 €, 10 % Treuerabatt, Reaktion binnen 24 h, Erreichbarkeit Mo–Sa 7–20 Uhr, Kontrollprotokoll inklusive, Besichtigung kostenlos. Es gibt keine Referenzen, Objektzahlen oder Zertifikate. Gründungsjahre, die nur aus Verzeichnissen stammen (HVG 1971, Müller 1955), habe ich in den Briefen weggelassen.

## Heutige Anrufliste (Top 5 nach Priorität)
| # | Lead | Telefon | Ansprechpartner | Wann | Aufhänger |
|---|---|---|---|---|---|
| 1 | L009 Hausverwaltung Santak | 05242 404641 | erfragen | heute | Objekte in Rheda, GT und Rietberg liegen in unserem Gebiet, Kontrollprotokoll und Reaktion binnen 24 h |
| 2 | L001 Bauverein Gütersloh | 05241 9037-0 | Jörg Höfel / Zuständige Person Bewirtschaftung | Tag 7 nach Brief | Spitzen bei Schnee, Laub und Grünpflege abfangen, Start mit einem Pilotobjekt |
| 3 | L002 SKW Hausverwaltung | 05241 5046250 | Katja Döring, Ansgar Stahl | Tag 7 nach Brief | Rahmenvereinbarung für Objekte im ganzen Kreis GT |
| 4 | L003 immoEINS Gütersloh | 05241 23488-0 | erfragen | Tag 7 nach Brief | Kontrollprotokoll als Unterlage für Beirat und Eigentümer bei großen WEGs |
| 5 | L006 HVG Oesterhelweg | 05241 5352-0 | Peter Oesterhelweg | Tag 7 nach Brief | ein Partner aus einer Hand für WEG, Miete und Gewerbe |

**Heute ohne vorherigen Brief anrufbar:** L009 Santak (05242 404641), L010 Dari (05241 6014999), L011 Müller (0170 5521638 / 05241 35507), L017 HVG Rheda (05242 57248), L018 E+S (05247 9256-250, nur nach Okay zur Kooperation).

## Vor dem Versand ergänzen (in allen Briefen markiert)
- `[OFFEN: PLZ]` bei allen Empfängeradressen, da die Leadliste keine PLZ enthält
- `[OFFEN: Rechtsform / Pflichtangaben im Briefkopf]` und in der E-Mail-Signatur
- `[OFFEN: netto/brutto]` überall, wo Preise genannt werden
- Ansprechpartner fehlen bei L003, L009, L013, L014, L016, L017, L019 und L020. Briefe dort an „Geschäftsführung“ bzw. eine Abteilung adressiert
- E-Mail-Adresse fehlt bei L011, L014, L017, L018 und L019. Nur im Telefonat und nur mit Einwilligung erfragen

## Fragen an den Inhaber
1. **Netto oder brutto?** Gilt die Kleinunternehmerregelung? Davon hängen alle Preisangaben ab.
2. **Rechtsform und Pflichtangaben** für Briefkopf und E-Mail-Signatur?
3. **Pilotobjekt / Probephase:** Darf ich dem Bauverein (und anderen) ein „Pilotobjekt“ anbieten? Zu welchen Bedingungen (normaler Preis, Laufzeit, Kündigung)?
4. **Kapazität:** Können Sie große Anlagen übernehmen (Bauverein, immoEINS bis 500 Einheiten), und wie viele neue Objekte gehen diesen Winter noch?
5. **Umkreis:** Gehören Bielefeld-Süd (L014, L020, L021), Bielefeld-Mitte (L019), Herzebrock-Clarholz (L013) und Oelde (Objekte von L009) dazu?
6. **Kooperation** mit E+S (L018) und als Nachunternehmer für BGW (L020) gewünscht?
7. **Winterdienst:** Einsatzzeiten (früh morgens, Sonn- und Feiertage)? Gibt es ein Streuprotokoll? Das wäre ein starkes Argument zur Haftung, wird aber erst nach Bestätigung erwähnt.
8. **Betriebshaftpflicht** vorhanden? Wird von großen Verwaltungen und der BGW sicher gefragt.
9. **Dauer einer Besichtigung** (für den Terminabschluss im Leitfaden)?
10. **Muster-Kontrollprotokoll:** Gibt es eine Vorlage, die ich bei Terminen zeigen kann? Sonst `angebots-profi` beauftragen.
11. **LinkedIn:** Gibt es ein Profil von Ihnen bzw. der Firma? Sonst entfallen die LinkedIn-Texte vorerst.
12. **Echte Referenzen** (mit Erlaubnis) würden die Briefe deutlich stärken. Gibt es welche?

## Nächste Schritte
- Inhaber: Briefe freigeben, `[OFFEN]`-Stellen füllen, drucken, versenden und dann in `leads/leads.csv` `status = angeschrieben` mit Versanddatum setzen.
- Heute Block 1 der Anrufliste (L009, L010, L011, L017, ggf. L018).
- Eine Woche nach Versand: Tag-7-Anrufe in der Reihenfolge der Anrufliste.
- Nach den ersten 10 Anrufen: Telefonleitfaden anhand der echten Einwände verbessern.
