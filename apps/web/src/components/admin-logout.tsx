"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { readCsrfCookie } from "@/lib/admin-client";

export function AdminLogout() {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function logout() {
    const csrf = readCsrfCookie();
    if (!csrf) return;
    setPending(true);
    await fetch("/api/admin/auth/logout", { method: "POST", headers: { "X-CSRF-Token": csrf } });
    router.replace("/admin/login");
    router.refresh();
  }

  return <button className="rounded-full border border-[var(--line)] px-4 py-2 text-sm" disabled={pending} onClick={logout} type="button">{pending ? "Signing out…" : "Sign out"}</button>;
}
