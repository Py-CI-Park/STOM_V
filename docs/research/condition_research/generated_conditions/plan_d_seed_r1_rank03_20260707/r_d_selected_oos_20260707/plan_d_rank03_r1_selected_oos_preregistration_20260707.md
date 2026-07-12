# Plan D rank03 R1 selected OOS preregistration

- created_at: 2026-07-07T18:01:57+09:00
- scope: `plan-d-rank03-r1-selected-oos-prereg-no-portfolio-export`
- source_selection_run_id: `lat_plan_d_rank03_r1_8_min_warm64_20260707`
- candidate_count: 1
- lane: min
- OOS-style window: 2026-01-01 to 2026-02-27
- warm engines: 64

## Selected Candidate

| label | profit | MDD | trades | daily | reason |
|---|---:|---:|---:|---:|---|
| `plan_d_r1_rank03_r1_08_parent_buy_default_tp3_sl3_hold90` | 1652322 | 15.79 | 181 | 0.80 | best_profit_and_lower_mdd_vs_rank03_parent_preflight |

## Execution Boundary

Run only the selected 1 pair in `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_d_selected_oos_20260707/pairs_plan_d_rank03_r1_selected1_oos_20260707.json` with config `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_d_selected_oos_20260707/oos_config_min_plan_d_rank03_r1_selected1_20260707.json`. Do not run any non-selected OOS, portfolio, export/live/final promotion, full tick/min 288, or DB UPDATE/DELETE.

## Caveat

The selected candidate was chosen from full-period min replay that includes the fixed OOS-style window, so this is a robustness/OOS-style replay, not a fully blind discovery OOS.
