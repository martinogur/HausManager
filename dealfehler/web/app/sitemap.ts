import type { MetadataRoute } from "next";
import { serverGet } from "@/lib/api";
import { CATEGORIES, SITE_URL } from "@/lib/format";

export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const deals = (await serverGet<{ slug: string; updated_at: string; active: boolean }[]>("/api/public/sitemap", 3600)) ?? [];
  return [
    { url: `${SITE_URL}/`, changeFrequency: "hourly", priority: 1 },
    { url: `${SITE_URL}/preisfehler`, changeFrequency: "hourly", priority: 0.9 },
    ...Object.keys(CATEGORIES).map((c) => ({ url: `${SITE_URL}/?category=${c}`, changeFrequency: "daily" as const, priority: 0.6 })),
    ...deals.filter((d) => d.active).map((d) => ({ url: `${SITE_URL}/deals/${d.slug}`, lastModified: d.updated_at, priority: 0.7 })),
  ];
}
