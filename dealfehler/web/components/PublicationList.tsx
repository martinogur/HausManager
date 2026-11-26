"use client";
import { act, ErrorBox, StatusPill, useApi } from "@/components/admin";
import { api } from "@/lib/api";
import { dt, eur } from "@/lib/format";

export function PublicationList({ platform, status, manual = false }: { platform?: string; status?: string; manual?: boolean }) {
  const qs = new URLSearchParams();
  if (platform) qs.set("platform", platform);
  if (status) qs.set("status", status);
  const { data, error, reload } = useApi<any[]>(`/api/publications?${qs}`);
  const post = (id: number, action: string, json: any = {}) =>
    act(() => api(`/api/publications/${id}/${action}`, { method: "POST", json }), reload);
  return (
    <>
      <ErrorBox error={error} />
      <div className="grid">
        {data?.length === 0 && <p className="muted">Keine Beiträge.</p>}
        {data?.map((p) => (
          <div key={p.id} className="card grid" style={{ gridTemplateColumns: "120px minmax(0,1fr)", alignItems: "start" }}>
            {p.media_url ? <img src={p.media_url} alt="" style={{ width: 120, borderRadius: 8 }} /> : <div />}
            <div className="grid" style={{ gap: 8 }}>
              <div className="row">
                <strong className="grow">{p.platform}{p.dry_run ? " · Testmodus" : ""} · {p.deal_title?.slice(0, 60)}</strong>
                <StatusPill s={p.status} /><span className="small muted">{eur(p.price_cents)}</span>
              </div>
              <div className="small muted">Geplant {dt(p.scheduled_at)} · Veröffentlicht {dt(p.published_at)}
                {p.external_url && <> · <a href={p.external_url} target="_blank" rel="noopener">ansehen</a></>}</div>
              {p.last_error && <div className="small error">{p.last_error}</div>}
              <details><summary className="small">Text anzeigen</summary><pre>{p.caption}</pre></details>
              <div className="row">
                {manual && p.status === "wartet_auf_freigabe" && (
                  <>
                    <button className="btn" onClick={() => navigator.clipboard.writeText(p.caption)}>Text kopieren</button>
                    {p.media_url && <a className="btn" href={p.media_url} download target="_blank" rel="noopener">Bild öffnen</a>}
                    <button className="btn primary" onClick={() => post(p.id, "mark-published")}>Als veröffentlicht markieren</button>
                  </>
                )}
                {p.status === "pausiert" && <button className="btn" onClick={() => post(p.id, "resume")}>Fortsetzen</button>}
                {["geplant", "pausiert", "wartet_auf_freigabe", "entwurf"].includes(p.status) &&
                  <button className="btn" onClick={() => post(p.id, "cancel")}>Abbrechen</button>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
