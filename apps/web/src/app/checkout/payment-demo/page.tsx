import Link from "next/link";

type PaymentDemoProps = { searchParams: Promise<{ reference?: string; order?: string }> };

export default async function PaymentDemoPage({ searchParams }: PaymentDemoProps) {
  const { reference, order } = await searchParams;
  return <main className="mx-auto flex min-h-screen max-w-xl items-center px-5 py-12"><section className="w-full rounded-[2.5rem] border border-[var(--line)] bg-white p-8 text-center sm:p-12"><p className="text-xs uppercase tracking-[0.18em] text-[var(--wine)]">Demo payment handoff</p><h1 className="mt-4 text-4xl font-semibold tracking-[-0.045em]">Your order is reserved.</h1><p className="mt-5 leading-7 text-[var(--muted)]">This development screen stands in for OPay until the merchant account and production payment credentials are connected.</p>{order && <p className="mt-6 font-semibold">Order {order}</p>}{reference && <p className="mt-2 break-all text-xs text-[var(--muted)]">Payment reference: {reference}</p>}<Link className="mt-8 inline-block rounded-full bg-[var(--ink)] px-6 py-3 font-semibold text-white" href="/">Continue shopping</Link></section></main>;
}
