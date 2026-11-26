import Link from "next/link";
import { CATEGORIES, eur } from "@/lib/format";

export type PublicDeal = {
  slug: string; title: string; category: string; label: string; price_cents: number;
  reference_price_cents: number | null; discount_pct: number | null; active: boolean;
  price_stand: string | null; image_url: string | null; score: number;
};

export function DealCard({ d }: { d: PublicDeal }) {
  return (
    <Link href={`/deals/${d.slug}`} className={`card deal-card${d.active ? "" : " inactive"}`}>
      {d.image_url ? <img src={d.image_url} alt={d.title} loading="lazy" /> : null}
      <div className="row">
        <span className={`pill ${d.label === "Preisfehler-Verdacht" ? "neon" : ""}`}>{d.label}</span>
        <span className="pill">{CATEGORIES[d.category] ?? d.category}</span>
        {!d.active && <span className="pill red">Abgelaufen</span>}
      </div>
      <strong>{d.title}</strong>
      <div className="row">
        <span className="price">{eur(d.price_cents)}</span>
        {d.reference_price_cents && d.discount_pct ? (
          <span className="muted small">Ø 90 Tage {eur(d.reference_price_cents)} · −{Math.floor(d.discount_pct)} %</span>
        ) : null}
      </div>
      {d.price_stand && <span className="muted small">Preis Stand: {d.price_stand}</span>}
    </Link>
  );
}
