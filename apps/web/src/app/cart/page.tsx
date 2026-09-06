"use client";

import Link from "next/link";
import { useState } from "react";

import { useCart } from "@/components/cart-provider";
import { StoreBrand } from "@/components/store-brand";
import { formatNaira } from "@/lib/catalogue";

export function QuantityInput({ productName, quantity, onCommit }: { productName: string; quantity: number; onCommit: (value: number) => void }) {
  const [draft, setDraft] = useState<string | null>(null);

  function commit(raw: string) {
    const value = Number(raw);
    if (Number.isInteger(value) && value >= 1 && value <= 20) onCommit(value);
    setDraft(null);
  }

  return <input aria-label={`Quantity for ${productName}`} className="checkout-input mt-2 block w-24" max="20" min="1" onBlur={(event) => commit(event.target.value)} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") (event.target as HTMLInputElement).blur(); }} type="number" value={draft ?? quantity} />;
}

export default function CartPage() {
  const cart = useCart();
  const subtotal = cart.items.reduce((sum, item) => sum + item.priceMinor * item.quantity, 0);

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-5 py-6 sm:px-8">
      <header className="mb-10 flex items-center justify-between border-b border-[var(--line)] pb-5">
        <StoreBrand name="Atiten Kids Store" />
        <Link className="text-sm" href="/#shop">Continue shopping</Link>
      </header>
      <div className="grid gap-10 md:grid-cols-[1fr_19rem] md:items-start">
        <section aria-labelledby="bag-title">
          <p className="text-xs uppercase tracking-[0.18em] text-(--wine)">Your selection</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-0.045em]" id="bag-title">Shopping bag</h1>
          {!cart.isReady ? (
            <p className="mt-8 text-(--muted)">Loading your bag…</p>
          ) : cart.items.length ? (
            <div className="mt-8 grid gap-4">
              {cart.items.map((item) => (
                <article className="rounded-3xl border border-[var(--line)] bg-white p-5" key={item.variantId}>
                  <div className="flex items-start justify-between gap-5">
                    <div><Link className="font-semibold" href={`/products/${item.productSlug}`}>{item.productName}</Link><p className="mt-1 text-sm text-(--muted)">{item.variantName}</p></div>
                    <p className="font-medium">{formatNaira(item.priceMinor * item.quantity)}</p>
                  </div>
                  <div className="mt-5 flex items-end justify-between">
                    <label className="text-sm">Quantity<QuantityInput onCommit={(value) => cart.updateQuantity(item.variantId, value)} productName={item.productName} quantity={item.quantity} /></label>
                    <button className="text-sm text-(--wine) underline underline-offset-4" onClick={() => cart.removeItem(item.variantId)} type="button">Remove</button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="mt-8 rounded-3xl border border-dashed border-[var(--line)] p-8 text-center"><p>Your bag is empty.</p><Link className="mt-4 inline-block text-sm text-(--wine) underline" href="/#shop">Find something you love</Link></div>
          )}
        </section>
        <aside className="rounded-3xl bg-[var(--ink)] p-6 text-white">
          <p className="text-sm text-white/65">Estimated subtotal</p>
          <p className="mt-2 text-3xl font-semibold">{formatNaira(subtotal)}</p>
          <p className="mt-3 text-sm leading-6 text-white/65">Delivery is calculated from your Lagos area at checkout.</p>
          {cart.items.length ? (
            <Link className="mt-6 block rounded-full bg-white px-5 py-3 text-center font-semibold text-(--ink)" href="/checkout">Continue to checkout</Link>
          ) : (
            <Link className="mt-6 block rounded-full border border-white/40 px-5 py-3 text-center font-semibold text-white" href="/#shop">Find something you love</Link>
          )}
        </aside>
      </div>
    </main>
  );
}
