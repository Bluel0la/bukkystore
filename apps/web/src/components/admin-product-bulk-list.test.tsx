import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ refresh: vi.fn(), readCsrfCookie: vi.fn((): string | null => "csrf-token") }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: mocks.refresh }) }));
vi.mock("@/lib/admin-client", () => ({ readCsrfCookie: mocks.readCsrfCookie }));

import { AdminProductBulkList } from "@/components/admin-product-bulk-list";
import type { AdminProduct } from "@/lib/admin-types";

function product(id: string, status: AdminProduct["status"] = "ACTIVE"): AdminProduct {
  return {
    id,
    category: { id: "category-id", name: "Dresses", slug: "dresses", parent_id: null },
    name: `Dress ${id}`,
    slug: `dress-${id}`,
    description: "A dress",
    base_price_minor: 2_500_000,
    compare_at_price_minor: null,
    currency: "NGN",
    status,
    featured: false,
    created_at: "2026-08-29T00:00:00Z",
    updated_at: "2026-08-29T00:00:00Z",
    variants: [{
      id: `variant-${id}`, sku: "SKU", colour: null, size: null, display_name: "Default",
      price_override_minor: null, stock_on_hand: 4, reserved_quantity: 0, available_quantity: 4,
      low_stock_threshold: 2, status: "ACTIVE",
    }],
    images: [],
  };
}

describe("AdminProductBulkList", () => {
  beforeEach(() => {
    mocks.refresh.mockReset();
    mocks.readCsrfCookie.mockReturnValue("csrf-token");
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "operation-id") });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("lists rows linking to edit pages with stock badges", () => {
    render(<AdminProductBulkList archivedTab={false} items={[product("p1"), product("p2")]} />);

    expect(screen.getByText("Dress p1")).toBeDefined();
    expect(screen.getAllByText("4 in stock")).toHaveLength(2);
    expect(screen.getByRole("link", { name: /Dress p1/ }).getAttribute("href")).toBe(
      "/admin/products/p1",
    );
    expect(screen.queryByText(/selected/)).toBeNull();
  });

  it("bulk archives selected products after confirmation", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminProductBulkList archivedTab={false} items={[product("p1"), product("p2")]} />);

    fireEvent.click(screen.getByLabelText("Select Dress p1"));
    fireEvent.click(screen.getByRole("button", { name: "Archive selected" }));
    fireEvent.click(screen.getByRole("button", { name: "Yes, archive them" }));

    await waitFor(() => expect(mocks.refresh).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][0]).toBe("/api/admin/products/bulk-archive");
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      product_ids: ["p1"],
      archived: true,
    });
    expect(fetchMock.mock.calls[0][1].headers["X-CSRF-Token"]).toBe("csrf-token");
  });

  it("bulk restores on the archived tab and selects all", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(
      <AdminProductBulkList archivedTab={true} items={[product("p1", "ARCHIVED"), product("p2", "ARCHIVED")]} />,
    );

    fireEvent.click(screen.getByLabelText("Select all on this page"));
    fireEvent.click(screen.getByRole("button", { name: "Restore selected" }));
    fireEvent.click(screen.getByRole("button", { name: "Yes, restore them" }));

    await waitFor(() => expect(mocks.refresh).toHaveBeenCalled());
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      product_ids: ["p1", "p2"],
      archived: false,
    });
  });

  it("reports bulk failures with status and code", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: "product_not_found", message: "Missing." }), {
        status: 404,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminProductBulkList archivedTab={false} items={[product("p1")]} />);

    fireEvent.click(screen.getByLabelText("Select Dress p1"));
    fireEvent.click(screen.getByRole("button", { name: "Archive selected" }));
    fireEvent.click(screen.getByRole("button", { name: "Yes, archive them" }));

    await screen.findByText(/HTTP 404 · product_not_found/);
    expect(mocks.refresh).not.toHaveBeenCalled();
  });

  it("renders nothing when empty", () => {
    const { container } = render(<AdminProductBulkList archivedTab={false} items={[]} />);
    expect(container.textContent).toBe("");
  });
});
