"use client";

import { useState } from "react";

import { productShareUrl, type AttributionSource } from "@/lib/attribution";
import type { ProductEngagement } from "@/lib/admin-types";

const channels: Array<{ ref: AttributionSource; label: string; hint: string }> = [
  { ref: "tiktok", label: "TikTok", hint: "Paste into your video caption or bio link" },
  { ref: "instagram", label: "Instagram", hint: "Paste into stories, bio, or DMs" },
  { ref: "whatsapp", label: "WhatsApp", hint: "Send straight to broadcast lists" },
];

export function AdminSharePanel({
  productSlug,
  engagement,
}: {
  productSlug: string;
  engagement: ProductEngagement | null;
}) {
  const [copied, setCopied] = useState("");

  async function copy(text: string, key: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
    } catch {
      setCopied("");
    }
  }

  return (
    <section className="checkout-card" aria-labelledby="share-heading">
      <h2 className="text-lg font-semibold" id="share-heading">Share this product</h2>
      <p className="mt-1 text-sm text-[var(--muted)]">Tagged links tell you which channel brings buyers.</p>
      {engagement && (
        <p className="mt-3 text-sm text-[var(--muted)]">
          Last {engagement.range_days} days: {engagement.views} views · {engagement.shares} shares · {engagement.whatsapp_clicks} WhatsApp chats
        </p>
      )}
      <div className="mt-4 grid gap-3">
        {channels.map(({ ref, label, hint }) => {
          const url = productShareUrl(productSlug, ref);
          return (
            <div className="rounded-2xl border border-[var(--line)] p-3" key={ref}>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium">{label}</p>
                  <p className="mt-1 text-xs text-[var(--muted)]">{hint}</p>
                </div>
                <button
                  className="shrink-0 rounded-full border border-[var(--line)] px-4 py-2 text-sm"
                  onClick={() => copy(url, ref)}
                  type="button"
                >
                  {copied === ref ? "Copied!" : "Copy link"}
                </button>
              </div>
              <p className="mt-2 truncate text-xs text-[var(--muted)]">{url}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
