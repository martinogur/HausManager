# Compliance – wie das System die Regeln durchsetzt

> Kein Rechtsrat. Die Regeln bilden die gängigen Anforderungen ab (Werbekennzeichnung, PartnerNet-Bedingungen,
> Preisangaben, Plattformrichtlinien). Bitte die jeweils aktuellen Bedingungen selbst prüfen.

| Anforderung | Umsetzung | Code |
|---|---|---|
| Werbekennzeichnung sichtbar | Jeder Social-Text beginnt mit „Anzeige“; Grafiken tragen „ANZEIGE · Affiliate-Link“; Compliance blockiert sonst | `domain/compliance.py` AD_MARKER_MISSING |
| Amazon-Partnerhinweis | „Als Amazon-Partner verdiene ich an qualifizierten Verkäufen.“ in Texten, auf jeder Website-Seite (Footer + Deal) | AMAZON_DISCLOSURE_MISSING / AFFILIATE_HINT_MISSING |
| Preis & Verfügbarkeit aktuell | Preis max. 60 min alt bei Veröffentlichung (sonst Nachprüfung); Zeitstempel „Preis Stand“ in Text und Bild; Preisüberwachung alle 15 min pausiert geplante Beiträge | PRICE_STALE, PRICE_TIMESTAMP_MISSING |
| Keine irreführenden Rabatte | Referenz = Median eigener Messungen 90 T. (nicht UVP); angegebene Prozente werden gegen den berechneten Rabatt geprüft; UVP-Referenz wird auf der Website nicht als Rabatt angezeigt | DISCOUNT_OVERSTATED |
| „Preisfehler“ nur mit Nachweis | Standard „Preisfehler-Verdacht“; nur Admin kann bestätigen | PRICE_ERROR_UNCONFIRMED |
| Keine künstliche Dringlichkeit | „nur heute“ etc. nur mit bekanntem Enddatum; „garantiert“, „100 % sicher“, „gratis“ blockiert | UNVERIFIED_URGENCY, MISLEADING_PHRASE |
| Bildrechte | Nur selbst erzeugte Grafiken (`license=generated`); keine Amazon-Produktbilder | MEDIA_LICENSE |
| Grafik = aktueller Preis | Gerenderter Preis wird gespeichert und verglichen | MEDIA_PRICE_MISMATCH |
| Keine Link-Verschleierung | Direkter `amazon.de/dp/ASIN?tag=…`-Link, `rel="sponsored"`; Social-Beiträge verlinken auf die eigene Deal-Seite; keine Kurzlinks | `domain/affiliate.py`, `BuyButton.tsx` |
| Keine Testdaten öffentlich | Quelle `demo` wird immer blockiert | DEMO_DATA |
| Plattformregeln | Textlängen, max. 30 Hashtags (Instagram), keine automatisierten Kommentare/Likes/Follows (nicht implementiert, bewusst) | TEXT_TOO_LONG, TOO_MANY_HASHTAGS |
| Spam-Vermeidung | Eigene Limits, Mindestabstände, Ruhezeiten, Wiederholungssperre 14 T., Mindest-Score je Plattform | `domain/frequency.py`, `domain/dedup.py` |
| Datenschutz | Keine Cookies/Tracker; Klicks ohne IP, nur täglich rotierender Hash | `api/public.py` |

## Bekannte Punkte zur eigenen Prüfung

* **E-Mail/Newsletter:** Amazon schränkt Partnerlinks in E-Mails ein. Deshalb soll ein Newsletter auf die eigene
  Website verlinken, nicht direkt auf Amazon (so ist der Kanal `newsletter` vorbereitet: manuell + Website-Links).
* **Messenger (WhatsApp/Telegram):** Beiträge verlinken auf die eigene Deal-Seite (`?src=…`), von dort direkter Amazon-Link.
  Kanäle in PartnerNet als Werbefläche angeben.
* **Impressumspflicht** gilt auch für Social-Media-Profile (Link zum Impressum in der Bio).
