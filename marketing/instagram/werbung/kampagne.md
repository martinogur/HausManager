# Instagram-Werbekampagne (Meta-Anzeigen) – Hausmeister Helden

> Entwurf vom 24.11.2026 (`instagram-manager`). **Nichts davon ist live.** Die Kampagne legt der Inhaber selbst im
> Meta-Werbeanzeigenmanager an und zahlt sie selbst. Alle Texte und Grafiken brauchen seine Freigabe.
> Keine Preise (noch nicht freigegeben), keine Zahlen, keine Bewertungen und keine Kundenstimmen in den Anzeigen.
> Meta kennzeichnet jede Anzeige automatisch als „Gesponsert“. Damit ist sie als Werbung erkennbar.

## 1. Auf einen Blick

| Punkt | Vorschlag |
|---|---|
| Ziel | Anfragen per **WhatsApp** (05241 3389748). Plan B: Klicks auf die Webseite |
| Kampagnenziel im Werbeanzeigenmanager | **Interaktion** → Conversion-Ort **Messaging-Apps → WhatsApp** → Leistungsziel „Anzahl der Unterhaltungen maximieren“ |
| Gebiet | Gütersloh + ca. 25 km Radius |
| Alter | 30–65+ (Meta bietet als Obergrenze nur „65+“ an, nicht genau 70) |
| Anzeigen | 3 Varianten als A/B/C-Test: **A** Winterdienst, **B** Ein Ansprechpartner, **C** Kostenlose Besichtigung |
| Test | 14 Tage, 9 €/Tag (3 × 3 €), insgesamt ca. 126 €. Sparvariante: 5 €/Tag = 70 € |
| Wichtigste Kennzahl | **Kosten pro begonnener Unterhaltung** und wie viele davon echte Anfragen sind |
| Grafiken | `marketing/instagram/werbung/grafiken/anzeigen/` (Feed 1080×1350, Story 1080×1920, Reel-Video 9 Sek.) |

**Ansprache in den Anzeigen: „Sie“.** Die Anzeigen richten sich vor allem an Vermieter und Hausverwaltungen, und die Vorgabe
lautete „Ihr Objekt“. Die normalen Posts bleiben beim „du“. `[OFFEN: Inhaber entscheidet, ob die Anzeigen auch auf „du“ umgestellt werden sollen.]`

## 2. Voraussetzungen (einmalig, bevor es losgeht)

1. **Instagram ist ein Business-Konto** (oder Creator-Konto). Mit einem privaten Konto kann man keine Anzeigen schalten.
2. **Es gibt eine Facebook-Seite „Hausmeister Helden“, und Instagram ist mit ihr verbunden.** Der Werbeanzeigenmanager
   arbeitet immer über die Facebook-Seite. Ein Instagram-Konto ohne verbundene Seite lässt sich dort nicht als Absender auswählen.
3. **WhatsApp Business** läuft auf dem Handy mit der Nummer 05241 3389748 und ist **mit der Facebook-Seite verknüpft**.
   Erst dann taucht WhatsApp als Ziel in der Anzeige auf.
   `[OFFEN: Die Nummer ist ein Festnetzanschluss. Bitte prüfen, ob WhatsApp Business darauf eingerichtet ist (Bestätigung per Anruf) und ob die Verknüpfung mit der Seite klappt. Wenn nicht: Plan B, Abschnitt 6.]`
4. **Werbekonto mit Zahlungsmethode** (Kreditkarte, PayPal o. Ä.) im Werbeanzeigenmanager.
5. **Angaben zu Begünstigtem und Zahler:** Für Anzeigen in der EU fragt Meta, wer von der Anzeige profitiert und wer sie bezahlt.
   Beides ist „Hausmeister Helden“ bzw. der Inhaber. Diese Angabe ist öffentlich in der Werbebibliothek sichtbar.
6. **Profil ist fertig** (siehe `marketing/instagram/profil.md`, „In 15 Minuten einrichten“) und hat **mindestens 3–6 Beiträge**.
   Wer auf die Anzeige tippt, schaut sich oft zuerst das Profil an. Ein leeres Profil kostet Anfragen.
