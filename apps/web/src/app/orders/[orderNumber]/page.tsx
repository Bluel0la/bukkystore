import type { Metadata } from "next";
import Link from "next/link";

import { formatNaira } from "@/lib/catalogue";
import { getPaymentStatus } from "@/lib/commerce";

export const metadata: Metadata = { title: "Order status" };

export default async function OrderStatusPage(props: PageProps<"/orders/[orderNumber]">) {
  const [{ orderNumber }, searchParams] = await Promise.all([props.params, props.searchParams]);
  const token = typeof searchParams.token === "string" ? searchParams.token : "";
  const status = token ? await getPaymentStatus(orderNumber, token) : null;

  if (!status) {
    return <main className="mx-auto flex min-h-screen max-w-xl items-center px-5 py-12"><section className="checkout-card w-full text-center"><p className="text-xs uppercase tracking-[0.18em] text-[var(--wine)]">Order lookup</p><h1 className="mt-4 text-3xl font-semibold">We couldn’t open this order.</h1><p className="mt-4 text-[var(--muted)]">Use the private link shown after checkout, or contact Atiten Kids Store with your order number.</p><Link className="admin-primary mt-7 inline-block" href="/">Return to the store</Link></section></main>;
  }

  const confirmed = status.payment_status === "SUCCESS" && status.order_status === "CONFIRMED";
  const needsHelp = status.order_status === "REFUND_REQUIRED";
  return <main className="mx-auto flex min-h-screen max-w-xl items-center px-5 py-12"><section className="checkout-card w-full text-center"><p className="text-xs uppercase tracking-[0.18em] text-[var(--wine)]">Order {status.order_number}</p><div className="mx-auto mt-6 flex h-16 w-16 items-center justify-center rounded-full bg-[#e4f3e8] text-2xl" aria-hidden="true">{confirmed ? "✓" : needsHelp ? "!" : "…"}</div><h1 className="mt-5 text-4xl font-semibold tracking-[-0.045em]">{confirmed ? "Payment received." : needsHelp ? "We’re reviewing your payment." : "Payment is still pending."}</h1><p className="mt-4 leading-7 text-[var(--muted)]">{confirmed ? "Your order is confirmed. Atiten Kids Store can now prepare it for delivery." : needsHelp ? "Your payment arrived after the reservation ended and stock changed. The store will contact you about a refund or replacement." : "Complete payment before the reservation expires to keep these items."}</p><div className="mt-8 rounded-2xl bg-[var(--sand)] p-5 text-left"><div className="flex justify-between"><span>Total</span><strong>{formatNaira(status.summary.total_minor)}</strong></div><div className="mt-3 flex justify-between text-sm text-[var(--muted)]"><span>Order status</span><span>{status.order_status.replaceAll("_", " ")}</span></div></div><Link className="admin-primary mt-7 inline-block" href="/">Continue shopping</Link></section></main>;
}
