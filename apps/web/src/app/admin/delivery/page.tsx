import Link from "next/link";
import { redirect } from "next/navigation";

import { AdminDeliveryAreas } from "@/components/admin-delivery-areas";
import { getAdminDeliveryAreas, getAdminUser } from "@/lib/admin";

export default async function AdminDeliveryPage() {
  const [user, areas] = await Promise.all([getAdminUser(), getAdminDeliveryAreas()]);
  if (!user || !areas) redirect("/admin/login");

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-5 py-6 sm:px-8">
      <header className="mb-8 flex items-center justify-between gap-4">
        <div>
          <p className="text-sm text-[var(--muted)]">Store</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em]">Delivery areas</h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--muted)]">
            The areas and flat fees customers choose at checkout. Changes apply immediately.
          </p>
        </div>
        <Link className="rounded-full border border-[var(--line)] px-4 py-2 text-sm" href="/admin">Back</Link>
      </header>
      <AdminDeliveryAreas initial={areas} />
    </main>
  );
}
