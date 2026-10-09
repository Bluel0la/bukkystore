export type AttributionSource = "tiktok" | "instagram" | "whatsapp" | "direct";

export type Attribution = { source: AttributionSource; campaign: string | null };

const STORAGE_KEY = "atiten_attribution";
const KNOWN_SOURCES: AttributionSource[] = ["tiktok", "instagram", "whatsapp", "direct"];

function normalizeSource(value: string | null): AttributionSource {
  const cleaned = (value ?? "").trim().toLowerCase();
  return (KNOWN_SOURCES as string[]).includes(cleaned) ? (cleaned as AttributionSource) : "direct";
}

function normalizeCampaign(value: string | null): string | null {
  const cleaned = (value ?? "").trim().slice(0, 100);
  return cleaned ? cleaned : null;
}

/** Read ?ref= / ?campaign= (and utm_* equivalents) from a query string. */
export function attributionFromSearch(search: string): Attribution | null {
  const params = new URLSearchParams(search.startsWith("?") ? search : `?${search}`);
  const ref = params.get("ref") ?? params.get("utm_source");
  const campaign = params.get("campaign") ?? params.get("utm_campaign");
  if (ref == null && campaign == null) return null;
  return { source: normalizeSource(ref), campaign: normalizeCampaign(campaign) };
}

/** Persist attribution for the product → bag → checkout journey. */
export function saveAttribution(attribution: Attribution): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(attribution));
  } catch {
    // Private browsing must never break shopping.
  }
}

/** Load the stored attribution, falling back to direct. */
export function loadAttribution(): Attribution {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as { source?: unknown; campaign?: unknown };
      return {
        source: normalizeSource(typeof parsed.source === "string" ? parsed.source : null),
        campaign: normalizeCampaign(
          typeof parsed.campaign === "string" ? parsed.campaign : null,
        ),
      };
    }
  } catch {
    // Corrupt storage must never break shopping.
  }
  return { source: "direct", campaign: null };
}

/** Capture ?ref= from the current URL when present. Call on product/checkout mount. */
export function captureAttribution(): Attribution {
  const found = attributionFromSearch(window.location.search);
  if (found) {
    // A fresh tagged link wins over older stored attribution.
    if (found.source !== "direct" || found.campaign) saveAttribution(found);
    return found.source === "direct" && !found.campaign ? loadAttribution() : found;
  }
  return loadAttribution();
}

/** Build a shareable product URL tagged for one channel. */
export function productShareUrl(slug: string, ref: AttributionSource): string {
  const site = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000").replace(/\/$/, "");
  return `${site}/products/${encodeURIComponent(slug)}?ref=${ref}`;
}
