import { beforeEach, describe, expect, it } from "vitest";

import {
  attributionFromSearch,
  captureAttribution,
  loadAttribution,
  productShareUrl,
  saveAttribution,
} from "@/lib/attribution";

describe("attribution", () => {
  beforeEach(() => window.localStorage.clear());

  it("reads ref and campaign from the query string", () => {
    expect(attributionFromSearch("?ref=tiktok&campaign=video1")).toEqual({
      source: "tiktok",
      campaign: "video1",
    });
    expect(attributionFromSearch("?ref=Instagram")).toEqual({
      source: "instagram",
      campaign: null,
    });
    expect(attributionFromSearch("?utm_source=whatsapp&utm_campaign=bc")).toEqual({
      source: "whatsapp",
      campaign: "bc",
    });
    expect(attributionFromSearch("?ref=unknown-channel")).toEqual({
      source: "direct",
      campaign: null,
    });
    expect(attributionFromSearch("")).toBeNull();
  });

  it("persists tagged visits and falls back to direct", () => {
    expect(loadAttribution()).toEqual({ source: "direct", campaign: null });
    saveAttribution({ source: "tiktok", campaign: "video1" });
    expect(loadAttribution()).toEqual({ source: "tiktok", campaign: "video1" });
  });

  it("captures tagged links over stored attribution", () => {
    saveAttribution({ source: "instagram", campaign: null });
    window.history.replaceState(null, "", "/products/dress?ref=tiktok&campaign=launch");
    expect(captureAttribution()).toEqual({ source: "tiktok", campaign: "launch" });
    window.history.replaceState(null, "", "/products/dress");
    expect(captureAttribution()).toEqual({ source: "tiktok", campaign: "launch" });
  });

  it("builds channel-tagged product URLs", () => {
    process.env.NEXT_PUBLIC_SITE_URL = "https://shop.test";
    expect(productShareUrl("brown-dress", "tiktok")).toBe(
      "https://shop.test/products/brown-dress?ref=tiktok",
    );
    delete process.env.NEXT_PUBLIC_SITE_URL;
  });
});
