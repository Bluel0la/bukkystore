import { describe, expect, it, vi } from "vitest";

import { fallbackStoreSettings, getPublicStoreSettings, whatsappLink } from "@/lib/store-settings";

describe("store-settings", () => {
  it("falls back to owner-confirmed details when the API is down", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    const settings = await getPublicStoreSettings();

    expect(settings).toEqual(fallbackStoreSettings);
    expect(settings.store_name).toBe("Atiten Kids Store");
    expect(settings.whatsapp_number).toBe("+2348121531909");
    vi.unstubAllGlobals();
  });

  it("returns live settings when the API responds", async () => {
    const live = { ...fallbackStoreSettings, store_name: "Atiten Kids Store Live" };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(live), { status: 200 })),
    );

    await expect(getPublicStoreSettings()).resolves.toEqual(live);
    vi.unstubAllGlobals();
  });

  it("falls back when the API returns an error status", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503 })));

    await expect(getPublicStoreSettings()).resolves.toEqual(fallbackStoreSettings);
    vi.unstubAllGlobals();
  });

  it("builds wa.me links from local Nigerian numbers", () => {
    expect(whatsappLink("08121531909", "Hello")).toBe("https://wa.me/2348121531909?text=Hello");
    expect(whatsappLink("+2348121531909", "Hello there")).toBe(
      "https://wa.me/2348121531909?text=Hello%20there",
    );
  });
});
