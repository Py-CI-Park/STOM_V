# STOM Dashboard Remodel 100-Point Completion Plan — RALPLAN Revision 2

## Summary
Revision 2 incorporates Architect WATCH and Critic ITERATE feedback. Baseline remains visual 71.5, structure 89.9, functional 79.8, corrected 79.6; Backtest 77.4 and Chart Replay 76.0 are lowest because zip visuals exist but production `/bt/*` and `/sim/*` depth is shallow. Option B remains recommended, now bounded by a specific adapter seam, fail-closed modes, endpoint evidence matrices, manifest schema, stronger gates, and explicit local-research versus safety-prohibited mutation rules.

## RALPLAN-DR
Principles: (1) zip captures/DOM are the visual source of truth; (2) production function depth is restored through contracts, not mocks; (3) `reference` mode is deterministic and fail-closed; (4) Human Approval Gate, Append-Only Audit, research/local-only cues are hard gates; (5) completion is manifest-backed only.
Decision drivers: 8-page 1920x1080 capture parity; Backtest `/bt/*` and Replay `/sim/*` parity; no-live-trading/no-hidden-export safety.
Options: A production React graph plus remodel skin: functional but already weak visually; invalidate unless every page visual >=95 and average >=97 without function loss. B zip-first shell plus production-contract adapters: recommended. C full React rebuild: fallback only after B invalidates.

## Chosen adapter seam and invalidation
Allowed architecture: keep `remodel/index.html` as static zip entry; `src/app.js` may split into vanilla JS modules; render target remains zip HTML/CSS. Add exactly three layers: mode gate before side effects; pure view-model adapters from fixture/API payloads to page models; small imperative controllers for user actions/WS lifecycles. Production React files are contract references, not default runtime imports. Do not import JSX directly into the vanilla shell by default. Allowed controllers: core shell route/tab/modal/theme/mode; Backtest strategy CRUD, variable/extract, run/job/ws_job, result/report/compare/overlay/portfolio; Replay inventory, strategy list, signal overlay, `/sim/ws` playback. Forbid wholesale reimplementation of production React state machines.
Invalidation triggers: a controller recreates a full production tab instead of endpoint adapters; Backtest requires duplicating more than library/editor, job tracking, result loading, analysis actions; Replay exceeds idle/playing/paused/done/error plus transcript handling; after reference mode and two visual passes any page remains visual <95 or corrected <95; endpoint matrices cannot be proven. If triggered, stop and re-plan Option C/React rebuild.

## Fail-closed mode matrix
| Behavior | reference | demo | live |
|---|---|---|---|
| Purpose | deterministic visual scoring | local/fallback exploration | real local backend |
| REST | forbidden; no `/health`, `/status`, `/runs`, `/bt/*`, `/sim/*` | fixtures/static JSON only, banner | allowed with loading/error |
| WS | forbidden; no WebSocket construction | forbidden unless demo harness, banner | `/ws`, `/bt/ws_job`, `/sim/ws` allowed |
| Timers | no reconnect/polling loops | deterministic UI only | bounded polling/reconnect allowed |
| Random/time | no `Math.random`, drifting timestamps/counters | deterministic seed/fixture | allowed outside scoring |
| localStorage | ignore base URL/live state; no writes | preferences only, no side effects | preferences/base URL allowed; no hidden export state |
| Mutations | save/delete/run/cancel/job_meta/portfolio/audit-submit inert with visible reference message | inert/no-op with banner | local research mutations allowed with confirmation where destructive |
| Scoring | only valid visual mode | invalid final score | invalid visual score; valid live smoke |
| Failure | fail if network/WS/timer/random detected | show demo/fallback | show real error; no fake success |

## Local research mutations vs prohibited controls
Allowed only in live mode as local research/backtest actions: `/bt/strategy` save, `/bt/strategy/delete`, `/bt/run`, `/bt/job/cancel`, `/bt/job/meta`, `/bt/portfolio`, validation/extract endpoints, append-only audit submission if implemented. Destructive local research actions require visible confirmation and must say they do not export to production. Always prohibited: live order, broker login, account balance/trading/connect, hidden export, automatic production export, mutable audit edit/delete, broker runtime invocation, account trading semantics. Final strategy export remains separate from Decision Audit and behind Human Approval Gate.

## File-level plan
`remodel/index.html`: preserve static entry. `remodel/src/app.js` or split modules: mode gate first, selectors, adapters, bounded controllers, no reference side effects. `remodel/src/data.js` and `data/stom-dummy-data.json`: reference fixture source for shell/page rows/backtest/replay. `remodel/styles/theme.css`: zip visual tuning and isolate obsolete production-skin conflicts. Production `bt-tab-*`, `bt-result-area`, `sim-tab-*`, `simulation-charts` are behavior references. Backend touched only for contract-preserving gaps: `backtest_api.py`, `simulation_api.py`, `app.py`.

