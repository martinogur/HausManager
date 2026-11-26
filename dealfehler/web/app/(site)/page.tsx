import Link from "next/link";
import { DealCard, PublicDeal } from "@/components/DealCard";
import { serverGet } from "@/lib/api";
import { CATEGORIES } from "@/lib/format";

export const revalidate = 60;

type Props = { searchParams: Promise<Record<string, string | undefined>> };

export async function generateMetadata({ searchParams }: Props) {
  const sp = await searchParams;
  const cat = sp.category ? CATEGORIES[sp.category] : null;
  return { title: cat ? `${cat} Deals & Angebote` : "Aktuelle Deals", alternates: { canonical: cat ? `/?category=${sp.category}` : "/" } };
}

export default async function Home({ searchParams }: Props) {
  const sp = await searchParams;
  const qs = new URLSearchParams();
  if (sp.category) qs.set("category", sp.category);
  if (sp.q) qs.set("q", sp.q);
  if (sp.page) qs.set("page", sp.page);
  const data = await serverGet<{ total: number; items: PublicDeal[] }>(`/api/public/deals?${qs}`);
  const cats = (await serverGet<{ category: string; count: number }[]>("/api/public/categories")) ?? [];
  return (
    <>
      <section className="hero">
        <h1>Gute Deals. <b>Schlechte Preise.</b> Dein Vorteil.</h1>
        <p className="muted">Jeder Deal wird gegen unsere eigene Preishistorie geprüft – keine Mondpreise, keine UVP-Tricks.</p>
        <form className="row" action="/">
          <input name="q" defaultValue={sp.q} placeholder="Produkt suchen …" aria-label="Suche" />
          {sp.category && <input type="hidden" name="category" value={sp.category} />}
          <button className="btn">Suchen</button>
        </form>
      </section>
      <div className="chips" style={{ margin: "12px 0 20px" }}>
        <Link href="/" className={`pill ${!sp.category ? "neon" : ""}`}>Alle</Link>
        {cats.map((c) => (
          <Link key={c.category} href={`/?category=${c.category}`} className={`pill ${sp.category === c.category ? "neon" : ""}`}>
            {CATEGORIES[c.category] ?? c.category} ({c.count})
          </Link>
        ))}
      </div>
      {!data ? (
        <p className="error">Deals konnten gerade nicht geladen werden.</p>
      ) : data.items.length === 0 ? (
        <p className="muted">Aktuell keine passenden Deals. Schau bald wieder vorbei.</p>
      ) : (
        <div className="grid cards">{data.items.map((d) => <DealCard key={d.slug} d={d} />)}</div>
      )}
    </>
  );
}
