# TICK Dashboard Observability and Research UX 20260604

## TL;DR
> **Summary**: Repair and verify the AI condition-research dashboard so it can show the whole backtest/research process clearly: route parity, progress, engine state, logs, active strategy code/diff, Hall of Fame sorting/scrolling, Research Wiki, AI Context Pack, and quant/human-reference research panels. This is a dashboard/research-observability plan, not a production-promotion or hard-gate relaxation plan.
> **Deliverables**:
> - Fresh dashboard route parity proof for `/strategy_diff`, `/prompts`, `/ai_context_pack`, `/research_docs`, `/research_doc`, `/index_compare`, `/variable_correlation`
> - Safe stale-server diagnostic for `http://127.0.0.1:8770/ui/`
> - Backtest progress payload and UI using honest available counters only
> - Engine status/settings/log panel with CPU/engine/timeframe/config details
> - Strategy inspector repair, current strategy visibility, and previous-strategy diff
> - Research Wiki and AI Context Pack 404 repair
> - Hall of Fame total-profit sorting and verified horizontal scroll
> - Clear explanation of `gen`, GA mode, payoff, period/year, and live-data-pending states
> - Human reference graph morphology dataset and research note integration
> - Variable correlation, histogram/range, market-cap/time/year segment research workflow
> - Max-hold-count audit and sparse-buy warning if the `0/1` holding count is real
> - Evidence report and focused tests
> **Effort**: XL
> **Parallel**: Yes - backend route/state work, frontend UX work, and research analytics can run in parallel after P0 diagnostics.
> **Critical Path**: P0 route/stale-server proof -> P1 state contract -> P2 frontend visibility -> P3 research analytics -> P4 live QA -> Final verification

## Context
### Original Request
The user asked for a `$ulw-plan` based on these issues and goals:

- Dashboard backtests do not show progress like the GUI.
- Backtest engine settings, status, CPU/engine count, timeframe, and logs are not visible enough.
- `strategy_diff HTTP 404`, Research Wiki 404, and AI Context Pack 404 occur in the dashboard.
- Hall of Fame lacks total-profit sorting and usable horizontal scrolling.
- Phase detail says `실시간 데이터 대기`, but the meaning is unclear.
- Clarify whether `gen` means genetic algorithm.
- Use `docs/research/2026-06-04_condition_research_rereview_human_reference_graphs.md`.
- Use human good-result graph screenshots as research reference, but do not overclaim proof.
- Improve quant analysis: variable correlations, histograms/ranges, market-cap/time/year segmentation, recency weighting, Backfinder/optimizer research, buy/sell grammar learning, wick/turning-point candidates.
- Show the currently used condition expression and diff from the previous one so the user can inspect whether AI is improving it.

### Canonical Handoff Sources
- `docs/AGENT_HANDOFF.md`
- `docs/update_log/2026-06-03_tick_program_complete_handoff.md`
- `docs/research/2026-06-04_condition_research_rereview_human_reference_graphs.md`
- `ai_strategy_loop/dashboard/reference_strategies.json`
- `docs/reference/STOM_Good_Results/`
- Existing OMO evidence under `.omo/evidence/`

### Non-Negotiable Constraints
- Do not edit protected/runtime paths:
  - `_database/`
  - `_database_v3k_shadow/`
  - `_log/`
  - `backup/`
  - `*.db`
  - `backtest/graph/`
  - `.omx/reports/`
  - `v3k_settings*.json`
- Do not change official backtest engine math, hard gates, or `backtest/graph`.
- Do not call or wire `final_approval` or `export_winner`.
- Do not perform KHOPENAPI login/connect, live broker wiring, live order wiring, or V3K gate advancement.
- New feature toggles, if required, must default OFF.
- No blanket `taskkill`; only stop a PID the worker spawned or a PID whose command line proves it is the exact dashboard process.
- Preserve existing dirty worktree changes unless they are part of this plan and intentionally owned.
- B_* input variables may be used for strategy generation; result/leakage variables are diagnostics only.
- Human-reference similarity, image-derived metrics, and recent-year weighting are research/ranking aids only. They are not promotion proof and must not be used to tune after fixed OOS.

