"use client";

/**
 * Adapted from Kokonut UI Smooth Tab v1.0.0 by @dorianbaffier (MIT).
 * Source: https://kokonutui.com/r/smooth-tab.json
 * Keeps its measured, spring-animated indicator; uses URL-controlled links
 * instead of the demo's local-state buttons and fixed-height content card.
 */
import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { useLayoutEffect, useRef, useState } from "react";

export type SmoothTabItem = { id: string; title: string; href: string };

export default function SmoothTab({ items, selected }: {
  items: SmoothTabItem[];
  selected: string;
}) {
  const reduceMotion = useReducedMotion();
  const containerRef = useRef<HTMLElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const linkRefs = useRef(new Map<string, HTMLAnchorElement>());
  const [dimensions, setDimensions] = useState({ width: 0, left: 0 });
  const indicatorReady = dimensions.width > 0 && items.some((item) => item.id === selected);

  useLayoutEffect(() => {
    const link = linkRefs.current.get(selected);
    const container = containerRef.current;
    const track = trackRef.current;
    if (!link || !container || !track) return;

    const measure = () => {
      setDimensions({ width: link.offsetWidth, left: link.offsetLeft });
      // Scroll only the horizontal category strip, never the whole document.
      const left = link.offsetLeft;
      const right = left + link.offsetWidth;
      if (left < container.scrollLeft) container.scrollLeft = left;
      else if (right > container.scrollLeft + container.clientWidth) {
        container.scrollLeft = right - container.clientWidth;
      }
    };
    const frame = requestAnimationFrame(measure);
    const observer = typeof ResizeObserver !== "undefined" ? new ResizeObserver(measure) : null;
    observer?.observe(track);
    observer?.observe(link);
    window.addEventListener("resize", measure);
    return () => {
      cancelAnimationFrame(frame);
      observer?.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [selected, items]);

  return <nav
    aria-label="Shop by category"
    className="category-tabs smooth-category-tabs"
    data-indicator-ready={indicatorReady}
    ref={containerRef}
  >
    <div className="smooth-category-track" ref={trackRef}>
      <motion.div
        aria-hidden="true"
        className="smooth-category-indicator"
        initial={false}
        animate={{ width: dimensions.width, x: dimensions.left, opacity: indicatorReady ? 1 : 0 }}
        transition={reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 400, damping: 30 }}
      />
      {items.map((item) => <Link
        key={item.id}
        href={item.href}
        scroll={false}
        aria-current={selected === item.id ? "page" : undefined}
        ref={(element) => {
          if (element) linkRefs.current.set(item.id, element);
          else linkRefs.current.delete(item.id);
        }}
      >{item.title}</Link>)}
    </div>
  </nav>;
}
