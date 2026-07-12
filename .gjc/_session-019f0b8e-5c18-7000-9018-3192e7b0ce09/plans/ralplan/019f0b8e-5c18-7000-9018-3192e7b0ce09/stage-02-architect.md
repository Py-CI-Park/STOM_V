## Summary
Revision 2 is architecturally sound and now incorporates the prior Architect and Critic amendments as executable plan content rather than reviewer side notes. The zip-first static-shell path remains the right choice for the inspected failure mode, and execution can proceed without architectural guessing if the plan invalidation gates are honored.

## Analysis
Evidence inspected:
- Revised plan: `.gjc/_session-019f0b7b-b0a1-7000-9f2d-80757688fa91/plans/ralplan/019f0b7b-b0a1-7000-9f2d-80757688fa91/stage-02-revision.md`.
- Prior Architect and Critic artifacts: `.gjc/_session-019f0b80-aa33-7000-b51f-3f9d297bb8d5/.../stage-01-architect.md` and `.gjc/_session-019f0b87-ad60-7000-aa70-05c7f62199be/.../stage-01-critic.md` requested an explicit adapter seam, fail-closed mode matrix, `/bt/*` and `/sim/*` evidence matrices, manifest schema, stronger gates, and local-research-vs-safety-prohibited mutation wording.
- Static shell evidence: `ai_strategy_loop/dashboard/frontend/remodel/index.html` loads only `styles/theme.css`, `src/data.js`, and `src/app.js`; `remodel/docs/ARCHITECTURE.md` describes a no-build static SPA where `src/app.js` renders from `window.STOM_DATA` and production migration replaces static data with REST hooks and a WS stream store.
- Current defect evidence: `artifacts/runtime/zip-parity-compare/detailed-scorecard.json` records visual 71.5 and corrected total 79.6, with Backtest 77.4 and Chart Replay 76.0; it attributes deltas to live backend state overwriting fixtures and shallow static Backtest or Replay depth.
- Current reference-mode risk evidence: `remodel/src/app.js` reads and writes `localStorage`, fetches `/health`, `/status`, and `/runs`, opens `/ws`, schedules reconnects, and uses `Math.random()` in History lineage text.
- Backend contract evidence: `app.py` includes the backtest and simulation routers and exposes `/health`, `/status`, `/runs`, and `/ws`; `backtest_api.py` exposes the full `/bt/*` surface through health, strategy CRUD, variable and extract and self-vars and backfinder, data range, run and jobs and job and cancel and meta, result and evo, analysis routes, compare, overlay, portfolio, report, and `/bt/ws_job`; `simulation_api.py` exposes `/sim/health`, `/sim/days`, `/sim/demo`, `/sim/stocks`, `/sim/signals`, and `/sim/ws`.
- Production frontend evidence: `bt-tab-root.jsx`, `bt-tab-run.jsx`, `bt-tab-library.jsx`, `bt-result-area.jsx`, and `bt-tab-analysis.jsx` consume the backtest routes including WS and poll fallback, CRUD, analysis, compare, overlay, portfolio, report, and evo generation paths. `sim-tab-root.jsx` consumes `/sim/*`, `/bt/strategies`, and implements `start/pause/resume/speed/seek/stop` plus handling for `meta/bars/history/done/error`.
- Safety source: `remodel/CODEX_AGENT_BRIEF.md` forbids live order, broker login, account trading or balance controls, automatic or hidden production export, and mutable decision-audit editing or deleting, while requiring research-only wording, Human Approval Gate, Append-Only Audit, and final export separation.

