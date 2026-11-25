# Agenten-Architektur

Zwei Ebenen, klar getrennt:

| Ebene | Wo | Wofür |
|---|---|---|
| **Betriebs-Agenten** (dieses Dokument) | `portal/app/agenten/` im Portal-Server | Laufender Betrieb rund um die Uhr: E-Mails, Anfragen, Leads, Disposition, Qualität, Abrechnung, Redaktionsplan, Berichte, Überwachung |
| **Wachstums-Agenten** (Claude Code) | `.claude/agents/`, Regeln in `CLAUDE.md` | Kreativ- und Recherchearbeit im Repository: Lead-Recherche mit Quellen, Briefe, Webseite, Grafiken, Kampagnen. Die Ergebnisse (z. B. `leads/leads.csv`) importiert das Portal. |

## 1. Das Team (13 Agenten, 19 Aufgaben)

| Agent | Verantwortung | Aufgaben | Darf delegieren an | KI | Budget/Tag | Erfolgsmessung |
|---|---|---|---|---|---|---|
| **CEO-Orchestrator** `ceo` | Steuerung | `tagesstart` (verteilt Routinearbeit, Lagebild, Prioritäten), `wochenbericht` | alle | ja | 60 ct | Freigaben < 48 h, keine unbemerkten Fehler, Bericht Mo 7 Uhr |
| **Sales** `sales` | Kundengewinnung | `lead_bewerten` (Region, Score, A/B/C, Kontaktvorschlag), `wiedervorlagen` (Nachfassen) | angebot, lead_research | ja | 60 ct | Wiedervorlagen pünktlich, Kontaktquote A, Abschlussquote |
| **Lead-Research** `lead_research` | Recherche-Eingang | `lead_aufnehmen` (Pflicht-Quelle, Dublettenprüfung), `bestand_importieren` | sales | nein | – | qualifizierte Leads/Woche, 0 Dubletten |
| **Marketing** `marketing` | Strategie | `monatsplan` (saisonale Schwerpunkte) | social, seo | ja | 30 ct | Anfragen je Kanal |
| **Social Media** `social` | Instagram/Facebook | `wochenplan` (5 Posts, 3 Reels, 5 Stories mit Text, Bildidee, Hashtags) | – | ja | 60 ct | Plan jeden Do., Freigabequote, Reichweite |
| **SEO** `seo` | Lokale Sichtbarkeit | `google_beitraege` (1 Beitrag/Woche fürs Google-Profil) | – | ja | 20 ct | Beiträge/Woche, echte Bewertungen |
| **Kundenservice** `kundenservice` | E-Mails, Anfragen | `email_einordnen` (Anfrage/Bewerbung/Bestand/Spam), `anfrage_bearbeiten` (Zusammenfassung, fehlende Angaben, Antwortentwurf) | hr, angebot | ja | 80 ct | Entwurf < 15 min, Antwort < 24 h |
| **Angebot** `angebot` | Kalkulation | `angebot_berechnen` (Preisliste, Selbstkosten, Marge → Entwurf + Freigabe) | – | nein | – | Marge ≥ Ziel, Angebotsquote |
| **Disposition** `dispatch` | Einsatzplanung | `einsatz_planen` (Termin + Personalvorschlag), `wiederkehrende_einsaetze` (14 Tage voraus) | – | nein | – | keine ungeplanten Einsätze < 48 h |
| **HR** `hr` | Bewerbungen | `bewerbung_aufnehmen` (neutrale Zusammenfassung, Eingangsbestätigung) | – | ja | 30 ct | Bestätigung < 24 h, Löschfristen |
| **Finanzen** `finance` | Abrechnung | `abrechnung_vorbereiten` (Rechnungsentwurf), `zahlungen_pruefen` (Fälligkeiten) | – | nein | – | Rechnung < 3 Tage, Forderungslaufzeit |
| **Qualität** `quality` | Auftragsqualität | `auftrag_pruefen` (Fotos vorher/nachher, Bericht, bestätigte Zeiten, DB) | – | nein | – | Anteil vollständig dokumentierter Aufträge |
| **Automation** `automation` | Überwachung | `ueberwachung` (Fehler in Folge, Ereignis-Stau, hängende Aufträge, KI-Budget ≥ 80 %) | – | nein | – | Ausfälle < 1 h gemeldet |

Budget, Grenzen und „aktiv“ stehen in der Tabelle `agenten`. Dort sind sie führend und im Admin bzw. unter
„KI-Agenten“ änderbar. `agenten_sync` legt nur fehlende Agenten an und überschreibt keine Betriebswerte.

## 2. Werkzeuge und Zugriffskontrolle

Agenten haben **keinen** freien Datenbank- oder Netzwerkzugriff und **keine** freie Werkzeugauswahl durch die KI.
Jede Aufgabe ist eine Python-Funktion. Sie nutzt nur die Fachdienste ihres Bereichs (z. B. `vertrieb.dienste`,
`auftraege.status`) und den Kontext `ctx`:

