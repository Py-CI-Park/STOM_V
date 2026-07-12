# Pending Approval Plan: STOM Dashboard Remodel 100% Replacement

Status: pending approval
Mode: RALPLAN deliberate consensus
User objective: develop `/ui/remodel/` until it fully replaces the current STOM dashboard, with systematic page-by-page visual verification and code verification, reaching 100% existing-dashboard parity and 100% standalone dashboard completeness.

## Consensus receipts

| Stage | Verdict | Artifact |
|---|---|---|
| Planner pass 1 | completed | `.gjc/_session-019f0846-48b0-7000-aba3-a901492312f0/plans/ralplan/019f0846-48b0-7000-aba3-a901492312f0/stage-01-planner.md` |
| Architect pass 1 | WATCH / COMMENT | `.gjc/_session-019f084d-488d-7000-a1a3-83362420c2cd/plans/ralplan/019f084d-488d-7000-a1a3-83362420c2cd/stage-01-architect.md` |
| Critic pass 1 | ITERATE | `.gjc/_session-019f0854-4ef1-7000-acac-baf0c8acaf9f/plans/ralplan/019f0854-4ef1-7000-acac-baf0c8acaf9f/stage-01-critic.md` |
| Planner revision pass 2 | revised | `.gjc/_session-019f0846-48b0-7000-aba3-a901492312f0/plans/ralplan/019f0846-48b0-7000-aba3-a901492312f0/stage-02-revision.md` |
| Architect pass 2 | CLEAR / APPROVE | `.gjc/_session-019f085a-a4a8-7000-8563-69a62c41c0b8/plans/ralplan/019f085a-a4a8-7000-8563-69a62c41c0b8/stage-02-architect.md` |
| Critic pass 2 | OKAY / APPROVE | `.gjc/_session-019f085e-c340-7000-a341-3eb113f6695e/plans/ralplan/019f085e-c340-7000-a341-3eb113f6695e/stage-02-critic.md` |
| Intent reconciliation | open-confirmations-pending | `.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/plans/ralplan/019f05e9-d676-7000-9c61-3c206a2d4031/stage-02-post-interview.md` |

## Current baseline

Current `/ui/remodel/` is a Phase A visual preview and partial live bridge. The detailed scorecard rates it around:

- Existing-dashboard parity: 55/100
- Standalone remodel completeness: 71/100

Largest gaps:

1. Backtest page is mostly static prototype instead of production `/bt/*` behavior.
2. Chart replay page is mostly static prototype instead of production `/sim/*` WS state machine.
3. Condition AI pages connect `/health`, `/status`, `/runs`, `/ws`, but many analysis, code, lab, workbench, and audit endpoints remain static.
4. Mock/preview panels are not consistently distinguished from real connected panels.
5. Full page-by-page E2E and visual verification is not yet in place.

## RALPLAN-DR summary

### Principles

1. Production behavior reuse first: remodel is shell, layout, routing, and design over the existing React/API/WS implementation.
2. One renderer, one production bundle path: no second live renderer and no stale remodel bundle drift.
3. Route isolation: `/ui/remodel/` owns its namespace and deep links; existing canonical routes remain stable controls.
4. Safety by construction: no hidden `final_approval`, live order, broker login, account, or account trading controls.
5. Evidence gates beat visual approval: no page reaches complete without functional E2E, visual capture, and source/DOM safety checks.

### Decision drivers

1. Backtest and chart replay parity require existing `/bt/*` and `/sim/*` state machines, not static remodel copies.
2. Route and bundle drift could create two dashboards with different behavior unless blocked by architecture gates.
3. Export/audit wording and hidden actions are safety-critical and need explicit source plus DOM guards.

### Chosen option

Use a hybrid remodel shell that mounts production React components/state machines and applies remodel design tokens/layout around them.

Rejected alternatives:

- Greenfield rewrite of the vanilla prototype: rejected because it duplicates mature production behavior and currently lacks most `/bt/*`, `/sim/*`, inspector, lab, audit, and analysis depth.
- iframe/embed of existing pages: rejected because it cannot satisfy standalone route ownership, deep-link behavior, accessibility, and complete replacement requirements.

## Non-negotiable gates

### Gate A — Remodel route namespace and deep-link behavior

- `/ui/remodel/` is the replacement candidate namespace.
- Remodel subpages must refresh in place under remodel namespace, for example `/ui/remodel/backtest`, `/ui/remodel/chart-replay`, `/ui/remodel/audit`, or equivalent hash/query scheme.
- Refreshing a remodel deep link must not escape to `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`, or bare `/ui/` unless the user explicitly clicks an external canonical-route link.
- Existing canonical routes remain preserved and tested.

### Gate B — Single build/bootstrap path and bundle drift guard

- `/ui/remodel/` must bootstrap the production React component graph or a shared entry that imports it.
- Vanilla `frontend/remodel/src/app.js` cannot remain an accepted production renderer; it may stay only as archived sample or clearly labeled preview fallback.
- A manifest/hash/build metadata guard must prove the remodel route uses the expected production bundle revision.
- Targeted tests must fail if remodel references stale standalone assets while production bundle files changed.

