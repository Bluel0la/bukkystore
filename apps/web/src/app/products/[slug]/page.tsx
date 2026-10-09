import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CartLink } from "@/components/cart-link";
import { ProductPurchasePanel } from "@/components/product-purchase-panel";
import { ProductGallery } from "@/components/product-gallery";
import { ProductShare } from "@/components/product-share";
import { StoreBrand } from "@/components/store-brand";
import { StoreFooter } from "@/components/store-footer";
import { ProductCard } from "@/components/product-card";
import { CatalogueRequestError, formatNaira, getProduct, getProducts } from "@/lib/catalogue";
import { getPublicStoreSettings } from "@/lib/store-settings";

type ProductPageProps = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: ProductPageProps): Promise<Metadata> {
  const { slug } = await params;
  const [product, settings] = await Promise.all([
    getProduct(slug).catch(() => null),
    getPublicStoreSettings(),
  ]);
  if (!product) return { title: "Product" };
  const site = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000").replace(/\/$/, "");
  const url = `${site}/products/${encodeURIComponent(product.slug)}`;
  const description = `${product.name} — ${formatNaira(product.price_minor)} at ${settings.store_name}. ${product.description}`;
  const images = product.images.map((image) => ({
    url: image.url,
    width: image.width,
    height: image.height,
    alt: image.alt_text,
  }));
  return {
    title: product.name,
    description,
    alternates: { canonical: url },
    openGraph: { title: product.name, description, url, type: "website", images },
    twitter: { card: "summary_large_image", title: product.name, description, images: product.images.map((image) => image.url) },
  };
}

export default async function ProductPage({ params }: ProductPageProps) {
  const { slug } = await params;
  const settingsPromise = getPublicStoreSettings();
  let product;
  try {
    product = await getProduct(slug);
  } catch (error) {
    if (error instanceof CatalogueRequestError && error.status === 404) notFound();
    throw error;
  }
  const settings = await settingsPromise;
  const related = await getProducts(new URLSearchParams({ category: product.category.slug, available: "true", limit: "5" }).toString()).catch(() => null);
  const recommendations = related?.items.filter((item) => item.id !== product.id).slice(0, 4) ?? [];

  return (
    <><main className="mx-auto min-h-screen max-w-5xl px-5 py-6 sm:px-8">
      <header className="mb-10 flex items-center justify-between border-b border-[var(--line)] pb-5">
        <StoreBrand name={settings.store_name} />
        <nav aria-label="Product navigation" className="flex items-center gap-5 text-sm"><Link href="/#shop">Back to shop</Link><CartLink /></nav>
      </header>
      <nav aria-label="Breadcrumb" className="mb-7 flex flex-wrap gap-2 text-xs text-(--muted)"><Link href="/#shop">Collection</Link><span aria-hidden="true">/</span><Link href={`/?category=${encodeURIComponent(product.category.slug)}#shop`}>{product.category.name}</Link><span aria-hidden="true">/</span><span aria-current="page">{product.name}</span></nav>
      <div className="grid gap-10 md:grid-cols-2 md:items-start">
        <ProductGallery images={product.images} />
        <section>
          <p className="text-xs uppercase tracking-[0.18em] text-(--wine)">{product.category.name}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.045em]">{product.name}</h1>
          <p className="mt-3 text-xl">{formatNaira(product.price_minor)}</p>
          <p className="mt-7 leading-7 text-(--muted)">{product.description}</p>
          <ProductPurchasePanel product={product} />
          <ProductShare
            productId={product.id}
            productName={product.name}
            productSlug={product.slug}
            priceMinor={product.price_minor}
            whatsappNumber={settings.whatsapp_number}
          />
          <div className="mt-8 border-t border-[var(--line)] pt-5 text-sm leading-7 text-(--muted)"><p>Lagos delivery · Fees shown at checkout.</p><p>Need help with sizing? Ask us using the WhatsApp link above.</p><Link href="/#help" className="underline underline-offset-4">Shopping & delivery help</Link></div>
        </section>
      </div>
      {recommendations.length > 0 && <section className="my-16" aria-labelledby="more-pieces"><p className="eyebrow">A little more to love</p><h2 className="mb-7 text-3xl font-semibold tracking-tight" id="more-pieces">Keep exploring</h2><div className="product-rail" tabIndex={0} role="region" aria-label="More products; scroll to explore">{recommendations.map((item) => <ProductCard product={item} key={item.id} />)}</div></section>}
    </main><StoreFooter settings={settings} /></>
  );
}
