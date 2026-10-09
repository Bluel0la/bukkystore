import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ refresh: vi.fn(), readCsrfCookie: vi.fn((): string | null => "csrf-token") }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: mocks.refresh }) }));
vi.mock("@/lib/admin-client", () => ({ readCsrfCookie: mocks.readCsrfCookie }));

import { AdminDeliveryAreas } from "@/components/admin-delivery-areas";
import type { AdminDeliveryArea } from "@/lib/admin-types";

const areas: AdminDeliveryArea[] = [
  { id: "area-1", name: "Lagos Mainland", fee_minor: 300_000, currency: "NGN", display_position: 0, is_active: true },
  { id: "area-2", name: "Lagos Island", fee_minor: 450_000, currency: "NGN", display_position: 1, is_active: false },
];

describe("AdminDeliveryAreas", () => {
  beforeEach(() => {
    mocks.refresh.mockReset();
    mocks.readCsrfCookie.mockReturnValue("csrf-token");
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "operation-id") });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("lists areas with formatted fees and active state", () => {
    render(<AdminDeliveryAreas initial={areas} />);

    expect(screen.getByText("Lagos Mainland")).toBeDefined();
    expect(screen.getByText(/inactive/)).toBeDefined();
  });

  it("creates an area with naira converted to kobo", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminDeliveryAreas initial={areas} />);

    fireEvent.change(screen.getByPlaceholderText("e.g. Ikeja"), { target: { value: "Ikeja" } });
    fireEvent.change(screen.getByPlaceholderText("2000"), { target: { value: "2000" } });
    fireEvent.click(screen.getByRole("button", { name: "Add area" }));

    await waitFor(() => expect(mocks.refresh).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][0]).toBe("/api/admin/delivery-areas");
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      name: "Ikeja",
      fee_minor: 200_000,
      display_position: 2,
    });
  });

  it("rejects invalid fees without calling the API", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminDeliveryAreas initial={areas} />);

    fireEvent.change(screen.getByPlaceholderText("e.g. Ikeja"), { target: { value: "I" } });
    fireEvent.change(screen.getByPlaceholderText("2000"), { target: { value: "2000" } });
    fireEvent.click(screen.getByRole("button", { name: "Add area" }));

    expect(screen.getByText("Area name needs at least 2 characters.")).toBeDefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("saves an edited fee converted to kobo and reactivates areas", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminDeliveryAreas initial={areas} />);

    fireEvent.change(screen.getByLabelText("Lagos Mainland fee in naira"), { target: { value: "2500" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Save fee" })[0]);

    await waitFor(() => expect(mocks.refresh).toHaveBeenCalled());
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ fee_minor: 250_000 });

    fireEvent.click(screen.getByRole("button", { name: "Activate" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ is_active: true });
  });

  it("reports delivery failures and rejects bad fees", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ message: "Area exists." }), { status: 409 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminDeliveryAreas initial={areas} />);

    fireEvent.change(screen.getByPlaceholderText("e.g. Ikeja"), { target: { value: "Ikeja" } });
    fireEvent.change(screen.getByPlaceholderText("2000"), { target: { value: "2000" } });
    fireEvent.click(screen.getByRole("button", { name: "Add area" }));
    await screen.findByText("Area exists.");

    fireEvent.change(screen.getByLabelText("Lagos Mainland fee in naira"), { target: { value: "-1" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Save fee" })[0]);
    await screen.findByText("Fee must be a positive amount in naira.");
  });

  it("toggles an area off with CSRF and idempotency headers", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminDeliveryAreas initial={areas} />);

    fireEvent.click(screen.getByRole("button", { name: "Deactivate" }));

    await waitFor(() => expect(mocks.refresh).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][0]).toBe("/api/admin/delivery-areas/area-1");
    expect(fetchMock.mock.calls[0][1].headers["X-CSRF-Token"]).toBe("csrf-token");
    expect(fetchMock.mock.calls[0][1].headers["Idempotency-Key"]).toBe("delivery:operation-id");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ is_active: false });
  });
});
