# Plan D rank02 R3 selected OOS preregistration

status: confirmed
scope: `plan-d-rank02-r3-selected-oos-prereg-no-portfolio-export`
source_run_id: `lat_plan_d_rank02_r3_8_min_warm64_20260707`
selected_count: 1
selected_pairs: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_j_r3_selected_oos_20260707/pairs_plan_d_rank02_r3_selected1_oos_20260707.json`
freeze_ledger: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_j_r3_selected_oos_20260707/plan_d_rank02_r3_selected_freeze_ledger_20260707.jsonl`

## Selected Candidate

- `plan_d_r1_rank02_r3_01_amt8000_default_tp3_sl3_hold90`: source profit=2297191, mdd=16.31, trades=209, daily=1.00

## OOS-Style Replay Profile

- lane: min
- DB: `_database/stock_min_back.db`
- window: 2026-01-01 to 2026-02-27
- time window: 09:00 to 15:19
- engine mode: warm
- warm engines: 64
- max selected pairs: 1

## Decision Rule

- survivor: status ok AND gate_passed true AND profit > 0 AND mdd <= 35 AND daily_avg_trades >= 0.5
- hold: status ok AND profit > 0 but one non-critical gate fails
- no_go: error/no_trades OR profit <= 0 OR mdd > 35

## Caveat

Selected candidate came from full-period min replay that included 2026-01-01 to 2026-02-27, so this is fixed OOS-style robustness replay, not fully blind discovery OOS.

## Forbidden

- non-selected OOS
- portfolio
- export/live/final promotion
- DB UPDATE/DELETE
- preregistration-free OOS
