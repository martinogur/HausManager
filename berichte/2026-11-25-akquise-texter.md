# Bericht akquise-texter – 25.11.2026 (Teil 2)

## Was wurde gemacht
- Gelesen wurden `CLAUDE.md`, `firma/profil.md` (Preise netto, freigegeben am 24.11.), `leads/leads.csv`, `leads/adressen.csv` und `berichte/2026-11-25-lead-finder.md`. Als Vorlage für Aufbau und Ton dienten die Briefe L002 und L021.
- Alle **16 neuen Leads L022–L037** sind bearbeitet (3× A, 10× B, 3× C). Die Empfehlungen des Lead-Finders sind umgesetzt:
  - KHW (L022): Pilotobjekt Winterdienst/Grünpflege in Gütersloh oder Verl. Dazu ein eigener Text für das Formular „Partner werden“, der erst nach Freigabe genutzt wird.
  - KWG (L023) und gbb (L024): Angebot nur als **Ergänzung** zu den eigenen Hausmeistern, also Winterdienst-Spitzen, Urlaubs- und Krankheitsvertretung, Grünpflege-Spitzen.
  - AVENIA (L026): Partner für die Bewirtschaftung ab Fertigstellung, einschließlich Tiefgaragen-Zufahrt, mitwachsend mit jedem Bauabschnitt. Nachfass schon an Tag 5.
  - Junkerkalefeld (L028): Der Brief geht direkt auf die genannte Leistung „Vertragsabschlüsse und -pflege mit Hausmeistern“ ein.
  - Böcker (L027) und EPKE (L033): Aufnahme in den Anbieterkreis bzw. Vergleichsangebot bei der nächsten Vertragsprüfung.
  - HEUTE (L035) und compassio (L036): sichere Wege, Winterdienst mit Einsatzprotokoll (Haftung), Außenanlagen. Bei L036 wird laut Leadliste **zuerst angerufen**, um die Zuständigkeit zu klären.
  - Oelde-Paket (L025, L028, L029): Die drei Briefe sollen zusammen rausgehen, die Termine nach Möglichkeit an einem Tag stattfinden.
- Keine Wettbewerber angeschrieben (GSWG/OWIS und Freie Scholle hatte der Lead-Finder schon aussortiert).
- In `leads/leads.csv` steht bei L022–L037 jetzt `status = entwurf_fertig`, und `naechster_schritt` ist pro Lead konkret ausgefüllt.
- In `akquise/anrufliste.md` sind die Einträge Nr. 22–37 ergänzt (A zuerst). Die bestehenden Einträge sind unverändert, „Heute möglich“ wurde um L036 erweitert.
- Nichts ist verschickt worden, und nichts ist committet.

## Entwürfe zur Freigabe

| Art | Anzahl | Ablage |
|---|---|---|
| Persönliche Briefe (je mit LinkedIn-Text ≤ 300 Zeichen und Nachfassplan) | 16 | `akquise/briefe/L022-…md` bis `L037-…md` |
| E-Mail-Vorlagen (je Fassung A „nach Telefonat“ und Fassung B „nach Antwort auf Brief“, Kopf mit an, voraussetzung und status) | 16 Dateien, 32 Fassungen | `akquise/emails/L022-…md` bis `L037-…md` |
| Formulartext „Partner werden“ (KHW) | 1 | in `akquise/briefe/L022-khw-wohnen.md` |
| Anrufliste ergänzt | 16 Einträge | `akquise/anrufliste.md` |

Briefe: L022 KHW · L023 KWG Halle · L024 gbb Brackwede · L025 Bauverein Oelde · L026 AVENIA Quartier · L027 Böcker · L028 Junkerkalefeld · L029 Nahrmann · L030 Kuhlmann · L031 Borsig · L032 Manss · L033 EPKE & KOLLEGEN · L034 Mario Kramer · L035 HEUTE GmbH · L036 compassio Verl · L037 KF Hausverwaltung.

## Druckfertig (PDF)
- **Die PDFs sind noch nicht erzeugt.** In dieser Sitzung stand mir keine Shell zur Verfügung. Bitte ausführen:
  `python3 akquise/brief_pdf.py L022 L023 L024 L025 L026 L027 L028 L029 L030 L031 L032 L033 L034 L035 L036 L037`
