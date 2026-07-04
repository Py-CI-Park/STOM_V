# CSS_V7 Repair And Resume Plan C/B/D

## Scope

Run the user's priority 1~7 sequence after the Plan C T5 blocker analysis.
This plan extends the original handoff order without replacing the source
Plan C/B/D documents.

## Invariants

- Research lane only; keep `hypothesis_seed`.
- No A3, promotion-review, export, live, or final promotion changes.
- No UPDATE/DELETE against strategy DBs. Repair rows must be append-only
  variants unless the user separately approves a destructive correction.
- Do not run Plan B before repaired CSS_V7 smoke evidence exists.
- OOS-blind: no OOS before freeze/preregistration.
- Do not clean/stage dashboard seven files, `.gjc`, or unrelated `.omo` residue.
- No `git add -A`.

## Read-First Sources

- `.omo/plans/ai-loop-full-next-execution-20260703.md`
- `docs/update_log/2026-07-03_ai_loop_full_implementation_session_handoff.md`
- `docs/research/condition_research/plans/2026-07-02_plan_C_chart_sulsa_validation_protocol.md`
- `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md`
- `docs/research/condition_research/plans/2026-07-02_plan_D_seed_research_program.md`
- `docs/research/condition_research/chart_sulsa/2026-07-02_chart_sulsa_v7_condition_catalog.md`
- `docs/research/condition_research/chart_sulsa/provenance_registry.jsonl`
- `docs/update_log/2026-07-03_css_v7_root_cause_before_plan_b.md`

## TODOs

- [x] P1. CSS_V7 append-only fixcall repair and arity gate

  Purpose: unblock Plan C without mutating original CSS_V7 DB rows.

  Acceptance:
  - Read-first receipt exists for this plan and the source documents.
  - A failing test captures that `self.Buy(...7 args)`/`self.Sell(...7 args)`
    is invalid for STOM runtime and that repaired variants use zero-arg calls.
  - A repair script creates `*_FIXCALL` rows in `ai_strategy_loop/state/loop_strategies.db`
    with backup, INSERT-only semantics, and collision abort.
  - Repaired pairs are written under `artifacts/chart_sulsa_validation_20260702/`.
  - Static arity gate reports zero invalid runtime calls for repaired rows.
  - Original CSS_V7 rows are not updated or deleted.
  - Evidence and timing are appended to `.omo/start-work/ledger.jsonl`.

- [x] P2. Plan C T5 repaired smoke validation

  Purpose: rerun CSS_V7 smoke on repaired pair list before any Plan B work.

  Acceptance:
  - Positive control is healthy or an explicit blocker is written.
  - Combo-first order is preserved using repaired pair names.
  - Tick and min smoke produce honest ok/error/no_trades statuses.
  - All pairs are classified `go|no_go|hold` for the smoke stage.
  - Revival registry is append-only for no_go pairs.

- [x] P3. Plan C train/OOS/WF/slippage for smoke survivors

  Purpose: finish Plan C classification and export Plan D seed-pool input.

  Acceptance:
  - Train is measurement-only, with comparator where available.
  - OOS usage is preregistered and logged.
  - WF/slippage are advisory as defined by Plan C.
  - Every unique repaired pair has final status `survivor|rejected|hold`.

- [x] P4. Plan B B1.1-B1.2 576 seed generation and loop DB registration

  Purpose: generate lattice seeds and register them INSERT-only.

  Acceptance:
  - `seed_count` is 576 unless a documented lane/family filter is used.
  - Loop DB registration has backup, collision check, pairs JSON, and provenance JSONL.
  - Duplicate-name abort is tested against a copied DB.

- [x] P5R. Plan B P5 root-cause repair before full smoke

  Purpose: remove the known blockers before resuming Plan B full smoke.

  Acceptance:
  - Lattice pair/DB strategy names are checked for Windows filename safety.
  - Existing `LAT_lattice_v1:...` rows remain untouched; sanitized strategy-name rows are added INSERT-only.
  - `pairs_tick.json` and `pairs_min.json` are regenerated with sanitized names, with a mapping ledger.
  - Batch evaluation records warm success + `csv=no` + missing metrics as `no_trades`, not generic `error`.
  - The 14 sampled tick seeds have a gate-by-gate feasibility audit.
  - Threshold relaxation need is decided before any full smoke.
  - Only a sanitized 20-pair stratified acceptance probe is run; full 288 tick/min smoke remains blocked.

  Result 2026-07-04:
  - Legacy `LAT_lattice_v1:...` rows were preserved; sanitized filename-safe rows were added INSERT-only.
  - `pairs_tick.json` and `pairs_min.json` now point to sanitized names, with mapping ledger.
  - Sanitized acceptance probe used 20 pairs only and returned `ok=20`, `gate_passed=0`, `trade_count=24..1418`.
  - Threshold relaxation is not required before resuming full smoke; later refinement is still needed because no sampled pair passed performance gates.

