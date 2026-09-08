import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import AdminProductsPage from "@/app/admin/products/page";

vi.mock("@/lib/admin", () => ({
  getAdminUser: vi.fn(),
  getAdminProducts: vi.fn(),
}));
vi.mock("@/components/admin-product-bulk-list", () => ({
  AdminProductBulkList: ({ items }: { items: unknown[] }) => (
    <div data-testid="bulk-list">{items.length} rows</div>
  ),
}));

import { getAdminProducts, getAdminUser } from "@/lib/admin";

const user = { id: "u", email: "o@e.c", display_name: "O", role: "OWNER" };

describe("AdminProductsPage", () => {
  it("defaults to published and renders the bulk list", async () => {
    vi.mocked(getAdminUser).mockResolvedValue(user as never);
    vi.mocked(getAdminProducts).mockResolvedValue({ items: [{ id: "p1" }], next_cursor: null } as never);

    render(await AdminProductsPage({ searchParams: Promise.resolve({}) }));

    expect(vi.mocked(getAdminProducts)).toHaveBeenCalledWith({ search: undefined, status: "ACTIVE" });
    expect(screen.getByTestId("bulk-list")).toHaveTextContent("1 rows");
    expect(screen.getByRole("link", { name: "Published" })).toHaveAttribute("aria-current", "page");
  });

  it("passes search and status filters through and handles emptiness", async () => {
    vi.mocked(getAdminUser).mockResolvedValue(user as never);
    vi.mocked(getAdminProducts).mockResolvedValue({ items: [], next_cursor: null });

    render(
      await AdminProductsPage({ searchParams: Promise.resolve({ q: "dress", status: "archived" }) }),
    );

    expect(vi.mocked(getAdminProducts)).toHaveBeenCalledWith({ search: "dress", status: "ARCHIVED" });
    expect(screen.getByText(/No products match/)).toBeDefined();
  });

  it("shows a virgin-store message when nothing is published", async () => {
    vi.mocked(getAdminUser).mockResolvedValue(user as never);
    vi.mocked(getAdminProducts).mockResolvedValue({ items: [], next_cursor: null });

    render(await AdminProductsPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Nothing published yet.")).toBeDefined();
  });
});
