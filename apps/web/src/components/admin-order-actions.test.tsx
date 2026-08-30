import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ refresh: vi.fn(), readCsrfCookie: vi.fn((): string | null => "csrf-token") }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: mocks.refresh }) }));
vi.mock("@/lib/admin-client", () => ({ readCsrfCookie: mocks.readCsrfCookie }));

import { AdminOrderActions } from "@/components/admin-order-actions";

const refund = {
  id: "refund-id", payment_id: "payment-id", amount_minor: 120_000, currency: "NGN" as const,
  reason: "Customer requested cancellation", status: "PENDING" as const,
  manual_reference: null, created_at: "2026-08-30T00:00:00Z", completed_at: null,
};

describe("AdminOrderActions", () => {
  beforeEach(() => {
    mocks.refresh.mockReset();
    mocks.readCsrfCookie.mockReturnValue("csrf-token");
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "operation-id") });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("advances the order with CSRF and idempotency headers", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminOrderActions orderId="order-id" availableActions={["START_PROCESSING"]} refunds={[]} />);

    fireEvent.click(screen.getByRole("button", { name: "Start processing" }));

    await waitFor(() => expect(mocks.refresh).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][0]).toBe("/api/admin/orders/order-id/transitions");
    expect(fetchMock.mock.calls[0][1].headers["Idempotency-Key"]).toBe("order:operation-id");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ action: "START_PROCESSING" });
  });

  it("requires a reason and submits cancellation safely", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminOrderActions orderId="order-id" availableActions={["CANCEL"]} refunds={[]} />);
    fireEvent.click(screen.getByText("Cancel order"));
    const button = screen.getByRole("button", { name: "Confirm cancellation" });
    expect(button).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Cancellation reason"), { target: { value: "Customer changed their mind" } });
    fireEvent.click(button);

    await waitFor(() => expect(mocks.refresh).toHaveBeenCalled());
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ reason: "Customer changed their mind" });
  });

  it("records a pending manual refund and reports session errors", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const { rerender } = render(<AdminOrderActions orderId="order-id" availableActions={["COMPLETE_REFUND"]} refunds={[refund]} />);
    fireEvent.change(screen.getByLabelText(/Transfer reference/), { target: { value: "TRANSFER-123" } });
    fireEvent.click(screen.getByRole("button", { name: "Mark refund sent" }));
    await waitFor(() => expect(mocks.refresh).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][0]).toBe("/api/admin/refunds/refund-id/complete");

    mocks.readCsrfCookie.mockReturnValue(null);
    rerender(<AdminOrderActions orderId="order-id" availableActions={["MARK_COMPLETED"]} refunds={[]} />);
    fireEvent.click(screen.getByRole("button", { name: "Mark completed" }));
    await screen.findByText("Your admin session security token is missing. Please sign in again.");
  });
});
