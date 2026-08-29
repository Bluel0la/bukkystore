export type Category = { id: string; name: string; slug: string; parent_id: string | null };

export type ProductImage = { url: string; alt_text: string; width: number; height: number };

export type ProductVariant = {
  id: string;
  sku: string;
  colour: string | null;
  size: string | null;
  display_name: string;
  price_minor: number;
  currency: "NGN";
  available: boolean;
  low_stock: boolean;
};

export type ProductCardData = {
  id: string;
  name: string;
  slug: string;
  category: Category;
  price_minor: number;
  compare_at_price_minor: number | null;
  currency: "NGN";
  featured: boolean;
  available: boolean;
  primary_image: ProductImage | null;
  colours: string[];
  sizes: string[];
};

export type ProductDetail = ProductCardData & {
  description: string;
  images: ProductImage[];
  variants: ProductVariant[];
};

export type ProductPage = { items: ProductCardData[]; next_cursor: string | null };

export class CatalogueRequestError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "CatalogueRequestError";
  }
}

function apiUrl(path: string): string {
  const baseUrl = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(apiUrl(path), {
    cache: "no-store",
    headers: { accept: "application/json" },
  });
  if (!response.ok) {
    throw new CatalogueRequestError("The catalogue request failed.", response.status);
  }
  return (await response.json()) as T;
}

export function getCategories(): Promise<Category[]> {
  return request<Category[]>("/api/v1/categories");
}

export function getProducts(query = ""): Promise<ProductPage> {
  return request<ProductPage>(`/api/v1/products${query ? `?${query}` : ""}`);
}

export function getProduct(slug: string): Promise<ProductDetail> {
  return request<ProductDetail>(`/api/v1/products/${encodeURIComponent(slug)}`);
}

export function formatNaira(priceMinor: number): string {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 0,
  }).format(priceMinor / 100);
}
