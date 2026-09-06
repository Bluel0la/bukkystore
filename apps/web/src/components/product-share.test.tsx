import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/analytics", () => ({ trackEvent: vi.fn() }));

import { trackEvent } from "@/lib/analytics";
import { ProductShare } from "@/components/product-share";

const props = {
  productId: "product-id",
  productName: "Brown Linen Dress",
  productSlug: "brown-linen-dress",
  priceMinor: 1_850_000,
  whatsappNumber: "+2348121531909",
};

describe("ProductShare", () => {
  beforeEach(() => {
    vi.mocked(trackEvent).mockReset();
    window.localStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  it("tracks the product view once and opens a prefilled WhatsApp enquiry", async () => {
    render(<ProductShare {...props} />);

    await waitFor(() =>
      expect(trackEvent).toHaveBeenCalledWith("product_view", { productId: "product-id" }),
    );
    const enquiry = screen.getByRole("link", { name: "Ask on WhatsApp" });
    expect(enquiry.getAttribute("href")).toContain("https://wa.me/2348121531909?text=");
    expect(decodeURIComponent(enquiry.getAttribute("href") ?? "")).toContain("Brown Linen Dress");
    expect(decodeURIComponent(enquiry.getAttribute("href") ?? "")).toContain("₦18,500");

    fireEvent.click(enquiry);
    expect(trackEvent).toHaveBeenCalledWith(
      "whatsapp_click",
      { productId: "product-id", channel: "enquiry" },
    );
  });

  it("copies tagged channel links and fires share events", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    process.env.NEXT_PUBLIC_SITE_URL = "https://shop.test";
    render(<ProductShare {...props} />);

    fireEvent.click(screen.getByRole("button", { name: "TikTok" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(
      "https://shop.test/products/brown-linen-dress?ref=tiktok",
    ));
    expect(trackEvent).toHaveBeenCalledWith(
      "share_click",
      { productId: "product-id", channel: "copy-tiktok" },
    );
    delete process.env.NEXT_PUBLIC_SITE_URL;
  });

  it("uses native share when available", async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { share });
    render(<ProductShare {...props} />);

    fireEvent.click(screen.getByRole("button", { name: "Share" }));
    await waitFor(() => expect(share).toHaveBeenCalled());
    expect(trackEvent).toHaveBeenCalledWith(
      "share_click",
      { productId: "product-id", channel: "native" },
    );
  });
});
