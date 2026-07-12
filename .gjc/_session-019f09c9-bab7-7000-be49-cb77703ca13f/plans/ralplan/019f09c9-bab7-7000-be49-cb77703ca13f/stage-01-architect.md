## Summary
G005 direct remodel deep links are substantially compliant: `/ui/remodel/condition`, `/process`, `/history`, `/lab`, `/workbench`, and `/audit` route into the remodel namespace shell while reusing the production React bundle and production condition/evolution pages. Browser and API artifacts show the six pages and 29 endpoint smoke checks returning HTTP 200, with no live-order/broker/account controls detected; recommendation is COMMENT because several handoff buttons leave the remodel namespace after the initial page load.

## Analysis
Stage 1 — Spec compliance:
- `ai_strategy_loop/dashboard/app.py:2703-2719` registers `/ui/remodel/{remodel_page}` and allowlists condition/evolution/process/history/records/lab/workbench/audit/verdict/backtest/chart-replay/simulation/settings, returning the remodel `index.html` instead of a prototype renderer.
- `ai_strategy_loop/dashboard/frontend/remodel/index.html:1-22` loads the production `/ui/bundle/app.js` and `/ui/bundle/stom-ui.js`, plus remodel CSS/bootstrap; it does not load the old static prototype renderer as the app body.
- `ai_strategy_loop/dashboard/frontend/remodel/remodel-bootstrap.js:1-77` seeds route state for `condition -> evolution/overview`, `process -> evolution/process`, `history -> evolution/records`, `lab -> evolution/lab`, `workbench -> evolution/workbench`, and `audit -> evolution/verdict`, and remaps History API navigation back to `/ui/remodel/*`.
- `ai_strategy_loop/dashboard/frontend/app.jsx:254-520` mounts the production shell and renders the production pages for process (`ProcessFlowPanel`), history (`ResearchRecordsPanel` + `ResearchIndexPage`), lab (`LabPage`), workbench (`ProPage`), audit (`VerdictPanel`), and the condition overview panels.
- `artifacts/ultragoal-g005-condition/browser-transcript.json:1-493` shows all six target URLs loaded with HTTP 200, active evolution subtabs matching the intended route, shared global shell visible, screenshots captured, and `forbiddenControls: 0`.
- `artifacts/ultragoal-g005-condition/api-smoke.json:1-38` shows `allOk: true` across 29 endpoints including health/status/runs/run_state/generation_durations/run_yearly/strategy_code/strategy_diff/prompts/ai_context_pack/equity/backtest/GUI parity/HoF/reference/autopsy/counterfactual/freeze/MC/TMAP/edge/feature/correlation/audit/process status.

Coverage evidence:
- Status/WS/runs: `conn-backend.jsx:1-150` provides same-origin default API base and `useBackend`; `app.py:2789-2791`, `app.py:2902-2910`, and `app.py:3381-3418` expose `/status`, `/runs`, and `/ws`; `app.jsx:64-126` consumes backend status, run list, and `/run_state` for archive browsing.
- Run state/durations/yearly: `app.py:2995-3019` exposes `/run_state`, `/generation_durations`, and `/run_yearly`; `chart-backtest-detail.jsx` consumes `/generation_durations` for period metadata and `rl-validation.jsx:112-141` consumes `/run_yearly` and `/equity_curve`.
- Code/diff/prompts/context: `code-viewer.jsx:1-260` fetches `/strategy_code`; `strategy-inspector.jsx:1-320` fetches `/strategy_diff` and `/prompts` and builds a safe AI context; `ai-context.jsx:1-130` consumes `/ai_context_pack` and surfaces forbidden actions.
- Equity/backtest detail and GUI parity: `chart-backtest-detail.jsx` consumes `/equity_curves` and `/backtest_detail`; `evolution-gui-parity-panel.jsx:1-143` consumes `/evolution_gui_parity` and renders the shared GUI parity section.
- HoF/reference: `chart-hall-of-fame.jsx:1-360` consumes `/hall_of_fame` and `/reference_screenshots`, preserving human/seed/AI benchmark fields and reference image gallery.
- Autopsy/counterfactual/freeze/MC/TMAP: `rl-validation.jsx:1-560` consumes `/autopsy`, `/counterfactual`, `/freeze_mc`, `/freeze_verdict`, `/ops_status`, `/tmap_map`, `/tmap_grid`, `/niche_compare`, `/pipeline_status`, and `/portfolio_sim` as read-only/advisory surfaces.
- Edge/feature/correlation: `rl-panel.jsx:1-269` owns the Lab tabs and wires `EdgeRatioPanel`, `FeatureImportancePanel`, and `/variable_correlation`; `analysis.jsx` fetches `/edge_ratio` and `/feature_importance`.
- Audit/handoff: `dashboard-pages.jsx:263-606` renders the append-only Decision Audit surface, separates REST `/record_decision` from WS `final_approval`, and labels final export approval as separate from the audit ledger.

