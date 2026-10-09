"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

export function AdminLoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPending(true);
    const form = new FormData(event.currentTarget);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch("/api/admin/auth/login", {
        signal: controller.signal,
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
      });
      if (!response.ok) {
        setError(response.status === 429
          ? "Too many attempts. Please wait and try again."
          : response.status === 401
            ? "Email or password is incorrect."
            : response.status === 504
              ? "Sign-in timed out. Please try again shortly."
              : "Sign-in is temporarily unavailable.");
        return;
      }
      router.replace("/admin");
      router.refresh();
    } catch {
      setError(controller.signal.aborted
        ? "Sign-in timed out. Please try again shortly."
        : "Sign-in is temporarily unavailable.");
    } finally {
      window.clearTimeout(timeout);
      setPending(false);
    }
  }

  return (
    <form className="mt-8 grid gap-5" onSubmit={submit}>
      <label className="grid gap-2 text-sm font-medium">
        Email
        <input autoComplete="email" className="admin-input" name="email" required type="email" />
      </label>
      <label className="grid gap-2 text-sm font-medium">
        Password
        <input autoComplete="current-password" className="admin-input" minLength={12} name="password" required type="password" />
      </label>
      {error && <p className="rounded-xl bg-[#f4e6e7] p-3 text-sm text-(--wine)" role="alert">{error}</p>}
      <button className="admin-primary" disabled={pending} type="submit">
        {pending ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
