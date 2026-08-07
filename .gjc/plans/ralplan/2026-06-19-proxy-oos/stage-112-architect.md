## Summary
Planner stage 112 is architecturally sound in direction: it preserves the brownfield dashboard, leads with result recovery and identity, and reuses BacktestTab and BtResultArea rather than inventing ten new screens. I recommend WATCH and COMMENT, with two execution-time amendments: make condition identity code-hash based with explicit legacy confidence, and remove the current Workbench-owned History and Compare duplication path instead of creating a second History.

## Analysis
Spec compliance is mostly satisfied. The spec requires condition expression as long-term identity and backtest result as evidence; current `BacktestJobSpec` stores buy, sell, start, end, timeframe, and mode, while `BacktestJobRecord` stores job_id, status, csv_path, metrics, mode_result, and user metadata (`ai_strategy_loop/dashboard/backtest_jobs.py:45-105`). Evolution evidence is keyed by `(run_id, gen_no)` in `generations` with buy_name, sell_name, csv_path, metrics, and no code copy (`ai_strategy_loop/controller/state.py:120-170,300-410`). The planner fields `condition_identity`, `evidence_id`, `source_type`, and additive `/bt/result` metadata are the right Phase 1 seam, but the identity rule must not collapse to mutable strategy names.

Current result access supports the reuse thesis. `BacktestTab` centralizes run, editor, result, evo, and compare state and auto-switches to result view on selected job or generation (`ai_strategy_loop/dashboard/frontend/bt-tab-root.jsx:25-66,179-265`). `BtResultArea` fetches `/bt/result` for either job_id or run_id plus gen_no and renders the analysis stack (`ai_strategy_loop/dashboard/frontend/bt-result-area.jsx:40-330`). `/bt/result` returns similar but not canonical payloads for job and run/gen, with no shared ResultDetail contract (`ai_strategy_loop/dashboard/backtest_api.py:646-712,819-860`). The planner shared ResultDetail is therefore aligned with the existing seam.

Result recovery sequencing is correct. Persisted running or pending jobs are currently converted to `status="error"` with `phase="stale"` on restart (`ai_strategy_loop/dashboard/backtest_jobs.py:702-724`), while the UI library only opens success and no_trades rows (`ai_strategy_loop/dashboard/frontend/bt-tab-run.jsx:640-672`) and badges lack stale or artifact-missing (`ai_strategy_loop/dashboard/frontend/bt-tab-utils.jsx:43-51`). A status taxonomy plus open, recover, and rerun actions before IA repaint is the right dependency order.

IA dedup is the biggest watch item. The planner correctly keeps three top-level routes and renames records/history in `ui-contract.jsx`, but the current implementation has `records` as campaign/docs/update_log lookup (`ai_strategy_loop/dashboard/frontend/ui-contract.jsx:12-30`, `dashboard-inventory.jsx:1-40`) while Workbench already contains `_RpHistory` and `_RpRunCompare`, and `_RpHistory` embeds `window.BtResultArea` for historical run/gen detail (`ai_strategy_loop/dashboard/frontend/rp-heatmap.jsx:426-570`). Execution must explicitly move or demote those Workbench components; otherwise Phase 2 will create duplicate History and Compare surfaces.

Chart replay phasing is sound. The current replay architecture preserves backend frames and client bars, supports WS pause, resume, speed, and seek, and sends history snapshots after seek (`ai_strategy_loop/dashboard/frontend/sim-tab-root.jsx:180-360`, `ai_strategy_loop/dashboard/simulation_api.py:469-690`). Existing render caps are fixed (`_SIM_LWC_MAX=5000`, `_SIM_WINDOW=400`; `ai_strategy_loop/dashboard/frontend/sim-chart-utils.jsx:15-18`) rather than adaptive. The planner rule that full bars are preserved and only render input is adaptive is the right constraint.

Legacy Phase 4 staging is appropriate. `ui/ui_vars_change.py` converts and sorts `self.vars` by executing replacement text and index rewriting (`ui/ui_vars_change.py:38-170`), and `backtest/backfinder.py` is a queue, DB, and sys.exit workflow that requires `self.tickcols` and `self.tickdata` in the selected strategy (`backtest/backfinder.py:43-69`). These are not safe Phase 1 foundations; staged adapter tests and delayed BackFinder UI are correct.

Steelman antithesis: Option C, a new domain store for Condition, Result, History, and HOF, would give the cleanest ontology. Immutable condition hashes, evidence rows, artifact states, and ownership rules could be enforced in one DB instead of scattered JSON, loop_runs.db, and strategy DB lookups. That would reduce UI adapter complexity and make History a real archive instead of a composition of BacktestTab, Workbench, and records surfaces. The strongest argument against the planner is that additive fields across `/bt/jobs`, `/bt/result`, `ResearchRecordsPanel`, and Workbench can become a semi-hidden distributed domain model.

