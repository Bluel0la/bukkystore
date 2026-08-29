"use client";

import Link from "next/link";

import { useCart } from "@/components/cart-provider";
import { formatNaira } from "@/lib/catalogue";

export default function CartPage() {
  const cart = useCart();
  const subtotal = cart.items.reduce((sum, item) => sum + item.priceMinor * item.quantity, 0);

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-5 py-6 sm:px-8">
      <header className="mb-10 flex items-center justify-between border-b border-[var(--line)] pb-5">
        <Link className="text-xl font-semibold" href="/">Bukky Store</Link>
        <Link className="text-sm" href="/#shop">Continue shopping</Link>
      </header>
      <div className="grid gap-10 md:grid-cols-[1fr_19rem] md:items-start">
        <section aria-labelledby="bag-title">
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--wine)]">Your selection</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-0.045em]" id="bag-title">Shopping bag</h1>
          {!cart.isReady ? (
            <p className="mt-8 text-[var(--muted)]">Loading your bag…</p>
          ) : cart.items.length ? (
            <div className="mt-8 grid gap-4">
              {cart.items.map((item) => (
                <article className="rounded-3xl border border-[var(--line)] bg-white p-5" key={item.variantId}>
                  <div className="flex items-start justify-between gap-5">
                    <div><Link className="font-semibold" href={`/products/${item.productSlug}`}>{item.productName}</Link><p className="mt-1 text-sm text-[var(--muted)]">{item.variantName}</p></div>
                    <p className="font-medium">{formatNaira(item.priceMinor * item.quantity)}</p>
                  </div>
                  <div className="mt-5 flex items-end justify-between">
                    <label className="text-sm">Quantity<input aria-label={`Quantity for ${item.productName}`} className="checkout-input mt-2 block w-24" max="20" min="1" onChange={(event) => cart.updateQuantity(item.variantId, Number(event.target.value))} type="number" value={item.quantity} /></label>
                    <button className="text-sm text-[var(--wine)] underline underline-offset-4" onClick={() => cart.removeItem(item.variantId)} type="button">Remove</button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="mt-8 rounded-3xl border border-dashed border-[var(--line)] p-8 text-center"><p>Your bag is empty.</p><Link className="mt-4 inline-block text-sm text-[var(--wine)] underline" href="/#shop">Find something you love</Link></div>
          )}
        </section>
        <aside className="rounded-3xl bg-[var(--ink)] p-6 text-white">
          <p className="text-sm text-white/65">Estimated subtotal</p>
          <p className="mt-2 text-3xl font-semibold">{formatNaira(subtotal)}</p>
          <p className="mt-3 text-sm leading-6 text-white/65">Delivery is calculated from your Lagos area at checkout.</p>
          <Link aria-disabled={!cart.items.length} className={`mt-6 block rounded-full bg-white px-5 py-3 text-center font-semibold text-[var(--ink)] ${!cart.items.length ? "pointer-events-none opacity-45" : ""}`} href="/checkout">Continue to checkout</Link>
        </aside>
      </div>
    </main>
  );
}
