"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { type ChangeEvent, useState } from "react";

import { readCsrfCookie } from "@/lib/admin-client";
import type { AdminProductImage } from "@/lib/admin-types";

type UploadSignature = {
  upload_url: string; api_key: string; timestamp: number; public_id: string; signature: string;
  max_bytes: number; allowed_mime_types: string[];
};
type CloudinaryUpload = {
  public_id: string; version: number; signature: string; width: number; height: number;
  bytes: number; format: "jpg" | "jpeg" | "png" | "webp" | "avif";
};

async function errorMessage(response: Response, fallback: string): Promise<string> {
  const body = await response.json().catch(() => null) as { message?: string } | null;
  return body?.message ?? fallback;
}

export function uploadPhoto(
  file: File,
  signed: UploadSignature,
  onProgress: (percentage: number) => void,
): Promise<CloudinaryUpload> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", signed.upload_url);
    request.responseType = "json";
    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    });
    request.addEventListener("load", () => {
      if (request.status >= 200 && request.status < 300) resolve(request.response as CloudinaryUpload);
      else reject(new Error("Cloudinary rejected the photo upload."));
    });
    request.addEventListener("error", () => reject(new Error("The photo upload was interrupted.")));
    const body = new FormData();
    body.set("file", file);
    body.set("api_key", signed.api_key);
    body.set("timestamp", String(signed.timestamp));
    body.set("signature", signed.signature);
    body.set("public_id", signed.public_id);
    body.set("overwrite", "false");
    request.send(body);
  });
}

