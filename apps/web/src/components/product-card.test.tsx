import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProductCard } from "@/components/product-card";
import type { ProductCardData } from "@/lib/catalogue";

const product: ProductCardData = {
  id: "product-id",
  name: "Brown Linen Dress",
  slug: "brown-linen-dress",
  category: { id: "category-id", name: "Dresses", slug: "dresses", parent_id: null },
  price_minor: 4550000,
  compare_at_price_minor: null,
  currency: "NGN",
  featured: true,
  available: true,
  primary_image: null,
  colours: ["Brown"],
  sizes: ["M", "L"],
};

describe("ProductCard", () => {
  it("renders product details and the photo placeholder", () => {
    render(<ProductCard product={product} />);

    expect(screen.getByRole("heading", { name: "Brown Linen Dress" })).toBeInTheDocument();
    expect(screen.getByText("Photo coming soon")).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute("href", "/products/brown-linen-dress");
    expect(screen.getByText(/Brown\s+\/\s+M · L/)).toBeInTheDocument();
  });

  it("labels unavailable products", () => {
    render(<ProductCard product={{ ...product, available: false }} />);

    expect(screen.getByText("Sold out")).toBeInTheDocument();
  });
});
