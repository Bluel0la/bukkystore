"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { readCsrfCookie } from "@/lib/admin-client";
import type { AdminRefund } from "@/lib/admin-types";

const transitionLabels: Record<string, string> = {
  START_PROCESSING: "Start processing",
  MARK_OUT_FOR_DELIVERY: "Mark out for delivery",
  MARK_COMPLETED: "Mark completed",
};

export function AdminOrderActions({ orderId, availableActions, refunds }: {
  orderId: string;
  availableActions: string[];
  refunds: AdminRefund[];
}) {
  const router = useRouter();
  const [reason, setReason] = useState("");
  const [reference, setReference] = useState("");
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");
  const pendingRefund = refunds.find((refund) => refund.status === "PENDING");

  async function mutate(path: string, body: object, action: string) {
    const csrf = readCsrfCookie();
    if (!csrf) {
      setError("Your admin session security token is missing. Please sign in again.");
      return;
    }
    setPending(action);
    setError("");
    try {
      const response = await fetch(`/api/admin/${path}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": `order:${crypto.randomUUID()}`,
          "X-CSRF-Token": csrf,
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const result = (await response.json()) as { message?: string };
        setError(result.message ?? "The order could not be updated.");
        return;
      }
      router.refresh();
    } catch {
      setError("The order service is unavailable. Please try again.");
    } finally {
      setPending("");
    }
  }

  const transition = availableActions.find((action) => action in transitionLabels);

  return (
    <section className="checkout-card" aria-labelledby="order-actions-heading">
      <h2 className="text-lg font-semibold" id="order-actions-heading">Next action</h2>
      {transition && <button className="admin-primary mt-4 w-full" disabled={Boolean(pending)} onClick={() => mutate(`orders/${orderId}/transitions`, { action: transition }, transition)} type="button">{pending === transition ? "Updating order…" : transitionLabels[transition]}</button>}
      {availableActions.includes("CANCEL") && <details className="mt-4 rounded-2xl border border-[var(--line)] p-4"><summary className="cursor-pointer text-sm font-medium text-[var(--wine)]">Cancel order</summary><label className="mt-4 block text-sm">Cancellation reason<textarea className="admin-input mt-2 min-h-24" maxLength={500} minLength={5} onChange={(event) => setReason(event.target.value)} required value={reason} /></label><button className="mt-3 w-full rounded-full border border-[var(--wine)] px-5 py-3 text-sm font-semibold text-[var(--wine)] disabled:opacity-50" disabled={Boolean(pending) || reason.trim().length < 5} onClick={() => mutate(`orders/${orderId}/cancellations`, { reason }, "CANCEL")} type="button">{pending === "CANCEL" ? "Cancelling safely…" : "Confirm cancellation"}</button></details>}
      {availableActions.includes("COMPLETE_REFUND") && pendingRefund && <div className="mt-4 rounded-2xl bg-[var(--sand)] p-4"><p className="text-sm font-medium">Refund due</p><p className="mt-1 text-xs leading-5 text-[var(--muted)]">Send the refund outside the store, then record its transfer reference here.</p><label className="mt-3 block text-sm">Transfer reference <span className="text-[var(--muted)]">(optional)</span><input className="admin-input mt-2" maxLength={120} onChange={(event) => setReference(event.target.value)} value={reference} /></label><button className="admin-primary mt-3 w-full" disabled={Boolean(pending)} onClick={() => mutate(`refunds/${pendingRefund.id}/complete`, { manual_reference: reference.trim() || null }, "COMPLETE_REFUND")} type="button">{pending === "COMPLETE_REFUND" ? "Recording refund…" : "Mark refund sent"}</button></div>}
      {!availableActions.length && <p className="mt-3 text-sm text-[var(--muted)]">No further order actions are available.</p>}
      <p aria-live="polite" className="mt-3 text-sm text-[var(--wine)]">{error}</p>
    </section>
  );
}
