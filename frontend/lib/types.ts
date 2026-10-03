export type Crop = "onion" | "tomato" | "soybean";
export type Lang = "en" | "mr" | "hi";
export type LotCondition = boolean | 0 | 1 | 2 | null;
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};
export interface Config {
  transport: {
    rate_per_km_per_qtl: number;
    loading_per_qtl: number;
    road_factor: number;
  };
  spoilage_per_day: Record<Crop, number>;
  storage_cost_per_qtl_per_day: Record<Crop, number>;
  fees_per_qtl: number;
  hold_limit_days: {
    onion: { default: number; answers: Record<string, number> };
    soybean: { default: number; answers: Record<string, number> };
    tomato: { default: number; answers: number[] };
  };
  hold_rule: { min_gain_per_qtl: number; max_downside_per_qtl: number };
  horizons: number[];
  fpo: {
    collection_centre: { name: string; lat: number | null; lon: number | null };
    first_mile_per_qtl: number;
    truck_capacity_qtl: number;
    truck_fixed_cost: number;
    truck_per_km: number;
    mandi_cap_qtl_per_day: number;
  };
  units: { bag_kg: Record<Crop, number>; crate_kg: { tomato: number } };
  forecast: {
    target_match_window_days: number;
    min_reported_days: number | null;
    selfcheck_ratio_max: number;
    selfcheck_min_rows: number;
    coverage_widen_below: number;
    glut_ratio: number;
  };
  confidence: { stale_days: number; narrow_range_pct: number };
  parser: { village_match_threshold: number };
}
export type Overrides = DeepPartial<Config> | null;
export interface AdviceRequest {
  crop: Crop;
  quantity_qtl: number;
  village: string;
  lot_condition: LotCondition;
  cash_needed_in_days: 3 | 7 | null;
  blocked_mandis: string[];
  overrides: Overrides;
  lang: Lang;
  as_of_date?: string | null;
}
export interface Baseline {
  mandi: string;
  net: number;
}
export interface MandiOption {
  mandi: string;
  distance_km: number;
  sell_day: number;
  price_low: number;
  price_mid: number;
  price_high: number;
  transport_per_qtl: number;
  net_low: number;
  net_per_qtl: number;
  net_high: number;
  flags: ("stale" | "glut" | "falling")[];
}
export interface Advice {
  action: "hold" | "sell_now";
  days: number;
  mandi: string;
  net_per_qtl: number;
  net_low: number;
  net_high: number;
  baseline_today: Baseline;
  best_today: Baseline;
  gain_vs_baseline: number;
  gain_from_mandi: number;
  gain_from_waiting: number;
  confidence: "high" | "medium" | "low";
  break_even_price: number | null;
  hold_limit_days: number;
  hold_success_rate: number | null;
  prices_as_of: string;
  uses_baseline: boolean;
  assumptions_default: boolean;
  why: {
    price: number;
    spoilage_loss: number;
    transport: number;
    storage: number;
    fees: number;
  };
  options: MandiOption[];
  notes: string[];
  hold_suppressed?: boolean;
  answers_effect?: { changed: boolean; message: string | null } | null;
  freshness?: {
    estimated_window_days: number;
    answer: LotCondition;
    basis: string;
    reasons: string[];
    missing: string[];
    references: string[];
  };
  storage_tip: string | null;
  message: string;
}
export interface Lot {
  member: string;
  crop: Crop;
  quantity_qtl: number;
  village: string;
  lot_condition: LotCondition;
  cash_needed_in_days: 3 | 7 | null;
}
export interface PlanRequest {
  lots: Lot[];
  blocked_mandis: string[];
  mandi_cap_qtl_per_day: number | null;
  collection_centre: Config["fpo"]["collection_centre"] | string | null;
  overrides: Overrides;
}
export interface Assignment {
  member: string;
  crop: Crop;
  quantity_qtl: number;
  mandi: string;
  sell_day: number;
  price: number;
  first_mile: number;
  truck_share: number;
  storage: number;
  net_total: number;
  net_per_qtl: number;
  baseline_today: Baseline;
  reason: string;
  origin: string;
}
export interface Truck {
  mandi: string;
  sell_day: number;
  quantity_qtl: number;
  trips: number;
  cost: number;
}
export interface Plan {
  collection_centre: string;
  assignments: Assignment[];
  trucks: Truck[];
  total_net: number;
  baseline_total: number;
  gain_vs_baseline: number;
  unplaced: { member: string; quantity_qtl: number; reason: string }[];
  placed_qtl?: number;
  unplaced_qtl?: number;
  prices_as_of: string;
  assumptions_default: boolean;
}
export interface Backtest {
  crop: Crop;
  assumptions: "default";
  test_period: { start: string; end: string };
  cases_tested: number;
  cases_excluded_by_reason: Record<string, number>;
  avg_gain_per_qtl: number | null;
  median_gain_per_qtl: number | null;
  loss_share: number | null;
  worst_loss_per_qtl: number | null;
  hold_cases: number;
  hold_success_rate: number | null;
  hold_record?: { won: number; lost: number; unscored: number };
  gain_split?: {
    from_mandi_choice: number | null;
    from_holding: number | null;
  };
  prices_as_of?: string | null;
  ladder: { policy: string; avg_net: number | null }[];
  coverage: { horizon_days: number; coverage: number | null; n: number }[];
  selfcheck: {
    mandi: string;
    horizon_days: number;
    ratio: number | null;
    rows: number;
    passed: boolean;
  }[];
}
export interface Forecast {
  crop: Crop;
  mandi: string;
  prices_as_of: string;
  history: { date: string; price: number }[];
  forecast: {
    horizon_days: number;
    date: string;
    price_low: number;
    price_mid: number;
    price_high: number;
    uses_baseline: boolean;
  }[];
}
export interface Mandi {
  mandi: string;
  lat: number;
  lon: number;
  crops: Crop[];
}
export interface Village {
  village: string;
  name_mr: string;
  name_hi?: string;
  lat: number;
  lon: number;
}
export interface Query {
  time: string;
  sender: string;
  text: string;
  reply: string;
}
export interface MessageRequest {
  sender: string;
  text: string;
}
export interface MessageResponse {
  reply: string;
  state: "awaiting_confirm" | "awaiting_freshness" | "awaiting_cash" | "done";
  parsed: { crop: Crop; quantity_qtl: number; village: string };
}
export interface ApiResult<T> {
  data: T;
  mock: boolean;
  fallback?: string;
}
export interface Snapshot {
  crop: Crop;
  prices_as_of: string;
  snapshot_date: string | null;
  basis: string;
  reporting: {
    mandi: string;
    district: string | null;
    modal_price: number;
    min_price: number;
    max_price: number;
    previous_date: string | null;
    previous_modal_price: number | null;
    change: number | null;
  }[];
  highest_price: { mandi: string; modal_price: number } | null;
  lowest_price: { mandi: string; modal_price: number } | null;
  spread: number | null;
  not_reporting: { mandi: string; last_reported_date: string | null }[];
  series_dates: string[];
  series_7d: {
    mandi: string;
    points: { date: string; modal_price: number | null }[];
  }[];
  village: string | null;
  money_in_hand: {
    label: string;
    rows: {
      mandi: string;
      road_km: number;
      modal_price: number;
      transport_per_qtl: number;
      net_per_qtl: number;
    }[];
    highest: { mandi: string; net_per_qtl: number };
    assumptions: string;
  } | null;
}
export interface Weather {
  village: string;
  available: boolean;
  label: string;
  attribution: string;
  time?: string;
  temperature_c?: number;
  relative_humidity_pct?: number;
}
