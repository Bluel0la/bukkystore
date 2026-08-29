import type { Category } from "@/lib/catalogue";

export type AdminUser = { id: string; email: string; display_name: string; role: "OWNER" | "ADMIN" };
export type AdminVariant = {
  id: string; sku: string; colour: string | null; size: string | null; display_name: string;
  price_override_minor: number | null; stock_on_hand: number; reserved_quantity: number;
  available_quantity: number; low_stock_threshold: number; status: "ACTIVE" | "ARCHIVED";
};
export type AdminProduct = {
  id: string; category: Category; name: string; slug: string; description: string;
  base_price_minor: number; compare_at_price_minor: number | null; currency: string;
  status: "DRAFT" | "ACTIVE" | "ARCHIVED"; featured: boolean; variants: AdminVariant[];
  created_at: string; updated_at: string;
};
export type AdminProductPage = { items: AdminProduct[]; next_cursor: string | null };
