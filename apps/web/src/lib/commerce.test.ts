import { afterEach, describe, expect, it, vi } from "vitest";

import { getDeliveryAreas } from "@/lib/commerce";

describe("commerce server client", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns delivery areas from the API", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify([{ id: "area", name: "Lagos", fee_minor: 300000, currency: "NGN" }]), { status: 200 })));
    await expect(getDeliveryAreas()).resolves.toHaveLength(1);
  });

  it("returns an empty list when delivery is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 503 })));
    await expect(getDeliveryAreas()).resolves.toEqual([]);
  });
});
