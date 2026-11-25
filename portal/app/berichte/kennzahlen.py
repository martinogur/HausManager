"""
Kennzahlen und Aufgabenlisten für das Dashboard – direkt per SQL.

Bewusst unabhängig von den Fachmodellen: Die Abfragen nutzen nur Tabellen und
Sichten aus ``portal/db/schema.sql`` (search_path = hh, public).
Alle Datumsgrenzen werden in Europe/Berlin berechnet.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from django.db import connection
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

ZEITZONE = "Europe/Berlin"


@dataclass(frozen=True)
class Zeitraum:
    heute: date
    wochenstart: date  # Montag
    wochenende: date  # Sonntag
    monatsstart: date

    @classmethod
    def aktuell(cls, heute: date | None = None) -> "Zeitraum":
        heute = heute or timezone.localdate()
        wochenstart = heute - timedelta(days=heute.weekday())
        return cls(heute, wochenstart, wochenstart + timedelta(days=6), heute.replace(day=1))

    def als_parameter(self) -> dict:
        return {
            "tz": ZEITZONE,
            "heute": self.heute,
            "wochenstart": self.wochenstart,
            "wochenende": self.wochenende,
            "monatsstart": self.monatsstart,
            "in_7_tagen": self.heute + timedelta(days=7),
        }


def _zeilen(sql: str, parameter) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(sql, parameter)
        spalten = [s.name for s in cursor.description]
        return [dict(zip(spalten, zeile)) for zeile in cursor.fetchall()]


def _admin_link(name: str) -> str | None:
    """Link in die Verwaltungsoberfläche, falls das Fachmodell dort registriert ist."""
    try:
        return reverse(f"admin:{name}_changelist")
    except NoReverseMatch:
        return None


# Offene Aufträge = alles, was noch nicht erledigt, abgerechnet oder storniert ist
_OFFENE_AUFTRAEGE = "status NOT IN ('erledigt', 'abgerechnet', 'storniert')"

KENNZAHLEN_SQL = f"""
SELECT
  (SELECT count(*) FROM kunden WHERE status = 'aktiv')                               AS kunden_aktiv,
  (SELECT count(*) FROM objekte)                                                      AS objekte,
  (SELECT count(*) FROM auftraege WHERE {_OFFENE_AUFTRAEGE})                          AS auftraege_offen,
  (SELECT count(*) FROM einsaetze
     WHERE status <> 'ausgefallen'
       AND (geplant_von AT TIME ZONE %(tz)s)::date = %(heute)s)                       AS einsaetze_heute,
  (SELECT count(*) FROM einsaetze
     WHERE status <> 'ausgefallen'
       AND (geplant_von AT TIME ZONE %(tz)s)::date BETWEEN %(wochenstart)s AND %(wochenende)s)
                                                                                      AS einsaetze_woche,
  (SELECT count(*) FROM v_offene_angebote)                                            AS angebote_offen,
  (SELECT coalesce(sum(netto_eur), 0) FROM v_offene_angebote)                         AS angebote_offen_eur,
  (SELECT count(*) FROM bewerbungen WHERE status = 'eingegangen')                     AS bewerbungen_neu,
  (SELECT count(*) FROM email_protokolle WHERE richtung = 'eingang' AND status = 'neu')
                                                                                      AS emails_neu,
  (SELECT coalesce(sum(stunden), 0) FROM v_arbeitsstunden_woche WHERE woche = %(wochenstart)s)
                                                                                      AS stunden_woche,
  (SELECT coalesce(sum(umsatz_netto_eur), 0) FROM v_umsatz_monat WHERE monat = %(monatsstart)s)
                                                                                      AS umsatz_monat_eur,
  (SELECT coalesce(sum(bezahlt_netto_eur), 0) FROM v_umsatz_monat WHERE monat = %(monatsstart)s)
                                                                                      AS bezahlt_monat_eur
"""


def kennzahlen(zeitraum: Zeitraum | None = None) -> dict:
    """Alle Kennzahlen für Büro/Admin in einer Abfrage."""
    zeitraum = zeitraum or Zeitraum.aktuell()
    werte = _zeilen(KENNZAHLEN_SQL, zeitraum.als_parameter())[0]
    werte["zeitraum"] = zeitraum
    return werte


EINSAETZE_HEUTE_SQL = """
SELECT e.id, e.geplant_von, e.geplant_bis, e.status,
       a.auftragsnummer, a.titel,
       o.bezeichnung AS objekt, o.strasse, o.hausnummer, o.plz, o.ort,
       coalesce(string_agg(m.vorname || ' ' || m.nachname, ', ' ORDER BY m.nachname), '') AS mitarbeiter
FROM einsaetze e
JOIN auftraege a ON a.id = e.auftrag_id
JOIN objekte o   ON o.id = a.objekt_id
LEFT JOIN einsatz_mitarbeiter em ON em.einsatz_id = e.id
LEFT JOIN mitarbeiter m ON m.id = em.mitarbeiter_id
WHERE (e.geplant_von AT TIME ZONE %(tz)s)::date = %(heute)s
  AND e.status <> 'ausgefallen'
