# Projekt-Masterplan – Hausmeister Helden AI OS

Stand 25.11.2026 · Verantwortlich: Claude (CTO-Rolle) · Entscheidungen: Martin Ogur (Inhaber)

## 1. Bestandsaufnahme (vor dieser Ausbaustufe)

Das Repository bestand aus zwei Arbeitslinien. Der Branch `main` war fast leer. Die eigentliche
Arbeit lag auf `claude/ecstatic-euler-92wew4`. Dieser Stand wurde übernommen.

| Vorhanden | Bewertung |
|---|---|
| **Verwaltungsportal Phase 1+2** (Django 5.2 LTS, PostgreSQL 16, HTMX): Login mit Pflicht-2FA, Rollen admin/büro/mitarbeiter, Audit-Trigger, 28 Tabellen mit harten Regeln, Dashboard, Docker/Caddy, SOPS-Secrets, restic-Backups mit Restore-Test, Hetzner-Automatik | Solide und getestet (116 + 27 Tests). **Basis für alles Weitere.** |
| **Wachstumszentrale**: 14 Claude-Code-Agenten (`.claude/agents/`), 52 recherchierte Leads mit Quellen, druckfertige Briefe, Preiskalkulation (freigegeben 24.11.), Angebotsvorlagen, Instagram-/Facebook-Inhalte, Stellenanzeigen, Webseite auf GitHub Pages | Inhaltlich stark, aber nicht mit dem Portal verbunden (Dateien statt Daten). |
| Firmenprofil `firma/profil.md` | Preise freigegeben. Offen: Umkreis (jetzt 30 km), Haftpflicht, Kleinunternehmerregelung. |

**Was fehlte:** Agenten-Laufzeit mit Budgets und Grenzen, Freigabe-Warteschlange, Ereignisse und
Automatisierungen, Akquise-Pipeline in der Datenbank, Angebotskalkulation im System, Controlling
(Gewinn, Deckungsbeitrag, Angebotsquote, wiederkehrender Umsatz), Steuerungsoberfläche, mobile
Einsatzansicht mit Fotos, Clients für IONOS/HubSpot/Lexware/Make.

**Fressnapf Gütersloh (895 € netto/Monat):** Im Repository gibt es **keinen** Beleg für Angebot oder Auftrag.
Der Datensatz ist als Lead mit Status „Angebot“ angelegt (`INH-001`), nicht als Kunde. Wiedervorlage:
Status klären.

## 2. Architekturentscheidung: Django statt Next.js/Supabase

Der Projektauftrag nennt Next.js, TypeScript, Supabase und Vercel. Freigegeben und umgesetzt war bereits
**E1: Django + PostgreSQL + HTMX auf Hetzner (Deutschland)**. Ich habe die bestehende Architektur
**beibehalten** und nicht neu geschrieben. Die Gründe:

1. **Funktionsfähig und getestet.** Ein Neuschreiben hätte Wochen gekostet und keinen fachlichen Mehrwert gebracht.
2. **Eine Laufzeitumgebung, eine Datenbank, eine Rechte-Logik.** Bei Next.js + Supabase wären Rechte auf RLS-Policies, Edge-Functions und Frontend verteilt.
3. **Regeln in PostgreSQL** (Freigabepflicht, UWG, Schleifenschutz) wirken unabhängig vom Frontend. Diesen Vorteil hätte Supabase auch, das Portal hat ihn bereits.
4. **EU-Hosting und Kosten:** Hetzner ca. 10–14 €/Monat, Daten in Deutschland. Vercel und Supabase sind US-Anbieter mit EU-Regionen und mehreren Verträgen.
5. **Die Claude API ist sprachunabhängig.** Das offizielle Python-SDK ist gleichwertig.

Bei einem späteren Wechsel bleibt die Datenbank nutzbar, denn `schema.sql` und die Erweiterungen sind
reines PostgreSQL. **Bitte bestätigen**, siehe Abschnitt 5.

## 3. Zielbild

```
Geschäftsführer ──entscheidet──▶ Freigabe-Warteschlange ◀──schlagen vor── 13 KI-Agenten
       │                                │                                     ▲
       └──── Dashboard / Controlling    └──Folgeaktion (intern)               │
                                                                    Automatisierungen
Ereignisse (DB-Trigger: neue Mail, Anfrage, Lead, Statuswechsel …) ──▶ (Ereignis/Zeitplan)
```

