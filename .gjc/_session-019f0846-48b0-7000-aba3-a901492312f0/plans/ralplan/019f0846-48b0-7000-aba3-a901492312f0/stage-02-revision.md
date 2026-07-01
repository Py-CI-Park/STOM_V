# RALPLAN Revision 2: Dashboard Remodel 100% Replacement Plan

## Summary
This revision incorporates Architect WATCH/COMMENT and Critic ITERATE feedback. The hybrid approach remains chosen, but the prior WATCH items are now non-negotiable architecture gates: remodel route namespace/deep-link behavior, single build/bootstrap path, final_approval/export safety semantics, CSS token bridge/scoping, and E2E gates protecting existing routes, APIs, WebSockets, audit, and safety.

Current evidence inspected in pass 1 remains the basis: the 2026-06-27 scorecard rates `/ui/remodel/` near 55/100 parity and 71/100 standalone completeness; the parity assessment says it is a Phase A visual preview with partial live bridge; the intake doc states production truth is `ai_strategy_loop/dashboard/frontend/` plus FastAPI routes in `app.py`, `backtest_api.py`, and `simulation_api.py`.

Chosen architecture: `/ui/remodel/` becomes a remodel shell that mounts production React components and state machines. The vanilla remodel renderer is retired or quarantined as preview-only. Existing `/ui/evolution`, `/ui/backtest`, and `/ui/chart-replay` stay preserved until all gates pass.

## RALPLAN-DR
### Principles
1. Production behavior reuse first: remodel is shell, layout, routing, and design over the existing React/API/WS implementation.
2. One renderer, one production bundle path: no second live renderer and no stale remodel bundle drift.
3. Route isolation: `/ui/remodel/` owns its namespace and deep links; existing canonical routes remain stable controls.
4. Safety by construction: no hidden `final_approval`, live order, broker login, account, or account trading controls.
5. Evidence gates beat visual approval: no page reaches complete without functional E2E, visual capture, and source/DOM safety checks.

### Top decision drivers
1. Backtest and chart replay parity require existing `/bt/*` and `/sim/*` state machines, not static remodel copies.
2. Route and bundle drift could create two dashboards with different behavior unless blocked by architecture gates.
3. Export/audit wording and hidden actions are safety-critical and need explicit source plus DOM guards.

### Options
- Option A, chosen: hybrid remodel shell mounting production components and shared bootstrap. Pros: fastest real parity, least duplication, reuses mature REST/WS behavior. Cons: needs route namespace decisions, scoped CSS bridge, and manifest/hash drift guard.
- Option B: rewrite the remodel prototype as a new production frontend. Pros: cleaner greenfield structure. Cons: repeats existing state machines and is invalidated by current static `DATA.*` gaps.
- Option C: iframe or embed existing pages. Pros: fast containment. Cons: not standalone, weak deep links, brittle focus/theme/state, and fails replacement completeness.

### Invalidation rationale
Option B is rejected because it discards the mature production dashboard while the prototype lacks most `/bt/*`, `/sim/*`, inspector, lab, audit, and analysis behavior. Option C is rejected because it hides parity rather than delivering `/ui/remodel/` as a true route-owned replacement. Option A dominates if and only if the gates below are enforced.

## Non-negotiable architecture gates

### Gate A: Remodel route namespace and deep-link behavior
- `/ui/remodel/` is the root namespace for the replacement candidate.
- Remodel subpages must refresh in place under the remodel namespace, for example `/ui/remodel/condition`, `/ui/remodel/process`, `/ui/remodel/history`, `/ui/remodel/lab`, `/ui/remodel/workbench`, `/ui/remodel/audit`, `/ui/remodel/backtest`, `/ui/remodel/chart-replay`, and `/ui/remodel/settings` or equivalent query/hash scheme.
- A refresh on a remodel deep link must not escape to `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`, or bare `/ui/` unless the user explicitly clicks an external canonical-route link.
- Existing canonical routes remain preserved and tested: `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`.
- Acceptance evidence: route tests plus browser refresh screenshots for every remodel deep link and the three preserved routes.

