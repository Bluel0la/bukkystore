import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ refresh: vi.fn(), readCsrfCookie: vi.fn((): string | null => "csrf-token") }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: mocks.refresh }) }));
vi.mock("@/lib/admin-client", () => ({ readCsrfCookie: mocks.readCsrfCookie }));

import { AdminSettingsForm } from "@/components/admin-settings-form";
import type { AdminStoreSettings } from "@/lib/admin-types";

const openDay = { closed: false, open: "09:00", close: "18:00" };
const settings: AdminStoreSettings = {
  id: "settings-id",
  store_name: "Atiten Kids Store",
  logo_ref: null,
  whatsapp_number: "+2348121531909",
  phone_number: "+2348121531909",
  instagram_url: null,
  tiktok_url: "https://www.tiktok.com/@bookie_kiddiestore",
  address: "Emily Bus-stop by Dikram Filling Station",
  city: "Lagos",
  currency: "NGN",
  minimum_order_minor: null,
  business_hours: {
    monday: { ...openDay },
    tuesday: { ...openDay },
    wednesday: { ...openDay },
    thursday: { ...openDay },
    friday: { ...openDay },
    saturday: { ...openDay },
    sunday: { closed: true, open: null, close: null },
  },
  created_at: "2026-09-05T00:00:00Z",
  updated_at: "2026-09-05T00:00:00Z",
};

describe("AdminSettingsForm", () => {
  beforeEach(() => {
    mocks.refresh.mockReset();
    mocks.readCsrfCookie.mockReturnValue("csrf-token");
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "operation-id") });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("saves the form with idempotency and CSRF headers", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminSettingsForm initial={settings} />);

    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));

    await waitFor(() => expect(mocks.refresh).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][0]).toBe("/api/admin/store-settings");
    expect(fetchMock.mock.calls[0][1].method).toBe("PATCH");
    expect(fetchMock.mock.calls[0][1].headers["Idempotency-Key"]).toBe("settings:operation-id");
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.store_name).toBe("Atiten Kids Store");
    expect(body.whatsapp_number).toBe("+2348121531909");
    expect(body.minimum_order_minor).toBeNull();
    expect(body.business_hours.sunday.closed).toBe(true);
    await screen.findByText("Settings saved.");
  });

  it("blocks a missing CSRF token before calling the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    mocks.readCsrfCookie.mockReturnValue(null);
    render(<AdminSettingsForm initial={settings} />);

    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));

    await screen.findByText("Your admin session security token is missing. Please sign in again.");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("reports API failures without refreshing", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ message: "The settings could not be saved." }), { status: 409 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminSettingsForm initial={settings} />);

    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));

    await screen.findByText("The settings could not be saved.");
    expect(mocks.refresh).not.toHaveBeenCalled();
  });

  it("edits every field, hours, and minimum order before saving", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminSettingsForm initial={settings} />);

    fireEvent.change(screen.getByLabelText("Store name"), { target: { value: "Atiten Kids" } });
    fireEvent.change(screen.getByLabelText(/Logo reference/), { target: { value: "logo-123" } });
    fireEvent.change(screen.getByLabelText("WhatsApp number"), { target: { value: "08031234567" } });
    fireEvent.change(screen.getByLabelText("Phone number"), { target: { value: "08031234567" } });
    fireEvent.change(screen.getByLabelText("Shop address"), { target: { value: "New address" } });
    fireEvent.change(screen.getByLabelText("City"), { target: { value: "Ikeja" } });
    fireEvent.change(screen.getByLabelText(/Instagram URL/), { target: { value: "https://instagram.com/shop" } });
    fireEvent.change(screen.getByLabelText(/TikTok URL/), { target: { value: "https://tiktok.com/@shop" } });
    fireEvent.change(screen.getByLabelText(/Minimum order/), { target: { value: "5000" } });
    fireEvent.change(screen.getByLabelText("Monday opening time"), { target: { value: "08:00" } });
    fireEvent.change(screen.getByLabelText("Monday closing time"), { target: { value: "17:00" } });
    fireEvent.click(screen.getAllByRole("checkbox")[0]);
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));

    await waitFor(() => expect(mocks.refresh).toHaveBeenCalled());
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.store_name).toBe("Atiten Kids");
    expect(body.logo_ref).toBe("logo-123");
    expect(body.city).toBe("Ikeja");
    expect(body.minimum_order_minor).toBe(500_000);
    expect(body.business_hours.monday.closed).toBe(true);
  });

  it("rejects a negative minimum order without calling the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminSettingsForm initial={settings} />);

    fireEvent.change(screen.getByLabelText(/Minimum order/), { target: { value: "-5" } });
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));

    await screen.findByText("Minimum order must be a positive amount in naira, or left empty.");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
