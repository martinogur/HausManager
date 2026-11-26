import type { Metadata } from "next";
import "./globals.css";
import { SITE_URL } from "@/lib/format";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "DealFehler – Gute Deals. Schlechte Preise. Dein Vorteil.", template: "%s | DealFehler" },
  description: "Geprüfte Amazon-Deals und Preisfehler-Verdachtsfälle – bewertet anhand echter Preishistorie.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body>{children}</body>
    </html>
  );
}
