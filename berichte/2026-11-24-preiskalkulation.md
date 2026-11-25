# Bericht Preiskalkulation – 24.11.2026

## Was wurde gemacht
- **Marktrecherche** für Gütersloh/OWL und bundesweit: Stundensätze, Treppenhaus, Winterdienst, Garten, Mülltonnen,
  Kontrolle, Anfahrt sowie Mindestlöhne 2026. Jede Zahl ist mit Quelle und Datum erfasst und als regional oder
  bundesweit gekennzeichnet. Regionale Preise gibt es kaum. Gefunden wurden die Hausmeisterei Jäger (Gütersloh),
  JovanoV, wertvoll-gartenservice und Krüger (Winterdienst-Seite für Gütersloh). Alles andere ist bundesweit.
  Für Winterdienst je laufendem Meter und für Garten je m² gibt es keine regionale Quelle.
- **`akquise/angebote/preiskalkulation.xlsx`** mit 5 Blättern:
  - Annahmen: gelbe Eingabefelder mit Begründung.
  - Stundensatz, Einheitspreise und Beispielobjekte: nur Formeln (377 Formeln).
  - Marktvergleich: mit URLs.
  Erstellt mit openpyxl und mit LibreOffice neu berechnet, ohne Formelfehler. Die Kernwerte sind per Python gegengerechnet.
- **`akquise/angebote/preiskalkulation.md`**: Zusammenfassung für den Inhaber mit Preisliste netto/brutto,
  Beispielrechnungen, Einführungsangebot, Hinweisen zu § 19 UStG und zur Haftung im Winterdienst, offenen Fragen und Quellen.

## Ergebnis in Kürze
- Selbstkosten des Inhabers: **49,35 €/h**. Empfohlener Stundensatz: **53,50 € netto**. Die Webseite nennt 35 €/h,
  damit bleiben vor Steuer nur ca. 1.440 €/Monat.
- Das Preismodell pro Wohneinheit passt nicht. Winterdienst (2,7- bis 4,6-mal), Garten (2,6- bis 3,6-mal) und
  Treppenhaus bei großen Objekten (2-mal) sind zu hoch. Mülltonnen bei kleinen Objekten und Kleinreparaturen sind zu niedrig.
- Beispiele, Monat netto, Webseite / Empfehlung / Markt:
  - 6 WE: 501 / 360 / 206–617 €
  - 12 WE: 1.002 / 471 / 280–782 €
  - 24 WE: 2.005 / 799 / 515–1.370 €

## Braucht Freigabe
- Neue Preisliste und neues Preismodell (Treppenhaus/Etage/lfm/m² intern, Festpreis pro Objekt nach außen).
- Einführungsangebot „Startpaket für die ersten 5 Objekte“.
- Jede Änderung der Webseitenpreise. Sie geht nur nach „Webseite freigeben“ über den `webseiten-bauer`.

## Fragen an den Inhaber
1. Sind die Webseitenpreise netto oder brutto? Gilt § 19 UStG? Bitte mit dem Steuerberater klären.
2. Welches Unternehmerlohn-Ziel? Wie hoch sind die echten Kosten für KV, Fahrzeug, Haftpflicht (Winterdienst eingeschlossen?) und Geräte?
3. Bitte die Zeitansätze vor Ort stoppen: Minuten je Etage, Rasen-m² pro Stunde, Minuten je Gehwegmeter.
4. Kommt ein Minijobber in Frage?
5. Winterdienst-Saison Okt–März oder Nov–März? Welche Räumzeiten gelten laut Satzung in Gütersloh?
6. Wohin geht der Grünschnitt, und was kostet die Entsorgung?

Nicht committet.
