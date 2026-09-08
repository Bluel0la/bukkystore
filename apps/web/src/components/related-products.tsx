"use client";

import { useEffect, useState } from "react";

import { useCart } from "@/components/cart-provider";
import { ProductCard } from "@/components/product-card";
import type { ProductCardData, ProductPage } from "@/lib/catalogue";

const MAX_RELATED = 4;

function shuffle<T>(items: T[]): T[] {
  const copy = [...items];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const other = Math.floor(Math.random() * (index + 1));
    [copy[index], copy[other]] = [copy[other] as T, copy[index] as T];
  }
  return copy;
}

async function fetchProducts(query: string): Promise<ProductCardData[]> {
  const response = await fetch(`/api/products?${query}`);
  if (!response.ok) throw new Error("Related products unavailable");
  return ((await response.json()) as ProductPage).items;
}

export function RelatedProducts() {
  const cart = useCart();
  const [products, setProducts] = useState<ProductCardData[] | null>(null);

  useEffect(() => {
    if (!cart.isReady || !cart.items.length) return;
    let cancelled = false;
    async function load() {
      try {
        const inBag = new Set(cart.items.map((item) => item.productSlug));
        const categories = [...new Set(
          cart.items.map((item) => item.categorySlug).filter((slug): slug is string => Boolean(slug)),
        )].slice(0, 2);
        const [latest, ...byCategory] = await Promise.all([
          fetchProducts("available=true&limit=8"),
          ...categories.map((slug) =>
            fetchProducts(`category=${encodeURIComponent(slug)}&available=true&limit=8`),
          ),
        ]);
        const seen = new Set<string>();
        const collect = (items: ProductCardData[]): ProductCardData[] =>
          items.filter((item) => {
            if (inBag.has(item.slug) || seen.has(item.id)) return false;
            seen.add(item.id);
            return true;
          });
        const picked = [
          ...shuffle(collect(byCategory.flat())),
          ...shuffle(collect(latest ?? [])),
        ].slice(0, MAX_RELATED);
        if (!cancelled) setProducts(picked.length ? picked : null);
      } catch {
        if (!cancelled) setProducts(null);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [cart.isReady, cart.items]);

  if (!cart.isReady || !cart.items.length || !products?.length) return null;
  return (
    <section aria-labelledby="related-heading" className="mt-14">
      <p className="text-xs uppercase tracking-[0.18em] text-(--wine)">Pairs well with your bag</p>
      <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]" id="related-heading">You may also like</h2>
      <div className="mt-7 grid grid-cols-2 gap-x-3 gap-y-10 md:grid-cols-4">
        {products.map((product) => <ProductCard key={product.id} product={product} />)}
      </div>
    </section>
  );
}