Spec compliance against the requested pass-2 focus:
1. Bounded adapter seam and invalidation triggers: adequate. The revised plan selects a static zip render target, permits split vanilla modules, requires a mode gate before side effects, pure view-model adapters, and small imperative controllers, treats React production files as contract references rather than default imports, forbids wholesale production state-machine reimplementation, and gives concrete invalidation triggers for controller scope, Backtest or Replay duplication, visual failure, and unprovable endpoint matrices.
2. Fail-closed reference, demo, and live matrix: adequate. `reference` forbids REST, WS, reconnect or poll timers, randomness, drifting time, localStorage writes and base URL state, and real mutations; `demo` is fixture and bannered; `live` is the only mode allowed to use real REST or WS and local research mutations with visible errors instead of fake success.
3. `/bt/*` endpoint-action-evidence matrix: adequate and complete against the inspected `backtest_router` surface. It includes CRUD, validation, variable extraction, legacy self-vars, BackFinder preflight, data range, run/jobs/job/cancel/meta, WS job progress, job and run/gen result loads, evo generation selection, all analysis endpoints, compare, overlay, portfolio, and report behavior, with reference no-network proof and live API evidence requirements.
4. `/sim/*` endpoint-action-WS matrix: adequate and complete against the inspected simulation surface. It includes health, days, demo presets, stocks, `/bt/strategies` for replay selectors, signals, and `/sim/ws`, and it specifies the client actions and server messages that must be transcript-proven, including seek and history replacement, forced error or error display, cleanup, and recovery or new session.
5. Artifact manifest schema: adequate. It ties run, worktree, commit, time, mode, viewport, and thresholds to per-page screenshot, diff, visual, corrected, structure, and function scores, console and network checks, modal coverage, API evidence IDs, WS transcript IDs, forbidden scan ID, pass or fail, and timestamps, with global API, WS, and scan artifact arrays and a no-100-claim rule.
6. Strengthened pre-mortem and verification gates: adequate. The plan now names fixture masking, adapter duplication, endpoint omission, WS flakiness, safety regression, score inflation, and local mutation confusion as gates, and blocks completion wording until manifest thresholds, console and network checks, modal coverage, endpoint evidence, transcripts, and forbidden scans pass.
7. Safety distinction: adequate. The plan distinguishes local research and backtest mutations allowed only in live mode from always-prohibited broker, account, live-order, export, and audit-mutation controls, requires confirmations for destructive local research actions, keeps reference mutations inert, and keeps final strategy export separate behind Human Approval Gate.

The only residual watchpoint is execution discipline, not plan insufficiency: the core `/health`, `/status`, `/runs`, and `/ws` evidence should remain captured in the manifest because the shell and six non-Backtest or Replay pages depend on them. The revised plan already supports this through the mode matrix, page checklist, and integration/API verification line, so no revision is required.

## Root Cause
The root defect is a mode-boundary and source-of-truth mismatch: production React preserved function but missed the zip and capture visual target, while the static zip shell preserved visual structure but lost production Backtest or Replay depth and allowed live state to contaminate reference captures. Revision 2 fixes the planning root cause by making reference mode fail-closed, restoring production depth through endpoint contracts instead of mocks, and making completion manifest-backed.

## Findings
No blocking or revision-required findings.

Non-blocking watchpoint, LOW: During execution, keep the core dashboard REST and WS evidence for `/health`, `/status`, `/runs`, and `/ws` correlated in the manifest alongside the explicit `/bt/*` and `/sim/*` matrices. This is already implied by the revised plan mode matrix, page checklist, and integration/API verification scope, so it does not block approval.

## Recommendations
1. Approve Revision 2 for execution after the normal user approval boundary; do not reopen planning unless an invalidation trigger fires.
2. Treat the adapter seam as a checkpoint: mode gate first, pure adapters second, bounded controllers third; re-plan Option C only if the controllers become a duplicated production frontend or endpoint evidence cannot be proven.
3. Enforce reference-mode no-network, no-WS, no-timer, no-random, and no-mutation checks before visual scoring, then collect separate live API and WS evidence for production-depth parity.
4. Require the final 100-point or completion claim to be manifest-backed only: all 8 pages, modal coverage, forbidden scan, `/bt/*` evidence, `/sim/*` evidence, WS transcripts, and score thresholds must pass.

## Architectural Status
`CLEAR`

## Code Review Recommendation
`APPROVE`

## Trade-offs
| Option | Strength | Weakness | Verdict |
|---|---|---|---|
| Zip-first shell plus production-contract adapters | Best alignment with zip and capture source of truth; deterministic reference scoring; restores Backtest and Replay through real contracts | Requires discipline to avoid duplicating React state machines | Recommended and now sufficiently bounded |
| Production React graph plus remodel skin | Preserves existing function depth and component ownership | Already mismatched the requested visual and capture source of truth | Keep only as invalidated alternative |
| Full React rebuild from zip spec | Cleaner long-term frontend architecture | Too broad for this recovery and unnecessary unless adapter seam fails | Fallback only on explicit invalidation |
