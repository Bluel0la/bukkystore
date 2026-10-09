import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AdminLoginForm } from "@/components/admin-login-form";
import { AdminLogout } from "@/components/admin-logout";

const replace = vi.fn();
const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace, refresh }) }));

describe("admin authentication controls", () => {
  beforeEach(() => {
    replace.mockReset();
    refresh.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    document.cookie = "bukky_admin_csrf=; Max-Age=0; path=/";
  });

  it("signs in and navigates to the dashboard", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminLoginForm />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "owner@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct-password-value" } });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/admin"));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/auth/login",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows invalid, throttled, and unavailable errors", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("{}", { status: 401 }))
      .mockResolvedValueOnce(new Response("{}", { status: 429 }))
      .mockRejectedValueOnce(new Error("offline"));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminLoginForm />);
    const form = screen.getByRole("button", { name: "Sign in" }).closest("form")!;
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "owner@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "incorrect-password" } });

    fireEvent.submit(form);
    await screen.findByText("Email or password is incorrect.");
    fireEvent.submit(form);
    await screen.findByText("Too many attempts. Please wait and try again.");
    fireEvent.submit(form);
    await screen.findByText("Sign-in is temporarily unavailable.");
  });

  it("signs out with the CSRF token", async () => {
    document.cookie = "bukky_admin_csrf=csrf-token; path=/";
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminLogout />);

    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/admin/login"));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/auth/logout",
      expect.objectContaining({ headers: { "X-CSRF-Token": "csrf-token" } }),
    );
  });

  it.each([500, 503, 504])("does not blame credentials for server error %s", async (status) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status })));
    render(<AdminLoginForm />);
    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);
    expect(await screen.findByRole("alert")).toHaveTextContent(status === 504 ? "Sign-in timed out" : "Sign-in is temporarily unavailable");
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
    expect(replace).not.toHaveBeenCalled();
  });

  it("aborts a stuck request and allows another attempt", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockImplementationOnce((_url, options: RequestInit) => new Promise((_resolve, reject) => {
      options.signal!.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    })).mockResolvedValueOnce(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminLoginForm />);
    const form = screen.getByRole("button", { name: "Sign in" }).closest("form")!;
    fireEvent.submit(form);
    expect(screen.getByRole("button", { name: "Signing in…" })).toBeDisabled();
    await act(() => vi.advanceTimersByTimeAsync(20000));
    expect(screen.getByRole("alert")).toHaveTextContent("Sign-in timed out");
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
    await act(async () => fireEvent.submit(form));
    expect(replace).toHaveBeenCalledWith("/admin");
  });

  it("does not send logout without a CSRF token", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminLogout />);
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
