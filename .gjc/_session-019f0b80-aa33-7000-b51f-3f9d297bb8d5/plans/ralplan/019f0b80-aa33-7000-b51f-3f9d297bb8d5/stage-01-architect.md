## Summary
The planner artifact is directionally sound: it correctly rejects a production-React-only skin as insufficient, keeps the provided zip/captures as the visual source of truth, and explicitly requires production-depth `/bt/*` and `/sim/*` parity plus safety gates. Architectural status is `WATCH`, not `CLEAR`, because the plan still needs execution-contract amendments for the static zip shell to production adapter seam, reference-mode fail-closed behavior, and endpoint/WS evidence matrices.

## Analysis
Evidence reviewed:
- Planner artifact: `.gjc/_session-019f0b7b-b0a1-7000-9f2d-80757688fa91/plans/ralplan/019f0b7b-b0a1-7000-9f2d-80757688fa91/stage-01-planner.md`.
- Current remodel entrypoint is the zip/static shell: `ai_strategy_loop/dashboard/frontend/remodel/index.html` loads `./styles/theme.css`, `./src/data.js`, and `./src/app.js`; it does not load `/ui/bundle/app.js`.
- Current remodel runtime is no-build vanilla JS: `ai_strategy_loop/dashboard/frontend/remodel/docs/ARCHITECTURE.md` says `index.html -> styles/theme.css -> src/data.js -> src/app.js`; `src/app.js` starts as an offline-first prototype and holds `routeToState` plus a live backend bridge.
- Corrected visual/function evidence supports the planner premise: `artifacts/runtime/zip-parity-compare/detailed-scorecard.json` reports average visual capture score `71.5`, average corrected total `79.6`, Backtest `77.4`, and Chart Replay `76.0`; the explanations identify live backend state overwriting fixture values and static Backtest/Replay depth as the main shortfalls.
- Current `src/app.js` always initializes from live/local state: it reads `localStorage` for backend URL, calls `reconnectBackend()` at load, fetches `/health`, `/status`, `/runs`, opens `/ws`, and uses `Math.random()` in History lineage text. This confirms the need for the planner `?demo=reference` fixture mode.
- Production Backtest depth exists and is not hypothetical: `backtest_api.py` exposes strategy list/get/validate/save/delete, variables/extract/self-vars/backfinder, data_range, run/jobs/job/cancel/meta, result, evo_gens, analysis routes, montecarlo/orderflow/gui_parity, compare, overlay, portfolio, report, and `/bt/ws_job`; production frontend files consume many of these (`bt-tab-run.jsx`, `bt-tab-library.jsx`, `bt-result-area.jsx`, `bt-tab-analysis.jsx`).
- Production Replay depth exists: `simulation_api.py` exposes `/sim/health`, `/sim/days`, `/sim/demo`, `/sim/stocks`, `/sim/signals`, and `/sim/ws`; production `sim-tab-root.jsx` consumes `/sim/*` and `/bt/strategies` and owns WS playback state.
- Safety source-of-truth is explicit: `ai_strategy_loop/dashboard/frontend/remodel/CODEX_AGENT_BRIEF.md` forbids live order, broker login, account controls, automatic or hidden production export, and mutable decision-audit edits/deletes while requiring research-only, Human Approval Gate, Append-Only Audit, and final-export separation.

Spec compliance:
- Visual source-of-truth alignment: The plan correctly uses zip captures/page IDs and requires 8-page 1920x1080 reference-mode capture gates with per-page >=95 and average >=97. This directly addresses the corrected scorecard rather than the obsolete 100/100 route-presence score.
- Production function depth: The plan explicitly elevates Backtest and Replay to high-risk epics and lists the core `/bt/*` and `/sim/*` flows. It should be amended to derive the full endpoint matrix from actual route decorators and production component usage so secondary endpoints are not missed.
- Reference fixture mode: The plan `?demo=reference` requirement is correct. It needs a stricter mode matrix so reference mode cannot accidentally fetch, reconnect WS, use localStorage, mutate state, or randomize text.
- Safety boundaries: The plan preserves the right prohibitions and keeps export approval separate from Decision Audit. It should additionally state that reference mode disables all mutating `/bt/*` actions, and live mode mutating research actions require explicit user confirmation and visible non-export semantics.
- Zip-first vs alternatives: The option analysis is good. Zip-first adapters are the right primary path because the evidence shows production skin preserved function but failed the requested visual structure, while static zip preserved visual structure but lost production depth. React rebuild remains a fallback, not the first move.
- Verification architecture: The plan has the correct categories: static/unit, API, browser/e2e, visual regression, forbidden scan, artifacts. It needs concrete matrices for endpoint calls, WS transcripts, modals, and score manifests.

