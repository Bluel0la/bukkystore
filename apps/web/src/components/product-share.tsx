"use client";

import { useEffect, useRef, useState } from "react";

import { trackEvent } from "@/lib/analytics";
import { captureAttribution, productShareUrl, type AttributionSource } from "@/lib/attribution";
import { formatNaira } from "@/lib/catalogue";
import { whatsappLink } from "@/lib/store-settings";

export function ProductShare({
  productId,
  productName,
  productSlug,
  priceMinor,
  whatsappNumber,
}: {
  productId: string;
  productName: string;
  productSlug: string;
  priceMinor: number;
  whatsappNumber: string;
}) {
  const [copied, setCopied] = useState("");
  const viewed = useRef(false);

  useEffect(() => {
    captureAttribution();
    if (!viewed.current) {
      viewed.current = true;
      trackEvent("product_view", { productId });
    }
  }, [productId]);

  const pageUrl = typeof window === "undefined" ? "" : window.location.href.split("?")[0];
  const canonicalUrl = pageUrl || productShareUrl(productSlug, "direct");
  const enquiryMessage =
    `Hello, I'm interested in the ${productName}.\n\nPrice: ${formatNaira(priceMinor)}\n\nProduct:\n${canonicalUrl}`;

  async function copyTaggedLink(ref: AttributionSource) {
    try {
      await navigator.clipboard.writeText(productShareUrl(productSlug, ref));
      setCopied(ref);
      trackEvent("share_click", { productId, channel: `copy-${ref}` });
    } catch {
      setCopied("");
    }
  }

  async function nativeShare() {
    trackEvent("share_click", { productId, channel: "native" });
    if (!navigator.share) {
      await copyTaggedLink("direct");
      return;
    }
    try {
      await navigator.share({
        title: productName,
        text: `${productName} — ${formatNaira(priceMinor)}`,
        url: canonicalUrl,
      });
    } catch {
      // Dismissed share sheets are not errors.
    }
  }

  const whatsappShareUrl = `https://wa.me/?text=${encodeURIComponent(
    `${productName} — ${formatNaira(priceMinor)} ${productShareUrl(productSlug, "whatsapp")}`,
  )}`;

  return (
    <div className="mt-10 rounded-3xl border border-[var(--line)] p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold">Share this piece</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">Send it to a friend or ask about it first.</p>
        </div>
        <button className="rounded-full border border-[var(--line)] bg-white px-4 py-2 text-sm" onClick={nativeShare} type="button">Share</button>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        <a
          className="rounded-full border border-[var(--line)] bg-white px-4 py-2 text-center text-sm transition hover:border-[var(--wine)]"
          href={whatsappShareUrl}
          onClick={() => trackEvent("share_click", { productId, channel: "whatsapp" })}
          rel="noreferrer"
          target="_blank"
        >
          WhatsApp
        </a>
        <button
          className="rounded-full border border-[var(--line)] bg-white px-4 py-2 text-sm transition hover:border-[var(--wine)]"
          onClick={() => copyTaggedLink("tiktok")}
          type="button"
        >
          {copied === "tiktok" ? "TikTok link copied!" : "TikTok"}
        </button>
        <button
          className="rounded-full border border-[var(--line)] bg-white px-4 py-2 text-sm transition hover:border-[var(--wine)]"
          onClick={() => copyTaggedLink("instagram")}
          type="button"
        >
          {copied === "instagram" ? "Instagram link copied!" : "Instagram"}
        </button>
      </div>
      {copied === "direct" && <p className="mt-2 text-sm text-[#1f7a46]">Link copied!</p>}
      <a
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-full bg-[#1f7a46] px-6 py-4 font-semibold text-white"
        href={whatsappLink(whatsappNumber, enquiryMessage)}
        onClick={() => trackEvent("whatsapp_click", { productId, channel: "enquiry" })}
        rel="noreferrer"
        target="_blank"
      >
        Ask on WhatsApp
      </a>
    </div>
  );
}