### Gate B: Single build/bootstrap path and bundle drift guard
- `/ui/remodel/` must bootstrap the same production React component graph used by the existing dashboard or a shared entry that imports it.
- The vanilla `remodel/src/app.js` renderer cannot remain an accepted production renderer. It may remain only as archived sample or preview fallback with visible preview labeling.
- A manifest/hash guard or equivalent must prove the remodel route uses the expected production bundle revision. Acceptable forms include checked asset manifest, bundle content hash, build metadata endpoint, or startup assertion logged/rendered in a diagnostics panel.
- CI or targeted test must fail if remodel references a stale standalone bundle while production bundle files changed.

### Gate C: final_approval/export and audit safety semantics
- `final_approval` remains the human export approval path only, never an automatic export path.
- Decision audit `/record_decision` remains append-only research governance and is separate from export approval.
- `/ui/remodel/` must not introduce hidden WebSocket `final_approval` calls, automatic production export calls, broker login, live order, account balance, account trading, or account controls.
- Source guards and rendered DOM guards must search for forbidden controls and hidden handlers. Any intentional mention must be explanatory safety text, not an actionable control.

### Gate D: CSS token bridge and scoping
- Remodel styling must be a scoped token bridge over existing `styles.css`, not a parallel theme that globally mutates canonical routes.
- Remodel-specific selectors are scoped under a remodel root class or route container.
- Existing route screenshots for `/ui/evolution`, `/ui/backtest`, and `/ui/chart-replay` are required before and after CSS integration.
- CSS changes fail if they alter canonical route layout beyond approved visual threshold.

### Gate E: E2E protection for routes, API, WS, audit, and safety
- E2E must cover preserved route navigation and screenshot capture.
- Backtest E2E must cover `/bt/health`, strategies, validation, run, job status or WS `/bt/ws_job`, result, report, compare or overlay.
- Replay E2E must cover `/sim/health`, days, stocks, signals, WS `/sim/ws`, play, pause, seek, speed, stop.
- Condition E2E must cover status WS `/ws`, run selection, generation inspector, code/diff/prompts/context, analysis, and backtest handoff.
- Audit E2E must cover `/decisions`, safe fixture append through `/record_decision` where configured, refresh, and hash/verified display when available.
- Safety E2E must assert no hidden live-order, broker, account, account-trading, or automatic-export controls in DOM or interaction paths.

## In scope / out of scope
### In scope
- `/ui/remodel/` common shell, condition AI, process, history, lab, workbench, audit, backtest, chart replay, and settings.
- Production component reuse from `app.jsx`, `ui-contract.jsx`, `conn-backend.jsx`, `dashboard-pages.jsx`, `panels*.jsx`, `phase-detail.jsx`, `chart*.jsx`, `research*.jsx`, `rl*.jsx`, `backtest.jsx`, `bt-tab-root.jsx`, `bt-tab-library.jsx`, `bt-tab-run.jsx`, `bt-result-area.jsx`, `bt-tab-analysis.jsx`, `simulation.jsx`, `sim-tab-root.jsx`, `sim-tab-controls.jsx`, `sim-chart-engines.jsx`, `sim-live-chart.jsx`, and `settings.jsx`.
- API parity against `app.py`, `backtest_api.py`, and `simulation_api.py`.
- Route, bundle, CSS, safety, E2E, and visual evidence.

### Out of scope and safety constraints
No live orders, no broker login, no account or account trading UI, no hidden automatic production export, no bypass of human approval, no mutable decision audit editing or deleting, no operating `_database` writes, no live broker wiring, and no removal or redirecting of preserved canonical routes before all gates pass.

