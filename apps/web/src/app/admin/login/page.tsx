import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { AdminLoginForm } from "@/components/admin-login-form";
import { getAdminUser } from "@/lib/admin";

export const metadata: Metadata = { title: "Admin sign in" };

export default async function AdminLoginPage() {
  if (await getAdminUser()) redirect("/admin");

  return (
    <main className="mx-auto grid min-h-screen max-w-5xl items-center px-5 py-10 sm:px-8">
      <div className="grid overflow-hidden rounded-[2rem] border border-[var(--line)] bg-white shadow-[0_24px_80px_rgba(70,35,30,0.08)] md:grid-cols-2">
        <section className="bg-[var(--wine)] p-8 text-white sm:p-12">
          <p className="text-xs uppercase tracking-[0.2em] text-[#f2c7b8]">Atiten Kids Store</p>
          <h1 className="mt-6 text-4xl font-semibold tracking-[-0.045em]">Your shop, in one calm place.</h1>
          <p className="mt-5 max-w-sm leading-7 text-[#f2ded7]">Add new pieces, publish them, and keep every colour and size in stock from your phone.</p>
          <Link className="mt-10 inline-block text-sm underline underline-offset-4" href="/">Back to storefront</Link>
        </section>
        <section className="p-8 sm:p-12">
          <p className="text-sm text-[var(--muted)]">Private management area</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">Welcome back</h2>
          <AdminLoginForm />
        </section>
      </div>
    </main>
  );
}
