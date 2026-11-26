"use client";
import { useState } from "react";
import { act, ErrorBox, useApi } from "@/components/admin";
import { api } from "@/lib/api";
import { dt } from "@/lib/format";

export default function Errors() {
  const [all, setAll] = useState(false);
  const { data, error, reload } = useApi<any[]>(`/api/errors?include_resolved=${all}`);
  return (
    <>
      <div className="topbar">
        <h1 className="grow">Fehlerprotokoll</h1>
        <label className="row" style={{ color: "var(--text)" }}><input type="checkbox" checked={all} onChange={(e) => setAll(e.target.checked)} /> erledigte anzeigen</label>
      </div>
      <ErrorBox error={error} />
      <div className="table-wrap"><table><thead><tr><th>Zeit</th><th>Quelle</th><th>Meldung</th><th></th></tr></thead><tbody>
        {data?.map((e) => (
          <tr key={e.id}><td className="small">{dt(e.created_at)}</td><td><span className={`pill ${e.level === "error" ? "red" : "warn"}`}>{e.source}</span></td>
            <td className="small">{e.message}{Object.keys(e.context || {}).length > 0 && <details><summary>Kontext</summary><pre>{JSON.stringify(e.context, null, 2)}</pre></details>}</td>
            <td>{!e.resolved && <button className="btn" onClick={() => act(() => api(`/api/errors/${e.id}/resolve`, { method: "POST" }), reload)}>Erledigt</button>}</td></tr>
        ))}
      </tbody></table></div>
    </>
  );
}
