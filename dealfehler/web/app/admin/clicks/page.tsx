"use client";
import Link from "next/link";
import { useState } from "react";
import { Bars, ErrorBox, useApi } from "@/components/admin";
import { CATEGORIES } from "@/lib/format";

export default function Clicks() {
  const [days, setDays] = useState(30);
  const { data, error } = useApi(`/api/stats/clicks?days=${days}`);
  const growth = useApi<any[]>("/api/reports?kind=growth&limit=1");
  const g = growth.data?.[0]?.content;
  const toRows = (o: Record<string, number> = {}) => Object.entries(o).map(([k, v]) => ({ k, v }));
  return (
    <>
      <div className="topbar">
        <h1 className="grow">Klickstatistiken</h1>
        <select value={days} onChange={(e) => setDays(+e.target.value)} aria-label="Zeitraum">
          <option value={7}>7 Tage</option><option value={30}>30 Tage</option><option value={90}>90 Tage</option>
        </select>
      </div>
      <ErrorBox error={error} />
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
        <Bars data={toRows(data?.by_channel)} x="k" y="v" label="Klicks nach Kanal" />
        <Bars data={toRows(data?.by_category).map((r) => ({ ...r, k: CATEGORIES[r.k] ?? r.k }))} x="k" y="v" label="Klicks nach Kategorie" />
      </div>
      <h2 style={{ marginTop: 20 }}>Top-Deals</h2>
      <div className="table-wrap"><table><tbody>
        {data?.top_deals.map((t: any) => <tr key={t.deal_id}><td><Link href={`/admin/deals/${t.deal_id}`}>{t.title}</Link></td>
          <td className="num">{t.clicks}</td></tr>)}
      </tbody></table></div>
      {g && (
        <>
          <h2 style={{ marginTop: 20 }}>Growth-Agent: Erkenntnisse ({growth.data?.[0]?.period})</h2>
          <div className="card"><ul>{g.suggestions.map((s: string) => <li key={s}>{s}</li>)}</ul>
            <p className="small muted">Klicks je Beitrag: {g.clicks_per_publication} · Gelernte Kategorie-Gewichte: {JSON.stringify(g.category_weights)}</p>
          </div>
        </>
      )}
    </>
  );
}