7. Antworten auf WhatsApp-Anfragen innerhalb von 24 Stunden. Das wird in jeder Anzeige versprochen.
   Die Begrüßungs- und Abwesenheitsnachricht aus `marketing/whatsapp/` sollte vorher aktiv sein.

## 3. Zielgruppe (Vorschlag, die Auswahl trifft der Inhaber)

- **Standort:** Gütersloh, Radius **25 km** (deckt Rheda-Wiedenbrück, Verl, Harsewinkel, Herzebrock-Clarholz, Steinhagen,
  Schloß Holte-Stukenbrock und Teile von Bielefeld ab). Option „Personen, die an diesem Ort wohnen oder sich kürzlich dort aufgehalten haben“ ist in Ordnung.
  `[OFFEN: Einsatzradius in firma/profil.md ist noch nicht bestätigt. 25 km ist der Vorschlag.]`
- **Alter:** 30 bis 65+.
- **Sprache:** Deutsch.
- **Interessen (nur Vorschläge, im Werbeanzeigenmanager aus der Liste wählen, was angeboten wird):**
  Immobilien, Vermietung, Hausverwaltung, Wohneigentum, Eigentümergemeinschaft, Immobilieninvestition, Facility Management.
  Nicht jeder Begriff existiert in Metas Liste. Was fehlt, einfach weglassen.
- **Tipp:** Die Zielgruppe nicht zu eng machen. Meta findet passende Personen oft selbst besser, wenn das Gebiet stimmt.
  Wenn Meta „Advantage+ Zielgruppe“ anbietet, gelten Alter und Interessen nur als Vorschlag. Wer die Altersgrenze hart setzen will,
  wählt „Ursprüngliche Zielgruppenoptionen verwenden“.
- **Sonderkategorie „Wohnen“:** Unsere Anzeigen bieten keine Wohnungen, Kredite oder Versicherungen an. Daher zunächst **keine**
  Sonderkategorie auswählen. Falls Meta die Anzeige trotzdem als „Wohnen“ einstuft (Kategorie umfasst laut Meta-Hilfe u. a. „Reparaturen am Wohnraum“),
  die Kategorie nachträglich setzen. Dann sind Alter und manche Interessen nicht mehr frei wählbar, der Radius muss mindestens 15 km sein.
  Für unseren 25-km-Radius ist das kein Problem.

## 4. Die drei Anzeigen

Jede Anzeige hat ein Feed-Bild (1080×1350), ein Story-Bild (1080×1920, mit Rand für die Instagram-Bedienelemente)
und optional ein 9-Sekunden-Text-Video für die Reels-Platzierung. Grafiken neu erzeugen:
```
python3 marketing/instagram/grafik.py marketing/instagram/werbung/anzeigen.json
```

### Anzeige A – Winterdienst-Saison

| Feld | Text |
|---|---|
| Feed-Bild | `marketing/instagram/werbung/grafiken/anzeigen/A-winterdienst-feed/folie-01.png` |
| Story-Bild | `marketing/instagram/werbung/grafiken/anzeigen/A-winterdienst-story/folie-01.png` |
| Reel-Video (optional) | `marketing/instagram/werbung/grafiken/anzeigen/A-winterdienst-reel/reel.mp4` |
| Überschrift | Winterdienst in Gütersloh |
| Beschreibung | Besichtigung kostenlos |
| Button (CTA) | **WhatsApp-Nachricht senden** |
| Vorausgefüllte Nachricht | Hallo, ich interessiere mich für den Winterdienst. (Anzeige A) |

**Primärtext:**
```
Glätte vor dem Haus? Wir räumen und streuen. ❄️

Hausmeister Helden übernimmt den Winterdienst in Gütersloh und Umgebung – für Vermieter, Hausverwaltungen und Gewerbe.

✅ Gehwege und Hauszugänge
✅ Antwort innerhalb von 24 Stunden
✅ Besichtigung kostenlos, Angebot unverbindlich

Schreiben Sie uns jetzt per WhatsApp – wir melden uns persönlich.
```

