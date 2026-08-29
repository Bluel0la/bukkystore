"use client";

import { useEffect, useState } from "react";

type Status = "checking" | "connected" | "unavailable";

const labels: Record<Status, string> = {
  checking: "Checking API…",
  connected: "Store API connected",
  unavailable: "Store API unavailable",
};

export function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    const controller = new AbortController();

    async function checkHealth() {
      try {
        const response = await fetch("/api/backend-health", {
          cache: "no-store",
          signal: controller.signal,
        });
        setStatus(response.ok ? "connected" : "unavailable");
      } catch {
        if (!controller.signal.aborted) setStatus("unavailable");
      }
    }

    void checkHealth();
    return () => controller.abort();
  }, []);

  return (
    <p aria-live="polite" className="mt-5 text-xs font-bold uppercase tracking-[0.15em]">
      <span aria-hidden="true">{status === "connected" ? "●" : "○"}</span> {labels[status]}
    </p>
  );
}
