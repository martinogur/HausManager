"use client";
import { DealsTable } from "@/components/DealsTable";

export default function PriceErrors() {
  return (
    <>
      <p className="muted">Score ≥ 75. „Preisfehler-Verdacht“ (≥ 90) erst nach zweifacher unabhängiger Preisprüfung.
        „Preisfehler“ ohne Zusatz darf nur ein Admin nach Nachweis bestätigen.</p>
      <DealsTable minScore={75} title="Preisfehler & Top-Deals" />
    </>
  );
}
