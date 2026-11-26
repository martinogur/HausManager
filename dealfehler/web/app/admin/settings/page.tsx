"use client";
import { useState } from "react";
import { act, ErrorBox, useApi } from "@/components/admin";
import { api } from "@/lib/api";

export default function Settings() {
  const { data, error, reload } = useApi("/api/settings");
  const users = useApi<any[]>("/api/users");
  const [nu, setNu] = useState({ email: "", password: "", role: "viewer" });
  return (
    <>
      <h1>Einstellungen</h1>
      <ErrorBox error={error} />
      {data && (
        <div className="card grid">
          <label className="row" style={{ color: "var(--text)" }}>
            <input type="checkbox" checked={data.demo_mode}
              onChange={(e) => act(() => api("/api/settings", { method: "PATCH", json: { demo_mode: e.target.checked } }), reload)} />
            Demo-Modus (Beispieldaten für die Oberfläche – werden von der Compliance nie veröffentlicht)
          </label>
          <div className="small muted">Testmodus DRY_RUN: <strong>{String(data.dry_run)}</strong> · Zeitzone {data.timezone} ·
            Max. Preisalter vor Veröffentlichung {data.max_price_age_minutes} min · Website {data.public_base_url}</div>
          <details><summary>Gelernte Gewichte (Lernsystem)</summary><pre>{JSON.stringify(data.learning, null, 2)}</pre></details>
        </div>
      )}
      <h2 style={{ marginTop: 20 }}>Benutzer & Rollen</h2>
      <p className="muted small">viewer = lesen · editor = Deals prüfen, Beiträge freigeben, Not-Aus auslösen · admin = alles inkl. Limits, Not-Aus aufheben, Benutzer</p>
      <ErrorBox error={users.error} />
      {users.data && (
        <div className="table-wrap"><table><tbody>
          {users.data.map((u) => (
            <tr key={u.id}><td>{u.email}</td>
              <td><select value={u.role} onChange={(e) => act(() => api(`/api/users/${u.id}`, { method: "PATCH", json: { role: e.target.value } }), users.reload)}>
                <option>viewer</option><option>editor</option><option>admin</option></select></td>
              <td><button className="btn" onClick={() => act(() => api(`/api/users/${u.id}`, { method: "PATCH", json: { is_active: !u.is_active } }), users.reload)}>
                {u.is_active ? "Deaktivieren" : "Aktivieren"}</button></td></tr>
          ))}
        </tbody></table></div>
      )}
      <div className="card row" style={{ marginTop: 12 }}>
        <input placeholder="E-Mail" value={nu.email} onChange={(e) => setNu({ ...nu, email: e.target.value })} />
        <input placeholder="Passwort (min. 10 Zeichen)" type="password" value={nu.password} onChange={(e) => setNu({ ...nu, password: e.target.value })} />
        <select value={nu.role} onChange={(e) => setNu({ ...nu, role: e.target.value })}><option>viewer</option><option>editor</option><option>admin</option></select>
        <button className="btn primary" onClick={() => act(() => api("/api/users", { method: "POST", json: nu }), users.reload)}>Benutzer anlegen</button>
      </div>
    </>
  );
}
