"use client";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowUpRight,
  BarChart3,
  ChevronRight,
  CircleHelp,
  Leaf,
  MapPin,
  MessageCircle,
  PanelLeftClose,
  PanelLeftOpen,
  SlidersHorizontal,
  Sprout,
  UsersRound,
} from "lucide-react";
import {
  getBacktest,
  getConfig,
  getMandis,
  getVillages,
  mockEnabled,
} from "@/lib/api";
import { defaultConfig } from "@/lib/demo";
import { dateLabel } from "@/lib/format";
import { useResource } from "@/lib/useResource";
import type { ApiResult, Lang, Overrides } from "@/lib/types";
import { AdviceTab } from "@/components/AdviceTab";
import { FpoPlanTab } from "@/components/FpoPlanTab";
import { EvidenceTab } from "@/components/EvidenceTab";
import { AssumptionsDrawer } from "@/components/AssumptionsDrawer";
import { QueriesDrawer } from "@/components/QueriesDrawer";
import { Drawer } from "@/components/Drawer";
import { Empty, ErrorState, Loading, SourceBadge } from "@/components/ui";
type Tab = "advice" | "fpo" | "evidence";
const tabs = [
  {
    id: "advice" as Tab,
    label: "Advice",
    icon: Sprout,
    description: "One harvest. A clearer next step.",
    title: "Make the most of your harvest.",
  },
  {
    id: "fpo" as Tab,
    label: "FPO Plan",
    icon: UsersRound,
    description: "Individual needs. Collective advantage.",
    title: "A smarter plan for the whole group.",
  },
  {
    id: "evidence" as Tab,
    label: "Evidence",
    icon: BarChart3,
    description: "Transparent numbers. Informed decisions.",
    title: "Good advice should show its work.",
  },
];
export default function Home() {
  const [tab, setTab] = useState<Tab>("advice");
  const [lang, setLang] = useState<Lang>("en");
  const [overrides, setOverrides] = useState<Overrides>(null);
  const [drawer, setDrawer] = useState<
    "assumptions" | "queries" | "help" | null
  >(null);
  const [mobileNav, setMobileNav] = useState(false);
  const [source, setSource] = useState(mockEnabled);
  const [asOf, setAsOf] = useState<string | null>(null);
  const villageResource = useResource("villages", getVillages);
  const mandiResource = useResource("mandis", getMandis);
  const configResource = useResource("config", getConfig);
  // "Prices as of" for every tab, from the backend (data/splits.json), before any tab has loaded
  const asOfResource = useResource("prices-as-of", () => getBacktest("onion"));
  const pricesAsOf = asOf ?? asOfResource.result?.data.prices_as_of ?? null;
  const config = configResource.result?.data ?? defaultConfig;
  const villages = villageResource.result?.data ?? [];
  const mandis = mandiResource.result?.data ?? [];
  const closeDrawer = useCallback(() => setDrawer(null), []);
  const onStatus = useCallback((result: ApiResult<unknown>) => {
    setSource(result.mock);
    const data = result.data as { prices_as_of?: string | null };
    if (data.prices_as_of) setAsOf(data.prices_as_of);
  }, []);
  const ignoreStatus = useCallback((_result: ApiResult<unknown>) => {}, []);
  useEffect(() => {
    if (!mobileNav) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileNav(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [mobileNav]);
  const active = tabs.find((t) => t.id === tab)!;
  const referenceError =
    villageResource.error ?? mandiResource.error ?? configResource.error;
  const referencesLoading =
    villageResource.loading || mandiResource.loading || configResource.loading;
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      {mobileNav && (
        <button
          className="nav-overlay"
          aria-label="Close navigation"
          onClick={() => setMobileNav(false)}
        />
      )}
      <aside className={`sidebar ${mobileNav ? "open" : ""}`}>
        <a className="brand" href="/" aria-label="SellSmart home">
          <span className="brand-icon">
            <Leaf size={25} />
          </span>
          <span>
            SellSmart<span className="brand-sub">A BETTER WAY TO MARKET</span>
          </span>
        </a>
        <div className="workspace-card">
          <span className="workspace-avatar">N</span>
          <div>
            <strong>Maharashtra FPO</strong>
            <span>
              <MapPin size={11} />
              Nashik district
            </span>
          </div>
          <span className="workspace-indicator" />
        </div>
        <span className="nav-caption">WORKSPACE</span>
        <nav aria-label="Main navigation">
          {tabs.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${tab === item.id ? "active" : ""}`}
              aria-current={tab === item.id ? "page" : undefined}
              onClick={() => {
                setTab(item.id);
                setMobileNav(false);
              }}
            >
              <item.icon size={19} />
              {item.label}
              {tab === item.id && <ChevronRight size={15} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-rule" />
        <span className="nav-caption">YOUR TOOLS</span>
        <button
          className="nav-item"
          onClick={() => {
            setDrawer("assumptions");
            setMobileNav(false);
          }}
        >
          <SlidersHorizontal size={18} />
          Assumptions{overrides && <span className="changed-dot" />}
        </button>
        <button
          className="nav-item"
          onClick={() => {
            setDrawer("queries");
            setMobileNav(false);
          }}
        >
          <MessageCircle size={18} />
          Farmer queries
          <ArrowUpRight size={14} />
        </button>
        <div className="sidebar-bottom">
          <div className="field-note">
            <span className="eyebrow">ROOTED IN YOUR REGION</span>
            <h3>
              Local harvests.
              <br />
              Better decisions.
            </h3>
            <svg viewBox="0 0 200 85" fill="none" aria-hidden="true">
              <path
                d="M-20 85C0 30 40 40 70 59s69 6 145-59M-20 98C4 41 47 53 76 66s75 1 137-38M-20 111C4 57 47 66 85 74s69 0 130-23M-20 124C10 69 55 79 93 82s74-4 121-12M125 7v44m0-26c-17 0-19-16-19-16 17 0 19 16 19 16Zm0 12c17 0 19-16 19-16-17 0-19 16-19 16Z"
                stroke="#779679"
                strokeWidth="1.2"
              />
            </svg>
            <span>Maharashtra · Onion, tomato & soybean</span>
          </div>
          <button
            className="nav-item help-button"
            onClick={() => setDrawer("help")}
          >
            <CircleHelp size={17} />
            How SellSmart works
          </button>
          <div className="operator">
            <span className="operator-avatar">FO</span>
            <div>
              <strong>FPO operator</strong>
              <span>Team Byte Me · EPOCH 1.0</span>
            </div>
            <span className="status-dot" />
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button menu-toggle"
              aria-label="Toggle navigation"
              onClick={() => setMobileNav((v) => !v)}
            >
              {mobileNav ? (
                <PanelLeftClose size={20} />
              ) : (
                <PanelLeftOpen size={20} />
              )}
            </button>
            <span className="desktop-breadcrumb">
              Workspace
              <ChevronRight size={13} />
            </span>
            <strong>{active.label}</strong>
          </div>
          <div className="topbar-right">
            <span className="region-label">
              <MapPin size={13} />
              Maharashtra
            </span>
            <div className="language-toggle" aria-label="Reply language">
              {(["en", "mr", "hi"] as Lang[]).map((l) => (
                <button
                  key={l}
                  aria-pressed={lang === l}
                  onClick={() => setLang(l)}
                >
                  {l === "en" ? "EN" : l === "mr" ? "मराठी" : "हिंदी"}
                </button>
              ))}
            </div>
            <span className="topbar-avatar">FO</span>
          </div>
        </header>
        <main id="main-content">
          <div className="page-heading">
            <div>
              <div className="page-eyebrow">
                <span className="status-dot" />
                {active.description}
              </div>
              <h1>{active.title}</h1>
              <p>
                {tab === "advice"
                  ? "Where to sell. When to sell. What’s left in hand."
                  : tab === "fpo"
                    ? "Put cash needs, freshness, and shared trucks into one practical plan."
                    : "Understand the backtest, the uncertainty, and the limits."}
              </p>
            </div>
            <div className="heading-status">
              <span className="date-badge">
                <span className="status-dot" />
                {pricesAsOf
                  ? `Prices as of ${dateLabel(pricesAsOf)}`
                  : "Prices as of — awaiting data"}
              </span>
              <div>
                <SourceBadge mock={source} />
                <span className="tiny">
                  {overrides ? "Custom assumptions" : "Default assumptions"}
                </span>
              </div>
            </div>
          </div>
          {referencesLoading ? (
            <Loading text="Opening your workspace…" />
          ) : referenceError ? (
            <ErrorState
              error={referenceError}
              retry={() => {
                villageResource.reload();
                mandiResource.reload();
                configResource.reload();
              }}
            />
          ) : !villages.length || !mandis.length ? (
            <Empty
              title="No markets or villages configured"
              text="Add the covered mandis and villages to the backend to start comparing harvest options."
            />
          ) : (
            <>
              <div hidden={tab !== "advice"}>
                <AdviceTab
                  active={tab === "advice"}
                  villages={villages}
                  lang={lang}
                  overrides={overrides}
                  onAssumptions={() => setDrawer("assumptions")}
                  onStatus={tab === "advice" ? onStatus : ignoreStatus}
                />
              </div>
              <div hidden={tab !== "fpo"}>
                <FpoPlanTab
                  mandis={mandis}
                  villages={villages}
                  config={config}
                  overrides={overrides}
                  onStatus={tab === "fpo" ? onStatus : ignoreStatus}
                />
              </div>
              <div hidden={tab !== "evidence"}>
                <EvidenceTab
                  config={config}
                  overrides={overrides}
                  onStatus={tab === "evidence" ? onStatus : ignoreStatus}
                />
              </div>
            </>
          )}
          <footer className="page-footer">
            <span>
              <Leaf size={13} />
              SellSmart <span className="footer-dot">·</span> From forecast to a
              next step.
            </span>
            <span>Built for the people behind the harvest.</span>
          </footer>
        </main>
      </div>
      {drawer === "assumptions" && (
        <AssumptionsDrawer
          defaults={config}
          current={overrides}
          onApply={setOverrides}
          onClose={closeDrawer}
        />
      )}
      {drawer === "queries" && <QueriesDrawer onClose={closeDrawer} />}
      {drawer === "help" && (
        <Drawer
          title="From a price to a next step."
          subtitle="Money-in-hand advice for Maharashtra farmers and FPO operators."
          onClose={closeDrawer}
        >
          <div className="help-content">
            <h3>1. Describe the harvest</h3>
            <p>
              Choose the crop, quantity, village, condition, and cash deadline.
              Advice compares eligible markets and selling days.
            </p>
            <h3>2. Understand what’s left</h3>
            <p>
              Forecast or reported price minus spoilage, transport, storage, and
              fees gives the money in hand per harvested quintal. Gains compare
              with the nearest mandi today.
            </p>
            <h3>3. Check before dispatch</h3>
            <p>
              Hold advice compares against the best net option today, and only
              passes when both the gain and downside checks clear. Confirm the
              reported price is above the break-even price before sending the
              crop.
            </p>
            <h3>4. Plan together</h3>
            <p>
              The FPO plan prioritises urgent members and freshness, then shares
              trucks from one collection centre. You can mark disruptions and
              see routes change.
            </p>
            <h3>5. Read the evidence</h3>
            <p>
              Backtest metrics are simulated at default assumptions. Unmeasured
              values say “Not enough data”. Mock data is illustrative, and
              storage guidance is general.
            </p>
            <div className="notice">
              Prices always carry a date. This prototype covers Maharashtra,
              onion, tomato, and soybean.
            </div>
          </div>
        </Drawer>
      )}
    </div>
  );
}
