"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { readCsrfCookie } from "@/lib/admin-client";
import type { AdminProduct } from "@/lib/admin-types";
import { formatNaira } from "@/lib/catalogue";

function stockSummary(product: AdminProduct): { label: string; tone: string } {
  const sellable = product.variants.filter((variant) => variant.status === "ACTIVE");
  const total = sellable.reduce((sum, variant) => sum + variant.available_quantity, 0);
  if (total === 0) return { label: "Out of stock", tone: "bg-[#f7e2e2] text-[#8a2d2d]" };
  const low = sellable.some(
    (variant) => variant.available_quantity <= variant.low_stock_threshold,
  );
  return {
    label: `${total} in stock`,
    tone: low ? "bg-[var(--sand)] text-(--wine)" : "bg-[#e4f3e8] text-[#1f7a46]",
  };
}

function statusLabel(status: AdminProduct["status"]): string {
  return status === "ACTIVE" ? "Published" : status === "DRAFT" ? "Draft" : "Archived";
}

export function AdminProductBulkList({
  items,
  archivedTab,
}: {
  items: AdminProduct[];
  archivedTab: boolean;
}) {
  const router = useRouter();
  const [selected, setSelected] = useState<string[]>([]);
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const action = archivedTab ? "Restore" : "Archive";

  function toggle(id: string) {
    setSelected((current) =>
      current.includes(id) ? current.filter((entry) => entry !== id) : [...current, id],
    );
  }

  function toggleAll() {
    setSelected((current) => (current.length === items.length ? [] : items.map((item) => item.id)));
  }

  async function runBulk() {
    const csrf = readCsrfCookie();
    if (!csrf) {
      setError("Your session expired.");
      return;
    }
    setPending(true);
    setError("");
    try {
      const response = await fetch("/api/admin/products/bulk-archive", {
        method: "POST",
        headers: { "content-type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify({ product_ids: selected, archived: !archivedTab }),
      });
      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const body = (await response.json()) as { message?: string; code?: string };
          detail = [body.code, body.message ?? "Bulk update failed."].filter(Boolean).join(" · ");
          detail = `Bulk update failed (HTTP ${response.status} · ${detail}).`;
        } catch {
          detail = `Bulk update failed (HTTP ${response.status}).`;
        }
        setError(detail);
        return;
      }
      setSelected([]);
      setConfirming(false);
      router.refresh();
    } catch {
      setError("Bulk update failed. Please try again.");
    } finally {
      setPending(false);
    }
  }

  if (!items.length) return null;

  return (
    <div>
      {selected.length > 0 && (
        <div className="mb-4 rounded-2xl border border-[var(--line)] bg-white p-4">
          {confirming ? (
            <div>
              <p className="text-sm">
                {action} <strong>{selected.length} product{selected.length === 1 ? "" : "s"}</strong>
                {archivedTab ? " back to published?" : "? They will disappear from the storefront."}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  className="rounded-full bg-[var(--ink)] px-5 py-2 text-sm font-semibold text-white disabled:opacity-50"
                  disabled={pending}
                  onClick={runBulk}
                  type="button"
                >
                  {pending ? "Working…" : `Yes, ${action.toLowerCase()} them`}
                </button>
                <button
                  className="rounded-full border border-[var(--line)] px-5 py-2 text-sm"
                  disabled={pending}
                  onClick={() => setConfirming(false)}
                  type="button"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm font-medium">
                {selected.length} selected
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  className="rounded-full border border-[var(--wine)] px-4 py-2 text-sm font-semibold text-(--wine)"
                  onClick={() => { setError(""); setConfirming(true); }}
                  type="button"
                >
                  {action} selected
                </button>
                <button
                  className="rounded-full border border-[var(--line)] px-4 py-2 text-sm"
                  onClick={() => setSelected([])}
                  type="button"
                >
                  Clear
                </button>
              </div>
            </div>
          )}
          {error && <p className="mt-3 text-sm text-(--wine)" role="alert">{error}</p>}
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
        <label className="flex items-center gap-3 border-b border-[var(--line)] bg-[var(--paper)] p-4 text-sm">
          <input
            checked={selected.length === items.length}
            onChange={toggleAll}
            type="checkbox"
          />
          Select all on this page
        </label>
        {items.map((product) => {
          const stock = stockSummary(product);
          const checked = selected.includes(product.id);
          return (
            <div
              className={`flex items-center gap-3 border-b border-[var(--line)] p-4 last:border-0 ${checked ? "bg-[var(--paper)]" : ""}`}
              key={product.id}
            >
              <input
                aria-label={`Select ${product.name}`}
                checked={checked}
                onChange={() => toggle(product.id)}
                type="checkbox"
              />
              <Link
                className="flex min-w-0 flex-1 items-center justify-between gap-4"
                href={`/admin/products/${product.id}`}
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{product.name}</p>
                  <p className="mt-1 truncate text-xs text-(--muted)">
                    {product.category.name} · {formatNaira(product.base_price_minor)} · {statusLabel(product.status)}
                  </p>
                </div>
                <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${stock.tone}`}>
                  {stock.label}
                </span>
              </Link>
            </div>
          );
        })}
      </div>
    </div>
  );
}
