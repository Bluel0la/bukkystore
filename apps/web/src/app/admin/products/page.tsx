import Link from "next/link";
import { redirect } from "next/navigation";

import { AdminProductBulkList } from "@/components/admin-product-bulk-list";
import { getAdminProducts, getAdminUser } from "@/lib/admin";

const STATUSES = ["ALL", "ACTIVE", "DRAFT", "ARCHIVED"] as const;
type StatusFilter = (typeof STATUSES)[number];

export default async function AdminProductsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string | string[]; status?: string | string[] }>;
}) {
  const params = await searchParams;
  const query = typeof params.q === "string" ? params.q.trim() : "";
  const requested =
    typeof params.status === "string" ? params.status.toUpperCase() : "ACTIVE";
  const status: StatusFilter = (STATUSES as readonly string[]).includes(requested)
    ? (requested as StatusFilter)
    : "ACTIVE";
  const [user, page] = await Promise.all([
    getAdminUser(),
    getAdminProducts({ search: query || undefined, status: status === "ALL" ? undefined : status }),
  ]);
  if (!user) redirect("/admin/login");
  const items = page?.items ?? [];

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-5 py-6 sm:px-8">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-(--muted)">Catalogue</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em]">Products</h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-(--muted)">
            Every product in one place. Tap one to edit details, stock, photos, or archive it.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="rounded-full border border-[var(--line)] bg-white px-4 py-2 text-sm" href="/admin">Back</Link>
          <Link className="admin-primary" href="/admin/products/new">Add product</Link>
        </div>
      </header>

      <form action="/admin/products" className="flex flex-wrap gap-3" method="get" role="search">
        <input
          aria-label="Search products"
          className="admin-input min-w-52 flex-1"
          defaultValue={query}
          maxLength={80}
          name="q"
          placeholder="Search by name…"
          type="search"
        />
        {status !== "ALL" && <input name="status" type="hidden" value={status} />}
        <button className="rounded-full border border-[var(--line)] bg-white px-5 py-2 text-sm" type="submit">Search</button>
      </form>
      <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Filter by status">
        {STATUSES.map((option) => (
          <Link
            key={option}
            aria-current={status === option ? "page" : undefined}
            className={`rounded-full border px-4 py-2 text-sm transition hover:border-[var(--wine)] ${status === option ? "border-[var(--wine)] bg-white font-semibold" : "border-[var(--line)] bg-white"}`}
            href={`/admin/products${option === "ACTIVE" && !query ? "" : `?${new URLSearchParams({ ...(query ? { q: query } : {}), status: option })}`}`}
          >
            {option === "ALL" ? "All" : option === "ACTIVE" ? "Published" : option === "DRAFT" ? "Drafts" : "Archived"}
          </Link>
        ))}
      </div>

      <div className="mt-6">
        <AdminProductBulkList archivedTab={status === "ARCHIVED"} items={items} />
        {!items.length && (
          <p className="mt-4 rounded-2xl border border-[var(--line)] bg-white p-8 text-center text-sm text-(--muted)">
            {query || status === "DRAFT" || status === "ARCHIVED"
              ? "No products match. Try a different search or filter."
              : status === "ALL"
                ? "No products yet. Add your first one above."
                : "Nothing published yet."}
          </p>
        )}
      </div>
    </main>
  );
}
