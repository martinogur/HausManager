# Bericht facebook-manager – 25.11.2026 (erste Runde)

## Was wurde gemacht
1. **`marketing/facebook/seite.md`** – komplettes Seiten-Setup zum Kopieren (Name, Kategorie, Nutzername-Vorschlag, Steckbrief, Info-Text,
   Kontakt, Öffnungszeiten, Einzugsgebiet, Aktions-Button, Impressum-Pflicht), Schritt-für-Schritt-Anleitung zum Anlegen,
   Verknüpfung mit Instagram und WhatsApp, Regeln.
2. **Titelbild** `marketing/facebook/grafiken/titelbild.png` (1640 × 624). `grafik.py` kann nur feste Instagram-Formate, deshalb neues kleines
   Skript **`marketing/facebook/titelbild.py`** (nutzt Schriften/Farben/`render()` aus `grafik.py`). Gerendert und angesehen; alles Wichtige
   liegt im Handy-Ausschnitt (Kontrollbild `titelbild-raster.png`, nicht hochladen).
3. **`marketing/facebook/2026-KW48.md`** – 3 Beiträge (Do 26.11. 18:30 Winterdienst-Pflichten mit Ratgeber-Link · Sa 28.11. 10:00 Winterdienst-Preis ·
   So 29.11. 17:00 Ablauf/1. Advent, zum Anpinnen). Texte in „Sie“, lokal (Stadtteile, Frost, Satzung), mit klarer Handlung.
   Die Instagram-Grafiken sagen „du“ – deshalb **Facebook-Fassung in „Sie“ neu gerendert** über `marketing/facebook/2026-KW48.json`
   → `marketing/facebook/grafiken/2026-KW48/…` (16 Bilder, geprüft). Ratgeber-Link geprüft: Seite ist live (HTTP 200).
4. **`marketing/facebook/gruppen.md`** – Recherche lokaler Gruppen. Ehrliches Ergebnis: **keine Gütersloher Gruppe mit überprüfbarem Link**
   per Websuche auffindbar (Facebook-Gruppen sind kaum indexiert). Aufgeführt: 3 Gruppennamen aus älteren NW-Artikeln (als ungeprüft markiert),
   5 öffentliche Gütersloher Seiten mit belegtem Link, Suchanleitung für den Inhaber, Tabelle zum Ausfüllen, feste Gruppen-Regeln + Antwortvorlage für Empfehlungsfragen.
5. **`marketing/facebook/automatisch-posten.md`** – aktuelle offizielle Meta-Doku (Graph API v27.0) ausgewertet: Foto-/Mehrbild-/Link-Beiträge,
   Vorplanen, Berechtigungen (`pages_manage_posts`, `pages_read_engagement`, `pages_show_list`), App mit Anwendungsfall „Manage everything on your Page“,
   kein App Review nötig (Standard-Zugriff), langlebiger Seiten-Token, Groups API abgeschaltet. Einrichtung Schritt für Schritt, mit Quellen.

Nichts wurde veröffentlicht, nichts committet.

## Was braucht Freigabe
- Seiten-Texte (`seite.md`) und Titelbild.
- Die 3 Beiträge der KW 48 (Texte + Sie-Grafiken).
- Antwortvorlage für Empfehlungsfragen in Gruppen (`gruppen.md`).

## Fragen an den Inhaber
1. Gibt es schon eine Facebook-Seite? Wenn nein: Bitte nach `seite.md` anlegen und den Link schicken (Eintrag in `firma/profil.md`).
2. Nutzername: `hausmeisterhelden.gt` o. ä. – zusammen mit dem Instagram-Handle festlegen (Facebook erlaubt keinen Unterstrich).
3. Kunden an der Adresse Auf der Benkert 68? (Adresse anzeigen oder nur Einzugsgebiet)
4. Einzugsgebiet 25 km bestätigen (Rietberg, Bielefeld dazu?).
5. Klappt die WhatsApp-Verknüpfung mit der Festnetznummer? Sonst Button „Jetzt anrufen“.
6. Bitte in Facebook selbst 10 Minuten nach Gütersloher Gruppen suchen (Anleitung `gruppen.md`, Abschnitt C) und Links schicken – ich prüfe die Regeln.
7. Automatisches Posten gewünscht? Dann Meta-App nach `automatisch-posten.md` anlegen; Token/App-Geheimnis nur über das sichere Formular.
8. Datenschutzerklärung der Webseite um die Facebook-Seite ergänzen (Art. 26 DSGVO) – vom Berater prüfen lassen.

## Nächste Schritte
- Nach Freigabe: Beiträge in der Meta Business Suite planen (von Hand) oder – nach Token – `marketing/facebook/plan.json` + `posten.py` bauen und testen.
- Ab nächster Woche jeden Montag 2–3 Beiträge aus dem Instagram-Wochenplan (Sie-Fassung).
