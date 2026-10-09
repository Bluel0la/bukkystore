import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const pathname = vi.hoisted(() => ({ value: "/admin/orders/one" }));
vi.mock("next/navigation", () => ({
  usePathname: () => pathname.value,
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
}));
vi.mock("@/components/admin-logout", () => ({ AdminLogout: () => <button>Sign out</button> }));

import { AdminShell } from "@/components/admin-shell";

const user = { id: "1", email: "owner@example.com", display_name: "Bukky", role: "OWNER" as const };

describe("AdminShell", () => {
  it("provides persistent navigation and marks the current section", () => {
    render(<AdminShell storeName="Atiten Kids Store" user={user}><h1>Order detail</h1></AdminShell>);
    expect(screen.getByRole("navigation", { name: "Admin navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Orders/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /Overview/ })).not.toHaveAttribute("aria-current");
    expect(screen.getByText("Bukky")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Order detail" })).toBeInTheDocument();
  });

  it("marks only the overview at the admin root", () => {
    pathname.value = "/admin";
    render(<AdminShell storeName="Atiten Kids Store" user={user}><p>Dashboard</p></AdminShell>);
    expect(screen.getByRole("link", { name: /Overview/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /Orders/ })).not.toHaveAttribute("aria-current");
    pathname.value = "/admin/orders/one";
  });
});
