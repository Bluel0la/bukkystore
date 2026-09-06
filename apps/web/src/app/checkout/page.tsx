import type { Metadata } from "next";
import Link from "next/link";

import { CheckoutForm } from "@/components/checkout-form";
import { StoreBrand } from "@/components/store-brand";
import { getDeliveryAreas } from "@/lib/commerce";

export const metadata: Metadata = { title: "Checkout" };

// Delivery areas must always be fresh at checkout time.
export const dynamic = "force-dynamic";

export default async function CheckoutPage() {
  const areas = await getDeliveryAreas().catch(() => []);
  return <main className="mx-auto min-h-screen max-w-5xl px-5 py-6 sm:px-8"><header className="mb-10 flex items-center justify-between border-b border-[var(--line)] pb-5"><StoreBrand name="Atiten Kids Store" /><Link className="text-sm" href="/cart">Back to bag</Link></header><div className="mb-9"><p className="text-xs uppercase tracking-[0.18em] text-(--wine)">Secure guest checkout</p><h1 className="mt-2 text-4xl font-semibold tracking-[-0.045em]">Where should we send it?</h1></div>{areas.length ? <CheckoutForm areas={areas} /> : <div className="rounded-3xl border border-dashed border-[var(--line)] p-8 text-center"><p>Delivery options are temporarily unavailable.</p><Link className="mt-4 inline-block text-(--wine) underline" href="/cart">Return to your bag</Link></div>}</main>;
}
