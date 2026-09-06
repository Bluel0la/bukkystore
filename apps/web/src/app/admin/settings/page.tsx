import Link from "next/link";
import { redirect } from "next/navigation";

import { AdminSettingsForm } from "@/components/admin-settings-form";
import { getAdminStoreSettings, getAdminUser } from "@/lib/admin";

export default async function AdminSettingsPage() {
  const [user, settings] = await Promise.all([getAdminUser(), getAdminStoreSettings()]);
  if (!user) redirect("/admin/login");

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-5 py-6 sm:px-8">
      <header className="mb-8 flex items-center justify-between gap-4">
        <div>
          <p className="text-sm text-[var(--muted)]">Store</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em]">Business settings</h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--muted)]">
            The name, contact details, socials, and hours customers see across the store.
          </p>
        </div>
        <Link className="rounded-full border border-[var(--line)] px-4 py-2 text-sm" href="/admin">Back</Link>
      </header>
      {!settings && <p className="checkout-card text-sm text-[var(--muted)]">Settings are not configured yet. Run the development seed, then refresh.</p>}
      {settings && <AdminSettingsForm initial={settings} />}
    </main>
  );
}