## Root Cause
The underlying defect is a source-of-truth and mode-boundary mismatch, not a single styling issue. Previous work alternated between production React function preservation and zip-static visual preservation; without a strict reference/live selector seam, live backend state overwrote capture fixtures, while Backtest/Replay became visually present but functionally shallow. The planner identifies this root cause and chooses the right direction, but execution must not reintroduce ambiguity through broad fallbacks or ad-hoc React/vanilla duplication.

## Strongest Steelman Antithesis
The strongest argument against the recommended zip-first adapter path is to keep the production React graph and reskin it: the existing React components already implement `/bt/*` job lifecycle, strategy CRUD, reports, analysis, overlays, portfolio, `/sim/*` playback, signal overlays, and WS state. Rebuilding these behaviors inside `remodel/src/app.js` risks duplicated state machines, stale endpoint assumptions, more untested imperative code, and a second frontend architecture. A production-skin approach would preserve maintainability and verified behavior if the visual mismatch were merely tokens/layout.

That antithesis is not decisive here because the inspected evidence shows the user-visible failure was exactly that production-skin/route-presence validation did not match the zip/capture source of truth. The synthesis is to keep the zip DOM/visual structure as the render target while deriving adapters from production route/component contracts, with a hard invalidation rule if adapter work becomes a duplicated React frontend.

## Findings

### MEDIUM - Specify the adapter seam before implementation
- Reference: planner `File-level changes` and steps 5-6; `remodel/src/app.js` is vanilla static, while production Backtest/Replay live in React JSX modules (`bt-tab-*.jsx`, `sim-tab-*.jsx`).
- Impact: "Adapt or mount production behavior" can be interpreted as direct JSX import, iframe/island mounting, or full imperative duplication. Without a chosen seam, executors can preserve either visuals or function depth but drift from the other.
- Fix: Add an amendment defining the allowed adapter shape: endpoint-derived view models and small imperative controllers inside the zip shell, or a deliberate React-island bridge with fixed mount points and visual contract tests. Forbid unbounded duplication of production state machines; if duplication becomes necessary, trigger the planner invalidation path to React rebuild.

### MEDIUM - Make reference fixture mode fail-closed
- Reference: current `remodel/src/app.js` reads `localStorage`, calls `reconnectBackend()` on load, fetches `/health`, `/status`, `/runs`, opens `/ws`, and uses `Math.random()` for history lineage text; `detailed-scorecard.json` attributes major deltas to live backend values overwriting fixture values.
- Impact: `?demo=reference` can still be nondeterministic unless it disables live fetch/WS, localStorage base URL overrides, timers, random values, and mutable controls. A flaky reference mode would undermine the capture scoring gate.
- Fix: Add a mode matrix: `reference` = frozen fixture only, no REST/WS/timers/random/localStorage writes/mutating actions; `demo` = local fixture/fallback with explicit banner; `live` = real API/WS with visible loading/error/fallback states. Capture scoring must only run in `reference`.

### MEDIUM - Turn production parity into explicit endpoint and action matrices
- Reference: `backtest_api.py` exposes more than the planner hand list, including `/bt/variables`, `/bt/legacy/self_vars`, `/bt/job/meta`, and analysis/gui-parity routes; production components consume different subsets. `simulation_api.py` and `sim-tab-root.jsx` define the replay contract and WS protocol.
- Impact: "wire `/bt/*` and `/sim/*`" is correct but broad. Missing secondary endpoints would recreate the current problem: function-presence claims without production-depth evidence.
- Fix: Add two matrices to the execution plan: endpoint, owner component/source, UI control, reference behavior, live behavior, expected evidence artifact. Include REST and WS separately for `/bt/ws_job` and `/sim/ws`.

