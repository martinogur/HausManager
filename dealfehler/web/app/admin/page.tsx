"use client";
import { useState } from "react";
import { act, Bars, ErrorBox, Stat, useApi } from "@/components/admin";
import { api } from "@/lib/api";
import { eur, STATUS_LABELS } from "@/lib/format";

export default function Overview() {
  const [days, setDays] = useState(1);
  const [platform, setPlatform] = useState("");
  const { data: o, error, reload } = useApi(`/api/dashboard/overview?days=${days}${platform ? `&platform=${platform}` : ""}`);
  return (
    <>
      <div className="topbar">
        <h1 className="grow">Übersicht</h1>
        <select value={days} onChange={(e) => setDays(+e.target.value)} aria-label="Zeitraum">
          <option value={1}>Heute (24 h)</option><option value={7}>7 Tage</option>
          <option value={30}>30 Tage</option><option value={90}>90 Tage</option>
        </select>
        <select value={platform} onChange={(e) => setPlatform(e.target.value)} aria-label="Plattform">
          <option value="">Alle Plattformen</option>
          {["instagram", "pinterest", "telegram", "whatsapp", "website"].map((p) => <option key={p}>{p}</option>)}
        </select>
        <button className="btn" onClick={() => act(() => api("/api/agents/master/run", { method: "POST" }), reload)}>
          Master-Zyklus starten
        </button>
        {o && (o.global_kill_switch
          ? <button className="btn primary" onClick={() => act(() => api("/api/system/kill-switch", { method: "POST", json: { active: false } }), reload)}>Not-Aus aufheben</button>
          : <button className="btn danger" onClick={() => confirm("Alle Veröffentlichungen sofort stoppen?") && act(() => api("/api/system/kill-switch", { method: "POST", json: { active: true } }), reload)}>NOT-AUS</button>)}
      </div>
      <ErrorBox error={error} />
      {o?.global_kill_switch && <div className="banner red">Globaler Not-Aus aktiv – es wird nichts veröffentlicht und keine Pipeline läuft.</div>}
      {o?.dry_run && <div className="banner warn">Testmodus (DRY_RUN): Social-Media-Beiträge werden nur simuliert, nichts wird extern veröffentlicht.</div>}
      {o && (
        <>
          <div className="grid stats">
            <Stat label="Deals gefunden" value={o.deals_found} />
            <Stat label="Preisfehler-Verdacht" value={o.price_error_suspects} />
            <Stat label="Veröffentlicht" value={o.published} hint={Object.entries(o.published_by_platform).map(([k, v]) => `${k} ${v}`).join(" · ")} />
            <Stat label="Instagram-Reichweite" value={o.instagram_reach} hint="aus Insights, sofern verbunden" />
            <Stat label="Pinterest-Impressionen" value={o.pinterest_impressions} />
            <Stat label="WhatsApp" value={`${o.whatsapp_published} / ${o.whatsapp_pending}`} hint="veröffentlicht / wartet" />
            <Stat label="Affiliate-Klicks" value={o.clicks} />
            <Stat label="Provision geschätzt" value={eur(o.commission_estimated_cents)} hint="laut importiertem Bericht" />
            <Stat label="Provision bestätigt" value={eur(o.commission_confirmed_cents)} />
            <Stat label="Kosten (KI)" value={`${o.cost_usd.toFixed(2)} $`} />
            <Stat label="Fehler" value={o.errors} />
          </div>
          <h2 style={{ marginTop: 24 }}>Entwicklung</h2>
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
            <Bars data={o.series} x="date" y="deals" label="Gefundene Deals pro Tag" />
            <Bars data={o.series} x="date" y="published" label="Veröffentlichungen pro Tag" />
            <Bars data={o.series} x="date" y="clicks" label="Affiliate-Klicks pro Tag" />
            <Bars data={o.series} x="date" y="commission_cents" label="Provision pro Tag (importiert)" format={(v) => eur(v)} />
          </div>
          <h2 style={{ marginTop: 24 }}>Pipeline</h2>
          <div className="chips">
            {Object.entries(o.pipeline).map(([k, v]) => <span key={k} className="pill">{STATUS_LABELS[k] ?? k}: {String(v)}</span>)}
          </div>
        </>
      )}
    </>
  );
}
