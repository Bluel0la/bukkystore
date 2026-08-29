import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CatalogueRequestError, formatNaira, getProduct } from "@/lib/catalogue";

type ProductPageProps = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: ProductPageProps): Promise<Metadata> {
  const { slug } = await params;
  const product = await getProduct(slug).catch(() => null);
  return product ? { title: product.name, description: product.description } : { title: "Product" };
}

export default async function ProductPage({ params }: ProductPageProps) {
  const { slug } = await params;
  let product;
  try {
    product = await getProduct(slug);
  } catch (error) {
    if (error instanceof CatalogueRequestError && error.status === 404) notFound();
    throw error;
  }

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-5 py-6 sm:px-8">
      <header className="mb-10 flex items-center justify-between border-b border-[var(--line)] pb-5">
        <Link className="text-xl font-semibold" href="/">Bukky Store</Link>
        <Link className="text-sm" href="/#shop">Back to shop</Link>
      </header>
      <div className="grid gap-10 md:grid-cols-2 md:items-start">
        <div className="relative flex aspect-[4/5] items-center justify-center overflow-hidden rounded-[2.5rem] border border-[var(--line)] bg-[var(--sand)] text-center">
          {product.primary_image ? (
            <Image
              alt={product.primary_image.alt_text}
              className="object-cover"
              fill
              priority
              sizes="(max-width: 768px) 100vw, 50vw"
              src={product.primary_image.url}
            />
          ) : (
            <div><span className="text-7xl text-[var(--peach)]" aria-hidden="true">B</span><p className="mt-5 text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Photo coming soon</p></div>
          )}
        </div>
        <section>
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--wine)]">{product.category.name}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.045em]">{product.name}</h1>
          <p className="mt-3 text-xl">{formatNaira(product.price_minor)}</p>
          <p className="mt-7 leading-7 text-[var(--muted)]">{product.description}</p>
          <h2 className="mt-10 text-sm font-semibold uppercase tracking-[0.14em]">Available options</h2>
          <div className="mt-4 grid gap-3">
            {product.variants.map((variant) => (
              <div className="flex items-center justify-between rounded-2xl border border-[var(--line)] bg-white p-4" key={variant.id}>
                <div><p className="font-medium">{variant.display_name}</p>{variant.low_stock && variant.available && <p className="mt-1 text-xs text-[var(--wine)]">Low stock</p>}</div>
                <span className={`text-sm ${variant.available ? "" : "text-[var(--muted)]"}`}>{variant.available ? formatNaira(variant.price_minor) : "Sold out"}</span>
              </div>
            ))}
          </div>
          <button className="mt-8 w-full rounded-full bg-[var(--ink)] px-6 py-4 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-45" disabled type="button">
            Checkout arrives in the next release
          </button>
        </section>
      </div>
    </main>
  );
}
