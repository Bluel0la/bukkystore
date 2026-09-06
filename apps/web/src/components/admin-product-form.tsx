"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import type { Category } from "@/lib/catalogue";
import { readCsrfCookie } from "@/lib/admin-client";

type DraftVariant = { colour: string; size: string; displayName: string; stock: string };
const emptyVariant = (): DraftVariant => ({ colour: "", size: "", displayName: "", stock: "0" });

export function AdminProductForm({ categories }: { categories: Category[] }) {
  const router = useRouter();
  const [variants, setVariants] = useState<DraftVariant[]>([emptyVariant()]);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  function updateVariant(index: number, field: keyof DraftVariant, value: string) {
    setVariants((current) => current.map((variant, position) => position === index ? { ...variant, [field]: value } : variant));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const csrf = readCsrfCookie();
    if (!csrf) return setError("Your session expired. Please sign in again.");
    const form = new FormData(event.currentTarget);
    setError("");
    setPending(true);
    const price = Math.round(Number(form.get("price")) * 100);
    const compareValue = String(form.get("comparePrice") ?? "").trim();
    const payload = {
      category_id: form.get("categoryId"),
      name: form.get("name"),
      slug: form.get("slug"),
      description: form.get("description"),
      base_price_minor: price,
      compare_at_price_minor: compareValue ? Math.round(Number(compareValue) * 100) : null,
      status: form.get("status"),
      featured: form.get("featured") === "on",
      variants: variants.map((variant) => ({
        sku: null,
        colour: variant.colour || null,
        size: variant.size || null,
        display_name: variant.displayName,
        initial_stock: Number(variant.stock),
        low_stock_threshold: 2,
      })),
    };
    try {
      const response = await fetch("/api/admin/products", {
        method: "POST",
        headers: { "content-type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify(payload),
      });
      const body = await response.json();
      if (!response.ok) {
        setError(body.message ?? "The product could not be saved.");
        return;
      }
      router.push(`/admin/products/${body.id}`);
      router.refresh();
    } catch {
      setError("The product could not be saved. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="grid gap-8" onSubmit={submit}>
      <section className="grid gap-5 rounded-3xl border border-[var(--line)] bg-white p-5 sm:p-7">
        <h2 className="text-xl font-semibold">Product details</h2>
        <div className="grid gap-5 sm:grid-cols-2">
          <label className="grid gap-2 text-sm font-medium">Name<input className="admin-input" name="name" required /></label>
          <label className="grid gap-2 text-sm font-medium">Shareable slug<input className="admin-input" name="slug" pattern="[a-z0-9]+(?:-[a-z0-9]+)*" placeholder="brown-linen-dress" required /></label>
          <label className="grid gap-2 text-sm font-medium">Category<select className="admin-input" name="categoryId" required>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
          <label className="grid gap-2 text-sm font-medium">Selling price (₦)<input className="admin-input" min="0" name="price" required step="0.01" type="number" /></label>
          <label className="grid gap-2 text-sm font-medium">Compare-at price (₦), optional<input className="admin-input" min="0" name="comparePrice" step="0.01" type="number" /></label>
          <label className="grid gap-2 text-sm font-medium">Visibility<select className="admin-input" defaultValue="DRAFT" name="status"><option value="DRAFT">Draft</option><option value="ACTIVE">Published</option></select></label>
        </div>
        <label className="grid gap-2 text-sm font-medium">Description<textarea className="admin-input min-h-32 resize-y" maxLength={10000} name="description" /></label>
        <label className="flex items-center gap-3 text-sm"><input name="featured" type="checkbox" /> Feature on the storefront</label>
      </section>

      <section className="rounded-3xl border border-[var(--line)] bg-white p-5 sm:p-7">
        <div className="flex items-center justify-between gap-4"><div><h2 className="text-xl font-semibold">Colours, sizes and stock</h2><p className="mt-1 text-sm text-(--muted)">Add one row for every option customers can choose. Product codes are generated automatically.</p></div><button className="rounded-full border border-[var(--line)] px-4 py-2 text-sm" onClick={() => setVariants((current) => [...current, emptyVariant()])} type="button">Add option</button></div>
        <div className="mt-6 grid gap-4">
          {variants.map((variant, index) => (
            <fieldset className="grid gap-3 rounded-2xl bg-[var(--paper)] p-4 sm:grid-cols-4" key={index}>
              <legend className="sr-only">Option {index + 1}</legend>
              <label className="grid gap-1 text-xs">Colour<input className="admin-input" onChange={(event) => updateVariant(index, "colour", event.target.value)} value={variant.colour} /></label>
              <label className="grid gap-1 text-xs">Size<input className="admin-input" onChange={(event) => updateVariant(index, "size", event.target.value)} value={variant.size} /></label>
              <label className="grid gap-1 text-xs">Display name<input className="admin-input" onChange={(event) => updateVariant(index, "displayName", event.target.value)} required value={variant.displayName} /></label>
              <label className="grid gap-1 text-xs">Opening stock<input className="admin-input" min="0" onChange={(event) => updateVariant(index, "stock", event.target.value)} required type="number" value={variant.stock} /></label>
              {variants.length > 1 && <button className="justify-self-start text-xs text-(--wine) sm:col-span-4" onClick={() => setVariants((current) => current.filter((_, position) => position !== index))} type="button">Remove option</button>}
            </fieldset>
          ))}
        </div>
      </section>
      {error && <p className="rounded-xl bg-[#f4e6e7] p-4 text-sm text-(--wine)" role="alert">{error}</p>}
      <div className="flex justify-end"><button className="admin-primary min-w-40" disabled={pending} type="submit">{pending ? "Saving…" : "Save product"}</button></div>
    </form>
  );
}
