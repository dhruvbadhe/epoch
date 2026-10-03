"use client";
import { useEffect, useState } from "react";
import {
  Check,
  Clipboard,
  MapPin,
  MessageCircle,
  RefreshCw,
  SlidersHorizontal,
  Sprout,
} from "lucide-react";
import { ApiError, getAdvice } from "@/lib/api";
import { useResource } from "@/lib/useResource";
import type {
  AdviceRequest,
  ApiResult,
  Lang,
  Overrides,
  Village,
} from "@/lib/types";
import { AdviceCard } from "./AdviceCard";
import { WhyBreakdown } from "./WhyBreakdown";
import { ForecastChart } from "./ForecastChart";
import { MandiTable } from "./MandiTable";
import { ScrollReveal } from "./ScrollReveal";
import {
  Empty,
  ErrorState,
  FreshnessSelect,
  Loading,
  SourceBadge,
  SourceNote,
} from "./ui";
export function AdviceTab({
  villages,
  lang,
  overrides,
  onAssumptions,
  onStatus,
  active = true,
}: {
  villages: Village[];
  lang: Lang;
  overrides: Overrides;
  onAssumptions: () => void;
  onStatus: (result: ApiResult<unknown>) => void;
  active?: boolean;
}) {
  const [input, setInput] = useState<AdviceRequest>({
    crop: "onion",
    quantity_qtl: 20,
    village: "Niphad",
    lot_condition: null,
    cash_needed_in_days: null,
    blocked_mandis: [],
    overrides: null,
    lang: "en",
  });
  const [quantity, setQuantity] = useState("20");
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState("");
  const request = { ...input, quantity_qtl: Number(quantity), overrides, lang };
  const valid =
    Number.isFinite(request.quantity_qtl) && request.quantity_qtl > 0;
  const { result, loading, error, reload } = useResource(
    JSON.stringify(request),
    () => getAdvice(request),
    valid && villages.length > 0,
  );
  useEffect(() => {
    if (result) onStatus(result);
  }, [result, onStatus]);
  useEffect(() => {
    setCopied(false);
  }, [result]);
  useEffect(() => {
    if (villages.length && !villages.some((v) => v.village === input.village))
      setInput((v) => ({ ...v, village: villages[0].village }));
  }, [villages, input.village]);
  const update = <K extends keyof AdviceRequest>(
    key: K,
    value: AdviceRequest[K],
  ) => setInput((v) => ({ ...v, [key]: value }));
  const fieldError = error instanceof ApiError ? error : null;
  return (
    <div className="tab-content">
      <section className="panel input-panel">
        <div className="input-panel-heading">
          <span>
            <Sprout size={16} />
            Tell us about the harvest
          </span>
          <span className="tiny">Advice updates as you change the details</span>
        </div>
        <div className="advice-inputs">
          <div className="field">
            <label htmlFor="crop">Crop</label>
            <select
              id="crop"
              value={input.crop}
              onChange={(e) =>
                setInput((v) => ({
                  ...v,
                  crop: e.target.value as AdviceRequest["crop"],
                  lot_condition: null,
                }))
              }
            >
              <option value="onion">🧅 Onion</option>
              <option value="tomato">🍅 Tomato</option>
              <option value="soybean">🌱 Soybean</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="quantity">Quantity</label>
            <div className="input-with-unit">
              <input
                id="quantity"
                type="number"
                min="0"
                step="any"
                value={quantity}
                aria-invalid={!valid}
                onChange={(e) => setQuantity(e.target.value)}
              />
              <span>quintals</span>
            </div>
            {!valid && (
              <small className="field-error">
                Enter a quantity greater than zero.
              </small>
            )}
            {fieldError?.field === "quantity_qtl" && (
              <small className="field-error">{fieldError.message}</small>
            )}
          </div>
          <div className="field">
            <label htmlFor="village">
              Village <MapPin size={11} />
            </label>
            <select
              id="village"
              value={input.village}
              onChange={(e) => update("village", e.target.value)}
            >
              {villages.map((v) => (
                <option key={v.village} value={v.village}>
                  {lang === "mr"
                    ? v.name_mr
                    : lang === "hi"
                      ? (v.name_hi ?? v.village)
                      : v.village}
                </option>
              ))}
            </select>
            {fieldError?.field === "village" && (
              <small className="field-error">{fieldError.message}</small>
            )}
          </div>
          <div className="field freshness-field">
            <label htmlFor="freshness">
              {input.crop === "tomato"
                ? "When was it picked?"
                : input.crop === "onion"
                  ? "Dried & ventilated?"
                  : "Fully dried?"}
            </label>
            <FreshnessSelect
              crop={input.crop}
              value={input.lot_condition}
              onChange={(v) => update("lot_condition", v)}
            />
          </div>
          <div className="field">
            <label htmlFor="cash">Need money by</label>
            <select
              id="cash"
              value={input.cash_needed_in_days ?? ""}
              onChange={(e) =>
                update(
                  "cash_needed_in_days",
                  e.target.value ? (Number(e.target.value) as 3 | 7) : null,
                )
              }
            >
              <option value="">No hurry</option>
              <option value="7">This week</option>
              <option value="3">In 2–3 days</option>
            </select>
          </div>
        </div>
        <div className="input-panel-footer">
          <span>
            <span className="status-dot" />
            Maharashtra · 3 crops · {villages.length} villages covered
          </span>
          <button onClick={onAssumptions}>
            <SlidersHorizontal size={13} />
            {overrides ? "Custom" : "Default"} assumptions
          </button>
        </div>
      </section>
      {!valid ? (
        <Empty
          title="Add the harvest quantity"
          text="A positive quantity is needed to calculate the lot’s estimated total."
        />
      ) : loading ? (
        <Loading />
      ) : error ? (
        <ErrorState error={error} retry={reload} />
      ) : (
        result && (
          <>
            <SourceNote result={result} />
            <ScrollReveal className="advice-grid">
              <AdviceCard
                advice={result.data}
                quantity={request.quantity_qtl}
                lang={lang}
              />
              <WhyBreakdown advice={result.data} />
            </ScrollReveal>
            <ScrollReveal className="outlook-grid">
              {active && (
                <ForecastChart crop={input.crop} mandi={result.data.mandi} />
              )}
              <section className="panel whatsapp-panel">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">WhatsApp reply</span>
                    <h2>
                      <MessageCircle size={20} />
                      The farmer’s reply
                    </h2>
                  </div>
                  <span className="badge">
                    {lang === "en"
                      ? "English"
                      : lang === "mr"
                        ? "मराठी"
                        : "हिंदी"}
                  </span>
                </div>
                <div className="whatsapp-preview">
                  <div className="chat-bubble">
                    {result.data.message.split("\n").map((line, i) => (
                      <p key={i}>
                        {line
                          .split(/(\*[^*]+\*)/g)
                          .map((part, j) =>
                            part.startsWith("*") ? (
                              <strong key={j}>{part.slice(1, -1)}</strong>
                            ) : (
                              part
                            ),
                          )}
                      </p>
                    ))}
                    <span className="chat-stamp">
                      SellSmart <Check size={11} />
                      <Check size={11} />
                    </span>
                  </div>
                </div>
                <div className="whatsapp-footer">
                  <span className="tiny">
                    Exact message returned by the advice API
                  </span>
                  <button
                    className="button subtle"
                    onClick={async () => {
                      try {
                        await navigator.clipboard.writeText(
                          result.data.message,
                        );
                        setCopied(true);
                        setCopyError("");
                      } catch {
                        setCopyError(
                          "Clipboard unavailable. Select the reply text to copy it.",
                        );
                      }
                    }}
                  >
                    {copied ? <Check size={14} /> : <Clipboard size={14} />}{" "}
                    {copied ? "Copied" : "Copy reply"}
                  </button>
                </div>
                {copyError && (
                  <p className="field-error" role="status">
                    {copyError}
                  </p>
                )}
              </section>
            </ScrollReveal>
            <ScrollReveal>
              <MandiTable advice={result.data} />
            </ScrollReveal>
            <div className="advice-notes">
              <div>
                <SourceBadge mock={result.mock} />
                <button className="button subtle" onClick={reload}>
                  <RefreshCw size={13} />
                  Refresh advice
                </button>
              </div>
            </div>
          </>
        )
      )}
    </div>
  );
}
