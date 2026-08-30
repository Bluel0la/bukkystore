import Link from "next/link";
import { redirect } from "next/navigation";

import { getAdminOrders, getAdminUser } from "@/lib/admin";
import { formatNaira } from "@/lib/catalogue";

export default async function AdminOrdersPage() {
  const [user, page] = await Promise.all([getAdminUser(), getAdminOrders()]);
  if (!user || !page) redirect("/admin/login");
  return <main className="mx-auto min-h-screen max-w-5xl px-5 py-6 sm:px-8"><header className="mb-8 flex items-center justify-between gap-4"><div><Link className="text-sm text-[var(--muted)] underline" href="/admin">← Dashboard</Link><h1 className="mt-3 text-3xl font-semibold tracking-[-0.04em]">Orders</h1></div><span className="rounded-full bg-[var(--sand)] px-4 py-2 text-sm">{page.items.length} recent</span></header><section className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white" aria-label="Recent orders">{page.items.map((order) => <Link className="grid gap-3 border-b border-[var(--line)] p-4 transition hover:bg-[var(--paper)] last:border-0 sm:grid-cols-[1.2fr_1fr_auto] sm:items-center" href={`/admin/orders/${order.id}`} key={order.id}><div><p className="font-semibold">{order.order_number}</p><p className="mt-1 text-sm text-[var(--muted)]">{order.customer_full_name} · {order.customer_phone}</p></div><div><p className="text-sm">{order.status.replaceAll("_", " ")}</p><p className="mt-1 text-xs text-[var(--muted)]">Payment: {order.payment_status.replaceAll("_", " ")}</p></div><strong>{formatNaira(order.total_minor)}</strong></Link>)}{!page.items.length && <div className="p-10 text-center"><p className="font-medium">No orders yet</p><p className="mt-1 text-sm text-[var(--muted)]">New checkouts will appear here.</p></div>}</section></main>;
}
