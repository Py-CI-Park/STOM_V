# Repair Composite Expanded Preflight Summary

created_at: 2026-07-06T09:30:29+09:00
run_id: `lat_repair_composite_expanded_48_official_full_warm64_20260706`

## Summary

| metric | value |
| --- | ---: |
| rows | 48 |
| status ok | 48 |
| gate_passed | 32 |
| go | 32 |
| hold | 0 |
| no_go | 16 |

## Sell Profile Decision Counts

| sell_profile | go | hold | no_go |
| --- | ---: | ---: | ---: |
| `sell_default_tp3_sl3_hold60` | 14 | 0 | 2 |
| `sell_tight_tp3_sl2p5_hold60` | 6 | 0 | 10 |
| `sell_loose_tp4_sl3_hold90` | 12 | 0 | 4 |

## Top Go Candidates

| rank | condition_id | profit | mdd | daily | trades | sell_profile | group |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | `repair_v3_20260706_13_top_four_plus_l14_sell_default_tp3_sl3_hold60` | 1887171.0 | 19.25 | 1.0 | 206 | `sell_default_tp3_sl3_hold60` | `cov04_plus_l14_daily_lift` |
| 2 | `repair_v3_20260706_19_profitmax_plus_l1430_sell_default_tp3_sl3_hold60` | 1426967.0 | 31.04 | 0.8 | 179 | `sell_default_tp3_sl3_hold60` | `cov04_plus_l1430` |
| 3 | `repair_v3_20260706_14_top_four_plus_l13_sell_default_tp3_sl3_hold60` | 1393641.0 | 13.34 | 1.8 | 375 | `sell_default_tp3_sl3_hold60` | `cov04_plus_l13_trade_lift` |
| 4 | `repair_v3_20260706_13_top_four_plus_l14_sell_loose_tp4_sl3_hold90` | 1340830.0 | 18.56 | 0.9 | 201 | `sell_loose_tp4_sl3_hold90` | `cov04_plus_l14_daily_lift` |
| 5 | `repair_v3_20260706_26_daily_boost_core_l1430_sell_default_tp3_sl3_hold60` | 1318354.0 | 33.04 | 0.9 | 184 | `sell_default_tp3_sl3_hold60` | `cov03_plus_l1430` |
| 6 | `repair_v3_20260706_25_daily_boost_core_l13_sell_default_tp3_sl3_hold60` | 1285028.0 | 14.11 | 1.8 | 380 | `sell_default_tp3_sl3_hold60` | `cov03_plus_l13` |
| 7 | `repair_v3_20260706_13_top_four_plus_l14_sell_tight_tp3_sl2p5_hold60` | 1203245.0 | 17.0 | 1.0 | 207 | `sell_tight_tp3_sl2p5_hold60` | `cov04_plus_l14_daily_lift` |
| 8 | `repair_v3_20260706_17_balanced_plus_l14_sell_default_tp3_sl3_hold60` | 1140636.0 | 19.84 | 0.9 | 197 | `sell_default_tp3_sl3_hold60` | `cov02_plus_l14` |
| 9 | `repair_v3_20260706_20_all_positive_plus_l14_l1430_sell_default_tp3_sl3_hold60` | 1123124.0 | 22.58 | 1.2 | 262 | `sell_default_tp3_sl3_hold60` | `cov12_plus_l1430` |
| 10 | `repair_v3_20260706_15_top_four_plus_l13_l14_sell_default_tp3_sl3_hold60` | 1059257.0 | 18.49 | 2.1 | 448 | `sell_default_tp3_sl3_hold60` | `cov04_plus_l13_l14_coverage` |
| 11 | `repair_v3_20260706_19_profitmax_plus_l1430_sell_tight_tp3_sl2p5_hold60` | 966665.0 | 25.91 | 0.8 | 180 | `sell_tight_tp3_sl2p5_hold60` | `cov04_plus_l1430` |
| 12 | `repair_v3_20260706_16_sparse_four_plus_l13_l14_sell_default_tp3_sl3_hold60` | 950644.0 | 19.21 | 2.1 | 453 | `sell_default_tp3_sl3_hold60` | `cov03_plus_l13_l14_coverage` |
| 13 | `repair_v3_20260706_26_daily_boost_core_l1430_sell_tight_tp3_sl2p5_hold60` | 876295.0 | 27.31 | 0.9 | 185 | `sell_tight_tp3_sl2p5_hold60` | `cov03_plus_l1430` |
| 14 | `repair_v3_20260706_26_daily_boost_core_l1430_sell_loose_tp4_sl3_hold90` | 874241.0 | 17.04 | 0.8 | 179 | `sell_loose_tp4_sl3_hold90` | `cov03_plus_l1430` |
| 15 | `repair_v3_20260706_19_profitmax_plus_l1430_sell_loose_tp4_sl3_hold90` | 852468.0 | 17.77 | 0.8 | 174 | `sell_loose_tp4_sl3_hold90` | `cov04_plus_l1430` |
| 16 | `repair_v3_20260706_27_l14_focus_sparse_strength_sell_default_tp3_sl3_hold60` | 797362.0 | 20.92 | 0.8 | 179 | `sell_default_tp3_sl3_hold60` | `l14_focus_strength` |

## Decisions

- Full chunk open: allowed_for_narrowed_composite_repair_only; avoid pure late-ladder and broad tight-sell expansion
- OOS readiness: ready_after_selected_go_freeze_and_user_scope_that_explicitly_permits_oos; no OOS executed in this range
- Plan D: blocked_until_oos_survivors_and_seed_pool_exist; no Plan D/P7 in current range
