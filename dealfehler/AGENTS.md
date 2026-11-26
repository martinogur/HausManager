# Agenten

Alle Agenten arbeiten ausschließlich über die zentrale Deal-Datenbank zusammen (kein direkter Aufruf
untereinander). Jeder Lauf wird in `agent_runs` protokolliert; Agenten lassen sich im Dashboard einzeln
pausieren, manuell starten und ihre Protokolle einsehen.

| # | Agent (Code-Name) | Datei | Takt | Aufgabe |
|---|---|---|---|---|
| 1 | **Master / CEO** (`master`) | `agents/master.py` | 10 min | Führt die Pipeline-Agenten der Reihe nach aus, beachtet den globalen Not-Aus, meldet Agenten mit Fehlerserien, protokolliert KI-Kosten, erstellt den Tagesbericht |
| 2 | **Deal Hunter** (`deal_hunter`) | `agents/pipeline.py` | im Master | Holt Kandidaten aus Keepa (Deals-Endpunkt: starke Preisstürze 24 h) bzw. CSV-Feeds, speichert Produkte + Preisverlauf, legt Deals an; Duplikatsperre per Fingerabdruck |
| 3 | **Preisfehler Hunter / Preisprüfer** (`price_checker`) | `agents/pipeline.py`, `domain/scoring.py` | im Master | Score 0–100 gegen eigene Historie; < 50 → abgelehnt; erneute Preisprüfung (≥ 10 min Abstand); ab Score 85 zwei Verifikationen; Alarm bei Treffern ≥ 85 |
| 4 | **Affiliate-Link** (`affiliate`) | `agents/pipeline.py`, `domain/affiliate.py` | im Master | Amazon-Links `/dp/ASIN?tag=…` je Kanal-Tracking-ID, Strukturprüfung, eindeutig je Deal × Kanal; ohne Partner-Tag wird blockiert + gewarnt |
| 5 | **Creative** (`creative`) | `agents/pipeline.py`, `creative/` | im Master | 3 Formate (Post 4:5, Story 9:16, Pin 2:3) × 4 Vorlagen; Vorlagenwahl per Epsilon-Greedy aus gelernten Gewichten; Texte je Kanal; Reel-Video (ffmpeg) verfügbar |
| 11 | **Compliance** (`compliance`) | `agents/pipeline.py`, `domain/compliance.py` | im Master + vor jeder Veröffentlichung | Kennzeichnung, Partner-Hinweis, Preisalter, Zeitstempel, „Preisfehler“-Wording, Rabatt belegt, Dringlichkeit, Bildlizenz, Preis in Grafik, Demo-Daten, Textlängen, Hashtags |
| – | **Master-Priorisierung** (`prioritizer`) | `agents/publishing.py` | im Master | Erwarteter Wert = Score × gelernte Kategorie-Gewichtung × Provisionspotenzial × Frische × Nachfrage |
| – | **Scheduler** (`scheduler`) | `agents/publishing.py`, `domain/frequency.py` | im Master | Verteilt Entwürfe in freie Slots je Plattform (Mindest-Score, Tageslimit, Abstand, Ruhezeit, Wiederholungssperre); WhatsApp → wartet auf Freigabe |
| 6–9 | **Plattform-Agenten** (`publisher`) | `agents/publishing.py`, `publishers/` | 1 min | Instagram (Graph API), Pinterest (API v5, Boards automatisch), Telegram (Bot API), Website; WhatsApp manuell. Vorher: Not-Aus/Limits, Preis-Nachprüfung, Compliance |
| – | **Preisüberwachung** (`price_watch`) | `agents/publishing.py` | 15 min | Prüft freigegebene/geplante/veröffentlichte Deals; Preisänderung → Beiträge pausiert, Deal zurück in Prüfung; Angebot weg → abgebrochen |
| 10 | **Growth & Umsatz** (`growth`) | `agents/growth.py` | täglich 04:17 | Klicks je Kanal/Kategorie/Vorlage/Stunde, Provisionen je Kategorie; lernt Gewichte erst ab 20 Beiträgen; Vorschläge; Frequenzausbau max. 1×/Woche bei 0 % Fehlern und ≥ 1 Klick/Beitrag |

## Pipeline je Deal

1. Deal Hunter findet Produkt → `neu`
2. Preisprüfer bewertet → `in_pruefung` (oder `abgelehnt`)
3. Erneute Preisprüfung → `verifiziert`
4. Affiliate-Agent ordnet Links zu
5. Creative erzeugt Medien + Entwürfe → `medien_werden_erstellt`
6. Compliance prüft jeden Entwurf → `freigegeben` (oder `fehlerhaft`)
7. Master priorisiert
8. Scheduler plant → `geplant`
9. Publisher veröffentlicht nach erneuter Preis- und Compliance-Prüfung → `veroeffentlicht`
10. Growth wertet aus; Preisüberwachung pausiert/korrigiert bei Änderungen

## Score-Logik (Preisfehler Hunter)

| Komponente | Punkte |
|---|---|
| Preissturz ggü. Median 90 T. (ohne letzte 24 h): 15 % → 0, 75 % → 45 | 0–45 |
| Robuste Anomalie (Median/MAD-z-Wert) | 0–20 |
| Unter 90-Tage-Tiefstpreis | 0–10 |
| Abweichung zu unabhängigen Quellen (z.B. Drittanbieter-Neupreis) | 0–15 |
| Verifikationen (je 5, max. 2) | 0–10 |
| Produktqualität (Bewertung) | −8 … +3 |

Deckel: < 5 Messpunkte oder < 14 Tage Historie → max. 74 · nur UVP als Referenz → max. 55 · < 10 % Rabatt → max. 30 ·
90+ nur mit ≥ 2 Verifikationen. Labels: 90–100 Preisfehler-Verdacht, 75–89 Top-Deal, 50–74 Deal, < 50 nicht veröffentlichen.

## Sicherheitsmechanismen

* Globaler Not-Aus (stoppt Pipeline und Veröffentlichungen) + Not-Aus je Plattform; Aufheben nur durch Admin.
* Plattformen sind standardmäßig **deaktiviert** (außer Website). Aktivieren ohne Zugangsdaten wird verweigert (außer im DRY_RUN).
* `DRY_RUN=true` (Standard): Social Media wird nur simuliert.
* Agent-Fehlerserien → Auto-Pause + Alarm. Plattform-Fehlerserien/Rate-Limits → Auto-Pause.
* KI-Kostenlimit pro Tag/Monat; bei Erreichen Vorlagentexte statt KI.
