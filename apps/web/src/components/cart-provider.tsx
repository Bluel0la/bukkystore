"use client";

import { createContext, use, useEffect, useMemo, useState, type ReactNode } from "react";

import type { CartItem } from "@/lib/commerce-types";

const STORAGE_KEY = "bukky-store-cart-v1";

type CartContextValue = {
  items: CartItem[];
  itemCount: number;
  isReady: boolean;
  addItem: (item: CartItem) => void;
  replaceWith: (item: CartItem) => void;
  updateQuantity: (variantId: string, quantity: number) => void;
  removeItem: (variantId: string) => void;
  clear: () => void;
};

const CartContext = createContext<CartContextValue | null>(null);

function readCart(): CartItem[] {
  try {
    const value: unknown = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "[]");
    if (!Array.isArray(value)) return [];
    return value.filter((item): item is CartItem => {
      if (!item || typeof item !== "object") return false;
      const candidate = item as Record<string, unknown>;
      return (
        typeof candidate.variantId === "string" &&
        typeof candidate.productName === "string" &&
        typeof candidate.productSlug === "string" &&
        typeof candidate.variantName === "string" &&
        typeof candidate.priceMinor === "number" &&
        Number.isSafeInteger(candidate.priceMinor) &&
        typeof candidate.quantity === "number" &&
        Number.isInteger(candidate.quantity) &&
        candidate.quantity >= 1 &&
        candidate.quantity <= 20
      );
    });
  } catch {
    return [];
  }
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setItems(readCart());
      setHydrated(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (hydrated) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  }, [hydrated, items]);

  const value = useMemo<CartContextValue>(
    () => ({
      items,
      itemCount: items.reduce((count, item) => count + item.quantity, 0),
      isReady: hydrated,
      addItem(item) {
        setItems((current) => {
          const existing = current.find((entry) => entry.variantId === item.variantId);
          if (!existing) return [...current, item];
          return current.map((entry) =>
            entry.variantId === item.variantId
              ? { ...entry, quantity: Math.min(20, entry.quantity + item.quantity) }
              : entry,
          );
        });
      },
      replaceWith(item) {
        setItems([item]);
      },
      updateQuantity(variantId, quantity) {
        if (!Number.isInteger(quantity) || quantity < 1 || quantity > 20) return;
        setItems((current) =>
          current.map((item) => (item.variantId === variantId ? { ...item, quantity } : item)),
        );
      },
      removeItem(variantId) {
        setItems((current) => current.filter((item) => item.variantId !== variantId));
      },
      clear() {
        setItems([]);
      },
    }),
    [hydrated, items],
  );

  return <CartContext value={value}>{children}</CartContext>;
}

export function useCart(): CartContextValue {
  const cart = use(CartContext);
  if (!cart) throw new Error("useCart must be used within CartProvider");
  return cart;
}
