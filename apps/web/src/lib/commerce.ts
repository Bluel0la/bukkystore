import type { DeliveryArea, PaymentStatus } from "@/lib/commerce-types";

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

export async function getPaymentStatus(
  orderNumber: string,
  token: string,
): Promise<PaymentStatus | null> {
  const query = new URLSearchParams({ token });
  const response = await fetch(
    apiUrl(`/api/v1/orders/${encodeURIComponent(orderNumber)}/payment-status?${query}`),
    { cache: "no-store", headers: { accept: "application/json" } },
  );
  if (!response.ok) return null;
  return (await response.json()) as PaymentStatus;
}
