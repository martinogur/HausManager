"use client";
import { useState } from "react";
import { ErrorBox, useApi } from "@/components/admin";

export default function Connections() {
  const [check, setCheck] = useState(false);
  const { data, error, loading } = useApi(`/api/connections?check=${check}`);
  return (
    <>
      <div className="topbar">
        <h1 className="grow">API-Verbindungen</h1>
        <button className="btn" onClick={() => setCheck(true)} disabled={loading}>Verbindungen live prüfen</button>
      </div>
      <ErrorBox error={error} />
      {data?.dry_run && <div className="banner warn">DRY_RUN=true – Veröffentlichungen werden simuliert. Erst nach erfolgreicher Live-Prüfung umstellen.</div>}
      <p className="muted small">Zugangsdaten werden ausschließlich als Umgebungsvariablen gesetzt (.env / Secrets), nie im Dashboard
        gespeichert. Anleitung: docs/SETUP_ACCESS.md.</p>
      <div className="table-wrap"><table><thead><tr><th>Dienst</th><th>Konfiguriert</th><th>Details</th></tr></thead><tbody>
        {data?.items.map((i: any) => (
          <tr key={i.key}><td><strong>{i.name}</strong></td>
            <td>{i.configured ? <span className="pill neon">ja</span> : <span className="pill red">nein</span>}</td>
            <td className="small">{i.detail}{i.health && <pre>{JSON.stringify(i.health)}</pre>}</td></tr>
        ))}
      </tbody></table></div>
    </>
  );
}
