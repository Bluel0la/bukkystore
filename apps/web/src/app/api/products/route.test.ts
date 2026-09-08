import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/products/route";

describe("products BFF", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("forwards an allowlisted catalogue query", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [] }), { status: 200, headers: { "content-type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const response = await GET(
      new Request("http://localhost/api/products?category=dresses&limit=8&drop=x", { method: "GET" }),
    );
    expect(response.status).toBe(200);
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain("/api/v1/products?");
    expect(url).toContain("category=dresses");
    expect(url).toContain("limit=8");
    expect(url).not.toContain("drop=");
  });

  it("masks upstream outages", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    const response = await GET(new Request("http://localhost/api/products", { method: "GET" }));
    expect(response.status).toBe(503);
  });
});
