# Repair Composite Selected OOS Summary

created_at: 2026-07-06T10:51:50+09:00
run_id: `lat_repair_composite_selected16_oos_min_warm64_20260706`
scope: `repair-composite-selected-oos-no-D`

## Profile

| item | value |
| --- | --- |
| lane | min |
| DB | `_database/stock_min_back.db` |
| OOS window | `2026-01-01~2026-02-27` |
| time window | `09:00~15:19` |
| warm engines | 64 |
| warm back_count | 480 |
| duration | 6.2m |

## Result

| metric | value |
| --- | ---: |
| rows | 16 |
| ok | 16 |
| gate_passed | 15 |
| survivor | 15 |
| hold | 0 |
| no_go | 1 |

## Sell Profile Counts

| sell_profile | survivor | hold | no_go |
| --- | ---: | ---: | ---: |
| `sell_default_tp3_sl3_hold60` | 9 | 0 | 0 |
| `sell_loose_tp4_sl3_hold90` | 4 | 0 | 1 |
| `sell_tight_tp3_sl2p5_hold60` | 2 | 0 | 0 |

## Top Survivors

| rank | condition_id | profit | MDD | daily | trades | sell_profile |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `repair_v3_20260706_13_top_four_plus_l14_sell_loose_tp4_sl3_hold90` | 1124220 | 4.12 | 0.50 | 18 | `sell_loose_tp4_sl3_hold90` |
| 2 | `repair_v3_20260706_13_top_four_plus_l14_sell_default_tp3_sl3_hold60` | 1079768 | 4.06 | 0.50 | 19 | `sell_default_tp3_sl3_hold60` |
| 3 | `repair_v3_20260706_20_all_positive_plus_l14_l1430_sell_loose_tp4_sl3_hold90` | 985556 | 6.64 | 0.80 | 31 | `sell_loose_tp4_sl3_hold90` |
| 4 | `repair_v3_20260706_20_all_positive_plus_l14_l1430_sell_default_tp3_sl3_hold60` | 981721 | 6.04 | 0.90 | 32 | `sell_default_tp3_sl3_hold60` |
| 5 | `repair_v3_20260706_17_balanced_plus_l14_sell_default_tp3_sl3_hold60` | 909297 | 4.06 | 0.50 | 18 | `sell_default_tp3_sl3_hold60` |
| 6 | `repair_v3_20260706_27_l14_focus_sparse_strength_sell_default_tp3_sl3_hold60` | 909297 | 4.06 | 0.50 | 18 | `sell_default_tp3_sl3_hold60` |
| 7 | `repair_v3_20260706_26_daily_boost_core_l1430_sell_loose_tp4_sl3_hold90` | 865831 | 6.28 | 0.50 | 19 | `sell_loose_tp4_sl3_hold90` |
| 8 | `repair_v3_20260706_19_profitmax_plus_l1430_sell_loose_tp4_sl3_hold90` | 865831 | 6.28 | 0.50 | 19 | `sell_loose_tp4_sl3_hold90` |
| 9 | `repair_v3_20260706_14_top_four_plus_l13_sell_default_tp3_sl3_hold60` | 826691 | 4.29 | 1.80 | 67 | `sell_default_tp3_sl3_hold60` |
| 10 | `repair_v3_20260706_25_daily_boost_core_l13_sell_default_tp3_sl3_hold60` | 826691 | 4.29 | 1.80 | 67 | `sell_default_tp3_sl3_hold60` |

## Caveat

The selected 16 were chosen from a full-period min preflight that included 2026-01-01~2026-02-27, so this is a fixed OOS-style robustness replay, not a fully blind discovery OOS.
