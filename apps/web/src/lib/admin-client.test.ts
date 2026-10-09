import { afterEach, describe, expect, it } from "vitest";

import { readCsrfCookie } from "@/lib/admin-client";

describe("readCsrfCookie", () => {
  afterEach(() => {
    document.cookie = "bukky_admin_csrf=; Max-Age=0; path=/";
  });

  it("reads and decodes the CSRF cookie", () => {
    document.cookie = "bukky_admin_csrf=token%2Fvalue; path=/";
    expect(readCsrfCookie()).toBe("token/value");
  });

  it("returns null when the cookie is absent", () => {
    expect(readCsrfCookie()).toBeNull();
  });
});
