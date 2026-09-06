import Link from "next/link";

import { BackendStatus } from "@/components/backend-status";
import { CartLink } from "@/components/cart-link";
import { ProductCard } from "@/components/product-card";
import { StoreBrand } from "@/components/store-brand";
import { getCategories, getProducts } from "@/lib/catalogue";
import { getPublicStoreSettings } from "@/lib/store-settings";

type HomeProps = { searchParams: Promise<{ category?: string | string[] }> };

export default async function Home({ searchParams }: HomeProps) {
  const requestedCategory = (await searchParams).category;
  const selectedCategory = typeof requestedCategory === "string" ? requestedCategory : undefined;
  const productQuery = new URLSearchParams({ limit: "8" });
  if (selectedCategory) productQuery.set("category", selectedCategory);
  const [catalogue, settings] = await Promise.all([
    Promise.all([getCategories(), getProducts(productQuery.toString())]).catch(() => null),
    getPublicStoreSettings(),
  ]);
  const allCategories = catalogue?.[0] ?? [];
  const parentIds = new Set(allCategories.flatMap((category) => category.parent_id ? [category.parent_id] : []));
  const categories = allCategories.filter((category) => !parentIds.has(category.id));
  const products = catalogue?.[1].items ?? [];

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-5 py-6 sm:px-8 lg:px-12">
      <header className="flex items-center justify-between border-b border-[var(--line)] pb-5">
        <StoreBrand name={settings.store_name} />
        <nav aria-label="Primary navigation" className="flex items-center gap-5 text-sm">
          <Link href="#shop">Shop</Link>
          <CartLink />
          <Link className="rounded-full bg-[var(--ink)] px-4 py-2 text-white" href="/admin">
            Admin
          </Link>
        </nav>
      </header>

      <section className="grid gap-10 py-16 md:grid-cols-[1.2fr_0.8fr] md:items-end md:py-24">
        <div>
          <p className="mb-5 text-xs font-bold uppercase tracking-[0.22em] text-[var(--wine)]">
            Atiten Stores · Fine Wears, we got you.
          </p>
          <h1 className="max-w-3xl text-5xl font-semibold leading-[0.95] tracking-[-0.055em] sm:text-7xl">
            Little outfits, big smiles.
          </h1>
        </div>
        <div className="border-l-2 border-[var(--peach)] pl-5 text-[var(--muted)]">
          <p className="max-w-sm leading-7">
            Kids clothing, shoes, and accessories selected for comfort and play.
          </p>
          <BackendStatus />
        </div>
      </section>

      <section aria-labelledby="categories-title" className="pb-16" id="categories">
        <h2 className="mb-5 text-2xl font-semibold tracking-[-0.03em]" id="categories-title">Shop by category</h2>
        {categories.length ? (
          <div className="flex flex-wrap gap-3">
            <Link
              aria-current={selectedCategory ? undefined : "page"}
              className={`rounded-full border px-5 py-3 text-sm transition hover:border-[var(--wine)] ${selectedCategory ? "border-[var(--line)] bg-white" : "border-[var(--wine)] bg-white font-semibold"}`}
              href="/#shop"
            >
              All
            </Link>
            {categories.map((category) => (
              <Link
                aria-current={selectedCategory === category.slug ? "page" : undefined}
                className={`rounded-full border px-5 py-3 text-sm transition hover:border-[var(--wine)] ${selectedCategory === category.slug ? "border-[var(--wine)] bg-white font-semibold" : "border-[var(--line)] bg-white"}`}
                href={`/?category=${category.slug}#shop`}
                key={category.id}
              >
                {category.name}
              </Link>
            ))}
          </div>
        ) : <p className="text-sm text-[var(--muted)]">Categories will appear when the store is online.</p>}
      </section>

      <section aria-labelledby="shop-title" className="pb-20" id="shop">
        <div className="mb-7 flex items-end justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--wine)]">Freshly added</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]" id="shop-title">
              {selectedCategory ? categories.find((category) => category.slug === selectedCategory)?.name ?? "Shop the collection" : "Shop the collection"}
            </h2>
          </div>
          <span className="text-sm text-[var(--muted)]">{products.length} pieces</span>
        </div>
        {products.length ? (
          <div className="grid grid-cols-2 gap-x-3 gap-y-10 md:grid-cols-3 lg:grid-cols-4">
            {products.map((product) => <ProductCard key={product.id} product={product} />)}
          </div>
        ) : (
          <div className="rounded-3xl border border-dashed border-[var(--line)] p-8 text-center text-[var(--muted)]">
            The catalogue is temporarily unavailable. Please check back shortly.
          </div>
        )}
      </section>
    </main>
  );
}