### Anzeige B – Ein Ansprechpartner für Ihr Objekt (Vermieter/Verwalter)

| Feld | Text |
|---|---|
| Feed-Bild | `marketing/instagram/werbung/grafiken/anzeigen/B-ansprechpartner-feed/folie-01.png` |
| Story-Bild | `marketing/instagram/werbung/grafiken/anzeigen/B-ansprechpartner-story/folie-01.png` |
| Reel-Video (optional) | `marketing/instagram/werbung/grafiken/anzeigen/B-ansprechpartner-reel/reel.mp4` |
| Überschrift | Ein Ansprechpartner für Ihr Objekt |
| Beschreibung | Hausmeisterservice Gütersloh |
| Button (CTA) | **WhatsApp-Nachricht senden** |
| Vorausgefüllte Nachricht | Hallo, ich suche einen Hausmeisterservice für mein Objekt. (Anzeige B) |

**Primärtext:**
```
Ein Ansprechpartner für Ihr Objekt – statt vieler einzelner Firmen.

Treppenhausreinigung, Winterdienst, Gartenarbeit, Kleinreparaturen und Mülltonnen-Service aus einer Hand. Für Vermieter, Eigentümer und Hausverwaltungen in Gütersloh und Umgebung.

✅ Inhaber persönlich erreichbar, kein Callcenter
✅ Gebäudekontrolle mit Protokoll inklusive
✅ Antwort innerhalb von 24 Stunden

Jetzt unverbindlich per WhatsApp anfragen.
```

### Anzeige C – Kostenlose Besichtigung

| Feld | Text |
|---|---|
| Feed-Bild | `marketing/instagram/werbung/grafiken/anzeigen/C-besichtigung-feed/folie-01.png` |
| Story-Bild | `marketing/instagram/werbung/grafiken/anzeigen/C-besichtigung-story/folie-01.png` |
| Reel-Video (optional) | `marketing/instagram/werbung/grafiken/anzeigen/C-besichtigung-reel/reel.mp4` |
| Überschrift | Kostenlose Besichtigung vor Ort |
| Beschreibung | Angebot unverbindlich |
| Button (CTA) | **WhatsApp-Nachricht senden** |
| Vorausgefüllte Nachricht | Hallo, ich möchte einen kostenlosen Besichtigungstermin. (Anzeige C) |

**Primärtext:**
```
Was braucht Ihr Haus wirklich? Wir sehen es uns kostenlos an.

So einfach geht's:
1️⃣ Kurze Nachricht per WhatsApp
2️⃣ Kostenloser Termin vor Ort in Gütersloh und Umgebung
3️⃣ Klares, unverbindliches Angebot

Treppenhaus, Winterdienst, Garten, Kleinreparaturen, Mülltonnen – Gebäudekontrolle mit Protokoll inklusive.
Mo–Sa von 7 bis 20 Uhr erreichbar.
```

**Warum die Kennung „(Anzeige A/B/C)“?** Sie steht in der vorausgefüllten Nachricht. So sieht der Inhaber in WhatsApp sofort,
welche Anzeige die Anfrage gebracht hat, und kann echte Anfragen pro Variante zählen. Der Kunde kann den Text vor dem Senden ändern.

**Bewusst weggelassen:** Preise, „Einsatzprotokoll“ beim Winterdienst (steht nicht in `firma/profil.md`), Zahlen zu Kunden/Objekten,
Bewertungen, Sterne, Fotos von „unseren Einsätzen“.

## 5. Budget und Test-Plan

### Empfehlung: 9 €/Tag für 14 Tage (ca. 126 €)
- **1 Kampagne**, darin **3 Anzeigengruppen** (A, B, C) mit **je 3 €/Tag** und **je 1 Anzeige**. Gleiches Gebiet, gleiches Alter, gleiche Interessen.
- So bekommt jede Variante gleich viel Geld, und der Vergleich ist fair.
  („Advantage+ Kampagnenbudget“ dafür **ausschalten**, sonst verteilt Meta das Geld selbst und eine Variante bekommt fast alles.)
