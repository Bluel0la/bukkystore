import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "@/app/api/analytics/events/route";

describe("analytics events BFF", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("forwards events to the API", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "event-id" }), { status: 201, headers: { "content-type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const response = await POST(
      new Request("http://localhost/api/analytics/events", { method: "POST", body: "{}" }),
    );
    expect(response.status).toBe(201);
    expect(fetchMock.mock.calls[0][0]).toContain("/api/v1/analytics/events");
  });

  it("rejects oversized requests and masks upstream outages", async () => {
    const large = new Request("http://localhost/api/analytics/events", {
      method: "POST",
      headers: { "content-length": "4001" },
      body: "{}",
    });
    expect((await POST(large)).status).toBe(413);
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    expect(
      (await POST(new Request("http://localhost/api/analytics/events", { method: "POST", body: "{}" }))).status,
    ).toBe(503);
  });
});
