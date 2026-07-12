# RALPLAN Planner Artifact: Dashboard Remodel as 100% STOM Dashboard Replacement

## Summary
Deliberate-mode plan for making `/ui/remodel/` a full replacement for the existing STOM dashboard. Inspected evidence: the 2026-06-27 scorecard rates remodel at about 55/100 existing-dashboard parity and 71/100 standalone completeness; the parity assessment says it is still a Phase A visual preview with partial live bridge; the intake doc says existing `ai_strategy_loop/dashboard/frontend/` and FastAPI routes are the production source of truth. Existing routes `/ui/evolution`, `/ui/backtest`, and `/ui/chart-replay` must remain preserved while `/ui/remodel/` is completed.

Chosen direction: hybrid remodel shell that reuses production React components, API clients, and WS state machines, with remodel design tokens layered on top. Do not rewrite mature backtest/replay/condition state machines from the vanilla prototype.

## RALPLAN-DR Summary
### Principles
1. Reuse production logic first; remodel is shell/layout/design, not a second dashboard engine.
2. No mock masquerade: live, fixture, disabled, or preview state must be visible.
3. Preserve existing routes until remodel proves full parity.
4. Keep safety boundaries explicit: research-only, human approval, append-only audit.
5. Completion requires functional code evidence plus page-by-page visual evidence.

### Top decision drivers
1. Parity risk is concentrated in backtest `/bt/*` and replay `/sim/*` depth.
2. Safety risk is concentrated around save/run/decision/export wording and hidden paths.
3. Verification must prove route preservation, endpoint consumption, interaction behavior, and visuals.

### Options
- Option A, chosen: mount production components/state machines inside a remodel shell. Pros: fastest real parity, least duplicated behavior, preserves existing API contracts. Cons: CSS token bridge and layout adaptation are required.
- Option B: rewrite the vanilla remodel prototype into a full production app. Pros: cleaner greenfield structure. Cons: highest risk; current `remodel/src/app.js` only bridges `/health`, `/status`, `/runs`, `/ws` and otherwise uses `DATA.*` mock state.
- Option C: iframe/embed existing pages. Pros: quick containment. Cons: not a standalone replacement; brittle routing/focus/theme; hides rather than solves parity.

### Invalidation rationale
Option B is rejected because the current prototype lacks most production backtest, replay, analysis, audit, and inspector behavior already implemented in the React dashboard. Option C is rejected because it cannot satisfy 100/100 standalone completeness or remodel route ownership. Option A dominates because the existing dashboard is the executable specification.

## In scope / out of scope
### In scope
- `/ui/remodel/` common shell plus condition AI, process, history, lab, workbench, audit, backtest, chart replay, and settings.
- Reuse of `app.jsx`, `ui-contract.jsx`, `conn-backend.jsx`, `dashboard-pages.jsx`, `panels*.jsx`, `phase-detail.jsx`, `chart*.jsx`, `research*.jsx`, `rl*.jsx`, `backtest.jsx`, `bt-tab-root.jsx`, `bt-tab-library.jsx`, `bt-tab-run.jsx`, `bt-result-area.jsx`, `bt-tab-analysis.jsx`, `simulation.jsx`, `sim-tab-root.jsx`, `sim-tab-controls.jsx`, `sim-chart-engines.jsx`, `sim-live-chart.jsx`, `settings.jsx`, and related modules.
- API parity against `app.py`, `backtest_api.py`, and `simulation_api.py`.
- Page-by-page scorecard closure and visual/code verification.

### Out of scope and safety constraints
No live orders, no broker login, no account/account trading, no account balance controls, no hidden automatic production export, no bypass of human approval, no mutable decision audit editing/deleting, no operating `_database` writes or live broker wiring, and no removal of `/ui/evolution`, `/ui/backtest`, or `/ui/chart-replay` during the migration.

