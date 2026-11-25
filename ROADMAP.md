# Roadmap

Jede Phase endet mit automatischen Tests, einer Vorschau und der Freigabe durch den Inhaber.
Die Phasen des Projektauftrags sind auf den vorhandenen Portal-Plan (`portal/docs/01-architektur.md`) abgebildet.

| Phase | Inhalt | Status | Nächster Schritt |
|---|---|---|---|
| **1 Fundament** | Architektur, Datenmodell, Auth mit 2FA, Rollen, Audit, Betrieb, Backups | ✅ fertig (Phase 1+2 Portal) | Server buchen (D2) |
| **2 Unternehmensdashboard** | Kunden, Objekte, Mitarbeiter, Aufträge, Kennzahlen, Controlling, 15 Bereiche | ✅ fertig (Stammdaten über Admin, Steuerung eigene Seiten) | Echte Stammdaten importieren (Phase 8) |
| **3 Systemintegrationen** | IONOS, HubSpot, Lexware, Make (Craftnote: Ablösung) | ✅ Code fertig · ⏳ Zugangsdaten | D3, D5, D6, D7 |
| **4 KI-Agenten** | 13 Agenten, Laufzeit, Budgets, Eskalation, Freigaben | ✅ fertig (regelbasiert + KI) | API-Schlüssel (D3), Prompts mit echten Mails nachschärfen |
| **5 Kundengewinnung** | Lead-Pipeline, Scoring, Kontaktwege nach UWG, Wiedervorlagen, Angebotsrechner | ✅ fertig, 52 Leads importierbar | Erste Brief-Welle freigeben; Fressnapf-Status (D4) |
| **6 Marketing** | Redaktionskalender (5/3/5 je Woche), Google-Beiträge, Saisonplan | ✅ Planung fertig · ⏳ Veröffentlichung | Instagram-Token, `posten.py` an Redaktionskalender anbinden; Kennzahlen-Import |
| **7 Vollautomatisierung** | Ereignisse, 18 Automatisierungen, Überwachung, Wochenbericht | ✅ fertig | Externe Uptime-Prüfung (Worker-Herzschlag), Rate-Limit `/api/` |
| **8 Optimierung & Produktivsetzung** | Datenimport, Lasttest, Datenschutz (VVT, AV-Verträge, Löschjobs), Kosten, Conversion | ⏳ offen | siehe TASKS.md P1 |

## Nächste 4 Wochen (Vorschlag)

1. **Woche 1:** D1–D3 entscheiden, Server aufsetzen (`portal/deploy/hetzner/server_erstellen.py`), Admin-Konto, Lead-Import, Fressnapf-Status.
2. **Woche 2:** IONOS-Postfach anbinden (D5), Kundenservice-Agent mit echten Mails beobachten, Antwortentwürfe bewerten.
3. **Woche 3:** Mitarbeiter-Konten für 2 Aushilfen + Hausmeister, mobile Einsatzansicht im Alltag, Craftnote parallel (D8).
4. **Woche 4:** Löschjobs, VVT, AV-Verträge; erste Optimierung der Preise/Margen anhand echter Arbeitszeiten (Controlling).