- Vorbeugend sind alle Briefe kürzer als die bereits geprüften Briefe vom 24.11. gehalten: 4 Stichpunkte, keine langen Preisaufzählungen.
- Im Brieftext gibt es keine offenen Platzhalter. Vorhanden ist nur „[Datum bei Versand]“, und das ersetzt das Skript. Der Absenderblock ist ohne Platzhalter (Einzelunternehmen, Name und Anschrift). Alle Empfängeradressen haben eine PLZ aus `leads/adressen.csv`.
- Meldet das Skript „ZU LANG“, zuerst den P.S.-Zusatz „Preisrechner: …“ oder den Beispielpreis im vierten Stichpunkt streichen.

## Fällige Nachfassaktionen
- Keine. Kein Lead hat den Status `angeschrieben` oder `angerufen`, es wurde also noch nichts versendet.

## Heutige Anrufliste (Top 5, ohne vorherigen Brief möglich)
| # | Lead | Telefon | Aufhänger |
|---|---|---|---|
| 1 | L009 Hausverwaltung Santak, Rheda-Wiedenbrück | 05242 404641 | Objekte in Rheda, GT und Rietberg liegen in unserem Gebiet, Kontrollprotokoll und Reaktion binnen 24 h (Bewertungen nicht ansprechen) |
| 2 | L010 Dari Immobilien, Gütersloh | 05241 6014999 | Notfalldienst bis 20 Uhr bei Ihnen, Erreichbarkeit bis 20 Uhr bei uns: von Inhaber zu Inhaber |
| 3 | L011 Müller Immobilien, Gütersloh | 0170 5521638 / 05241 35507 | Reinigung, Winterdienst, Garten und Tonnen für Ihre Häuser mit einem festen Ansprechpartner |
| 4 | L036 compassio Seniorenresidenz Verl (neu) | 05246 9060-200 | Wer ist für Winterdienst und Außenanlagen zuständig, Sie vor Ort oder die Zentrale? (Namen notieren, dann Brief anpassen) |
| 5 | L017 HVG Verwaltungsgesellschaft, Rheda-Wiedenbrück | 05242 57248 | Kurz klären, ob es Objekte gibt, für die ein zuverlässiger Hausmeister aus der Region gebraucht wird |

Ersatz bzw. danach: L018 E+S Harsewinkel (05247 9256-250), aber nur, wenn der Inhaber Kooperationen will. Wichtigster neuer Lead nach dem Versand: **L026 AVENIA (0171 2200299), Anruf an Tag 5.**

## Fragen an den Inhaber
1. **Einsatzgebiet:** Gehören Oelde (L025, L028, L029, ca. 23 km), Halle (Westf.) mit Werther, Borgholzhausen und Versmold (L023, L030) sowie Bielefeld-Senne/Brackwede (L024, L033, L034) dazu? Der Umkreis ist im Profil noch `[OFFEN]`. Fällt ein Ort heraus, werden die betreffenden Briefe nicht verschickt.
2. **KHW-Formular „Partner werden“:** Darf der Text aus der Brief-Datei L022 nach Freigabe dort eingetragen werden?
3. **Kontrolle/Protokoll:** Das Profil sagt einmal „Gebäudekontrolle mit Protokoll kostenlos bei jeder Leistung“ und bei den Preisen „Sichtkontrolle bei jedem Einsatz inklusive, Objektkontrolle mit Fotoprotokoll 27 €“. In den neuen Briefen steht deshalb nur „Gebäudekontrolle bei jedem Einsatz inklusive, Auffälligkeiten melde ich direkt“ und kein kostenloses Protokoll. Ein Protokoll wird nur beim Winterdienst (Einsatzprotokoll, im Preis enthalten) versprochen. Bitte festlegen, was gilt. Die Briefe L001–L021 versprechen noch „Kontrolle mit Protokoll kostenlos“.
4. **Delbrück (L035):** Der Standort liegt im Kreis Paderborn und wird im Brief bewusst nicht genannt. Soll er mit angeboten werden?
5. **Alte Briefe L001–L021:** Der Bericht vom 24.11. nennt noch alte Preise und 10 % Treuerabatt. Es lohnt sich zu prüfen, ob in den alten Briefen und E-Mails noch Preise oder Rabatte stehen, die nicht mehr freigegeben sind. L002 enthält bereits die neuen Preise.
6. **E-Mail-Signatur:** In den neuen E-Mail-Vorlagen steht die Signatur mit vollem Namen und Anschrift (Einzelunternehmen, laut Profil ausreichend). Gibt es eine USt-IdNr., die ergänzt werden soll?
