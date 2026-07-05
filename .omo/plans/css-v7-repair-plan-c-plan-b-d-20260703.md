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

- [x] P5. Plan B B1.3 overnight smoke batch

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
  Chunk04 blocker 2026-07-04: the first chunk04 attempt is partial/stale, not
  complete. Evidence:
  `docs/update_log/2026-07-04_p5_tick_chunk04_blocker_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk04_blocker_official_full_warm64_20260704_receipt.json`.
  Current state: run `lat_tick_official_full_warm64_chunk04_20260704` has
  13/24 rows (`ok=11`, `error=2`), DB status `running`, and no live batch
  process. Do not start chunk05/min/P6/P7; resolve with a new chunk04
  retry/supplement run id without DB `UPDATE`/`DELETE`.
  Chunk04 supplement 2026-07-04: resolved the partial/stale run with new run id
  `lat_tick_official_full_warm64_chunk04_supplement11_23_20260704`. Evidence:
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk04_supplement11_23_official_full_warm64_20260704_receipt.json`
  and combined official receipt
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk04_official_full_warm64_20260704_receipt.json`.
  Combined chunk04 state is 24/24 honest `ok` rows, `gate_passed=0`,
  MDD `295.04~990.41`, profit `-539,464,054~-30,170,099`. The stale first
  attempt remains preserved as blocker evidence; do not mutate it.
  Next allowed action is chunk05 only.
  Chunk05 2026-07-05: executed cleanly with 24/24 honest `ok` rows,
  `gate_passed=0`, MDD `181.44~1307.53`. Evidence:
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk05_official_full_warm64_20260704_receipt.json`.
  Chunk05 is coverage-map evidence only; next allowed action is chunk06 only.
  Chunk06 blocker 2026-07-05: the first chunk06 attempt is partial/stale, not
  complete. Evidence:
  `docs/update_log/2026-07-04_p5_tick_chunk06_blocker_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk06_blocker_official_full_warm64_20260704_receipt.json`.
  Current state: run `lat_tick_official_full_warm64_chunk06_20260704` has
  10/24 rows (`ok=10`, `error=0`), DB status `running`, and no live batch
  process. Do not start chunk07/min/P6/P7; resolve with new chunk06 supplement
  run id `lat_tick_official_full_warm64_chunk06_supplement10_23_20260704`
  without DB `UPDATE`/`DELETE`.
  Chunk06 supplement 2026-07-05: resolved the partial/stale run with new run id
  `lat_tick_official_full_warm64_chunk06_supplement10_23_20260704`. Evidence:
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk06_supplement10_23_official_full_warm64_20260704_receipt.json`
  and combined official receipt
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk06_official_full_warm64_20260704_receipt.json`.
  Combined chunk06 state is 24/24 honest `ok` rows, `gate_passed=0`,
  MDD `236.83~805.16`, profit `-506,115,259~-22,864,504`. The stale first
  attempt remains preserved as blocker evidence; do not mutate it.
  Next allowed action is chunk07 only.
  Chunk07 2026-07-05: executed cleanly with 24/24 honest `ok` rows,
  `gate_passed=0`, MDD `116.59~1034.91`. Evidence:
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk07_official_full_warm64_20260704_receipt.json`.
  Chunk07 is coverage-map evidence only; next allowed action is chunk08 only.
  Chunk08 blocker 2026-07-05: the first chunk08 attempt is partial/stale, not
  complete. Evidence:
  `docs/update_log/2026-07-04_p5_tick_chunk08_blocker_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk08_blocker_official_full_warm64_20260704_receipt.json`.
  Current state: run `lat_tick_official_full_warm64_chunk08_20260704` has
  13/24 rows (`ok=13`, `error=0`), DB status `running`, and no live batch
  process. Do not start chunk09/min/P6/P7; resolve with new chunk08 supplement
  run id `lat_tick_official_full_warm64_chunk08_supplement13_23_20260704`
  without DB `UPDATE`/`DELETE`.
  Chunk08 supplement 2026-07-05: supplement rows were recorded with new run id
  `lat_tick_official_full_warm64_chunk08_supplement13_23_20260704`, but the
  supplement run also remained DB-status `running` after all 11 rows were
  written. Evidence:
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk08_supplement13_23_official_full_warm64_20260704_receipt.json`
  and combined official row-level receipt
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk08_official_full_warm64_20260704_receipt.json`.
  Combined chunk08 row coverage is 24/24 honest `ok` rows, `gate_passed=0`,
  MDD `208.90~653.93`, profit `-442,696,240~-25,456,677`. Both stale source
  runs remain preserved as evidence; do not mutate them.
  Next allowed action is chunk09 only.
  Chunk09 stale-start 2026-07-05: original run id
  `lat_tick_official_full_warm64_chunk09_20260704` stopped before warm prepare
  and before any generation row was recorded. Evidence:
  `docs/update_log/2026-07-05_p5_tick_chunk09_stale_start_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk09_stale_start_official_full_warm64_20260705_receipt.json`.
  The stale run has DB status `running`, 0/24 rows, and no live batch process;
  preserve it without DB `UPDATE`/`DELETE`.
  Chunk09 retry 2026-07-05: completed with new run id
  `lat_tick_official_full_warm64_chunk09_retry01_20260705`. Evidence:
  `docs/update_log/2026-07-05_p5_tick_chunk09_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk09_official_full_warm64_20260705_receipt.json`.
  Result: 24/24 honest `ok` rows, `gate_passed=0`, warm prepare
  `back_count=2424 elapsed=262s`, MDD `53.41~1061.11`, profit
  `-372,950,355~-2,497,875`. Chunk09 is coverage-map evidence only; next
  allowed action is chunk10 only.
  Chunk10 2026-07-05: executed cleanly with official DB-full-period + warm64.
  Evidence:
  `docs/update_log/2026-07-05_p5_tick_chunk10_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk10_official_full_warm64_20260705_receipt.json`.
  Result: 24/24 honest `ok` rows, `gate_passed=0`, warm prepare
  `back_count=2424 elapsed=312s`, MDD `211.98~586.81`, profit
  `-425,621,498~-21,242,273`. Chunk10 is coverage-map evidence only; next
  allowed action is chunk11 only.
  Chunk11 2026-07-05: executed cleanly with official DB-full-period + warm64.
  Evidence:
  `docs/update_log/2026-07-05_p5_tick_chunk11_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk11_official_full_warm64_20260705_receipt.json`.
  Result: 24/24 honest `ok` rows, `gate_passed=0`, warm prepare
  `back_count=2424 elapsed=274s`, MDD `16.88~621.39`, profit
  `-198,665,247~-899,093`. Chunk11 is coverage-map evidence only; next
  allowed action is chunk12 only.
  Chunk12 2026-07-05: executed cleanly with official DB-full-period + warm64.
  Evidence:
  `docs/update_log/2026-07-05_p5_tick_chunk12_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk12_official_full_warm64_20260705_receipt.json`.
  Result: 24/24 honest `ok` rows, `gate_passed=0`, warm prepare
  `back_count=2424 elapsed=282s`, MDD `149.78~387.60`, profit
  `-219,558,866~-11,642,820`. Chunk12 is coverage-map evidence only.
  Official tick 288/288 coverage judgment 2026-07-05: complete. Evidence:
  `docs/update_log/2026-07-05_p5_tick_288_coverage_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_full_warm64_288_coverage_20260705_receipt.json`.
  Result: `12/12` chunks, `288/288` unique pairs, `ok=288`,
  `gate_passed=0`. Tick export, min, P6, P7, and Plan D were not run in this
  selected range. Next allowed action is tick export/summary only.
  Tick export/summary and min readiness 2026-07-05: completed without running
  min. Evidence:
  `docs/update_log/2026-07-05_p5_tick_export_summary_min_readiness_handoff.md`
  plus JSONL export
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_full_warm64_288_export_summary_20260705.jsonl`
  and summary JSON
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_full_warm64_288_export_summary_20260705.json`.
  Result: `ok=288`, `gate_passed=0`, `negative_profit_count=288`,
  `mdd_excess_count=287`, `low_daily_trades_count=9`. Root-cause judgment:
  condition structure is primary; strict gate and tick lane are secondary
  filters. Official min config and `pairs_min.json` are ready, but full min 288
  should not start directly. Next allowed action is min official warm64
  preflight4 only.
  Min preflight4 2026-07-05: executed with official DB-full-period + warm64.
  Evidence:
  `docs/update_log/2026-07-05_p5_min_preflight4_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_preflight4_official_full_warm64_20260705_receipt.json`.
  Result: warm prepare `status=ok`, `back_count=1379`, elapsed `129s`;
  recorded `4/4` honest rows with `status_counts={'ok': 3, 'error': 1}`,
  `gate_passed=0`, total runtime `4.8m`. Full min 288 is possible only as a
  chunked coverage run with per-chunk error monitoring; do not run monolithic
  288. Next allowed action is min chunk manifest plus chunk01 only.
  Min chunk01 2026-07-05: generated the official 12-chunk min manifest and ran
  chunk01 only. Evidence:
  `docs/update_log/2026-07-05_p5_min_chunk01_handoff.md`,
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_full_run_protocol_after_preflight_20260705.json`,
  and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_chunk01_official_full_warm64_20260705_receipt.json`.
  Result: warm prepare `status=ok`, `back_count=1379`, elapsed `121s`;
  recorded `24/24` honest `ok` rows, `gate_passed=0`, total runtime `11.4m`.
  Chunk01 is clean coverage evidence but has no survivor. Next allowed action
  is min chunk02 only; P6/P7/Plan D remain blocked until official min 288
  coverage and export exist.
  Min chunk02 2026-07-05: executed with official DB-full-period + warm64.
  Evidence:
  `docs/update_log/2026-07-05_p5_min_chunk02_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_chunk02_official_full_warm64_20260705_receipt.json`.
  Result: warm prepare `status=ok`, `back_count=1379`, elapsed `124s`;
  recorded `24/24` honest `ok` rows, `gate_passed=0`, total runtime `13.3m`.
  Official min coverage is now `48/288`. Chunk02 is clean coverage evidence
  but has no survivor. Next allowed action is min chunk03 only; P6/P7/Plan D
  remain blocked until official min 288 coverage and export exist.
  Min chunk03 2026-07-05: executed with official DB-full-period + warm64.
  Evidence:
  `docs/update_log/2026-07-05_p5_min_chunk03_handoff.md` and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_chunk03_official_full_warm64_20260705_receipt.json`.
  Result: warm prepare `status=ok`, `back_count=1379`, elapsed `110s`;
  recorded `24/24` honest `ok` rows, `gate_passed=0`, total runtime `10.9m`.
  Official min coverage is now `72/288`. Chunk03 is clean coverage evidence
  but has no survivor. Next allowed action is min chunk04 only; P6/P7/Plan D
  remain blocked until official min 288 coverage and export exist.
  Min chunk04~12/export 2026-07-05: completed official DB-full-period + warm64
  min coverage and export. Evidence:
  `docs/update_log/2026-07-05_p5_min_288_export_p6_no_d_handoff.md`,
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_chunks04_12_official_full_warm64_20260705_receipt.json`,
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_official_full_warm64_288_coverage_20260705_receipt.json`,
  and
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_official_full_warm64_288_export_summary_20260705.json`.
  Result: min `288/288` rows, `status_counts={'ok': 281, 'error': 7}`,
  `gate_passed=0`. Chunk08 was resolved append-only with supplement01;
  the original stale partial run remains preserved without DB UPDATE/DELETE.

  Acceptance:
  - Resume manifest and first-10-pair timing estimate are written.
  - Tick smoke result export exists before min starts.
  - Any cleanup uses dry-run inventory and explicit PID exclusion.

- [x] P6. Plan B B2-B5 coverage, refinement, OOS, portfolio

  Purpose: convert smoke results into go/no_go, refine go cells, freeze before OOS,
  then assemble a portfolio only with 2+ OOS survivors.

  Status 2026-07-05: completed P6 no-D classification from official tick 288
  and min 288 exports. Evidence:
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p6_lattice_coverage_gaps_batch_plan_no_d_20260705.json`,
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p6_lattice_go_no_go_hold_20260705.json`,
  and append-only registry
  `docs/research/condition_research/research_runs/seed_lattice_20260702/p6_lattice_revival_registry_20260705.jsonl`.
  Result: coverage `576/576`, `go=0`, `hold=0`, `no_go=576`.
  Refinement/OOS/portfolio were not opened because no go candidate or
  preregistered survivor exists.

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