- **Sparvariante 5 €/Tag (70 €):** 1 Anzeigengruppe mit allen 3 Anzeigen. Meta verteilt dann selbst. Billiger, aber der Vergleich ist weniger sauber.
- **Obergrenze 10 €/Tag (140 €):** gleiche Aufteilung, je ca. 3,30 €.
- Immer ein **Enddatum** setzen (Tag 14), damit nicht versehentlich weiter Geld läuft.

### Wann umschichten?
| Zeitpunkt | Was tun |
|---|---|
| Tag 1–3 | **Nichts ändern.** Meta lernt noch (Lernphase). Jede Änderung startet das Lernen neu. Nur prüfen: Läuft die Anzeige? Kommen WhatsApp-Nachrichten an? |
| Tag 7 | Erste Auswertung (Tabelle unten). Eine Variante **abschalten**, wenn sie nach 7 Tagen **0 Unterhaltungen** hat oder ihre **Kosten pro Unterhaltung mehr als doppelt so hoch** sind wie bei der besten. Ihr Budget auf die beste Variante legen (z. B. 6 € + 3 €). Budget höchstens um ca. 20–30 % auf einmal erhöhen, nicht sprunghaft. |
| Tag 14 | Endauswertung. Gewinner weiterlaufen lassen (z. B. 5–7 €/Tag), Verlierer aus. Gegen den Gewinner eine **neue** Variante testen (anderer Titel oder anderes Bild), nie mehrere Dinge auf einmal ändern. |
| Ab Februar/März | Winterdienst-Variante (A) zum Saisonende auslaufen lassen. Im Frühjahr Variante „Garten & Außenanlagen“ als Ersatz testen. |

**Wichtig:** Bei 3 €/Tag pro Variante sind die Zahlen klein. Ein Unterschied von 1–2 Nachrichten ist Zufall.
Entscheidend ist am Ende, **welche Variante echte Anfragen mit Objekt und Ort bringt**, nicht nur Klicks.

### Welche Kennzahlen zählen
| Kennzahl (im Werbeanzeigenmanager) | Bedeutung | Bewertung |
|---|---|---|
| **Kosten pro begonnener Unterhaltung** („Messaging-Unterhaltungen begonnen“) | Was kostet eine WhatsApp-Nachricht? | **Hauptkennzahl** |
| **Echte Anfragen** (selbst zählen in WhatsApp, Kennung A/B/C) | Nachricht mit Objekt/Ort/Leistung, keine reine Neugier | wichtiger als jede Meta-Zahl |
| Besichtigungen / Aufträge pro Variante | Was kam am Ende heraus? | das eigentliche Ziel |
| Link-Klickrate (CTR) | Wie viele tippen auf die Anzeige? | niedrig = Bild/Titel überzeugt nicht |
| Frequenz | Wie oft hat eine Person die Anzeige gesehen? | über ca. 3–4 in 14 Tagen: neues Bild nötig |
| CPM (Kosten pro 1.000 Einblendungen) | Wie teuer ist die Zielgruppe? | nur zum Vergleich |

**Ziel-Kosten pro Anfrage** legt der Inhaber selbst fest: Was darf eine echte Anfrage kosten, wenn z. B. jede fünfte zu einem Auftrag wird?
`[OFFEN: Zielwert für „Kosten pro echte Anfrage“ – hängt von Auftragswert und Abschlussquote ab.]`

**Auswertungs-Tabelle (zum Ausfüllen am Tag 7 und 14):**

| Variante | Ausgegeben € | Unterhaltungen | Kosten/Unterhaltung | Echte Anfragen | Besichtigungen | Aufträge |
|---|---|---|---|---|---|---|
| A Winterdienst | | | | | | |
| B Ansprechpartner | | | | | | |
| C Besichtigung | | | | | | |

