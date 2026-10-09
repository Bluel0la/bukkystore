import { afterEach, describe, expect, it, vi } from "vitest";

import { getDeliveryAreas, getPaymentStatus } from "@/lib/commerce";

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

  it("loads a private payment status without caching", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ order_number: "BS-1", payment_status: "SUCCESS" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getPaymentStatus("BS/1", "private token")).resolves.toMatchObject({ payment_status: "SUCCESS" });
    expect(fetchMock.mock.calls[0][0]).toContain("BS%2F1/payment-status?token=private+token");
    expect(fetchMock.mock.calls[0][1].cache).toBe("no-store");
  });

  it("does not expose failed order lookups", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 404 })));
    await expect(getPaymentStatus("BS-1", "wrong-token")).resolves.toBeNull();
  });
});