## File-level changes
- `ai_strategy_loop/dashboard/app.py`: preserve static mount order with `/ui/remodel` before `/ui`; add remodel deep-link fallback only inside `/ui/remodel/*`; do not change preserved route handlers except tests.
- `frontend/ui-contract.jsx`: keep canonical contracts stable; add remodel route map or namespace helpers without changing existing canonical outputs.
- `frontend/app.jsx` and shared bootstrap: expose a route-aware production mount for remodel.
- `frontend/remodel/index.html`: become thin bootstrap to shared production renderer.
- `frontend/remodel/src/app.js`: retire from production path or mark preview-only; no accepted page may depend on unlabeled `DATA.*` mocks.
- `frontend/styles.css` and `frontend/remodel/styles/theme.css`: implement scoped remodel token bridge.
- Backtest modules: mount full `BacktestTab` and preserve `/bt/*` behavior.
- Simulation modules: mount full `SimulationTab` and preserve `/sim/*` behavior.
- Tests: add route refresh, preserved-route screenshots, bundle hash/manifest guard, source/DOM safety guard, API/WS E2E, and audit checks.

## Sequencing and dependencies
1. Baseline matrix: freeze the scorecard rows as acceptance items; capture current preserved routes and remodel preview; inventory mock-backed remodel panels.
2. Architecture gate setup: route namespace helpers, shared bootstrap decision, bundle manifest/hash guard, scoped CSS root, forbidden-action guard list.
3. Common shell: base URL, route boundary strip, core/backtest/replay health, REST/WS badges, run selector, theme, settings, safety footer, page status labels.
4. Backtest parity: replace static backtest with `BacktestTab`; verify CRUD, validate, variables, self.vars/sweep, BackFinder, run modes, job WS, cancel, metadata, results, charts, insights, MAE/MFE, orderflow, GUI parity, compare, overlay, portfolio, report, evo handoff.
5. Chart replay parity: replace static replay with `SimulationTab`; verify inventory, demo preset, stock search, strategies, signals, WS controls, shortcuts, chart engines, split/overlay, indicators, minimap, learning auto-pause, signal log, variable watch, diagnostics.
6. Condition pages: overview, process, history, lab, workbench, and audit use existing live/read-only APIs and panels; remove or badge mock sections.
7. Settings and modals: `/config/spec`, `/gpt_auth/status`, `/gpt_auth/test`, code/diff/prompts/context, approval dialog, and audit/export separation.
8. Completion lock: remove stale renderer from production path, run full verification, update evidence docs, then consider any default-route promotion.

## Page-by-page implementation plan
- Common shell: remodel namespace navigation, deep-link refresh, health badges for core/backtest/replay, safety footer, route boundary, live/archive run selector, generation/provider/timeframe/run_id, scoped theme.
- Condition AI: `/status`, `/ws`, `/runs`, generation table, active/best/winner, phase timeline, criteria, config, costs, equity/backtest detail, HoF, inspector, prompts, diff, context pack, approval/export status.
- Process: process flow, `/pipeline_status`, `/ops_status`, durations, artifacts, logs, node detail, unavailable/error states.
- History: `/runs`, `/run_state`, `/runs/compare`, research records/index, result detail, lineage search, backtest/result handoff.
- Lab: `/ops_status`, `/freeze_verdict`, `/edge_ratio`, `/feature_importance`, `/variable_correlation`, `/tmap_grid`, `/tmap_map`, validation/holdout, wiki, AI context.
- Workbench: HoF candidates, deep analysis, equity/IC/risk/heatmaps, evidence links, review queue, backtest handoff, audit handoff.
- Audit: `/decisions`, `/record_decision`, freeze/regime/revival/portfolio verdicts, append-only refresh, export separation.
- Backtest: full `BacktestTab`; static job/result/analysis cards are not acceptable.
- Chart replay: full `SimulationTab`; static candles/signals/playback are not acceptable.
- Settings: config spec, GPT auth status/test, theme/base URL persistence, safe loading and error states.

