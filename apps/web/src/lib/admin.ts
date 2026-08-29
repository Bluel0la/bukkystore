import { cookies } from "next/headers";

import type { AdminProduct, AdminProductPage, AdminUser } from "@/lib/admin-types";
import type { Category } from "@/lib/catalogue";

function internalUrl(path: string): string {
  const baseUrl = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";
  return `${baseUrl.replace(/\/$/, "")}/api/v1/admin${path}`;
}

export async function adminRequest<T>(path: string): Promise<T | null> {
  const cookieStore = await cookies();
  const response = await fetch(internalUrl(path), {
    cache: "no-store",
    headers: {
      accept: "application/json",
      cookie: cookieStore.toString(),
    },
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error("Admin service unavailable");
  return (await response.json()) as T;
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
