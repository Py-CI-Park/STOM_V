## Summary
Revision 2 resolves the prior Architect WATCH and Critic ITERATE items. The plan now has a bounded zip-first adapter seam, a fail-closed reference/demo/live mode matrix, explicit `/bt/*` and `/sim/*` evidence matrices, a manifest schema, stronger gates, and a correct distinction between local research mutations and prohibited safety controls.

Architectural status is `CLEAR` and code-review recommendation is `APPROVE`. Execution can proceed architecturally after pending approval; the approval should remain gated on the plan workflow, not this review alone.

## Analysis
Evidence reviewed:
- Revised plan: `.gjc/_session-019f0b7b-b0a1-7000-9f2d-80757688fa91/plans/ralplan/019f0b7b-b0a1-7000-9f2d-80757688fa91/stage-02-revision.md`.
- Prior Architect WATCH artifact: `.gjc/_session-019f0b80-aa33-7000-b51f-3f9d297bb8d5/plans/ralplan/019f0b80-aa33-7000-b51f-3f9d297bb8d5/stage-01-architect.md`.
- Prior Critic ITERATE artifact: `.gjc/_session-019f0b87-ad60-7000-aa70-05c7f62199be/plans/ralplan/019f0b87-ad60-7000-aa70-05c7f62199be/stage-01-critic.md`.
- The remodel entrypoint `ai_strategy_loop/dashboard/frontend/remodel/index.html` loads only `./styles/theme.css`, `./src/data.js`, and `./src/app.js`, and `docs/ARCHITECTURE.md` defines it as a no-build static SPA driven by `window.STOM_DATA`. This supports the revised zip-first shell and vanilla adapter seam.
- The corrected scorecard `artifacts/runtime/zip-parity-compare/detailed-scorecard.json` reports average visual capture score `71.5`, average corrected total `79.6`, Backtest `77.4`, and Chart Replay `76.0`; it attributes major gaps to live state overwriting fixtures and shallow static Backtest/Replay depth. The plan targets those causes directly.
- Current `remodel/src/app.js` still has the exact side effects the plan must eliminate in reference mode: localStorage base URL read/write, `fetch` calls, `reconnectBackend()`, `/ws` construction/reconnect timers, `sendControl`, and `Math.random()` lineage text.
- `ai_strategy_loop/dashboard/backtest_api.py` route evidence matches the revised `/bt/*` matrix: health, strategies, strategy get/validate/save/delete, variables, extract_vars, legacy/self_vars, backfinder/preflight, data_range, run, jobs, job, job/cancel, job/meta, result, evo_gens, all analysis routes, compare, overlay, portfolio, report, and websocket `/bt/ws_job`.
- `ai_strategy_loop/dashboard/simulation_api.py` route and protocol evidence matches the revised `/sim/*` matrix: health, days, demo, stocks, signals, websocket `/sim/ws`, client actions `start/pause/resume/speed/seek/stop`, and server messages including `meta`, `bars`, `history`, `done`, and `error`.
- Production frontend evidence in `bt-tab-root.jsx`, `bt-tab-run.jsx`, `bt-tab-library.jsx`, `bt-result-area.jsx`, `bt-tab-analysis.jsx`, and `sim-tab-root.jsx` confirms the matrix corresponds to real UI behavior: strategy CRUD, variable extraction, self vars, run/job/WS, result/report/compare/overlay/portfolio, replay inventory, strategy selectors, signal overlays, and replay WS controls.
- The safety brief `ai_strategy_loop/dashboard/frontend/remodel/CODEX_AGENT_BRIEF.md` forbids live orders, broker login, account trading controls, automatic/hidden production export, and mutable audit edit/delete, while requiring research-only wording, Human Approval Gate, Append-Only Audit, and final export separation.