## File-level changes
- `ai_strategy_loop/dashboard/frontend/ui-contract.jsx`: keep canonical route contracts; add remodel metadata only without changing existing route outputs.
- `ai_strategy_loop/dashboard/frontend/app.jsx`: extract/adapt global shell, route selection, run selector, theme, settings, error boundary, and tab orchestration for remodel mounting.
- `ai_strategy_loop/dashboard/frontend/styles.css` and `frontend/remodel/styles/theme.css`: build a token bridge; avoid parallel unrelated themes.
- `frontend/remodel/index.html`: remain `/ui/remodel/` entry; transition to production React bootstrap.
- `frontend/remodel/src/app.js` and `src/data.js`: retire mock renderers page by page or keep only as clearly labeled preview fallback.
- Condition pages: reuse existing status/config/analysis/research/audit panels and endpoints.
- Backtest: mount `BacktestTab` and retain `/bt/health`, `/bt/data_range`, `/bt/strategies`, `/bt/strategy`, `/bt/strategy/validate`, `/bt/strategy`, `/bt/strategy/delete`, `/bt/variables`, `/bt/extract_vars`, `/bt/legacy/self_vars`, `/bt/backfinder/preflight`, `/bt/run`, `/bt/jobs`, `/bt/job`, `/bt/ws_job`, `/bt/job/cancel`, `/bt/job/meta`, `/bt/result`, `/bt/analysis/*`, `/bt/compare`, `/bt/overlay`, `/bt/portfolio`, `/bt/report`, `/bt/evo_gens`.
- Chart replay: mount `SimulationTab` and retain `/sim/health`, `/sim/days`, `/sim/demo`, `/sim/stocks`, `/sim/signals`, WS `/sim/ws`.
- Backend: preserve `app.py` static mount order where `/ui/remodel` mounts before `/ui`; only add narrow backend fields if a verified missing contract blocks parity.
- Tests/evidence: extend dashboard route/unit tests, add API integration fixtures, add browser E2E and screenshot capture for every page and modal.

## Sequencing and dependencies
1. Baseline: freeze the 2026-06-27 scorecard as the acceptance matrix; record current screenshots and route map; identify every `DATA.*`/static remodel panel.
2. Common shell: production route contracts, base URL, REST/WS badges, run selector, theme, settings, safety footer, error boundary, page status labels.
3. Backtest parity: replace static backtest page with `BacktestTab`; verify CRUD, validate, variables, self.vars/sweep, BackFinder, run modes, job WS, cancel, metadata, result library, charts, insights, MAE/MFE, orderflow, GUI parity, compare, overlay, portfolio, report, evo handoff.
4. Chart replay parity: replace static replay page with `SimulationTab`; verify inventory, demo preset, stock search, strategies, signals, WS start/pause/resume/stop/speed/seek, shortcuts, chart engines, split/overlay, indicators, minimap, learning auto-pause, signal log, variable watch, diagnostics.
5. Condition AI pages: overview, process, history, lab, workbench, and audit use existing live/read-only APIs and panels; remove or badge mock-only sections.
6. Settings/modals: connect `/config/spec`, `/gpt_auth/status`, `/gpt_auth/test`, strategy code/diff/prompts/context, approval dialog, and audit separation.
7. Completion lock: quarantine obsolete mock code, run verification, update evidence docs, then consider route promotion only after 100/100 matrix closure.

## Page-by-page implementation plan
- Common shell: show core/backtest/replay health, backend URL, route boundary, safety footer, live/archive run selector, generation progress, provider/timeframe/run_id, route-safe navigation.
- Condition AI: real `/status`, `/ws`, `/runs`, generations, active/best/winner strategy, phase timeline, research criteria, config, cost, equity/backtest detail, HoF, inspector, prompts, diff, context pack, approval/export status.
- Process: real phase/process flow plus `/pipeline_status`, `/ops_status`, durations, artifacts, logs, node detail, and error states.
- History: `/runs`, `/run_state`, `/runs/compare`, research records/index, result detail, lineage/document search, backtest/result handoff.
- Lab: `/ops_status`, `/freeze_verdict`, `/edge_ratio`, `/feature_importance`, `/variable_correlation`, `/tmap_grid`, `/tmap_map`, validation/holdout, research wiki, AI context.
- Workbench: HoF candidates, candidate analysis, equity/IC/risk/heatmap charts, evidence links, review queue, backtest handoff, audit handoff.
- Audit: `/decisions`, `/record_decision`, `/freeze_verdict`, `/regime_report`, `/revival_registry`, `/portfolio_verdict`; submit is append-only and separate from export.
- Backtest: full `BacktestTab`; no static job/result/analysis cards accepted as complete.
- Chart replay: full `SimulationTab`; no static candle/signal/playback mocks accepted as complete.
- Settings: dynamic config spec, GPT auth status/test, theme/base URL persistence, safe loading/error states.

