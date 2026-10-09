import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { POST } from "./route";

const request = () => new NextRequest("http://localhost/api/admin/auth/login", { method: "POST", body: JSON.stringify({ email: "owner@example.com", password: "test-password-only" }), headers: { "content-type": "application/json" } });
const context = { params: Promise.resolve({ path: ["auth", "login"] }) };
afterEach(() => vi.unstubAllGlobals());

describe("admin login proxy", () => {
  it("bounds the upstream request and preserves successful session cookies", async () => {
    const headers = new Headers({ "content-type": "application/json" });
    headers.append("set-cookie", "session=test; HttpOnly; Path=/");
    headers.append("set-cookie", "csrf=test; Path=/");
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { headers }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await POST(request(), context);
    expect(response.status).toBe(200);
    expect(response.headers.getSetCookie()).toHaveLength(2);
    expect(fetchMock.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal);
  });
  it("returns a retryable timeout instead of hanging or reporting invalid credentials", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("Timed out", "TimeoutError")));
    const response = await POST(request(), context);
    expect(response.status).toBe(504);
    expect(await response.json()).toEqual({ message: "Sign-in timed out. Please try again shortly." });
  });
  it("reports a disconnected API as unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    expect((await POST(request(), context)).status).toBe(503);
  });
});
