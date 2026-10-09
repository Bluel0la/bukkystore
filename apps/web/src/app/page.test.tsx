import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fallbackStoreSettings } from "@/lib/store-settings";

vi.mock("@/lib/catalogue", async (original) => ({ ...await original<typeof import("@/lib/catalogue")>(), getCategories: vi.fn(async () => []), getProducts: vi.fn(async () => ({ items: [], next_cursor: null })) }));
vi.mock("@/lib/store-settings", async (original) => ({ ...await original<typeof import("@/lib/store-settings")>(), getPublicStoreSettings: vi.fn() }));
vi.mock("@/components/cart-link", () => ({ CartLink: () => null }));
import Home from "@/app/page";
import { getCategories, getProducts } from "@/lib/catalogue";
import { getPublicStoreSettings } from "@/lib/store-settings";

beforeEach(() => { vi.mocked(getPublicStoreSettings).mockResolvedValue(fallbackStoreSettings); vi.mocked(getCategories).mockResolvedValue([]); vi.mocked(getProducts).mockResolvedValue({ items: [], next_cursor: null }); });
describe("Storefront discovery", () => {
  it("keeps one filter form when a populated collection changes and returns to all products", async () => {
    vi.mocked(getProducts).mockResolvedValue({ items: [{
      id: "dress-1", name: "Linen Dress", slug: "linen-dress",
      category: { id: "dresses", name: "Dresses", slug: "dresses", parent_id: null },
      price_minor: 1500000, compare_at_price_minor: null, currency: "NGN",
      featured: false, available: true, primary_image: null, colours: [], sizes: ["4Y"],
    }], next_cursor: null });
    const errors = vi.spyOn(console, "error");
    try {
      const { rerender } = render(await Home({ searchParams: Promise.resolve({}) }));
      for (const params of [{ category: "dresses", search: "linen" }, {}, { search: "dress" }, {}]) {
        rerender(await Home({ searchParams: Promise.resolve(params) }));
        expect(screen.getAllByRole("search")).toHaveLength(1);
        expect(screen.getAllByRole("searchbox")).toHaveLength(1);
        expect(screen.getAllByRole("button", { name: "Find pieces" })).toHaveLength(1);
        expect(screen.getByRole("searchbox")).toHaveValue(params.search ?? "");
        expect(screen.getAllByRole("heading", { name: "Linen Dress" })).toHaveLength(1);
      }
      expect(errors.mock.calls.flat().join(" ")).not.toContain("same key");
    } finally {
      errors.mockRestore();
    }
  });
  it("offers search and distinguishes an empty catalogue from an outage", async () => {
    render(await Home({ searchParams: Promise.resolve({ search: "dress", budget: "10000", available: "true" }) }));
    expect(screen.getByRole("searchbox")).toHaveValue("dress");
    expect(screen.getByText("No little finds just yet.")).toBeInTheDocument();
    expect(getProducts).toHaveBeenCalledWith("limit=12&search=dress&available=true&max_price_minor=1000000");
    expect(screen.getByRole("link", { name: "Clear filters ×" })).toHaveAttribute("href", "/#shop");
  });
  it("preserves filters when paging and resets the cursor when changing category", async () => {
    vi.mocked(getCategories).mockResolvedValue([{ id: "1", name: "Dresses", slug: "dresses", parent_id: null }]);
    vi.mocked(getProducts).mockResolvedValue({ items: [], next_cursor: "next-token" });
    render(await Home({ searchParams: Promise.resolve({ search: "linen", cursor: "old-token", budget: "20000" }) }));
    expect(screen.getByRole("link", { name: "Dresses" })).toHaveAttribute("href", "/?search=linen&budget=20000&category=dresses#shop");
    expect(screen.getByRole("link", { name: "More little finds →" }).getAttribute("href")).toContain("cursor=next-token");
    expect(screen.getByRole("link", { name: "← Back to first page" }).getAttribute("href")).not.toContain("cursor=");
  });
  it("keeps contact and navigation available during a catalogue outage", async () => {
    vi.mocked(getProducts).mockRejectedValue(new Error("offline"));
    render(await Home({ searchParams: Promise.resolve({}) }));
    expect(screen.getByText("Our collection is taking a little break.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ask us on WhatsApp ↗" })).toHaveAttribute("href", expect.stringContaining("https://wa.me/2348121531909"));
    expect(screen.getByRole("heading", { name: "Good to know." })).toBeInTheDocument();
  });
});
