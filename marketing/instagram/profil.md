# Instagram-Profil – Hausmeister Helden (Version 3, Stand 24.11.2026 – mit 15-Minuten-Checkliste)

> Entwurf. Nichts davon ist live. Der Inhaber richtet das Profil selbst ein bzw. gibt es frei.
> Grundlage: `firma/profil.md`. Fehlende Daten sind als `[OFFEN: …]` markiert.

## 1. Benutzername (Handle)
`[OFFEN: Instagram-Name noch nicht festgelegt]`

**Vorschläge** (vor dem Anlegen auf Verfügbarkeit prüfen, keiner davon ist bestätigt):
1. `@hausmeisterhelden_gt` (Favorit: kurz, „GT“ = Kennzeichen-/Ortskürzel Gütersloh)
2. `@hausmeister.helden.guetersloh` (Ort ausgeschrieben, besser für die Suche)
3. `@hausmeisterhelden` (falls frei, am einfachsten zu merken)

Tipp: Gleichen Namen auch für Facebook/TikTok sichern, falls später gewünscht.

## 2. Name-Feld (wird bei der Instagram-Suche durchsucht)
Maximal 30 Zeichen. Keyword + Ort sind wichtiger als der reine Firmenname.

- **Empfehlung:** `Hausmeister Helden | Gütersloh` (30 Zeichen)
- Alternative: `Hausmeisterservice Gütersloh` (28 Zeichen, reines Keyword)
- Langform aus der Vorgabe: `Hausmeister Helden | Hausmeisterservice Gütersloh` ist mit 49 Zeichen zu lang für das Name-Feld. Das Keyword „Hausmeisterservice“ kommt deshalb in die erste Bio-Zeile bzw. in die Kategorie.

**Kategorie (Business-Konto):** „Hausmeisterdienst“ oder „Gebäudedienstleister“ (je nachdem, was Instagram anbietet).
**Kontaktoptionen:** Telefon 05241 3389748, E-Mail info@haus-meister-helden.de, Adresse Auf der Benkert 68, 33330 Gütersloh, WhatsApp-Button mit WhatsApp Business verknüpfen.

## 3. Bio-Varianten (max. 150 Zeichen)

**Variante A – Leistungen (Empfehlung)**
```
Hausmeisterservice Gütersloh & Umgebung
❄️ Winterdienst · 🧹 Treppenhaus · 🌿 Garten · 🔧 Reparaturen
Antwort in 24 h
📲 Angebot per WhatsApp 👇
```

**Variante B – Nutzen für Vermieter/Verwalter**
```
Ihr Haus. Unsere Pflicht. 🦸
Hausmeisterservice für Vermieter & Verwaltungen im Kreis Gütersloh
Fester Ansprechpartner · Kontrolle inklusive
📲 Angebot per WhatsApp
```

**Variante C – Winterdienst-Saison (Nov–März)**
```
❄️ Winterdienst Gütersloh – räumen & streuen
+ Treppenhaus, Garten, Kleinreparaturen
Besichtigung kostenlos
📲 Jetzt Angebot per WhatsApp 👇
```

Hinweis: Instagram zählt Emojis teilweise doppelt. Nach dem Einfügen prüfen, ob die Bio unter 150 Zeichen bleibt.
Ansprache in der Bio neutral (ohne du/Sie), weil Verwalter und Privatleute mitlesen. In Posts gilt „du“.

## 4. Link-Strategie
Instagram erlaubt bis zu 5 Links in der Bio, sichtbar ist der erste.

| Reihenfolge | Titel | Link |
|---|---|---|
| 1 (sichtbar) | 📲 Angebot per WhatsApp | https://wa.me/4952413389748 |
| 2 | Webseite & Preisrechner | https://www.haus-meister-helden.de |
| 3 | Winterdienst | `[OFFEN: Unterseite Winterdienst auf der Webseite? sonst Startseite]` |
| 4 | Google-Bewertungen | `[OFFEN: Google-Bewertungslink, sobald Profil vorhanden]` |

- **WhatsApp-Link mit vorausgefülltem Text** (empfohlen, zeigt die Herkunft der Anfrage):
  `https://wa.me/4952413389748?text=Hallo%2C%20ich%20komme%20von%20Instagram%20und%20h%C3%A4tte%20gern%20ein%20Angebot.`
  Dann sieht der Inhaber sofort: Anfrage kam über Instagram (für die Erfolgsmessung).