### Gate C — final_approval/export and audit safety

- `final_approval` remains human export approval only, never automatic export.
- Decision audit `/record_decision` remains append-only research governance and remains separate from export approval.
- `/ui/remodel/` must not introduce hidden WebSocket `final_approval` calls, automatic production export calls, broker login, live order, account balance, account trading, or account controls.
- Source and rendered DOM guards must search for forbidden controls and hidden handlers.

### Gate D — CSS token bridge and scoping

- Remodel styling must be a scoped token bridge over existing `styles.css`, not a parallel global theme.
- Remodel-specific selectors are scoped under a remodel root class/container.
- Existing route screenshots for `/ui/evolution`, `/ui/backtest`, and `/ui/chart-replay` are required before and after CSS integration.

### Gate E — E2E protection for routes, API, WS, audit, and safety

- Preserved route navigation and screenshots.
- Backtest E2E: `/bt/health`, strategies, validation, run, job status or `/bt/ws_job`, result, report, compare or overlay.
- Replay E2E: `/sim/health`, days, stocks, signals, `/sim/ws`, play, pause, seek, speed, stop.
- Condition E2E: `/ws`, run selection, generation inspector, code/diff/prompts/context, analysis, and backtest handoff.
- Audit E2E: `/decisions`, safe fixture append through `/record_decision` where configured, refresh, and hash/verified display when available.
- Safety E2E: no hidden live-order, broker, account, account-trading, or automatic-export controls in DOM or interaction paths.

## Implementation plan after approval

### Phase 0 — Baseline and acceptance matrix

- Freeze `docs/update_log/2026-06-27_dashboard_remodel_detailed_100_point_scorecard.md` as the acceptance matrix.
- Inventory every static `DATA.*`/mock panel in remodel.
- Capture current screenshots for `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`, and `/ui/remodel/`.
- Record route map and existing API contracts.

### Phase 1 — Architecture shell and bootstrap

- Add remodel namespace/deep-link handling without disturbing existing routes.
- Add shared production bootstrap for `/ui/remodel/`.
- Add bundle manifest/hash/build metadata guard.
- Add scoped CSS root and token bridge.
- Add visible live/preview/disabled/unavailable state model.

### Phase 2 — Backtest full parity

Replace static remodel backtest with production `BacktestTab` behavior.

Required behavior:

- `/bt/health`, `/bt/data_range`
- `/bt/strategies`, `/bt/strategy`
- `/bt/strategy/validate`, `/bt/strategy`, `/bt/strategy/delete`
- `/bt/variables`, `/bt/extract_vars`
- `/bt/legacy/self_vars`
- `/bt/backfinder/preflight`
- `/bt/run`, `/bt/jobs`, `/bt/job`, `/bt/ws_job`, `/bt/job/cancel`, `/bt/job/meta`
- `/bt/result`, `/bt/analysis/*`
- `/bt/compare`, `/bt/overlay`, `/bt/portfolio`, `/bt/report`, `/bt/evo_gens`

100% condition: no static job/result/analysis cards are accepted as complete.

### Phase 3 — Chart replay full parity

Replace static remodel replay with production `SimulationTab` behavior.

Required behavior:

- `/sim/health`
- `/sim/days`
- `/sim/demo`
- `/sim/stocks`
- `/sim/signals`
- WebSocket `/sim/ws`
- play, pause, resume, stop, speed, seek
- live/LWC/SVG chart engines
- split/overlay charts
- indicator toggles and overlays
- signal log, signal marker, auto-pause learning, variable watch, diagnostics

100% condition: no static candle/signal/playback mock is accepted as complete.

### Phase 4 — Condition AI pages full parity

Connect or reuse production panels for:

- `/status`, `/ws`, `/runs`, `/run_state`, `/generation_durations`, `/run_yearly`
- `/strategy_code`, `/strategy_diff`, `/prompts`, `/ai_context_pack`
- `/equity_curves`, `/equity_curve`, `/backtest_detail`, `/evolution_gui_parity`
- `/hall_of_fame`, `/reference_screenshots`
- `/autopsy`, `/selector_preview`, `/counterfactual`, `/freeze_mc`
- `/tmap_grid`, `/tmap_map`, `/edge_ratio`, `/feature_importance`, `/variable_correlation`

Pages covered:

- Condition AI overview
- Process
- History
- Lab
- Workbench
- Audit

### Phase 5 — Decision audit, approval, settings, and safety

- Connect `/decisions` and safe `/record_decision` fixture/guarded path.
- Keep decision audit separate from final export approval.
- Connect `/config/spec`, `/gpt_auth/status`, `/gpt_auth/test`.
- Add source and DOM safety guards for forbidden actions.
- Ensure all buttons either work, open the correct modal, submit through guarded API, or are disabled with explanation.

