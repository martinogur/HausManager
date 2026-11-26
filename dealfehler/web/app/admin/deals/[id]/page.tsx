"use client";
import { useParams } from "next/navigation";
import { useState } from "react";
import { act, ErrorBox, StatusPill, useApi } from "@/components/admin";
import { api } from "@/lib/api";
import { dt, eur } from "@/lib/format";

export default function DealDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: d, error, reload } = useApi(`/api/deals/${id}`);
  const [price, setPrice] = useState("");
  const [note, setNote] = useState<string | null>(null);
  if (!d) return <ErrorBox error={error} />;
  const patch = (json: any) => act(() => api(`/api/deals/${id}`, { method: "PATCH", json }), reload);
  return (
    <>
      <div className="topbar">
        <h1 className="grow">{d.title}</h1>
        <StatusPill s={d.status} />
        <span className="pill neon">Score {d.score}</span>
      </div>
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
        <div className="card grid">
          <div className="big-price">{eur(d.price_cents)}</div>
          <div className="muted small">Referenz ({d.reference_kind ?? "–"}): {eur(d.reference_price_cents)} · Rabatt {d.discount_pct ?? 0} %</div>
          <div className="small">Preis geprüft: {dt(d.price_checked_at)} · {d.verification_count}× verifiziert</div>
          <div className="small">{d.label} · {d.merchant} · {d.external_id} · Quelle {d.source}</div>
          <div className="row">
            <input placeholder="Preis z.B. 19,99" value={price} onChange={(e) => setPrice(e.target.value)} style={{ width: 130 }} />
            <button className="btn" onClick={() => act(() => api(`/api/deals/${id}/confirm-price`, { method: "POST", json: { price } }), reload)}>
              Preis manuell bestätigen
            </button>
          </div>
          <div className="row">
            <button className="btn" onClick={() => patch({ status: "abgelaufen", note: "manuell" })}>Als abgelaufen markieren</button>
            <button className="btn" onClick={() => patch({ status: "abgelehnt", note: "manuell" })}>Ablehnen</button>
            <button className="btn" onClick={() => confirm("Preisfehler wirklich nachgewiesen? Danach darf 'Preisfehler' ohne 'Verdacht' verwendet werden.") && patch({ confirmed_price_error: !d.confirmed_price_error })}>
              {d.confirmed_price_error ? "Preisfehler-Bestätigung entfernen" : "Preisfehler bestätigen (Admin)"}
            </button>
          </div>
        </div>
        <div className="card grid">
          <h3>Redaktioneller Mehrwert (Website)</h3>
          <textarea defaultValue={d.editorial_note ?? ""} onChange={(e) => setNote(e.target.value)}
            placeholder="Kurze Einordnung: Für wen lohnt sich das Produkt? Worauf achten?" />
          <button className="btn" disabled={note === null} onClick={() => patch({ editorial_note: note })}>Speichern</button>
        </div>
        <div className="card">
          <h3>Score-Aufschlüsselung</h3>
          <pre>{JSON.stringify(d.score_breakdown, null, 2)}</pre>
        </div>
      </div>
      <h2 style={{ marginTop: 20 }}>Affiliate-Links</h2>
      <div className="table-wrap"><table><thead><tr><th>Kanal</th><th>Netzwerk</th><th>Link</th><th>Status</th></tr></thead><tbody>
        {d.links.map((l: any) => <tr key={l.id}><td>{l.channel}</td><td>{l.network}</td>
          <td className="small"><a href={l.url} target="_blank" rel="noopener">{l.url}</a></td>
          <td>{l.is_valid ? <span className="pill neon">gültig</span> : <span className="pill red">{l.check_error}</span>}</td></tr>)}
      </tbody></table></div>
      <h2 style={{ marginTop: 20 }}>Medien</h2>
      <div className="row">{d.media.map((m: any) => (
        <a key={m.id} href={m.url} target="_blank" rel="noopener" title={`${m.kind} · ${m.template}`}>
          <img src={m.url} alt={m.kind} style={{ height: 160, borderRadius: 8 }} />
        </a>))}</div>
      <h2 style={{ marginTop: 20 }}>Beiträge</h2>
      <div className="table-wrap"><table><thead><tr><th>Plattform</th><th>Status</th><th>Geplant</th><th>Fehler</th></tr></thead><tbody>
        {d.publications.map((p: any) => <tr key={p.id}><td>{p.platform}{p.dry_run ? " (Test)" : ""}</td><td><StatusPill s={p.status} /></td>
          <td className="small">{dt(p.scheduled_at)}</td><td className="small error">{p.last_error}</td></tr>)}
      </tbody></table></div>
      <h2 style={{ marginTop: 20 }}>Verlauf</h2>
      <div className="table-wrap"><table><tbody>
        {d.events.map((e: any, i: number) => <tr key={i}><td className="small">{dt(e.at)}</td><td>{e.from ?? "–"} → <strong>{e.to}</strong></td>
          <td className="small">{e.actor}</td><td className="small">{e.note}</td></tr>)}
      </tbody></table></div>
    </>
  );
}
