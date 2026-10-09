import { loadAttribution } from "@/lib/attribution";

export type AnalyticsEventType = "product_view" | "share_click" | "whatsapp_click";

const SESSION_COOKIE = "bs_session";

function sessionId(): string {
  const found = document.cookie
    .split("; ")
    .find((part) => part.startsWith(`${SESSION_COOKIE}=`));
  if (found) {
    const value = decodeURIComponent(found.slice(SESSION_COOKIE.length + 1));
    if (/^[A-Za-z0-9_-]{8,64}$/.test(value)) return value;
  }
  const fresh = crypto.randomUUID().replaceAll("-", "");
  const expiry = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toUTCString();
  document.cookie = `${SESSION_COOKIE}=${fresh}; expires=${expiry}; path=/; samesite=lax`;
  return fresh;
}

/**
 * Fire-and-forget analytics beacon. Failures are swallowed deliberately:
 * tracking must never break shopping.
 */
export function trackEvent(
  eventType: AnalyticsEventType,
  options: { productId?: string; channel?: string } = {},
): void {
  try {
    const attribution = loadAttribution();
    const metadata = options.channel ? { channel: options.channel } : {};
    const body = JSON.stringify({
      event_type: eventType,
      session_id: sessionId(),
      product_id: options.productId ?? null,
      source: attribution.source,
      campaign: attribution.campaign,
      metadata,
    });
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: "application/json" });
      if (navigator.sendBeacon("/api/analytics/events", blob)) return;
    }
    void fetch("/api/analytics/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    }).catch(() => undefined);
  } catch {
    // Analytics must never break the storefront.
  }
}