GROUP BY e.id, a.id, o.id
ORDER BY e.geplant_von
"""

HINWEISE_SQL = f"""
SELECT
  (SELECT count(*) FROM email_protokolle WHERE richtung = 'eingang' AND status = 'neu')       AS emails_neu,
  (SELECT count(*) FROM email_protokolle WHERE richtung = 'ausgang' AND status = 'entwurf')   AS emails_entwurf,
  (SELECT count(*) FROM anfragen WHERE status = 'neu')                                        AS anfragen_neu,
  (SELECT count(*) FROM bewerbungen WHERE status = 'eingegangen')                             AS bewerbungen_neu,
  (SELECT count(*) FROM angebote WHERE status = 'versendet'
      AND gueltig_bis BETWEEN %(heute)s AND %(in_7_tagen)s)                                   AS angebote_laufen_ab,
  (SELECT count(*) FROM auftraege WHERE {_OFFENE_AUFTRAEGE} AND faellig_am <= %(heute)s)     AS auftraege_faellig,
  (SELECT count(*) FROM einsaetze e WHERE (e.geplant_von AT TIME ZONE %(tz)s)::date = %(heute)s
      AND e.status <> 'ausgefallen'
      AND NOT EXISTS (SELECT 1 FROM einsatz_mitarbeiter em WHERE em.einsatz_id = e.id))       AS einsaetze_ohne_personal,
  (SELECT count(*) FROM arbeitszeiten WHERE ende IS NOT NULL AND bestaetigt_am IS NULL)       AS zeiten_unbestaetigt,
  (SELECT count(*) FROM bewerbungen WHERE loeschen_ab <= %(heute)s)                           AS bewerbungen_loeschfrist
"""

# (Schlüssel, Text, Admin-Seite, dringend?)
_HINWEIS_TEXTE = [
    ("einsaetze_ohne_personal", "Einsätze heute ohne Mitarbeiter", "auftraege_einsatz", True),
    ("auftraege_faellig", "Aufträge fällig oder überfällig", "auftraege_auftrag", True),
    ("emails_neu", "neue E-Mails zuordnen", "kommunikation_emailprotokoll", False),
    ("emails_entwurf", "Antwortentwürfe warten auf Freigabe", "kommunikation_emailprotokoll", False),
    ("anfragen_neu", "neue Anfragen bearbeiten", "auftraege_anfrage", False),
    ("angebote_laufen_ab", "Angebote laufen in 7 Tagen ab – nachfassen", "auftraege_angebot", False),
    ("bewerbungen_neu", "neue Bewerbungen sichten", "personal_bewerbung", False),
    ("zeiten_unbestaetigt", "Arbeitszeiten bestätigen", "personal_arbeitszeit", False),
    ("bewerbungen_loeschfrist", "Bewerbungen haben die Löschfrist erreicht", "personal_bewerbung", True),
]


def heute_zu_tun(zeitraum: Zeitraum | None = None) -> dict:
    """Einsätze von heute und offene Punkte (nur Einträge mit Anzahl > 0)."""
    zeitraum = zeitraum or Zeitraum.aktuell()
    parameter = zeitraum.als_parameter()
    zaehler = _zeilen(HINWEISE_SQL, parameter)[0]
    hinweise = [
        {"anzahl": zaehler[schluessel], "text": text, "link": _admin_link(seite), "dringend": dringend}
        for schluessel, text, seite, dringend in _HINWEIS_TEXTE
        if zaehler[schluessel]
    ]
    return {"einsaetze": _zeilen(EINSAETZE_HEUTE_SQL, parameter), "hinweise": hinweise}


EIGENE_EINSAETZE_SQL = """
SELECT e.id, e.geplant_von, e.geplant_bis, e.status, e.notiz_buero,
       a.titel,
       o.bezeichnung AS objekt, o.strasse, o.hausnummer, o.plz, o.ort, o.zugang_hinweise
FROM einsaetze e
JOIN einsatz_mitarbeiter em ON em.einsatz_id = e.id
JOIN mitarbeiter m          ON m.id = em.mitarbeiter_id
JOIN auftraege a            ON a.id = e.auftrag_id
JOIN objekte o              ON o.id = a.objekt_id
WHERE m.benutzer_id = %(benutzer_id)s
  AND (e.geplant_von AT TIME ZONE %(tz)s)::date BETWEEN %(von)s AND %(bis)s
  AND e.status <> 'ausgefallen'
ORDER BY e.geplant_von
"""


def eigene_einsaetze(benutzer, von: date, bis: date | None = None) -> list[dict]:
    """Einsätze, denen der Benutzer (über mitarbeiter.benutzer_id) zugeteilt ist."""
    return _zeilen(
        EIGENE_EINSAETZE_SQL,
        {"benutzer_id": benutzer.pk, "tz": ZEITZONE, "von": von, "bis": bis or von},
    )


def ist_als_mitarbeiter_verknuepft(benutzer) -> bool:
    return bool(_zeilen("SELECT 1 FROM mitarbeiter WHERE benutzer_id = %s", [benutzer.pk]))
