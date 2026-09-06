"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useCart } from "@/components/cart-provider";
import { formatNaira, type ProductDetail } from "@/lib/catalogue";

export function ProductPurchasePanel({ product }: { product: ProductDetail }) {
  const available = product.variants.filter((variant) => variant.available);
  const [variantId, setVariantId] = useState(available[0]?.id ?? "");
  const [quantity, setQuantity] = useState(1);
  const [message, setMessage] = useState("");
  const cart = useCart();
  const router = useRouter();
  const selected = product.variants.find((variant) => variant.id === variantId);

  function cartItem() {
    if (!selected?.available) return null;
    return {
      variantId: selected.id,
      productName: product.name,
      productSlug: product.slug,
      variantName: selected.display_name,
      priceMinor: selected.price_minor,
      quantity,
    };
  }

  function addToBag() {
    const item = cartItem();
    if (!item) return;
    cart.addItem(item);
    setMessage(`${selected?.display_name} added to your bag.`);
  }

  function buyNow() {
    const item = cartItem();
    if (!item) return;
    cart.replaceWith(item);
    router.push("/checkout");
  }

  return (
    <div className="mt-10">
      <label className="text-sm font-semibold" htmlFor="variant">Choose an option</label>
      <select
        className="checkout-input mt-3"
        disabled={!available.length}
        id="variant"
        onChange={(event) => setVariantId(event.target.value)}
        value={variantId}
      >
        {!available.length && <option value="">Sold out</option>}
        {product.variants.map((variant) => (
          <option disabled={!variant.available} key={variant.id} value={variant.id}>
            {variant.display_name} · {variant.available ? formatNaira(variant.price_minor) : "Sold out"}
          </option>
        ))}
      </select>
      <label className="mt-5 block text-sm font-semibold" htmlFor="quantity">Quantity</label>
      <input
        className="checkout-input mt-3 max-w-28"
        id="quantity"
        max="20"
        min="1"
        onChange={(event) => setQuantity(Number(event.target.value))}
        type="number"
        value={quantity}
      />
      <div className="mt-7 grid gap-3 sm:grid-cols-2">
        <button
          className="rounded-full border border-[var(--ink)] px-6 py-4 font-semibold disabled:opacity-45"
          disabled={!selected?.available || quantity < 1 || quantity > 20}
          onClick={addToBag}
          type="button"
        >
          Add to bag
        </button>
        <button
          className="rounded-full bg-[var(--ink)] px-6 py-4 font-semibold text-white disabled:opacity-45"
          disabled={!selected?.available || quantity < 1 || quantity > 20}
          onClick={buyNow}
          type="button"
        >
          Buy now
        </button>
      </div>
      <p aria-live="polite" className="mt-3 min-h-5 text-sm text-(--wine)">{message}</p>
    </div>
  );
}
