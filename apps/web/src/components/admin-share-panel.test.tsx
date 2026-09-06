import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AdminSharePanel } from "@/components/admin-share-panel";

const engagement = {
  product_id: "product-id",
  product_name: "Brown Linen Dress",
  range_days: 30,
  period_start: "2026-08-01T00:00:00Z",
  views: 42,
  shares: 7,
  whatsapp_clicks: 5,
};

describe("AdminSharePanel", () => {
  it("renders tagged links with engagement and copies them", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    process.env.NEXT_PUBLIC_SITE_URL = "https://shop.test";
    render(<AdminSharePanel engagement={engagement} productSlug="brown-linen-dress" />);

    expect(screen.getByText(/42 views · 7 shares · 5 WhatsApp chats/)).toBeDefined();
    fireEvent.click(screen.getAllByRole("button", { name: "Copy link" })[0]);
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(
      "https://shop.test/products/brown-linen-dress?ref=tiktok",
    ));
    await screen.findByText("Copied!");
    delete process.env.NEXT_PUBLIC_SITE_URL;
  });

  it("renders without engagement data", () => {
    render(<AdminSharePanel engagement={null} productSlug="brown-linen-dress" />);
    expect(screen.getByText("TikTok")).toBeDefined();
  });
});