- [ ] P5. Plan B B1.3 overnight smoke batch

  Purpose: run tick first, then min, and export smoke results.

  Status 2026-07-03: blocked before full batch. Tick first10 plus a
  stratified 4-pair probe produced 14/14 `status=error` with raw backtest
  `success` but `csv=no`, so running the full 288 tick pairs would likely hit
  the Plan B consecutive-error stop condition before producing useful smoke
  results.

  Status 2026-07-04: P5R resolved the pre-full-smoke blocker. Full 288 tick
  smoke and min smoke are still not run in this selected-range session.

  Pause 2026-07-04: tick smoke was partially run with the wrong official
  profile (`2025-01-01~2025-03-31`, warm 8). The original run plus resume01
  through resume07 produced 254/288 rows (`ok=238`, `error=16`,
  `gate_passed=0`), but these outputs are smoke/reference evidence only and
  must not be used for survivor/rejection/P6 decisions. Do not continue
  chunk08~chunk10. First read
  `docs/update_log/2026-07-04_plan_b_lattice_wrong_profile_pause_handoff.md`
  and run a P5 profile audit for DB-full-period + warm64 configs.

  Quant midreview 2026-07-04: gate_passed=0 is decomposed in
  `docs/update_log/2026-07-04_quant_midreview_gate_zero_diagnosis_handoff.md`.
  Verdicts: CSS_V7 non-OPT is invalid as complete strategies (demote to clause
  fragments); lattice seeds are map-purpose seeds, not promotion candidates.
  The P5 profile audit scope is extended with 4 items: gate-param propagation
  audit (config `min_daily_trades 0.3` vs effective `0.5`), chunk 40-60 pairs
  plus warm-engine restart protocol (gen154~169 timeout streak), success
  criterion switched to coverage-map completion (per-cell trades and gross/net
  EV via `fitness/lift.py`), and gate_passed count demoted to advisory.

  Profile audit 2026-07-04: completed as static audit only; no preflight or
  288 full run was executed. Evidence:
  `docs/update_log/2026-07-04_p5_profile_audit_official_config_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_profile_audit_official_full_warm64_20260704.json`.
  Official configs now use DB-full-period + warm64 and align configured/effective
  gates at `min_daily_trades=0.5`, `mdd_cap=35`. Tick runtime policy is
  09:00~09:28 (raw DB reaches 09:30); min policy is 09:00~15:19.

  Tick preflight 2026-07-04: executed with official DB-full-period + warm64.
  Evidence:
  `docs/update_log/2026-07-04_p5_tick_preflight_failfast_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_preflight_official_full_warm64_20260704_receipt.json`.
  Result: 4/4 honest `ok` rows, `gate_passed=0`, warm prepare `back_count=2424`.
  Full-run protocol 2026-07-04: reviewed and committed in
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_full_run_protocol_after_preflight_20260704.json`.
  Next allowed action is pilot12 only with `--fail-fast-timeout`; single-run 288,
  chunk02+, min, P6, and P7 remain blocked until pilot/chunk receipts allow them.
  Pilot12 2026-07-04: executed cleanly with official DB-full-period + warm64 and
  `--fail-fast-timeout`. Evidence:
  `docs/update_log/2026-07-04_p5_tick_pilot12_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_pilot12_official_full_warm64_20260704_receipt.json`.
  Result: 12/12 honest `ok` rows, `gate_passed=0`, MDD `280.14~1558.72`,
  profit `-472,898,110~-42,046,738`. This is process-clean but
  trading-quality-bad; pilot rows are not survivors. Next allowed action is
  24-pair tick chunk01 only as coverage-map evidence; min, P6, and P7 remain
  blocked until official tick export exists.
  Chunk01 2026-07-04: executed cleanly with official DB-full-period + warm64.
  Evidence:
  `docs/update_log/2026-07-04_p5_tick_chunk01_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk01_official_full_warm64_20260704_receipt.json`.
  Result: 24/24 honest `ok` rows, `gate_passed=0`, MDD `280.14~1558.72`,
  profit `-472,898,110~-42,046,738`. Chunk01 is coverage-map evidence only;
  rows are not survivors. Next allowed action is chunk02 only; min, P6, and
  P7 remain blocked until official tick export exists.
  Chunk02 2026-07-04: executed cleanly with 24/24 honest `ok` rows,
  `gate_passed=0`, MDD `338.29~1038.66`, profit
  `-692,611,103~-34,363,738`. Evidence:
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk02_official_full_warm64_20260704_receipt.json`.
  Chunk02 is coverage-map evidence only; next allowed action is chunk03 only.
  Chunk03 2026-07-04: executed cleanly with 24/24 honest `ok` rows,
  `gate_passed=0`, MDD `255.82~1470.77`, profit
  `-514,230,966~-12,886,150`. Evidence:
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk03_official_full_warm64_20260704_receipt.json`.
  Chunk03 is coverage-map evidence only; next allowed action is chunk04 only.

  Acceptance:
  - Resume manifest and first-10-pair timing estimate are written.
  - Tick smoke result export exists before min starts.
  - Any cleanup uses dry-run inventory and explicit PID exclusion.

- [ ] P6. Plan B B2-B5 coverage, refinement, OOS, portfolio

  Purpose: convert smoke results into go/no_go, refine go cells, freeze before OOS,
  then assemble a portfolio only with 2+ OOS survivors.

  Acceptance:
  - coverage/gaps/batch_plan JSONs exist per lane.
  - no_go seeds are appended to revival registry.
  - OOS preregistration exists before every OOS run.
  - Portfolio outputs include measurement-frame labels.

- [ ] P7. Plan D survivor seed research program

  Purpose: build seed pool from Plan C survivors, Plan B survivors, and verified
  rr8 seed; run serial seed research until top 3 seeds are frozen.

  Acceptance:
  - `seed_pool.jsonl` is append-only and sha-checked.
  - Only one active seed runs at a time.
  - R-a/R-b/R-c/R-d outputs exist per round.
  - Program stops when top 3 priority seeds are frozen, seed pool is exhausted,
    positive control fails, or 3 seeds show all-round no-improve.

## Final Verification Wave

- [ ] F1. Evidence and scope audit
- [ ] F2. Code quality and test audit
- [ ] F3. Research lineage and protected-path audit
