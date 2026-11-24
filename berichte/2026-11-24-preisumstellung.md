# Preisumstellung auf die neue Preisliste – 24.11.2026 (akquise-texter)

## Was wurde gemacht
Alle Angebots- und Akquisetexte auf die freigegebene Preisliste vom 24.11.2026 umgestellt
(`firma/profil.md`, Abschnitt „Preise“, und `akquise/angebote/preiskalkulation.md`):
- Alle Preise **netto zzgl. 19 % MwSt.**, Platzhalter `[OFFEN: netto/brutto]` entfernt.
- Abrechnung nach Aufwand (Treppenhaus/Etage, lfd. Meter Gehweg, m² Grünfläche, Abfuhrtermin), nicht pro Wohneinheit.
- Treuerabatt gestrichen. Wöchentlich = Normalpreis, 14-täglich + 15 % je Reinigung.
- Winterdienst: 220 € je Saison + 9,50 € je Meter, inkl. Streugut und Einsatzprotokoll. Saison Nov.–März.
- Kleinreparaturen 53,50 €/h (15-Minuten-Takt, mindestens 30 Min.), Anfahrt 14,50 € / 36,50 €.
- Das „Startpaket“ wurde **nicht** verwendet.
- `preiskalkulation.md` und `preiskalkulation.xlsx` sind unverändert.

## Geänderte Dateien
**Angebote**
- `akquise/angebote/leistungsverzeichnisse.md`
- `akquise/angebote/preisrechner.md`: neu aufgebaut, Beispiel MFH 6 WE ≈ 360 € netto/Monat wie in der Kalkulation
- `akquise/angebote/preisrechner.csv`: neu aufgebaut, mit neuen Eingaben, Sätzen und Formeln
- `akquise/angebote/upsell-liste.md`
- `akquise/angebote/vorlagen/01-objektbetreuung-rahmenvertrag.md`
- `akquise/angebote/vorlagen/02-winterdienst-saisonvertrag.md`
- `akquise/angebote/vorlagen/03-gartenpflege-jahresvertrag.md`
- `akquise/angebote/vorlagen/04-treppenhausreinigung.md`
- `akquise/angebote/vorlagen/05-einzelauftrag.md`

**Akquise und WhatsApp**
- `akquise/briefe/L002-skw-hausverwaltung.md`, `L006-hvg-oesterhelweg.md`, `L008-hvw-lueke.md`,
  `L011-mueller-immobilien.md`, `L012-rasspe-verwaltung.md`, `L016-lmk-immobilien.md`
- `akquise/emails/L012-rasspe-verwaltung.md`
- `akquise/nachfass-serie.md`
- `akquise/telefonleitfaden.md`: Einwand „zu teuer“. Die Datei stand nicht in der Liste, enthielt aber noch 8 €/Einheit und den Treuerabatt.
- `marketing/whatsapp/automatische-nachrichten.md`: `/preis` und `/winter` mit den neuen Beispielpreisen, `/angebot` und `/objekt` fragen jetzt nach Treppenhäusern, Etagen, Metern und m² statt nach Wohneinheiten.

## Prüfung (grep)
In den Dateien oben kommen diese Muster nicht mehr vor: „8 €/Einheit“, „30 €/Einheit“, „5 €/Einheit“, „35 €“, „Treuerabatt“,
„pro Einheit“, „OFFEN: netto/brutto“, „Startpaket“.
Diese Muster stehen nur noch in folgenden Dateien:
- `akquise/angebote/preiskalkulation.md` (darf nicht geändert werden, dort als Vergleich zu den alten Webseitenpreisen)
- `akquise/angebote/preiskalkulation_erzeugen.py` (erzeugt die .xlsx, deshalb nicht angefasst)
- außerhalb des Auftrags: `marketing/seo/google-profil.md` (Leistungstabelle und FAQ mit 8 €/Einheit, 30 €, 35 €/h, 5 €)
  sowie ältere Berichte in `berichte/`.

## Braucht Freigabe
Alle geänderten Texte sind Entwürfe. Bitte vor dem Versand prüfen, vor allem die Briefe L002, L006, L008, L011, L012 und L016.

## Fragen an den Inhaber
1. **Gebäudekontrolle „kostenlos mit Protokoll“:** Laut Preisliste ist nur die Sichtkontrolle bei jedem Einsatz inklusive.
   Die Objektkontrolle mit Fotoprotokoll kostet 27 €. In den Angebotsvorlagen und den Nachfass-Texten habe ich das angepasst.
   In fast allen Briefen und E-Mails (L001–L021) steht aber noch „Gebäudekontrolle mit Protokoll, bei jedem Einsatz kostenlos“.
   Auch im Profil steht unter „Leistungen“ noch „kostenlos inklusive“. Welche Aussage gilt? Danach passe ich alle Briefe einheitlich an.
2. **Winterdienst-Saison:** Okt.–März (Profil, Leistungen) oder Nov.–März (Preisliste)? In den Vorlagen steht jetzt Nov.–März.
3. **Abschluss während der Saison:** Vorlage 02 sagt „Preis anteilig für die verbleibenden Monate“. Gilt das allgemein?
   (In der Kalkulation steht es nur beim nicht freigegebenen Startpaket.)
4. **Google-Profil** (`marketing/seo/google-profil.md`) hat noch die alten Preise. Soll `seo-reichweite` das umstellen?
5. Kleinunternehmerregelung (§ 19 UStG) weiter [OFFEN], mit dem Steuerberater klären.

Nichts committet.