## Discovery Findings
### Dashboard Routes
Current source already contains the routes reported as 404:

- `ai_strategy_loop/dashboard/app.py` registers `/prompts`, `/strategy_diff`, `/ai_context_pack`, `/variable_correlation`, `/hall_of_fame`, `/strategy_code`, `/runs/compare`.
- `ai_strategy_loop/dashboard/research_api.py` registers `/research_docs`, `/research_doc`, `/index_compare`.
- Existing tests cover most individual endpoint contracts:
  - `tests/unit/test_dashboard_strategy_diff.py`
  - `tests/unit/test_dashboard_prompts.py`
  - `tests/unit/test_dashboard_ai_context_pack.py`
  - `tests/unit/test_dashboard_research_docs.py`
  - `tests/unit/test_variable_correlation.py`

Observed runtime clue from prior verification:

- `http://127.0.0.1:8770/health` returned OK.
- The live `8770` OpenAPI did not include several current routes.
- Therefore the first hypothesis is stale/wrong dashboard process, not missing source routes.

### GUI Progress Reference
The desktop GUI already has progress semantics:

- `ui/ui_update_progressbar.py` computes percent, elapsed time, and remaining time.
- It uses `back_start_time`, `shared_cnt`, `back_tick_cunsum`, `back_count`, and Optuna counters.
- `ui/ui_backtest_engine.py` creates `shared_cnt`, `back_tick_cunsum`, and `back_count`.
- `backtest/backengine_base.py` increments the shared counter while engine work proceeds.

The AI loop must not fake this exact tick progress unless a real counter is available. It can honestly show phase/generation progress and any real backtest counter exposed through the runner.

### AI Loop State Reference
The AI loop already publishes useful state:

- `ai_strategy_loop/controller/loop.py::_publish_live`
- `ai_strategy_loop/controller/state.py::to_loop_state`
- `ai_strategy_loop/controller/state.py::build_active_config`
- `ai_strategy_loop/controller/contract.py::LatestInfo`
- `ai_strategy_loop/controller/contract.py::LoopState`

Current useful fields include phase, message, recent logs, current step, phase start time, generation start time, step timings, generations, and active config.

### Research Surfaces
Current research-related files and routes:

- `ai_strategy_loop/dashboard/reference_strategies.json`
- `docs/reference/STOM_Good_Results/`
- `ai_strategy_loop/dashboard/app.py` routes for Hall of Fame, reference screenshots, edge ratio, feature importance, variable correlation, strategy diff, and backtest detail.
- `ai_strategy_loop/dashboard/frontend/chart.jsx`
- `ai_strategy_loop/dashboard/frontend/analysis.jsx`
- `ai_strategy_loop/dashboard/frontend/research-lab.jsx`
- `ai_strategy_loop/dashboard/frontend/strategy-inspector.jsx`
- `ai_strategy_loop/autopsy/analyze.py`
- `ai_strategy_loop/autopsy/segment.py`
- `ai_strategy_loop/fitness/correlation.py`
- `ai_strategy_loop/fitness/edge_ratio.py`
- `ai_strategy_loop/fitness/feature_importance.py`

## Metis Review Incorporated
Metis found no contradictions, but required the final plan to resolve these gaps:

- Route parity must mean fresh `create_app()` route/OpenAPI parity plus frontend fetch parity. Live `8770` is diagnostic evidence only.
- Safe live verification must use a fresh, owned alternate-port server first.
- AI dashboard progress must be generation/phase progress unless a real per-backtest counter is exposed.
- Engine status needs an explicit schema with backward-compatible defaults.
- Hall of Fame total profit must use a concrete metric name.
- Human graph morphology must prefer structured report/JSON data and treat image-only inference as low confidence.
- Recency weighting must be research-only and must not affect hard gates, winner selection, or OOS verdicts.
- Analytics endpoints need row limits/downsampling/caching so they do not scan huge CSV pools unbounded.
- Context packs/logs/prompts must preserve secret redaction behavior.

