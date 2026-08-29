import Link from "next/link";

const cards = ["Sales", "Orders", "Visitors", "WhatsApp enquiries", "Low stock"];

export default function AdminPage() {
  return (
    <main className="mx-auto min-h-screen max-w-5xl px-5 py-6 sm:px-8">
      <header className="mb-10 flex items-center justify-between">
        <div>
          <p className="text-sm text-[var(--muted)]">Bukky Store</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em]">Dashboard foundation</h1>
        </div>
        <Link className="rounded-full border border-[var(--line)] px-4 py-2 text-sm" href="/">
          View store
        </Link>
      </header>
      <section aria-label="Store overview" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {cards.map((card) => (
          <article className="min-h-32 rounded-2xl border border-[var(--line)] bg-white p-4" key={card}>
            <p className="text-sm text-[var(--muted)]">{card}</p>
            <p className="mt-5 text-2xl font-semibold">—</p>
          </article>
        ))}
      </section>
      <p className="mt-8 rounded-2xl bg-[#f6ded2] p-5 text-sm leading-6">
        Authentication and real store data arrive with the catalogue release. This route exists
        now to validate the shared mobile-first application shell.
      </p>
    </main>
  );
}
