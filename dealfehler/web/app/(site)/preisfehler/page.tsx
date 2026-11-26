import { DealCard, PublicDeal } from "@/components/DealCard";
import { serverGet } from "@/lib/api";

export const revalidate = 60;
export const metadata = { title: "Preisfehler-Verdacht – auffällig günstige Angebote" };

export default async function PriceErrors() {
  const data = await serverGet<{ items: PublicDeal[] }>("/api/public/deals?type=preisfehler&include_expired=true");
  return (
    <section className="hero">
      <h1>Preisfehler-Verdacht</h1>
      <p className="muted">
        Preise, die mehrfach geprüft deutlich unter dem Median der letzten 90 Tage liegen (Score ≥ 90). Ein
        Verdacht ist keine Garantie: Händler können Bestellungen zu offensichtlichen Fehlpreisen stornieren.
      </p>
      <div className="grid cards" style={{ marginTop: 16 }}>
        {(data?.items ?? []).map((d) => <DealCard key={d.slug} d={d} />)}
      </div>
      {data && data.items.length === 0 && <p className="muted">Gerade kein Verdachtsfall.</p>}
    </section>
  );
}
