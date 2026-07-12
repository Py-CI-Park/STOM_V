# STOM dashboard remodel 100-point completion plan

## Summary
Baseline from inspected evidence is not 100: visual 71.5, structure 89.9, function 79.8, corrected 79.6. Main gaps: live backend values overwrite zip reference fixture values, and Backtest 77.4 plus Chart Replay 76.0 are visually present but too static versus production `/bt/*` and `/sim/*` depth. Current remodel entry is static: `index.html` loads `theme.css`, `src/data.js`, `src/app.js`; `app.js` renders 8 routes, maps `/health`, `/status`, `/runs`, `/ws`, and has safety footer and modals. Production frontend already has BacktestTab and SimulationTab consuming `/bt/*` and `/sim/*`.

## RALPLAN-DR
Principles:
1. Zip visual structure is source of truth.
2. Production function depth must survive, especially `/bt/*` and `/sim/*`.
3. `?demo=reference` fixture mode is mandatory for scoring.
4. Safety gates are hard blockers: Human Approval Gate, Append-Only Audit, research/local-only.
5. Evidence gates decide completion, not route or function presence.

Decision drivers:
1. 8-page capture parity at 1920x1080.
2. Backtest and replay production parity.
3. Strict no-live-trading safety contract.

Options:
A. Production React graph plus remodel skin. Pros: fastest functional depth, established APIs. Cons: already failed visual/user expectation, hard to match zip DOM. Invalidate unless quick proof reaches every page visual >=95 and average >=97 without function loss.
B. Zip-first shell plus production adapters/transplants. Pros: best visual alignment, deterministic fixture scoring, restores `/bt/*` and `/sim/*` via proven contracts. Cons: adapter complexity and `app.js` growth risk. Invalidate if Backtest/Replay require full duplicated state machines or if two visual tuning passes leave any page <95.
C. React rebuild from zip spec. Pros: long-term maintainability. Cons: too broad now. Use only if B invalidates.
Recommended: B, because it fixes the exact failures: fixture instability, static Backtest/Replay, and prior scoring confusion.

## In scope / out of scope
In scope: reference fixture mode; zip shell preservation; selector/adapters for reference, fallback, live; six condition-suite pages; real Backtest `/bt/*`; real Replay `/sim/*`; capture scoring gate; focused tests and evidence.
Out of scope: live order, broker login, account trading, account balance, hidden or automatic production export, mutable audit edit/delete, broad framework rewrite, unrelated desktop/trade/V3K changes.

## File-level changes
- `remodel/index.html`: keep static shell, update cache/version only if needed.
- `remodel/src/app.js`: add mode-aware routing and selectors; stop live data from mutating reference captures; adapt or mount production Backtest/Replay behavior.
- `remodel/src/data.js` and `data/stom-dummy-data.json`: freeze reference values for shell, rows, ledgers, candidates, backtest demo job, replay session.
- `remodel/styles/theme.css`: tune zip layout and isolate obsolete production-skin conflicts.
- Reuse production references: `frontend/bt-tab-root.jsx`, `bt-tab-run.jsx`, `bt-tab-library.jsx`, `bt-result-area.jsx`, `bt-tab-analysis.jsx`, `sim-tab-root.jsx`, `sim-tab-controls.jsx`, `sim-tab-panels.jsx`, `simulation-charts.jsx`.
- Backend only if contract gaps appear: `backtest_api.py`, `simulation_api.py`, `app.py`.
- Tests/evidence: remodel static contract tests, browser capture tooling, visual score JSON/contact sheet generator.

## Sequencing and dependencies
1. Baseline freeze: lock page IDs `01_condition_ai_overview` through `08_chart_replay`, current scorecard, route list, viewport, artifact paths.
2. Reference fixture mode: add `?demo=reference`; freeze backend URL, REST/WS, run status, Gen 137 style shell, progress, rows, logs, audit ledger, backtest and replay fixtures; live mode remains separate.
3. Selector seam: route all renderers through mode-aware selectors; normalize API responses; visible fallback/error states.
4. Six condition pages: condition, process, history, lab, workbench, audit reach visual/function checklist without randomness.
5. Backtest parity: wire zip panels to `/bt/health`, strategies, strategy get/save/delete, validate, extract vars, data range, run, jobs, job, cancel, ws_job, result, montecarlo, report, compare, overlay, evo_gens, portfolio, backfinder.
6. Replay parity: wire zip panels to `/sim/health`, days, demo, stocks, signals, ws plus `/bt/strategies`; preserve play/pause/resume/seek/speed/stop.
7. Capture gate: rebuild 8 current captures, diffs, contact sheet, detailed scorecard, forbidden scan.
8. Verification/evidence: focused unit, API/integration, browser/e2e, visual regression, artifact manifest.

