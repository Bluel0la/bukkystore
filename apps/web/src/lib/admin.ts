import { cookies } from "next/headers";

import type { AdminAnalyticsOverview, AdminDeliveryArea, AdminOrder, AdminOrderPage, AdminProduct, AdminProductPage, AdminStoreSettings, AdminUser, ProductEngagement } from "@/lib/admin-types";
import type { Category } from "@/lib/catalogue";

function internalUrl(path: string): string {
  const baseUrl = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";
  return `${baseUrl.replace(/\/$/, "")}/api/v1/admin${path}`;
}

export async function adminRequest<T>(path: string): Promise<T | null> {
  const cookieStore = await cookies();
  try {
    const response = await fetch(internalUrl(path), {
      cache: "no-store",
      headers: {
        accept: "application/json",
        cookie: cookieStore.toString(),
      },
    });
    if (response.status === 401 || response.status === 403) return null;
    if (!response.ok) {
      console.warn(`[admin] ${path} responded ${response.status}`);
      return null;
    }
    return (await response.json()) as T;
  } catch (error) {
    console.warn(`[admin] ${path} fetch failed:`, error instanceof Error ? error.message : error);
    return null;
  }
}

export function getAdminUser(): Promise<AdminUser | null> {
  return adminRequest<AdminUser>("/auth/me");
}

export function getAdminProducts(): Promise<AdminProductPage | null> {
  return adminRequest<AdminProductPage>("/products?limit=100");
}

export function getAdminProduct(productId: string): Promise<AdminProduct | null> {
  return adminRequest<AdminProduct>(`/products/${encodeURIComponent(productId)}`);
}

export function getAdminCategories(): Promise<Category[] | null> {
  return adminRequest<Category[]>("/categories");
}

export function getAdminOrders(): Promise<AdminOrderPage | null> {
  return adminRequest<AdminOrderPage>("/orders?limit=100");
}

export function getAdminOrder(orderId: string): Promise<AdminOrder | null> {
  return adminRequest<AdminOrder>(`/orders/${encodeURIComponent(orderId)}`);
}

export function getAdminAnalytics(days = 30): Promise<AdminAnalyticsOverview | null> {
  return adminRequest<AdminAnalyticsOverview>(`/analytics/overview?days=${days}`);
}

export function getAdminStoreSettings(): Promise<AdminStoreSettings | null> {
  return adminRequest<AdminStoreSettings>("/store-settings");
}

export function getAdminDeliveryAreas(): Promise<AdminDeliveryArea[] | null> {
  return adminRequest<AdminDeliveryArea[]>("/delivery-areas");
}

export function getProductEngagement(productId: string, days = 30): Promise<ProductEngagement | null> {
  return adminRequest<ProductEngagement>(
    `/analytics/products/${encodeURIComponent(productId)}?days=${days}`,
  );
}
