"use client";
import { useEffect, useRef } from "react";
import { X } from "lucide-react";
export function Drawer({
  title,
  subtitle,
  onClose,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panel.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const handle = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab") return;
      const focusables = panel.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), a[href], [tabindex="0"]',
      );
      if (!focusables?.length) return;
      const first = focusables[0],
        last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handle);
    return () => {
      document.removeEventListener("keydown", handle);
      document.body.style.overflow = overflow;
      previous?.focus();
    };
  }, [onClose]);
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <section
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        ref={panel}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="drawer-heading">
          <div>
            <span className="eyebrow">SELLSMART WORKSPACE</span>
            <h2 id="drawer-title">{title}</h2>
            <p>{subtitle}</p>
          </div>
          <button
            className="icon-button"
            aria-label="Close drawer"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </header>
        <div className="drawer-body">{children}</div>
        {footer && <footer className="drawer-footer">{footer}</footer>}
      </section>
    </div>
  );
}
