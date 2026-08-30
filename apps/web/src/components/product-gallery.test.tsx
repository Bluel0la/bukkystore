import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProductGallery } from "@/components/product-gallery";

describe("ProductGallery", () => {
  it("shows a placeholder when no photos exist", () => {
    render(<ProductGallery images={[]} />);
    expect(screen.getByText("Photo coming soon")).toBeInTheDocument();
  });

  it("lets a customer select another product photo", () => {
    render(<ProductGallery images={[
      { url: "https://res.cloudinary.com/bukky/image/upload/v1/front.jpg", alt_text: "Front view", width: 1000, height: 1250 },
      { url: "https://res.cloudinary.com/bukky/image/upload/v1/back.jpg", alt_text: "Back view", width: 1000, height: 1250 },
    ]} />);
    expect(screen.getByAltText("Front view")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show photo 2" }));
    expect(screen.getByAltText("Back view")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Show photo 2" })).toHaveAttribute("aria-pressed", "true");
  });
});