Synthesis: despite the antithesis, the brownfield constraints favor Option A. Existing seams already support job and run/gen detail, protected DB boundaries are sensitive, and the spec explicitly rejects duplicate top-level screens and engine replacement. The synthesis is incremental reuse plus one explicit contract: namespaced `evidence_id`, code-hash-first `condition_identity`, and a presentational ResultDetail body shared by BacktestTab, History, Workbench links, and HOF links.

## Root Cause
The core architectural risk is identity drift: current dashboard evidence is keyed by operational artifacts such as job_id, `(run_id, gen_no)`, strategy names, and csv_path, while the target product language treats the condition expression as durable identity. Without explicit identity derivation and legacy-confidence semantics, UI reuse can still merge or compare the wrong evidence when strategy names are reused or old job JSON lacks code snapshots.

## Findings
- MEDIUM — `backtest_jobs.py:45-105`, `controller/state.py:120-170,300-410`, `backtest_api.py:646-712`: Result identity is directionally planned but underspecified. Impact: mutable buy/sell names can be mistaken for durable condition identity, especially for old job JSON and strategy DB rewrites. Fix: Phase 1 must define `evidence_id = job:<job_id> | gen:<run_id>:<gen_no> | history:<id>`, `condition_identity.kind = code_hash | name_only_legacy`, normalized buy/sell code hashes when available, and a visible legacy confidence or artifact note.
- MEDIUM — `rp-heatmap.jsx:426-570`, `ui-contract.jsx:12-30`, `dashboard-inventory.jsx:1-40`: History and Compare ownership migration misses the current Workbench implementation file where History and RunCompare actually live. Impact: execution can leave `_RpHistory` and `_RpRunCompare` in Workbench while adding a renamed History route, violating IA dedup. Fix: add `rp-heatmap.jsx` to Phase 2 and Phase 3 file list and decide one migration path: move History and Compare to `/ui/evolution/records` or make Workbench render links into History mode only.
- LOW — `bt-tab-run.jsx:179-184,640-672`: BacktestTab auto-opens only success, while no_trades is already a valid openable result state. Impact: acceptance wording that run completion opens detail may remain inconsistent for no-trade completions. Fix: include no_trades in post-run detail auto-open, while failed, cancelled, and stale rows expose status-aware open, recover, or rerun actions rather than silent detail open.
- LOW — `bt-result-area.jsx:40-330`: `BtResultArea` is both fetch container and detail renderer. Impact: adding History item payloads directly risks source-specific branches in the shared component. Fix: split a small `ResultDetailBody` that receives canonical payload and actions from containers for job, run/gen, and history item; keep `/bt/result` compatibility fields.
- LOW — `sim-tab-root.jsx:180-360`, `sim-chart-utils.jsx:15-18`, `simulation_api.py:469-690`: Replay rendering has fixed caps but not adaptive selection. Impact: Phase 4 could accidentally downsample the authoritative store instead of just the render input. Fix: keep `barsRef` and server frames full, derive per-engine renderBars via viewport, device, and count budget, and leave seek, export, and signal logic on full data.

## Recommendations
1. Amend Phase 1 handoff with the exact identity contract and legacy fallback semantics before implementation.
2. Amend Phase 2 and Phase 3 file lists to include `rp-heatmap.jsx` and explicitly retire or relocate `_RpHistory` and `_RpRunCompare` from Workbench ownership.
3. Extract ResultDetail as presentational body plus source containers; do not fork separate Backtest, History, and HOF detail implementations.
4. Keep API changes additive: preserve `/bt/result` fields `available`, `job_id`, `run_id`, `gen_no`, `status`, `metrics`, `analysis`, and `mode_result`; add derived identity and action fields without changing existing status meanings until UI consumers are updated.
5. Phase 4 replay must decimate or window render inputs only, never authoritative bars or backend frames. Phase 4 legacy work must wrap `self.vars` and BackFinder behind tested adapters and jobs, not direct web request imports.

## Architectural Status
WATCH

## Code Review Recommendation
COMMENT

## Trade-offs
| Option | Upside | Downside | Verdict |
|---|---|---|---|
| Planner Option A: BacktestTab-centered incremental reuse | Reuses `BacktestTab`, `/bt/result`, `BtResultArea`, existing WS replay; lowest brownfield risk | Requires precise adapters across JSON jobs, loop DB, Workbench, and History | Best path with identity and IA amendments |
| New domain store | Clean identity/evidence schema and archive ownership | DB cutover, migration, protected-path and live-loop risk; exceeds spec constraints | Strong antithesis, not recommended now |
| History-first repaint | Users see final IA early | Repaints stale, cancelled, or unopenable evidence before recovery; duplicates Workbench history | Reject |
| Adaptive replay in backend | Lower client payload and render cost | Risks data loss and seek/export inconsistencies | Reject for Phase 4; render-only adaptation preferred |