export function AdminProductPhotos({
  productId, productName, initialImages,
}: { productId: string; productName: string; initialImages: AdminProductImage[] }) {
  const router = useRouter();
  const [images, setImages] = useState(initialImages);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);

  function csrfToken(): string | null {
    const token = readCsrfCookie();
    if (!token) setError("Your session expired. Please sign in again.");
    return token;
  }

  async function choosePhotos(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (!files.length) return;
    if (images.length + files.length > 10) return setError("Each product can have up to 10 photos.");
    const invalid = files.find((file) => !["image/jpeg", "image/png", "image/webp", "image/avif"].includes(file.type) || file.size > 10_000_000);
    if (invalid) return setError("Use JPG, PNG, WebP or AVIF photos no larger than 10 MB.");
    const csrf = csrfToken();
    if (!csrf) return;
    setPending(true);
    setError("");
    setMessage("");
    try {
      const uploaded: AdminProductImage[] = [];
      for (const file of files) {
        setProgress(0);
        const signatureResponse = await fetch(`/api/admin/products/${productId}/images/signatures`, {
          method: "POST", headers: { "X-CSRF-Token": csrf },
        });
        if (!signatureResponse.ok) throw new Error(await errorMessage(signatureResponse, "The upload could not be prepared."));
        const signed = await signatureResponse.json() as UploadSignature;
        const cloudinary = await uploadPhoto(file, signed, setProgress);
        const registerResponse = await fetch(`/api/admin/products/${productId}/images`, {
          method: "POST",
          headers: { "content-type": "application/json", "X-CSRF-Token": csrf },
          body: JSON.stringify({
            public_id: cloudinary.public_id,
            version: cloudinary.version,
            signature: cloudinary.signature,
            width: cloudinary.width,
            height: cloudinary.height,
            bytes: cloudinary.bytes,
            format: cloudinary.format,
            alt_text: `${productName} product photo`,
          }),
        });
        if (!registerResponse.ok) throw new Error(await errorMessage(registerResponse, "The uploaded photo could not be saved."));
        uploaded.push(await registerResponse.json() as AdminProductImage);
      }
      setImages((current) => [...current, ...uploaded]);
      setMessage(`${uploaded.length} photo${uploaded.length === 1 ? "" : "s"} added.`);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The photo could not be uploaded.");
    } finally {
      setPending(false);
      setProgress(null);
    }
  }

  async function saveAltText(image: AdminProductImage, altText: string) {
    const csrf = csrfToken();
    if (!csrf) return;
    const response = await fetch(`/api/admin/products/${productId}/images/${image.id}/alt-text`, {
      method: "PATCH",
      headers: { "content-type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({ alt_text: altText }),
    });
    if (!response.ok) return setError(await errorMessage(response, "Alternative text could not be saved."));
    const updated = await response.json() as AdminProductImage;
    setImages((current) => current.map((item) => item.id === updated.id ? updated : item));
    setMessage("Photo description saved.");
  }

  async function moveImage(index: number, direction: -1 | 1) {
    const destination = index + direction;
    if (destination < 0 || destination >= images.length) return;
    const csrf = csrfToken();
    if (!csrf) return;
    const reordered = [...images];
    [reordered[index], reordered[destination]] = [reordered[destination], reordered[index]];
    setImages(reordered);
    const response = await fetch(`/api/admin/products/${productId}/images/reorder`, {
      method: "PATCH",
      headers: { "content-type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({ image_ids: reordered.map((image) => image.id) }),
    });
    if (!response.ok) {
      setImages(images);
      setError(await errorMessage(response, "Photo order could not be saved."));
      return;
    }
    setImages(await response.json() as AdminProductImage[]);
    setMessage("Photo order saved.");
    router.refresh();
  }

  async function removeImage(image: AdminProductImage) {
    if (!window.confirm("Remove this photo from the product and Cloudinary?")) return;
    const csrf = csrfToken();
    if (!csrf) return;
    const response = await fetch(`/api/admin/products/${productId}/images/${image.id}`, {
      method: "DELETE", headers: { "X-CSRF-Token": csrf },
    });
    if (!response.ok) return setError(await errorMessage(response, "The photo could not be removed."));
    setImages(await response.json() as AdminProductImage[]);
    setMessage("Photo removed.");
    router.refresh();
  }

  return (
    <section className="rounded-3xl border border-[var(--line)] bg-white p-5 sm:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><h2 className="text-xl font-semibold">Product photos</h2><p className="mt-1 text-sm text-[var(--muted)]">The first photo is the cover. Add up to 10 JPG, PNG, WebP or AVIF files.</p></div>
        <label className="admin-primary cursor-pointer">
          {pending ? `Uploading${progress === null ? "" : ` ${progress}%`}…` : "Add photos"}
          <input accept="image/avif,image/jpeg,image/png,image/webp" className="sr-only" disabled={pending || images.length >= 10} multiple onChange={choosePhotos} type="file" />
        </label>
      </div>
      {progress !== null && <progress aria-label="Photo upload progress" className="mt-5 h-2 w-full accent-[var(--wine)]" max="100" value={progress}>{progress}%</progress>}
      {error && <p className="mt-4 text-sm text-[var(--wine)]" role="alert">{error}</p>}
      {message && <p className="mt-4 text-sm" role="status">{message}</p>}
      {images.length ? <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {images.map((image, index) => <article className="overflow-hidden rounded-2xl border border-[var(--line)]" key={image.id}>
          <div className="relative aspect-[4/5] bg-[var(--sand)]"><Image alt={image.alt_text} className="object-cover" fill sizes="(max-width: 640px) 100vw, 40vw" src={image.url} />{index === 0 && <span className="absolute left-3 top-3 rounded-full bg-[var(--ink)] px-3 py-1 text-xs text-white">Cover</span>}</div>
          <div className="grid gap-3 p-4">
            <label className="grid gap-1 text-xs text-[var(--muted)]">Photo description<input aria-label={`Description for photo ${index + 1}`} className="admin-input" defaultValue={image.alt_text} maxLength={255} minLength={2} onBlur={(event) => { if (event.target.value !== image.alt_text) void saveAltText(image, event.target.value); }} /></label>
            <div className="flex flex-wrap gap-2"><button className="rounded-full border border-[var(--line)] px-3 py-2 text-xs" disabled={index === 0} onClick={() => void moveImage(index, -1)} type="button">Move earlier</button><button className="rounded-full border border-[var(--line)] px-3 py-2 text-xs" disabled={index === images.length - 1} onClick={() => void moveImage(index, 1)} type="button">Move later</button><button className="ml-auto rounded-full px-3 py-2 text-xs text-[var(--wine)]" onClick={() => void removeImage(image)} type="button">Remove</button></div>
          </div>
        </article>)}
      </div> : <div className="mt-6 rounded-2xl border border-dashed border-[var(--line)] bg-[var(--paper)] px-5 py-10 text-center text-sm text-[var(--muted)]">No product photos yet. Add clear front, back and detail views.</div>}
    </section>
  );
}
