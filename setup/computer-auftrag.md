# Auftrag für Claude auf dem Computer des Inhabers

So startest du ihn:
1. Öffne auf deinem Computer die **Claude-Desktop-App**.
2. Starte eine neue Aufgabe und erlaube „Computer verwenden“ bzw. den Browser.
3. Kopiere den Text unten (ab „Du arbeitest für …“) hinein.

Passwörter und Bestätigungscodes gibst du selbst ein. Claude fragt dich, wenn ein Login nötig ist.

---

Du arbeitest für Martin Ogur, Inhaber von **Hausmeister Helden** (Gütersloh). Bediene meinen Browser, um die folgenden Punkte einzurichten. Ich bin am Computer und gebe Logins, Passwörter und Bestätigungscodes selbst ein. Frag mich jeweils, wenn du an einer Login-Seite ankommst. Gib keine Zahlungsdaten ein, kauf nichts und schließe keine Verträge ab, ohne mich vorher konkret zu fragen. Lösch nichts in meinem IONOS-Konto.

Alle Unterlagen liegen im GitHub-Repository **martinogur/HausManager** auf dem Branch **claude/ecstatic-euler-92wew4**. Lade es als ZIP herunter: auf github.com einloggen, Repository öffnen, Branch wählen, dann „Code“ und „Download ZIP“. Danach entpacken.

## Teil 1: Webseite online stellen – ERLEDIGT am 24.11.2026 (über GitHub Pages statt Deploy Now, diesen Teil überspringen)
Anleitung: `webseite/README.md`, Abschnitt „Einmalig einrichten: IONOS Deploy Now“.
1. Melde dich bei IONOS an (my.ionos.de). Das Login mache ich.
2. Öffne **Deploy Now** und lege ein neues Projekt an. Verbinde GitHub und wähle das Repository `martinogur/HausManager`.
3. Einstellungen:
   - statische Seite, kein Framework
   - Build-Befehl leer
   - Veröffentlichungsordner `webseite/public`
   - Produktions-Branch **`webseite-live`**
4. Zeig mir vor dem Bestätigen, ob dafür Kosten entstehen. Frag mich und warte auf mein Ja.
5. Verbinde nach dem ersten erfolgreichen Deployment unter „Domain verbinden“ `haus-meister-helden.de` und `www.haus-meister-helden.de`. Achtung, das ersetzt die alte Baukasten-Seite. Frag mich vorher.
6. Prüfe danach https://www.haus-meister-helden.de. Es muss die neue Seite sein, mit dem Preisrechner mit Treppenhäusern und Etagen.
7. Melde Erfolg oder Problem mit Screenshot.

## Teil 2: Instagram-Profil fertigstellen
Anleitung: `marketing/instagram/profil.md`, Abschnitt 7 „In 15 Minuten einrichten“.
1. Öffne instagram.com bzw. die Einstellungen. Das Login mache ich.
2. Stelle auf ein **professionelles Konto (Unternehmen)** um, Kategorie laut Anleitung.
3. Trage Name, Bio, Links und Kontakt-Buttons exakt aus der Anleitung ein. Instagram-Name und Handle fragst du mich.
4. Verbinde eine Facebook-Seite. Falls keine existiert, lege mit mir zusammen eine an: Name „Hausmeister Helden“, Kategorie Hausmeisterservice.

## Teil 3: Beiträge einplanen (Meta Business Suite)
Anleitung: `marketing/instagram/automatisch-posten.md`, Weg 1. Fertige Grafiken: `marketing/instagram/grafiken/2026-KW48/`, Captions in `marketing/instagram/2026-KW48.md`.
1. Öffne business.facebook.com und dann den **Planer**.
2. Plane die Beiträge der Woche mit Caption, Hashtags und Uhrzeit wie im Plan ein. Karussells mit allen Folien in der richtigen Reihenfolge, das Reel als `reel.mp4`.
3. Lade die Highlight-Cover aus `00-highlight-cover/` hoch, falls die Anleitung das vorsieht.
4. Zeig mir zum Schluss die Liste der eingeplanten Beiträge.

## Teil 4 (nur nach meinem ausdrücklichen Okay): Werbekampagne
Anleitung: `marketing/instagram/werbung/kampagne.md`. Lege die Kampagne **als Entwurf** an und veröffentliche sie nicht. Zahlungsdaten und Budget bestätige ich selbst.

## Zum Schluss
Schreib eine kurze Zusammenfassung: was eingerichtet ist, was noch fehlt, und die Instagram-Handle- und Facebook-Seiten-URL. Diese Zusammenfassung gebe ich an meine Claude-Sitzung zurück.
