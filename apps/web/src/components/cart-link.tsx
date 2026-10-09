"use client";

import Link from "next/link";

import { useCart } from "@/components/cart-provider";

export function CartLink() {
  const { itemCount } = useCart();
  return <Link href="/cart">Bag{itemCount > 0 ? ` (${itemCount})` : ""}</Link>;
}