## 6. Plan B: Website-Klicks statt WhatsApp
Falls WhatsApp sich nicht mit der Facebook-Seite verknüpfen lässt (Festnetznummer):
- Kampagnenziel **Traffic** → Conversion-Ort **Website**, Leistungsziel „Anzahl der Landingpage-Aufrufe maximieren“.
- Button: **Mehr dazu** oder **Angebot anfordern**.
- Ziel-URL mit Kennung, damit man in der Statistik sieht, woher der Besuch kommt:
  - A: `https://www.haus-meister-helden.de/?utm_source=instagram&utm_medium=paid&utm_campaign=test-dez26&utm_content=A`
  - B: gleiche URL mit `utm_content=B`, C: mit `utm_content=C`
  - `[OFFEN: Gibt es eine Winterdienst-Unterseite? Dann für Anzeige A direkt dorthin verlinken.]`
- Auf der Webseite muss der WhatsApp-Button gut sichtbar sein (Aufgabe für `webseiten-bauer`).
- Kein Meta-Pixel ohne Cookie-Einwilligung einbauen. Für den Test reicht die Messung über die URL-Kennung.

## 7. Schritt-für-Schritt im Meta-Werbeanzeigenmanager (für Laien)

Am besten am Computer, nicht am Handy. Dauer beim ersten Mal ca. 30–45 Minuten.
Meta ändert die Oberfläche öfter. Wenn ein Knopf anders heißt, nach dem sinngemäßen Begriff suchen.

**A. Einmalig vorbereiten**
1. **Instagram auf Business umstellen:** Instagram-App → Profil → ☰ Menü → „Kontotyp und Tools“ → „Zu professionellem Konto wechseln“ → **Unternehmen** → Kategorie wählen.
2. **Facebook-Seite anlegen** (falls noch keine da ist): facebook.com → Menü → „Seiten“ → „Neue Seite erstellen“ → Name „Hausmeister Helden“, Kategorie „Hausmeisterdienst“ o. ä., Adresse, Telefon, Webseite.
3. **Instagram mit der Seite verbinden:** business.facebook.com öffnen (Meta Business Suite) → „Einstellungen“ → „Instagram-Konto verbinden“ (bzw. in der Seite: Einstellungen → „Verknüpfte Konten“ → Instagram) → mit dem Instagram-Login bestätigen.
4. **WhatsApp verbinden:** Seiten-Einstellungen → „Verknüpfte Konten“ → **WhatsApp** → Nummer 05241 3389748 eingeben → Code, der per WhatsApp kommt, eintragen.
5. **Zahlungsmethode hinterlegen:** adsmanager.facebook.com → „Abrechnung und Zahlungen“ → Zahlungsmethode hinzufügen.

**B. Kampagne anlegen**
6. adsmanager.facebook.com öffnen → grüner Knopf **„+ Erstellen“**.
7. Kampagnenziel **„Interaktion“** wählen → „Weiter“. (Falls Meta „Manuelle Kampagne“ oder „Advantage+“ zur Wahl stellt: **manuell**.)
8. Kampagnenname: `HMH Test Dez26 WhatsApp`. „Sonderkategorien“: nichts auswählen (siehe Abschnitt 3). „Advantage+ Kampagnenbudget“: **aus**.

**C. Anzeigengruppe A anlegen** (danach zweimal duplizieren für B und C)
9. Name: `A Winterdienst`.
10. **Conversion-Ort:** „Messaging-Apps“ → **nur WhatsApp** anhaken → die Nummer auswählen.
11. **Leistungsziel:** „Anzahl der Unterhaltungen maximieren“.
12. **Budget und Zeitplan:** Tagesbudget **3,00 €**, Startdatum, **Enddatum = Start + 14 Tage**.
13. **Zielgruppe:** Standort „Gütersloh“ eintippen → Radius auf **25 km** stellen. Alter **30 bis 65+**. Sprache Deutsch.
    Detailliertes Targeting: Interessen aus Abschnitt 3 eintippen und vorhandene auswählen.
