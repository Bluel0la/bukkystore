import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import SmoothTab from "./smooth-tab";

const items = [
  { id: "all", title: "All little things", href: "/?search=linen#shop" },
  { id: "dresses", title: "Dresses", href: "/?search=linen&category=dresses#shop" },
];

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("Smooth category navigation", () => {
  it("follows the URL-selected category when navigating forwards and backwards", () => {
    const { rerender } = render(<SmoothTab items={items} selected="all" />);
    expect(screen.getByRole("link", { name: "All little things" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Dresses" })).toHaveAttribute("href", items[1].href);
    rerender(<SmoothTab items={items} selected="dresses" />);
    expect(screen.getByRole("link", { name: "Dresses" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "All little things" })).not.toHaveAttribute("aria-current");
    rerender(<SmoothTab items={items} selected="all" />);
    expect(screen.getAllByRole("navigation")).toHaveLength(1);
    expect(screen.getAllByRole("link")).toHaveLength(2);
    expect(screen.getByRole("link", { name: "All little things" })).toHaveAttribute("aria-current", "page");
  });

  it("measures the active link, keeps it visible, and cleans up observers", () => {
    const disconnect = vi.fn();
    const observe = vi.fn();
    vi.stubGlobal("ResizeObserver", class { observe = observe; disconnect = disconnect; });
    let measure: FrameRequestCallback = () => {};
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => { measure = callback; return 1; });
    const { rerender, unmount } = render(<SmoothTab items={items} selected="dresses" />);
    const nav = screen.getByRole("navigation");
    const link = screen.getByRole("link", { name: "Dresses" });
    Object.defineProperties(link, { offsetLeft: { value: 150 }, offsetWidth: { value: 100 } });
    Object.defineProperty(nav, "clientWidth", { value: 200 });
    act(() => measure(0));
    expect(nav).toHaveAttribute("data-indicator-ready", "true");
    expect(nav.scrollLeft).toBe(50);
    nav.scrollLeft = 180;
    act(() => window.dispatchEvent(new Event("resize")));
    expect(nav.scrollLeft).toBe(150);
    expect(observe).toHaveBeenCalledTimes(2);
    rerender(<SmoothTab items={items} selected="unknown" />);
    expect(nav).toHaveAttribute("data-indicator-ready", "false");
    unmount();
    expect(disconnect).toHaveBeenCalled();
  });
});
