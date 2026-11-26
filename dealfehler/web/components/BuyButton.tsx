"use client";
import { PUBLIC_API } from "@/lib/api";

/** Direkter, unverschleierter Affiliate-Link. Klickzählung per Beacon (keine Weiterleitung). */
export function BuyButton({ url, slug, src }: { url: string; slug: string; src?: string }) {
  const track = () => {
    try {
      const body = new Blob([JSON.stringify({ slug, src: src || "website" })], { type: "application/json" });
      navigator.sendBeacon(`${PUBLIC_API}/api/public/click`, body);
    } catch {}
  };
  return (
    <a className="btn primary" href={url} target="_blank" rel="sponsored nofollow noopener" onClick={track}
       style={{ fontSize: "1.05rem", padding: "12px 22px" }}>
      Zum Angebot bei Amazon* →
    </a>
  );
}