Stage 2 — Architecture:
The strongest architectural choice is reuse: remodel deep links route into the existing production backend, production bundle, route contracts, owner inventory, and page components instead of maintaining a second implementation. Existing canonical `/ui/evolution/*`, `/ui/backtest`, and `/ui/chart-replay` routes remain registered in `app.py:2721-2766`, so canonical routes are preserved while remodel deep links are available.

The main maintainability risk is route-awareness split across `ui-contract.jsx`, `remodel-bootstrap.js`, and several hard-coded `window.location.href` handoffs. History API navigation is remodel-aware, but direct location assignment is not, creating inconsistent shell retention after handoff clicks.

Stage 3 — Code quality/security/performance:
No high-severity security issue was found. The review found no live order button, broker login, account trading control, or hidden export bypass in the target artifacts. Existing production export remains an explicit human approval dialog (`cards.jsx:196-272`) requiring names and exact `승인` text, while `app.py:3465-3491` ignores client-supplied export destination and uses the fixed production strategy DB path. Decision audit is append-only via `/record_decision`; mutable edit/delete controls were not observed.

## Root Cause
The non-blocking handoff issue comes from direct full-page navigation in nested production panels. `remodel-bootstrap.js` only patches `history.pushState` and `history.replaceState`; it cannot remap `window.location.href = ...`, so any hard-coded canonical href bypasses the remodel namespace shim.

## Findings
- MEDIUM — `ai_strategy_loop/dashboard/frontend/dashboard-pages.jsx:47`: `_dpNavigateToTab` assigns `window.location.href = dashboardPathFor("evolution", subtab)`, so Lab -> Workbench leaves `/ui/remodel/*` and loads canonical `/ui/evolution/*`. The same pattern appears in `research-records-panel.jsx:103` (`/ui/backtest`) and `rp-panel.jsx:79,162` (`/ui/`, `/ui/evolution/records`). Impact: direct remodel deep links pass, but handoff surfaces are not namespace-sticky. Fix: route through parent SPA navigation where available, or centralize a remodel-aware URL builder using `window.STOM_DASHBOARD_BASE_PATH` before assigning `location.href`.

## Recommendations
1. Make all handoff buttons namespace-aware: replace direct canonical `window.location.href` assignments with parent `onNavigate`/`syncBrowserRoute` callbacks or a shared helper that maps to `/ui/remodel/*` when `window.STOM_REMODEL_MODE` is true.
2. Add a focused browser smoke that starts at `/ui/remodel/lab`, clicks 상세 워크벤치, then verifies the path remains `/ui/remodel/workbench`; repeat for Workbench -> History and History/HoF -> Backtest handoffs.
3. Keep the current explicit approval/audit separation: no automatic export, no broker/account/live-order UI, and no mutable decision audit operations.

## Architectural Status
WATCH

## Code Review Recommendation
COMMENT

## Trade-offs
| Option | Pros | Cons |
|---|---|---|
| Keep canonical href handoffs | Legacy routes remain visibly preserved; no extra routing helper | Remodel users can unexpectedly exit the remodel shell after handoff clicks |
| Remodel-aware handoff helper | Keeps namespace parity and still preserves canonical routes for direct legacy entry | Requires touching all direct `location.href` handoffs and adding a focused click smoke |

## Commands
- No project-wide tests, lint, or formatters run, per assignment.
- Evidence gathered with read/search over the specified source files and browser/API artifacts.
- Persisted with `gjc ralplan --write --stage architect --stage_n 1 --artifact <inline markdown> --json`.
