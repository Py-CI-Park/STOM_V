# Plan D rank03 R1 Context Pack

- scope: `plan-d-seed-r1-rank03-readiness-dryrun-no-oos-portfolio-export`
- active_seed_id: `plan_d_rcs_oos_20260706_rank03`
- active_condition_id: `repair_v3_20260706_26_daily_boost_core_l1430_sell_loose_tp4_sl3_hold90`
- buy_sha256: `8bc41fe1cead5449625dc6daf7b675fdc23009237d382a32028b6c10c413feb4`
- sell_sha256: `0b38c51567b12e8c1df6b18b2491ab71845394ac452787470d24dd11c1bb79b6`
- selected_oos_profit_krw: 865831.0
- selected_oos_mdd_pct: 6.28
- selected_oos_trade_count: 19
- selected_oos_daily_avg_trades: 0.5
- readiness_status: `ready_for_rank03_r1_generate8_dryrun_next_scope`

## Design Intent

Rank03 has a daily-boost core with an L1430 late-day component and sparse selected-OOS daily coverage. R1 candidates therefore probe bounded L1430 coverage, adjacent L14/L13 bridge coverage, and small sell/momentum/strength changes before any INSERT/replay decision.

## Hard Bounds

- DB registration dry-run only in this scope.
- No DB INSERT apply, official replay, OOS, portfolio, or export/live/final promotion.
- Candidate names are sanitized and research-lane hypothesis_seed only.
