# Facebook-Seite automatisch posten – Einrichtung und was technisch geht

> Stand 25.11.2026 (`facebook-manager`). Recherche in der **offiziellen Meta-Doku** (aktuelle Graph-API-Version laut Doku: **v27.0**).
> Grundregel aus `CLAUDE.md`: **Nichts wird ohne Freigabe des Inhabers veröffentlicht.** Automatisches Posten heißt nur:
> Der Inhaber gibt den Wochenplan frei („Facebook freigeben“), danach postet ein Skript zu den geplanten Zeiten.
> **Noch nicht eingerichtet** – es gibt weder Facebook-Seite noch Meta-App noch Token. Das Posting-Skript wird erst gebaut, wenn der Token da ist.

## 1. Kurz: Was geht, was nicht

| Geht per Schnittstelle (Pages API) | Geht nicht bzw. nur von Hand |
|---|---|
| **Foto-Beitrag** mit Text (ein Bild) – `POST /{page-id}/photos` | **In Gruppen posten** – die Groups API wurde von Meta abgeschaltet (ab v19.0, für alle Versionen seit 22.04.2024). Gruppen also immer von Hand und nur nach Freigabe (`gruppen.md`). |
| **Mehrere Bilder in einem Beitrag** (unsere Karussell-Grafiken): Bilder zuerst unveröffentlicht hochladen, dann gemeinsam über `POST /{page-id}/feed` veröffentlichen | Beiträge, die **nicht** über unsere App erstellt wurden, kann die App nicht bearbeiten („An app can only update a Page post if the post was made using that app.“) |
| **Text- oder Link-Beitrag** – `POST /{page-id}/feed` mit `message` und `link` | Ort-Markierung, Musik, Umfragen in Beiträgen: in der Doku zum Posten nicht vorgesehen – von Hand in der App/Business Suite |
| **Beitrag bei Facebook vorplanen** – `published=false` + `scheduled_publish_time` | Beitrag oben anpinnen – von Hand |
| Beitrag ändern / löschen (nur selbst über die App erstellte) | Antworten auf Kommentare/Nachrichten: technisch möglich (`pages_manage_engagement`), aber **bei uns nur Entwürfe**, der Inhaber antwortet selbst |
| Seiten-Storys: Meta hat eine eigene „Page Stories API“ (laut Doku vorhanden, hier noch nicht im Detail geprüft) | Reels/Videos: laufen über die Video API – nicht Teil dieser Einrichtung |

**Vorteil gegenüber Instagram:** Bei Facebook kann das Skript die Bilder **direkt hochladen** (Datei-Upload, `multipart/form-data`).
Die Grafiken müssen also **nicht** vorher öffentlich ins GitHub-Repository gepusht werden (anders als bei `marketing/instagram/posten.py`).
PNG ist erlaubt (Formate laut Doku: JPEG, BMP, PNG, GIF, TIFF; max. 10 MB, PNG möglichst unter 1 MB → unsere Grafiken werden vor dem Upload in JPEG umgewandelt).

## 2. Einrichtung für den Inhaber (einmalig, ca. 45–60 Minuten, am PC)

Voraussetzung: Die Facebook-Seite „Hausmeister Helden“ ist angelegt (`seite.md`) und Sie sind dort Administrator (volle Kontrolle).

**Schritt 1 – Meta-Entwicklerkonto**
1. https://developers.facebook.com öffnen, mit Ihrem Facebook-Profil anmelden → „Loslegen“/„Get Started“ → als Entwickler registrieren (Telefonnummer bestätigen).

**Schritt 2 – App anlegen**
2. „Meine Apps“ → **„App erstellen“**. Name z. B. `Hausmeister Helden Posting`, Kontakt-E-Mail info@haus-meister-helden.de.
3. Anwendungsfall (Use Case) auswählen: **„Manage everything on your Page“** („Alles auf deiner Seite verwalten“). Dadurch werden
   `business_management`, `pages_show_list` und `public_profile` automatisch hinzugefügt.
   (Hinweis aus der Doku: Dieser Anwendungsfall lässt sich nicht mit „Facebook Login“ in derselben App kombinieren – das ist für uns auch nicht nötig.)
