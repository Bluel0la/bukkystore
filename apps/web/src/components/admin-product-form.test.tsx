import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AdminProductForm } from "@/components/admin-product-form";

const push = vi.fn();
const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, refresh }) }));

const categories = [{ id: "category-id", name: "Dresses", slug: "dresses", parent_id: null }];

function fillForm() {
  fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Blue Dress" } });
  fireEvent.change(screen.getByLabelText("Shareable slug"), { target: { value: "blue-dress" } });
  fireEvent.change(screen.getByLabelText("Selling price (₦)"), { target: { value: "25000" } });
  fireEvent.change(screen.getByLabelText("Compare-at price (₦), optional"), { target: { value: "30000" } });
  fireEvent.change(screen.getByLabelText("SKU"), { target: { value: "BLUE-M" } });
  fireEvent.change(screen.getByLabelText("Colour"), { target: { value: "Blue" } });
  fireEvent.change(screen.getByLabelText("Size"), { target: { value: "M" } });
  fireEvent.change(screen.getByLabelText("Display name"), { target: { value: "Blue / M" } });
  fireEvent.change(screen.getByLabelText("Opening stock"), { target: { value: "4" } });
}

describe("AdminProductForm", () => {
  beforeEach(() => {
    push.mockReset();
    refresh.mockReset();
    document.cookie = "bukky_admin_csrf=csrf-token; path=/";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "bukky_admin_csrf=; Max-Age=0; path=/";
  });

  it("creates a product with converted prices and variant stock", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "product-id" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminProductForm categories={categories} />);
    fillForm();
    fireEvent.click(screen.getByLabelText("Feature on the storefront"));
    fireEvent.click(screen.getByRole("button", { name: "Save product" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/admin/products/product-id"));
    const request = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(request.base_price_minor).toBe(2_500_000);
    expect(request.compare_at_price_minor).toBe(3_000_000);
    expect(request.variants[0]).toMatchObject({ sku: "BLUE-M", initial_stock: 4 });
  });

  it("adds and removes option rows", () => {
    render(<AdminProductForm categories={categories} />);
    fireEvent.click(screen.getByRole("button", { name: "Add option" }));
    expect(screen.getAllByLabelText("SKU")).toHaveLength(2);
    fireEvent.click(screen.getAllByRole("button", { name: "Remove option" })[0]);
    expect(screen.getAllByLabelText("SKU")).toHaveLength(1);
  });

  it("shows API and network failures", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ message: "Slug already used." }), {
          status: 409,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockRejectedValueOnce(new Error("offline"));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminProductForm categories={categories} />);
    fillForm();
    fireEvent.click(screen.getByRole("button", { name: "Save product" }));
    await screen.findByText("Slug already used.");
    fireEvent.click(screen.getByRole("button", { name: "Save product" }));
    await screen.findByText("The product could not be saved. Please try again.");
  });

  it("rejects submission after the CSRF cookie expires", () => {
    document.cookie = "bukky_admin_csrf=; Max-Age=0; path=/";
    render(<AdminProductForm categories={categories} />);
    fillForm();
    fireEvent.click(screen.getByRole("button", { name: "Save product" }));
    expect(screen.getByRole("alert")).toHaveTextContent("session expired");
  });
});