- `[OFFEN: Die Nummer ist ein Festnetzanschluss. Bitte einmal testen, ob der wa.me-Link vom Handy aus wirklich den WhatsApp-Business-Chat öffnet.]`
- Webseite optional mit Kennung versehen, z. B. `https://www.haus-meister-helden.de/?utm_source=instagram`, falls die IONOS-Statistik das auswertet.
- In Captions keinen klickbaren Link erwarten: Immer „Link in der Bio“ oder „schreib uns per WhatsApp“ schreiben. In Stories den Link-Sticker nutzen.

## 5. Story-Highlights (Version 2: komplett ohne Filmen)
Der Inhaber möchte nicht selbst im Bild sein und hat derzeit keine Aufträge zum Filmen. Deshalb entfallen „Vorher/Nachher“ und „Team“; alle Highlights bestehen aus Grafiken, Text-Stories und Stickern.

**Cover:** fertige Grafiken im Hausmeister-Helden-Design (dunkler Hintergrund, grüner Schriftzug), erzeugt mit
`python3 marketing/instagram/grafik.py marketing/instagram/2026-KW48.json` (Post-ID `00-highlight-cover`):

| Reihenfolge | Highlight | Cover-Datei | Inhalt |
|---|---|---|---|
| 1 | Leistungen | `marketing/instagram/grafiken/2026-KW48/00-highlight-cover/folie-01.png` | Je 1 Text-Story pro Leistung: Treppenhaus, Winterdienst, Garten, Kleinreparaturen, Mülltonnen, Gebäudekontrolle mit Protokoll (kostenlos inklusive) |
| 2 | Ablauf | `…/00-highlight-cover/folie-02.png` | Karussell „So betreuen wir dein Haus“ (KW48, Post 4) als Stories: melden → kostenlose Besichtigung → Angebot → Betreuung |
| 3 | Winterdienst | `…/00-highlight-cover/folie-03.png` | Karussells „3 Pflichten“ und „4 Mythen“, Reel „Wer räumt vor deinem Haus?“, Umfrage-/Quiz-Stories |
| 4 | FAQ | `…/00-highlight-cover/folie-04.png` | Antworten auf Fragen-Sticker (ohne Namen/Profilbild der Fragenden), z. B. „Wie schnell meldet ihr euch?“ – „Innerhalb von 24 Stunden.“ |
| 5 | Kontakt | `…/00-highlight-cover/folie-05.png` | Telefon/WhatsApp 05241 3389748, Link-Sticker https://wa.me/4952413389748, Mo–Sa 7–20 Uhr, Gütersloh & Umgebung, „Besichtigung kostenlos“ |
| später | Bewertungen | – | Erst anlegen, wenn echte Bewertungen vorliegen (Google-Screenshots oder WhatsApp-Lob, nur mit Erlaubnis, ohne Namen/Profilbild). `[OFFEN: noch keine Referenzen vorhanden]` |

So geht's: Jede Cover-Grafik einmal als Story posten (sie ist gleichzeitig die Einstiegs-Story des Highlights), dann ins Highlight speichern und beim Bearbeiten des Highlights als Titelbild wählen; den runden Ausschnitt auf den grünen Schriftzug ziehen.
Alternative, falls die Schrift im Kreis zu klein wirkt: in der App einfarbige Cover mit Emoji (🛠️ 📋 ❄️ ❓ 📲).
Sobald es echte Aufträge gibt: Objektfotos (ohne Personen, Hausnummern, Kennzeichen, mit Einwilligung des Auftraggebers) können als zusätzliches Highlight „Einsätze“ dazukommen.

## 6. Profil-Checkliste für den Inhaber
- [ ] Handle festlegen und anlegen (Vorschlag siehe oben)
- [ ] Auf **Business-Konto** umstellen (Statistiken, Kontakt-Buttons)
- [ ] Profilbild: Logo `[OFFEN]` (kein Foto des Inhabers, da er nicht im Bild sein möchte)
- [ ] Name-Feld, Bio, Links eintragen
- [ ] WhatsApp-Button verknüpfen und Link testen
- [ ] Erste 6 Beiträge posten, bevor aktiv kommentiert wird (Profil soll nicht leer wirken)
- [ ] Highlights anlegen, sobald je 1 Story vorhanden ist

## 7. In 15 Minuten einrichten (einmal komplett fertig machen)
> Am Handy in der Instagram-App. Menünamen können je nach App-Version leicht abweichen.

