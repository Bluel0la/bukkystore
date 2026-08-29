import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

import { CartProvider } from "@/components/cart-provider";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "Bukky Store", template: "%s · Bukky Store" },
  description: "Clothing, shoes, bags, and accessories selected in Lagos.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body><CartProvider>{children}</CartProvider></body>
    </html>
  );
}
