# Selected Freeze / Preregistration Draft - Composite Expanded Repair

created_at: 2026-07-06T09:31:27+09:00
status: draft_only_no_oos_executed
source_run_id: `lat_repair_composite_expanded_48_official_full_warm64_20260706`
selected_count: 16

Selection rule: gate_passed and mdd <= 25 and daily_avg_trades >= 0.8; top16 by profit then lower mdd.

| rank | condition_id | profit | mdd | daily | trades | sell_profile | group |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | `repair_v3_20260706_13_top_four_plus_l14_sell_default_tp3_sl3_hold60` | 1887171.0 | 19.25 | 1.0 | 206 | `sell_default_tp3_sl3_hold60` | `cov04_plus_l14_daily_lift` |
| 2 | `repair_v3_20260706_14_top_four_plus_l13_sell_default_tp3_sl3_hold60` | 1393641.0 | 13.34 | 1.8 | 375 | `sell_default_tp3_sl3_hold60` | `cov04_plus_l13_trade_lift` |
| 3 | `repair_v3_20260706_13_top_four_plus_l14_sell_loose_tp4_sl3_hold90` | 1340830.0 | 18.56 | 0.9 | 201 | `sell_loose_tp4_sl3_hold90` | `cov04_plus_l14_daily_lift` |
| 4 | `repair_v3_20260706_25_daily_boost_core_l13_sell_default_tp3_sl3_hold60` | 1285028.0 | 14.11 | 1.8 | 380 | `sell_default_tp3_sl3_hold60` | `cov03_plus_l13` |
| 5 | `repair_v3_20260706_13_top_four_plus_l14_sell_tight_tp3_sl2p5_hold60` | 1203245.0 | 17.0 | 1.0 | 207 | `sell_tight_tp3_sl2p5_hold60` | `cov04_plus_l14_daily_lift` |
| 6 | `repair_v3_20260706_17_balanced_plus_l14_sell_default_tp3_sl3_hold60` | 1140636.0 | 19.84 | 0.9 | 197 | `sell_default_tp3_sl3_hold60` | `cov02_plus_l14` |
| 7 | `repair_v3_20260706_20_all_positive_plus_l14_l1430_sell_default_tp3_sl3_hold60` | 1123124.0 | 22.58 | 1.2 | 262 | `sell_default_tp3_sl3_hold60` | `cov12_plus_l1430` |
| 8 | `repair_v3_20260706_15_top_four_plus_l13_l14_sell_default_tp3_sl3_hold60` | 1059257.0 | 18.49 | 2.1 | 448 | `sell_default_tp3_sl3_hold60` | `cov04_plus_l13_l14_coverage` |
| 9 | `repair_v3_20260706_16_sparse_four_plus_l13_l14_sell_default_tp3_sl3_hold60` | 950644.0 | 19.21 | 2.1 | 453 | `sell_default_tp3_sl3_hold60` | `cov03_plus_l13_l14_coverage` |
| 10 | `repair_v3_20260706_26_daily_boost_core_l1430_sell_loose_tp4_sl3_hold90` | 874241.0 | 17.04 | 0.8 | 179 | `sell_loose_tp4_sl3_hold90` | `cov03_plus_l1430` |
| 11 | `repair_v3_20260706_19_profitmax_plus_l1430_sell_loose_tp4_sl3_hold90` | 852468.0 | 17.77 | 0.8 | 174 | `sell_loose_tp4_sl3_hold90` | `cov04_plus_l1430` |
| 12 | `repair_v3_20260706_27_l14_focus_sparse_strength_sell_default_tp3_sl3_hold60` | 797362.0 | 20.92 | 0.8 | 179 | `sell_default_tp3_sl3_hold60` | `l14_focus_strength` |
| 13 | `repair_v3_20260706_17_balanced_plus_l14_sell_tight_tp3_sl2p5_hold60` | 751652.0 | 18.99 | 0.9 | 198 | `sell_tight_tp3_sl2p5_hold60` | `cov02_plus_l14` |
| 14 | `repair_v3_20260706_20_all_positive_plus_l14_l1430_sell_loose_tp4_sl3_hold90` | 726216.0 | 20.5 | 1.2 | 257 | `sell_loose_tp4_sl3_hold90` | `cov12_plus_l1430` |
| 15 | `repair_v3_20260706_25_daily_boost_core_l13_sell_loose_tp4_sl3_hold90` | 718567.0 | 13.19 | 1.7 | 372 | `sell_loose_tp4_sl3_hold90` | `cov03_plus_l13` |
| 16 | `repair_v3_20260706_24_strength_profitmax_l13_l14_sell_default_tp3_sl3_hold60` | 715983.0 | 21.06 | 2.0 | 430 | `sell_default_tp3_sl3_hold60` | `strength_profitmax_l13_l14` |

## Required Before OOS

- User scope must explicitly permit OOS.
- Use these selected frozen candidates only; do not promote all go candidates automatically.
- Keep DB operations append-only.
- Plan D/P7 remains blocked until OOS survivors exist.
