import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

import { DemoPaymentPanel } from "@/components/demo-payment-panel";

describe("DemoPaymentPanel", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    push.mockReset();
  });

  it("confirms and opens the private order status page", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
    render(<DemoPaymentPanel order="BS-1" token="private token" />);

    fireEvent.click(screen.getByRole("button", { name: "Simulate successful payment" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/orders/BS-1?token=private%20token"));
  });

  it("shows safe API and network failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce(new Response(JSON.stringify({ message: "Payment expired." }), { status: 409 }))
        .mockRejectedValueOnce(new Error("offline")),
    );
    render(<DemoPaymentPanel order="BS-1" token="private-token" />);

    fireEvent.click(screen.getByRole("button", { name: "Simulate successful payment" }));
    await screen.findByText("Payment expired.");
    fireEvent.click(screen.getByRole("button", { name: "Simulate successful payment" }));
    await screen.findByText("We could not reach payment confirmation. Please try again.");
  });
});
