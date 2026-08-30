import Link from "next/link";
import { redirect } from "next/navigation";

import { AdminLogout } from "@/components/admin-logout";
import { getAdminOrders, getAdminProducts, getAdminUser } from "@/lib/admin";

export default async function AdminPage() {
  const [user, catalogue, orderPage] = await Promise.all([getAdminUser(), getAdminProducts(), getAdminOrders()]);
  if (!user || !catalogue || !orderPage) redirect("/admin/login");
  const products = catalogue?.items ?? [];
  const published = products.filter((product) => product.status === "ACTIVE").length;
  const lowStock = products.flatMap((product) => product.variants).filter((variant) => variant.status === "ACTIVE" && variant.available_quantity <= variant.low_stock_threshold).length;

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-5 py-6 sm:px-8">
      <header className="mb-10 flex flex-wrap items-center justify-between gap-5">
        <div>
          <p className="text-sm text-[var(--muted)]">Welcome, {user.display_name}</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em]">Your catalogue</h1>
        </div>
        <div className="flex gap-2"><Link className="rounded-full border border-[var(--line)] px-4 py-2 text-sm" href="/">View store</Link><AdminLogout /></div>
      </header>
      <section aria-label="Store summary" className="grid gap-3 sm:grid-cols-4">
        {[["Orders", orderPage.items.length], ["All products", products.length], ["Published", published], ["Low or out of stock", lowStock]].map(([label, value]) => (
          <article className="rounded-2xl border border-[var(--line)] bg-white p-5" key={label}>
            <p className="text-sm text-[var(--muted)]">{label}</p>
            <p className="mt-5 text-3xl font-semibold">{value}</p>
          </article>
        ))}
      </section>
      <section className="mt-8" aria-labelledby="orders-heading"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold" id="orders-heading">Recent orders</h2><Link className="rounded-full border border-[var(--line)] px-4 py-2 text-sm" href="/admin/orders">View all orders</Link></div><div className="mt-4 overflow-hidden rounded-2xl border border-[var(--line)] bg-white">{orderPage.items.slice(0, 5).map((order) => <Link className="flex items-center justify-between gap-4 border-b border-[var(--line)] p-4 transition hover:bg-[var(--paper)] last:border-0" href={`/admin/orders/${order.id}`} key={order.id}><div><p className="font-medium">{order.order_number}</p><p className="mt-1 text-xs text-[var(--muted)]">{order.customer_full_name} · {order.payment_status.replaceAll("_", " ")}</p></div><span className="text-sm">{order.status.replaceAll("_", " ")}</span></Link>)}{!orderPage.items.length && <p className="p-6 text-sm text-[var(--muted)]">No orders yet.</p>}</div></section>
      <section className="mt-8" aria-labelledby="products-heading">
        <div className="flex items-center justify-between"><h2 className="text-xl font-semibold" id="products-heading">Products</h2><Link className="admin-primary" href="/admin/products/new">Add product</Link></div>
        <div className="mt-4 overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
          {products.map((product) => (
            <Link className="flex items-center justify-between border-b border-[var(--line)] p-4 transition hover:bg-[var(--paper)] last:border-0" href={`/admin/products/${product.id}`} key={product.id}>
              <div><p className="font-medium">{product.name}</p><p className="mt-1 text-xs text-[var(--muted)]">{product.category.name} · {product.variants.reduce((total, variant) => total + variant.stock_on_hand, 0)} in stock</p></div>
              <span className={`rounded-full px-3 py-1 text-xs ${product.status === "ACTIVE" ? "bg-[#e4f3e8] text-[#245d34]" : "bg-[#efe7dc] text-[var(--muted)]"}`}>{product.status === "ACTIVE" ? "Published" : product.status === "DRAFT" ? "Draft" : "Archived"}</span>
            </Link>
          ))}
          {!products.length && <div className="p-8 text-center"><p className="font-medium">No products yet</p><p className="mt-1 text-sm text-[var(--muted)]">Add the first piece to start your catalogue.</p></div>}
        </div>
      </section>
    </main>
  );
}