## Definition Of Done
- A new or updated evidence folder exists, for example:
  - `.omo/evidence/tick-dashboard-observability-research-ux-20260604/`
- Focused route/state/frontend/research tests pass.
- Fresh app route parity proves the source app exposes every frontend-called route listed in this plan.
- Alternate-port dashboard smoke passes without mutating protected/runtime paths.
- If live `8770` is stale, the evidence report documents PID, command line if discoverable, OpenAPI mismatch, and safe restart recommendation. It does not kill the process unless ownership is proven.
- Dashboard shows:
  - backtest progress/elapsed/ETA or an honest "counter unavailable" state
  - engine status/settings/logs
  - current strategy buy/sell code
  - previous diff
  - test period/year/timeframe
  - payoff explanation
  - `gen = generation` and GA mode only when `evolution_mode == "ga"`
  - Hall of Fame total-profit sort and usable horizontal scroll
  - Research Wiki and AI Context Pack without 404 on a fresh server
- Research panels or artifacts include:
  - variable correlations
  - histograms/ranges
  - market-cap/time/year segments
  - human-reference morphology summary
  - max-hold-count audit
- No official engine/hard-gate/protected-path/live/export behavior is changed.
- Final report separates UX/research improvements from actual human-level/OOS performance proof.

## Execution Strategy
### Parallel Waves
Wave 1 is diagnostic and mostly sequential. Waves 2 and 3 can run in parallel after P0.

| Wave | Focus | Parallelizable |
|---|---|---|
| P0 | Safety snapshot, route parity, stale-server diagnosis | Limited |
| P1 | Backend state contracts for progress, engine status, logs | Yes |
| P2 | Frontend UX repair and visibility | Yes after P1 schema |
| P3 | Research analytics and human-reference artifacts | Yes after P0 |
| P4 | Max-hold and strategy-code/diff audit | Yes after P0 |
| P5 | Fresh dashboard live-smoke and report | No |
| Final | Verifiers and protected-path audit | No |

## TODOs
- [x] P0 - Safety snapshot, route parity, stale-server diagnosis, and evidence capture.
- [x] P1 - Backtest progress and engine state contract with focused tests.
- [x] P2 - Frontend dashboard UX repair for strategy diff/code, wiki/context pack, labels, Hall sorting/scroll.
- [x] P3 - Research analytics and human-reference artifacts.
- [x] P4 - Max-hold count and sparse-buy audit.
- [x] P5 - Fresh dashboard live-smoke and evidence report.
- [x] Final - Focused regression, nonrelease sync, protected-path audit, and cleanup evidence.

## P0 - Safety Snapshot And Route Parity
### Goal
Determine whether 404s are source bugs, stale running server bugs, or frontend/base-url bugs before changing code.

### Tasks
1. Capture current branch, commit, dirty status, and active dashboard process evidence.
2. Read canonical handoff docs and the human-reference research note.
3. Add a consolidated route parity test if missing:
   - Build the app through the same production `create_app()` path.
   - Assert frontend-called routes exist in `app.routes`.
   - Assert `/openapi.json` contains every route that should be documented.
   - Assert key read-only GET routes return non-404 through `TestClient`.
4. Compare frontend fetch targets against backend route names:
   - `/strategy_diff`
   - `/prompts`
   - `/ai_context_pack`
   - `/research_docs`
   - `/research_doc`
   - `/index_compare`
   - `/variable_correlation`
5. Start a fresh dashboard only on an owned alternate port.
6. Curl:
   - `/health`
   - `/openapi.json`
   - every route above
7. Inspect live `8770` only as diagnostic evidence:
   - owner PID
   - command line if available
   - route list mismatch
   - start time
