# API-Integrationen

Alle Clients: `portal/app/integrationen/`. Nur Standardbibliothek (urllib, imaplib, smtplib), Zugangsdaten aus
Umgebungsvariablen. Fehlen sie, meldet die Integration „nicht eingerichtet“ (kein Fehler, kein Alarm). Jeder Aufruf
steht in `sync_protokoll`. Endpunkte wurden am 25.11.2026 in der offiziellen Dokumentation geprüft. Erfundene Funktionen gibt es nicht.

| System | Rolle | Code | Status | Benötigt vom Inhaber | Kosten |
|---|---|---|---|---|---|
| **IONOS E-Mail** | Eingang/Ausgang | `ionos.py` | ✅ fertig, mit Fake-Server getestet | Postfach + Passwort (D5) | vorhanden |
| **Claude API** | KI-Texte, Einordnung, Berichte | `agenten/ki.py` | ✅ fertig, mit Fake-SDK getestet | API-Schlüssel mit Limit (D3) | ≈ 10 €/Monat, max. 60 € |
| **HubSpot** | CRM-Export neuer Anfragen | `hubspot.py` | ✅ fertig | Private-App-Token, Pipeline-/Stage-IDs (D6) | Free-Tarif genügt |
| **Lexware Office** | Rechnungsentwurf, Zahlungsstatus | `lexware.py` | ✅ fertig, Pflichtfelder getestet | Tarif XL + API-Schlüssel (D7) | +20 €/Monat |
| **Make** | eingehende Anfragen (Formular/WhatsApp) | `make.py` | ✅ fertig, getestet | Token setzen, Szenario in Make bauen | vorhandener Tarif |
| **Craftnote** | Einsatzplanung (bisher) | – | ⏸ bewusst nicht angebunden | Entscheidung E9/D8 | entfällt nach Ablösung |
| **Instagram** | Veröffentlichung | `marketing/instagram/posten.py` (Bestand) | vorhanden (Wachstumszentrale) | Instagram-Token | 0 € |

## IONOS (IMAP/SMTP)

* Server laut Vorgabe: `imap.ionos.de:993` (SSL), `smtp.ionos.de:465` (SSL). Variablen `IONOS_MAIL_BENUTZER`, `IONOS_MAIL_PASSWORT`.
* Abruf: `UID SEARCH SINCE <7 Tage>` + `BODY.PEEK[]` (Mails bleiben ungelesen), Speichern von Absender, Empfänger, Betreff,
  Textauszug (8.000 Zeichen), Datum, Message-ID. Doppelimport verhindert der eindeutige Index `(postfach, message_id)`.
* Versand: nur `richtung=ausgang`, `status=freigegeben`, `freigegeben_von` gesetzt; setzt `Message-ID`, `In-Reply-To`/`References`.
  Fehler → Status `fehler` mit Text, sichtbar in E-Mails und Überwachung.
* *Offen:* Anhänge (als Dokument speichern), HTML-Mails (derzeit nur Text-Teil).

## Claude API (Anthropic)

* SDK `anthropic==2.8.0`, `client.beta.messages.create` mit `output_config.format` (JSON-Schema), `effort`,
  `betas=["server-side-fallback-2026-07-01"]`, `fallbacks="default"`. Modell `claude-opus-5-5`.
* Preise (11/2026): 4 $ Eingabe / 20 $ Ausgabe je Mio. Tokens; Cache-Lesen 0,20 $. Kostenberechnung in `ki.kosten_cent`.
* Variable `ANTHROPIC_API_KEY`. Fehlt sie, arbeiten alle Agenten regelbasiert.

## HubSpot

* `POST https://api.hubapi.com/crm/v3/objects/deals`, `Authorization: Bearer <Private-App-Token>`, Body
  `{"properties": {"dealname", "pipeline", "dealstage", "description"}}`. `dealstage` ist die **interne** ID der Stufe.
* Variablen `HUBSPOT_TOKEN`, `HUBSPOT_PIPELINE` (Standard `default`), `HUBSPOT_DEALSTAGE_NEU`.
* Idempotent über `anfragen.hubspot_deal_id`.
* *Empfehlung:* Da das Portal jetzt eine eigene Pipeline hat, HubSpot nur weiterführen, wenn es aktiv genutzt wird (D6).

## Lexware Office (Public API)

* Basis `https://api.lexware.io`, `Authorization: Bearer <API-Key>`, **max. 2 Anfragen/s** (429 sonst).
* `POST /v1/invoices` legt einen **Entwurf** an (ohne `?finalize=true`, das nutzen wir nie). Pflichtfelder: `voucherDate`,
  `address` (`name`, `countryCode`), `lineItems` (`type: custom`, `name`, `quantity`, `unitName`,
  `unitPrice{currency, netAmount, taxRatePercentage}`), `totalPrice{currency}`, `taxConditions{taxType}`,
  `shippingConditions{shippingType, shippingDate}`.
* `GET /v1/invoices/{id}` → `voucherStatus` `draft | open | paid | voided` → Portal `entwurf | offen | bezahlt | storniert`.
* Nur ab **Tarif XL** (laut `firma/profil.md`: aktuell M). Bis dahin: Freigegebener Entwurf wird von Hand in Lexware angelegt.

## Make

* `POST /api/make/anfrage`, Header `X-HH-Token`, JSON `name` (Pflicht), `email`, `telefon`, `plz`, `ort`, `nachricht`,
  `leistungen[]`, `kanal`, `referenz` (für Wiederholungen). Antwort `201 {anfrage_id, anfragenummer}`.
* Legt Interessent + Anfrage an. Das Ereignis `anfrage.neu` startet den Kundenservice-Agenten.
* Make-Szenario-Vorschlag: Webseiten-Formular / WhatsApp Business → HTTP-Modul „Make a request“ mit obigem Body.

## Craftnote

Nicht angebunden. Das Portal deckt Einsatzplanung, Zeiterfassung, Fotos und Berichte mobil ab. Eine Synchronisation
würde doppelte Pflege erzeugen. Bei Bedarf (E9 „beibehalten“): Craftnote REST-API mit API-Key (Dokumentation
`github.com/craftnote/api-doc`), Export Objekt → Projekt, Einsatz → Aufgabe über die vorhandenen Felder
`objekte.craftnote_project_id`, `einsaetze.craftnote_task_id`.
