## Summary
Scoped read-only review covered only the five requested files under `C:/System_Trading/STOM/STOM_V.wt-dashboard-next/ai_strategy_loop/dashboard/frontend/`. Product status is CLEAR; architecture/code are WATCH only for a non-blocking dependency on externally defined Verdict shared globals. Recommendation: APPROVE; no blockers found in the scoped files.

## Analysis
Evidence-backed assessment:
- Stable route contract is preserved in `ui-contract.jsx`: all eight required keys are present at lines 7-14 (`evolution`, `backtest`, `simulation`, `records`, `lab`, `pro`, `verdict`, `process`), invalid stored values normalize back to `evolution` at lines 35-36, and Track Z/global publication is preserved at lines 39-48.
- Grouped IA/navigation is explicit: `DASHBOARD_TAB_GROUPS` maps run/verify/research/decision groups at `ui-contract.jsx` lines 17-22, while `app.jsx` consumes the same contract through direct imports at lines 32-33 and renders grouped tabs from `DASHBOARD_TAB_GROUPS` at lines 442-454.
- Direct page imports plus standalone globals are preserved: `app.jsx` directly imports `LabPage`, `ProPage`, `VerdictPanel`, and `ResearchIndexPage` at line 32; `dashboard-pages.jsx` imports its page dependencies at lines 17-21, supports standalone base URL/navigation fallback at lines 34-42, and publishes page globals plus dual-safe exports at lines 557-560.
- App-level backend, base URL, theme, run selector, start/stop, and approval dialog responsibilities remain at the App shell: `useBackend(baseUrl)` is at `app.jsx` line 60; theme/base controls render at lines 196-203; start/stop callbacks are lines 131-138; final approval sends `final_approval` at lines 140-148 and is wired through `ApprovalDialog` at lines 415-418; run selector state/use is lines 68-114 and UI wiring is lines 241-252 and 583-613.
- Simulation keep-alive is implemented: `simVisited` is initialized and latched at `app.jsx` lines 57-58, then the `SimulationTab` remains mounted and is hidden by display state at lines 263-269.
- Read-only process state and `/process_flow` compatibility are preserved: the process tab renders `ProcessFlowPanel` and an iframe to `baseUrl + "/process_flow"` at `app.jsx` lines 295-300. `phase-detail.jsx` derives flow state from `state.latest.current_step`, `recent_logs`, `phase_elapsed_sec`, `gen_started_at`, and `step_timings` at lines 679-688, computes display-only progress/timing rows at lines 708-716, and labels the source as `state.latest.current_step` / `step_timings` at lines 770-787. There are no writes or fetches in this flow panel.
- Shared UI primitives are presentation-only: `ui-state.jsx` defines render helpers at lines 16-79 and only publishes globals/exports at lines 82-85. Search across `ui-state.jsx` found no `fetch`, `send`, storage, document, or location side effects.
- No new package dependencies were found in the scoped files: search for non-relative import sources across the five exact files returned no matches; imports are relative local modules or absent.
- Records/Verdict remodel behavior is aligned within scope: `ResearchIndexPage` delegates Records rendering to `ResearchIndexPanel` at `dashboard-pages.jsx` lines 209-218 without adding mutation logic; Verdict reads `/decisions` at lines 285-288 and records decisions through `/record_decision` at lines 302-308, with user-facing copy explicitly stating append-only decision logging at lines 502-508 and 511.

## Root Cause
No blocking defect was found. The only residual risk is an order-sensitive shared-global contract in `VerdictPanel`: its summary subtab renders `window.VdtPromoteChecklist`, `window.VdtAlerts`, and `window.VdtSummaryLines` directly, relying on an external module to publish them before this component renders.

## Findings
- Severity: LOW. Reference: `C:/System_Trading/STOM/STOM_V.wt-dashboard-next/ai_strategy_loop/dashboard/frontend/dashboard-pages.jsx` lines 355-379. Impact: the Verdict summary subtab will throw if standalone page or bundle ordering ever stops defining `window.VdtPromoteChecklist`, `window.VdtAlerts`, or `window.VdtSummaryLines` first. This does not block the current scoped remodel because the file documents the ordering contract at lines 258-262, but it is a maintainability risk for Track Z/standalone compatibility. Fix suggestion: keep a smoke assertion for bundle order, or add the same narrow loading guard pattern used by `_DpLoading` when any required `window.Vdt*` component is absent.

## Recommendations
1. APPROVE the scoped remodel for Ultragoal checkpointing; no blockers were found in the five requested files.
2. Preserve the eight tab-key contract with tests around `normalizeDashboardTabKey` and `DASHBOARD_TAB_GROUPS` before future key/group changes.
3. Keep the Verdict shared-global order contract tested, or add a guarded fallback for the three `window.Vdt*` summary components to make standalone rendering resilient.
4. Keep `/process_flow` iframe compatibility until external consumers are confirmed migrated, since the native `ProcessFlowPanel` and iframe currently coexist without mutating process state.

## Architectural Status
WATCH

Product Status: CLEAR
Code Status: WATCH

## Code Review Recommendation
APPROVE

## Trade-offs
| Option | Benefit | Cost/Risk |
| --- | --- | --- |
| Current centralized `ui-contract.jsx` route table plus grouped tab arrays | Stable tab keys and flexible IA grouping without migrating storage keys | Future edits must keep route keys and group tabs synchronized |
| Direct page imports plus `Object.assign(window, ...)` globals | Supports both bundled SPA imports and standalone page mounting | Requires continued Track Z bundle discipline and order checks |
| Native `ProcessFlowPanel` plus `/process_flow` iframe | Modern in-app process view while preserving legacy iframe consumers | Duplicate process presentation, but state remains read-only |
| Shared Verdict summary components via `window.Vdt*` | Avoids duplicating checklist/alert/summary rendering | Order-sensitive; should be guarded or smoke-tested |
