import { eur } from "@/lib/format";

/** Preisverlauf als schlichte SVG-Linie (eigene Messwerte). */
export function PriceChart({ points, current }: { points: { date: string; price_cents: number }[]; current: number }) {
  if (points.length < 2) return <p className="muted small">Noch zu wenige Messpunkte für einen Verlauf.</p>;
  const W = 600, H = 180, P = 28;
  const vals = points.map((p) => p.price_cents);
  const max = Math.max(...vals, current), min = Math.min(...vals, current);
  const span = Math.max(max - min, 1);
  const x = (i: number) => P + (i * (W - 2 * P)) / (points.length - 1);
  const y = (v: number) => H - P - ((v - min) / span) * (H - 2 * P);
  const d = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.price_cents).toFixed(1)}`).join(" ");
  return (
    <figure style={{ margin: 0 }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Preisverlauf der letzten 90 Tage">
        <line x1={P} x2={W - P} y1={y(current)} y2={y(current)} stroke="var(--accent)" strokeDasharray="4 4" />
        <path d={d} fill="none" stroke="var(--text)" strokeWidth={2} />
        <text x={P} y={14} fontSize={12} fill="var(--muted)">max {eur(max)}</text>
        <text x={P} y={H - 6} fontSize={12} fill="var(--muted)">min {eur(min)}</text>
        <text x={W - P} y={y(current) - 6} fontSize={12} textAnchor="end" fill="var(--accent)">jetzt {eur(current)}</text>
      </svg>
      <figcaption className="muted small">Tagestiefstpreise aus unserer eigenen Preisbeobachtung (90 Tage).</figcaption>
    </figure>
  );
}
