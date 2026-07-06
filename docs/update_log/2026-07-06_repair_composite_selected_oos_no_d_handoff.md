# Repair Composite Selected OOS No-D Handoff

????: 2026-07-06T10:51:50+09:00
??: `repair-composite-selected-oos-no-D`
???: `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`

## 1. ??? ?? ??

?? ????? selected freeze 16?? OOS-style ?? ??? ????. Plan D/P7, portfolio, full tick/min, export/live/final ??? ???? ???.

- Plan D/P7 ?? ??
- portfolio ?? ??
- full tick 288 / full min 288 ?? ??
- selected 16? ? OOS ?? ??
- DB UPDATE/DELETE ??
- A3/promotion/export/live/final ?? ??

## 2. ???

| ?? | ?? |
| --- | --- |
| source read receipt | `.omo/evidence/repair-composite-selected-oos-no-d-20260706/source_read_receipt.md` |
| freeze recheck | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_freeze_recheck_20260706.json` |
| OOS preregistration | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_preregistration_20260706.md` |
| pairs selected 16 | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/pairs_repair_composite_selected_16_oos_20260706.json` |
| OOS config | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/oos_config_min_selected16_20260706.json` |
| OOS result | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_result_20260706.json` |
| OOS summary | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_summary_20260706.md` |
| OOS survivors | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_survivors_20260706.jsonl` |
| OOS no_go | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_no_go_20260706.jsonl` |

## 3. ?? OOS-style ?? ??

| ?? | ? |
| --- | ---: |
| run_id | `lat_repair_composite_selected16_oos_min_warm64_20260706` |
| lane | min |
| DB | `_database/stock_min_back.db` |
| ?? | `2026-01-01~2026-02-27` |
| ?? | `09:00~15:19` |
| warm engines | 64 |
| warm back_count | 480 |
| rows | 16 |
| ok | 16 |
| gate_passed | 15 |
| survivor | 15 |
| hold | 0 |
| no_go | 1 |

sell profile? ??:

| sell_profile | survivor | hold | no_go |
| --- | ---: | ---: | ---: |
| `sell_default_tp3_sl3_hold60` | 9 | 0 | 0 |
| `sell_loose_tp4_sl3_hold90` | 4 | 0 | 1 |
| `sell_tight_tp3_sl2p5_hold60` | 2 | 0 | 0 |

?? survivor:

| rank | condition_id | profit | MDD | daily | trades |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `repair_v3_20260706_13_top_four_plus_l14_sell_loose_tp4_sl3_hold90` | 1124220 | 4.12 | 0.50 | 18 |
| 2 | `repair_v3_20260706_13_top_four_plus_l14_sell_default_tp3_sl3_hold60` | 1079768 | 4.06 | 0.50 | 19 |
| 3 | `repair_v3_20260706_20_all_positive_plus_l14_l1430_sell_loose_tp4_sl3_hold90` | 985556 | 6.64 | 0.80 | 31 |
| 4 | `repair_v3_20260706_20_all_positive_plus_l14_l1430_sell_default_tp3_sl3_hold60` | 981721 | 6.04 | 0.90 | 32 |
| 5 | `repair_v3_20260706_17_balanced_plus_l14_sell_default_tp3_sl3_hold60` | 909297 | 4.06 | 0.50 | 18 |

## 4. ??

- selected 16 ? 15?? OOS-style ?? ??? survivor ??? ????.
- no_go 1?? `repair_v3_20260706_25_daily_boost_core_l13_sell_loose_tp4_sl3_hold90`?? profit ??? ????.
- Plan D seed-pool intake? ????. ?? ?? selected ?? ??? ???? preflight ????, ?? ??? ?? ???? ?? OOS? ??? ?? ? robustness replay?? caveat? ??? ??? ??.
- portfolio? ?? ???? ???. Plan D?? seed pool intake? ?? readiness audit? ?? ???? ??.

## 5. ?? ?? ???

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

??? repair-composite-plan-d-seed-pool-intake??? ????.
??? selected OOS survivor 15?? Plan D seed-pool ?? ??? append-only ????,
Plan D 1? ?? ? positive control/lineage/readiness audit? ???? ???.

??? ?? ?? ??:
- docs/update_log/2026-07-06_repair_composite_selected_oos_no_d_handoff.md
- docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_result_20260706.json
- docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_survivors_20260706.jsonl
- docs/research/condition_research/plans/2026-07-02_plan_D_seed_research_program.md

??:
1. survivor 15?? buy/sell sha, OOS metrics, caveat? ?????.
2. Plan D seed_pool intake ??? append-only? ????.
3. positive control? lineage/readiness audit? ????.
4. Plan D seed research round? ??? ? ??? ????.
5. ?? ????? portfolio/export/live/final promotion? ???? ???.

??:
- portfolio ?? ??
- export/live/final promotion ??
- DB UPDATE/DELETE ??
- git add -A ??
- dashboard 7??, .gjc, unrelated .omo ?? ???? ??
```
