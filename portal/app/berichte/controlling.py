"""Controlling-Kennzahlen für Dashboard, Controlling-Seite und Wochenbericht.

Direkt per SQL auf Tabellen/Sichten aus schema.sql und 0003_betriebssystem.sql.
Umsatz = Rechnungen (Spiegel aus Lexware; führend ist Lexware Office).
Gewinn hier = Umsatz netto − Personalkosten (Arbeitszeiten × Stundenlohn × Nebenkosten bzw.
kalkulatorischer Satz) − Materialkosten der Aufträge. Fixkosten (Fahrzeug, Versicherung …)
sind nicht enthalten → Bezeichnung „Rohertrag“ in der Oberfläche.
"""

from dataclasses import dataclass
from datetime import date

from django.db import connection

ZEITZONE = "Europe/Berlin"


def _eine_zeile(sql: str, parameter: dict) -> dict:
    with connection.cursor() as c:
        c.execute(sql, parameter)
        spalten = [s.name for s in c.description]
        return dict(zip(spalten, c.fetchone()))


def _zeilen(sql: str, parameter: dict) -> list[dict]:
    with connection.cursor() as c:
        c.execute(sql, parameter)
        spalten = [s.name for s in c.description]
        return [dict(zip(spalten, z)) for z in c.fetchall()]


@dataclass(frozen=True)
class Zeitraum:
    von: date  # einschließlich
    bis: date  # ausschließlich

    @classmethod
    def monat(cls, tag: date) -> "Zeitraum":
        start = tag.replace(day=1)
        ende = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
        return cls(start, ende)

    @classmethod
    def jahr(cls, tag: date) -> "Zeitraum":
        return cls(date(tag.year, 1, 1), date(tag.year + 1, 1, 1))


KENNZAHLEN_SQL = """
WITH zeiten AS (
    SELECT coalesce(sum((extract(epoch FROM (z.ende - z.beginn)) / 3600 - z.pause_minuten / 60.0)
           * CASE WHEN m.stundenlohn_cent IS NOT NULL
                  THEN m.stundenlohn_cent * (1 + (SELECT (wert #>> '{}')::numeric FROM firmenparameter WHERE schluessel = 'lohnnebenkosten_prozent') / 100)
                  ELSE (SELECT (wert #>> '{}')::numeric FROM firmenparameter WHERE schluessel = 'kalk_stundensatz_ohne_lohn_cent') END), 0) AS cent,
           coalesce(sum(extract(epoch FROM (z.ende - z.beginn)) / 3600 - z.pause_minuten / 60.0), 0) AS stunden
    FROM arbeitszeiten z JOIN mitarbeiter m ON m.id = z.mitarbeiter_id
    WHERE z.ende IS NOT NULL AND (z.beginn AT TIME ZONE %(tz)s)::date >= %(von)s AND (z.beginn AT TIME ZONE %(tz)s)::date < %(bis)s
), angebote_zeitraum AS (
    SELECT count(*) FILTER (WHERE status = 'angenommen') AS angenommen,
           count(*) FILTER (WHERE status IN ('angenommen', 'abgelehnt', 'abgelaufen')) AS entschieden
    FROM angebote WHERE (geaendert_am AT TIME ZONE %(tz)s)::date >= %(von)s AND (geaendert_am AT TIME ZONE %(tz)s)::date < %(bis)s
)
SELECT
  (SELECT coalesce(sum(summe_netto_cent), 0) FROM rechnungen
     WHERE status <> 'storniert' AND rechnungsdatum >= %(von)s AND rechnungsdatum < %(bis)s)      AS umsatz_cent,
  (SELECT coalesce(sum(summe_netto_cent), 0) FROM rechnungen
     WHERE status IN ('offen', 'ueberfaellig'))                                                  AS offene_rechnungen_cent,
  (SELECT count(*) FROM rechnungen WHERE status = 'ueberfaellig')                                AS rechnungen_ueberfaellig,
  (SELECT cent FROM zeiten)                                                                      AS personalkosten_cent,
  (SELECT stunden FROM zeiten)                                                                   AS arbeitsstunden,
  (SELECT coalesce(sum(materialkosten_cent), 0) FROM auftraege
     WHERE status IN ('erledigt', 'abgerechnet') AND (geaendert_am AT TIME ZONE %(tz)s)::date >= %(von)s
       AND (geaendert_am AT TIME ZONE %(tz)s)::date < %(bis)s)                                   AS materialkosten_cent,
  (SELECT count(*) FROM auftraege WHERE status NOT IN ('erledigt', 'abgerechnet', 'storniert'))  AS auftraege_offen,
  (SELECT count(*) FROM auftraege WHERE status IN ('erledigt', 'abgerechnet')
     AND (geaendert_am AT TIME ZONE %(tz)s)::date >= %(von)s AND (geaendert_am AT TIME ZONE %(tz)s)::date < %(bis)s)
                                                                                                 AS auftraege_abgeschlossen,
  (SELECT count(*) FROM anfragen WHERE (eingegangen_am AT TIME ZONE %(tz)s)::date >= %(von)s
     AND (eingegangen_am AT TIME ZONE %(tz)s)::date < %(bis)s)                                   AS anfragen_neu,
  (SELECT count(*) FROM leads WHERE (erstellt_am AT TIME ZONE %(tz)s)::date >= %(von)s
     AND (erstellt_am AT TIME ZONE %(tz)s)::date < %(bis)s)                                      AS leads_neu,
  (SELECT count(*) FROM angebote WHERE status IN ('entwurf', 'versendet'))                       AS angebote_offen,
  (SELECT angenommen FROM angebote_zeitraum)                                                     AS angebote_angenommen,
  (SELECT entschieden FROM angebote_zeitraum)                                                    AS angebote_entschieden,
  (SELECT coalesce(sum(monatsumsatz_cent), 0) FROM v_wiederkehrende_umsaetze)                    AS wiederkehrend_monat_cent,
  (SELECT count(DISTINCT vereinbarung_id) FROM v_wiederkehrende_umsaetze)                        AS wiederkehrende_vertraege,
  (SELECT count(*) FROM freigaben WHERE status = 'offen')                                        AS freigaben_offen,
  (SELECT coalesce(sum(kosten_cent), 0) FROM ki_aufrufe WHERE (erstellt_am AT TIME ZONE %(tz)s)::date >= %(von)s
     AND (erstellt_am AT TIME ZONE %(tz)s)::date < %(bis)s)                                      AS ki_kosten_cent
"""


