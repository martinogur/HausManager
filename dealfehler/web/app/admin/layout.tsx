"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, getToken, setToken } from "@/lib/api";

const NAV: [string, [string, string][]][] = [
  ["Betrieb", [["/admin", "Übersicht"], ["/admin/deals", "Gefundene Deals"], ["/admin/preisfehler", "Preisfehler"],
    ["/admin/publications", "Veröffentlichungen"]]],
  ["Kanäle", [["/admin/platform/instagram", "Instagram"], ["/admin/platform/pinterest", "Pinterest"],
    ["/admin/platform/whatsapp", "WhatsApp"], ["/admin/platform/telegram", "Telegram"], ["/admin/platform/website", "Website"]]],
  ["Umsatz", [["/admin/revenue", "Affiliate-Umsätze"], ["/admin/clicks", "Klickstatistiken"], ["/admin/costs", "Kostenkontrolle"]]],
  ["System", [["/admin/agents", "Agentenverwaltung"], ["/admin/connections", "API-Verbindungen"],
    ["/admin/errors", "Fehlerprotokoll"], ["/admin/settings", "Einstellungen"]]],
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<{ email: string; role: string } | null>(null);
  const isLogin = path === "/admin/login";

  useEffect(() => {
    if (isLogin) return;
    if (!getToken()) { router.replace("/admin/login"); return; }
    api("/api/auth/me").then(setMe).catch(() => router.replace("/admin/login"));
  }, [isLogin, router]);

  if (isLogin) return <>{children}</>;
  if (!me) return <p style={{ padding: 24 }}>Lade …</p>;
  return (
    <div className="admin">
      <aside>
        <Link href="/admin" className="logo" style={{ fontSize: "1.2rem", display: "block", margin: "4px 10px 8px" }}>
          DEAL<span>FEHLER</span>
        </Link>
        {NAV.map(([section, items]) => (
          <div key={section}>
            <div className="section">{section}</div>
            {items.map(([href, label]) => (
              <Link key={href} href={href} className={path === href ? "active" : ""}>{label}</Link>
            ))}
          </div>
        ))}
        <div className="section">{me.email} · {me.role}</div>
        <a href="#" onClick={(e) => { e.preventDefault(); setToken(null); router.replace("/admin/login"); }}>Abmelden</a>
      </aside>
      <main>{children}</main>
    </div>
  );
}
