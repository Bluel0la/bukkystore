import Image from "next/image";
import Link from "next/link";

import { formatNaira, type ProductCardData } from "@/lib/catalogue";

export function ProductCard({ product }: { product: ProductCardData }) {
  return (
    <article className="group">
      <Link href={`/products/${product.slug}`}>
        <div className="relative flex aspect-[4/5] items-center justify-center overflow-hidden rounded-[2rem] border border-[var(--line)] bg-[var(--sand)]">
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
              <span className="block text-5xl text-(--peach)" aria-hidden="true">B</span>
              <span className="mt-4 block text-xs uppercase tracking-[0.18em] text-(--muted)">Photo coming soon</span>
            </div>
          )}
          {!product.available && <span className="absolute left-3 top-3 rounded-full bg-white px-3 py-1 text-xs font-semibold">Sold out</span>}
        </div>
        <div className="px-1 pt-4">
          <p className="text-xs uppercase tracking-[0.14em] text-(--muted)">{product.category.name}</p>
          <div className="mt-1 flex items-start justify-between gap-3">
            <h3 className="font-semibold">{product.name}</h3>
            <p className="whitespace-nowrap text-sm">{formatNaira(product.price_minor)}</p>
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
