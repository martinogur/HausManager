import Link from "next/link";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <header className="site-header">
        <div className="container">
          <Link href="/" className="logo">DEAL<span>FEHLER</span></Link>
          <nav>
            <Link href="/">Aktuelle Deals</Link>
            <Link href="/preisfehler">Preisfehler-Verdacht</Link>
            <Link href="/?category=technik">Technik</Link>
            <Link href="/?category=haushalt">Haushalt</Link>
            <Link href="/?category=werkzeug">Werkzeug</Link>
            <Link href="/?category=gaming">Gaming</Link>
          </nav>
        </div>
      </header>
      <main className="container">{children}</main>
      <footer className="site-footer">
        <div className="container grid">
          <p className="disclosure">
            Werbehinweis: Links zu Händlern sind Affiliate-Links (Anzeige). Als Amazon-Partner verdiene ich an
            qualifizierten Verkäufen. Für dich entstehen keine Mehrkosten. Preise und Verfügbarkeit können sich
            jederzeit ändern; maßgeblich ist der Preis beim Händler zum Kaufzeitpunkt.
          </p>
          <p className="disclosure">
            Unsere Vergleichspreise sind der Median unserer eigenen Preisbeobachtungen der letzten 90 Tage – nicht die
            UVP. „Preisfehler-Verdacht“ bedeutet einen ungewöhnlich niedrigen Preis; ob der Händler liefert, ist offen.
          </p>
          <div className="row">
            <Link href="/impressum">Impressum</Link>
            <Link href="/datenschutz">Datenschutz</Link>
          </div>
        </div>
      </footer>
    </>
  );
}
