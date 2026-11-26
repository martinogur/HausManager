"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { act, ErrorBox, Stat, useApi } from "@/components/admin";
import { PublicationList } from "@/components/PublicationList";
import { api, PUBLIC_API } from "@/lib/api";
import { dt } from "@/lib/format";

const TITLES: Record<string, string> = {
  instagram: "Instagram (@dealfehler)", pinterest: "Pinterest", whatsapp: "WhatsApp-Kanal", telegram: "Telegram-Kanal",
  website: "Website",
};
const FIELDS: [string, string][] = [
  ["daily_limit", "Eigenes Tageslimit"], ["daily_limit_max", "Obergrenze für Ausbau"], ["ramp_step", "Ausbau pro Woche"],
  ["min_interval_minutes", "Mindestabstand (min)"], ["min_score", "Mindest-Score"], ["quiet_hours_start", "Ruhezeit ab (h)"],
  ["quiet_hours_end", "Ruhezeit bis (h)"], ["repost_cooldown_days", "Wiederholungs-Sperre (Tage)"],
];

export default function PlatformPage() {
  const { name } = useParams<{ name: string }>();
  const { data: all, error, reload } = useApi<any[]>("/api/platforms");
  const st = all?.find((p) => p.platform === name);
  const [form, setForm] = useState<Record<string, number>>({});
  useEffect(() => { if (st) setForm(Object.fromEntries(FIELDS.map(([k]) => [k, st[k]]))); }, [st]);
  const kit = useApi(name === "whatsapp" ? "/api/channel-kit/whatsapp" : null);
  if (!st) return <ErrorBox error={error} />;
  const save = (json: any) => act(() => api(`/api/platforms/${name}`, { method: "PATCH", json }), reload);
  return (
    <>
      <div className="topbar">
        <h1 className="grow">{TITLES[name] ?? name}</h1>
        <label className="row" style={{ color: "var(--text)" }}>
          <input type="checkbox" checked={st.enabled} onChange={(e) => save({ enabled: e.target.checked })} /> aktiv
        </label>
        {st.kill_switch
          ? <button className="btn primary" onClick={() => act(() => api(`/api/platforms/${name}/resume`, { method: "POST" }), reload)}>Not-Aus aufheben</button>
          : <button className="btn danger" onClick={() => act(() => api(`/api/platforms/${name}/kill`, { method: "POST" }), reload)}>Not-Aus {name}</button>}
      </div>
      {st.kill_switch && <div className="banner red">Not-Aus aktiv – auf {name} wird nichts veröffentlicht.</div>}
      {st.paused_until && new Date(st.paused_until) > new Date() &&
        <div className="banner warn">Automatisch pausiert bis {dt(st.paused_until)}: {st.pause_reason}</div>}
      <div className="grid stats">
        <Stat label="Veröffentlicht (24 h)" value={`${st.published_24h} / ${st.daily_limit}`} />
        <Stat label="Geplant" value={st.scheduled} />
        <Stat label="Fehler in Folge" value={st.consecutive_errors} />
        <Stat label="Modus" value={st.requires_manual_approval ? "Manuell" : "Automatisch"} />
      </div>
      <h2 style={{ marginTop: 20 }}>Frequenzmanagement</h2>
      <p className="muted small">Eigene, konservative Limits – keine Annahmen über Plattform-Maxima. Der Growth-Agent erhöht das
        Tageslimit höchstens einmal pro Woche um den Ausbauschritt, und nur ohne Fehler und mit Klicks.</p>
      <div className="card row">
        {FIELDS.map(([k, label]) => (
          <label key={k}>{label}<input type="number" value={form[k] ?? ""} style={{ width: 110 }}
            onChange={(e) => setForm({ ...form, [k]: +e.target.value })} /></label>
        ))}
        <button className="btn primary" onClick={() => save(form)}>Speichern</button>
      </div>
      {name === "whatsapp" && kit.data && (
        <>
          <h2 style={{ marginTop: 20 }}>Kanal-Paket</h2>
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
            <div className="card grid"><h3>Kanalname</h3><pre>{kit.data.name}</pre><h3>Beschreibung</h3><pre>{kit.data.description}</pre>
              <button className="btn" onClick={() => navigator.clipboard.writeText(kit.data.description)}>Beschreibung kopieren</button></div>
            <div className="card grid"><h3>Begrüßung</h3><pre>{kit.data.welcome}</pre>
              <h3>Profilbild</h3><img src={`${PUBLIC_API}/api/channel-kit/profile.png`} alt="Profilbild" style={{ width: 160 }} /></div>
            <div className="card grid"><h3>Werbekonzept</h3><ul>{kit.data.promotion.map((p: string) => <li key={p}>{p}</li>)}</ul>
              <h3>Regeln</h3><ul>{kit.data.posting_rules.map((p: string) => <li key={p}>{p}</li>)}</ul></div>
            <div className="card grid"><h3>Einladung & QR-Code</h3>
              {kit.data.qr_available
                ? <><a href={kit.data.invite_url} target="_blank" rel="noopener">{kit.data.invite_url}</a>
                    <img src={`${PUBLIC_API}/api/channel-kit/whatsapp/qr.png`} alt="QR-Code" style={{ width: 200 }} /></>
                : <p className="muted">Nach dem Anlegen des Kanals WHATSAPP_CHANNEL_INVITE_URL setzen – dann erscheint hier der QR-Code.</p>}
            </div>
          </div>
          <p className="muted small" style={{ marginTop: 12 }}>WhatsApp-Kanäle bieten keine offiziell freigegebene Veröffentlichungs-API für
            Dritte. Beiträge werden vorbereitet und hier per Klick freigegeben – keine WhatsApp-Web-Bots.</p>
        </>
      )}
      <h2 style={{ marginTop: 20 }}>Beiträge</h2>
      <PublicationList platform={name} manual={st.requires_manual_approval} />
    </>
  );
}
