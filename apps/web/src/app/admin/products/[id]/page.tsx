import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { AdminProductEditor } from "@/components/admin-product-editor";
import { AdminSharePanel } from "@/components/admin-share-panel";
import { getAdminCategories, getAdminProduct, getAdminUser, getProductEngagement } from "@/lib/admin";

export default async function EditProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [user, product, categories, engagement] = await Promise.all([getAdminUser(), getAdminProduct(id), getAdminCategories(), getProductEngagement(id).catch(() => null)]);
  if (!user) redirect("/admin/login");
  if (!product || !categories) notFound();
  return <main className="mx-auto min-h-screen max-w-5xl px-5 py-6 sm:px-8"><header className="mb-8 flex items-center justify-between"><div><p className="text-sm text-[var(--muted)]">{product.category.name}</p><h1 className="text-3xl font-semibold tracking-[-0.04em]">{product.name}</h1></div><Link className="rounded-full border border-[var(--line)] px-4 py-2 text-sm" href="/admin">Back</Link></header><div className="grid gap-5"><AdminSharePanel engagement={engagement} productSlug={product.slug} /><AdminProductEditor categories={categories} product={product} /></div></main>;
}
