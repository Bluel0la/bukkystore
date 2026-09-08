import { afterEach, describe, expect, it, vi } from "vitest";

const cookieString = vi.fn(() => "bukky_admin_session=session");
vi.mock("next/headers", () => ({ cookies: vi.fn(async () => ({ toString: cookieString })) }));

import {
  adminRequest,
  getAdminAnalytics,
  getAdminCategories,
  getAdminDeliveryAreas,
  getAdminOrder,
  getAdminOrders,
  getAdminProduct,
  getAdminProducts,
  getAdminStoreSettings,
  getAdminUser,
  getProductEngagement,
} from "@/lib/admin";

describe("admin server client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.API_INTERNAL_URL;
  });

  it("loads each protected resource with the incoming session cookie", async () => {
    process.env.API_INTERNAL_URL = "http://api.test/";
    const fetchMock = vi.fn().mockImplementation(async () =>
      new Response(JSON.stringify({ id: "result" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await getAdminUser();
    await getAdminProducts();
    await getAdminProduct("product/id");
    await getAdminCategories();
    await getAdminOrders();
    await getAdminOrder("order/id");
    await getAdminAnalytics();
    await getAdminStoreSettings();
    await getAdminDeliveryAreas();
    await getProductEngagement("product/id");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://api.test/api/v1/admin/auth/me",
      expect.objectContaining({ headers: expect.objectContaining({ cookie: "bukky_admin_session=session" }) }),
    );
    expect(fetchMock.mock.calls[2][0]).toContain("product%2Fid");
    expect(fetchMock.mock.calls[5][0]).toContain("order%2Fid");
    expect(fetchMock.mock.calls[6][0]).toContain("/analytics/overview?days=30");
    expect(fetchMock.mock.calls[7][0]).toContain("/store-settings");
    expect(fetchMock.mock.calls[8][0]).toContain("/delivery-areas");
    expect(fetchMock.mock.calls[9][0]).toContain("/analytics/products/product%2Fid?days=30");
  });

  it("builds product list filters into the query string", async () => {
    const fetchMock = vi.fn().mockImplementation(async () =>
      new Response(JSON.stringify({ items: [], next_cursor: null }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await getAdminProducts({ search: "dress", status: "ARCHIVED" });

    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain("/products?");
    expect(url).toContain("search=dress");
    expect(url).toContain("status=ARCHIVED");
    expect(url).toContain("limit=100");
  });

  it("returns null for an expired or forbidden session", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401 })));
    await expect(adminRequest("/products")).resolves.toBeNull();

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 403 })));
    await expect(adminRequest("/products")).resolves.toBeNull();
  });

  it("returns null when the API is unavailable or fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503 })));
    await expect(adminRequest("/products")).resolves.toBeNull();

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network connection error")));
    await expect(adminRequest("/products")).resolves.toBeNull();
  });
});