def kennzahlen(zeitraum: Zeitraum) -> dict:
    k = _eine_zeile(KENNZAHLEN_SQL, {"tz": ZEITZONE, "von": zeitraum.von, "bis": zeitraum.bis})
    k = {schluessel: (float(wert) if hasattr(wert, "as_integer_ratio") and not isinstance(wert, int) else wert)
         for schluessel, wert in k.items()}
    k["personalkosten_cent"] = round(k["personalkosten_cent"])
    k["arbeitsstunden"] = round(k["arbeitsstunden"], 1)
    k["ki_kosten_cent"] = round(k["ki_kosten_cent"], 2)
    k["rohertrag_cent"] = k["umsatz_cent"] - k["personalkosten_cent"] - k["materialkosten_cent"]
    k["angebotsquote_prozent"] = (round(100 * k["angebote_angenommen"] / k["angebote_entschieden"], 1)
                                  if k["angebote_entschieden"] else None)
    return k


def auftragsrentabilitaet(grenze: int = 20) -> list[dict]:
    """Aufträge mit Verkaufspreis, sortiert nach Deckungsbeitrag in % (schlechteste zuerst)."""
    return _zeilen(
        """SELECT w.*, a.titel, k.name AS kunde FROM v_auftrag_wirtschaftlichkeit w
           JOIN auftraege a ON a.id = w.auftrag_id JOIN kunden k ON k.id = a.kunde_id
           WHERE w.verkaufspreis_netto_cent IS NOT NULL AND w.status <> 'storniert'
           ORDER BY w.deckungsbeitrag_prozent NULLS LAST LIMIT %(grenze)s""",
        {"grenze": grenze},
    )


def umsatz_je_monat(jahr: int) -> list[dict]:
    """12 Monate (auch leere) für das Umsatzdiagramm."""
    return _zeilen(
        """SELECT m::date AS monat,
                  coalesce((SELECT sum(summe_netto_cent) FROM rechnungen r WHERE r.status <> 'storniert'
                            AND date_trunc('month', r.rechnungsdatum) = m), 0)::bigint AS umsatz_cent
           FROM generate_series(make_date(%(jahr)s, 1, 1), make_date(%(jahr)s, 12, 1), interval '1 month') m
           ORDER BY m""",
        {"jahr": jahr},
    )


def lead_pipeline() -> list[dict]:
    return _zeilen(
        """SELECT status::text, prioritaet::text, count(*) AS anzahl,
                  coalesce(sum(geschaetzter_monatsumsatz_cent), 0) AS potenzial_cent
           FROM leads GROUP BY 1, 2 ORDER BY 1, 2""",
        {},
    )