## Story breakdown for ultragoal
Epic 1 Fixture and scoring: mode detection; stable fixture data; no live fetch in reference; capture/score artifact generator.
Epic 2 App seams: selectors per page; backend adapters; stable route aliases; honest connected/fallback states.
Epic 3 Condition suite: condition overview, process, history, lab, workbench, audit parity; modals and safety footer invariants.
Epic 4 Backtest: strategy library, dual editor, validation/vars, run/job/WS/cancel, result/analysis/report, compare/overlay/portfolio/evo.
Epic 5 Replay: health/day/stock/preset, strategy selectors, signal overlay, WS replay, chart modes, indicators, signal log.
Epic 6 Safety/evidence: forbidden-control scan, tests, screenshots, score JSON, contact sheet, API/WS transcript summary.

## Page-by-page checklist
Condition: zip topbar/tabs/3-column layout/KPI/generation table/winner/inspector; live status, active strategy, charts, modals; fixture/live separation; safety footer; score >=95.
Process: selector/menu/governance side, flow map, logs, catalog, boundary contract, metadata; fixture logs; local research-only cues; score >=95.
History: risk/PnL, lineage, summary KPIs, run archive, records, ResultDetail, compare; `/runs` mapping; approval-gated export wording; score >=95.
Lab: run sidebar, stall warning, queue, freeze summary, heatmap, importance, correlation, holdout, combos, context pack; no advice/export bypass; score >=95.
Workbench: global state, candidate strip, Hall of Fame, monthly heatmap, detail charts, handoff, review queue; no approval/export authority; score >=95.
Audit: append-only banner, checklist, OOS, evidence links, decision form, ledger, audit metadata; no edit/delete; export approval separate; score >=95.
Backtest: zip layout plus real `/bt/*`: strategy choose/edit/validate/save/delete, run/progress/cancel/logs, result, WFO/sweep, report, compare, overlay, portfolio, evo result; research-only labels; visual and functional >=95.
Chart Replay: source/day/stock/strategy/agg, preset, playback, chart mode/layout/engine/indicators, charts, signal log, learning/watch, minimap, WS state; real `/sim/*`; historical replay only; visual and functional >=95.

## Acceptance criteria
Visual: all 8 pages captured at 1920x1080 in reference mode; every `weightedVisualParityScore >=95`; average `weightedVisualParityScore >=97`; every `totalCorrectedScore >=95`; average `totalCorrectedScore >=97`; contact sheet, diffs, JSON reports exist.
Functional: all tabs and subtabs render; global shell visible; settings, strategy inspector, Human Approval dialogs open; audit has append-only ledger/form; Backtest has live `/bt/*` edit/run/progress/result/analysis/report/library; Replay has live `/sim/*` controls/chart/signal log/WS status; API failures are visible, not fake success.
Safety: zero forbidden controls or handlers for live order, broker login, account trading/balance/connect, hidden export, automatic production export, audit edit/delete. Human Approval Gate, Append-Only Audit, research-only/local-only remain visible. Final export approval stays separate from Decision Audit.
API/WS: evidence for `/health`, `/status`, `/runs`, `/ws`, required `/bt/*`, required `/sim/*`. WS errors recover visibly.
Browser captures: 8 routes plus modal states; no uncaught console errors on smoke path; manifest records route, viewport, mode, screenshot, timestamp.

## Verification plan
Unit/static: remodel static and baseline contract tests; route mapping; fixture immutability; forbidden scan; selector modes.
Integration/API: core dashboard, `/bt/*` job/result/report/compare paths, `/sim/*` days/stocks/signals/ws paths using fixtures or safe local data.
Browser/e2e: 8 routes, shell, tabs, page landmarks, modals, Backtest demo/reference controls, Replay demo/reference controls, no forbidden controls.
Visual regression: current captures, diffs, contact sheet, detailed scorecard; hard fail below thresholds.
Observability artifacts: score JSON, visual report JSON, contact sheet, 8 screenshots, 8 diffs, API/WS summary, forbidden scan, focused test outputs.

## Deliberate pre-mortem
1. Fixture mode masks live regressions. Mitigate with separate selectors and required live API/WS smoke evidence.
2. Backtest/Replay remain shallow static clones. Mitigate by treating them as high-risk epics and reusing production contracts; require functional >=95.
3. Safety weakened by run/export controls. Mitigate with hard forbidden scan, explicit research-only wording, Human Approval Gate, and no broker/account/live handlers.
4. Visual scores fluctuate. Mitigate by freezing reference values, disabling live refresh in reference mode, fixing viewport/theme/scroll, and removing render randomness.

## Handoff
After approval use ultragoal for durable checkpoints. Use executor only for bounded slices: fixture mode, selectors, Backtest adapter, Replay adapter, capture gate, tests. Use architect to review adapter boundaries, critic to review gates before execution, and team only if parallel approved execution is desired.
