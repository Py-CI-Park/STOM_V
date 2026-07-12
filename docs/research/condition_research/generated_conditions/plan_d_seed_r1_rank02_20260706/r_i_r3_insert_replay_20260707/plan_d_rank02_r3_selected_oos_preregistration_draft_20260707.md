# Plan D rank02 R3 selected OOS preregistration draft

status: draft_pending_next_scope_confirmation
source_run_id: `lat_plan_d_rank02_r3_8_min_warm64_20260707`
selected_count: 1
selected_pairs: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_i_r3_insert_replay_20260707/pairs_plan_d_rank02_r3_selected_oos_draft_20260707.json`

## Selected candidates

- `plan_d_r1_rank02_r3_01_amt8000_default_tp3_sl3_hold90`: profit=2297191, mdd=16.31, trades=209, daily=1.00

## OOS decision rule

- survivor: status ok AND gate_passed true AND profit > 0 AND mdd <= 35 AND daily_avg_trades >= 0.5
- hold: status ok AND profit > 0 but one non-critical gate fails
- no_go: error/no_trades OR profit <= 0 OR mdd > 35

## Caveat

Selected from full-period min replay that includes 2026-01-01~2026-02-27, so the next OOS is fixed OOS-style robustness replay, not fully blind discovery OOS.

## Forbidden until next explicit scope

- OOS execution
- portfolio
- export/live/final promotion
- DB UPDATE/DELETE
- non-selected OOS
