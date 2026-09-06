"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { readCsrfCookie } from "@/lib/admin-client";
import type { AdminStoreSettings, BusinessHours, DaySchedule } from "@/lib/admin-types";

const days: Array<{ key: keyof BusinessHours; label: string }> = [
  { key: "monday", label: "Monday" },
  { key: "tuesday", label: "Tuesday" },
  { key: "wednesday", label: "Wednesday" },
  { key: "thursday", label: "Thursday" },
  { key: "friday", label: "Friday" },
  { key: "saturday", label: "Saturday" },
  { key: "sunday", label: "Sunday" },
];

export function AdminSettingsForm({ initial }: { initial: AdminStoreSettings }) {
  const router = useRouter();
  const [storeName, setStoreName] = useState(initial.store_name);
  const [logoRef, setLogoRef] = useState(initial.logo_ref ?? "");
  const [whatsappNumber, setWhatsappNumber] = useState(initial.whatsapp_number);
  const [phoneNumber, setPhoneNumber] = useState(initial.phone_number);
  const [instagramUrl, setInstagramUrl] = useState(initial.instagram_url ?? "");
  const [tiktokUrl, setTiktokUrl] = useState(initial.tiktok_url ?? "");
  const [address, setAddress] = useState(initial.address);
  const [city, setCity] = useState(initial.city);
  const [minimumOrder, setMinimumOrder] = useState(
    initial.minimum_order_minor == null ? "" : String(initial.minimum_order_minor / 100),
  );
  const [hours, setHours] = useState<BusinessHours>(initial.business_hours);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  function setDay(key: keyof BusinessHours, patch: Partial<DaySchedule>) {
    setHours((current) => ({ ...current, [key]: { ...current[key], ...patch } }));
  }

  async function save() {
    const csrf = readCsrfCookie();
    if (!csrf) {
      setError("Your admin session security token is missing. Please sign in again.");
      return;
    }
    const minimum = minimumOrder.trim();
    const minimumMinor = minimum === "" ? null : Math.round(Number(minimum) * 100);
    if (minimum !== "" && (!Number.isFinite(minimumMinor) || (minimumMinor ?? 0) < 0)) {
      setError("Minimum order must be a positive amount in naira, or left empty.");
      return;
    }
    setPending(true);
    setError("");
    setSaved(false);
    try {
      const response = await fetch("/api/admin/store-settings", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": `settings:${crypto.randomUUID()}`,
          "X-CSRF-Token": csrf,
        },
        body: JSON.stringify({
          store_name: storeName.trim(),
          logo_ref: logoRef.trim() || null,
          whatsapp_number: whatsappNumber.trim(),
          phone_number: phoneNumber.trim(),
          instagram_url: instagramUrl.trim() || null,
          tiktok_url: tiktokUrl.trim() || null,
          address: address.trim(),
          city: city.trim() || "Lagos",
          currency: "NGN",
          minimum_order_minor: minimumMinor,
          business_hours: hours,
        }),
      });
      if (!response.ok) {
        const result = (await response.json()) as { message?: string };
        setError(result.message ?? "The settings could not be saved.");
        return;
      }
      setSaved(true);
      router.refresh();
    } catch {
      setError("The settings service is unavailable. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="grid gap-5">
      <section className="checkout-card" aria-labelledby="identity-heading">
        <h2 className="text-lg font-semibold" id="identity-heading">Store identity</h2>
        <label className="mt-4 block text-sm">Store name<input className="admin-input mt-2" maxLength={120} onChange={(event) => setStoreName(event.target.value)} required value={storeName} /></label>
        <label className="mt-4 block text-sm">Logo reference <span className="text-[var(--muted)]">(optional, until the new logo is ready)</span><input className="admin-input mt-2" maxLength={500} onChange={(event) => setLogoRef(event.target.value)} placeholder="Uploads later — leave empty for now" value={logoRef} /></label>
      </section>

      <section className="checkout-card" aria-labelledby="contact-heading">
        <h2 className="text-lg font-semibold" id="contact-heading">Contact and socials</h2>
        <label className="mt-4 block text-sm">WhatsApp number<input className="admin-input mt-2" inputMode="tel" onChange={(event) => setWhatsappNumber(event.target.value)} required value={whatsappNumber} /></label>
        <label className="mt-4 block text-sm">Phone number<input className="admin-input mt-2" inputMode="tel" onChange={(event) => setPhoneNumber(event.target.value)} required value={phoneNumber} /></label>
        <label className="mt-4 block text-sm">Shop address<textarea className="admin-input mt-2 min-h-20" maxLength={500} onChange={(event) => setAddress(event.target.value)} required value={address} /></label>
        <label className="mt-4 block text-sm">City<input className="admin-input mt-2" maxLength={120} onChange={(event) => setCity(event.target.value)} value={city} /></label>
        <label className="mt-4 block text-sm">Instagram URL <span className="text-[var(--muted)]">(optional)</span><input className="admin-input mt-2" inputMode="url" onChange={(event) => setInstagramUrl(event.target.value)} placeholder="https://instagram.com/…" value={instagramUrl} /></label>
        <label className="mt-4 block text-sm">TikTok URL <span className="text-[var(--muted)]">(optional)</span><input className="admin-input mt-2" inputMode="url" onChange={(event) => setTiktokUrl(event.target.value)} placeholder="https://tiktok.com/@…" value={tiktokUrl} /></label>
        <label className="mt-4 block text-sm">Minimum order (₦) <span className="text-[var(--muted)]">(optional, empty means none)</span><input className="admin-input mt-2" inputMode="decimal" onChange={(event) => setMinimumOrder(event.target.value)} placeholder="No minimum" value={minimumOrder} /></label>
      </section>

      <section className="checkout-card" aria-labelledby="hours-heading">
        <h2 className="text-lg font-semibold" id="hours-heading">Business hours</h2>
        <div className="mt-4 grid gap-3">
          {days.map(({ key, label }) => (
            <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-[var(--line)] p-3" key={key}>
              <span className="w-24 text-sm font-medium">{label}</span>
              <label className="flex items-center gap-2 text-sm"><input checked={hours[key].closed} onChange={(event) => setDay(key, { closed: event.target.checked })} type="checkbox" />Closed</label>
              {!hours[key].closed && (
                <>
                  <label className="flex items-center gap-2 text-sm">Opens<input aria-label={`${label} opening time`} className="admin-input w-28" onChange={(event) => setDay(key, { open: event.target.value })} type="time" value={hours[key].open ?? ""} /></label>
                  <label className="flex items-center gap-2 text-sm">Closes<input aria-label={`${label} closing time`} className="admin-input w-28" onChange={(event) => setDay(key, { close: event.target.value })} type="time" value={hours[key].close ?? ""} /></label>
                </>
              )}
            </div>
          ))}
        </div>
      </section>

      <div>
        <button className="admin-primary w-full" disabled={pending} onClick={save} type="button">{pending ? "Saving…" : "Save settings"}</button>
        <p aria-live="polite" className="mt-3 text-sm text-[var(--wine)]">{error}</p>
        {saved && !error && <p aria-live="polite" className="mt-3 text-sm text-[#1f7a46]">Settings saved.</p>}
      </div>
    </div>
  );
}