## Sequencing
1. Lock page IDs/routes/viewport/thresholds; implement fail-closed mode gate before adapters.
2. Freeze fixtures: shell values, rows, logs, ledger, candidates, backtest demo job, replay session; remove random/timer/network in reference.
3. Create pure view-model adapters and mode-guarded action controllers.
4. Bring condition, process, history, lab, workbench, audit to visual/function parity.
5. Implement Backtest matrix and evidence capture.
6. Implement Replay REST/WS matrix and transcript capture.
7. Regenerate 8 captures, diffs, contact sheet, score JSON, forbidden scan.
8. Package unit/static, API/integration, browser/e2e, visual, manifest evidence.

## `/bt/*` endpoint-action-evidence matrix
Every row: reference = fixture/inert/no network; live = actual endpoint with visible error state; evidence = manifest API call or reference no-network proof.
| Endpoint | Method | UI/action | Evidence |
|---|---|---|---|
| `/bt/health` | GET | connection badge | status/api_version |
| `/bt/strategies?kind=buy|sell` | GET | selectors/library | list or empty state |
| `/bt/strategy?kind&name` | GET | editor load | code/unavailable |
| `/bt/strategy/validate` | POST | validate | ok/error result |
| `/bt/variables` | GET | glossary/chips | variable list/empty |
| `/bt/extract_vars` | POST | variable chips | known/unknown |
| `/bt/legacy/self_vars?kind&name` | GET | self-vars import | rows/no-vars |
| `/bt/backfinder/preflight?kind&name` | GET | preflight | pass/fail diagnostic |
| `/bt/strategy` | POST | save strategy | confirmation; saved/error |
| `/bt/strategy/delete` | POST | delete strategy | destructive confirmation; deleted/error |
| `/bt/data_range` | GET | run date range | min/max/unavailable |
| `/bt/run` | POST | run backtest/WFO/sweep | job_id or validation error |
| `/bt/jobs` | GET | result library | job list/filters/empty |
| `/bt/job?job_id` | GET | active job/poll fallback | status/progress/log_tail |
| `/bt/job/cancel` | POST | cancel job | confirmation; canceled/error |
| `/bt/job/meta` | POST | tags/notes/favorite | local meta update |
| `/bt/ws_job?job_id` | WS | job progress | open/progress/log/done/error or fallback |
| `/bt/result?job_id` | GET | result analysis | metrics/chart data |
| `/bt/result?run_id&gen_no` | GET | evo result | run/gen result |
| `/bt/evo_gens?run_id` | GET | evo selector | generation list/empty |
| `/bt/analysis/summary` | GET | analysis details | summary payload if used |
| `/bt/analysis/equity` | GET | equity chart | equity series if used |
| `/bt/analysis/distribution` | GET | distribution | histogram if used |
| `/bt/analysis/heatmap` | GET | heatmap | heatmap payload if used |
| `/bt/analysis/underwater` | GET | drawdown | underwater series if used |
| `/bt/analysis/insights` | GET | insights | insights payload if used |
| `/bt/analysis/mae_mfe` | GET | scatter | scatter data if used |
| `/bt/analysis/exit_reasons` | GET | exit reasons | table/chart if used |
| `/bt/analysis/montecarlo` | GET | Monte Carlo | n, curves, summary |
| `/bt/analysis/orderflow` | GET | orderflow | response/unavailable |
| `/bt/analysis/gui_parity` | GET | GUI parity | parity payload/unavailable |
| `/bt/compare?job_a&job_b` | GET | A/B compare | delta metrics/chart |
| `/bt/overlay?job_ids` | GET | multi-job overlay | overlay series |
| `/bt/portfolio` | POST | portfolio combination | local analysis result |
| `/bt/report` | GET | HTML report link | opened/fetch status; no export |
Reference evidence must show zero `/bt/*` network calls, disabled/inert mutation buttons, and fixture Backtest screenshot.

## `/sim/*` endpoint-action-WS matrix
Every row: reference = fixture/inert/no network; live = actual endpoint or visible error; evidence = API calls and WS transcript.
| Endpoint/protocol | Method | UI/action | Evidence |
|---|---|---|---|
| `/sim/health` | GET | replay badge | status/api_version |
| `/sim/days?src=tick|min` | GET | day calendar | days/count/src or empty |
| `/sim/demo?src&mode` | GET | latest/top-gainer preset | date/code or unavailable |
| `/sim/stocks?date&src` | GET | stock list | stocks/empty |
| `/bt/strategies?kind=buy|sell` | GET | replay strategy selectors | strategy list/empty |
| `/sim/signals?date&src&code&buy&sell` | GET | signal overlay/log | trades or timeout/error |
| `/sim/ws` | WS | playback | transcript with actions/messages |
`/sim/ws` client actions to prove: `start` with date/src/codes/speed/agg_sec, `pause`, `resume`, `speed`, `seek`, `stop`. Server messages to handle/prove: `meta`, `bars`, `history`, `done`, `error`. Evidence must include playback start, pause/resume, speed change, seek/history replacement, stop cleanup, error display or forced-error case, and recovery/new session.

