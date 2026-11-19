# HausManager

Eine App für zwei Aufgaben:

1. **Eigene Immobilien automatisch verwalten**: Mieten, Zahlungseingänge, Mahnungen, Fristen und Reparaturen
2. **Hausmeister Helden: mehr Aufträge**: automatische Anschreiben an Hausverwaltungen, Nachfass-Sequenz, Angebote und eine Website mit Anfrageformular

Technik: Python + Flask + SQLite. Alles läuft lokal oder auf einem kleinen Server, ohne Abo und ohne Cloud-Zwang.

---

## Schnellstart

```bash
pip install -r requirements.txt
cp .env.example .env          # Passwort + E-Mail-Zugang eintragen
python -m hausmanager.demo    # optional: Beispieldaten zum Ausprobieren
python -m hausmanager.app     # → http://localhost:5000
```

Unter **Einstellungen** trägst du Firmendaten, IBAN und Fristen ein. Die Daten liegen in `data/hausmanager.db`. Sichere diese Datei regelmäßig.

### Automatik täglich laufen lassen

Im Dashboard gibt es den Button **⚡ Automatik jetzt ausführen**. Damit alles von selbst passiert, richtest du einen Cronjob ein (Linux/Mac):

```cron
0 7 * * *  cd /pfad/zu/HausManager && python3 -m hausmanager.automation >> data/automatik.log 2>&1
```

Unter Windows geht das über die Aufgabenplanung mit demselben Befehl.

---

## Modul 1: Eigene Immobilien

| Was | Wie es automatisch läuft |
|---|---|
| **Mietforderungen** | Für jeden Vertrag wird jeden Monat die Soll-Miete (kalt + NK) erzeugt. |
| **Zahlungseingänge** | Kontoauszug als CSV aus dem Online-Banking hochladen. Zahlungen werden über den Mieternamen erkannt und auf die ältesten offenen Monate verbucht. Doppelte Importe werden ignoriert. |
| **Mahnwesen** | Nach 7 Tagen Verzug wird eine freundliche Zahlungserinnerung erstellt, nach 21 Tagen eine Mahnung (Tage einstellbar). Hat der Mieter eine E-Mail-Adresse, geht sie per Mail raus, sonst als Brief an die Wohnung. Zahlt der Mieter vorher, wird der Entwurf automatisch verworfen. |
| **Rückstand ≥ 2 Monatsmieten** | Warnung als Aufgabe (Kündigungsgrund nach § 543 BGB prüfen). |
| **Mieterhöhung** | Erinnerung, sobald eine Erhöhung nach § 558 BGB wieder möglich ist (15 Monate nach der letzten). |
| **Vertragsende** | Aufgabe 90 Tage vorher (Übergabe und Nachvermietung planen). |
| **Tickets** | Reparaturen erfassen. Dringende Tickets, die länger als 2 Tage offen sind, landen als Aufgabe im Dashboard. |
| **Kennzahlen** | Soll/Ist im Monat, offene Posten, Leerstand, Bruttomietrendite. |

## Modul 2: Hausmeister Helden, Akquise

**Ablauf:**

1. **Leads sammeln**: Hausverwaltungen, WEG-Verwalter, Genossenschaften und Wohnungsbaugesellschaften. Am schnellsten per CSV (Vorlage: `beispiele/leads_vorlage.csv`).
   Gute Quellen sind Google Maps („Hausverwaltung + Stadt“), Gelbe Seiten, das Impressum auf den Verwaltungs-Websites und die Mitgliederlisten der VDIV-Landesverbände.
2. **Die Automatik schreibt an**, in 3 Stufen:
   - Schritt 1: Vorstellung mit Angebot eines **kostenlosen Objekt-Checks**
   - Schritt 2 (nach 7 Tagen): kurzes Nachfassen
   - Schritt 3 (nach weiteren 14 Tagen): letzter Impuls
   - Nach 30 Tagen ohne Reaktion: Wiedervorlage in 6 Monaten
   - Zu jedem Lead mit Telefonnummer gibt es **Anruf-Aufgaben**.
3. **Postausgang**: Alle Briefe druckst du mit einem Klick als Serienbrief (DIN 5008, passend für Fensterkuverts). E-Mails gehen nach Freigabe raus, oder automatisch, wenn du das in den Einstellungen aktivierst.
4. **Reaktion?** Setze den Status auf „interessiert“. Die Sequenz stoppt dann, und es entsteht eine Aufgabe „Objekt-Check + Angebot“.
5. **Angebot erstellen**: Positionen eintragen, die App rechnet und gibt ein druckfertiges PDF-Angebot aus. Nach 7 Tagen kommt eine Nachfass-Aufgabe.
6. **Website** unter `/helden`: Landingpage mit Anfrageformular. Jede Anfrage wird automatisch als Lead angelegt, bekommt eine Eingangsbestätigung per Mail und erscheint sofort als 🔥-Aufgabe (optional auch als Benachrichtigung per Mail).

Alle Texte kannst du in `hausmanager/vorlagen.py` anpassen. Einzelne Entwürfe lassen sich im Postausgang auch vor dem Senden bearbeiten.

### ⚖️ Wichtig: Werbung per E-Mail (UWG § 7)

Werbe-E-Mails ohne vorherige ausdrückliche Einwilligung sind in Deutschland **auch an Firmen** unzulässig und können abgemahnt werden. Deshalb arbeitet die App so:

- **E-Mail** nur, wenn beim Lead „Einwilligung liegt vor“ angehakt ist
- **sonst Brief**: Briefwerbung an Firmen ist erlaubt
- **Telefon**: Anrufe bei Gewerbetreibenden sind bei *mutmaßlicher Einwilligung* zulässig. Bei Hausverwaltungen, die regelmäßig Hausmeisterdienste vergeben, wird das in der Regel angenommen.

Das ist keine Rechtsberatung. Bei Unsicherheit lass es kurz prüfen.

---

## Online stellen (Website + Zugriff vom Handy)

- Setze in `.env` unbedingt `ADMIN_PASSWORT`. Danach ist alles außer `/helden` passwortgeschützt.
- Die Seite läuft z. B. auf einem kleinen VPS (Hetzner, IONOS) mit `gunicorn -w 2 -b 127.0.0.1:5000 hausmanager.app:app` hinter Caddy oder nginx (HTTPS).
- Die Landingpage braucht **Impressum und Datenschutzerklärung**. Die Links im Footer von `templates/landing.html` müssen noch befüllt werden.

## Tests

```bash
pip install pytest
python -m pytest
```

## Ideen für später

- Nebenkostenabrechnung je Objekt (Umlageschlüssel nach Fläche)
- Dokumentenablage (Verträge, Protokolle) je Einheit
- Bank-Anbindung per FinTS/HBCI statt CSV-Import
- Mieter-Portal für Schadensmeldungen, die direkt als Ticket ankommen
- Einsatzprotokolle mit Fotos für Hausmeister-Kunden
