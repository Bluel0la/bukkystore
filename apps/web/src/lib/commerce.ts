import type { DeliveryArea } from "@/lib/commerce-types";

function apiUrl(path: string): string {
  const baseUrl = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

export async function getDeliveryAreas(): Promise<DeliveryArea[]> {
  const response = await fetch(apiUrl("/api/v1/delivery-areas"), {
    cache: "no-store",
    headers: { accept: "application/json" },
  });
  if (!response.ok) return [];
  return (await response.json()) as DeliveryArea[];
}
