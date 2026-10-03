"use client";

import { useEffect, useRef, type ReactNode } from "react";

export function ScrollReveal({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  const element = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const target = element.current;
    if (
      !target ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    )
      return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          target.classList.add("is-revealed");
          observer.disconnect();
        }
      },
      { threshold: 0.06, rootMargin: "0px 0px -20px 0px" },
    );
    target.classList.add("reveal-ready");
    observer.observe(target);
    return () => observer.disconnect();
  }, []);
  return (
    <div ref={element} className={`scroll-reveal ${className}`}>
      {children}
    </div>
  );
}
