export const eur = (cents?: number | null) =>
  cents == null ? "–" : (cents / 100).toLocaleString("de-DE", { style: "currency", currency: "EUR" });

export const dt = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" }) : "–";

export const CATEGORIES: Record<string, string> = {
  technik: "Technik", haushalt: "Haushalt", werkzeug: "Werkzeug", garten: "Garten", kueche: "Küche",
  gaming: "Gaming", baby: "Baby & Kinder", auto: "Auto", sport: "Sport", drogerie: "Drogerie", sonstiges: "Sonstiges",
};

export const STATUS_LABELS: Record<string, string> = {
  neu: "Neu", in_pruefung: "In Prüfung", verifiziert: "Verifiziert", medien_werden_erstellt: "Medien werden erstellt",
  freigegeben: "Freigegeben", geplant: "Geplant", veroeffentlicht: "Veröffentlicht", preis_geaendert: "Preis geändert",
  abgelaufen: "Abgelaufen", fehlerhaft: "Fehlerhaft", abgelehnt: "Abgelehnt",
  entwurf: "Entwurf", wartet_auf_freigabe: "Wartet auf Freigabe", wird_veroeffentlicht: "Wird veröffentlicht",
  pausiert: "Pausiert", fehlgeschlagen: "Fehlgeschlagen", abgebrochen: "Abgebrochen",
};

export const SITE_NAME = "DealFehler";
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