8. Do not stop or restart `8770` unless process ownership is proven and the executor intentionally owns that server.

### Acceptance
- Fresh source app proves non-404 route parity.
- If 8770 still returns 404, the evidence clearly states it is stale/wrong-process behavior.
- No protected files are touched.

## P1 - Backtest Progress And Engine State Contract
### Goal
Expose dashboard-visible backtest progress, elapsed time, ETA, engine settings, engine state, and logs without pretending to have counters that do not exist.

### Schema Decision
Add backward-compatible optional payload objects:

- `latest.backtest_progress` or `page_data.backtest_progress`
- `latest.engine_state` or `page_data.engine_state`

The implementation should prefer one consistent location and keep older `current_state.json` payloads readable.

### Backtest Progress Fields
Use these fields when known:

- `source`: `gui_counter`, `loop_generation`, `runner_counter`, or `unavailable`
- `phase`
- `current_gen`
- `max_generations`
- `done_units`
- `total_units`
- `percent`
- `elapsed_sec`
- `eta_sec`
- `timeframe`
- `period_start`
- `period_end`
- `message`

Rules:

- If a real counter is unavailable, show generation/phase progress only.
- Do not import GUI shared counters into the AI loop.
- Do not fabricate tick-level percent.
- If ETA cannot be computed honestly, set `eta_sec = null` and show a clear pending label.

### Engine State Fields
Expose:

- `cpu_count`
- `process_cpu_percent` if cheap and already available
- `bt_engine_count`
- `bt_warm_engine_count`
- `effective_engine_count`
- `bt_engine_mode`
- `bt_timeframe`
- `is_tick`
- `period_start`
- `period_end`
- `start_time`
- `end_time`
- `buy_start_time`
- `buy_end_time`
- `warm_prepared`
- `back_count` if known
- `recent_logs`
- `active_config`
- `run_id`

### Tests
- Existing timing/state tests:
  - `tests/unit/test_process_timing.py`
  - `tests/unit/test_state_contract.py`
  - `tests/unit/test_publish_live_page_data.py`
- Add focused tests for:
  - progress defaults for old payloads
  - percent/ETA computation when total/done units exist
  - no fake percent when units are absent
  - engine_state includes config and CPU/engine fields
  - recent logs are bounded and redacted

### Acceptance
- Dashboard API can report progress, elapsed, and ETA when data is available.
- Dashboard API can report engine settings and logs for the active loop.
- No official backtest engine behavior changes.

## P2 - Frontend Dashboard UX Repair
### Goal
Make the running dashboard understandable to a human operator and useful for AI-human joint condition research.

### Tasks
1. Strategy Inspector:
   - Make `/strategy_diff` errors non-fatal and explicit.
   - Show selected run/gen/strategy source.
   - Show buy and sell strategy code.
   - Show previous-generation diff when available.
   - Show the prompt used for AI request where available.
2. Main current-strategy panel:
   - Show current active condition expression.
   - Show prior condition expression and concise diff.
   - Show whether the strategy is only research, selected, frozen, or live-disabled.
3. Research Wiki:
   - Fix `/research_docs` and `/research_doc` route use on fresh app.
   - Continue to state that screenshots are reference only, not live proof.
   - Render markdown more readably if supported without adding a new framework.
4. AI Context Pack:
   - Fix `/ai_context_pack` route use on fresh app.
   - Preserve redaction/no-secret tests.
   - Show the exact prompt/context pack used for AI requests when available.
5. Phase Detail:
   - Replace or explain `실시간 데이터 대기`.
   - Use clear states such as:
     - backend connected, no live snapshot yet
     - run idle
     - loop running, progress available
     - loop running, counter unavailable
6. `gen` and GA wording:
   - Show `gen = generation`.
   - Show `GA` only when `active_config.evolution_mode == "ga"`.
   - If mode is `hillclimb`, say generation is an iteration, not a genetic algorithm population.
7. Payoff and period labels:
   - Explain payoff as average win divided by average loss where applicable.
   - Always show test period and year buckets.