### LOW - Gate research-mutating controls separately from safety-prohibited controls
- Reference: `backtest_api.py` `POST /bt/strategy`, `POST /bt/strategy/delete`, `POST /bt/run`, `POST /bt/job/cancel`, and `POST /bt/job/meta` are real local research mutations; the safety contract forbids live orders/broker/account/hidden export/audit edits, not all research actions.
- Impact: Treating all mutations as equivalent either weakens safety wording or over-disables necessary Backtest parity.
- Fix: Add wording that these are local research/backtest mutations only, disabled in reference mode, visibly confirmed in live mode, and excluded from export/broker/account paths. Decision Audit remains append-only; final export remains a separate Human Approval flow.

### LOW - Verification artifacts need a manifest schema, not only categories
- Reference: existing capture results under `frontend/remodel/docs/captures` prove render/pass text checks but not capture-to-capture parity; corrected score artifacts under `artifacts/runtime/zip-parity-compare` prove visual scoring but not endpoint/WS coverage.
- Impact: Completion can again be overstated if route, text, screenshot, and API evidence are not correlated.
- Fix: Define a manifest with route, mode, viewport, screenshot path, diff path, visual score, console status, modal coverage, API calls, WS transcript, forbidden scan result, and commit/worktree metadata for all 8 pages.

## Principle Violations
- Planner artifact: no hard safety violation found. It respects the zip visual source of truth, production function preservation, reference fixture need, and safety constraints.
- Existing implementation state that the plan is correcting: deterministic fixture mode is violated by live backend refresh and `Math.random()`; production function depth is violated by static Backtest/Replay; earlier verification violated the evidence-gate principle by conflating route/function presence with capture parity.
- Fallback policy watchpoint: fallback/demo behavior must remain visible and must not hide live API/WS failures as success. The plan mentions visible fallback/error states; the mode matrix amendment should make this mandatory.

## Recommendations
1. Keep Option B as the primary plan: zip-first shell plus production-contract adapters.
2. Add the four amendments above before execution handoff: adapter seam, fail-closed reference mode, endpoint/action matrices, and artifact manifest schema.
3. Treat Backtest and Replay as separate high-risk milestones with their own parity gates before final all-page scoring.
4. Require capture scoring to run only against `?demo=reference`; require separate live API/WS smoke evidence so fixture mode cannot mask live regressions.
5. Preserve the exact safety contract: no live order, broker login, account/balance trading, hidden export, automatic production export, or mutable audit edits/deletes; local research/backtest mutations must be explicit, visible, and non-exporting.

## Architectural Status
`WATCH`

Rationale: The direction is sound and no fundamental blocker is present, but the adapter seam and deterministic reference mode are high-leverage risks that must be watched or amended before implementation claims 100-point completion.

## Code Review Recommendation
`COMMENT`

No request to discard or re-plan from scratch. Incorporate the amendments as execution-contract addenda; otherwise downstream executors will still have to guess at the riskiest seams.

## Trade-offs
| Option | Strength | Weakness | Verdict |
|---|---|---|---|
| Zip-first shell + production adapters | Best visual source-of-truth alignment; deterministic reference fixture possible; targets the actual 71.5/79.6 failure mode | Adapter complexity; risk of duplicating React state machines in vanilla JS | Recommended with adapter seam guardrails |
| Production React graph + remodel skin | Preserves existing `/bt/*` and `/sim/*` depth, build tooling, and component tests | Already failed user-visible zip/capture expectation; visual parity risk remains high | Use only if a quick proof reaches all visual gates without function loss |
| Full React rebuild from zip spec | Long-term maintainability and typed state seams | Too broad for the current 100-point recovery; likely delays verification | Fallback only if zip-first adapters collapse |
| Static fixture-only prototype | Fastest capture parity | Fails production depth for Backtest/Replay and live evidence | Not acceptable |

Real tension: the more strictly the zip DOM is preserved, the more production React behavior must be adapted rather than reused directly; the more production React is reused directly, the more visual parity can drift from the provided captures. The synthesis is a zip render shell with small, contract-tested data/action adapters and a hard escape hatch to React rebuild if the adapters become a second frontend.