**Vorher bereitlegen:** Logo als Bild `[OFFEN: Logo-Datei]`, die 5 Highlight-Cover und die ersten 3 Posts aus
`marketing/instagram/grafiken/2026-KW48/` aufs Handy laden.

1. **Business-Konto (2 Min.):** Profil → ☰ → „Kontotyp und Tools“ → „Zu professionellem Konto wechseln“ → **Unternehmen**.
2. **Kategorie (1 Min.):** „Hausmeisterdienst“ wählen, sonst „Gebäudedienstleister“ o. ä. → im Profil anzeigen: **an**.
3. **Mit Facebook-Seite verbinden (2 Min.):** Profil bearbeiten → „Seite“ → Facebook-Seite „Hausmeister Helden“ verbinden
   (nötig für Werbung und Planer, siehe `werbung/kampagne.md`).
4. **Name & Benutzername (1 Min.):** Name: `Hausmeister Helden | Gütersloh` · Benutzername: `[OFFEN: z. B. @hausmeisterhelden_gt]`.
5. **Bio zum Kopieren (1 Min.):**
   ```
   Hausmeisterservice Gütersloh & Umgebung
   ❄️ Winterdienst · 🧹 Treppenhaus · 🌿 Garten · 🔧 Reparaturen
   Antwort in 24 h
   📲 Angebot per WhatsApp 👇
   ```
6. **Kontakt-Buttons (2 Min.):** Profil bearbeiten → „Kontaktoptionen“ → Telefon **05241 3389748**, E-Mail **info@haus-meister-helden.de**,
   Adresse **Auf der Benkert 68, 33330 Gütersloh**. WhatsApp: unter „Kontaktoptionen“ bzw. „Links“ → **WhatsApp hinzufügen** → Nummer bestätigen.
7. **Links (2 Min.):** Profil bearbeiten → „Links“ → in dieser Reihenfolge:
   1. `📲 Angebot per WhatsApp` → `https://wa.me/4952413389748?text=Hallo%2C%20ich%20komme%20von%20Instagram%20und%20h%C3%A4tte%20gern%20ein%20Angebot.`
   2. `Webseite & Preisrechner` → `https://www.haus-meister-helden.de`
   3. `Impressum` → `[OFFEN: genaue Impressum-URL der Webseite]` (geschäftliche Profile brauchen ein leicht erreichbares Impressum)
8. **Erste 3 Posts (3 Min.):** in **dieser** Reihenfolge posten (das zuletzt gepostete steht oben links):
   1. `grafiken/2026-KW48/02-winterdienst-mythen/` (6 Folien)
   2. `grafiken/2026-KW48/01-winterdienst-pflichten/` (5 Folien)
   3. `grafiken/2026-KW48/04-objektbetreuung-ablauf/` (7 Folien) → danach **anheften** (⋯ → „An Profil anheften“), weil er erklärt, wie wir arbeiten.
   Captions und Hashtags stehen in `2026-KW48.md`. Standort „Gütersloh“ taggen. Diese 3 Posts entfallen dann im KW48-Plan; das Reel (`03-wer-raeumt-reel`) wie geplant posten.
9. **Highlights (2 Min.):** Die 5 Cover aus `grafiken/2026-KW48/00-highlight-cover/` nacheinander als Story posten → jede Story über „Highlight“ speichern:
   `folie-01.png` → **Leistungen**, `folie-02.png` → **Ablauf**, `folie-03.png` → **Winterdienst**, `folie-04.png` → **FAQ**, `folie-05.png` → **Kontakt**.
   Beim Titelbild den runden Ausschnitt auf den grünen Schriftzug ziehen.
10. **Prüfen (1 Min.):** Vom Handy eines Bekannten oder ausgeloggt das Profil ansehen: WhatsApp-Link tippen → öffnet sich der Chat mit 05241 3389748?

Danach: Wochenplan über die Meta Business Suite vorplanen (`automatisch-posten.md`), erst dann Werbung starten (`werbung/kampagne.md`).

## 8. Regeln
- Keine gekauften Follower/Likes, keine Follow/Unfollow-Bots (Sperrgefahr).
- Keine erkennbaren Personen, Hausnummern, Klingelschilder oder Kfz-Kennzeichen ohne Einwilligung zeigen.
- Keine erfundenen Kundenstimmen, Zahlen oder Zertifikate.
