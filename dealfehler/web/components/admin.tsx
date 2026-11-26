"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { STATUS_LABELS } from "@/lib/format";

export function useApi<T = any>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const reload = useCallback(async () => {
    if (!path) return;
    setLoading(true);
    try {
      setData(await api<T>(path));
      setError(null);
    } catch (e: any) {
      setError(e.message || "Fehler");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]);
  useEffect(() => { reload(); }, [reload]);
  return { data, error, loading, reload, setData };
}

export function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="card stat">
      <div className="v">{value}</div>
      <div className="l">{label}</div>
      {hint && <div className="muted small">{hint}</div>}
    </div>
  );
}

export function StatusPill({ s }: { s: string }) {
  const cls = ["veroeffentlicht", "verifiziert", "freigegeben"].includes(s) ? "neon"
    : ["fehlerhaft", "fehlgeschlagen"].includes(s) ? "red"
    : ["pausiert", "preis_geaendert", "wartet_auf_freigabe"].includes(s) ? "warn" : "";
  return <span className={`pill ${cls}`}>{STATUS_LABELS[s] ?? s}</span>;
}

/** Einfaches Balkendiagramm (SVG), eine Reihe. */
export function Bars({ data, x, y, label, format = (v: number) => String(v) }: {
  data: any[]; x: string; y: string; label: string; format?: (v: number) => string;
}) {
  if (!data?.length) return <p className="muted small">Keine Daten.</p>;
  const W = 640, H = 170, P = 24;
  const max = Math.max(1, ...data.map((d) => d[y] || 0));
  const bw = (W - 2 * P) / data.length;
  return (
    <figure className="card" style={{ margin: 0 }}>
      <figcaption className="small muted" style={{ marginBottom: 6 }}>{label}</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={label}>
        {data.map((d, i) => {
          const h = ((d[y] || 0) / max) * (H - 2 * P);
          const w = Math.min(Math.max(bw - 4, 1), 48);
          return (
            <g key={i}>
              <rect x={P + i * bw + (bw - w) / 2} y={H - P - h} width={w} height={h} rx={3} fill="var(--accent)">
                <title>{`${d[x]}: ${format(d[y] || 0)}`}</title>
              </rect>
              {data.length <= 14 && (
                <text x={P + i * bw + bw / 2} y={H - 6} fontSize={10} textAnchor="middle" fill="var(--muted)">
                  {String(d[x]).slice(5)}
                </text>
              )}
            </g>
          );
        })}
        <text x={P} y={12} fontSize={11} fill="var(--muted)">max {format(max)}</text>
      </svg>
    </figure>
  );
}

export function ErrorBox({ error }: { error: string | null }) {
  return error ? <p className="error">{error}</p> : null;
}

export async function act(fn: () => Promise<unknown>, reload?: () => void) {
  try {
    await fn();
    reload?.();
  } catch (e: any) {
    alert(e.message || "Aktion fehlgeschlagen");
  }
}
