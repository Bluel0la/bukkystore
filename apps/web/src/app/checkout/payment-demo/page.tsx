import Link from "next/link";

import { DemoPaymentPanel } from "@/components/demo-payment-panel";

type PaymentDemoProps = { searchParams: Promise<{ reference?: string; order?: string; token?: string }> };

export default async function PaymentDemoPage({ searchParams }: PaymentDemoProps) {
  const { reference, order, token } = await searchParams;
  return <main className="mx-auto flex min-h-screen max-w-xl items-center px-5 py-12"><section className="w-full rounded-[2.5rem] border border-[var(--line)] bg-white p-8 text-center sm:p-12"><p className="text-xs uppercase tracking-[0.18em] text-(--wine)">Demo payment handoff</p><h1 className="mt-4 text-4xl font-semibold tracking-[-0.045em]">Your order is reserved.</h1><p className="mt-5 leading-7 text-(--muted)">This development screen stands in for OPay until the merchant account and production payment credentials are connected.</p>{order && <p className="mt-6 font-semibold">Order {order}</p>}{reference && <p className="mt-2 break-all text-xs text-(--muted)">Payment reference: {reference}</p>}{order && token ? <DemoPaymentPanel order={order} token={token} /> : <p className="mt-8 text-sm text-(--wine)">This payment link is incomplete. Return to checkout and try again.</p>}<Link className="mt-5 inline-block text-sm text-(--muted) underline" href="/">Continue shopping</Link></section></main>;
}
