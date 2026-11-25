"""Das Agenten-Team von Hausmeister Helden (Register).

Jeder Agent: Verantwortungsbereich, Aufgaben (in ``agenten/team/``), erlaubte Delegationsziele,
Werkzeuge (Datenzugriffe), Budget und Grenzen, Erfolgsmessung. Eskalation läuft immer über
die Freigabe-Warteschlange zum Geschäftsführer.
"""

from .laufzeit import agent

ALLE = frozenset({"ceo", "sales", "lead_research", "marketing", "social", "seo", "kundenservice", "angebot",
                  "dispatch", "hr", "finance", "quality", "automation"})

agent(code="ceo", name="CEO-Orchestrator", verantwortung="Steuerung",
      beschreibung="Verteilt Tagesaufgaben, prüft Ergebnisse, setzt Prioritäten, erstellt Tagesbriefing und "
                   "Wochenbericht, leitet offene Entscheidungen an den Geschäftsführer weiter.",
      darf_delegieren_an=ALLE - {"ceo"}, werkzeuge=("kennzahlen_lesen", "freigaben_lesen", "agenten_beauftragen"),
      tagesbudget_cent=60, max_schritte=12, max_laufzeit_sekunden=180,
      erfolgsmessung="Offene Freigaben < 48 h alt, keine unbemerkten Fehler, Bericht jeden Montag 7 Uhr")
agent(code="sales", name="Sales-Agent", verantwortung="Kundengewinnung",
      beschreibung="Bewertet Leads (A/B/C), wählt zulässige Kontaktwege (UWG), erstellt Kontakt- und "
                   "Nachfassvorschläge zur Freigabe, überwacht Wiedervorlagen und Vertriebskennzahlen.",
      darf_delegieren_an=frozenset({"angebot", "lead_research"}),
      werkzeuge=("leads_lesen", "lead_bewerten", "kontaktvorschlag_freigabe"), tagesbudget_cent=60,
      erfolgsmessung="Wiedervorlagen pünktlich, Kontaktquote A-Leads, Angebote je Monat, Abschlussquote")
agent(code="lead_research", name="Lead-Research-Agent", verantwortung="Lead-Recherche",
      beschreibung="Nimmt recherchierte Leads (Hausverwaltungen, Gewerbe, Filialen, Büros, Investoren) mit "
                   "Pflicht-Quelle auf, prüft Dubletten und Region, importiert den Lead-Bestand. Kein Scraping.",
      darf_delegieren_an=frozenset({"sales"}), werkzeuge=("lead_anlegen", "bestand_importieren"), modell=None,
      tagesbudget_cent=0, erfolgsmessung="Neue qualifizierte Leads je Woche im Einsatzgebiet, 0 Dubletten")
agent(code="marketing", name="Marketing-Agent", verantwortung="Marketingstrategie",
      beschreibung="Plant saisonale Kampagnen (Winterdienst, Frühjahr, Garten, Laub) und gibt Themen an "
                   "Social Media und SEO weiter.",
      darf_delegieren_an=frozenset({"social", "seo"}), werkzeuge=("kennzahlen_lesen",), tagesbudget_cent=30,
      erfolgsmessung="Anfragen je Kanal, Kosten je Anfrage")
agent(code="social", name="Social-Media-Agent", verantwortung="Instagram/Facebook",
      beschreibung="Erstellt den Wochenplan (5 Posts, 2–3 Reels, Stories) mit Texten, Bildideen und regionalen "
                   "Hashtags als Entwürfe im Redaktionskalender – Veröffentlichung nur nach Freigabe.",
      werkzeuge=("redaktionskalender_schreiben", "freigabe_anfordern"), tagesbudget_cent=60, max_laufzeit_sekunden=240,
      max_schritte=20,
      erfolgsmessung="Plan jeden Donnerstag fertig, Freigabequote, Reichweite/Interaktionen")
agent(code="seo", name="SEO-Agent", verantwortung="Lokale Sichtbarkeit",
      beschreibung="Plant wöchentliche Beiträge für das Google-Unternehmensprofil und erinnert an "
                   "Bewertungsbitten nach erledigten Aufträgen (nie gekaufte Bewertungen).",
      werkzeuge=("redaktionskalender_schreiben",), tagesbudget_cent=20,
      erfolgsmessung="1 Google-Beitrag/Woche, Anzahl echter Bewertungen")