14. **Platzierungen:** „Manuelle Platzierungen“ → nur **Instagram** anhaken (Feed, Stories, Reels, Explore).
    Facebook später als eigenen Test dazunehmen, wenn Instagram läuft.

**D. Anzeige A anlegen**
15. Name: `A Winterdienst Bild`. **Identität:** Facebook-Seite „Hausmeister Helden“ und das **Instagram-Konto** auswählen.
16. Format: **Einzelbild oder -video**. Bild hochladen: `A-winterdienst-feed/folie-01.png`.
17. **Platzierungen anpassen:** Bei „Stories und Reels“ auf „Bearbeiten“ → stattdessen `A-winterdienst-story/folie-01.png` wählen
    (optional für Reels das Video `A-winterdienst-reel/reel.mp4`). So wird nichts abgeschnitten.
18. **Primärtext**, **Überschrift**, **Beschreibung** aus Abschnitt 4 hineinkopieren.
19. **Call-to-Action:** „WhatsApp-Nachricht senden“. Bei „Nachrichtenvorlage“ / „Vorausgefüllte Nachricht“ den Text mit „(Anzeige A)“ eintragen.
20. **„Advantage+ Creative“ / automatische Optimierungen ausschalten** (Musik, Text-Varianten, KI-Hintergründe), damit die Anzeige genau so erscheint wie freigegeben.
21. Rechts in der **Vorschau** Feed, Story und Reels kontrollieren. Dann **„Veröffentlichen“**. Meta prüft die Anzeige (meist wenige Stunden, bis zu 24 h).

**E. Varianten B und C**
22. In der Übersicht die Anzeigengruppe A anhaken → **„Duplizieren“** → zweimal. Umbenennen in `B Ansprechpartner` und `C Besichtigung`.
23. In jeder Kopie in der Anzeige nur **Bilder, Texte und vorausgefüllte Nachricht** austauschen (B bzw. C). Zielgruppe und Budget bleiben gleich.
24. Alle drei veröffentlichen. Danach 3 Tage nichts ändern.

**F. Auswerten**
25. Im Werbeanzeigenmanager Spalten „Leistung“ wählen; die Spalte „Kosten pro begonnener Messaging-Unterhaltung“ hinzufügen.
26. Am Tag 7 und 14 die Tabelle in Abschnitt 5 ausfüllen und entscheiden.

**Nicht nutzen:** den „Bewerben“-Knopf direkt unter einem Instagram-Beitrag für diesen Test. Er ist bequem, erlaubt aber keinen sauberen A/B/C-Vergleich und
weniger Kontrolle über Zielgruppe und Text.

## 8. Regeln
- Keine erfundenen Zahlen, Bewertungen oder Kundenstimmen; keine Fotos, die als „unsere Arbeit“ ausgegeben werden.
- Keine Preise, bis der Inhaber sie freigibt (netto/brutto ist noch offen).
- Anfragen aus Anzeigen sind Personen, die **selbst** schreiben. Keine ungefragten Nachrichten an Fremde.
- Kundendaten aus WhatsApp nicht in Tabellen außerhalb des Handys sammeln, ohne dass das in der Datenschutzerklärung steht.

## Quellen (abgerufen 24.11.2026)
- WhatsApp Business – Anzeigen, die zu WhatsApp führen (Schritte im Werbeanzeigenmanager): https://whatsappbusiness.com/products/create-ads-that-click-to-whatsapp/
- Meta Marketing API – Messaging Ads (WhatsApp-Nummer und mit der Seite verknüpftes Instagram-Konto nötig): https://developers.facebook.com/documentation/ads-commerce/marketing-api/ad-creative/messaging-ads
- Metricool-Hilfe – Instagram muss über Facebook verbunden sein, um zu werben: https://help.metricool.com/de/create-meta-ads-campaigns-from-metricool-4t3tx
- Meta – Special Ad Categories: https://developers.facebook.com/docs/marketing-api/audiences/special-ad-category
- Jon Loomer – Special Ad Categories (Umfang „Housing“ inkl. Reparaturen): https://www.jonloomer.com/special-ad-categories-meta-ads/
