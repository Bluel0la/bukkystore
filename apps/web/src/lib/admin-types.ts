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

export type AdminOrderSummary = {
  id: string; order_number: string; customer_full_name: string; customer_phone: string;
  total_minor: number; currency: "NGN"; status: string; payment_status: string; created_at: string;
};
export type AdminOrder = AdminOrderSummary & {
  customer_email: string | null; delivery_area_name: string; delivery_address: string;
  delivery_directions: string | null; subtotal_minor: number; delivery_fee_minor: number;
  items: Array<{ id: string; product_name: string; variant_name: string; sku: string;
    unit_price_minor: number; quantity: number; line_subtotal_minor: number }>;
};
export type AdminOrderPage = { items: AdminOrderSummary[] };