agent(code="kundenservice", name="Kundenservice-Agent", verantwortung="E-Mails und Anfragen",
      beschreibung="Ordnet eingehende E-Mails ein (Anfrage, Bewerbung, Bestandskunde, Spam), legt Anfragen an, "
                   "fasst zusammen, erkennt fehlende Angaben, schreibt Antwortentwürfe zur Freigabe.",
      darf_delegieren_an=frozenset({"hr", "angebot"}), werkzeuge=("emails_lesen", "anfrage_anlegen", "antwortentwurf"),
      tagesbudget_cent=80, erfolgsmessung="Antwortentwurf < 15 Min. nach Eingang, Reaktion < 24 h")
agent(code="angebot", name="Angebots-Agent", verantwortung="Angebotskalkulation",
      beschreibung="Berechnet Angebote nach der freigegebenen Preisliste, prüft Selbstkosten und Marge, legt "
                   "Angebotsentwürfe an und fordert die Freigabe an. Nichts wird ohne Freigabe verbindlich.",
      werkzeuge=("kalkulation", "angebot_entwurf"), modell=None, tagesbudget_cent=0,
      erfolgsmessung="Marge ≥ Ziel, Angebotsquote, Zeit bis Angebot")
agent(code="dispatch", name="Dispositions-Agent", verantwortung="Einsatzplanung",
      beschreibung="Erzeugt wiederkehrende Einsätze aus Leistungsvereinbarungen, plant Einsätze zu "
                   "freigegebenen Aufträgen und schlägt verfügbare Mitarbeiter vor (Zuweisung nach Freigabe).",
      werkzeuge=("einsaetze_schreiben", "verfuegbarkeit_lesen"), modell=None, tagesbudget_cent=0,
      erfolgsmessung="Keine ungeplanten Einsätze < 48 h, Auslastung, keine Doppelbelegung")
agent(code="hr", name="HR-Agent", verantwortung="Bewerbungen und Personal",
      beschreibung="Fasst Bewerbungen sachlich zusammen (keine Bewertung, keine Entscheidung), entwirft "
                   "Eingangsbestätigungen, achtet auf Löschfristen.",
      werkzeuge=("bewerbungen_lesen", "antwortentwurf"), tagesbudget_cent=30,
      erfolgsmessung="Eingangsbestätigung < 24 h, Löschfristen eingehalten")
agent(code="finance", name="Finanz-Agent", verantwortung="Abrechnung und Zahlungen",
      beschreibung="Bereitet Rechnungsentwürfe zu erledigten Aufträgen vor, überwacht Fälligkeiten und "
                   "Deckungsbeiträge. Keine Zahlungen, keine Festschreibung ohne Inhaber.",
      werkzeuge=("rechnungen_schreiben_entwurf", "kennzahlen_lesen"), modell=None, tagesbudget_cent=0,
      erfolgsmessung="Rechnung < 3 Tage nach Erledigung, Forderungslaufzeit, DB je Auftrag")
agent(code="quality", name="Qualitäts-Agent", verantwortung="Auftragsqualität",
      beschreibung="Prüft erledigte Aufträge auf Vorher/Nachher-Fotos, Arbeitsbericht, bestätigte Zeiten und "
                   "Rentabilität; meldet wiederkehrende Probleme.",
      werkzeuge=("auftraege_lesen", "fotos_lesen"), modell=None, tagesbudget_cent=0,
      erfolgsmessung="Anteil vollständig dokumentierter Aufträge, Beschwerden")
agent(code="automation", name="Automations-Agent", verantwortung="Überwachung",
      beschreibung="Überwacht Automatisierungen, Ereignisse, Agentenaufträge und KI-Kosten; meldet Ausfälle "
                   "und Budget-Engpässe als Eskalation.",
      werkzeuge=("protokolle_lesen",), modell=None, tagesbudget_cent=0,
      erfolgsmessung="Ausfälle innerhalb 1 h gemeldet")

from .team import betrieb, ceo, marketing, service, technik, vertrieb  # noqa: E402,F401  (registriert Aufgaben)
