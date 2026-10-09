"use client";

import Image from "next/image";
import { useState } from "react";

import type { ProductImage } from "@/lib/catalogue";

export function ProductGallery({ images }: { images: ProductImage[] }) {
  const [selected, setSelected] = useState(0);
  if (!images.length) return <div className="flex aspect-[4/5] items-center justify-center rounded-[2.5rem] border border-[var(--line)] bg-[var(--sand)] text-center"><div><span className="text-7xl text-(--peach)" aria-hidden="true">B</span><p className="mt-5 text-xs uppercase tracking-[0.2em] text-(--muted)">Photo coming soon</p></div></div>;
  const active = images[selected] ?? images[0];
  return <div className="grid gap-3">
    <div className="relative aspect-[4/5] overflow-hidden rounded-[2.5rem] border border-[var(--line)] bg-[var(--sand)]">
      <Image alt={active.alt_text} className="object-cover" fill priority sizes="(max-width: 768px) 100vw, 50vw" src={active.url} />
    </div>
    {images.length > 1 && <div aria-label="Choose a product photo" className="grid grid-cols-5 gap-2" role="group">{images.map((image, index) => <button aria-label={`Show photo ${index + 1}`} aria-pressed={selected === index} className={`relative aspect-[4/5] overflow-hidden rounded-xl border-2 ${selected === index ? "border-[var(--wine)]" : "border-transparent"}`} key={image.url} onClick={() => setSelected(index)} type="button"><Image alt="" className="object-cover" fill sizes="20vw" src={image.url} /></button>)}</div>}
  </div>;
}
