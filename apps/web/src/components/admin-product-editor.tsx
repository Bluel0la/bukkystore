"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { readCsrfCookie } from "@/lib/admin-client";
import { AdminProductPhotos } from "@/components/admin-product-photos";
import type { AdminProduct, AdminVariant } from "@/lib/admin-types";
import type { Category } from "@/lib/catalogue";

function StockAdjustment({ variant }: { variant: AdminVariant }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const csrf = readCsrfCookie();
    if (!csrf) return setError("Your session expired.");
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError("");
    const response = await fetch(`/api/admin/variants/${variant.id}/stock-adjustments`, {
      method: "POST",
      headers: { "content-type": "application/json", "X-CSRF-Token": csrf, "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({ quantity_delta: Number(form.get("delta")), reason: form.get("reason") }),
    });
    if (!response.ok) {
      const body = await response.json();
      setError(body.message ?? "Stock could not be changed.");
    } else {
      formElement.reset();
      router.refresh();
    }
    setPending(false);
  }

  return (
    <form className="grid gap-3 rounded-2xl border border-[var(--line)] p-4" onSubmit={submit}>
      <div className="flex items-start justify-between gap-4"><div><p className="font-medium">{variant.display_name}</p><p className="mt-1 text-xs text-(--muted)">{variant.sku}</p></div><div className="text-right"><p className="text-2xl font-semibold">{variant.stock_on_hand}</p><p className="text-xs text-(--muted)">{variant.reserved_quantity} reserved</p></div></div>
      <div className="grid gap-3 sm:grid-cols-[7rem_1fr_auto]"><input aria-label={`Stock change for ${variant.display_name}`} className="admin-input" name="delta" placeholder="+3 or -1" required type="number" /><input aria-label={`Reason for ${variant.display_name}`} className="admin-input" maxLength={500} name="reason" placeholder="Reason for change" required /><button className="rounded-full bg-[var(--ink)] px-4 py-2 text-sm text-white" disabled={pending} type="submit">{pending ? "Saving…" : "Adjust"}</button></div>
      {error && <p className="text-xs text-(--wine)" role="alert">{error}</p>}
    </form>
  );
}

