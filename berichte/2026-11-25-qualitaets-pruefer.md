# Bericht Qualitätsprüfer – 25.11.2026 (erste Runde)

Geprüft: alles, was an Kunden oder die Öffentlichkeit gehen soll – `akquise/briefe/` (L001–L037), `akquise/emails/`,
`akquise/einladungen/`, `akquise/telefonleitfaden.md`, `akquise/nachfass-serie.md`, `akquise/angebote/vorlagen/`,
`marketing/whatsapp/automatische-nachrichten.md`, `marketing/seo/google-profil.md`, `marketing/bewertungen/vorlagen.md`,
`marketing/instagram/2026-11-25-posten.md` + `plan.json`-Captions, `webseite/build.py` (nur Texte, nicht geändert).
Maßstab: `firma/profil.md` (Stand 24.11.2026).

## Ampel je Bereich

| Bereich | Ampel | Kurzbegründung |
|---|---|---|
| Briefe L001–L037 | 🟡 | Preise korrekt, Sprache sauber, alle 37 passen auf eine Seite (Probelauf Variante A und B), keine offenen Platzhalter in Variante B. Gelb nur wegen Gebäudekontrolle-Versprechen (Entscheidung offen) und Einsatzgebiet Oelde/Halle/Versmold/Bielefeld. |
| E-Mail-Vorlagen | 🟢 | Nur nach dokumentierter Einwilligung / Antwort – UWG sauber geregelt. 42× offenes `[OFFEN: Pflichtangaben E-Mail-Signatur]` behoben (siehe Korrekturen). Gebäudekontrolle-Versprechen wie bei den Briefen. |
| Einladungen / Portale E001–E015 | 🟡 | Texte sauber, Preise und Bruttowerte korrekt nachgerechnet. Versand erst möglich, wenn Kapazität, Betriebshaftpflicht und Gewerbeanmeldung vorliegen (in fast allen `[OFFEN]`). E011–E013: Plattform zahlt 22–34 €/h statt 53,50 €. |
| Telefonleitfaden | 🟡 | Rechtlich ordentlich (§ 7 Abs. 2 Nr. 1 UWG korrekt zitiert, Einwilligung wird dokumentiert). Z. 46 verspricht „Gebäudekontrolle mit Protokoll bei jeder Leistung kostenlos“. `[OFFEN: Dauer]` der Besichtigung. |
| Nachfass-Serie | 🟢 | Preise korrekt, Post/Telefon, Abmeldehinweis vorhanden. Neues Versprechen „Mängelmeldung am selben Tag“ (Z. 50) – bitte bestätigen. |
| Angebotsvorlagen 01–05 | 🟢 | Preise exakt wie Profil, Saison 01.11.–31.03., Sicht-/Objektkontrolle bereits sauber getrennt (inkl. bzw. 27 €). Interne `[OFFEN]` (Laufzeit, Zahlungsziel, Versicherung, § 19 UStG) vor erster Nutzung festlegen. |
| WhatsApp-Texte | 🟡 | Korrigiert (siehe unten). Offen: `[Notdienst-Nummer]` in der Abwesenheitsnachricht; `/objekt` verspricht „regelmäßige Kontrollgänge … alles mit Fotodokumentation“; Preise nur netto, obwohl Privatkunden schreiben (PAngV). |
| Google-Profil | 🟡 | Korrigiert (Saison, Mülltonnen-Preis). Gebäudekontrolle „kostenlos inklusive bei jeder Leistung“ an 6 Stellen; „Wir übernehmen die Räum- und Streupflicht“ ohne geklärte Betriebshaftpflicht; `[OFFEN]` Kapazität, Haftungsübernahme, Einsatz zwischen den Jahren. |
| Bewertungen (Vorlagen) | 🟢 | Fair, kein Vorfiltern, keine Gegenleistung. Hinweis: Bewertungsbitte per E-Mail gilt laut BGH als Werbung – nur an Kunden, die E-Mails von uns zugestimmt haben, oder mit Widerspruchshinweis nach § 7 Abs. 3 UWG. |
| Instagram 25.11. (Posten + plan.json) | 🟡 | Caption in `plan.json` und `2026-11-25-posten.md` identisch, Rechnung 220 € + 25 × 9,50 € = 457,50 € stimmt, Saison Nov–März. Gelb: Instagram spricht auch Privatleute an („du“) – nur Nettopreise = PAngV-Risiko. |
| Webseite (build.py, nicht geändert) | 🟡 | Preise korrekt. **Winterdienst-Saison steht noch an 2 Stellen auf „Oktober bis März“** (build.py Z. 97 und Z. 104, dazu `webseite/inhalte/ratgeber/winterdienst-pflichten-vermieter.md`) – widerspricht Profil und Preisdetail derselben Seite (Z. 99: November–März). Gebäudekontrolle „immer inklusive“ (6 Stellen). „Antwort in Stunden, nicht Tagen“ (Z. 446) vs. 24 h. Nur Nettopreise trotz Privatkunden. |

