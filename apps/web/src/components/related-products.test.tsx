import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as useCartModule from "@/components/cart-provider";
import { RelatedProducts } from "@/components/related-products";

vi.mock("@/components/cart-provider", () => ({ useCart: vi.fn() }));

function product(id: string, slug: string, name = slug) {
  return {
    id, name, slug,
    category: { id: "category-id", name: "Dresses", slug: "dresses", parent_id: null },
    price_minor: 100_000, compare_at_price_minor: null, currency: "NGN" as const,
    featured: false, available: true, primary_image: null, colours: [], sizes: [],
  };
}

const bagItem = {
  variantId: "variant-1", productName: "Blue Dress", productSlug: "blue-dress",
  categorySlug: "dresses", variantName: "Blue / M", priceMinor: 100_000, quantity: 1,
};

function mockCart(items: unknown[]) {
  vi.mocked(useCartModule.useCart).mockReturnValue({
    items: items as never[], itemCount: items.length, isReady: true,
    addItem: vi.fn(), replaceWith: vi.fn(), updateQuantity: vi.fn(),
    removeItem: vi.fn(), clear: vi.fn(),
  });
}

describe("RelatedProducts", () => {
  it("prefers same-category picks, excludes in-bag items, and caps at four", async () => {
    mockCart([bagItem]);
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [
        product("2", "blue-dress"),
        product("3", "red-dress"),
        product("4", "green-dress"),
        product("5", "yellow-dress"),
        product("6", "pink-dress"),
      ] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [
        product("3", "red-dress"),
        product("7", "shoe"),
      ] }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<RelatedProducts />);

    await waitFor(() => expect(screen.getByText("You may also like")).toBeDefined());
    expect(screen.queryByText("Blue Dress")).toBeNull();
    expect(fetchMock.mock.calls[0][0]).toContain("available=true");
    expect(fetchMock.mock.calls.some((call) => String(call[0]).includes("category=dresses"))).toBe(true);
    const cards = document.querySelectorAll("article");
    expect(cards.length).toBeLessThanOrEqual(4);
    expect(cards.length).toBeGreaterThan(0);
    vi.unstubAllGlobals();
  });

  it("hides the rail for an empty bag and on API failure", async () => {
    mockCart([]);
    vi.stubGlobal("fetch", vi.fn());
    const { unmount } = render(<RelatedProducts />);
    expect(screen.queryByText("You may also like")).toBeNull();
    unmount();

    mockCart([bagItem]);
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    render(<RelatedProducts />);
    await waitFor(() => expect(screen.queryByText("You may also like")).toBeNull());
    vi.unstubAllGlobals();
  });
});