## Acceptance criteria
### 100/100 existing-dashboard parity
- Every scorecard item is present in `/ui/remodel/` or explicitly approved obsolete.
- `/ui/evolution`, `/ui/backtest`, and `/ui/chart-replay` still render, pass route tests, and have preserved-route screenshot checks.
- `/ui/remodel/` deep links refresh in the remodel namespace and do not route-escape unless intentionally clicked.
- Remodel uses the shared production renderer or shared bootstrap; bundle manifest/hash guard passes.
- Backtest covers CRUD, validation, variables, run/job lifecycle, WS progress, result analysis, compare, overlay, portfolio, report, and evo handoff.
- Replay covers inventory, selection, signals, WS playback, chart engines, overlays, indicators, signal log, diagnostics.
- Condition pages cover status, archive, inspector, code/diff/prompts/context, analysis, lab, workbench, audit, and approval separation.
- No accepted panel is backed by unlabeled static mock data.

### 100/100 standalone completeness
- Every button works, opens the right modal, submits through the correct guarded API, or is disabled with explanation.
- Loading, empty, disconnected, stale, error, and unavailable states are visible.
- CSS is remodel-scoped and does not regress canonical routes.
- Deep links and refresh work for every remodel page and modal entry point that claims routeability.
- Keyboard and basic accessibility work for navigation, modals, replay controls, and forms.
- Browser console has no unexpected 404 loops, WS storms, stale-bundle warnings, or uncaught exceptions.
- Source and DOM guards prove no hidden `final_approval`, automatic export, live order, broker, account, or account-trading controls.

## Verification plan
Planning stage runs no tests, builds, formatters, or source edits. Execution verification must include:
- Unit: route namespace and preserved canonical routes; deep-link refresh mapping; bundle manifest/hash guard; token-scope class guard; safety string/action guard.
- Integration: TestClient for `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`, `/ui/remodel/`, remodel deep links, `/health`, `/bt/health`, `/sim/health`; mocked `/bt/*`, `/sim/*`, condition analysis, and audit endpoints.
- E2E: preserved route screenshots; remodel deep-link refresh; condition inspector; backtest validate-run-job-result-report; replay date-stock-play-pause-seek-speed-stop; audit load/append/refresh; safety DOM scan.
- Visual: before/after captures for existing routes plus remodel common shell, condition, process, history, lab, workbench, audit, backtest, chart replay, settings, inspector, and approval modal.
- Observability: REST/WS badges, endpoint errors, WS close/reconnect, job logs, replay diagnostics, audit feedback, no console failures.
- Manual QA: walk every scorecard row and attach evidence.

## Risks and mitigations
- Route escape from remodel deep links: namespace tests and browser refresh E2E.
- Stale second renderer drifts from production: shared bootstrap plus manifest/hash guard.
- CSS bleeds into canonical routes: scoped root plus preserved-route screenshots.
- Hidden export or trading controls appear: source/DOM/interaction safety gates.
- Fixture gaps block E2E: deterministic fixtures or read-only DB override; never operating DB writes.

## Pre-mortem
1. Visual parity is declared while static backtest/replay mocks still exist. Prevention: no page passes without API/WS E2E.
2. `/ui/remodel/backtest` refresh redirects to `/ui/backtest` and masks namespace failure. Prevention: deep-link refresh gate.
3. Shared CSS makes existing `/ui/backtest` worse while remodel looks good. Prevention: preserved-route screenshot gate.
4. A hidden `final_approval` shortcut ships under remodel. Prevention: source/DOM/action safety guard.
5. Remodel uses an old bundle after production changes. Prevention: manifest/hash drift guard.

## Handoff guidance
Use `executor` only after approval for bounded implementation slices. Use `architect` to review gates A through E after shell/bootstrap work. Use `critic` for the final evidence matrix. Use `team` only for approved parallel backtest/replay/condition execution. Use `ultragoal` only if the migration becomes a long-running durable ledger.
