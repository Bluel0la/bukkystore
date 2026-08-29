import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CheckoutForm } from "@/components/checkout-form";

const clear = vi.fn();
const cart = { items: [{ variantId: "variant-id", productName: "Brown Dress", productSlug: "brown-dress", variantName: "Brown / M", priceMinor: 1_850_000, quantity: 1 }], itemCount: 1, isReady: true, clear, addItem: vi.fn(), replaceWith: vi.fn(), updateQuantity: vi.fn(), removeItem: vi.fn() };
vi.mock("@/components/cart-provider", () => ({ useCart: () => cart }));

const areas = [{ id: "area-id", name: "Lagos Mainland", fee_minor: 300_000, currency: "NGN" as const }];

function fill() {
  fireEvent.change(screen.getByLabelText("Full name"), { target: { value: "Ada Okafor" } });
  fireEvent.change(screen.getByLabelText("Phone number"), { target: { value: "08012345678" } });
  fireEvent.change(screen.getByLabelText("Full delivery address"), { target: { value: "12 Example Street, Lagos" } });
}

describe("CheckoutForm", () => {
  beforeEach(() => {
    clear.mockReset();
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "request-id") });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("submits variant IDs with an idempotency key", async () => {
    const assign = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ payment_url: "http://localhost:3000/checkout/payment-demo?order=BS-1" }), { status: 201, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    render(<CheckoutForm areas={areas} onPaymentReady={assign} />);
    fill();
    fireEvent.click(screen.getByRole("button", { name: "Place order & pay" }));
    await waitFor(() => expect(clear).toHaveBeenCalled());
    const options = fetchMock.mock.calls[0][1];
    expect(options.headers["Idempotency-Key"]).toBe("checkout:request-id");
    expect(JSON.parse(options.body).items).toEqual([{ variant_id: "variant-id", quantity: 1 }]);
    expect(assign).toHaveBeenCalled();
  });

  it("shows safe API and network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ message: "Not enough stock." }), { status: 409 })).mockRejectedValueOnce(new Error("offline")));
    render(<CheckoutForm areas={areas} />);
    fill();
    fireEvent.click(screen.getByRole("button", { name: "Place order & pay" }));
    await screen.findByText("Not enough stock.");
    fireEvent.click(screen.getByRole("button", { name: "Place order & pay" }));
    await screen.findByText("We could not reach checkout. Please check your connection and try again.");
  });
});
