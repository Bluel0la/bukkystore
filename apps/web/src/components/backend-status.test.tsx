import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { BackendStatus } from "./backend-status";

afterEach(() => {
  vi.restoreAllMocks();
});

test("reports a connected API", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 200 }));

  render(<BackendStatus />);

  expect(screen.getByText(/checking api/i)).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText(/store api connected/i)).toBeInTheDocument());
});

test("reports an unavailable API after a failed response", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 503 }));

  render(<BackendStatus />);

  await waitFor(() => expect(screen.getByText(/store api unavailable/i)).toBeInTheDocument());
});

test("reports an unavailable API after a network failure", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network unavailable"));

  render(<BackendStatus />);

  await waitFor(() => expect(screen.getByText(/store api unavailable/i)).toBeInTheDocument());
});
