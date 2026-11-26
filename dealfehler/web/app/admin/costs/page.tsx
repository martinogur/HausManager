"use client";
import { ErrorBox, Stat, useApi } from "@/components/admin";

export default function Costs() {
  const { data, error } = useApi("/api/costs?days=30");
  return (
    <>
      <h1>Kostenkontrolle</h1>
      <ErrorBox error={error} />
      {data && (
        <>
          <div className="grid stats">
            <Stat label="KI heute" value={`${data.llm_today_usd.toFixed(2)} $`} hint={`Limit ${data.llm_daily_budget_usd} $`} />
            <Stat label="KI 30 Tage" value={`${data.llm_month_usd.toFixed(2)} $`} hint={`Limit ${data.llm_monthly_budget_usd} $`} />
          </div>
          <p className="muted small">Bei erreichtem Limit arbeitet das System automatisch mit Vorlagentexten weiter (keine KI-Aufrufe).
            Limits über LLM_DAILY_BUDGET_USD / LLM_MONTHLY_BUDGET_USD.</p>
          <div className="table-wrap"><table><thead><tr><th>Anbieter</th><th>Vorgang</th><th className="num">Aufrufe</th><th className="num">Kosten</th></tr></thead><tbody>
            {data.rows.map((r: any, i: number) => <tr key={i}><td>{r.provider}</td><td>{r.operation}</td><td className="num">{r.calls}</td>
              <td className="num">{r.cost_usd.toFixed(4)} $</td></tr>)}
          </tbody></table></div>
        </>
      )}
    </>
  );
}