4. Falls nach einem Unternehmensportfolio (Business) gefragt wird: das vorhandene auswählen oder „Ich möchte noch kein Unternehmensportfolio verbinden“.
5. Im App-Dashboard beim Anwendungsfall **„Anpassen“** → diese Berechtigungen hinzufügen:
   **`pages_manage_posts`**, **`pages_read_engagement`** (und, falls angeboten, `pages_read_user_engagement`).
   Mehr nicht – keine Werbe-, Nachrichten- oder Gruppenrechte.

**Keine App-Prüfung (App Review) nötig:** Die App wird nur von Ihnen selbst genutzt (Sie haben eine Rolle in der App). Laut Meta reicht dafür
der „Standard-Zugriff“; der „Erweiterte Zugriff“ mit App Review und Unternehmensverifizierung ist nur nötig, wenn fremde Nutzer die App verwenden.
Die App kann im Modus „Entwicklung“ bleiben.

**Schritt 3 – Seiten-Token erzeugen**
6. https://developers.facebook.com/tools/explorer (Graph API Explorer) öffnen → rechts die App `Hausmeister Helden Posting` wählen →
   „Berechtigungen hinzufügen“: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts` → **„Generate Access Token“** →
   im Facebook-Fenster die Seite „Hausmeister Helden“ auswählen und zustimmen.
7. Dieser Token ist kurzlebig (ca. 1–2 Stunden). Für den Dauerbetrieb braucht es einen **langlebigen Seiten-Token**:
   - kurzlebigen Nutzer-Token gegen einen langlebigen tauschen (`GET /oauth/access_token?grant_type=fb_exchange_token&client_id=…&client_secret=…&fb_exchange_token=…`,
     hält laut Meta ca. 60 Tage – braucht das **App-Geheimnis**, deshalb nicht im Browser teilen),
   - mit dem langlebigen Nutzer-Token `GET /me/accounts` aufrufen → dort steht der **Seiten-Token** für „Hausmeister Helden“ und die **Seiten-ID**.
   - Laut Meta haben langlebige Seiten-Token **kein festes Ablaufdatum**; sie werden aber ungültig, wenn z. B. das Passwort geändert,
     die Admin-Rolle entzogen oder die App-Berechtigung widerrufen wird.
   Diesen Tausch können wir **gemeinsam in einer Sitzung** machen: Sie geben App-ID, App-Geheimnis und den kurzlebigen Token über das
   **sichere Formular** ein (nie in den Chat), das Skript erledigt den Rest.
8. Den **Seiten-Token** ebenfalls nur über das **sichere Formular** hinterlegen (Host `graph.facebook.com`). Der Token steht nie im Repository,
   in `plan.json` oder in Ausgaben – genau wie beim Instagram-Token.
9. Die **Seiten-ID** darf in `firma/profil.md` stehen (ist nicht geheim).

**Sicherheit:** Zwei-Faktor-Anmeldung für Ihr Facebook-Profil einschalten. Wenn Sie den Zugriff entziehen wollen:
Facebook → Einstellungen → „Business-Integrationen“ → App entfernen – danach ist der Token sofort wertlos.

## 3. Wie das automatische Posten dann läuft (gleiches Verfahren wie bei Instagram)

1. **Wochenplan:** Ich erstelle jeden Montag `marketing/facebook/JJJJ-KW<nr>.md/.json` und trage jeden Beitrag in **`marketing/facebook/plan.json`** ein –
   im selben Format wie `marketing/instagram/plan.json` (`id`, `zeitpunkt`, `typ`, `dateien`, `caption`, `status: "geplant"`, Rückmeldefelder `post_id`, `gepostet_am`, `fehler`).
2. **Vorschau → Freigabe:** Sie sehen Bilder, Texte, Uhrzeiten. Erst nach **„Facebook freigeben“** werden die Einträge auf `freigegeben` gesetzt.
3. **Zu den Zeiten:** Eine geplante Aufgabe ruft das Posting-Skript auf (geplant: `marketing/facebook/posten.py --faellige`, noch nicht gebaut).
   Alternativ kann das Skript direkt nach der Freigabe alle Beiträge **bei Facebook vorplanen** (`scheduled_publish_time`) – dann sehen Sie sie
   in der Meta Business Suite unter „Geplant“ und können sie dort noch ändern oder löschen.
4. Ergebnis (Beitrags-ID, Zeit, Fehler) wird in `plan.json` zurückgeschrieben; verpasste Termine > 2 Stunden werden nicht nachgeholt; ein Beitrag wird nie doppelt gepostet.

## 4. Technik kurz (für das spätere Skript – aus der offiziellen Doku, v27.0)

- **Zugang:** Seiten-Token (Page access token) einer Person, die auf der Seite die Aufgabe `CREATE_CONTENT` ausführen darf
  (Pages-Posts-Leitfaden nennt zusätzlich `MANAGE` und `MODERATE`). Berechtigungen laut Foto-Referenz: `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`.
- **Ein Foto:** `POST https://graph.facebook.com/v27.0/{page-id}/photos` mit Datei (multipart, historisch Feldname `source`) **oder** `url` (öffentliche Bild-URL),
  Text im Feld `caption` (`message` ist bei Fotos laut Referenz veraltet). Antwort: `{"id": photo_id, "post_id": page_post_id}`.