* **Das Portal ist die zentrale Steuerung** und für Kunden, Objekte, Aufträge, Einsätze, Personal und Leads führend.
* **HubSpot** bekommt Anfragen als Deals (Export), **Lexware** ist führend für Rechnungen und Zahlungen,
  **IONOS** für E-Mails. **Craftnote** entfällt voraussichtlich, weil das Portal Einsätze, Zeiten und Fotos selbst abdeckt (Entscheidung E9).
* Agenten arbeiten **regelbasiert** und werden durch die KI **verbessert**. Ohne API-Schlüssel oder bei erschöpftem Budget läuft alles weiter.

## 4. Was diese Ausbaustufe geliefert hat

| Paket | Inhalt | Nachweis |
|---|---|---|
| Datenbank 0003 | 11 Tabellen, 3 Sichten, Trigger für Ereignisse, Statusregeln, UWG-Regeln, Schleifenschutz | `portal/db/tests/test_betriebssystem.sql` |
| Fachlogik | Angebotskalkulation (trifft die Beispielobjekte 360/471/799 € exakt), Lead-Scoring A/B/C, Einsatzgebiet 30 km, zulässige Kontaktwege, Controlling | `vertrieb/tests`, `berichte/tests` |
| Agenten | 13 Agenten, 19 Aufgaben, Laufzeit mit Warteschlange, Budget, Schritt- und Zeitgrenzen, Backoff, Eskalation; Claude-Client mit Kostenprotokoll | `agenten/tests` (31 Tests) |
| Automatisierungen | 18 Abläufe aus der Automatisierungskarte | `AUTOMATION_MAP.md` |
| Oberfläche | Navigation mit 15 Bereichen, Freigaben, Agenten, Automatisierungen, Akquise, Angebotsrechner, Aufträge, Controlling, Marketing, mobile Einsatzansicht | `cockpit/tests` (27 Tests) |
| Integrationen | IONOS IMAP/SMTP, HubSpot-Deal, Lexware-Rechnungsentwurf und Statusabgleich, Make-Webhook | `integrationen/test_make.py`, `agenten/tests/test_ablaeufe.py` |
| Bestandsdaten | 52 Leads aus `leads/leads.csv` importierbar (inkl. Einladungsbelege E001–E015) | `vertrieb/tests/test_dienste.py` |

## 5. Entscheidungen für Martin (bitte beantworten)

| Nr. | Frage | Empfehlung |
|---|---|---|
| D1 | Architektur Django/Hetzner beibehalten statt Next.js/Supabase/Vercel? | **Ja** (siehe Abschnitt 2) |
| D2 | Hetzner-Server + Storage Box buchen (ca. 10–14 €/Monat)? | Ja, für Testbetrieb mit echten Daten |
| D3 | Anthropic-API-Schlüssel mit Ausgabenlimit (Vorschlag 30 €/Monat, intern 2 €/Tag) | Ja |
| D4 | Fressnapf: Wurde das Angebot über 895 €/Monat angenommen? Welcher Leistungsumfang? | Status im Portal nachtragen |
| D5 | IONOS-Postfach für den Abruf (eigenes Postfach `anfragen@` oder `info@`)? | Eigenes App-Passwort für `info@` |
| D6 | HubSpot weiter nutzen? (Das Portal hat jetzt eine eigene Pipeline; doppelte Pflege vermeiden) | HubSpot nur als Export-Ziel oder ganz weglassen |
| D7 | Lexware Tarif XL (+20 €/Monat) für die Rechnungsautomatik? | Erst ab ca. 10 Rechnungen/Monat |
| D8 | Craftnote kündigen, sobald die mobile Einsatzansicht im Alltag genutzt wird (E9)? | Ja, nach 4 Wochen Parallelbetrieb |
| D9 | Kleinunternehmerregelung (USt): Rechnungsentwürfe sind derzeit mit 19 % angelegt | Mit Steuerberater klären |

## 6. Grenzen (bewusst)

* Keine automatische Kaltakquise per E-Mail, keine automatisierten Anrufe, kein Scraping (§ 7 UWG, DSGVO).
* Keine Vertragsabschlüsse, Preise, Zahlungen oder Einstellungen durch Agenten.
* Lead-Recherche im Internet bleibt bei den Claude-Code-Agenten (`lead-finder`), mit Quelle für jeden Datensatz. Das Portal importiert die Ergebnisse.
