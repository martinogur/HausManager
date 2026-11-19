"""Textvorlagen für Akquise (Hausmeister Helden) und Mieterkommunikation.

Platzhalter in {geschweiften Klammern} werden automatisch befüllt. Texte hier anpassen – sie werden bei jedem Automatik-Lauf verwendet. """


class _Safe(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def fuellen(text, daten):
    return text.format_map(_Safe(daten))


def briefanrede(anrede, name):
    if anrede == "Herr" and name:
        return f"Sehr geehrter Herr {name.split()[-1]}"
    if anrede == "Frau" and name:
        return f"Sehr geehrte Frau {name.split()[-1]}"
    return "Sehr geehrte Damen und Herren"


# ---------------------------------------------------------------------------
# Akquise-Sequenz an Hausverwaltungen / WEGs / Wohnungsunternehmen
# Schritt 1 = Erstkontakt, 2 = Nachfassen, 3 = letzter Impuls
# ---------------------------------------------------------------------------
AKQUISE = {
    1: {
        "betreff": "Zuverlässiger Hausmeisterservice für Ihre Objekte in {einsatzgebiet}",
        "text": """{briefanrede},

als Verwaltung wissen Sie am besten: Ein Hausmeister, der nicht erreichbar ist oder Termine verschiebt, kostet Sie Zeit, Nerven und am Ende Ärger mit Eigentümern und Mietern.

Wir sind {firma_name} – Ihr Hausmeisterservice in {einsatzgebiet}. Wir übernehmen für {firma}:

  • Objektbetreuung & regelmäßige Begehungen mit Fotoprotokoll
  • Treppenhaus- und Außenanlagenreinigung, Grünpflege
  • Winterdienst inkl. Dokumentation (Haftungssicherheit)
  • Kleinreparaturen, Mülltonnenservice, Zählerablesung
  • Schnelle Reaktion bei Schäden – ein fester Ansprechpartner

Unser Angebot zum Kennenlernen: Ein kostenloser Objekt-Check für eine Liegenschaft Ihrer Wahl – inklusive kurzem Zustandsbericht, den Sie direkt an die Eigentümer weitergeben können.

Rufen Sie mich einfach an ({firma_telefon}) oder antworten Sie kurz per E-Mail ({firma_email}) – ich melde mich innerhalb von 24 Stunden.

Mit freundlichen Grüßen

{firma_inhaber}
{firma_name}
{firma_adresse}
{firma_web}
""",
    },
    2: {
        "betreff": "Kurze Nachfrage: kostenloser Objekt-Check für {firma}",
        "text": """{briefanrede},

vor kurzem habe ich Ihnen {firma_name} vorgestellt. Ich weiß, dass im Verwaltungsalltag viel liegen bleibt – deshalb nur kurz:

Unser Angebot eines kostenlosen Objekt-Checks gilt weiterhin. Sie nennen uns eine Liegenschaft, wir prüfen Treppenhaus, Außenanlagen, Keller, Technikräume und Müllplätze und schicken Ihnen einen Bericht mit Fotos – unverbindlich.

Viele Verwaltungen nutzen das, um bei der nächsten Eigentümerversammlung einen Dienstleisterwechsel sauber zu begründen.

Passt Ihnen ein kurzes Telefonat in den nächsten Tagen? Sie erreichen mich unter
{firma_telefon}.

Mit freundlichen Grüßen

{firma_inhaber}
{firma_name}
""",
    },
    3: {
        "betreff": "Letzte Nachricht von {firma_name}",
        "text": """{briefanrede},

ich möchte Sie nicht weiter mit Nachrichten belasten – daher ein letztes Mal:

Falls Sie aktuell oder künftig einen verlässlichen Hausmeisterservice in {einsatzgebiet} suchen (z. B. als Vertretung, für neue Objekte oder zum Ausschreibungsstichtag), legen Sie diesen Brief gern zu Ihren Unterlagen. Wir erstellen Ihnen jederzeit ein Angebot innerhalb von 48 Stunden.

Mit freundlichen Grüßen

{firma_inhaber}
{firma_name}
Tel. {firma_telefon} · {firma_email} · {firma_web} """,
    },
}

ABMELDE_HINWEIS = (
    "\n--\nSie möchten keine weiteren Nachrichten von uns erhalten? "
    "Eine kurze Antwort mit „Abmelden“ genügt.\n"
)

ANFRAGE_AUTOANTWORT = {
    "betreff": "Ihre Anfrage bei {firma_name} – wir melden uns",
    "text": """{briefanrede},

vielen Dank für Ihre Anfrage! Wir haben sie erhalten und melden uns innerhalb von 24 Stunden (werktags) bei Ihnen – in der Regel telefonisch unter {telefon}.

Ihre Nachricht:
{nachricht}

Mit freundlichen Grüßen

{firma_inhaber}
{firma_name}
Tel. {firma_telefon}
""",
}

# ---------------------------------------------------------------------------
# Mieterkommunikation (eigene Immobilien)
# ---------------------------------------------------------------------------
ZAHLUNGSERINNERUNG = {
    1: {
        "betreff": "Zahlungserinnerung Miete {monat}",
        "text": """Hallo {mieter_name},

sicher ist es nur ein Versehen: Für {einheit} ist die Miete für {monat} in Höhe von {offen} € noch nicht (vollständig) bei uns eingegangen (fällig am {faellig_am}).

Bitte überweisen Sie den offenen Betrag in den nächsten Tagen auf folgendes Konto:
IBAN: {vermieter_iban}
Verwendungszweck: Miete {monat} {einheit}

Falls Sie bereits gezahlt haben, betrachten Sie diese Nachricht bitte als gegenstandslos.

Viele Grüße
{vermieter_name}
""",
    },
    2: {
        "betreff": "Mahnung – offene Miete {monat}",
        "text": """Guten Tag {mieter_name},

trotz unserer Zahlungserinnerung ist die Miete für {monat} ({einheit}) in Höhe von {offen} € weiterhin offen.

Wir bitten Sie, den Betrag bis spätestens {frist} zu überweisen:
IBAN: {vermieter_iban}
Verwendungszweck: Miete {monat} {einheit}

Sollten Sie in Zahlungsschwierigkeiten sein, sprechen Sie uns bitte an – gemeinsam finden wir meist eine Lösung. Andernfalls behalten wir uns weitere Schritte vor.

Mit freundlichen Grüßen
{vermieter_name}
""",
    },
}
