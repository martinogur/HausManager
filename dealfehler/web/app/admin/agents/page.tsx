"use client";
import { useState } from "react";
import { act, ErrorBox, useApi } from "@/components/admin";
import { api } from "@/lib/api";
import { dt } from "@/lib/format";

export default function Agents() {
  const { data, error, reload } = useApi<any[]>("/api/agents");
  const [open, setOpen] = useState<string | null>(null);
  const runs = useApi<any[]>(open ? `/api/agents/${open}/runs` : null);
  return (
    <>
      <h1>Agentenverwaltung</h1>
      <ErrorBox error={error} />
      <div className="table-wrap"><table><thead><tr><th>Agent</th><th>Status</th><th>Letzter Lauf</th><th className="num">Läufe</th><th></th></tr></thead><tbody>
        {data?.map((a) => (
          <tr key={a.name}>
            <td><strong>{a.title}</strong><div className="muted small">{a.description}</div>
              {a.last_error && <div className="small error">{a.last_error.slice(0, 200)}</div>}</td>
            <td>{a.enabled ? <span className="pill neon">aktiv</span> : <span className="pill red">pausiert</span>}
              {a.consecutive_failures > 0 && <div className="small error">{a.consecutive_failures} Fehler in Folge</div>}</td>
            <td className="small">{dt(a.last_run_at)} {a.last_status && `(${a.last_status})`}</td>
            <td className="num">{a.run_count}</td>
            <td><div className="row">
              <button className="btn" onClick={() => act(() => api(`/api/agents/${a.name}/run`, { method: "POST" }), reload)}>Jetzt ausführen</button>
              <button className="btn" onClick={() => act(() => api(`/api/agents/${a.name}`, { method: "PATCH", json: { enabled: !a.enabled } }), reload)}>
                {a.enabled ? "Pausieren" : "Aktivieren"}</button>
              <button className="btn" onClick={() => setOpen(open === a.name ? null : a.name)}>Protokoll</button>
            </div></td>
          </tr>
        ))}
      </tbody></table></div>
      {open && runs.data && (
        <>
          <h2 style={{ marginTop: 20 }}>Läufe: {open}</h2>
          <div className="table-wrap"><table><tbody>
            {runs.data.map((r) => <tr key={r.id}><td className="small">{dt(r.started_at)}</td><td>{r.status}</td>
              <td><pre>{JSON.stringify(r.stats)}</pre>{r.error && <div className="error small">{r.error}</div>}</td></tr>)}
          </tbody></table></div>
        </>
      )}
    </>
  );
}
