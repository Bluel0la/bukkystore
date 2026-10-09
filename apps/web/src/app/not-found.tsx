import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl items-center px-5 py-12">
      <section className="checkout-card w-full text-center">
        <p className="text-xs uppercase tracking-[0.18em] text-(--wine)">Missing page</p>
        <h1 className="mt-4 text-3xl font-semibold">We couldn&apos;t find that.</h1>
        <p className="mt-4 text-(--muted)">The product may have sold out or the link may be old.</p>
        <Link className="admin-primary mt-7 inline-block" href="/">Return to the store</Link>
      </section>
    </main>
  );
}