### Phase 6 — Verification and visual closure

Required verification after implementation:

- Unit tests for route namespace, preserved routes, data mappers, bundle guard, CSS scope, and safety guards.
- Integration tests for `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`, `/ui/remodel/`, remodel deep links, `/health`, `/bt/health`, `/sim/health`, and selected API fixtures.
- Browser E2E for condition inspector, backtest workflow, replay workflow, audit workflow, preserved route navigation, safety DOM scan.
- Visual captures for existing canonical routes and every remodel page/modal.
- Console/network verification: no 404 loops, WS storms, stale-bundle warnings, uncaught exceptions.

## Page-by-page completion checklist

| Page | 100% completion condition |
|---|---|
| Common shell | scoped remodel namespace, deep-link refresh, base URL, core/backtest/replay health, route boundary, safety footer, live/preview states |
| Condition AI | real run/gen status, inspector, code/diff/prompts/context, charts, HoF, approval status, no unlabeled mock data |
| Process | live phase/process status, `/pipeline_status`, `/ops_status`, logs/artifacts, node detail, error states |
| History | run archive, run detail, compare, lineage search, research records, backtest/result handoff |
| Lab | active/stalled runs, freeze verdict, edge ratio, feature importance, variable correlation, TMAP, wiki, AI context |
| Workbench | real candidates, deep analysis, evidence links, backtest handoff, audit handoff, review queue |
| Audit | decision ledger, append-only submit, freeze/regime/revival/portfolio evidence, export separation |
| Backtest | full production `BacktestTab` workflow and `/bt/*` API/WS coverage |
| Chart replay | full production `SimulationTab` workflow and `/sim/*` API/WS coverage |
| Settings | config spec, GPT auth status/test, theme/base URL persistence, safe loading/error states |

## Pre-mortem

1. Visual parity is declared while static backtest/replay mocks still exist. Prevention: no page passes without API/WS E2E.
2. `/ui/remodel/backtest` refresh redirects to `/ui/backtest` and masks namespace failure. Prevention: deep-link refresh gate.
3. Shared CSS makes existing `/ui/backtest` worse while remodel looks good. Prevention: preserved-route screenshot gate.
4. A hidden `final_approval` shortcut ships under remodel. Prevention: source/DOM/action safety guard.
5. Remodel uses an old bundle after production changes. Prevention: manifest/hash drift guard.

## Intent Reconciliation

Automated mode: no user questions were asked. The following open confirmations are carried to the pending approval gate:

1. Route promotion: `/ui/remodel/` remains the replacement candidate while `/ui/evolution`, `/ui/backtest`, and `/ui/chart-replay` remain preserved controls until every gate passes. Default-route promotion requires later explicit approval.
2. Architecture choice: use hybrid shell and production component reuse; do not continue a greenfield rewrite of the vanilla prototype as the production path.
3. Data usage: real-data verification may use fixture DBs or read-only references to existing `_database` data, but must not create operating DB writes or live-broker side effects.
4. Safety: no live order, broker login, account/account-trading, hidden automatic export, or hidden `final_approval` action is acceptable. Human export approval and decision audit remain separate.
5. Execution: this plan is pending approval only. Execution should proceed through an approved execution workflow after user approval.
6. Completeness: 100% means both existing-dashboard parity and standalone completeness: real API/WS behavior, no unlabeled static mocks, page-by-page screenshots, route/deep-link refresh, source/DOM safety checks, E2E interactions, and preserved-route controls.

Prior-context conflict check: no conflicting prior deep-interview spec was found under `.gjc/**/specs/*.md`. The plan aligns with project constraints in `AGENTS.md` around runtime safety, protected DB/runtime paths, and explicit gates.

## ADR

### Decision
Adopt the hybrid remodel-shell architecture for `/ui/remodel/`: reuse production React components, REST clients, WebSocket state machines, and FastAPI contracts; apply remodel route namespace, shell, layout, and scoped design tokens on top.

### Drivers
- Existing dashboard components are the executable specification for 100% parity.
- Static prototype rewrite cannot safely reproduce mature `/bt/*` and `/sim/*` behavior quickly.
- Safety and audit/export semantics must remain exactly controlled.
- Page-by-page visual and code verification must prove completion.

### Alternatives considered
- Greenfield rewrite of vanilla prototype: rejected due duplicated state machines and high parity risk.
- iframe/embed existing pages: rejected due weak standalone replacement, routing, accessibility, and state ownership.
- Keep current remodel as design-only: rejected because user requested full replacement.

### Why chosen
The hybrid shell is the only option that can realistically reach 100% parity while preserving existing routes and safety contracts.

### Consequences
- Implementation must manage route namespace, CSS scoping, and shared bootstrap carefully.
- Some static prototype code will be retired or demoted to preview-only.
- Verification workload is high but necessary.

### Follow-ups
- Approve execution via an execution workflow.
- Implement in bounded page/component slices.
- Maintain scorecard closure and screenshot evidence continuously.