8. Hall of Fame:
   - Add sort option for total profit using the canonical available field:
     - prefer `profit_krw`
     - fallback `final_profit`
     - fallback `total_profit`
   - Verify and fix horizontal scroll with real overflow, not just a CSS declaration.
9. Cost display:
   - Display costs to one decimal place where the dashboard shows cost/slippage-like numeric fields.

### Tests
- Existing frontend source tests:
  - `tests/unit/test_dashboard_strategy_prompt_frontend.py`
  - `tests/unit/test_dashboard_wiki_frontend.py`
  - `tests/unit/test_dashboard_research_lab_frontend.py`
  - `tests/unit/test_dashboard_run_compare_frontend.py`
  - `tests/unit/test_dashboard_hall_of_fame.py`
- Add or update tests for:
  - total-profit Hall sort option
  - current strategy/diff labels
  - `gen`/GA wording
  - live-data-pending wording
  - route paths remain aligned

### Acceptance
- The user can inspect what the AI is using now, what changed from the previous strategy, and why the dashboard is waiting when data is pending.
- The user can sort Hall of Fame by total profit and scroll wide result tables.

## P3 - Research Analytics And Human Reference Artifacts
### Goal
Build better research feedback for condition development without leaking OOS or overfitting hard gates.

### Human Reference Graph Morphology
Use source priority:

1. Structured metrics in `ai_strategy_loop/dashboard/reference_strategies.json`
2. Reports under `docs/reference/STOM_Good_Results/`
3. Image screenshots under `docs/reference/STOM_Good_Results/`

Image-derived data must be tagged low-confidence unless backed by structured report data.

Metrics to derive where possible:

- cumulative return shape
- slope and slope stability
- drawdown depth/frequency
- recovery time
- late-period collapse score
- profit concentration
- trade density
- staircase smoothness
- max-hold-count corridor
- year/period labels

### Variable Correlation And Histogram Research
Extend existing research surfaces instead of inventing a new system:

- `ai_strategy_loop/fitness/correlation.py`
- `ai_strategy_loop/fitness/edge_ratio.py`
- `ai_strategy_loop/fitness/feature_importance.py`
- `ai_strategy_loop/autopsy/analyze.py`
- `ai_strategy_loop/autopsy/segment.py`

Add or expose:

- variable-to-result correlation heatmap data
- variable-to-variable correlation heatmap data
- histogram/range summaries for buy-time variables
- win/loss range contrast
- market-cap segment summaries
- time-of-day segment summaries
- year-bucket summaries
- pairwise interaction top-k candidates

Performance rules:

- Row limits are mandatory.
- Downsampling is acceptable if reported.
- Read-only SQLite/CSV access only.
- Cache or memoize expensive dashboard requests if needed.
- Return clear `sample_count`, `truncated`, and `source` fields.

### Recency Weighting Research
Add a research-only recency lens:

- During 2023-2025 training analysis, later years may be weighted higher for ranking/reporting.
- 2026 must not influence training, selector tuning, prompt tuning, or candidate freeze if it is fixed OOS.
- Any recency-weighted score must be labelled `research_score`, not promotion score.
- Suggested initial weights for reporting only:
  - 2023: 1.0
  - 2024: 1.25
  - 2025: 1.5

### Buy/Sell Grammar And Candlestick Ideas
Read before generation-related changes:

- `utility/ai_agent/strategy.txt`
- `utility/ai_agent/rules.txt`

Research-only candidate ideas:

- buy: lower wick, pullback recovery, intraday turning point, time-window expansion, market-cap-conditioned filters
- sell: upper wick, giveback control, turn-down exit, trailing-style exit, existing sell-condition form learning

Rules:

- This phase produces analysis artifacts and prompt candidates only.
- Any generation behavior change needs a separate default-OFF toggle and separate tests.
- No hard-gate or selector relaxation.

