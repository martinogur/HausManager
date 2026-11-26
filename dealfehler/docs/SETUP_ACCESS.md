# Zugänge einrichten

Alle Werte kommen in die `.env` auf dem Server (nie ins Git). Nach jeder Änderung: `docker compose up -d`.
Dann im Dashboard → **API-Verbindungen → „Verbindungen live prüfen“**.

## 1. Amazon PartnerNet (Pflicht)

1. Konto unter partnernet.amazon.de, Website/Kanäle (Instagram, Pinterest, Telegram, WhatsApp, Domain) **alle angeben**.
2. Partner-ID (z.B. `dealfehler-21`) → `AMAZON_PARTNER_TAG`.
3. Empfohlen: je Kanal eine Tracking-ID anlegen → `AMAZON_CHANNEL_TRACKING_IDS=instagram=…-21,pinterest=…-21,telegram=…-21`.
   Dadurch zeigt der PartnerNet-Bericht, welcher Kanal Umsatz bringt.
4. Provisionsbericht regelmäßig als CSV exportieren → Dashboard → Affiliate-Umsätze → Import.
5. Beachte die Fristen: Für die Freischaltung sind qualifizierte Verkäufe innerhalb der ersten Monate nötig.

**Produktdaten von Amazon:** Die PA-API 5 wurde von Amazon durch die **Creators API** (OAuth 2.0, neue Zugangsdaten)
ersetzt; alte AWS-Schlüssel funktionieren dort nicht. Der Zugang setzt in der Regel qualifizierte Verkäufe voraus.
Ein Adapter dafür ist eine offene Aufgabe (TASKS.md) – bis dahin liefert Keepa die Preisdaten.

## 2. Keepa (Preisverläufe, empfohlen)

keepa.com → API-Zugang buchen (Token-basiert) → `KEEPA_API_KEY`. `KEEPA_DOMAIN=3` = amazon.de.
Der Deal Hunter nutzt den `/deal`-Endpunkt (Preisstürze ≥ 30 % in 24 h) und `/product` mit 90-Tage-Statistik.
Token-Verbrauch im Auge behalten (das Fehlerprotokoll zeigt Keepa-Fehler).

## 3. Medienspeicher (Pflicht für Instagram)

Instagram lädt Bilder/Videos selbst von einer **öffentlichen https-URL**. S3-kompatiblen Bucket anlegen
(z.B. Hetzner Object Storage), Objekte öffentlich lesbar, Versionierung an:
`STORAGE_BACKEND=s3`, `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_PUBLIC_BASE_URL`.

## 4. Telegram (einfachster vollautomatischer Kanal + Alarme)

1. @BotFather → neuer Bot → Token → `TELEGRAM_BOT_TOKEN`.
2. Öffentlichen Kanal `@dealfehler` anlegen, Bot als Administrator mit „Nachrichten senden“ hinzufügen → `TELEGRAM_CHANNEL_ID=@dealfehler`.
3. Alarme: dem Bot privat schreiben, Chat-ID ermitteln → `ALERT_TELEGRAM_CHAT_ID`.

## 5. Pinterest

1. Business-Konto, developers.pinterest.com → App anlegen, Zugang beantragen (Trial → Standard).
2. OAuth-Token mit Scopes `boards:read`, `boards:write`, `pins:read`, `pins:write`, `user_accounts:read` → `PINTEREST_ACCESS_TOKEN`.
3. Boards werden automatisch angelegt (Amazon Preisfehler-Verdacht, Technik Deals, Haushalt Deals, Werkzeug Angebote,
   Gaming Deals, Küche und Wohnen, Baby und Kinder, Tagesangebote). Pins verlinken auf die eigene Deal-Seite.
4. Hinweis: Access-Tokens laufen ab – Erneuerung per Refresh-Token ist noch manuell.

## 6. Instagram (Meta Graph API)

1. Instagram auf **Professional (Business/Creator)** umstellen und mit einer Facebook-Seite verknüpfen.
2. developers.facebook.com → App (Typ Business) → Produkt „Instagram“ → Berechtigungen
   `instagram_basic`, `instagram_content_publish`, `pages_show_list` (für Livebetrieb: App-Review).
3. Long-lived Access Token (~60 Tage) → `INSTAGRAM_ACCESS_TOKEN`; Instagram-Business-Account-ID → `INSTAGRAM_USER_ID`.
4. `META_GRAPH_VERSION` auf die aktuell unterstützte Version setzen.
5. Plattformseitige Veröffentlichungslimits fragt der Client über `content_publishing_limit` ab; unsere eigenen Limits liegen deutlich darunter.
6. Links in Captions sind auf Instagram nicht klickbar → Bio-Link auf die Website (Deal-Übersicht).

## 7. WhatsApp-Kanal

1. In WhatsApp: Aktualisierungen → Kanal erstellen „DealFehler“. Texte, Profilbild und Werbekonzept liefert das Dashboard
   (WhatsApp → Kanal-Paket; Profilbild unter `/api/channel-kit/profile.png`).
2. Einladungslink → `WHATSAPP_CHANNEL_INVITE_URL` (dann erscheint der QR-Code).
3. Veröffentlichung: Dashboard → WhatsApp → „Text kopieren“, Bild öffnen, im Kanal posten, „Als veröffentlicht markieren“.
   Es gibt keine offiziell freigegebene Kanal-API für Dritte; daher bewusst kein Bot.

## 8. Claude (optional)

console.anthropic.com → API-Key → `ANTHROPIC_API_KEY`. Budget über `LLM_DAILY_BUDGET_USD` / `LLM_MONTHLY_BUDGET_USD`.

## 9. Domain, Hosting, Search Console

* DNS: `www.` → Web-Container, `api.` → API-Container, beide hinter TLS-Proxy.
* `PUBLIC_BASE_URL`, `API_BASE_URL`, `NEXT_PUBLIC_API_URL`, `CORS_ORIGINS` setzen.
* Impressum + Datenschutz befüllen (`web/app/(site)/impressum`, `…/datenschutz`).
* Google Search Console: Domain bestätigen, `https://www.…/sitemap.xml` einreichen.

## 10. Livegang-Checkliste

- [ ] `SECRET_KEY` gesetzt (≥ 32 Zeichen), Admin-Passwort stark, danach `BOOTSTRAP_ADMIN_PASSWORD` aus `.env` entfernen
- [ ] Backups laufen (`./backups` enthält Dumps), Restore einmal getestet
- [ ] Alarme kommen an (Agent manuell mit falschem Key starten → Telegram-Nachricht)
- [ ] Je Plattform: Verbindung live geprüft → Tageslimit 1 → `DRY_RUN=false` → ersten Beitrag kontrollieren → Limit langsam erhöhen
