import Link from "next/link";
import { redirect } from "next/navigation";

import { getAdminOrders, getAdminUser } from "@/lib/admin";
import { formatNaira } from "@/lib/catalogue";

function label(value: string) {
  return value.replaceAll("_", " ").toLowerCase().replace(/^./, (letter) => letter.toUpperCase());
}

function tone(status: string) {
  if (["COMPLETED", "PAID"].includes(status)) return "admin-status-success";
  if (["CANCELLED", "PAYMENT_FAILED", "REFUNDED"].includes(status)) return "admin-status-danger";
  if (["AWAITING_PAYMENT", "PENDING"].includes(status)) return "admin-status-warn";
  return "admin-status-neutral";
}

export default async function AdminOrdersPage({ searchParams }: {
  searchParams: Promise<{ q?: string | string[]; status?: string | string[] }>;
}) {
  const params = await searchParams;
  const query = typeof params.q === "string" ? params.q.trim().toLowerCase().slice(0, 80) : "";
  const selectedStatus = typeof params.status === "string" ? params.status.toUpperCase() : "ALL";
  const [user, page] = await Promise.all([getAdminUser(), getAdminOrders()]);
  if (!user || !page) redirect("/admin/login");

  const statuses = [...new Set(page.items.map((order) => order.status))];
  const items = page.items.filter((order) => {
    const matchesStatus = selectedStatus === "ALL" || order.status === selectedStatus;
    const haystack = `${order.order_number} ${order.customer_full_name} ${order.customer_phone}`.toLowerCase();
    return matchesStatus && (!query || haystack.includes(query));
  });

  function href(status: string) {
    const next = new URLSearchParams();
    if (query) next.set("q", query);
    if (status !== "ALL") next.set("status", status);
    return `/admin/orders${next.size ? `?${next}` : ""}`;
  }

  return <main className="mx-auto min-h-screen max-w-6xl px-5 py-6 sm:px-8">
    <header className="mb-7 flex flex-wrap items-end justify-between gap-4">
      <div><p className="text-xs font-bold uppercase tracking-[0.14em] text-(--wine)">Fulfilment</p><h1 className="mt-2 text-4xl font-semibold tracking-[-0.045em]">Orders</h1><p className="mt-2 text-sm text-(--muted)">Find a customer order and move it through delivery.</p></div>
      <span className="rounded-lg border border-[var(--line)] bg-white px-4 py-3 text-sm"><strong>{page.items.length}</strong> recent orders</span>
    </header>

    <section className="admin-list-toolbar" aria-label="Order filters">
      <form action="/admin/orders" method="get" role="search">
        {selectedStatus !== "ALL" && <input name="status" type="hidden" value={selectedStatus} />}
        <label><span aria-hidden="true">⌕</span><span className="sr-only">Search orders</span><input defaultValue={query} maxLength={80} name="q" placeholder="Order number, customer, or phone…" type="search" /></label>
        <button type="submit">Search</button>
      </form>
      <nav aria-label="Filter orders by status">
        {["ALL", ...statuses].map((status) => <Link aria-current={selectedStatus === status ? "page" : undefined} href={href(status)} key={status}>{status === "ALL" ? "All orders" : label(status)}</Link>)}
      </nav>
    </section>

    <section className="admin-order-list" aria-label="Orders">
      <div className="admin-order-head"><span>Order</span><span>Status</span><span>Payment</span><span>Total</span></div>
      {items.map((order) => <Link href={`/admin/orders/${order.id}`} key={order.id}>
        <div><strong>{order.order_number}</strong><span>{order.customer_full_name} · {order.customer_phone}</span></div>
        <span className={`admin-status ${tone(order.status)}`}>{label(order.status)}</span>
        <span className={`admin-status ${tone(order.payment_status)}`}>{label(order.payment_status)}</span>
        <strong>{formatNaira(order.total_minor)}</strong>
      </Link>)}
      {!items.length && <div className="p-12 text-center"><p className="font-semibold">No matching orders</p><p className="mt-2 text-sm text-(--muted)">{query || selectedStatus !== "ALL" ? "Clear the search or choose another status." : "New checkouts will appear here."}</p>{(query || selectedStatus !== "ALL") && <Link className="mt-4 inline-block text-sm text-(--wine) underline" href="/admin/orders">Clear filters</Link>}</div>}
    </section>
  </main>;
}
