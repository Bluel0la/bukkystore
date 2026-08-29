import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "@/app/api/checkout/route";

describe("checkout BFF", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("forwards checkout and idempotency headers", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ order_number: "BS-1" }), { status: 201, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await POST(new Request("http://localhost/api/checkout", { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": "checkout:key-0001" }, body: "{}" }));
    expect(response.status).toBe(201);
    expect(fetchMock.mock.calls[0][1].headers["Idempotency-Key"]).toBe("checkout:key-0001");
  });

  it("rejects oversized requests and masks upstream outages", async () => {
    const large = new Request("http://localhost/api/checkout", { method: "POST", headers: { "content-length": "20001" }, body: "{}" });
    expect((await POST(large)).status).toBe(413);
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    expect((await POST(new Request("http://localhost/api/checkout", { method: "POST", body: "{}" }))).status).toBe(503);
  });
});
