import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }) }));

import AdminCategoriesPage from "@/app/admin/categories/page";

vi.mock("@/lib/admin", () => ({
  getAdminUser: vi.fn(),
  getAdminCategories: vi.fn(),
}));

import { getAdminCategories, getAdminUser } from "@/lib/admin";

const user = { id: "u", email: "o@e.c", display_name: "O", role: "OWNER" };
const categories = [
  { id: "c1", name: "Dresses", slug: "dresses", parent_id: null, is_active: true },
];

describe("AdminCategoriesPage", () => {
  it("renders the manager with fetched categories", async () => {
    vi.mocked(getAdminUser).mockResolvedValue(user as never);
    vi.mocked(getAdminCategories).mockResolvedValue(categories as never);

    render(await AdminCategoriesPage());

    expect(screen.getByRole("heading", { name: "Categories", level: 1 })).toBeDefined();
    expect(screen.getAllByText("Dresses").length).toBeGreaterThan(0);
  });
});
