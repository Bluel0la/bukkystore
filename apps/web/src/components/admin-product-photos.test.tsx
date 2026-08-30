import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AdminProductPhotos, uploadPhoto } from "@/components/admin-product-photos";
import type { AdminProductImage } from "@/lib/admin-types";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

const photos: AdminProductImage[] = [
  { id: "photo-1", public_id: "public-1", url: "https://res.cloudinary.com/bukky/image/upload/v1/one.jpg", alt_text: "Front view", width: 1000, height: 1250, position: 0 },
  { id: "photo-2", public_id: "public-2", url: "https://res.cloudinary.com/bukky/image/upload/v1/two.jpg", alt_text: "Back view", width: 1000, height: 1250, position: 1 },
];

class SuccessfulXhr {
  status = 200;
  responseType = "";
  response = { public_id: "public-new", version: 2, signature: "a".repeat(64), width: 1200, height: 1500, bytes: 500, format: "jpg" };
  private listeners = new Map<string, () => void>();
  private progress?: (event: { lengthComputable: boolean; loaded: number; total: number }) => void;
  upload = { addEventListener: (_name: string, listener: typeof this.progress) => { this.progress = listener; } };
  open = vi.fn();
  addEventListener(name: string, listener: () => void) { this.listeners.set(name, listener); }
  send = vi.fn(() => { this.progress?.({ lengthComputable: true, loaded: 1, total: 1 }); this.listeners.get("load")?.(); });
}

describe("AdminProductPhotos", () => {
  beforeEach(() => {
    refresh.mockReset();
    document.cookie = "bukky_admin_csrf=csrf-token; path=/";
    vi.stubGlobal("XMLHttpRequest", SuccessfulXhr);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "bukky_admin_csrf=; Max-Age=0; path=/";
  });

  it("shows the empty state and validates files locally", async () => {
    render(<AdminProductPhotos initialImages={[]} productId="product-id" productName="Brown Dress" />);
    expect(screen.getByText(/No product photos yet/)).toBeInTheDocument();
    const input = screen.getByLabelText("Add photos");
    const invalid = new File([new Uint8Array(20)], "dress.gif", { type: "image/gif" });
    fireEvent.change(input, { target: { files: [invalid] } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Use JPG, PNG, WebP or AVIF");
  });

  it("uploads directly with progress and registers verified metadata", async () => {
    const registered: AdminProductImage = { ...photos[0], id: "photo-new", public_id: "public-new", position: 0 };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({
        upload_url: "https://api.cloudinary.com/upload", api_key: "key", timestamp: 1,
        public_id: "public-new", signature: "signed", max_bytes: 10_000_000,
        allowed_mime_types: ["image/jpeg"],
      }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(registered), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminProductPhotos initialImages={[]} productId="product-id" productName="Brown Dress" />);
    const file = new File([new Uint8Array(20)], "dress.jpg", { type: "image/jpeg" });
    fireEvent.change(screen.getByLabelText("Add photos"), { target: { files: [file] } });

    await screen.findByText("1 photo added.");
    expect(screen.getByText("Cover")).toBeInTheDocument();
    expect(refresh).toHaveBeenCalled();
    expect(fetchMock.mock.calls[0][0]).toContain("/images/signatures");
    const registeredBody = JSON.parse(fetchMock.mock.calls[1][1].body as string);
    expect(registeredBody.alt_text).toBe("Brown Dress product photo");
  });

  it("edits descriptions, reorders photos, and confirms deletion", async () => {
    const updated = { ...photos[0], alt_text: "Brown dress front detail" };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(updated), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([photos[1], updated]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([updated]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("confirm", vi.fn(() => true));
    render(<AdminProductPhotos initialImages={photos} productId="product-id" productName="Brown Dress" />);

    fireEvent.change(screen.getByLabelText("Description for photo 1"), { target: { value: updated.alt_text } });
    fireEvent.blur(screen.getByLabelText("Description for photo 1"));
    await screen.findByText("Photo description saved.");
    fireEvent.click(screen.getAllByRole("button", { name: "Move later" })[0]);
    await screen.findByText("Photo order saved.");
    fireEvent.click(screen.getAllByRole("button", { name: "Remove" })[0]);
    await screen.findByText("Photo removed.");

    expect(fetchMock.mock.calls.map((call) => call[1].method)).toEqual(["PATCH", "PATCH", "DELETE"]);
  });

  it("reports expired sessions and upload-provider failures", async () => {
    document.cookie = "bukky_admin_csrf=; Max-Age=0; path=/";
    render(<AdminProductPhotos initialImages={[]} productId="product-id" productName="Brown Dress" />);
    const file = new File([new Uint8Array(20)], "dress.jpg", { type: "image/jpeg" });
    fireEvent.change(screen.getByLabelText("Add photos"), { target: { files: [file] } });
    expect(await screen.findByRole("alert")).toHaveTextContent("session expired");

    const signed = { upload_url: "/upload", api_key: "key", timestamp: 1, public_id: "photo", signature: "signed", max_bytes: 10, allowed_mime_types: ["image/jpeg"] };
    class FailedXhr extends SuccessfulXhr { override status = 400; }
    vi.stubGlobal("XMLHttpRequest", FailedXhr);
    await expect(uploadPhoto(file, signed, vi.fn())).rejects.toThrow("Cloudinary rejected");
  });

  it("enforces the photo limit and surfaces signature failures", async () => {
    const ninePhotos = Array.from({ length: 9 }, (_, index) => ({
      ...photos[0], id: `photo-${index}`, position: index,
    }));
    const { unmount } = render(<AdminProductPhotos initialImages={ninePhotos} productId="product-id" productName="Brown Dress" />);
    const first = new File([new Uint8Array(20)], "one.jpg", { type: "image/jpeg" });
    const second = new File([new Uint8Array(20)], "two.jpg", { type: "image/jpeg" });
    fireEvent.change(screen.getByLabelText("Add photos"), { target: { files: [first, second] } });
    expect(await screen.findByRole("alert")).toHaveTextContent("up to 10 photos");
    unmount();

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ message: "Cloudinary is not configured." }),
      { status: 503, headers: { "content-type": "application/json" } },
    )));
    render(<AdminProductPhotos initialImages={[]} productId="product-id" productName="Brown Dress" />);
    fireEvent.change(screen.getByLabelText("Add photos"), { target: { files: [first] } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Cloudinary is not configured");
  });

  it("restores photo order after a rejected reorder and can cancel removal", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response("not-json", { status: 409 }))
      .mockResolvedValueOnce(new Response("not-json", { status: 409 }));
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("confirm", vi.fn(() => false));
    render(<AdminProductPhotos initialImages={photos} productId="product-id" productName="Brown Dress" />);

    fireEvent.change(screen.getByLabelText("Description for photo 1"), { target: { value: "Changed description" } });
    fireEvent.blur(screen.getByLabelText("Description for photo 1"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Alternative text could not be saved");
    fireEvent.click(screen.getAllByRole("button", { name: "Move later" })[0]);
    expect(await screen.findByRole("alert")).toHaveTextContent("Photo order could not be saved");
    fireEvent.click(screen.getAllByRole("button", { name: "Remove" })[0]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
