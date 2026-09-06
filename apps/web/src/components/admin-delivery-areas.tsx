"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { readCsrfCookie } from "@/lib/admin-client";
import type { AdminDeliveryArea } from "@/lib/admin-types";
import { formatNaira } from "@/lib/catalogue";

export function AdminDeliveryAreas({ initial }: { initial: AdminDeliveryArea[] }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [fee, setFee] = useState("");
  const [editing, setEditing] = useState<Record<string, string>>({});
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");

  async function mutate(path: string, method: string, body: object, action: string) {
    const csrf = readCsrfCookie();
    if (!csrf) {
      setError("Your admin session security token is missing. Please sign in again.");
      return;
    }
    setPending(action);
    setError("");
    try {
      const response = await fetch(`/api/admin/${path}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": `delivery:${crypto.randomUUID()}`,
          "X-CSRF-Token": csrf,
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const result = (await response.json()) as { message?: string };
        setError(result.message ?? "The delivery area could not be saved.");
        return;
      }
      setName("");
      setFee("");
      setEditing({});
      router.refresh();
    } catch {
      setError("The delivery service is unavailable. Please try again.");
    } finally {
      setPending("");
    }
  }

  function addArea() {
    const feeMinor = Math.round(Number(fee) * 100);
    if (name.trim().length < 2) {
      setError("Area name needs at least 2 characters.");
      return;
    }
    if (!Number.isFinite(feeMinor) || feeMinor < 0) {
      setError("Fee must be a positive amount in naira.");
      return;
    }
    void mutate(
      "delivery-areas",
      "POST",
      { name: name.trim(), fee_minor: feeMinor, display_position: initial.length },
      "add",
    );
  }

  function saveFee(area: AdminDeliveryArea) {
    const raw = editing[area.id];
    const feeMinor = Math.round(Number(raw) * 100);
    if (!Number.isFinite(feeMinor) || feeMinor < 0) {
      setError("Fee must be a positive amount in naira.");
      return;
    }
    void mutate(`delivery-areas/${area.id}`, "PATCH", { fee_minor: feeMinor }, `fee:${area.id}`);
  }

  function toggleActive(area: AdminDeliveryArea) {
    void mutate(
      `delivery-areas/${area.id}`,
      "PATCH",
      { is_active: !area.is_active },
      `toggle:${area.id}`,
    );
  }

  return (
    <div className="grid gap-5">
      <section className="checkout-card" aria-labelledby="add-area-heading">
        <h2 className="text-lg font-semibold" id="add-area-heading">Add delivery area</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_10rem_auto]">
          <label className="block text-sm">Area name<input className="admin-input mt-2" maxLength={120} onChange={(event) => setName(event.target.value)} placeholder="e.g. Ikeja" value={name} /></label>
          <label className="block text-sm">Fee (₦)<input className="admin-input mt-2" inputMode="decimal" onChange={(event) => setFee(event.target.value)} placeholder="2000" value={fee} /></label>
          <button className="admin-primary self-end" disabled={pending === "add"} onClick={addArea} type="button">{pending === "add" ? "Adding…" : "Add area"}</button>
        </div>
      </section>

      <section className="checkout-card" aria-labelledby="areas-heading">
        <h2 className="text-lg font-semibold" id="areas-heading">Delivery areas</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">Checkout only offers active areas. Deactivate instead of deleting to keep order history intact.</p>
        <div className="mt-4 grid gap-3">
          {initial.map((area) => (
            <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-[var(--line)] p-3" key={area.id}>
              <div className="min-w-36 flex-1">
                <p className="font-medium">{area.name}</p>
                <p className="mt-1 text-xs text-[var(--muted)]">{formatNaira(area.fee_minor)}{area.is_active ? "" : " · inactive"}</p>
              </div>
              <label className="flex items-center gap-2 text-sm">Fee (₦)<input aria-label={`${area.name} fee in naira`} className="admin-input w-28" inputMode="decimal" onChange={(event) => setEditing((current) => ({ ...current, [area.id]: event.target.value }))} placeholder={String(area.fee_minor / 100)} value={editing[area.id] ?? ""} /></label>
              <button className="rounded-full border border-[var(--line)] px-4 py-2 text-sm disabled:opacity-50" disabled={pending === `fee:${area.id}` || editing[area.id] == null || editing[area.id] === ""} onClick={() => saveFee(area)} type="button">{pending === `fee:${area.id}` ? "Saving…" : "Save fee"}</button>
              <button className="rounded-full border border-[var(--line)] px-4 py-2 text-sm disabled:opacity-50" disabled={pending === `toggle:${area.id}`} onClick={() => toggleActive(area)} type="button">{area.is_active ? "Deactivate" : "Activate"}</button>
            </div>
          ))}
          {!initial.length && <p className="text-sm text-[var(--muted)]">No delivery areas yet. Add the first one above.</p>}
        </div>
        <p aria-live="polite" className="mt-3 text-sm text-[var(--wine)]">{error}</p>
      </section>
    </div>
  );
}
