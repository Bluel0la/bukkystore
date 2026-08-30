"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function DemoPaymentPanel({ order, token }: { order: string; token: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function confirm() {
    setPending(true);
    setError("");
    try {
      const response = await fetch("/api/payments/fake/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ order_number: order, order_access_token: token }),
      });
      if (!response.ok) {
        const result = (await response.json()) as { message?: string };
        setError(result.message ?? "Payment could not be confirmed.");
        return;
      }
      router.push(`/orders/${encodeURIComponent(order)}?token=${encodeURIComponent(token)}`);
    } catch {
      setError("We could not reach payment confirmation. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mt-8">
      <button className="admin-primary w-full" disabled={pending} onClick={confirm} type="button">
        {pending ? "Confirming payment…" : "Simulate successful payment"}
      </button>
      <p aria-live="polite" className="mt-3 text-sm text-[var(--wine)]">{error}</p>
    </div>
  );
}
