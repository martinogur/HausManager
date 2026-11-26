"use client";
import { useRef, useState } from "react";
import { ErrorBox, Stat, useApi } from "@/components/admin";
import { api } from "@/lib/api";
import { eur } from "@/lib/format";

export default function Revenue() {
  const [days, setDays] = useState(30);
  const { data, error, reload } = useApi(`/api/stats/revenue?days=${days}`);
  const file = useRef<HTMLInputElement>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const upload = async () => {
    const f = file.current?.files?.[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    try {
      const r = await api("/api/commissions/import", { method: "POST", body: fd });
      setMsg(`${r.added} Einträge importiert${r.errors.length ? `, ${r.errors.length} Fehler` : ""}`);
      reload();
    } catch (e: any) { setMsg(e.message); }
  };
  const sum = (s: string) => (data?.rows ?? []).filter((r: any) => r.status === s).reduce((a: number, r: any) => a + r.commission_cents, 0);
  return (
    <>
      <div className="topbar">
        <h1 className="grow">Affiliate-Umsätze</h1>
        <select value={days} onChange={(e) => setDays(+e.target.value)} aria-label="Zeitraum">
          <option value={7}>7 Tage</option><option value={30}>30 Tage</option><option value={90}>90 Tage</option><option value={365}>12 Monate</option>
        </select>
      </div>
      <ErrorBox error={error} />
      <p className="muted small">Nur echte Zahlen aus importierten Partnerprogramm-Berichten – keine Hochrechnungen.</p>
      <div className="grid stats">
        <Stat label="Bestätigt" value={eur(sum("confirmed"))} />
        <Stat label="Geschätzt (offen)" value={eur(sum("estimated"))} />
        <Stat label="Storniert" value={eur(sum("rejected"))} />
        <Stat label="Beiträge" value={data?.publications ?? "–"} />
        <Stat label="Bestätigt je Beitrag" value={data?.confirmed_commission_per_publication_cents != null ? eur(data.confirmed_commission_per_publication_cents) : "–"} />
        <Stat label="KI-Kosten je Beitrag" value={data?.cost_per_publication_usd != null ? `${data.cost_per_publication_usd} $` : "–"} />
      </div>
      <div className="card row" style={{ marginTop: 16 }}>
        <strong>Bericht importieren (CSV)</strong>
        <span className="muted small">Spalten: id, asin, date (JJJJ-MM-TT), revenue, commission, status</span>
        <input type="file" ref={file} accept=".csv,.tsv,.txt" /><button className="btn" onClick={upload}>Importieren</button>
        {msg && <span className="small">{msg}</span>}
      </div>
      <div className="table-wrap" style={{ marginTop: 16 }}><table><thead><tr><th>Netzwerk</th><th>Status</th>
        <th className="num">Bestellungen</th><th className="num">Umsatz</th><th className="num">Provision</th></tr></thead><tbody>
        {data?.rows.map((r: any, i: number) => <tr key={i}><td>{r.network}</td><td>{r.status}</td><td className="num">{r.orders}</td>
          <td className="num">{eur(r.revenue_cents)}</td><td className="num">{eur(r.commission_cents)}</td></tr>)}
      </tbody></table></div>
    </>
  );
}
