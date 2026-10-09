import { describe, expect, it } from "vitest";
import { shopHref, shopQuery } from "./shop-query";

describe("catalogue filter URLs", () => {
  it("bounds filters and converts naira to minor units", () => {
    const query = shopQuery({ search: "  linen  ", category: "dresses", size: " 4Y ", budget: "25000", available: "true" });
    expect(Object.fromEntries(query)).toEqual({ limit: "12", search: "linen", category: "dresses", size: "4Y", max_price_minor: "2500000", available: "true" });
  });
  it("ignores arrays, malformed categories, negative and fractional budgets", () => {
    expect(shopQuery({ search: ["a", "b"], category: "../bad", budget: "-1", available: "false" }).toString()).toBe("limit=12");
    expect(shopQuery({ budget: "1.5" }).has("max_price_minor")).toBe(false);
    expect(shopQuery({ search: "x".repeat(90) }).get("search")).toHaveLength(80);
  });
  it("preserves price and search while resetting pagination", () => {
    const query = shopQuery({ budget: "10000", search: "dress", cursor: "abc" });
    const href = shopHref(query, { category: "shoes", cursor: null });
    expect(href).toBe("/?search=dress&budget=10000&category=shoes#shop");
    expect(query.get("cursor")).toBe("abc");
    expect(shopHref(shopQuery({}))).toBe("/#shop");
  });
});
