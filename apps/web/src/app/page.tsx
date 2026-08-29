import Link from "next/link";

import { BackendStatus } from "@/components/backend-status";

const categories = ["Dresses", "Shoes", "Bags", "Accessories"];

export default function Home() {
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-5 py-6 sm:px-8 lg:px-12">
      <header className="flex items-center justify-between border-b border-[var(--line)] pb-5">
        <Link className="text-xl font-semibold tracking-[-0.03em]" href="/">
          Bukky Store
        </Link>
        <nav aria-label="Primary navigation" className="flex items-center gap-5 text-sm">
          <Link href="#categories">Shop</Link>
          <Link className="rounded-full bg-[var(--ink)] px-4 py-2 text-white" href="/admin">
            Admin
          </Link>
        </nav>
      </header>

      <section className="grid gap-10 py-16 md:grid-cols-[1.2fr_0.8fr] md:items-end md:py-24">
        <div>
          <p className="mb-5 text-xs font-bold uppercase tracking-[0.22em] text-[var(--wine)]">
            Lagos · New collection coming soon
          </p>
          <h1 className="max-w-3xl text-5xl font-semibold leading-[0.95] tracking-[-0.055em] sm:text-7xl">
            Find the piece that feels like you.
          </h1>
        </div>
        <div className="border-l-2 border-[var(--peach)] pl-5 text-[var(--muted)]">
          <p className="max-w-sm leading-7">
            A mobile-first home for clothing, shoes, bags, and accessories—made easy to
            discover, ask about, and buy.
          </p>
          <BackendStatus />
        </div>
      </section>

      <section aria-labelledby="categories-title" id="categories">
        <div className="mb-5 flex items-end justify-between">
          <h2 className="text-2xl font-semibold tracking-[-0.03em]" id="categories-title">
            Shop by category
          </h2>
          <span className="text-sm text-[var(--muted)]">Catalogue arriving next</span>
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {categories.map((category, index) => (
            <div
              className="flex aspect-[4/5] items-end rounded-3xl border border-[var(--line)] p-5"
              key={category}
              style={{ backgroundColor: index % 2 === 0 ? "#f6ded2" : "#efe7dc" }}
            >
              <span className="text-lg font-semibold">{category}</span>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