## Artifact manifest schema
Final evidence must include JSON with: `run_id`, `worktree`, `commit` or explicit unknown, `generated_at`, `mode`, `viewport {width:1920,height:1080,device_scale_factor:1}`, `thresholds {page_visual_min:95,avg_visual_min:97,page_total_min:95,avg_total_min:97}`. Each page row requires: `id`, `route`, `mode`, `screenshot`, `diff`, `weighted_visual_score`, `corrected_total_score`, `structure_score`, `functional_score`, `console {errors,warnings_allowed}`, `network {unexpected_calls,api_calls}`, `modals`, `api_evidence_ids`, `ws_transcript_ids`, `forbidden_scan_id`, `passed`, `timestamp`. Global arrays: `api_evidence [{id,endpoint,method,mode,status,artifact}]`, `ws_transcripts [{id,url,messages,artifact}]`, `forbidden_scan {passed,terms,artifact}`. No 100-point claim unless every manifest page passes, required endpoint rows have evidence or justified not-used state, and forbidden scan passes.

## Page checklist
Condition: zip shell/tabs/KPIs/generation table/winner/inspector; `/status`/`/runs`/`/ws` live only; modals; safety footer; visual/function >=95. Process: selector/menu/governance, flow map, logs, catalog, boundary contract, metadata; fixture logs; research-only cues; >=95. History: risk/PnL, lineage, summaries, archive, records, ResultDetail, compare; `/runs` live mapping; no random lineage in reference; >=95. Lab: run sidebar, stall, queue, freeze, heatmap, importance, correlation, holdout, combos, context pack; no advice/export bypass; >=95. Workbench: global state, candidate strip, HoF, heatmap, detail charts, handoff/review queue; no approval/export authority; >=95. Audit: append-only banner, checklist, OOS, evidence, decision form, ledger, metadata; no edit/delete; final export separate; >=95. Backtest: zip layout plus matrix; edit/run/progress/cancel/logs/result/WFO/sweep/report/compare/overlay/portfolio/evo; visual and functional >=95. Chart Replay: source/day/stock/strategy/agg/preset/playback/chart modes/indicators/log/watch/minimap/WS; matrix; historical replay only; visual and functional >=95.

## Acceptance criteria
Visual: 8 reference captures at 1920x1080; every weighted visual >=95; average weighted visual >=97; every corrected total >=95; average corrected total >=97; contact sheet, diffs, score JSON, manifest exist. Functional: all tabs/subtabs render; global shell persists; settings/inspector/approval modals open; audit append-only ledger/form; Backtest matrix live evidence; Replay matrix live evidence; API errors visible and never fake success. Safety: forbidden scan passes; Human Approval Gate, Append-Only Audit, research-only/local-only visible; final export separate; no broker/account/live-order/hidden-export/mutable-audit controls.

## Strengthened pre-mortem and gates
1. Fixture masking live regressions: reference manifest plus separate live API/WS matrix evidence. 2. Adapter duplication: controller boundaries reviewed and invalidation checked before continuing. 3. Secondary endpoint omission: every `/bt/*` and `/sim/*` row marked proven, inert in reference, or not-used with reason. 4. WS flakiness: transcript includes success and recoverable error paths plus cleanup after stop/navigation. 5. Safety regression: static scan, browser DOM scan, and handler/action review. 6. Score inflation: no completion wording until manifest thresholds, console/network checks, modal coverage, and forbidden scan pass. 7. Local mutation confusion: reference disables mutations; live labels local mutations as research/backtest and never export/broker/account.

## Verification plan
Planning runs no tests or servers. Execution must run focused unit/static tests for mode gate, selectors, forbidden scan, route mapping; integration/API for core, full `/bt/*`, full `/sim/*`; browser/e2e for 8 pages, modals, Backtest/Replay interactions; visual regression for captures/diffs/contact sheet/scorecard; observability package for manifest, API evidence, WS transcripts, console/network logs, worktree metadata.

## Handoff
After approval, use ultragoal for durable checkpoints. Use executor for bounded slices: mode gate, selectors, Backtest matrix, Replay matrix, visual gate, tests. Use architect to clear adapter seam before implementation expands; use critic to approve manifest/gates before execution. Team mode only if approved parallel implementation is needed.