### Backfinder/Optimizer Research
First identify what `Backfinder` or `백파인터` refers to in this repo.

- If a module exists, map its inputs/outputs and tests.
- If no module exists, document the gap and propose a follow-up plan.
- Do not implement a speculative optimizer in this plan without a concrete code owner and tests.

### Acceptance
- The dashboard or evidence folder gives the user and AI enough context to study variables, ranges, year shifts, and human-reference graph patterns.
- No research artifact is represented as OOS proof.

## P4 - Max-Hold Count And Sparse-Buy Audit
### Goal
Determine whether low simultaneous holdings (`0/1`) is a real strategy behavior, a metric extraction bug, or a dashboard display bug.

### Tasks
1. Trace max-hold-count source fields from run CSV/database/state payloads.
2. Compare:
   - run detail
   - Hall of Fame
   - generation table
   - strategy inspector
   - run compare console
3. Add tests that pin max-hold-count parsing and display.
4. Add a dashboard warning only if confirmed:
   - `max_hold_count <= 1`
   - enough trades exist to make sparse holding suspicious
5. Add total profit, return, time, period, and year info to run comparison console if missing.

### Acceptance
- The user can tell whether a strategy is too sparse, and whether that is a real backtest behavior.

## P5 - Live Dashboard Smoke And Evidence
### Goal
Prove the dashboard works from the same browser-facing surface the user uses, without mutating runtime/protected paths.

### Safe Server Procedure
1. Choose an unused alternate port.
2. Start a fresh dashboard process owned by the executor.
3. Do not POST `/start` or trigger live trading/backtest mutation unless the plan phase explicitly needs a read-only run.
4. Curl:
   - `/health`
   - `/openapi.json`
   - `/strategy_diff`
   - `/prompts`
   - `/ai_context_pack`
   - `/research_docs`
   - `/research_doc`
   - `/variable_correlation`
   - `/hall_of_fame`
   - `/reference_screenshots`
5. If browser QA is feasible, inspect `http://127.0.0.1:<alt>/ui/`.
6. Stop only the owned alternate-port process.

### Evidence
Write:

- route parity output
- alternate-port curl output
- screenshot or text QA note
- live 8770 stale-server diagnostic if relevant
- protected-path status
- test output summary

## Final Verification
Run focused tests first:

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_prompts.py tests/unit/test_dashboard_ai_context_pack.py tests/unit/test_dashboard_research_docs.py tests/unit/test_variable_correlation.py tests/unit/test_dashboard_hall_of_fame.py tests/unit/test_process_timing.py tests/unit/test_state_contract.py tests/unit/test_publish_live_page_data.py tests/unit/test_dashboard_phase_mapping.py tests/unit/test_dashboard_runs_enriched.py -q
```

Run final safety checks:

```powershell
git diff --check
python scripts/verify_nonrelease_sync.py
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

Optional, only if dashboard source was changed and a fresh server can be started safely:

```powershell
$env:PYTHONUTF8='1'
# start dashboard on an unused alternate port; verify /health and /openapi.json; stop only that owned PID
```

## Final Verification Wave
- [ ] Final - Focused tests, safety checks, protected-path audit, and final report.

## Reporting Requirements
The final implementation report must state:

- What was fixed.
- What remains research-only.
- Whether current `8770` was stale and what evidence proves it.
- Whether any dashboard endpoint still returns 404.
- What progress fields are real counters versus phase/generation estimates.
- What `gen` means and whether GA mode is active.
- Whether max-hold-count `0/1` is real or a display/extraction issue.
- What human-reference graph features were extracted and their confidence level.
- What tests and safe server smoke commands passed.
- That no hard gate, official engine math, protected runtime path, live broker path, `final_approval`, or `export_winner` was touched.

## Recommended Start Command
```powershell
$start-work tick-dashboard-observability-research-ux-20260604
```

For an extra review pass before execution:

```powershell
$ulw-plan high accuracy review .omo/plans/tick-dashboard-observability-research-ux-20260604.md
```
