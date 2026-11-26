"use client";
import { useRef, useState } from "react";
import { DealsTable } from "@/components/DealsTable";
import { api } from "@/lib/api";

export default function Deals() {
  const file = useRef<HTMLInputElement>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [key, setKey] = useState(0);
  const upload = async () => {
    const f = file.current?.files?.[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    try {
      const r = await api("/api/products/import", { method: "POST", body: fd });
      setMsg(`${r.items} Zeilen, ${r.deals_created} neue Deals, ${r.errors.length} Fehler ${r.errors.slice(0, 3).join(" | ")}`);
      setKey((k) => k + 1);
    } catch (e: any) { setMsg(e.message); }
  };
  return (
    <>
      <div className="card row" style={{ marginBottom: 16 }}>
        <strong>Feed / CSV importieren</strong>
        <span className="muted small">Spalten: asin|external_id, title, price, url, category (optional: list_price, coupon_code)</span>
        <input type="file" ref={file} accept=".csv,.tsv,.txt" />
        <button className="btn" onClick={upload}>Importieren</button>
        {msg && <span className="small">{msg}</span>}
      </div>
      <DealsTable key={key} title="Gefundene Deals" />
    </>
  );
}
