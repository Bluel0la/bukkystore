"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { useCart } from "@/components/cart-provider";
import { captureAttribution, loadAttribution } from "@/lib/attribution";
import { formatNaira } from "@/lib/catalogue";
import type { CheckoutResponse, DeliveryArea } from "@/lib/commerce-types";

export function CheckoutForm({
  areas,
  onPaymentReady = (url: string) => window.location.assign(url),
}: {
  areas: DeliveryArea[];
  onPaymentReady?: (url: string) => void;
}) {
  const cart = useCart();
  const [areaId, setAreaId] = useState(areas[0]?.id ?? "");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const idempotencyKey = useRef("");
  const previousPayload = useRef("");
  const area = areas.find((item) => item.id === areaId);
  const subtotal = cart.items.reduce((sum, item) => sum + item.priceMinor * item.quantity, 0);

  useEffect(() => {
    captureAttribution();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!cart.items.length || !areaId) return;
    const form = new FormData(event.currentTarget);
    const attribution = loadAttribution();
    const payload = {
      customer: {
        full_name: String(form.get("fullName") ?? ""),
        phone: String(form.get("phone") ?? ""),
        email: String(form.get("email") ?? "") || null,
      },
      delivery: {
        area_id: areaId,
        address: String(form.get("address") ?? ""),
        directions: String(form.get("directions") ?? "") || null,
      },
      items: cart.items.map((item) => ({ variant_id: item.variantId, quantity: item.quantity })),
      attribution: { source: attribution.source, campaign: attribution.campaign },
    };
    const serialized = JSON.stringify(payload);
    if (!idempotencyKey.current || previousPayload.current !== serialized) {
      idempotencyKey.current = `checkout:${crypto.randomUUID()}`;
      previousPayload.current = serialized;
    }
    setPending(true);
    setError("");
    try {
      const response = await fetch("/api/checkout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": idempotencyKey.current,
        },
        body: serialized,
      });
      const result = (await response.json()) as CheckoutResponse | { message?: string };
      if (!response.ok || !("payment_url" in result)) {
        setError("message" in result && result.message ? result.message : "Checkout could not be completed.");
        return;
      }
      cart.clear();
      const paymentUrl = new URL(result.payment_url);
      paymentUrl.searchParams.set("token", result.order_access_token);
      onPaymentReady(paymentUrl.toString());
    } catch {
      setError("We could not reach checkout. Please check your connection and try again.");
    } finally {
      setPending(false);
    }
  }

  if (!cart.isReady) return <p className="text-[var(--muted)]">Loading your bag…</p>;
  if (!cart.items.length) return <div className="rounded-3xl border border-dashed border-[var(--line)] p-8 text-center"><p>Your bag is empty.</p><Link className="mt-4 inline-block text-[var(--wine)] underline" href="/#shop">Return to the shop</Link></div>;

  return (
    <form className="grid gap-10 md:grid-cols-[1fr_21rem] md:items-start" onSubmit={submit}>
      <div className="grid gap-8">
        <fieldset className="checkout-card"><legend>Contact details</legend><div className="mt-5 grid gap-5 sm:grid-cols-2"><label>Full name<input className="checkout-input mt-2" name="fullName" required /></label><label>Phone number<input className="checkout-input mt-2" name="phone" pattern="(?:\+234|0)[789][0-9]{9}" placeholder="0801 234 5678" required /></label><label className="sm:col-span-2">Email <span className="text-[var(--muted)]">(optional)</span><input className="checkout-input mt-2" name="email" type="email" /></label></div></fieldset>
        <fieldset className="checkout-card"><legend>Delivery in Lagos</legend><div className="mt-5 grid gap-5"><label>Delivery area<select className="checkout-input mt-2" name="area" onChange={(event) => setAreaId(event.target.value)} required value={areaId}><option disabled value="">Choose an area</option>{areas.map((deliveryArea) => <option key={deliveryArea.id} value={deliveryArea.id}>{deliveryArea.name} · {formatNaira(deliveryArea.fee_minor)}</option>)}</select></label><label>Full delivery address<textarea className="checkout-input mt-2 min-h-28" maxLength={500} name="address" required /></label><label>Directions or landmark <span className="text-[var(--muted)]">(optional)</span><textarea className="checkout-input mt-2 min-h-24" maxLength={500} name="directions" /></label></div></fieldset>
      </div>
      <aside className="checkout-card md:sticky md:top-6"><h2 className="text-xl font-semibold">Order summary</h2><div className="mt-5 grid gap-4">{cart.items.map((item) => <div className="flex justify-between gap-4 text-sm" key={item.variantId}><div><p className="font-medium">{item.productName} × {item.quantity}</p><p className="text-[var(--muted)]">{item.variantName}</p></div><span>{formatNaira(item.priceMinor * item.quantity)}</span></div>)}</div><div className="mt-6 border-t border-[var(--line)] pt-5 text-sm"><div className="flex justify-between"><span>Subtotal</span><span>{formatNaira(subtotal)}</span></div><div className="mt-3 flex justify-between"><span>Delivery</span><span>{area ? formatNaira(area.fee_minor) : "—"}</span></div><div className="mt-5 flex justify-between text-lg font-semibold"><span>Estimated total</span><span>{formatNaira(subtotal + (area?.fee_minor ?? 0))}</span></div></div><p className="mt-5 text-xs leading-5 text-[var(--muted)]">Prices and availability are checked securely when you place the order.</p><button className="mt-6 w-full rounded-full bg-[var(--ink)] px-6 py-4 font-semibold text-white disabled:cursor-wait disabled:opacity-50" disabled={pending || !areas.length} type="submit">{pending ? "Creating your order…" : "Place order & pay"}</button><p aria-live="polite" className="mt-4 text-sm text-[var(--wine)]" role="alert">{error}</p></aside>
    </form>
  );
}
