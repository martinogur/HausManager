import Link from "next/link";
import { notFound } from "next/navigation";
import { BuyButton } from "@/components/BuyButton";
import { DealCard, PublicDeal } from "@/components/DealCard";
import { PriceChart } from "@/components/PriceChart";
import { serverGet } from "@/lib/api";
import { CATEGORIES, eur } from "@/lib/format";

export const revalidate = 60;

type Detail = PublicDeal & {
  text: string; affiliate_url: string | null; coupon_code: string | null; brand: string | null;
  price_history: { date: string; price_cents: number }[]; reference_explanation: string; disclosure: string;
  related: PublicDeal[]; price_checked_at: string | null; updated_at: string;
};
type Props = { params: Promise<{ slug: string }>; searchParams: Promise<{ src?: string }> };

export async function generateMetadata({ params }: Props) {
  const { slug } = await params;
  const d = await serverGet<Detail>(`/api/public/deals/${slug}`);
  if (!d) return { title: "Deal nicht gefunden" };
  return {
    title: `${d.title} für ${eur(d.price_cents)}`,
    description: d.text.slice(0, 155),
    alternates: { canonical: `/deals/${slug}` },
    openGraph: { images: d.image_url ? [d.image_url] : [] },
    robots: d.active ? undefined : { index: false },
  };
}

export default async function DealPage({ params, searchParams }: Props) {
  const { slug } = await params;
  const { src } = await searchParams;
  const d = await serverGet<Detail>(`/api/public/deals/${slug}${src ? `?src=${encodeURIComponent(src)}` : ""}`);
  if (!d) notFound();
  const jsonLd = {
    "@context": "https://schema.org", "@type": "Product", name: d.title,
    ...(d.brand ? { brand: { "@type": "Brand", name: d.brand } } : {}),
    ...(d.image_url ? { image: d.image_url } : {}),
    offers: {
      "@type": "Offer", priceCurrency: "EUR", price: (d.price_cents / 100).toFixed(2),
      availability: d.active ? "https://schema.org/InStock" : "https://schema.org/OutOfStock",
      ...(d.affiliate_url ? { url: d.affiliate_url } : {}),
    },
  };
  return (
    <article style={{ paddingTop: 24 }}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <p className="small"><Link href="/">Deals</Link> › <Link href={`/?category=${d.category}`}>{CATEGORIES[d.category] ?? d.category}</Link></p>
      <div className="detail">
        <div>{d.image_url && <img src={d.image_url} alt={`${d.title} – ${d.label}`} />}</div>
        <div className="grid" style={{ alignContent: "start" }}>
          <div className="row">
            <span className={`pill ${d.label === "Preisfehler-Verdacht" ? "neon" : ""}`}>{d.label}</span>
            {!d.active && <span className="pill red">Angebot abgelaufen</span>}
          </div>
          <h1>{d.title}</h1>
          <div className="big-price">{eur(d.price_cents)}</div>
          {d.reference_price_cents && d.discount_pct ? (
            <p className="muted">Ø-Preis der letzten 90 Tage: {eur(d.reference_price_cents)} (−{Math.floor(d.discount_pct)} %)</p>
          ) : null}
          {d.price_stand && <p className="small muted">Preis Stand: {d.price_stand}. Preise können sich jederzeit ändern.</p>}
          {d.coupon_code && <p>Gutscheincode: <strong>{d.coupon_code}</strong></p>}
          {d.affiliate_url ? <BuyButton url={d.affiliate_url} slug={d.slug} src={src} /> :
            <p className="muted">Dieses Angebot ist nicht mehr aktiv.</p>}
          <p className="disclosure">* Anzeige / Affiliate-Link. {d.disclosure}</p>
        </div>
      </div>
      <section className="card" style={{ marginTop: 24 }}>
        <h2>Einordnung</h2>
        <p>{d.text}</p>
        <PriceChart points={d.price_history} current={d.price_cents} />
        <p className="muted small">{d.reference_explanation}</p>
      </section>
      {d.related.length > 0 && (
        <section style={{ marginTop: 24 }}>
          <h2>Weitere Deals aus {CATEGORIES[d.category] ?? d.category}</h2>
          <div className="grid cards">{d.related.map((r) => <DealCard key={r.slug} d={r} />)}</div>
        </section>
      )}
    </article>
  );
}
