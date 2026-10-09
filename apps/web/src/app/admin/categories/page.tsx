import Link from "next/link";
import { redirect } from "next/navigation";

import { AdminCategories } from "@/components/admin-categories";
import { getAdminCategories, getAdminUser } from "@/lib/admin";

export default async function AdminCategoriesPage() {
  const [user, categories] = await Promise.all([getAdminUser(), getAdminCategories()]);
  if (!user || !categories) redirect("/admin/login");

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-5 py-6 sm:px-8">
      <header className="mb-8 flex items-center justify-between gap-4">
        <div>
          <p className="text-sm text-(--muted)">Catalogue</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em]">Categories</h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-(--muted)">
            Group products for the storefront. Changes appear in the shop immediately.
          </p>
        </div>
        <Link className="rounded-full border border-[var(--line)] px-4 py-2 text-sm" href="/admin">Back</Link>
      </header>
      <AdminCategories initial={categories} />
    </main>
  );
}
