import Link from "next/link";
import { redirect } from "next/navigation";

import { AdminLogout } from "@/components/admin-logout";
import { getAdminAnalytics, getAdminOrders, getAdminStoreSettings, getAdminUser } from "@/lib/admin";
import { formatNaira } from "@/lib/catalogue";

export default async function AdminPage() {
  const [user, analytics, orderPage, settings] = await Promise.all([
    getAdminUser(),
    getAdminAnalytics(30),
    getAdminOrders(),
    getAdminStoreSettings(),
  ]);
  if (!user || !analytics || !orderPage) redirect("/admin/login");
  const storeName = settings?.store_name ?? "Atiten Kids Store";

  const topProducts = analytics.top_products ?? [];
  const sources = analytics.sources ?? [];
  const lowStock = analytics.low_stock ?? [];
  const engagement = analytics.engagement ?? [];

  const maxUnits = Math.max(...topProducts.map((product) => product.units_sold), 1);
  const maxSourceOrders = Math.max(...sources.map((source) => source.orders), 1);
  const cards = [
    { label: "30-day sales", value: formatNaira(analytics.sales_minor), note: `${analytics.sales_orders} paid orders` },
    { label: "Open fulfilment", value: analytics.open_fulfilment_orders, note: "Needs preparation or delivery" },
    { label: "Pending refunds", value: analytics.pending_refunds, note: analytics.pending_refunds ? "Needs attention" : "Nothing outstanding" },
    { label: "Low stock", value: analytics.low_stock_variants, note: "Active variants at threshold" },
  ];

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-5 py-6 sm:px-8">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="text-sm text-[var(--muted)]">Welcome back, {user.display_name}</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-[-0.04em]">Store operations</h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--muted)]">
            A current view of sales, fulfilment, refunds, and stock across {storeName}.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="rounded-full border border-[var(--line)] bg-white px-4 py-2 text-sm" href="/">View store</Link>
          <Link className="rounded-full border border-[var(--line)] bg-white px-4 py-2 text-sm" href="/admin/settings">Settings</Link>
          <Link className="rounded-full border border-[var(--line)] bg-white px-4 py-2 text-sm" href="/admin/delivery">Delivery</Link>
          <Link className="admin-primary" href="/admin/products/new">Add product</Link>
          <AdminLogout />
        </div>
      </header>

      <section aria-label="Store summary" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => (
          <article className="rounded-2xl border border-[var(--line)] bg-white p-5" key={card.label}>
            <p className="text-sm text-[var(--muted)]">{card.label}</p>
            <p className="mt-5 text-3xl font-semibold tracking-[-0.035em]">{card.value}</p>
            <p className="mt-2 text-xs leading-5 text-[var(--muted)]">{card.note}</p>
          </article>
        ))}
      </section>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.35fr_0.85fr]">
        <section aria-labelledby="orders-heading">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold" id="orders-heading">Recent orders</h2>
              <p className="mt-1 text-sm text-[var(--muted)]">{analytics.awaiting_payment_orders} currently awaiting payment</p>
            </div>
            <Link className="rounded-full border border-[var(--line)] bg-white px-4 py-2 text-sm" href="/admin/orders">View all</Link>
          </div>
          <div className="mt-4 overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
            {(orderPage.items ?? []).slice(0, 6).map((order) => (
              <Link className="grid gap-2 border-b border-[var(--line)] p-4 transition hover:bg-[var(--paper)] last:border-0 sm:grid-cols-[1fr_auto] sm:items-center" href={`/admin/orders/${order.id}`} key={order.id}>
                <div>
                  <p className="font-medium">{order.order_number}</p>
                  <p className="mt-1 text-xs text-[var(--muted)]">{order.customer_full_name} · {order.status.replaceAll("_", " ")}</p>
                </div>
                <strong className="text-sm">{formatNaira(order.total_minor)}</strong>
              </Link>
            ))}
            {!(orderPage.items ?? []).length && <p className="p-8 text-center text-sm text-[var(--muted)]">No orders yet. New checkouts will appear here.</p>}
          </div>
        </section>

        <section aria-labelledby="stock-heading">
          <div>
            <h2 className="text-xl font-semibold" id="stock-heading">Stock attention</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">Lowest availability first</p>
          </div>
          <div className="mt-4 overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
            {lowStock.map((variant) => (
              <Link className="flex items-center justify-between gap-4 border-b border-[var(--line)] p-4 transition hover:bg-[var(--paper)] last:border-0" href={`/admin/products/${variant.product_id}`} key={variant.variant_id}>
                <div className="min-w-0">
                  <p className="truncate font-medium">{variant.product_name}</p>
                  <p className="mt-1 truncate text-xs text-[var(--muted)]">{variant.variant_name} · {variant.sku}</p>
                </div>
                <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${variant.available_quantity === 0 ? "bg-[#f7e2e2] text-[#8a2d2d]" : "bg-[var(--sand)] text-[var(--wine)]"}`}>
                  {variant.available_quantity === 0 ? "Out" : `${variant.available_quantity} left`}
                </span>
              </Link>
            ))}
            {!lowStock.length && <p className="p-8 text-center text-sm text-[var(--muted)]">Stock levels look healthy.</p>}
          </div>
        </section>
      </div>

      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <section className="rounded-2xl border border-[var(--line)] bg-white p-5" aria-labelledby="products-heading">
          <div className="flex items-end justify-between gap-4">
            <div><h2 className="text-xl font-semibold" id="products-heading">Top products</h2><p className="mt-1 text-sm text-[var(--muted)]">Units sold in the last 30 days</p></div>
            <span className="text-xs text-[var(--muted)]">Avg. {formatNaira(analytics.average_order_minor)} / order</span>
          </div>
          <div className="mt-6 grid gap-5">
            {topProducts.map((product) => (
              <div key={product.product_id}>
                <div className="flex items-center justify-between gap-4 text-sm"><span className="truncate font-medium">{product.product_name}</span><span>{product.units_sold} sold</span></div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-[var(--sand)]"><div className="h-full rounded-full bg-[var(--wine)]" style={{ width: `${Math.max((product.units_sold / maxUnits) * 100, 5)}%` }} /></div>
              </div>
            ))}
            {!topProducts.length && <p className="text-sm text-[var(--muted)]">Paid orders will reveal the strongest products.</p>}
          </div>
        </section>

        <section className="rounded-2xl border border-[var(--line)] bg-white p-5" aria-labelledby="sources-heading">
          <div><h2 className="text-xl font-semibold" id="sources-heading">Where orders come from</h2><p className="mt-1 text-sm text-[var(--muted)]">Checkout attribution for paid orders</p></div>
          <div className="mt-6 grid gap-5">
            {sources.map((source) => (
              <div key={source.source}>
                <div className="flex items-center justify-between gap-4 text-sm"><span className="font-medium capitalize">{source.source}</span><span>{source.orders} orders · {formatNaira(source.sales_minor)}</span></div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-[var(--sand)]"><div className="h-full rounded-full bg-[var(--peach)]" style={{ width: `${Math.max((source.orders / maxSourceOrders) * 100, 5)}%` }} /></div>
              </div>
            ))}
            {!sources.length && <p className="text-sm text-[var(--muted)]">Source results will appear after paid checkouts.</p>}
          </div>
        </section>
      </div>

      <section className="mt-8 rounded-2xl border border-[var(--line)] bg-white p-5" aria-labelledby="interest-heading">
        <div><h2 className="text-xl font-semibold" id="interest-heading">Product interest</h2><p className="mt-1 text-sm text-[var(--muted)]">Views and WhatsApp chats in the last 30 days</p></div>
        <div className="mt-4 overflow-hidden">
          {engagement.map((item) => (
            <div className="flex items-center justify-between gap-4 border-b border-[var(--line)] py-3 text-sm last:border-0" key={item.product_id}>
              <span className="truncate font-medium">{item.product_name}</span>
              <span className="shrink-0 text-[var(--muted)]">{item.views} views · {item.whatsapp_clicks} chats</span>
            </div>
          ))}
          {!engagement.length && <p className="text-sm text-[var(--muted)]">Interest will appear once customers open shared product links.</p>}
        </div>
      </section>
    </main>
  );
}
