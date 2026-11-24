# Instagram automatisch posten – zwei Wege

> Stand 24.11.2026 (`instagram-manager`). Nur Beschreibung, **nichts davon ist eingerichtet**.
> Grundregel aus `CLAUDE.md`: Nichts wird ohne Freigabe des Inhabers veröffentlicht. Automatisches Posten (Weg 2)
> ist erst erlaubt, wenn der Inhaber es **ausdrücklich für Instagram** erlaubt.

## Überblick

| | Weg 1: Meta Business Suite „Planer“ | Weg 2: Instagram-Schnittstelle (Graph API) |
|---|---|---|
| Kosten | kostenlos | kostenlos (Meta), evtl. Speicherplatz für Bilder |
| Aufwand pro Woche | ca. 10 Minuten (Montag) | 0 Minuten (nur Freigabe per Nachricht) |
| Einrichtung | keine | einmalig ca. 1–2 Stunden, technisch |
| Trend-Sound beim Reel | nein in der Business Suite, ja in der Instagram-App | nein (Video wird ohne Ton gepostet) |
| Empfehlung | **jetzt sofort starten** | später, wenn das Posten regelmäßig läuft |

---

## Weg 1 (sofort, kostenlos): Meta Business Suite „Planer“

### Was jeden Montag bereitliegt
Claude erstellt jede Woche (geplante Aufgabe):
- `marketing/instagram/JJJJ-KW<nr>.md` – Wochenplan mit Tag, Uhrzeit, Caption und Hashtags zum Kopieren
- `marketing/instagram/grafiken/JJJJ-KW<nr>/<post-id>/folie-01.png …` – fertige Bilder in der richtigen Reihenfolge
- bei Reels zusätzlich `reel.mp4`

Beispiel aktuelle Woche: `marketing/instagram/2026-KW48.md` und `marketing/instagram/grafiken/2026-KW48/`.

### Voraussetzungen (einmalig)
- Instagram ist ein **Business-Konto** und mit der **Facebook-Seite** verbunden (siehe `profil.md` und `werbung/kampagne.md`, Abschnitt 7 A).
- Am PC: Ordner der Woche herunterladen (z. B. als ZIP), damit die Bilder auf dem Rechner liegen.

### Alle 4 Posts in ca. 10 Minuten vorplanen (am PC)
1. **business.facebook.com** öffnen → links **„Planer“** (oder „Content“ → „Geplant“).
2. **Karussell:** „Beitrag erstellen“ → oben bei „Posten auf“ **nur Instagram** anhaken (Facebook abwählen, falls nicht gewünscht).
   - „Foto/Video hinzufügen“ → alle Bilder des Posts auf einmal auswählen (`folie-01.png` bis `folie-0x.png`). Mehrere Bilder = Karussell.
   - Reihenfolge prüfen: Folie 01 muss vorne sein (Bilder notfalls per Ziehen sortieren).
   - Caption und Hashtags aus der Wochen-`.md` hineinkopieren. Standort „Gütersloh“ hinzufügen, falls die Business Suite das anbietet.
   - Unten **„Planen“** → Datum und Uhrzeit aus dem Wochenplan → „Beitrag planen“.
3. Schritt 2 für das zweite (und dritte) Karussell wiederholen.
4. **Reel:** „Reel erstellen“ → `reel.mp4` hochladen → Caption einfügen → „Planen“ → Datum/Uhrzeit.
   - Die Business Suite bietet keine Instagram-Musik. Das Reel hat keinen Ton. Für einen **Trend-Sound** das Reel stattdessen
     in der **Instagram-App** planen: neues Reel → Video wählen → Musik hinzufügen → Caption → **„Erweiterte Einstellungen“ → „Dieses Reel planen“** → Datum/Uhrzeit.
5. Im Planer-Kalender kontrollieren: 4 Einträge an den richtigen Tagen. Fertig.

Hinweise:
- Geplante Beiträge lassen sich bis zur Veröffentlichung im Planer ändern oder löschen.
- Die Business Suite erlaubt in der Regel bis zu 10 Bilder pro Karussell. Unsere Karussells haben 5–7 Folien.
- Stories (Umfragen, Quiz) **nicht** vorplanen: Sticker funktionieren nur beim Posten direkt in der App. Die Story-Ideen stehen in der Wochen-`.md`.
- Nach dem Posten: die ersten 30–60 Minuten auf Kommentare antworten, das hilft der Reichweite.

---

## Weg 2 (voll automatisch): Instagram Graph API – „Content Publishing“

Damit kann Claude die fertigen Posts selbst zur geplanten Uhrzeit veröffentlichen. **Der Inhaber muss dafür einmalig einiges einrichten.**
Claude richtet nichts selbst ein und meldet sich nirgends an.

### Was Meta voraussetzt (Stand der Meta-Dokumentation, November 2026)
- Ein **Instagram-Profikonto** (Business oder Creator). Private Konten gehen nicht.
- Eine **Meta-App** im Meta-Entwicklerportal mit der Berechtigung zum Posten:
  - Variante „Facebook Login“ (Konto ist mit der Facebook-Seite verbunden – passt zu uns, weil die Seite für Werbung ohnehin nötig ist):
    `instagram_basic`, `instagram_content_publish`, `pages_read_engagement` (plus `pages_show_list` zum Auswählen der Seite).
  - Alternative „Instagram Login“ (ohne Facebook-Seite möglich): `instagram_business_basic`, `instagram_business_content_publish`.
