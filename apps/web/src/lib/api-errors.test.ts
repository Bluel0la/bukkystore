import { describe, expect, it } from "vitest";

import { apiErrorDetails, formatApiError } from "@/lib/api-errors";

const FALLBACK = "The product could not be saved.";

describe("api-errors", () => {
  it("formats the reported compare-at violation the way the aunt sees it", () => {
    const body = {
      code: "validation_failed",
      message: "The request could not be validated.",
      details: [
        {
          location: ["body", "compare_at_price_minor"],
          message: "Value error, compare_at_price_minor must exceed base_price_minor",
          type: "value_error",
        },
      ],
    };

    expect(formatApiError(body, FALLBACK)).toBe(
      "Compare-at price must be higher than the selling price.",
    );
  });

  it("names nested option fields with human-readable indexes", () => {
    expect(
      apiErrorDetails({
        details: [{ location: ["body", "variants", 0, "sku"], message: "Already used." }],
      }),
    ).toEqual(["Variants #1 · SKU: Already used."]);
  });

  it("caps long detail lists and skips empty entries", () => {
    const details = [
      { location: ["body", "name"], message: "Too short." },
      { location: ["body", "slug"], message: "Taken." },
      { location: ["body", "price"], message: "Negative." },
      { location: ["body", "extra"], message: "One more." },
      { location: ["body", "blank"], message: "   " },
      { message: "No location." },
    ];

    expect(apiErrorDetails({ details })).toEqual([
      "Name: Too short.",
      "Slug: Taken.",
      "Price: Negative.",
    ]);
  });

  it("falls back through message to the safe default", () => {
    expect(formatApiError({ code: "conflict", message: "Slug already used." }, FALLBACK)).toBe(
      "Slug already used.",
    );
    expect(formatApiError({ code: "internal_error" }, FALLBACK)).toBe(FALLBACK);
    expect(formatApiError(null, FALLBACK)).toBe(FALLBACK);
    expect(formatApiError("boom", FALLBACK)).toBe(FALLBACK);
  });

  it("drops framework roots and handles fieldless details", () => {
    expect(apiErrorDetails({ details: [{ message: "Bad JSON." }] })).toEqual(["Bad JSON."]);
    expect(apiErrorDetails({ details: [{ location: ["body"], message: "Bad body." }] })).toEqual([
      "Bad body.",
    ]);
  });
});