## Direkt korrigiert (eindeutige Fehler)

1. **E-Mail-Signaturen L001–L021 (42 Stellen):** `[OFFEN: Pflichtangaben E-Mail-Signatur]` bzw. eine doppelte Adresszeile (L001 Fassung A)
   ersetzt durch die Signatur, die L022–L037 schon nutzen: „Hausmeister Helden, Inhaber Martin Ogur · Auf der Benkert 68, 33330 Gütersloh /
   Telefon und WhatsApp 05241 3389748 · info@haus-meister-helden.de · www.haus-meister-helden.de“ (Pflichtangaben laut Profil: Name + Anschrift).
   Eine USt-IdNr. fehlt noch – falls vorhanden, bitte nennen.
2. **WhatsApp** (`marketing/whatsapp/automatische-nachrichten.md`):
   - Begrüßung „in der Regel innerhalb von wenigen Stunden“ → „innerhalb von 24 Stunden“ (Profil).
   - `/angebot`: „Sie erhalten das Angebot innerhalb von 24 Stunden“ → „Wir melden uns innerhalb von 24 Stunden“ (ein Angebot gibt es laut allen anderen Texten erst nach der Besichtigung).
   - `/bewertung`: „Wenn Sie zufrieden waren …“ (= Vorfiltern, verstößt gegen Google-Richtlinien und eigene Bewertungsregeln) und Platzhalter `[Google-Bewertungslink]` ersetzt durch neutrale Bitte + https://www.haus-meister-helden.de/bewertung.html.
   - Profilbeschreibung: „Treppenhausreinigung“ stand doppelt → zweites durch „Mülltonnen-Service“ ersetzt; „Antwort in wenigen Stunden“ → „innerhalb von 24 Stunden“.
3. **Google-Profil** (`marketing/seo/google-profil.md`): Beitrag 1 „von Oktober bis März“ → „von November bis März“; Mülltonnen-Preis um „+ 1,34 € je Leerung“ ergänzt (sonst unvollständig/irreführend).
4. **Instagram-Profil** (`marketing/instagram/profil.md`): Bio-Variante C „Winterdienst-Saison (Okt–März)“ → „(Nov–März)“.

Briefe: kein Tippfehler oder Formfehler gefunden → keine Brief-Datei geändert, keine PDFs neu erzeugt. Probelauf von
`akquise/brief_pdf.py` (in einer Kopie im Scratchpad, Variante A und B): alle 37 Briefe passen auf eine Seite; offene Platzhalter
nur in Variante A (Gesprächsdatum, Ansprechpartner bei L009/L017 – werden nach dem Telefonat gefüllt).

## Gebäudekontrolle – alle Stellen mit „kostenlos / inklusive / mit Protokoll bei jedem Einsatz“ (NICHT geändert)

Widerspruch im Profil selbst: unter Leistungen „Gebäudekontrolle mit Protokoll – kostenlos inklusive bei jeder Leistung“, unter Preise
„Objektkontrolle mit Fotoprotokoll als eigener Termin: 27 €; Sichtkontrolle bei jedem Einsatz inklusive“.

**Versprechen „Gebäudekontrolle mit Protokoll, kostenlos, bei jedem Einsatz“:**
- Briefe (Aufzählung, Z. 31–34): L001, L002, L003, L004, L005, L006, L007, L008, L009, L010, L011, L012, L013, L014, L015, L016, L017, L019, L021
- Briefe „mit Protokoll bei jedem Einsatz“ (ohne „kostenlos“): L018, L020
- Briefe „Gebäudekontrolle bei jedem Einsatz inklusive“ (ohne Protokoll): L025, L026, L028, L029, L030, L031, L033, L034, L037
- LinkedIn-Texte „Kontrollprotokoll (bei jedem Einsatz)“: L002–L007, L009–L017, L019
- „Zeige Ihnen unser Kontrollprotokoll“: Brief L007, L015; E-Mail L003, L007, L015
- E-Mails Fassung A „Gebäudekontrolle mit Protokoll bei jedem Einsatz, kostenlos“: L001–L017, L019, L021; ohne „kostenlos“: L018, L020; sinngemäß L028
- `akquise/telefonleitfaden.md` Z. 46
- `marketing/seo/google-profil.md` Z. 57, 68, 73 („kostenlos (inklusive)“), 111, 116–117 (FAQ „kostenlose Gebäudekontrolle“), 167
- `marketing/whatsapp/automatische-nachrichten.md` `/objekt` („regelmäßige Kontrollgänge … alles mit Fotodokumentation“)
- `marketing/instagram/profil.md` Z. 40 („Kontrolle inklusive“)
- `webseite/build.py` Z. 89, 150–151 („0 € – bei jeder Leistung inklusive“), 350, 372, 418, 520 („Gebäudekontrolle mit Protokoll ist immer inklusive“), 531 („Protokoll inklusive“)

