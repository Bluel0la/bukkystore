import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AdminProductEditor } from "@/components/admin-product-editor";
import type { AdminProduct } from "@/lib/admin-types";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

const product: AdminProduct = {
  id: "product-id",
  category: { id: "category-id", name: "Dresses", slug: "dresses", parent_id: null },
  name: "Brown Dress",
  slug: "brown-dress",
  description: "A dress",
  base_price_minor: 2_500_000,
  compare_at_price_minor: null,
  currency: "NGN",
  status: "ACTIVE",
  featured: false,
  created_at: "2026-08-29T00:00:00Z",
  updated_at: "2026-08-29T00:00:00Z",
  variants: [{
    id: "variant-id", sku: "DRESS-M", colour: "Brown", size: "M", display_name: "Brown / M",
    price_override_minor: null, stock_on_hand: 4, reserved_quantity: 1, available_quantity: 3,
    low_stock_threshold: 2, status: "ACTIVE",
  }],
};
const categories = [product.category];

describe("AdminProductEditor", () => {
  beforeEach(() => {
    refresh.mockReset();
    document.cookie = "bukky_admin_csrf=csrf-token; path=/";
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "idempotency-key") });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "bukky_admin_csrf=; Max-Age=0; path=/";
  });

  it("saves product details", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminProductEditor categories={categories} product={product} />);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Updated Dress" } });
    fireEvent.click(screen.getByRole("button", { name: "Save details" }));

    await screen.findByText("Product details saved.");
    expect(refresh).toHaveBeenCalled();
    const request = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(request.name).toBe("Updated Dress");
    expect(request.base_price_minor).toBe(2_500_000);
  });

  it("shows a failed product update", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 409 })));
    render(<AdminProductEditor categories={categories} product={product} />);
    fireEvent.click(screen.getByRole("button", { name: "Save details" }));
    await screen.findByText("Product details could not be saved.");
  });

  it("adjusts stock with a unique idempotency key", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminProductEditor categories={categories} product={product} />);
    fireEvent.change(screen.getByLabelText("Stock change for Brown / M"), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText("Reason for Brown / M"), { target: { value: "New delivery" } });
    fireEvent.click(screen.getByRole("button", { name: "Adjust" }));

    await waitFor(() => expect(refresh).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][1].headers).toMatchObject({ "Idempotency-Key": "idempotency-key" });
  });

  it("shows stock adjustment errors and expired sessions", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ message: "Stock is reserved." }), {
        status: 409,
        headers: { "content-type": "application/json" },
      }),
    ));
    render(<AdminProductEditor categories={categories} product={product} />);
    fireEvent.change(screen.getByLabelText("Stock change for Brown / M"), { target: { value: "-5" } });
    fireEvent.change(screen.getByLabelText("Reason for Brown / M"), { target: { value: "Correction" } });
    fireEvent.click(screen.getByRole("button", { name: "Adjust" }));
    await screen.findByText("Stock is reserved.");

    document.cookie = "bukky_admin_csrf=; Max-Age=0; path=/";
    fireEvent.click(screen.getByRole("button", { name: "Save details" }));
    await screen.findByText("Your session expired.");
  });
});
