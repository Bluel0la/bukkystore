import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CartProvider } from "@/components/cart-provider";
import { ProductPurchasePanel } from "@/components/product-purchase-panel";
import type { ProductDetail } from "@/lib/catalogue";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const product: ProductDetail = {
  id: "product-id", name: "Brown Dress", slug: "brown-dress", description: "A dress",
  category: { id: "category-id", name: "Dresses", slug: "dresses", parent_id: null },
  price_minor: 1_850_000, compare_at_price_minor: null, currency: "NGN", featured: false,
  available: true, primary_image: null, images: [], colours: ["Brown"], sizes: ["M"],
  variants: [{ id: "variant-id", sku: "DRESS-M", colour: "Brown", size: "M", display_name: "Brown / M", price_minor: 1_850_000, currency: "NGN", available: true, low_stock: false }],
};

describe("ProductPurchasePanel", () => {
  afterEach(() => { window.localStorage.clear(); push.mockReset(); vi.useRealTimers(); });

  it("adds an option to the bag and supports Buy now", async () => {
    vi.useFakeTimers();
    render(<CartProvider><ProductPurchasePanel product={product} /></CartProvider>);
    await act(() => vi.runAllTimersAsync());
    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Add to bag" }));
    expect(screen.getByText("Brown / M added to your bag.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Buy now" }));
    expect(push).toHaveBeenCalledWith("/checkout");
  });

  it("disables purchasing when every option is sold out", async () => {
    vi.useFakeTimers();
    const soldOut = { ...product, variants: [{ ...product.variants[0], available: false }] };
    render(<CartProvider><ProductPurchasePanel product={soldOut} /></CartProvider>);
    await act(() => vi.runAllTimersAsync());
    expect(screen.getByRole("button", { name: "Buy now" })).toBeDisabled();
  });
});
