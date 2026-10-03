"use client";
import {
  AlertCircle,
  ArrowUpRight,
  Database,
  RefreshCw,
  SearchX,
} from "lucide-react";
import type { ApiResult, Crop, LotCondition } from "@/lib/types";
export function SourceNote({ result }: { result: ApiResult<unknown> | null }) {
  if (!result) return null;
  return result.fallback ? (
    <div className="notice warning" role="status">
      <Database size={16} />
      {result.fallback}
    </div>
  ) : null;
}
export function SourceBadge({ mock }: { mock: boolean }) {
  return (
    <span className={`badge ${mock ? "mock" : "green"}`}>
      <span className="status-dot" />
      {mock ? "Mock data" : "Live engine"}
    </span>
  );
}
export function Loading({
  text = "Preparing your recommendation…",
}: {
  text?: string;
}) {
  return (
    <div className="empty-state loading-state" role="status">
      <RefreshCw size={24} />
      <h3>{text}</h3>
      <p>Comparing prices, costs, and the lot’s constraints.</p>
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: Error;
  retry: () => void;
}) {
  return (
    <div className="empty-state error-state" role="alert">
      <AlertCircle size={28} />
      <h3>We couldn’t complete this request</h3>
      <p>{error.message}</p>
      <button className="button secondary" onClick={retry}>
        <RefreshCw size={15} />
        Try again
      </button>
    </div>
  );
}
export function Empty({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty-state">
      <SearchX size={28} />
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}
export function SectionHeading({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h2>{title}</h2>
      </div>
      {children}
    </div>
  );
}
export function FreshnessSelect({
  crop,
  value,
  onChange,
  id = "freshness",
}: {
  crop: Crop;
  value: LotCondition;
  onChange: (v: LotCondition) => void;
  id?: string;
}) {
  return (
    <select
      id={id}
      aria-label="Lot condition"
      value={value === null ? "" : String(value)}
      onChange={(e) =>
        onChange(
          e.target.value === ""
            ? null
            : crop === "tomato"
              ? (Number(e.target.value) as 0 | 1 | 2)
              : e.target.value === "true",
        )
      }
    >
      <option value="">Not asked</option>
      {crop === "tomato" ? (
        <>
          <option value="0">Picked today</option>
          <option value="1">Picked 1–2 days ago</option>
          <option value="2">Picked 3+ days ago</option>
        </>
      ) : (
        <>
          <option value="true">
            Yes, {crop === "onion" ? "dried & ventilated" : "fully dried"}
          </option>
          <option value="false">
            No, {crop === "onion" ? "not cured" : "not fully dried"}
          </option>
        </>
      )}
    </select>
  );
}
export function GainTag({ children }: { children: React.ReactNode }) {
  return (
    <span className="gain-tag">
      <ArrowUpRight size={15} />
      {children}
    </span>
  );
}
export function downloadCsv(
  name: string,
  headers: string[],
  rows: (string | number)[][],
) {
  const csv =
    "\uFEFF" +
    [headers, ...rows]
      .map((row) =>
        row.map((v) => `"${String(v).replaceAll('"', '""')}"`).join(","),
      )
      .join("\r\n");
  const url = URL.createObjectURL(
    new Blob([csv], { type: "text/csv;charset=utf-8;" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