## Acceptance criteria
### 100/100 existing-dashboard parity
- Every scorecard item from the existing dashboard is present in `/ui/remodel/` or explicitly approved as obsolete.
- `/ui/evolution`, `/ui/backtest`, and `/ui/chart-replay` still render and pass route tests.
- `/ui/remodel/` consumes the same production REST/WS contracts for condition AI, backtest, and replay.
- Backtest covers CRUD, validation, variables, run/job lifecycle, WS progress, result analysis, compare, overlay, portfolio, report, and evo handoff.
- Replay covers inventory, selection, signals, WS playback, chart engines, overlays, indicators, signal log, and diagnostics.
- Condition pages cover status, archive, inspector, code/diff/prompts/context, analysis, lab, workbench, audit, and approval separation.
- No accepted panel is backed by unlabeled static mock data.

### 100/100 standalone completeness
- Every button works, opens the right modal, submits through the correct guarded API, or is disabled with explanation.
- Loading, empty, disconnected, stale, error, and unavailable states are visible.
- Deep links and refresh work for each remodel page/subpage.
- Visual density and hierarchy match the remodel design without breaking production usability.
- Keyboard/basic accessibility works for navigation, modals, replay controls, and forms.
- Browser console has no unexpected 404 loops, WS storms, or uncaught exceptions.
- Safety cues are visible across the app.

## Verification
Planning stage runs no tests/builds/formatters. Execution verification should include:
- Unit: route contract preservation, remodel mount, data mappers, pure chart/status helpers, safety-string/DOM guards.
- Integration: TestClient for `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`, `/ui/remodel/`, `/health`, `/bt/health`, `/sim/health`; mocked `/bt/*`, `/sim/*`, condition analysis, and audit endpoints.
- E2E: shell navigation/settings/inspector/approval; condition run/gen inspector and backtest handoff; backtest validate-run-job-result-report; replay date-stock-play-pause-seek-speed-signal-stop; audit load/submit/refresh in safe fixture mode.
- Visual: screenshots for existing three routes and remodel common shell, condition AI, process, history, lab, workbench, audit, backtest, chart replay, settings, inspector, approval modal.
- Observability/logging: REST/WS badges, endpoint errors, WS close/reconnect, job log tail, replay diagnostics, audit feedback, no console failures.
- Manual QA: walk every scorecard row; confirm safety/non-goals in rendered UI, DOM/source search, and docs.

## Risks and mitigations
- Visual remodel breaks production behavior: mount production components first, style second, and keep old routes as controls.
- Mock data remains unnoticed: tests fail accepted panels that still depend on `DATA.*` without preview badges.
- Safety boundary blurs: source/DOM scans plus explicit approval/export/audit review.
- Fixture DB gaps block E2E: use deterministic fixtures or read-only DB overrides; never create operating DB writes.
- Premature route promotion: require completed acceptance matrix and screenshots before default-route changes.

## Pre-mortem
1. Visual parity is declared while backtest WS/result/report and replay WS controls are still static. Prevention: functional E2E gates each page score.
2. Remodel route works but existing routes regress from shared CSS or route changes. Prevention: route tests and screenshot controls for `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay` every pass.
3. A convenience shortcut creates hidden export or trading-adjacent UI. Prevention: safety scans, DOM assertions, and no broker/account/live-order scope.

## Handoff guidance
Use `executor` for approved page/component implementation slices. Use `architect` after the common shell and before promotion. Use `critic` for the final evidence matrix. Use `team` only for approved parallel execution across backtest, replay, and condition pages. Use `ultragoal` only if this becomes a longer durable migration ledger.
