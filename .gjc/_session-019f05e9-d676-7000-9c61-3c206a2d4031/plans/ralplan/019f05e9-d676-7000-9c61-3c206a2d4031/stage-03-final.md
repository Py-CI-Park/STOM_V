# Pending Approval Plan: STOM Dashboard Remodel 100-Point Completion

Status: pending approval
Mode: RALPLAN deliberate consensus
Worktree: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel`
Reference zip: `C:/Users/parkc/Downloads/stom-ai-dashboard-frontend-reviewed.zip`

## Consensus receipts

| Stage | Verdict | Artifact |
|---|---|---|
| Planner pass 1 | completed | `.gjc/_session-019f0b7b-b0a1-7000-9f2d-80757688fa91/plans/ralplan/019f0b7b-b0a1-7000-9f2d-80757688fa91/stage-01-planner.md` |
| Architect pass 1 | WATCH / COMMENT | `.gjc/_session-019f0b80-aa33-7000-b51f-3f9d297bb8d5/plans/ralplan/019f0b80-aa33-7000-b51f-3f9d297bb8d5/stage-01-architect.md` |
| Critic pass 1 | ITERATE | `.gjc/_session-019f0b87-ad60-7000-aa70-05c7f62199be/plans/ralplan/019f0b87-ad60-7000-aa70-05c7f62199be/stage-01-critic.md` |
| Planner revision pass 2 | revised | `.gjc/_session-019f0b7b-b0a1-7000-9f2d-80757688fa91/plans/ralplan/019f0b7b-b0a1-7000-9f2d-80757688fa91/stage-02-revision.md` |
| Architect pass 2 | CLEAR / APPROVE | `.gjc/_session-019f0b8e-5c18-7000-9018-3192e7b0ce09/plans/ralplan/019f0b8e-5c18-7000-9018-3192e7b0ce09/stage-02-architect.md` |
| Critic pass 2 | OKAY | `.gjc/_session-019f0b93-31fc-7000-9196-a9770d31c444/plans/ralplan/019f0b93-31fc-7000-9196-a9770d31c444/stage-02-critic.md` |
| Intent reconciliation | open-confirmations-pending | `.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/plans/ralplan/019f05e9-d676-7000-9c61-3c206a2d4031/stage-03-post-interview.md` |

## Current baseline

Corrected evidence says the current remodel is not 100-point complete:

- Visual capture score: `71.5/100`
- Structure score: `89.9/100`
- Functional score: `79.8/100`
- Corrected total: `79.6/100`
- Lowest pages: Backtest `77.4`, Chart Replay `76.0`

Primary causes: live state contaminates reference captures; Backtest and Replay are visually present but too static versus production `/bt/*` and `/sim/*` depth; prior validation confused route/function presence with capture/function replacement.

## RALPLAN-DR summary

### Principles

1. Zip captures/DOM are the visual source of truth.
2. Production function depth is restored through contracts, not mocks.
3. `reference` mode is deterministic and fail-closed.
4. Human Approval Gate, Append-Only Audit, research/local-only cues are hard gates.
5. Completion is manifest-backed only; no 100-point claim without evidence.

### Decision drivers

1. Eight-page capture parity at 1920x1080.
2. Backtest `/bt/*` and Replay `/sim/*` production parity.
3. No-live-trading/no-hidden-export safety.

### Chosen option

Option B: zip-first shell plus production-contract adapters.

Rejected or fallback alternatives:

- Production React graph plus remodel skin: functional but already failed user-visible zip/capture expectation. Use only if quick proof reaches every visual gate without function loss.
- Full React rebuild: fallback only after bounded zip-first adapters invalidate.
- Static fixture-only prototype: rejected because it fails production Backtest/Replay depth.

## Architecture contract

Keep `remodel/index.html` as the static zip entry. `src/app.js` may split into vanilla JS modules, but the render target remains the zip HTML/CSS structure. Add exactly three layers:

1. Mode gate before side effects.
2. Pure view-model adapters from fixture/API payloads to page models.
3. Small imperative controllers for user actions and WS lifecycles.

Production React files are contract references, not default runtime imports. Do not import JSX directly into the vanilla shell by default. Forbid wholesale reimplementation of production React state machines.

Invalidation triggers:

- A controller recreates a full production tab instead of endpoint adapters.
- Backtest requires duplicating more than library/editor, job tracking, result loading, and analysis actions.
- Replay exceeds idle/playing/paused/done/error plus transcript handling.
- After reference mode and two visual passes, any page remains visual `<95` or corrected `<95`.
- Endpoint matrices cannot be proven.

If any trigger occurs, stop execution and re-plan Option C / React rebuild.

## Mode matrix

| Behavior | reference | demo | live |
|---|---|---|---|
| Purpose | deterministic visual scoring | local/fallback exploration | real local backend |
| REST | forbidden; no `/health`, `/status`, `/runs`, `/bt/*`, `/sim/*` | fixtures/static JSON only, banner | allowed with loading/error |
| WS | forbidden | forbidden unless demo harness, banner | `/ws`, `/bt/ws_job`, `/sim/ws` allowed |
| Timers | no reconnect/polling loops | deterministic UI only | bounded polling/reconnect allowed |
| Random/time | no `Math.random`, drifting timestamps/counters | deterministic seed/fixture | allowed outside scoring |
| localStorage | ignore base URL/live state; no writes | preferences only, no side effects | preferences/base URL allowed; no hidden export state |
| Mutations | inert with visible reference message | inert/no-op with banner | local research mutations allowed with confirmation where destructive |
| Scoring | only valid visual mode | invalid final score | invalid visual score; valid live smoke |
| Failure | fail if network/WS/timer/random detected | show demo/fallback | show real error; no fake success |

## Safety contract

Allowed only in live mode as local research/backtest actions: `/bt/strategy` save/delete, `/bt/run`, `/bt/job/cancel`, `/bt/job/meta`, `/bt/portfolio`, validation/extract endpoints, append-only audit submission if implemented. Destructive local research actions require visible confirmation and must say they do not export to production.

Always prohibited: live order, broker login, account balance/trading/connect, hidden export, automatic production export, mutable audit edit/delete, broker runtime invocation, account trading semantics. Final strategy export remains separate from Decision Audit and behind Human Approval Gate.

## Implementation phases after approval

### Phase 1 — Baseline, fixtures, and scoring gate

- Lock page IDs/routes/viewport/thresholds.
- Implement fail-closed `reference` mode before adapters.
- Freeze fixture shell values, rows, logs, ledger, candidates, backtest demo job, replay session.
- Remove random/timer/network effects in reference mode.
- Build visual manifest with screenshots, diffs, scores, console/network, modal, API/WS, forbidden scan fields.

### Phase 2 — App seams and six condition pages

- Create pure selectors/view models.
- Add mode-guarded action controllers.
- Bring condition, process, history, lab, workbench, and audit to visual/function parity.
- Preserve settings, inspector, Human Approval dialog, append-only audit, and safety footer.

### Phase 3 — Backtest production-depth parity

Wire zip panels to the full `/bt/*` matrix:

- `/bt/health`
- `/bt/strategies?kind=buy|sell`
- `/bt/strategy?kind&name`
- `/bt/strategy/validate`
- `/bt/variables`
- `/bt/extract_vars`
- `/bt/legacy/self_vars?kind&name`
- `/bt/backfinder/preflight?kind&name`
- `/bt/strategy` save
- `/bt/strategy/delete`
- `/bt/data_range`
- `/bt/run`
- `/bt/jobs`
- `/bt/job?job_id`
- `/bt/job/cancel`
- `/bt/job/meta`
- `/bt/ws_job?job_id`
- `/bt/result?job_id`
- `/bt/result?run_id&gen_no`
- `/bt/evo_gens?run_id`
- `/bt/analysis/summary`, equity, distribution, heatmap, underwater, insights, mae_mfe, exit_reasons, montecarlo, orderflow, gui_parity
- `/bt/compare?job_a&job_b`
- `/bt/overlay?job_ids`
- `/bt/portfolio`
- `/bt/report`

Reference evidence must prove zero `/bt/*` network calls, disabled/inert mutation buttons, and fixture Backtest screenshot. Live evidence must prove real endpoint behavior or visible error.

### Phase 4 — Chart Replay production-depth parity

Wire zip panels to the full `/sim/*` and replay matrix:

- `/sim/health`
- `/sim/days?src=tick|min`
- `/sim/demo?src&mode`
- `/sim/stocks?date&src`
- `/bt/strategies?kind=buy|sell` for replay strategy selectors
- `/sim/signals?date&src&code&buy&sell`
- `/sim/ws`

WS client actions to prove: `start`, `pause`, `resume`, `speed`, `seek`, `stop`. Server messages to handle/prove: `meta`, `bars`, `history`, `done`, `error`.

### Phase 5 — Final safety and evidence package

- Forbidden source/DOM/action scan.
- Browser E2E for 8 pages plus settings, inspector, approval modal, Backtest, Replay, Audit.
- Separate live API/WS smoke evidence so reference mode cannot mask live failures.
- Contact sheet, diff images, detailed score JSON, final manifest.

## Acceptance criteria

Visual:

- 8 reference captures at 1920x1080.
- Every weighted visual score `>=95`.
- Average weighted visual score `>=97`.
- Every corrected total score `>=95`.
- Average corrected total score `>=97`.
- Contact sheet, diffs, score JSON, manifest exist.

Functional:

- All tabs/subtabs render.
- Global shell persists.
- Settings, inspector, and approval modals open.
- Audit has append-only ledger/form.
- Backtest matrix has live evidence.
- Replay matrix has live evidence.
- API failures are visible and never fake success.

Safety:

- Forbidden scan passes.
- Human Approval Gate, Append-Only Audit, research-only/local-only visible.
- Final export approval remains separate.
- No broker/account/live-order/hidden-export/mutable-audit controls.

## Verification commands and evidence

Execution must include at minimum:

```powershell
pytest tests/unit/test_dashboard_remodel_static.py tests/unit/test_dashboard_remodel_baseline_contract.py -q
pytest tests/unit/test_dashboard* tests/unit/dashboard -q
python -m py_compile ai_strategy_loop/dashboard/app.py ai_strategy_loop/dashboard/backtest_api.py ai_strategy_loop/dashboard/simulation_api.py
node --check ai_strategy_loop/dashboard/frontend/remodel/src/app.js
node --check ai_strategy_loop/dashboard/frontend/remodel/remodel-bootstrap.js
git diff --check
```

Browser/evidence requirements:

- `/ui/remodel/condition?demo=reference`
- `/ui/remodel/process?demo=reference`
- `/ui/remodel/history?demo=reference`
- `/ui/remodel/lab?demo=reference`
- `/ui/remodel/workbench?demo=reference`
- `/ui/remodel/audit?demo=reference`
- `/ui/remodel/backtest?demo=reference`
- `/ui/remodel/chart-replay?demo=reference`
- Separate live-mode `/bt/*` and `/sim/*` API/WS transcripts.

## Pre-mortem

1. Fixture masking live regressions. Mitigation: reference manifest plus separate live API/WS matrix evidence.
2. Adapter duplication. Mitigation: enforce controller boundaries and invalidation triggers before implementation expands.
3. Secondary endpoint omission. Mitigation: every `/bt/*` and `/sim/*` row must be proven, inert in reference, or not-used with reason.
4. WS flakiness. Mitigation: transcript includes success and recoverable error paths plus cleanup after stop/navigation.
5. Safety regression. Mitigation: static scan, browser DOM scan, and handler/action review.
6. Score inflation. Mitigation: no completion wording until manifest thresholds, console/network checks, modal coverage, and forbidden scan pass.
7. Local mutation confusion. Mitigation: reference disables mutations; live labels local mutations as research/backtest and never export/broker/account.

## Intent Reconciliation

Automated mode: no user questions were asked. The following open confirmations are carried to the pending approval gate:

1. Architecture pivot: prior pending plan preferred a hybrid production React/component reuse path and disallowed vanilla `frontend/remodel/src/app.js` as production renderer. This revised plan intentionally pivots to zip-first static shell with bounded production-contract adapters because the user later identified visual/capture mismatch and requested 100-point completion against the provided zip/captures.
2. Visual scoring priority: provided zip captures/DOM are the visual source of truth and `reference` capture gates decide visual completion.
3. Function depth priority: Backtest and Chart Replay must regain production `/bt/*` and `/sim/*` depth even though the render shell remains zip-first.
4. Reference mode: `?demo=reference` disables REST, WS, timers, random values, localStorage side effects, and mutations. Separate live-mode evidence remains required.
5. Safety: live order, broker login, account/balance/trading controls, hidden or automatic production export, mutable audit edit/delete, and hidden `final_approval` remain forbidden.
6. Route promotion: `/ui/remodel/*` remains replacement candidate until all gates pass. Canonical `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay` remain preserved controls. Default-route promotion requires later explicit approval.
7. Data usage: verification may use fixtures, safe local endpoints, or read-only references to existing `_database` data, but must not create operating DB writes or live-broker side effects.

## ADR

Decision: Use a zip-first static remodel shell plus bounded production-contract adapters.

Drivers: user-visible capture parity failure, Backtest/Replay function-depth gaps, safety-critical local-only research boundary, and need for a manifest-backed 100-point gate.

Alternatives considered:

- Production React graph plus remodel skin: rejected as primary because it already failed visual/capture expectation.
- Full React rebuild: deferred as fallback if adapter seam invalidates.
- Static fixture-only prototype: rejected because it fails production function depth.

Why chosen: It directly addresses the current failures: zip visual mismatch, live-state capture contamination, and shallow Backtest/Replay. It preserves the provided visual source while forcing production-depth endpoint/WS evidence.

Consequences: Implementation requires careful mode gating and adapter boundaries. Backtest and Replay become high-risk milestones. Completion cannot be claimed without visual, API, WS, safety, and manifest evidence.

Follow-ups: Execute via ultragoal after explicit approval; preserve canonical routes until all gates pass; re-plan if invalidation triggers fire.

## Pending approval

This plan is approved by Planner/Architect/Critic consensus but remains pending user execution approval. Recommended execution path: `/skill:ultragoal` using this `pending-approval.md` path.