Spec compliance review:
- Bounded adapter seam: resolved. Revision 2 chooses the zip HTML/CSS render target, permits `src/app.js` splitting into vanilla modules, defines exactly three layers, treats production React as contract reference rather than default runtime import, and defines invalidation triggers for duplicated state-machine risk.
- Fail-closed reference/demo/live matrix: resolved. The plan now forbids REST, WS, timers, random/drifting time, localStorage side effects, and real mutations in `reference`; confines `demo` to visible fixtures; and allows `live` only with visible loading/error states and no fake success.
- `/bt/*` endpoint-action-evidence matrix: resolved. The matrix covers the route decorators and production behavior surface found in `backtest_api.py` and the React Backtest tab files. Query variants such as the `/bt/result` demo/sentinel path should be recorded under the `/bt/result` evidence row if retained during execution, but this is an execution detail, not a plan blocker.
- `/sim/*` endpoint-action-WS matrix: resolved. The matrix includes `/sim/health`, `/sim/days`, `/sim/demo`, `/sim/stocks`, `/sim/signals`, `/bt/strategies` usage, `/sim/ws`, required client actions, required server messages, seek/history behavior, cleanup, error, and recovery evidence.
- Artifact manifest schema: resolved. The plan requires run/worktree/commit metadata, viewport and thresholds, per-page screenshots/diffs/scores, console and network status, modal coverage, API evidence IDs, WS transcript IDs, forbidden scan IDs, and global evidence arrays.
- Stronger gates: resolved. The pre-mortem now has concrete gates for fixture masking, adapter duplication, secondary endpoint omission, WS flakiness, safety regression, score inflation, and local mutation confusion.
- Local research mutation distinction: resolved. The plan separates allowed live-mode local research/backtest actions from prohibited broker/account/live-order/export/audit-mutation controls, disables research mutations in reference, and requires visible confirmation/non-export semantics where destructive.

Architecture review:
- Option B is now a coherent architecture rather than a vague direction: preserve the zip visual shell while restoring production-depth behavior through endpoint-derived adapters and bounded controllers.
- The invalidation triggers are sufficiently concrete to prevent the adapter layer from becoming a second production React frontend. If those triggers fire, Option C/React rebuild is the right re-plan path.
- The verification architecture is evidence-driven and should prevent a repeat of the earlier false 100-point claim: reference visual scoring and live API/WS evidence are deliberately separate.

## Root Cause
The underlying failure was a source-of-truth and mode-boundary mismatch. The production React path preserved deeper behavior but missed the requested zip/capture visual structure; the zip-static path preserved the visual shell but lost production Backtest/Replay depth, and live backend state/randomness made visual scoring nondeterministic. Revision 2 addresses that root cause by making the zip shell the visual target, production endpoints the behavior contract, and `reference` mode fail-closed for scoring.

## Findings
No blocking findings remain.

- Severity: LOW, execution note only. Reference: `backtest_api.py` supports `/bt/result` via `job_id`, `run_id/gen_no`, and a `demo=1`/sentinel branch, while the plan lists the two production result variants. Impact: if the execution keeps the sentinel demo default, evidence should attach it to the `/bt/result` row so it is not mistaken for an untracked behavior. Fix: record the demo/sentinel result path as a `/bt/result` variant in the final manifest if it remains visible. This does not require another plan revision.

## Recommendations
1. Approve Revision 2 architecturally. Execution can proceed after pending approval.
2. Preserve the plan sequencing: mode gate first, then fixtures, then adapters/controllers, then Backtest and Replay matrices, then visual and manifest evidence.
3. Enforce invalidation triggers strictly. If Backtest or Replay controllers expand into duplicated production tab state machines, stop and re-plan Option C.
4. Keep visual scoring restricted to `reference` mode and keep live REST/WS proof separate so fixture determinism cannot hide integration regressions.
5. Require the final manifest before any 100-point/completion claim.

## Architectural Status
`CLEAR`

Revision 2 has enough boundary, evidence, and safety specificity for execution planning. Remaining risk is execution discipline, not plan ambiguity.

## Code Review Recommendation
`APPROVE`

The plan resolves the previous WATCH/ITERATE items. Execution can proceed architecturally after pending approval.

## Trade-offs
| Option | Strength | Weakness | Verdict |
|---|---|---|---|
| Zip-first shell plus production-contract adapters | Best alignment with the provided visual source of truth; deterministic reference scoring; direct repair for Backtest/Replay shallowness | Requires disciplined adapter boundaries and manifest evidence | Approved primary path |
| Production React graph plus remodel skin | Preserves existing functional depth and React state machines | Already weak against zip/capture visual expectations; high visual drift risk | Keep only as invalidated alternative |
| Full React rebuild from zip spec | Potentially cleaner long-term component architecture | Broader, slower, and unnecessary before adapter invalidation | Fallback after Option B triggers |
| Static fixture-only prototype | Fastest visual parity | Fails production Backtest/Replay depth and live evidence | Not acceptable |

The accepted trade-off is to spend complexity on a narrow adapter seam rather than rebuild the visual shell or fake production depth. The revised gates are strong enough to detect when that trade-off stops paying off.
