"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // Logged client-side only; the correlation ID stays server-side for safety.
    console.error("storefront_error", error.message);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-screen max-w-xl items-center px-5 py-12">
      <section className="checkout-card w-full text-center">
        <p className="text-xs uppercase tracking-[0.18em] text-[var(--wine)]">Something went wrong</p>
        <h1 className="mt-4 text-3xl font-semibold">Please try again.</h1>
        <p className="mt-4 text-[var(--muted)]">The store hit a temporary problem loading this page.</p>
        <div className="mt-7 flex justify-center gap-3">
          <button className="admin-primary" onClick={reset} type="button">Try again</button>
          <Link className="rounded-full border border-[var(--line)] px-4 py-2 text-sm" href="/">Return to the store</Link>
        </div>
      </section>
    </main>
  );
}
