import Link from "next/link";
import { redirect } from "next/navigation";

import { AdminProductForm } from "@/components/admin-product-form";
import { getAdminCategories, getAdminUser } from "@/lib/admin";

export default async function NewProductPage() {
  const [user, categories] = await Promise.all([getAdminUser(), getAdminCategories()]);
  if (!user || !categories) redirect("/admin/login");
  return <main className="mx-auto min-h-screen max-w-5xl px-5 py-6 sm:px-8"><header className="mb-8 flex items-center justify-between"><div><p className="text-sm text-[var(--muted)]">Catalogue</p><h1 className="text-3xl font-semibold tracking-[-0.04em]">Add a product</h1></div><Link className="rounded-full border border-[var(--line)] px-4 py-2 text-sm" href="/admin">Cancel</Link></header><AdminProductForm categories={categories} /></main>;
}
