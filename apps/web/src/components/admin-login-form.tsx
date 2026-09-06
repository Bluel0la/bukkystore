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
    try {
      const response = await fetch("/api/admin/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
      });
      if (!response.ok) {
        setError(response.status === 429 ? "Too many attempts. Please wait and try again." : "Email or password is incorrect.");
        return;
      }
      router.replace("/admin");
      router.refresh();
    } catch {
      setError("Sign-in is temporarily unavailable.");
    } finally {
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
