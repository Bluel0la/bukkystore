import { afterEach, describe, expect, it, vi } from "vitest";

const cookieString = vi.fn(() => "bukky_admin_session=session");
vi.mock("next/headers", () => ({ cookies: vi.fn(async () => ({ toString: cookieString })) }));

import {
  adminRequest,
  getAdminCategories,
  getAdminOrder,
  getAdminOrders,
  getAdminProduct,
  getAdminProducts,
  getAdminUser,
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

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://api.test/api/v1/admin/auth/me",
      expect.objectContaining({ headers: expect.objectContaining({ cookie: "bukky_admin_session=session" }) }),
    );
    expect(fetchMock.mock.calls[2][0]).toContain("product%2Fid");
    expect(fetchMock.mock.calls[5][0]).toContain("order%2Fid");
  });

  it("returns null for an expired session", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401 })));
    await expect(adminRequest("/products")).resolves.toBeNull();
  });

  it("throws a safe error when the API is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503 })));
    await expect(adminRequest("/products")).rejects.toThrow("Admin service unavailable");
  });
});
