"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { readCsrfCookie } from "@/lib/admin-client";
import type { AdminCategory } from "@/lib/admin-types";
import { formatApiError } from "@/lib/api-errors";

export function slugify(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[_\s]+/g, "-")
    .replace(/[^a-z0-9-]/g, "")
    .replace(/-{2,}/g, "-")
    .replace(/^-+|-+$/g, "");
}

async function mutate(
  path: string,
  method: string,
  body: object,
): Promise<{ ok: boolean; status: number; body: unknown }> {
  const csrf = readCsrfCookie();
  if (!csrf) throw new Error("Your session expired.");
  const response = await fetch(`/api/admin/${path}`, {
    method,
    headers: { "content-type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify(body),
  });
  let parsed: unknown = null;
  try {
    parsed = await response.json();
  } catch {
    parsed = null;
  }
  return { ok: response.ok, status: response.status, body: parsed };
}

function parentName(categories: AdminCategory[], parentId: string | null): string | null {
  if (!parentId) return null;
  return categories.find((category) => category.id === parentId)?.name ?? null;
}

export function AdminCategories({ initial }: { initial: AdminCategory[] }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [parentId, setParentId] = useState("");
  const [renaming, setRenaming] = useState<Record<string, string>>({});
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");
  const topLevel = initial.filter((category) => !category.parent_id);

  function onNameChange(value: string) {
    setName(value);
    if (!slugTouched) setSlug(slugify(value));
  }

  async function addCategory() {
    const cleanSlug = slugify(slug || name);
    if (name.trim().length < 2 || !cleanSlug) {
      setError("Give the category a name of at least 2 characters.");
      return;
    }
    setPending("add");
    setError("");
    try {
      const result = await mutate("categories", "POST", {
        name: name.trim(),
        slug: cleanSlug,
        parent_id: parentId || null,
      });
      if (!result.ok) {
        setError(formatApiError(result.body, "The category could not be added."));
        return;
      }
      setName("");
      setSlug("");
      setSlugTouched(false);
      setParentId("");
      router.refresh();
    } catch {
      setError("The catalogue service is unavailable. Please try again.");
    } finally {
      setPending("");
    }
  }

  async function saveRename(category: AdminCategory) {
    const next = (renaming[category.id] ?? "").trim();
    if (next.length < 2) {
      setError("Names need at least 2 characters.");
      return;
    }
    setPending(`rename:${category.id}`);
    setError("");
    try {
      const result = await mutate(`categories/${category.id}`, "PATCH", {
        name: next,
        slug: slugify(next),
      });
      if (!result.ok) {
        setError(formatApiError(result.body, "The category could not be renamed."));
        return;
      }
      setRenaming((current) => {
        const copy = { ...current };
        delete copy[category.id];
        return copy;
      });
      router.refresh();
    } catch {
      setError("The catalogue service is unavailable. Please try again.");
    } finally {
      setPending("");
    }
  }

  async function toggleActive(category: AdminCategory) {
    setPending(`toggle:${category.id}`);
    setError("");
    try {
      const result = await mutate(`categories/${category.id}`, "PATCH", {
        is_active: !category.is_active,
      });
      if (!result.ok) {
        setError(formatApiError(result.body, "The category could not be updated."));
        return;
      }
      router.refresh();
    } catch {
      setError("The catalogue service is unavailable. Please try again.");
    } finally {
      setPending("");
    }
  }

  return (
    <div className="grid gap-5">
      <section className="checkout-card" aria-labelledby="add-category-heading">
        <h2 className="text-lg font-semibold" id="add-category-heading">Add a category</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_10rem_auto]">
          <label className="block text-sm">Name<input className="admin-input mt-2" maxLength={100} onChange={(event) => onNameChange(event.target.value)} placeholder="e.g. Kaftans" value={name} /></label>
          <label className="block text-sm">Link slug<input className="admin-input mt-2" maxLength={200} onChange={(event) => { setSlug(event.target.value); setSlugTouched(true); }} placeholder="kaftans" value={slug} /></label>
          <label className="block text-sm">Under<select className="admin-input mt-2" onChange={(event) => setParentId(event.target.value)} value={parentId}><option value="">Top level</option>{topLevel.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
          <button className="admin-primary self-end" disabled={pending === "add"} onClick={addCategory} type="button">{pending === "add" ? "Adding…" : "Add"}</button>
        </div>
      </section>

      <section className="checkout-card" aria-labelledby="categories-heading">
        <h2 className="text-lg font-semibold" id="categories-heading">Categories</h2>
        <p className="mt-1 text-sm text-(--muted)">Switching a category off hides it from shoppers. Categories are never deleted so past orders keep their history.</p>
        <div className="mt-4 grid gap-3">
          {initial.map((category) => {
            const parent = parentName(initial, category.parent_id);
            const editing = renaming[category.id] !== undefined;
            return (
              <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-[var(--line)] p-3" key={category.id}>
                <div className="min-w-36 flex-1">
                  {editing ? (
                    <input
                      aria-label={`New name for ${category.name}`}
                      className="admin-input"
                      maxLength={100}
                      onChange={(event) => setRenaming((current) => ({ ...current, [category.id]: event.target.value }))}
                      value={renaming[category.id] ?? ""}
                    />
                  ) : (
                    <>
                      <p className="font-medium">{category.name}</p>
                      <p className="mt-1 text-xs text-(--muted)">
                        /{category.slug}{parent ? ` · under ${parent}` : ""}
                        {category.is_active ? "" : " · hidden"}
                      </p>
                    </>
                  )}
                </div>
                {editing ? (
                  <>
                    <button className="rounded-full border border-[var(--line)] px-4 py-2 text-sm disabled:opacity-50" disabled={pending === `rename:${category.id}`} onClick={() => saveRename(category)} type="button">{pending === `rename:${category.id}` ? "Saving…" : "Save"}</button>
                    <button
                      className="rounded-full border border-[var(--line)] px-4 py-2 text-sm"
                      onClick={() => setRenaming((current) => {
                        const copy = { ...current };
                        delete copy[category.id];
                        return copy;
                      })}
                      type="button"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      className="rounded-full border border-[var(--line)] px-4 py-2 text-sm"
                      onClick={() => setRenaming((current) => ({ ...current, [category.id]: category.name }))}
                      type="button"
                    >
                      Rename
                    </button>
                    <button
                      className="rounded-full border border-[var(--line)] px-4 py-2 text-sm disabled:opacity-50"
                      disabled={pending === `toggle:${category.id}`}
                      onClick={() => toggleActive(category)}
                      type="button"
                    >
                      {category.is_active ? "Hide" : "Show"}
                    </button>
                  </>
                )}
              </div>
            );
          })}
          {!initial.length && <p className="text-sm text-(--muted)">No categories yet. Add the first one above.</p>}
        </div>
        <p aria-live="polite" className="mt-3 text-sm text-(--wine)">{error}</p>
      </section>
    </div>
  );
}