**Schon passend zur Preisliste (Sichtkontrolle inkl., Fotoprotokoll 27 €):** E001, E002, Nachfass-Serie Z. 27/50, Angebotsvorlage 01 (Pos. 5/6), 03.
Zusätzliches Versprechen „Mängelmeldung am selben Tag“: Nachfass-Serie Z. 50, Angebotsvorlage 01 Z. 88.

## Weitere Risiken (Recht)

- **PAngV (B2C-Preise):** Webseite, Instagram, WhatsApp und Google-Profil nennen nur Nettopreise. Bei Privatkunden (Zielgruppe 5) müssen Endpreise inkl. MwSt. genannt werden. Hängt an § 19 UStG (offen).
- **Winterdienst-Haftung:** Google-Profil „Wir übernehmen die Räum- und Streupflicht“, viele Briefe „sofort startklar“ – ohne bestätigte Betriebshaftpflicht (Profil `[OFFEN]`) riskant; Angebotsvorlage 02 sagt das selbst.
- **UWG Telefon:** Ankündigung „Ich rufe Sie in der kommenden Woche an“ in fast allen Briefen. B2B erlaubt nur bei mutmaßlicher Einwilligung; bei reinen Werbeanrufen an Verwaltungen ohne vorherigen Kontakt legen Gerichte das eng aus. Empfehlung: bei Einwand sofort Sperrvermerk, nie erneut anrufen (steht im Leitfaden).
- **UWG E-Mail:** Einladungen E001, E009, E010 gehen per E-Mail – zulässig, weil die Empfänger öffentlich dazu auffordern (Quelle notiert). E-Mail-Vorlagen L001–L037 nur mit dokumentierter Einwilligung – korrekt.
- **AGG:** keine Stellenanzeigen im Prüfumfang, nichts gefunden.
- **DSGVO:** Leads nur mit geschäftlichen Kontaktdaten aus Impressum/Webseite, Quelle je Brief notiert – in Ordnung.

## Entscheidungen / Fragen an den Inhaber

1. **Gebäudekontrolle:** Was gilt? (a) „Gebäudekontrolle mit Protokoll kostenlos bei jedem Einsatz“ oder (b) „Sichtkontrolle bei jedem Einsatz inklusive, Objektkontrolle mit Fotoprotokoll 27 €“ (Preisliste). Danach passe ich alle Stellen oben einheitlich an (Webseite über `webseiten-bauer` + Freigabe).
2. **Webseite Winterdienst-Saison:** „Oktober bis März“ (build.py Z. 97, 104; Ratgeber-Artikel) auf „November bis März“ ändern lassen – über `webseiten-bauer` und Freigabe.
3. **Einsatzgebiet:** Gehören Oelde (L025, L028, L029), Versmold/Borgholzhausen/Werther (L023), Spenge (E014), Bad Rothenfelde (E015) und Bielefeld-Süd dazu? Anfahrtspreis über 25 km fehlt.
4. **Betriebshaftpflicht und Gewerbeanmeldung:** Nachweise vorhanden? Ohne sie keine Portal-Bewerbungen (E001–E013) und keine Übernahme der Räum- und Streupflicht.
5. **Kapazität Winterdienst:** Wie viele Objekte/Meter sind diese Saison noch frei? („sofort startklar“ in fast allen Briefen.)
6. **Kleinunternehmerregelung § 19 UStG** klären, danach Bruttopreise für Privatkunden auf Webseite, Instagram, WhatsApp, Google-Profil.
7. **Notdienst:** Gibt es eine Notdienst-Nummer? Sonst Satz aus der WhatsApp-Abwesenheitsnachricht streichen.
8. **„Mängelmeldung am selben Tag“** (Nachfass-Serie, Rahmenvertrag) – zusagen oder auf „innerhalb von 24 Stunden“ ändern?
9. **USt-IdNr.** vorhanden? Dann in E-Mail-Signatur und Briefe aufnehmen.
10. **E011–E013** (anonyme Plattform, 22–34 €/h statt 53,50 €/h): überhaupt bewerben?
11. **Dauer der Objektbesichtigung** für den Telefonleitfaden (`[OFFEN: Dauer]`).

## Was braucht Freigabe
Alle Briefe, E-Mails, Einladungen, Instagram-Beiträge, WhatsApp-Texte und das Google-Profil sind weiterhin Entwürfe. Nichts wurde verschickt, veröffentlicht oder committet.
