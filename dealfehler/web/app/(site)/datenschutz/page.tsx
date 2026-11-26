export const metadata = { title: "Datenschutz", robots: { index: false } };

export default function Datenschutz() {
  return (
    <section className="hero">
      <h1>Datenschutzerklärung</h1>
      <p className="error">Platzhalter – vor dem Livegang durch eine vollständige Datenschutzerklärung ersetzen.</p>
      <h2>Technische Fakten zur Erstellung der Erklärung</h2>
      <ul>
        <li>Keine Cookies, kein Tracking-Pixel, keine Analyse-Dienste von Drittanbietern.</li>
        <li>Klickzählung auf Affiliate-Buttons: Es wird keine IP-Adresse gespeichert, nur ein täglich wechselnder,
          gesalzener Hash (IP + Browserkennung + Datum) zur Dublettenerkennung.</li>
        <li>Affiliate-Links führen zu Amazon; dort gelten die Datenschutzhinweise von Amazon (Partnerprogramm-Cookie).</li>
      </ul>
    </section>
  );
}
