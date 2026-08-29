import Link from "next/link";

import { getProducts } from "@/lib/catalogue";

export default async function AdminPage() {
  const catalogue = await getProducts("limit=50").catch(() => null);
  const products = catalogue?.items ?? [];
  const available = products.filter((product) => product.available).length;

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-5 py-6 sm:px-8">
      <header className="mb-10 flex items-center justify-between">
        <div>
          <p className="text-sm text-[var(--muted)]">Bukky Store</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em]">Catalogue overview</h1>
        </div>
        <Link className="rounded-full border border-[var(--line)] px-4 py-2 text-sm" href="/">
          View store
        </Link>
      </header>
      <section aria-label="Catalogue summary" className="grid gap-3 sm:grid-cols-3">
        {[["Products", products.length], ["Available", available], ["Sold out", products.length - available]].map(([label, value]) => (
          <article className="rounded-2xl border border-[var(--line)] bg-white p-5" key={label}>
            <p className="text-sm text-[var(--muted)]">{label}</p>
            <p className="mt-5 text-3xl font-semibold">{value}</p>
          </article>
        ))}
      </section>
      <section className="mt-8" aria-labelledby="products-heading">
        <h2 className="text-xl font-semibold" id="products-heading">Products</h2>
        <div className="mt-4 overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
          {products.map((product) => (
            <div className="flex items-center justify-between border-b border-[var(--line)] p-4 last:border-0" key={product.id}>
              <div><p className="font-medium">{product.name}</p><p className="mt-1 text-xs text-[var(--muted)]">{product.category.name}</p></div>
              <span className={`rounded-full px-3 py-1 text-xs ${product.available ? "bg-[#e4f3e8] text-[#245d34]" : "bg-[#f4e6e7] text-[var(--wine)]"}`}>
                {product.available ? "Available" : "Sold out"}
              </span>
            </div>
          ))}
          {!products.length && <p className="p-5 text-sm text-[var(--muted)]">Catalogue unavailable.</p>}
        </div>
      </section>
      <p className="mt-8 rounded-2xl bg-[#f6ded2] p-5 text-sm leading-6">
        Product editing and exact stock counts stay locked until admin authentication is in place.
      </p>
    </main>
  );
}
