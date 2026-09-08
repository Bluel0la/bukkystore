import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CartProvider, useCart } from "@/components/cart-provider";

function CartHarness() {
  const cart = useCart();
  return <div><span>{cart.isReady ? "ready" : "loading"}</span><span>{cart.itemCount}</span><button onClick={() => cart.addItem({ variantId: "variant-1", productName: "Dress", productSlug: "dress", categorySlug: "dresses", variantName: "Brown / M", priceMinor: 100, quantity: 1 })}>Add</button><button onClick={() => cart.updateQuantity("variant-1", 3)}>Three</button><button onClick={() => cart.removeItem("variant-1")}>Remove</button></div>;
}

describe("CartProvider", () => {
  afterEach(() => {
    window.localStorage.clear();
    vi.useRealTimers();
  });

  it("hydrates, persists, updates, and removes cart items", async () => {
    vi.useFakeTimers();
    window.localStorage.setItem("bukky-store-cart-v1", JSON.stringify([{ variantId: "variant-1", productName: "Dress", productSlug: "dress", variantName: "Brown / M", priceMinor: 100, quantity: 2 }]));
    render(<CartProvider><CartHarness /></CartProvider>);
    await act(() => vi.runAllTimersAsync());
    expect(screen.getByText("ready")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    fireEvent.click(screen.getByRole("button", { name: "Three" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove" }));
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("ignores malformed stored cart data", async () => {
    vi.useFakeTimers();
    window.localStorage.setItem("bukky-store-cart-v1", "not-json");
    render(<CartProvider><CartHarness /></CartProvider>);
    await act(() => vi.runAllTimersAsync());
    expect(screen.getByText("0")).toBeInTheDocument();
  });
});