- **Standard Access reicht**, solange die App nur das eigene Konto bedient. Eine App-Prüfung durch Meta und Unternehmensverifizierung sind nur nötig, wenn man fremde Konten verwaltet.
- Falls die Facebook-Seite eine **Seitenveröffentlichungs-Autorisierung** (Identitätsbestätigung) verlangt, muss diese erst erledigt sein, sonst schlägt das Posten fehl.
- **Bilder und Videos müssen unter einer öffentlichen Internetadresse liegen**, wenn gepostet wird. Instagram holt sie dort selbst ab.
- **Bilder nur als JPEG.** Unsere Grafiken sind PNG – Claude wandelt sie vor dem Hochladen in JPEG um.
- Karussell: Meta nennt aktuell bis zu 20 Bilder/Videos pro Karussell, alle werden auf das Format des ersten Bildes zugeschnitten.
- Reels: Video (MP4/H.264) über eine öffentliche Adresse; Instagram verarbeitet es, dann wird veröffentlicht. **Kein Trend-Sound** per Schnittstelle.
- Stories sind ebenfalls möglich, aber **ohne interaktive Sticker** (Umfrage/Quiz) – die bleiben Handarbeit in der App.
- **Limit:** Meta nennt 50 per Schnittstelle veröffentlichte Beiträge in 24 Stunden (eine ältere Stelle der Doku nennt 100). Ein Karussell zählt als ein Beitrag. Mit 4 Posts pro Woche sind wir weit darunter.
- Die Schnittstelle kennt kein „später veröffentlichen“. Claude postet deshalb **genau zur geplanten Uhrzeit** über eine geplante Aufgabe.

### Was der Inhaber einmalig einrichtet (Checkliste)
1. Instagram-Business-Konto ✔ und mit Facebook-Seite verbunden ✔ (wie für die Werbung).
2. Auf **developers.facebook.com** mit dem eigenen Facebook-Konto ein Entwicklerkonto anlegen.
3. **„App erstellen“** → Anwendungsfall für Instagram (z. B. „Nachrichten und Inhalte auf Instagram verwalten“) → App dem Business-Portfolio „Hausmeister Helden“ zuordnen.
4. In der App die Berechtigungen aus der Liste oben hinzufügen.
5. **Zugriffstoken erzeugen:**
   - Einfach: im „Graph API Explorer“ die App wählen, Berechtigungen anhaken, Token erzeugen, in einen **langlebigen Token (ca. 60 Tage)** umtauschen. Muss dann alle 2 Monate erneuert werden.
   - Besser für Dauerbetrieb: in den **Business-Einstellungen einen Systemnutzer** anlegen, ihm App, Seite und Instagram-Konto zuweisen und für ihn einen Token mit den Berechtigungen erzeugen (läuft nicht automatisch ab).
6. Die **Instagram-Konto-ID** (IG User ID) notieren (zeigt der Graph API Explorer an).
7. **Token sicher übergeben:** als geheime Umgebungsvariable (z. B. `IG_ACCESS_TOKEN`, `IG_USER_ID`) in der Umgebung der geplanten Aufgabe – **niemals** in dieses Repository, in eine `.md`-Datei oder in einen Chat schreiben.
8. **Öffentlicher Speicherplatz für die Bilder** festlegen, z. B. ein Ordner `/ig/` auf der eigenen Webseite
   (`https://www.haus-meister-helden.de/ig/2026-KW49/…jpg`).
   Achtung: Nach `CLAUDE.md` geht die Webseite nur nach „Webseite freigeben“ live. Für wöchentliches Posten braucht es deshalb
   **entweder** eine ausdrückliche Dauer-Erlaubnis nur für den Ordner `/ig/` **oder** einen getrennten Speicher (z. B. IONOS Object Storage mit öffentlichem Lesezugriff).
   `[OFFEN: Welcher Speicherort? Dauer-Erlaubnis für /ig/?]`
9. **Schriftliche Erlaubnis** an Claude, z. B.: „Instagram automatisch posten erlaubt, nach meiner Wochenfreigabe.“

### So läuft es danach jede Woche
1. **Montag:** Claude erstellt Wochenplan, Grafiken und Captions (wie bisher) und schickt die Übersicht zur Freigabe.
2. Inhaber antwortet „Woche freigegeben“ (oder ändert etwas). **Ohne Freigabe wird nichts gepostet.**
3. Claude wandelt die Bilder in JPEG um und legt sie unter der öffentlichen Adresse ab.
4. Zur geplanten Uhrzeit postet Claude über die Schnittstelle:
   - Karussell: für jedes Bild einen Container anlegen (`POST /<IG_USER_ID>/media` mit `image_url`, `is_carousel_item=true`) →
     Karussell-Container mit Caption (`media_type=CAROUSEL`, `children=…`) → veröffentlichen (`POST /<IG_USER_ID>/media_publish`).
   - Reel: Container mit `media_type=REELS` und `video_url` → warten, bis der Status „FINISHED“ ist → veröffentlichen.
   - Vorher mit `GET /<IG_USER_ID>/content_publishing_limit` prüfen, ob das Limit frei ist.
