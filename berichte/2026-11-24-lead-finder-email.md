# Bericht lead-finder – E-Mail-Lauf (24.11.2026)

## Auftrag
Nur Firmen und Personen finden, die man **rechtlich zulässig direkt anschreiben** darf, weil sie selbst
öffentlich um Kontakt durch Dienstleister bitten (§ 7 UWG). Region: Gütersloh + ca. 25–30 km.

## Ergebnis in Zahlen
- **15 Treffer** mit belegter Einladung (E001–E015): 10 × Kategorie A (Partner/Nachunternehmer/Listung),
  5 × Kategorie B (aktuelles Gesuch), 0 × Kategorie C (Ausschreibung).
- Prioritäten: **3 × A** (E001, E002, E011), **7 × B**, **5 × C**.
- **Rund 75 Quellen geprüft**, davon 26 TED-Bekanntmachungen gescreent. **31 Fälle verworfen** und
  begründet, dazu kommen weitere Kleinanzeigen-Treffer, die offensichtlich nicht passen
  (Haushaltsreinigung, Ersatzteile).
- Die Liste steht in `leads/email-erlaubt.md` mit Beleg-URL und wörtlichem Zitat. Die Treffer sind
  als E001–E015 in `leads/leads.csv` eingetragen (status „neu“). Der Nachtrag zu den Ausschreibungen
  steht in `leads/ausschreibungen.md`.
- Die bestehenden Leads L001–L021 habe ich nicht geändert: Auf ihren Webseiten gibt es keine
  Dienstleister-Einladung, sie bleiben bei Brief und Anruf.

## Die Treffer
| ID | Firma | Ort | Kat. | Kontaktweg | Prio |
|---|---|---|---|---|---|
| E001 | Fedder und Zünkler (Winterdienst/Grünpflege-Netz) | Laer, betreut Bielefeld | A | Formular oder info@fedder-zuenkler.de | A |
| E002 | Amendt Winterdienst | Telgte/Münster, nennt Bielefeld | A | Partner-Formular (info@amendt-winterdienst.de) | A |
| E003 | Stemweder Service Group | Marl/Stemwede, deutschlandweit | A | Nachunternehmer-Formular | B |
| E004 | Piepenbrock (NL Bielefeld) | Bielefeld | A | Nachunternehmer-Formular | B |
| E005 | LEG Wohnen NRW über Youtilly | NRW | A | Registrierung im Portal Youtilly | B |
| E006 | Vonovia Partnerportal | bundesweit/Bielefeld | A | Partnerportal | C |
| E007 | Ihre Hausmeister (IMMOBILIENWERK UG) | Schwerte, bundesweit | A | Formular/Telefon | C |
| E008 | ATRIONA Facility | Karlsruhe, bundesweit | A | Fragebogen | C |
| E009 | Seibel365 | Bielefeld | A | service@gmbh-seibel.de | C |
| E010 | Stadt Bielefeld, Anbieterliste Winterdienst | Bielefeld | A (Listung) | winterdienst@bielefeld.de | B |
| E011 | Gebäudereinigung.com: Winterdienst-Subunternehmer | Gütersloh | B | Bewerbung im Portal | A |
| E012 | Gebäudereinigung.com: Winterdienst-Subunternehmer | Bielefeld | B | Bewerbung im Portal | B |
| E013 | Gebäudereinigung.com: Reinigungs-Subunternehmer (u. a. Treppenhaus) | Bielefeld | B | Bewerbung im Portal | C |
| E014 | S. Vermietungen, 2 MFH Treppenhausreinigung | Spenge | B | Kleinanzeigen-Nachricht | B |
| E015 | Vermieter, 3 Apartments, Kleinreparaturen | Bad Rothenfelde | B | Kleinanzeigen-Nachricht | B |

