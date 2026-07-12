// track-z-entry.pilot.js — Track Z FLAGGED bundle entry module (STOM_BUNDLE=1).
//
//   PR-1 began as a tiny pilot (phase-detail only). PR-3 grows it into the FULL app-graph
//   root: importing app.jsx pulls in the entire converted module graph (app.jsx imports every
//   cross-file component it bare-consumes; those transitively import their own deps). The
//   result is a real per-module-scope ESM bundle that builds to .track-z/app.pilot.js.
//
//   Mechanism (Driver-2): every module's React hooks resolve `react` -> src/react-shim.js
//     (aliased in build-app.mjs), which re-exports window.React. No React copy is bundled →
//     single React identity, zero require("react"), zero second-React sentinel.
//
//   Two jobs of this entry:
//     (1) SIDE-EFFECT IMPORTS — pull in the modules that are consumed ONLY via window.X (never
//         bare-imported into app.jsx's graph), so their top-level `Object.assign(window, {...})`
//         runs and republishes their symbols on window. Without these, window.LabPage /
//         window.useBackend / window.ResearchProPanel etc. would be undefined in the bundle.
//         Reachable-from-app (already in graph, no need to re-import): panels, run-compare,
//         engine, chart, hypothesis, table, cards, code-viewer, strategy-inspector, phase-detail,
//         settings, glossary, backtest, backtest-charts, simulation, simulation-charts,
//         evolution-analysis, research-lab, analysis. NOT reachable (imported here for effect):
//         connection, ai-context, research-pro, research-wiki, sim-live-chart, dashboard-pages.
//     (2) FROZEN republish — the bundled IIFE hides each file's top-level bare declarations, so
//         the HTML mount-by-name globals must be explicitly re-set on window: App, ErrorBoundary
//         (index.html), LabPage/ProPage/VerdictPanel (lab/pro/verdict.html). Defensively
//         window-consumed shared components (TRACK_Z_DEPS §4) are also re-published so standalone
//         pages don't silently break.
//
//   Bare stom-ui symbols (fmt*, STATUS_KR, _axisTicks, …) and bare connection helpers
//   (useBackend, DEFAULT_BASE, isDemoSource, livePanelPending) inside the modules resolve to the
//   GLOBAL object at runtime (esbuild leaves undeclared bare reads as global lookups), because
//   stom-ui.js and connection's Object.assign publish them on window before App renders. They are
//   NEVER import-converted (HARD RULE) — this entry only ensures their publishers run.

// --- (1) side-effect imports: modules consumed only via window.X (publish-on-import) ---
import "../../frontend/connection.jsx";   // window.useBackend / DEFAULT_BASE / isDemoSource / livePanelPending
import "../../frontend/ai-context.jsx";   // window.* AI context panel (consumes DemoBadge via window)
import "../../frontend/research-pro.jsx";  // window.ResearchProPanel / ResearchHeatmapPanel
import "../../frontend/research-wiki.jsx"; // window.ResearchWikiPanel
import "../../frontend/sim-live-chart.jsx";// window.SimLiveChart

// --- (2) named imports for explicit FROZEN + shared republish ---
import { App, ErrorBoundary } from "../../frontend/app.jsx";
import { LabPage, ProPage, VerdictPanel, ResearchIndexPage } from "../../frontend/dashboard-pages.jsx";
import { DashboardV4Shell } from "../../frontend/dashboard-v4-shell.jsx"; // window.DashboardV4Shell — v4.html mounts by name (opt-in V4 preview)
import { DemoBadge, LivePending, PhaseDetailPanel, PhaseTimeline, ProcessFlowPanel } from "../../frontend/phase-detail.jsx";
import { EnginePanel, LiveBacktestChart } from "../../frontend/engine.jsx";
import { ResearchLabPanel, VdtAlerts, VdtPromoteChecklist, VdtSummaryLines } from "../../frontend/research-lab.jsx";
import { BtResultArea } from "../../frontend/backtest-charts.jsx";
import { BtVarChips } from "../../frontend/backtest.jsx";
import { SimCandleChart, SimCandleChartLWC, SimCandleChartSVG } from "../../frontend/simulation-charts.jsx";

// FROZEN mount-by-name globals (HTML mounts) + the defensively window-consumed shared set.
Object.assign(window, {
  // FROZEN — index.html / lab.html / pro.html / verdict.html / v4.html mount these by name.
  App, ErrorBoundary, LabPage, ProPage, VerdictPanel, ResearchIndexPage, DashboardV4Shell,
  // TRACK_Z_DEPS §4 — shared components consumed via window.X across standalone pages.
  DemoBadge, LivePending, LiveBacktestChart, EnginePanel,
  PhaseDetailPanel, PhaseTimeline, ProcessFlowPanel,
  ResearchLabPanel, VdtAlerts, VdtPromoteChecklist, VdtSummaryLines,
  BtResultArea, BtVarChips,
  SimCandleChart, SimCandleChartLWC, SimCandleChartSVG,
});
