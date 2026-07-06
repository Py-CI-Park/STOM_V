# Plan D rank02 R1 Context Pack

- scope: `plan-d-rank02-r1-generate8-dryrun-no-portfolio-export`
- active_seed_id: `plan_d_rcs_oos_20260706_rank02`
- active_condition_id: `repair_v3_20260706_13_top_four_plus_l14_sell_loose_tp4_sl3_hold90`
- buy_sha256: `3158a4cfd78c4cc0edee798ba2b1bb58190e676ffa2774fa52cb06059a4b032e`
- sell_sha256: `0b38c51567b12e8c1df6b18b2491ab71845394ac452787470d24dd11c1bb79b6`
- selected_oos_profit_krw: 1124220.0
- selected_oos_mdd_pct: 4.12
- selected_oos_trade_count: 18
- selected_oos_daily_avg_trades: 0.5
- readiness_status: `ready_for_rank02_r1_readiness_or_generate_dryrun_next_scope`

## Design Intent

Rank02 has strong selected OOS score and profit, but sparse daily coverage. R1 candidates therefore avoid changing the research lane boundary and probe only limited coverage or sell-profile mutations before any INSERT/replay decision.

## Hard Bounds

- DB registration dry-run only in this scope.
- No official replay, OOS, portfolio, or export/live/final promotion.
- Candidate names are sanitized and research-lane hypothesis_seed only.