5. Claude trägt den Link zum Beitrag in den Wochenbericht ein. Fehler (z. B. abgelaufener Token) meldet Claude im Bericht; dann postet der Inhaber diesen Beitrag über Weg 1.

---

## Kommentare und Nachrichten automatisch beantworten (Option)

**Erlaubt und sinnvoll:** automatisch antworten, wenn jemand **uns** schreibt oder **unter unserem Beitrag** kommentiert.
**Nicht vorgesehen:** massenhaft fremde Leute ungefragt per Direktnachricht anschreiben. Das verstößt gegen die Instagram-Richtlinien
(Gefahr der Kontosperre) und wäre unerlaubte Werbung (§ 7 UWG). Ebenso keine Follow/Unfollow- oder Like-Bots.

### Stufe 1 – ohne Technik (Meta Business Suite, kostenlos)
In der Business Suite unter **„Posteingang“ → „Automatisierungen“** (Bezeichnung kann abweichen):
- **Sofortantwort** auf die erste Direktnachricht: „Danke für deine Nachricht! Wir melden uns innerhalb von 24 Stunden. Am schnellsten geht's per WhatsApp: https://wa.me/4952413389748“
- **Häufige Fragen** (antippbare Fragen im Chat): „Welche Leistungen bietet ihr an?“, „In welchen Orten seid ihr unterwegs?“, „Ist die Besichtigung kostenlos?“
- **Abwesenheitsnachricht** außerhalb Mo–Sa 7–20 Uhr.
- Je nach Konto auch **Antworten auf Stichwörter** in Direktnachrichten (z. B. „WINTER“).

### Stufe 2 – Stichwort im Kommentar → private Antwort (über die Schnittstelle oder ein Tool)
Beispiel: Unter dem Winterdienst-Post steht „Kommentiere **WINTER**, dann schicken wir dir die Infos per Nachricht.“
Wer „WINTER“ kommentiert, bekommt automatisch eine private Nachricht:
```
Hi! Danke für dein Interesse am Winterdienst ❄️
Wir räumen und streuen in Gütersloh und Umgebung – für Vermieter, Verwaltungen und Gewerbe.
Besichtigung kostenlos, Angebot unverbindlich.
Schreib uns direkt per WhatsApp: https://wa.me/4952413389748?text=WINTER
Oder antworte hier mit deinem Ort, dann melden wir uns.
```
Regeln von Meta dafür:
- **Eine** private Antwort pro Kommentar, und zwar innerhalb von **7 Tagen** nach dem Kommentar.
- Weitere Nachrichten erst, wenn die Person selbst antwortet – dann innerhalb von **24 Stunden** nach ihrer Antwort.
- Ein Kommentar allein öffnet kein normales Nachrichtenfenster.
- Berechtigungen: für Kommentare `instagram_business_manage_comments` (bzw. `instagram_manage_comments`), für Nachrichten `instagram_business_manage_messages` (bzw. `instagram_manage_messages`). Die Meta-Doku nennt hier nicht überall dieselben – beim Einrichten prüfen.

Umsetzung entweder über dieselbe Meta-App wie in Weg 2 (Claude kann den Ablauf dann beschreiben/bauen, nach Freigabe)
oder über ein Tool eines offiziellen Meta-Partners (meist kostenpflichtig). Bitte keine inoffiziellen „Instagram-Bots“ mit Passwort-Login verwenden.
Datenschutz: In der Datenschutzerklärung der Webseite erwähnen, dass Instagram-Nachrichten automatisiert beantwortet werden. `[OFFEN: Abstimmung Datenschutzerklärung]`

## Quellen (abgerufen 24.11.2026)
- Meta – Content Publishing (Voraussetzungen, Berechtigungen, JPEG, öffentliche URL, Limits, Karussell, Reels, Stories): https://developers.facebook.com/docs/instagram-platform/content-publishing/
- Meta – IG User Content Publishing Limit: https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/content_publishing_limit
- Meta – IG User Media / Media Publish: https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media und https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media_publish
- Meta – Business Login for Instagram (Instagram-Login-Variante): https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/business-login
- Meta – Private Replies (eine Antwort pro Kommentar, 7 Tage, 24-Stunden-Fenster): https://developers.facebook.com/docs/instagram-platform/private-replies/
- bundle.social – Übersicht der Instagram-API-Limits (Hinweis auf widersprüchliche Angaben 25/50/100): https://bundle.social/blog/instagram-api-rate-limits
- onlinemarketing.de – Instagram-Posts und Reels am Desktop planen: https://onlinemarketing.de/social-media-marketing/instagram-posts-und-reels-am-desktop-planen-scheduling
- metricool – Meta Business Suite Anleitung 2026: https://metricool.com/de/meta-business-suite-tutorial/
