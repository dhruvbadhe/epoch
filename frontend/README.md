# SahiDaam frontend

A responsive FPO operator dashboard for Maharashtra: **Advice**, **FPO Plan**, and **Evidence**. Built with Next.js App Router, TypeScript, Tailwind CSS, Recharts, and Lucide icons. All business API calls originate in client components. No server actions or database.

## Run

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The included `pnpm-lock.yaml` also supports `pnpm install` and `pnpm dev`. Node.js 20.9 or later is required.

## Backend handoff

Copy `.env.example` to `.env.local` and change:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK=false
```

Restart the dev server after changing environment variables. Enable CORS for `http://localhost:3000` in the backend. `lib/api.ts` covers `/advise`, `/fpo/plan`, `/backtest`, `/forecast`, `/mandis`, `/villages`, `/config`, `/queries`, and `/message` with the supplied API contract. HTTP errors and malformed responses display errors. Only connection failures and timeouts fall back to demo fixtures with a visible notice and mock badge. Requests time out after six seconds.

Development writes to `.next/`; production writes to `.next-production/`. Build cleanup is disabled because this workspace is under OneDrive, which can lock generated directories. Build manifests still point to the current generated assets.

## Demo behavior

Advice opens directly on a 20-quintal onion lot from Niphad. Info contains the seed-to-plant animation, live net market rankings, previous-day gross prices and seven previous calendar days of reported prices. Missing observations are shown explicitly; the API does not provide realised profit or collection history.

Scroll reveals, the Info growth timeline, hover feedback and tablet navigation retain the existing ivory/green palette. Reduced-motion users receive a static plant and the complete history table.

Live API mode is the default. Explicit mock mode or unreachable-backend fallback uses illustrative demo data. JSON fixtures are in `mock/`; `lib/demo.ts` derives responsive, **illustrative** advice and collective plans from those fixtures. It is a frontend demonstration, not a trained forecasting model or a replacement backend engine. The price cutoff is **31 August 2026**. The fixture self-check flags illustrate UI behavior; they are not measured validation results. The Evidence fixture keeps all unmeasured metrics `null`, rendered as “not enough data”.

Changes to freshness, cash deadlines, villages, closures, and assumptions affect the demo. FPO plans allocate urgently constrained lots first, enforce mandi/day capacity, split lots where needed, conserve quantity, and reconcile weighted truck shares. Baselines use each member’s own nearest available crop-trading mandi; FPO net uses the collection centre and shared trucks. Unplaced lots are explicit and have zero sale proceeds in the group total. CSV exports preserve units and price dates.

Assumptions are loaded from `/config`. The drawer sends only changed values with the contract’s nested `overrides` shape, with validation and reset controls. Evidence remains at default assumptions and displays a banner when overrides are active. Farmer queries refresh every ten seconds while the drawer is open. Language buttons change main Advice card labels and the API `lang` value. Copy reply only copies locally; the dashboard does not send WhatsApp messages.

## Verify

```bash
npm run typecheck
npm test
npm run build
```

`tests/demo.test.ts` checks deadline/freshness constraints, money reconciliation, closure exclusion, capacity limits, quantity conservation, baselines, truck cost splits, language output, and null evidence. `tests/browser-check.cjs` exercises the full UI against the running dev server using a local headless Chrome; adapt its executable path for other machines. Screenshots are written to the ignored `test-results/` folder.

`node tests/workspace-live.cjs` checks all four live tabs, the exact onion result, closure replanning, null evidence, network destinations, mobile layout and offline fallback. Screenshots are saved under `test-results/`.

Frontend changes are kept inside this directory. Backend and ML files remain under their respective team owners. Before sharing changes, synchronize with the team’s latest `main` and commit only owned files.
