# Pending Approval Plan: STOM Dashboard Remodel 100-Point Completion

Status: pending approval
Mode: RALPLAN deliberate consensus
Worktree: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel`
Reference zip: `C:/Users/parkc/Downloads/stom-ai-dashboard-frontend-reviewed.zip`

## User objective

Re-develop `/ui/remodel/*` to reach true 100-point dashboard remodel completion: preserve the provided zip/capture visual structure, restore existing production dashboard function depth, and prove completion through page-by-page browser capture, API/WS evidence, forbidden-control safety scans, and a hard visual scoring gate.

## Consensus receipts

| Stage | Verdict | Artifact |
|---|---|---|
| Planner pass 1 | completed | `.gjc/_session-019f0b7b-b0a1-7000-9f2d-80757688fa91/plans/ralplan/019f0b7b-b0a1-7000-9f2d-80757688fa91/stage-01-planner.md` |
| Architect pass 1 | WATCH / COMMENT | `.gjc/_session-019f0b80-aa33-7000-b51f-3f9d297bb8d5/plans/ralplan/019f0b80-aa33-7000-b51f-3f9d297bb8d5/stage-01-architect.md` |
| Critic pass 1 | ITERATE | `.gjc/_session-019f0b87-ad60-7000-aa70-05c7f62199be/plans/ralplan/019f0b87-ad60-7000-aa70-05c7f62199be/stage-01-critic.md` |
| Planner revision pass 2 | revised | `.gjc/_session-019f0b7b-b0a1-7000-9f2d-80757688fa91/plans/ralplan/019f0b7b-b0a1-7000-9f2d-80757688fa91/stage-02-revision.md` |
| Architect pass 2 | CLEAR / APPROVE | `.gjc/_session-019f0b8e-5c18-7000-9018-3192e7b0ce09/plans/ralplan/019f0b8e-5c18-7000-9018-3192e7b0ce09/stage-02-architect.md` |
| Critic pass 2 | OKAY / APPROVE | `.gjc/_session-019f0b93-31fc-7000-9196-a9770d31c444/plans/ralplan/019f0b93-31fc-7000-9196-a9770d31c444/stage-02-critic.md` |
| Intent reconciliation | open-confirmations-pending | `.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/plans/ralplan/019f05e9-d676-7000-9c61-3c206a2d4031/stage-03-post-interview.md` |

## Current baseline

Corrected evidence shows current implementation is not 100-point complete: visual capture average 71.5/100, DOM/information structure 89.9/100, functional parity 79.8/100, corrected total 79.6/100. Lowest pages are Backtest 77.4 and Chart Replay 76.0. Root causes: live backend state contaminates reference captures; Backtest/Replay are visually present but too static versus production `/bt/*` and `/sim/*`; prior 100-point claims used route/function-presence evidence instead of capture/function replacement evidence.

## ADR

Decision: choose Option B — zip-first static render shell plus bounded production-contract adapters.

Drivers: zip/capture visual source of truth, production `/bt/*` and `/sim/*` function depth, strict safety constraints, and manifest-backed completion.

Rejected alternatives: production React graph plus skin unless it can meet all gates; full React rebuild unless Option B invalidates; static fixture-only prototype because it cannot preserve production depth.

Consequences: `/ui/remodel/*` keeps zip visual structure; production React files are contract references; Backtest/Replay depth is restored through endpoint/action/WS adapters; reference scoring is deterministic and fail-closed; execution stops for re-plan if adapters become a duplicated full frontend or matrices cannot be proven.

## Chosen adapter seam

Keep `frontend/remodel/index.html` as static zip entry. `src/app.js` may split into vanilla modules. Add exactly three layers: mode gate before side effects, pure view-model adapters from fixture/API payloads to page models, and small imperative controllers for user actions and WS lifecycles. Render target remains zip HTML/CSS. Production Backtest/Replay React files are behavior references and endpoint/source maps.

Invalidation triggers: controller recreates a whole production tab; Backtest duplicates more than library/editor/job tracking/result loading/analysis actions; Replay exceeds idle/playing/paused/done/error plus transcript handling; after reference mode and two visual passes any page remains visual <95 or corrected <95; `/bt/*` or `/sim/*` matrices cannot be proven.

## Fail-closed mode matrix

| Behavior | reference | demo | live |
|---|---|---|---|
| Purpose | deterministic visual scoring | local/fallback exploration | real local backend |
| REST | forbidden | fixtures/static JSON only | allowed with loading/error |
| WS | forbidden | forbidden unless demo harness | `/ws`, `/bt/ws_job`, `/sim/ws` allowed |
| Timers | forbidden | deterministic only | bounded polling/reconnect |
| Random/time | forbidden | deterministic seed | allowed outside scoring |
| localStorage | ignore live/base state; no writes | preferences only | preferences/base URL allowed |
| Mutations | inert with visible reference message | inert/no-op with banner | local research mutations allowed with confirmation when destructive |
| Scoring | valid visual mode | invalid final score | invalid visual score; valid live smoke |
| Failure | fail if network/WS/timer/random detected | visible demo/fallback | visible real error, no fake success |

## Safety contract

Allowed only in live mode as local research/backtest actions: `/bt/strategy` save/delete, `/bt/run`, `/bt/job/cancel`, `/bt/job/meta`, `/bt/portfolio`, validation/extract endpoints, append-only audit submission if implemented. Always prohibited: live order, broker login, account balance/trading/connect, hidden export, automatic production export, mutable audit edit/delete, broker runtime invocation, account trading semantics. Final strategy export remains separate from Decision Audit and behind Human Approval Gate.

## Implementation phases after approval

1. Baseline and gates: lock routes/page IDs, viewport, thresholds, current scorecard, artifact paths.
2. Reference fixture mode: `?demo=reference`, no REST/WS/timers/random/localStorage writes/mutations, stable shell/page data.
3. Mode-aware selectors/adapters: fixture, demo, live adapters with visible error/fallback states.
4. Six condition-suite pages: condition, process, history, lab, workbench, audit to visual/function >=95.
5. Backtest parity: full `/bt/*` matrix implemented and evidenced.
6. Chart Replay parity: full `/sim/*` matrix and WS transcript implemented and evidenced.
7. Safety/evidence package: forbidden scans, screenshots, visual score JSON, contact sheet, API/WS manifest.
8. Final browser and test gate: no completion unless manifest thresholds pass.

## `/bt/*` endpoint-action-evidence matrix

Required endpoints/actions: `/bt/health`, `/bt/strategies`, `/bt/strategy`, `/bt/strategy/validate`, `/bt/variables`, `/bt/extract_vars`, `/bt/legacy/self_vars`, `/bt/backfinder/preflight`, `/bt/strategy` save, `/bt/strategy/delete`, `/bt/data_range`, `/bt/run`, `/bt/jobs`, `/bt/job`, `/bt/job/cancel`, `/bt/job/meta`, `/bt/ws_job`, `/bt/result`, `/bt/evo_gens`, `/bt/analysis/summary`, `/bt/analysis/equity`, `/bt/analysis/distribution`, `/bt/analysis/heatmap`, `/bt/analysis/underwater`, `/bt/analysis/insights`, `/bt/analysis/mae_mfe`, `/bt/analysis/exit_reasons`, `/bt/analysis/montecarlo`, `/bt/analysis/orderflow`, `/bt/analysis/gui_parity`, `/bt/compare`, `/bt/overlay`, `/bt/portfolio`, `/bt/report`. Reference mode must prove zero `/bt/*` network calls and inert mutations; live mode must produce manifest API/WS evidence or explicit not-used reason.

## `/sim/*` endpoint-action-WS matrix

Required endpoints/protocol: `/sim/health`, `/sim/days`, `/sim/demo`, `/sim/stocks`, `/bt/strategies`, `/sim/signals`, `/sim/ws`. `/sim/ws` client actions to prove: `start`, `pause`, `resume`, `speed`, `seek`, `stop`. Server messages to handle/prove: `meta`, `bars`, `history`, `done`, `error`.

## Page-by-page 100-point checklist

| Page | 100-point condition |
|---|---|
| Condition | zip shell/tabs/KPIs/generation table/winner/inspector; `/status`/`/runs`/`/ws` live only; modals; safety footer; visual/function >=95 |
| Process | selector/menu/governance, flow map, logs, catalog, boundary contract, metadata, fixture logs, research-only cues; >=95 |
| History | risk/PnL, lineage, summaries, archive, records, ResultDetail, compare, `/runs` live mapping, no random lineage in reference; >=95 |
| Lab | run sidebar, stall, queue, freeze, heatmap, importance, correlation, holdout, combos, context pack; no advice/export bypass; >=95 |
| Workbench | global state, candidate strip, HoF, heatmap, detail charts, handoff/review queue, no approval/export authority; >=95 |
| Audit | append-only banner, checklist, OOS, evidence, decision form, ledger, metadata, no edit/delete, final export separate; >=95 |
| Backtest | zip layout plus `/bt/*` matrix: edit/run/progress/cancel/logs/result/WFO/sweep/report/compare/overlay/portfolio/evo; visual/function >=95 |
| Chart Replay | source/day/stock/strategy/agg/preset/playback/chart modes/indicators/log/watch/minimap/WS; `/sim/*` matrix; historical replay only; visual/function >=95 |

## Acceptance gates

8 reference captures at 1920x1080; every weighted visual score >=95; average weighted visual score >=97; every corrected total score >=95; average corrected total score >=97; contact sheet, diffs, score JSON, final manifest exist; console errors 0; unexpected request failures 0; source/DOM forbidden scan passes; Backtest live evidence covers `/bt/*`; Replay live evidence covers `/sim/*` and WS transcript; Settings, Strategy Inspector, Human Approval dialog open; canonical `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay` remain preserved controls.

## Artifact manifest schema

Final evidence JSON must include `run_id`, `worktree`, `commit` or explicit unknown, `generated_at`, `mode`, `viewport`, thresholds. Each page row requires `id`, `route`, `mode`, `screenshot`, `diff`, `weighted_visual_score`, `corrected_total_score`, `structure_score`, `functional_score`, `console`, `network`, `modals`, `api_evidence_ids`, `ws_transcript_ids`, `forbidden_scan_id`, `passed`, `timestamp`. Global arrays: `api_evidence`, `ws_transcripts`, `forbidden_scan`.

## Verification plan

Unit/static: route mapping, mode gate, fixture immutability, selectors, forbidden scan. Integration/API: core dashboard, `/bt/*` job/result/report/compare paths, `/sim/*` days/stocks/signals/ws paths. Browser/E2E: 8 routes, shell, tabs, modals, Backtest controls, Replay controls, no forbidden controls. Visual regression: captures, diffs, contact sheet, detailed scorecard. Observability: manifest, API evidence, WS transcripts, console/network logs, worktree metadata.

## Pre-mortem

Fixture mode can mask live regressions, adapters can become duplicated frontend, secondary endpoints can be omitted, WS flakiness can hide replay failures, safety regression can sneak in, score inflation can repeat, and local mutation semantics can confuse safety. Mitigations are separate live evidence, seam invalidation, complete matrices, WS transcript, source/DOM/action scans, manifest thresholds, and explicit research/backtest-only labels.

## Intent Reconciliation

Automated mode: no user questions were asked. Pending confirmations: architecture pivot from prior production-React shell plan to zip-first shell plus adapters; `/ui/remodel/*` remains replacement candidate until all gates pass; canonical routes remain controls; default-route promotion needs later explicit approval; verification may use fixtures, safe local endpoints, or read-only `_database` references but no operating DB writes or live-broker side effects; safety prohibitions remain absolute.

## Handoff recommendation

After explicit approval, execute through `/skill:ultragoal` so each story checkpoints evidence. Recommended next command:

```text
/skill:ultragoal "execute approved pending plan for STOM dashboard remodel 100-point completion: C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/plans/ralplan/019f05e9-d676-7000-9c61-3c206a2d4031/pending-approval.md"
```
