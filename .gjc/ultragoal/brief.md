Approved plan: execute 100% STOM dashboard remodel replacement from pending approval artifact `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/plans/ralplan/019f05e9-d676-7000-9c61-3c206a2d4031/pending-approval.md`.

Global constraints:
- Worktree: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel`.
- Preserve existing routes `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay` until all gates pass.
- Build `/ui/remodel/` as full replacement candidate with remodel namespace/deep-link refresh and no route escape.
- Reuse production React components/API/WS state machines; do not continue static prototype as production renderer.
- No live orders, no broker login, no account/account-trading controls, no hidden automatic export, no hidden final_approval action.
- Use fixture DB or read-only DB verification only; no live broker or operating DB writes.
- Completion requires page-by-page code checks, API/WS checks, E2E checks, visual screenshots, source/DOM safety checks, and preserved-route regression checks.

@goal: Baseline acceptance matrix and route inventory
Freeze the approved scorecard and pending plan into the execution ledger, inventory every static/mock-backed remodel page section, map existing production components/API contracts, capture baseline screenshots for `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`, and `/ui/remodel/`, and add focused tests/docs needed to prevent route/safety regressions before implementation.

@goal: Remodel namespace shell and shared bootstrap
Convert `/ui/remodel/` from static prototype production path into a scoped remodel namespace shell that can mount the production React component graph, supports remodel deep links without route escape, includes bundle drift guard, scoped CSS token bridge, real/preview/disabled state labeling, and preserves canonical routes.

@goal: Backtest full parity
Replace the static remodel backtest page with production `BacktestTab` behavior and `/bt/*` API/WS coverage: strategy CRUD, validation, variables, self.vars/sweep, BackFinder, run/job lifecycle, `/bt/ws_job`, cancel/meta, result library, analysis, compare, overlay, portfolio, report, and evolution handoff.

@goal: Chart replay full parity
Replace the static remodel chart replay page with production `SimulationTab` behavior and `/sim/*` API/WS coverage: health, days, demo, stocks, strategies, signals, `/sim/ws`, playback controls, seek/speed, chart engines, split/overlay, indicators, signal log, auto-pause learning, variable watch, and diagnostics.

@goal: Condition AI pages full parity
Connect or reuse production condition AI pages for overview, process, history, lab, workbench, and audit analysis surfaces: status/ws/runs, run state, generation durations, strategy code/diff/prompts/context, equity/backtest detail, GUI parity, HoF/reference, autopsy, counterfactual, freeze/MC, TMAP, edge ratio, feature importance, variable correlation, and handoffs.

@goal: Decision audit settings and safety completion
Complete decision audit, approval, settings, and safety surfaces: `/decisions`, guarded `/record_decision`, final approval/export separation, `/config/spec`, `/gpt_auth/status`, `/gpt_auth/test`, source and DOM forbidden-action guards, and all buttons either working, disabled with explanation, or clearly preview-only.

@goal: Final page-by-page verification and completion evidence
Run full verification and evidence closure: unit/integration tests, browser E2E for condition/backtest/replay/audit, preserved route regression checks, source/DOM safety scans, visual captures for every remodel and canonical page/modal, console/network checks, quality gate review, and final 100/100 scorecard update.
