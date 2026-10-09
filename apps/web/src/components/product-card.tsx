import Image from "next/image";
import Link from "next/link";

import { formatNaira, type ProductCardData } from "@/lib/catalogue";

export function ProductCard({ product }: { product: ProductCardData }) {
  return (
    <article className="product-card group">
      <Link href={`/products/${product.slug}`}>
        <div className="product-image relative flex aspect-[4/5] items-center justify-center overflow-hidden rounded-[2rem] border border-[var(--line)] bg-[var(--sand)]">
          {product.primary_image ? (
            <Image
              alt={product.primary_image.alt_text}
              className="object-cover transition duration-500 group-hover:scale-[1.02]"
              fill
              sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
              src={product.primary_image.url}
            />
          ) : (
            <div className="px-6 text-center">
              <span className="product-placeholder block" aria-hidden="true">a.</span>
              <span className="mt-4 block text-xs uppercase tracking-[0.18em] text-(--muted)">Photo coming soon</span>
            </div>
          )}
          {!product.available && <span className="absolute left-3 top-3 rounded-full bg-white px-3 py-1 text-xs font-semibold">Sold out</span>}
          {product.available && product.compare_at_price_minor !== null && product.compare_at_price_minor > product.price_minor && <span className="absolute left-3 top-3 rounded-full bg-white px-3 py-1 text-xs font-semibold">Sale</span>}
        </div>
        <div className="px-1 pt-4">
          <p className="text-xs uppercase tracking-[0.14em] text-(--muted)">{product.category.name}</p>
          <div className="mt-1 grid gap-1">
            <h3 className="font-semibold">{product.name}</h3>
            <p className="product-price flex flex-wrap items-center gap-2">{formatNaira(product.price_minor)}{product.compare_at_price_minor !== null && product.compare_at_price_minor > product.price_minor && <del className="text-xs font-normal text-(--muted)"><span className="sr-only">Previously </span>{formatNaira(product.compare_at_price_minor)}</del>}</p>
          </div>
          {(product.colours.length > 0 || product.sizes.length > 0) && (
            <p className="mt-2 text-xs text-(--muted)">
              {[product.colours.join(" · "), product.sizes.join(" · ")].filter(Boolean).join("  /  ")}
            </p>
          )}
        </div>
      </Link>
    </article>
  );
}
