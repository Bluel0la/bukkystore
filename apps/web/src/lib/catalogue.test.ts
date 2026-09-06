import {
  formatNaira,
  getCategories,
  getProduct,
  getProducts,
} from "@/lib/catalogue";
import { afterEach, describe, expect, it, vi } from "vitest";

describe("catalogue client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.API_INTERNAL_URL;
  });

  it("loads catalogue resources from the internal API", async () => {
    process.env.API_INTERNAL_URL = "http://api.test/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([{ id: "category" }]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [], next_cursor: null }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "product" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getCategories()).resolves.toEqual([{ id: "category" }]);
    await expect(getProducts("limit=8")).resolves.toEqual({ items: [], next_cursor: null });
    await expect(getProduct("brown linen/dress")).resolves.toEqual({ id: "product" });
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://api.test/api/v1/categories",
      expect.objectContaining({ next: { revalidate: 300 } }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "http://api.test/api/v1/products/brown%20linen%2Fdress",
      expect.any(Object),
    );
  });

  it("raises a safe typed error for unsuccessful responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 404 })));

    await expect(getProduct("missing")).rejects.toMatchObject({ status: 404 });
  });

  it("formats minor units as whole-naira prices", () => {
    expect(formatNaira(4550000)).toMatch(/45,500/);
  });
});
