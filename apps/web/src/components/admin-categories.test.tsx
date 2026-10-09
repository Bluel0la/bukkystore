import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ refresh: vi.fn(), readCsrfCookie: vi.fn((): string | null => "csrf-token") }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: mocks.refresh }) }));
vi.mock("@/lib/admin-client", () => ({ readCsrfCookie: mocks.readCsrfCookie }));

import { AdminCategories, slugify } from "@/components/admin-categories";
import type { AdminCategory } from "@/lib/admin-types";

const categories: AdminCategory[] = [
  { id: "clothing-id", name: "Clothing", slug: "clothing", parent_id: null, is_active: true },
  { id: "dresses-id", name: "Dresses", slug: "dresses", parent_id: "clothing-id", is_active: true },
  { id: "old-id", name: "Old Season", slug: "old-season", parent_id: null, is_active: false },
];

describe("slugify", () => {
  it("builds backend-compatible slugs", () => {
    expect(slugify("Kaftans & More!")).toBe("kaftans-more");
    expect(slugify("  Two  Words  ")).toBe("two-words");
    expect(slugify("!!!")).toBe("");
  });
});

describe("AdminCategories", () => {
  beforeEach(() => {
    mocks.refresh.mockReset();
    mocks.readCsrfCookie.mockReturnValue("csrf-token");
  });
  afterEach(() => vi.unstubAllGlobals());

  it("lists categories with hierarchy and visibility", () => {
    render(<AdminCategories initial={categories} />);

    expect(screen.getByText("Dresses")).toBeDefined();
    expect(screen.getByText(/under Clothing/)).toBeDefined();
    expect(screen.getByText(/hidden/)).toBeDefined();
  });

  it("adds a category with an auto slug and parent", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminCategories initial={categories} />);

    fireEvent.change(screen.getByPlaceholderText("e.g. Kaftans"), { target: { value: "Kaftans" } });
    const selects = document.querySelectorAll("select");
    fireEvent.change(selects[0] as HTMLSelectElement, { target: { value: "clothing-id" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() => expect(mocks.refresh).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][0]).toBe("/api/admin/categories");
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      name: "Kaftans",
      slug: "kaftans",
      parent_id: "clothing-id",
    });
  });

  it("rejects short names without calling the API", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminCategories initial={categories} />);

    fireEvent.change(screen.getByPlaceholderText("e.g. Kaftans"), { target: { value: "K" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(screen.getByText("Give the category a name of at least 2 characters.")).toBeDefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("renames a category with a regenerated slug", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminCategories initial={categories} />);

    fireEvent.click(screen.getAllByRole("button", { name: "Rename" })[0]);
    fireEvent.change(screen.getByLabelText("New name for Clothing"), { target: { value: "All Clothing" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(mocks.refresh).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][0]).toBe("/api/admin/categories/clothing-id");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      name: "All Clothing",
      slug: "all-clothing",
    });
  });

  it("toggles visibility and reports failures with field detail", async () => {
    const fetchMock = vi.fn().mockImplementation(
      () =>
        new Response(JSON.stringify({ code: "category_conflict", message: "Taken." }), {
          status: 409,
          headers: { "content-type": "application/json" },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminCategories initial={categories} />);

    fireEvent.click(screen.getAllByRole("button", { name: "Hide" })[0]);

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ is_active: false });

    fireEvent.click(screen.getAllByRole("button", { name: "Rename" })[0]);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText("Taken.");
  });
});
