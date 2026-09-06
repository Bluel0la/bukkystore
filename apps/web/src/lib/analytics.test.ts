import { afterEach, describe, expect, it, vi } from "vitest";

import { trackEvent } from "@/lib/analytics";

describe("analytics beacon", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends events with session and attribution without breaking callers", () => {
    const beacon = vi.fn(() => true);
    vi.stubGlobal("navigator", { sendBeacon: beacon });
    window.localStorage.setItem(
      "atiten_attribution",
      JSON.stringify({ source: "tiktok", campaign: "video1" }),
    );
    document.cookie = "bs_session=session-1234";

    expect(() => trackEvent("whatsapp_click", { productId: "product-id" })).not.toThrow();
    expect(beacon).toHaveBeenCalledOnce();
    const [url, blob] = beacon.mock.calls[0] as unknown as [string, Blob];
    expect(url).toBe("/api/analytics/events");
    expect(blob.type).toBe("application/json");
  });

  it("falls back to fetch and swallows failures", async () => {
    vi.stubGlobal("navigator", {});
    const fetchMock = vi.fn().mockRejectedValue(new Error("offline"));
    vi.stubGlobal("fetch", fetchMock);
    window.localStorage.clear();
    document.cookie = "bs_session=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";

    expect(() => trackEvent("product_view")).not.toThrow();
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.event_type).toBe("product_view");
    expect(body.source).toBe("direct");
    expect(body.session_id).toMatch(/^[A-Za-z0-9]{32}$/);
  });
});
