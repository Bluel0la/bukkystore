import type { Metadata } from "next";
import { Nunito } from "next/font/google";
import type { ReactNode } from "react";

import "./globals.css";

import { CartProvider } from "@/components/cart-provider";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

const bodyFont = Nunito({ subsets: ["latin"], display: "swap", variable: "--font-body" });

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "Atiten Kids Store", template: "%s · Atiten Kids Store" },
  description: "Kids clothing, shoes, and accessories selected in Lagos.",
  icons: { icon: "/favicon.ico", apple: "/atiten-logo-icon.png" },
  openGraph: {
    siteName: "Atiten Kids Store",
    images: [{ url: "/atiten-logo.jpg", width: 1408, height: 768, alt: "Atiten Kids Store" }],
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" className={bodyFont.variable}>
      <body><CartProvider>{children}</CartProvider></body>
    </html>
  );
}