| `ctx`-Funktion | Wirkung | Grenze |
|---|---|---|
| `ctx.ki(...)` / `ctx.ki_oder_regel(...)` | Strukturierte Antwort von Claude (JSON-Schema) bzw. regelbasierter Ersatz | Budget je Agent + gesamt, zählt als Schritt, Restlaufzeit als Timeout |
| `ctx.delegieren(agent, aufgabe)` | Unterauftrag | nur erlaubte Ziele, DB-Schleifenschutz |
| `ctx.freigabe_anfordern(...)` | Vorschlag an den Geschäftsführer | eine offene Freigabe je Bezug |
| `ctx.protokoll(...)` | Eintrag im Agenten-Protokoll | nur anfügen |
| `ctx.schritt(...)` | Zählt Schritte, prüft die Laufzeit | `max_schritte`, `max_laufzeit_sekunden` |

**Kein Agent kann:** E-Mails senden, Briefe verschicken, posten, Rechnungen festschreiben, Preise verbindlich machen,
Verträge schließen, Personal einstellen oder bewerten. Versand geschieht nur für freigegebene Datensätze durch die
Integrationsjobs. Das sichern Datenbank-Regeln ab.

## 3. Laufzeit (`agenten/laufzeit.py`)

```
wartend ──holen() [FOR UPDATE SKIP LOCKED]──▶ läuft ──Erfolg──▶ erledigt
   ▲                                            ├─ Fehler, Versuche übrig ─▶ wartend (+2^n Min.)
   └──────── Budget erschöpft (bis 06:00) ◀─────┤─ Fehler, keine Versuche ─▶ fehlgeschlagen + Eskalation
                                                ├─ Schritt-/Zeitgrenze ─────▶ fehlgeschlagen + Eskalation
                                                └─ Eskalation (Entscheidung nötig) ─▶ eskaliert + Freigabe
```

* **Transaktion je Aufgabe:** Bei einem Fehler wird alles zurückgerollt. **Die KI-Kosten bleiben erhalten**, sie werden nach dem Rollback nachgetragen, sonst wäre das Budget umgehbar.
* **Hängende Aufträge** (Sperrzeit abgelaufen) nimmt der nächste Lauf wieder auf.
* **Mehrere Worker** sind möglich (SKIP LOCKED).
* **Idempotenz:** Automatisierungen und Tagesroutinen vergeben Schlüssel (`ereignis:<id>:…`, `zeitplan:<code>:<Fenster>`).

## 4. Schutz vor Endlosschleifen

1. **Delegationsrechte** im Code (`darf_delegieren_an`), geprüft vor dem Anlegen.
2. **Datenbank-Trigger** `agenten_auftraege_kette`: Tiefe ≤ 3, dieselbe Agent+Aufgabe darf in einer Kette nicht erneut vorkommen, max. 20 Aufträge je Kette.
3. **Schritt- und Zeitgrenzen** je Agent. Bei Überschreitung wird nicht wiederholt, sondern eskaliert.
4. **Ereignisse lösen nur einmal aus**: ein erfolgreicher Lauf je Automatisierung und Ereignis.

## 5. KI-Nutzung (`agenten/ki.py`)

* Offizielles Python-SDK, Modell **Claude Opus 5.5** (`claude-opus-5-5`), **Structured Outputs** (JSON-Schema),
  serverseitiger Fallback bei Ablehnungen (`fallbacks="default"`), `effort` je Zweck (Routine `low`, Bericht `medium`).
* Prüfungen: Ablehnung (`refusal`), abgeschnittene Antwort, ungültiges JSON, fehlende Schemafelder ⇒ `KiFehler` ⇒ regelbasierter Ersatz.
* Jeder Aufruf steht in `ki_aufrufe` mit Agent, Auftrag, Tokens und Kosten (Preise 11/2026: 4 $ / 20 $ je Mio. Tokens).
* **Datensparsamkeit:** Es geht nur der für die Aufgabe nötige Text an die API (E-Mail-Auszug, Lead-Kurzdaten). Keine Lohn- oder Gesundheitsdaten, keine Bewertung von Bewerbern.
* **Warum kein freier Tool-Loop?** Die Abläufe sind bekannt und rechtlich sensibel. Ein Code-gesteuerter Ablauf mit
  strukturierten KI-Antworten ist vorhersehbar, testbar und günstig. Ein offener Agenten-Loop (z. B. Claude Managed
  Agents) lohnt sich erst für offene Rechercheaufgaben. Die erledigen heute die Claude-Code-Agenten.

**Kostenschätzung** (10 E-Mails/Tag, wöchentlicher Social-Plan, Wochenbericht): ca. 0,3 € pro Tag, also **≈ 10 € im Monat**.
Harte Obergrenze: `ki_tagesbudget_gesamt_cent` = 200 (2 €/Tag) plus das Ausgabenlimit im Anthropic-Konto.

## 6. Eskalation

| Auslöser | Ergebnis |
|---|---|
| Aufgabe wirft `Eskalation` (z. B. kein verfügbarer Mitarbeiter, kein Preis für Rechnung) | Status `eskaliert`, Freigabe „Entscheidung/Eskalation“ (hoch) |
| Letzter Versuch gescheitert, Schritt- oder Zeitgrenze | `fehlgeschlagen`, Eskalation mit Fehlertext |
| Ereignis 5× nicht verarbeitbar | Alarm-Eskalation |
| Automatisierung ≥ 3 Fehler in Folge, Ereignis-Stau > 30 min, KI-Budget ≥ 80 % | Überwachungsagent meldet stündlich |

Alle Eskalationen erscheinen unter **Freigaben** und im Tagesbriefing des CEO-Agenten.
