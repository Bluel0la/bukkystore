import type { BusinessHours } from "@/lib/admin-types";

export type PublicStoreSettings = {
  store_name: string;
  logo_ref: string | null;
  whatsapp_number: string;
  phone_number: string;
  instagram_url: string | null;
  tiktok_url: string | null;
  address: string;
  city: string;
  currency: string;
  minimum_order_minor: number | null;
  business_hours: BusinessHours;
};

const closedDay = { closed: true, open: null, close: null };
const openDay = { closed: false, open: "09:00", close: "18:00" };

export const fallbackStoreSettings: PublicStoreSettings = {
  store_name: "Atiten Kids Store",
  logo_ref: null,
  whatsapp_number: "+2348121531909",
  phone_number: "+2348121531909",
  instagram_url: null,
  tiktok_url: "https://www.tiktok.com/@bookie_kiddiestore",
  address: "Emily Bus-stop by Dikram Filling Station",
  city: "Lagos",
  currency: "NGN",
  minimum_order_minor: null,
  business_hours: {
    monday: { ...openDay },
    tuesday: { ...openDay },
    wednesday: { ...openDay },
    thursday: { ...openDay },
    friday: { ...openDay },
    saturday: { ...openDay },
    sunday: { ...closedDay },
  },
};

function apiUrl(path: string): string {
  const baseUrl = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

export async function getPublicStoreSettings(): Promise<PublicStoreSettings> {
  try {
    const response = await fetch(apiUrl("/api/v1/store-settings"), {
      next: { revalidate: 300 },
      headers: { accept: "application/json" },
    });
    if (!response.ok) return fallbackStoreSettings;
    return (await response.json()) as PublicStoreSettings;
  } catch {
    return fallbackStoreSettings;
  }
}

export function whatsappLink(phone: string, message: string): string {
  const digits = phone.replace(/\D/g, "");
  const international = digits.startsWith("0") ? `234${digits.slice(1)}` : digits;
  return `https://wa.me/${international}?text=${encodeURIComponent(message)}`;
}