## Offene Ausschreibungen mit Frist
Im Umkreis gibt es keine passende. Geprüft und verworfen: HWK OWL „Außenanlagen“ (Frist 16.12.2026,
Neubau), Uni Paderborn Grünpflege (Frist 18.12.2026, außerhalb), Reinigung Studieninstitut
(Frist 07.01.2027, Münster). Details stehen in `leads/ausschreibungen.md`.

## Empfehlung für den `akquise-texter`
1. **Diese Woche zuerst:** E011 (Winterdienst Gütersloh, Portal-Bewerbung), E002 (Amendt, die Saison läuft)
   und E001 (Fedder und Zünkler). Kurz und sachlich schreiben: Einsatzgebiet, Personal, Geräte,
   Streugut, Erreichbarkeit, Gewerbe- und Haftpflichtnachweis.
2. **Jede Nachricht nimmt Bezug auf die konkrete Einladung** (Seite oder Anzeige nennen). Keine
   Sammelmail, die Adressen nicht für andere Werbung verwenden. Wo nur Formular oder Portal genannt
   ist, nur diesen Weg nutzen.
3. **Preise aus der freigegebenen Liste** (netto zzgl. 19 % MwSt., `firma/profil.md`):
   - E014 Spenge: 12 € je Treppenhaus und Reinigung + 8 € je Etage, bei 14-täglicher Reinigung +15 %,
     Anfahrt Umland 36,50 €. Die Etagenzahl über eine kostenlose Besichtigung klären.
   - E015 Bad Rothenfelde: 53,50 €/Std. (je angefangene 15 Min. 13,50 €, mindestens 30 Min.),
     Anfahrt Umland 36,50 €.
   - Bei Netzwerk-Partnern (E001–E005, E011) legen meist die Auftraggeber die Vergütung fest. Deshalb
     erst deren Sätze abfragen und keine eigenen Preise vorgeben.
4. **E010** ist ein einfacher Gewinn: kostenlos auf die Bielefelder Anbieterliste Winterdienst.
5. **Ehrlich bleiben:** E015 fragt nach Referenzen. Es gibt noch keine echten, also keine erfinden,
   sondern kostenlose Probe-Besichtigung und 24-h-Reaktion anbieten.

## Was braucht Freigabe
- Jede einzelne Nachricht und Bewerbung (E001–E015). Nichts ist verschickt, nichts ist committet.
- Registrierungen in Portalen (Youtilly, Vonovia, Piepenbrock, Gebäudereinigung.com) muss der Inhaber
  selbst machen, weil dabei Firmendaten und AGB bestätigt werden.

## Fragen an den Inhaber
1. Gibt es Kapazität für **Winterdienst mit 24/7-Bereitschaft** (Amendt verlangt das) und für wie viele
   Objekte? Gibt es ein Streugutlager und ein Räumfahrzeug?
2. Liegen **Gewerbeanmeldung und Betriebshaftpflicht-Nachweis** vor? [OFFEN] ATRIONA, Stemweder,
   Amendt und Gebäudereinigung.com verlangen das bei der Bewerbung.
3. Wollen Sie als **Subunternehmer unter fremder Marke** arbeiten (Ihre Hausmeister, Netzwerke) oder
   nur unter Hausmeister Helden?
4. Ist **Paderborn** (Momm GmbH sucht Winterdienst-Subunternehmer) oder **Spenge/Bad Rothenfelde**
   (am Rand von 25 km) noch Ihr Gebiet? Welche Anfahrt gilt über 25 km? [OFFEN]
5. Hinweis: LUTHER IMMO (Halle) sucht einen Minijob-Hausmeister. Das ist keine E-Mail-Einladung, aber
   ein Bedarfssignal für einen normalen Brief oder Anruf. Soll der Lead in die normale Liste?

## Nicht prüfbar
MyHammer (Bot-Schutz), Check24-Profis, die Youtilly-Ausschreibungsliste und Facebook-Gruppen gehen nur
mit Konto. Einige Seiten waren aus der Arbeitsumgebung nicht erreichbar (winterdienst-nrw-24.de,
Gegenbauer, B&O Service, Momm-Website).
