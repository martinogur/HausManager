"use client";
import { useState } from "react";
import { PublicationList } from "@/components/PublicationList";
import { STATUS_LABELS } from "@/lib/format";

export default function Publications() {
  const [platform, setPlatform] = useState("");
  const [status, setStatus] = useState("");
  return (
    <>
      <div className="topbar">
        <h1 className="grow">Veröffentlichungen</h1>
        <select value={platform} onChange={(e) => setPlatform(e.target.value)} aria-label="Plattform">
          <option value="">Alle Plattformen</option>
          {["instagram", "pinterest", "telegram", "whatsapp", "website"].map((p) => <option key={p}>{p}</option>)}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="">Alle Status</option>
          {["entwurf", "wartet_auf_freigabe", "geplant", "veroeffentlicht", "pausiert", "fehlgeschlagen", "abgebrochen"].map((s) =>
            <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
        </select>
      </div>
      <PublicationList key={platform + status} platform={platform || undefined} status={status || undefined} manual />
    </>
  );
}
