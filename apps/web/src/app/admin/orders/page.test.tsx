import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/admin", () => ({ getAdminOrders: vi.fn(), getAdminUser: vi.fn() }));

import AdminOrdersPage from "@/app/admin/orders/page";
import { getAdminOrders, getAdminUser } from "@/lib/admin";

const user = { id: "u", email: "owner@example.com", display_name: "Bukky", role: "OWNER" as const };
const orders = [
  { id: "1", order_number: "AT-100", customer_full_name: "Ada Okafor", customer_phone: "0801", total_minor: 2500000, currency: "NGN" as const, status: "PROCESSING", payment_status: "PAID", created_at: "2026-10-01" },
  { id: "2", order_number: "AT-101", customer_full_name: "Tomi Bello", customer_phone: "0802", total_minor: 1500000, currency: "NGN" as const, status: "AWAITING_PAYMENT", payment_status: "PENDING", created_at: "2026-10-02" },
];

describe("AdminOrdersPage", () => {
  it("searches recent orders and keeps the selected status in the form", async () => {
    vi.mocked(getAdminUser).mockResolvedValue(user);
    vi.mocked(getAdminOrders).mockResolvedValue({ items: orders });
    render(await AdminOrdersPage({ searchParams: Promise.resolve({ q: "ada", status: "processing" }) }));
    expect(screen.getByRole("link", { name: /AT-100/ })).toBeInTheDocument();
    expect(screen.queryByText("AT-101")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Processing" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("searchbox")).toHaveValue("ada");
  });

  it("offers a clear action for an empty filter", async () => {
    vi.mocked(getAdminUser).mockResolvedValue(user);
    vi.mocked(getAdminOrders).mockResolvedValue({ items: orders });
    render(await AdminOrdersPage({ searchParams: Promise.resolve({ q: "missing" }) }));
    expect(screen.getByText("No matching orders")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Clear filters" })).toHaveAttribute("href", "/admin/orders");
  });
});
