"use client";
import Link from "next/link";
import { useState } from "react";
import { ErrorBox, StatusPill, useApi } from "@/components/admin";
import { CATEGORIES, dt, eur, STATUS_LABELS } from "@/lib/format";

export function DealsTable({ minScore = 0, title }: { minScore?: number; title: string }) {
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState(minScore >= 90 ? "score" : "created");
  const qs = new URLSearchParams({ min_score: String(minScore), sort, limit: "100" });
  if (status) qs.set("status", status);
  if (category) qs.set("category", category);
  if (q) qs.set("q", q);
  const { data, error } = useApi(`/api/deals?${qs}`);
  return (
    <>
      <div className="topbar">
        <h1 className="grow">{title}</h1>
        <input placeholder="Suche / ASIN" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="">Alle Status</option>
          {Object.entries(STATUS_LABELS).slice(0, 11).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Kategorie">
          <option value="">Alle Kategorien</option>
          {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sortierung">
          <option value="created">Neueste</option><option value="score">Score</option><option value="priority">Priorität</option>
        </select>
      </div>
      <ErrorBox error={error} />
      <p className="muted small">{data?.total ?? 0} Treffer</p>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Produkt</th><th>Status</th><th className="num">Score</th><th className="num">Preis</th>
            <th className="num">Ø 90 T.</th><th className="num">Rabatt</th><th>Quelle</th><th>Geprüft</th></tr></thead>
          <tbody>
            {data?.items.map((d: any) => (
              <tr key={d.id}>
                <td><Link href={`/admin/deals/${d.id}`}><strong>{d.title.slice(0, 70)}</strong></Link>
                  <div className="muted small">{d.label} · {CATEGORIES[d.category] ?? d.category} · {d.external_id}</div></td>
                <td><StatusPill s={d.status} /></td>
                <td className="num"><strong>{d.score}</strong></td>
                <td className="num">{eur(d.price_cents)}</td>
                <td className="num">{eur(d.reference_price_cents)}</td>
                <td className="num">{d.discount_pct ? `−${d.discount_pct} %` : "–"}</td>
                <td>{d.source}</td>
                <td className="small">{dt(d.price_checked_at)} ({d.verification_count}×)</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
