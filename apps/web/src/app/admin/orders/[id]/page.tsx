import Link from "next/link";
import { redirect } from "next/navigation";

import { AdminOrderActions } from "@/components/admin-order-actions";
import { getAdminOrder, getAdminStoreSettings, getAdminUser } from "@/lib/admin";
import { formatNaira } from "@/lib/catalogue";

function whatsappNumber(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  return digits.startsWith("0") ? `234${digits.slice(1)}` : digits;
}

export default async function AdminOrderPage(props: PageProps<"/admin/orders/[id]">) {
  const { id } = await props.params;
  const [user, order, settings] = await Promise.all([getAdminUser(), getAdminOrder(id), getAdminStoreSettings()]);
  if (!user || !order) redirect("/admin/login");
  const storeName = settings?.store_name ?? "Atiten Kids Store";
  const whatsappMessage = encodeURIComponent(
    `Hello ${order.customer_full_name}, I am contacting you from ${storeName} about order ${order.order_number}.`,
  );

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-5 py-6 sm:px-8">
      <header className="mb-8">
        <Link className="text-sm text-(--muted) underline" href="/admin/orders">← All orders</Link>
        <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
          <div><p className="text-sm text-(--wine)">{order.status.replaceAll("_", " ")}</p><h1 className="mt-1 text-3xl font-semibold tracking-[-0.04em]">{order.order_number}</h1></div>
          <strong className="text-2xl">{formatNaira(order.total_minor)}</strong>
        </div>
      </header>
      <div className="grid gap-5 md:grid-cols-[1.35fr_1fr]">
        <div className="grid gap-5">
          <section className="checkout-card">
            <h2 className="text-lg font-semibold">Items</h2>
            <div className="mt-4">{order.items.map((item) => <div className="flex justify-between gap-4 border-t border-[var(--line)] py-4 first:border-0" key={item.id}><div><p className="font-medium">{item.product_name} × {item.quantity}</p><p className="mt-1 text-xs text-(--muted)">{item.variant_name} · {item.sku}</p></div><span>{formatNaira(item.line_subtotal_minor)}</span></div>)}</div>
            <div className="border-t border-[var(--line)] pt-4 text-sm"><div className="flex justify-between"><span>Subtotal</span><span>{formatNaira(order.subtotal_minor)}</span></div><div className="mt-2 flex justify-between"><span>Delivery</span><span>{formatNaira(order.delivery_fee_minor)}</span></div></div>
          </section>
          <AdminOrderActions orderId={order.id} availableActions={order.available_actions} refunds={order.refunds} />
        </div>
        <aside className="grid content-start gap-5">
          <section className="checkout-card">
            <h2 className="text-lg font-semibold">Customer</h2><p className="mt-4 font-medium">{order.customer_full_name}</p><p className="mt-1 text-sm text-(--muted)">{order.customer_phone}</p>{order.customer_email && <p className="mt-1 break-all text-sm text-(--muted)">{order.customer_email}</p>}
            <a className="mt-4 inline-block rounded-full bg-[#1f7a46] px-4 py-2 text-sm font-semibold text-white" href={`https://wa.me/${whatsappNumber(order.customer_phone)}?text=${whatsappMessage}`} rel="noreferrer" target="_blank">Message on WhatsApp</a>
          </section>
          <section className="checkout-card"><h2 className="text-lg font-semibold">Delivery</h2><p className="mt-4 text-sm font-medium">{order.delivery_area_name}</p><p className="mt-2 text-sm leading-6 text-(--muted)">{order.delivery_address}</p>{order.delivery_directions && <p className="mt-3 border-t border-[var(--line)] pt-3 text-xs leading-5 text-(--muted)">Landmark: {order.delivery_directions}</p>}</section>
          <section className="checkout-card"><h2 className="text-lg font-semibold">Payment</h2><p className="mt-4 text-sm">{order.payment_status.replaceAll("_", " ")}</p>{order.refunds.map((refund) => <div className="mt-3 rounded-xl bg-[var(--sand)] p-3 text-sm" key={refund.id}><p>Refund: {refund.status}</p><p className="mt-1 text-xs text-(--muted)">{formatNaira(refund.amount_minor)}</p></div>)}</section>
        </aside>
      </div>
    </main>
  );
}