- **Mehrere Fotos in einem Beitrag:** jedes Foto mit `published=false` hochladen (unveröffentlichte Fotos löscht Meta nach ca. 24 Stunden, also erst kurz vor dem Posten hochladen),
  dann `POST /{page-id}/feed` mit `message` und den zurückgegebenen IDs als `attached_media` (`[{"media_fbid": "…"}, …]`).
  Bei geplanten Mehrbild-Beiträgen müssen laut Referenz `published`, `scheduled_publish_time` und `unpublished_content_type` mitgegeben werden.
  *Das genaue Format von `attached_media` beim Bau des Skripts mit einem Testbeitrag (Seite im Entwurf/„nur ich“) prüfen.*
- **Text/Link:** `POST /{page-id}/feed` mit `message` und optional `link`. Antwort `{"id": page_post_id}`.
- **Vorplanen:** `published=false` + `scheduled_publish_time` (Unix-Zeit, ISO 8601 oder relativ). Zeitfenster: Der Pages-Leitfaden nennt
  **10 Minuten bis 30 Tage**, die Feed-Referenz **10 Minuten bis 75 Tage** – wir planen deshalb höchstens 30 Tage im Voraus.
- **Ändern/Löschen:** `POST /{page-post-id}` bzw. `DELETE /{page-post-id}` – nur für Beiträge, die unsere App erstellt hat.
- **Token-Handhabung:** wie bei Instagram – Umgebungsvariable (z. B. `FB_PAGE_TOKEN`), sonst Platzhalter, den der Sitzungs-Proxy ersetzt. Nie loggen.

## 5. Quellen (abgerufen am 25.11.2026)
- Pages API – Posts (Anforderungen, `/feed`, `/photos`, Planen 10 Min.–30 Tage, Einschränkungen): https://developers.facebook.com/docs/pages-api/posts
- Graph API Reference – Page Photos (Berechtigungen, `url`/Upload, `published`, `caption`, Mehrbild-Beiträge über `/feed`, 24-Stunden-Regel, Formate/10 MB): https://developers.facebook.com/docs/graph-api/reference/page/photos
- Graph API Reference – Page Feed (Planen 10 Min.–75 Tage, Berechtigungen): https://developers.facebook.com/docs/graph-api/reference/page/feed
- Pages API – Getting Started (`/me/accounts` liefert Seiten-Token, v27.0): https://developers.facebook.com/docs/pages-api/getting-started
- App mit Anwendungsfall „Manage everything on your Page“: https://developers.facebook.com/docs/pages-api/create-an-app
- Langlebige Token (Nutzer ca. 60 Tage, Seiten-Token ohne festes Ablaufdatum): https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived
- Zugriffsstufen (Standard-Zugriff für Nutzer mit App-Rolle, Advanced Access nur mit App Review + Unternehmensverifizierung): https://developers.facebook.com/docs/graph-api/overview/access-levels
- Groups API abgeschaltet (v19.0, alle Versionen ab 22.04.2024): https://developers.facebook.com/blog/post/2024/01/23/introducing-facebook-graph-and-marketing-api-v19/ und https://developers.facebook.com/docs/graph-api/changelog/version19.0/
- Page Stories API: https://developers.facebook.com/docs/page-stories-api