export function AdminProductEditor({ product, categories }: { product: AdminProduct; categories: Category[] }) {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const [confirmingArchive, setConfirmingArchive] = useState(false);
  const [archiveError, setArchiveError] = useState("");
  const [archiving, setArchiving] = useState(false);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const csrf = readCsrfCookie();
    if (!csrf) return setMessage("Your session expired.");
    const form = new FormData(event.currentTarget);
    setPending(true);
    const response = await fetch(`/api/admin/products/${product.id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({
        category_id: form.get("categoryId"), name: form.get("name"), slug: form.get("slug"),
        description: form.get("description"), base_price_minor: Math.round(Number(form.get("price")) * 100),
        status: form.get("status"), featured: form.get("featured") === "on",
      }),
    });
    setMessage(response.ok ? "Product details saved." : "Product details could not be saved.");
    setPending(false);
    if (response.ok) router.refresh();
  }

  async function readError(response: Response, fallback: string): Promise<string> {
    try {
      const body = (await response.json()) as { message?: string; code?: string };
      const detail = [body.code, body.message ?? fallback].filter(Boolean).join(" · ");
      return `${fallback} (HTTP ${response.status} · ${detail}).`;
    } catch {
      return `${fallback} (HTTP ${response.status}).`;
    }
  }

  async function archive() {
    const csrf = readCsrfCookie();
    if (!csrf) {
      setArchiveError("Your session expired.");
      return;
    }
    setArchiving(true);
    setArchiveError("");
    try {
      const response = await fetch(`/api/admin/products/${product.id}/archive`, {
        method: "POST",
        headers: { "X-CSRF-Token": csrf },
      });
      if (!response.ok) {
        setArchiveError(await readError(response, "Product could not be archived"));
        return;
      }
      setConfirmingArchive(false);
      router.refresh();
    } catch {
      setArchiveError("Product could not be archived. Please try again.");
    } finally {
      setArchiving(false);
    }
  }

  async function restore() {
    const csrf = readCsrfCookie();
    if (!csrf) {
      setArchiveError("Your session expired.");
      return;
    }
    setArchiving(true);
    setArchiveError("");
    try {
      const response = await fetch(`/api/admin/products/${product.id}/unarchive`, {
        method: "POST",
        headers: { "X-CSRF-Token": csrf },
      });
      if (!response.ok) {
        setArchiveError(await readError(response, "Product could not be restored"));
        return;
      }
      router.refresh();
    } catch {
      setArchiveError("Product could not be restored. Please try again.");
    } finally {
      setArchiving(false);
    }
  }

  return (
    <div className="grid gap-8">
      <AdminProductPhotos initialImages={product.images} productId={product.id} productName={product.name} />
      <form className="grid gap-5 rounded-3xl border border-[var(--line)] bg-white p-5 sm:p-7" onSubmit={save}>
        <div className="grid gap-5 sm:grid-cols-2"><label className="grid gap-2 text-sm">Name<input className="admin-input" defaultValue={product.name} name="name" required /></label><label className="grid gap-2 text-sm">Slug<input className="admin-input" defaultValue={product.slug} name="slug" required /></label><label className="grid gap-2 text-sm">Category<select className="admin-input" defaultValue={product.category.id} name="categoryId">{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label><label className="grid gap-2 text-sm">Price (₦)<input className="admin-input" defaultValue={product.base_price_minor / 100} min="0" name="price" step="0.01" type="number" /></label><label className="grid gap-2 text-sm">Visibility<select className="admin-input" defaultValue={product.status} name="status"><option value="DRAFT">Draft</option><option value="ACTIVE">Published</option></select></label></div>
        <label className="grid gap-2 text-sm">Description<textarea className="admin-input min-h-28" defaultValue={product.description} name="description" /></label><label className="flex gap-3 text-sm"><input defaultChecked={product.featured} name="featured" type="checkbox" /> Feature on storefront</label>
        {message && <p className="text-sm" role="status">{message}</p>}<button className="admin-primary justify-self-start" disabled={pending} type="submit">{pending ? "Saving…" : "Save details"}</button>
      </form>
      <section><div className="mb-4"><h2 className="text-xl font-semibold">Stock by option</h2><p className="mt-1 text-sm text-(--muted)">Use a positive number to add stock or a negative number to correct it down.</p></div><div className="grid gap-3">{product.variants.map((variant) => <StockAdjustment key={variant.id} variant={variant} />)}</div></section>
      <section aria-labelledby="danger-zone-heading" className="rounded-3xl border border-[var(--wine)]/40 bg-white p-5 sm:p-7">
        <h2 className="text-xl font-semibold" id="danger-zone-heading">Danger zone</h2>
        {product.status === "ARCHIVED" ? (
          <div>
            <p className="mt-2 text-sm text-(--muted)">This product is archived. It is hidden from the storefront but kept for order history.</p>
            <button className="mt-4 rounded-full border border-[var(--line)] bg-white px-5 py-2 text-sm font-semibold" disabled={archiving} onClick={restore} type="button">{archiving ? "Restoring…" : "Restore to published"}</button>
            {archiveError && <p className="mt-3 text-sm text-(--wine)" role="alert">{archiveError}</p>}
          </div>
        ) : confirmingArchive ? (
          <div>
            <p className="mt-2 text-sm">Archive <strong>{product.name}</strong>? It will disappear from the storefront immediately. This cannot be undone from here.</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button className="rounded-full bg-[var(--wine)] px-5 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={archiving} onClick={archive} type="button">{archiving ? "Archiving…" : "Yes, archive it"}</button>
              <button className="rounded-full border border-[var(--line)] px-5 py-2 text-sm" disabled={archiving} onClick={() => setConfirmingArchive(false)} type="button">Keep it</button>
            </div>
            {archiveError && <p className="mt-3 text-sm text-(--wine)" role="alert">{archiveError}</p>}
          </div>
        ) : (
          <div>
            <p className="mt-2 text-sm text-(--muted)">Archiving hides the product from shoppers while preserving past orders.</p>
            <button className="mt-4 rounded-full border border-[var(--wine)] px-5 py-2 text-sm font-semibold text-(--wine)" onClick={() => { setArchiveError(""); setConfirmingArchive(true); }} type="button">Archive product</button>
            {archiveError && <p className="mt-3 text-sm text-(--wine)" role="alert">{archiveError}</p>}
          </div>
        )}
      </section>
    </div>
  );
}
