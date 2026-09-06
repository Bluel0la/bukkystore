import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/catalogue", () => ({
  getCategories: vi.fn(async () => []),
  getProducts: vi.fn(async () => ({ items: [], next_cursor: null })),
}));
vi.mock("@/lib/store-settings", () => ({
  getPublicStoreSettings: vi.fn(async () => ({ store_name: "Atiten Kids Store" })),
}));
vi.mock("@/components/cart-link", () => ({ CartLink: () => null }));
vi.mock("@/components/backend-status", () => ({ BackendStatus: () => null }));

import Home from "@/app/page";

describe("Home background effect", () => {
  it("renders the liquid-glass layer spanning the whole page", async () => {
    const { container } = render(await Home({ searchParams: Promise.resolve({}) }));

    const effect = container.querySelector('[data-aifx="liquid-glass"]');
    expect(effect).not.toBeNull();
    expect(effect?.getAttribute("class")).toContain("-z-10");
    expect(effect?.getAttribute("aria-hidden")).toBe("true");
    const main = container.querySelector("main");
    expect(main?.className).toContain("isolate");
    expect(main?.contains(effect)).toBe(true);
  });
});
