"""Lead-Bewertung (A/B/C) und zulässige Kontaktwege.

Priorität A: hoher Umsatz und regelmäßiger Bedarf.
Priorität B: interessanter Einzelauftrag bzw. mittleres Potenzial.
Priorität C: geringes wirtschaftliches Potenzial oder außerhalb des Einsatzgebiets.

Die Bewertung ist regelbasiert und nachvollziehbar (jede Punktzahl hat eine Begründung);
ein KI-Agent darf Eingabewerte vorschlagen, die Rechnung selbst bleibt deterministisch.
"""

from dataclasses import dataclass

# Grundpotenzial je Zielgruppe (Bestand, Wiederkehr, Entscheidungsweg)
ZIELGRUPPE_PUNKTE = {
    "wohnungsunternehmen": 30, "hausverwaltung": 30, "gewerbeimmobilie": 22, "investor": 22,
    "einzelhandel": 20, "buero": 18, "eigentuemer": 18, "unternehmen": 15, "partnernetz": 15,
    "sonstige": 8, "privat": 5,
}
A_MINDEST_MONATSUMSATZ_CENT = 40000  # 400 € netto/Monat


@dataclass(frozen=True)
class LeadMerkmale:
    zielgruppe: str
    regelmaessiger_bedarf: bool | None
    geschaetzter_monatsumsatz_cent: int | None
    entfernung_km: float | None
    im_einsatzgebiet: bool | None
    hat_postanschrift: bool
    hat_telefon: bool
    widerspruch: bool = False
    vorbewertung: str | None = None   # A/B/C aus der Recherche (nur genutzt, wenn der Umsatz unbekannt ist)


@dataclass(frozen=True)
class Bewertung:
    score: int
    prioritaet: str
    gruende: list[tuple[str, int]]

    def als_json(self) -> dict:
        return {"score": self.score, "prioritaet": self.prioritaet, "gruende": [{"grund": g, "punkte": p} for g, p in self.gruende]}


def bewerte(m: LeadMerkmale) -> Bewertung:
    gruende: list[tuple[str, int]] = []
    zg = ZIELGRUPPE_PUNKTE.get(m.zielgruppe, 8)
    gruende.append((f"Zielgruppe {m.zielgruppe}", zg))

    if m.regelmaessiger_bedarf is True:
        gruende.append(("Regelmäßiger Bedarf (wiederkehrender Vertrag möglich)", 25))
    elif m.regelmaessiger_bedarf is None:
        gruende.append(("Bedarf unbekannt", 10))
    else:
        gruende.append(("Nur Einzelbedarf", 0))

    u = m.geschaetzter_monatsumsatz_cent
    if u is None:
        gruende.append(("Umsatzpotenzial unbekannt", 6))
    elif u >= 150000:
        gruende.append(("Umsatzpotenzial ≥ 1.500 €/Monat", 25))
    elif u >= 80000:
        gruende.append(("Umsatzpotenzial ≥ 800 €/Monat", 20))
    elif u >= 40000:
        gruende.append(("Umsatzpotenzial ≥ 400 €/Monat", 14))
    elif u >= 15000:
        gruende.append(("Umsatzpotenzial ≥ 150 €/Monat", 8))
    else:
        gruende.append(("Geringes Umsatzpotenzial", 2))

    if m.im_einsatzgebiet is False:
        gruende.append(("Außerhalb des Einsatzgebiets", -40))
    elif m.entfernung_km is None:
        gruende.append(("Entfernung noch nicht geprüft", 3))
    elif m.entfernung_km <= 10:
        gruende.append(("Nah (≤ 10 km, Anfahrtszone 1)", 15))
    elif m.entfernung_km <= 25:
        gruende.append(("Mittel (≤ 25 km, Anfahrtszone 2)", 10))
    else:
        gruende.append(("Randlage des Einsatzgebiets", 4))

    if m.hat_postanschrift or m.hat_telefon:
        gruende.append(("Zulässiger Kontaktweg vorhanden (Brief/Telefon)", 5))
    else:
        gruende.append(("Kein zulässiger Kontaktweg bekannt", -10))

    score = max(0, min(100, sum(p for _, p in gruende)))
    if m.widerspruch:
        gruende.append(("Werbewiderspruch – kein Kontakt", 0))
        return Bewertung(0, "C", gruende)

    umsatz_hoch = (u or 0) >= A_MINDEST_MONATSUMSATZ_CENT or (u is None and m.vorbewertung == "A")
    if m.im_einsatzgebiet is False:
        prio = "C"
    elif score >= 70 and m.regelmaessiger_bedarf is True and umsatz_hoch:
        prio = "A"
    elif score >= 45:
        prio = "B"
    else:
        prio = "C"
    return Bewertung(score, prio, gruende)


def zulaessige_kontaktwege(zielgruppe: str, *, hat_postanschrift: bool, hat_telefon: bool, hat_email: bool,
                           email_einwilligung: bool, einladung_beleg: bool, widerspruch: bool) -> list[tuple[str, str]]:
    """Kontaktwege in empfohlener Reihenfolge mit Rechtsgrundlage (§ 7 UWG, DSGVO).

    * Brief: zulässig (kein Werbeverbot, Robinsonliste/Widerspruch beachten).
    * Telefon B2B: nur bei mutmaßlicher Einwilligung (konkreter Bezug zum Geschäft), nie bei Privatpersonen
      ohne ausdrückliche Einwilligung (§ 7 Abs. 2 Nr. 1 UWG).
    * E-Mail: nur mit vorheriger ausdrücklicher Einwilligung (§ 7 Abs. 2 Nr. 2 UWG) oder als Antwort auf
      eine öffentliche Einladung (Partner-/Nachunternehmerseite, Ausschreibung) über genau diesen Weg.
    * Keine Massen-E-Mails, keine automatisierten Anrufe.
    """
    if widerspruch:
        return []
    wege = []
    if einladung_beleg:
        wege.append(("kontaktformular", "Antwort auf öffentliche Einladung – nur der dort genannte Weg"))
    if hat_email and (email_einwilligung or einladung_beleg):
        wege.append(("email", "Einwilligung oder öffentliche Einladung liegt vor"))
    if hat_postanschrift:
        wege.append(("brief", "Werbebrief an Geschäftsadresse zulässig"))
    if hat_telefon and zielgruppe != "privat":
        wege.append(("telefon", "B2B: nur bei mutmaßlichem Interesse mit konkretem Bezug, persönlich, nicht automatisiert"))
    return wege
