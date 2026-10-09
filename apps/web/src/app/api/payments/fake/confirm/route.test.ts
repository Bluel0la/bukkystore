import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "@/app/api/payments/fake/confirm/route";

describe("fake payment confirmation BFF", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("forwards the private confirmation payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ payment_status: "SUCCESS" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const body = JSON.stringify({ order_number: "BS-1", order_access_token: "token" });
    const response = await POST(new Request("http://localhost/api/payments/fake/confirm", { method: "POST", body }));

    expect(response.status).toBe(200);
    expect(fetchMock.mock.calls[0][0]).toContain("/api/v1/payments/fake/confirm");
    expect(fetchMock.mock.calls[0][1].body).toBe(body);
  });

  it("rejects oversized bodies and masks upstream outages", async () => {
    expect((await POST(new Request("http://localhost", { method: "POST", body: "x".repeat(1_001) }))).status).toBe(413);
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    expect((await POST(new Request("http://localhost", { method: "POST", body: "{}" }))).status).toBe(503);
  });
});
