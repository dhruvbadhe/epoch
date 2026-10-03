import backtest from "@/mock/backtest.json";
import mandis from "@/mock/mandis.json";
import villages from "@/mock/villages.json";
import queries from "@/mock/queries.json";
import { defaultConfig, demoAdvice, demoForecast, demoPlan } from "./demo";
import type {
  Advice,
  AdviceRequest,
  ApiResult,
  Backtest,
  Config,
  Crop,
  Forecast,
  Mandi,
  MessageRequest,
  MessageResponse,
  Plan,
  PlanRequest,
  Query,
  Village,
} from "./types";
const baseUrl = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");
export const mockEnabled = process.env.NEXT_PUBLIC_USE_MOCK === "true";
export class ApiError extends Error {
  constructor(
    message: string,
    public field?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
function validResponse(path: string, value: unknown): boolean {
  const record = value as Record<string, unknown> | null;
  const endpoint = path.split("?")[0];
  if (["/mandis", "/villages", "/queries"].includes(endpoint)) {
    if (!Array.isArray(value)) return false;
    const key =
      endpoint === "/mandis"
        ? "mandi"
        : endpoint === "/villages"
          ? "village"
          : "sender";
    return value.every((row) => row && typeof row[key] === "string");
  }
  if (!record || typeof record !== "object" || Array.isArray(record))
    return false;
  if (endpoint === "/advise")
    return (
      ["hold", "sell_now"].includes(String(record.action)) &&
      typeof record.net_per_qtl === "number" &&
      typeof record.prices_as_of === "string" &&
      typeof record.message === "string" &&
      Array.isArray(record.options) &&
      Array.isArray(record.notes) &&
      !!record.why &&
      !!record.baseline_today &&
      !!record.best_today
    );
  if (endpoint === "/fpo/plan")
    return (
      Array.isArray(record.assignments) &&
      Array.isArray(record.trucks) &&
      Array.isArray(record.unplaced) &&
      typeof record.total_net === "number" &&
      typeof record.prices_as_of === "string"
    );
  if (endpoint === "/backtest")
    return (
      Array.isArray(record.ladder) &&
      Array.isArray(record.coverage) &&
      Array.isArray(record.selfcheck) &&
      !!record.test_period &&
      !!record.cases_excluded_by_reason
    );
  if (endpoint === "/forecast")
    return (
      Array.isArray(record.history) &&
      Array.isArray(record.forecast) &&
      typeof record.prices_as_of === "string"
    );
  if (endpoint === "/config")
    return (
      !!record.transport &&
      !!record.fpo &&
      !!record.hold_limit_days &&
      !!record.confidence &&
      !!record.forecast &&
      !!record.spoilage_per_day &&
      !!record.storage_cost_per_qtl_per_day
    );
  return (
    typeof record.reply === "string" &&
    typeof record.state === "string" &&
    !!record.parsed
  );
}
async function call<T>(
  path: string,
  fallback: () => T,
  body?: unknown,
): Promise<ApiResult<T>> {
  if (mockEnabled) return { data: fallback(), mock: true };
  try {
    const response = await fetch(`${baseUrl}${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers:
        body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(6000),
      cache: "no-store",
    });
    if (response.status >= 400 && response.status < 500) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(
        error.error ?? "Please check your input.",
        error.field,
      );
    }
    if (!response.ok)
      throw new ApiError(
        `API returned ${response.status}. Please check the backend.`,
      );
    const data: unknown = await response.json().catch(() => {
      throw new ApiError("The API returned invalid JSON.");
    });
    if (!validResponse(path, data))
      throw new ApiError(
        "The API response does not match the expected contract.",
      );
    return {
      data: data as T,
      mock: response.headers.get("X-SellSmart-Engine") === "fake",
    };
  } catch (error) {
    if (error instanceof ApiError) throw error;
    return {
      data: fallback(),
      mock: true,
      fallback: "Backend unavailable. Showing demo data, not engine results.",
    };
  }
}
export const getAdvice = (input: AdviceRequest) =>
  call<Advice>("/advise", () => demoAdvice(input), input);
export const getPlan = (input: PlanRequest) =>
  call<Plan>("/fpo/plan", () => demoPlan(input), input);
export const getBacktest = (crop: Crop) =>
  call<Backtest>(`/backtest?crop=${crop}`, () => ({
    ...(structuredClone(backtest) as Backtest),
    crop,
  }));
export const getForecast = (crop: Crop, mandi: string) =>
  call<Forecast>(
    `/forecast?crop=${crop}&mandi=${encodeURIComponent(mandi)}`,
    () => demoForecast(crop, mandi),
  );
export const getMandis = () =>
  call<Mandi[]>("/mandis", () => structuredClone(mandis) as Mandi[]);
export const getVillages = () =>
  call<Village[]>("/villages", () => structuredClone(villages));
export const getConfig = () =>
  call<Config>("/config", () => structuredClone(defaultConfig));
export const getQueries = () =>
  call<Query[]>("/queries", () => structuredClone(queries));
export const postMessage = (input: MessageRequest) =>
  call<MessageResponse>(
    "/message",
    () => ({
      reply: "The WhatsApp adapter is not connected in this frontend demo.",
      state: "awaiting_confirm",
      parsed: { crop: "onion", quantity_qtl: 10, village: "Niphad" },
    }),
    input,
  );
