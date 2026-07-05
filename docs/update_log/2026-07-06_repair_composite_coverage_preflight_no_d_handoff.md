# Repair Composite Coverage Preflight No-D Handoff

????: 2026-07-06T08:13:32+09:00
?? ??: `repair-composite-coverage-preflight-no-D`
??: `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`

## 1. ??

?? ??? ????. Plan D/P7, OOS, portfolio, full tick/min 288? ???? ???.

?? ??:

- phase1~phase3 hold ?? 37?? ?/???/family ?? 7? ???? ?? ????.
- daily ??? ??? ???? ?? composite OR ?? 24?? ????.
- ?? composite buy/sell ??? compile ? token_check? ????.
- DB ??? INSERT-only? ????.
- ?? min ???? warm64 ?? preflight ?? `24/24 ok`, `gate_passed=16`??.
- full chunk ?? ???? `YES`? ????. ?, ?? ??? no-D/no-OOS ???? freeze? ?? ??? ??? ???.
- Plan D? ??? ????. OOS survivor? portfolio seed pool? ?? ??.

## 2. ???

| ?? | ?? |
| --- | --- |
| Read receipt | `.omo/evidence/repair-composite-coverage-preflight-no-d-20260706/source_read_receipt.md` |
| hold dedup | `docs\research\condition_research\research_runs\seed_lattice_20260702\repair_composite_coverage_20260706\repair_composite_hold_dedup_20260706.json` |
| composite ?? | `docs\research\condition_research\research_runs\seed_lattice_20260702\repair_composite_coverage_20260706\repair_composite_coverage_design_20260706.json` |
| compile/token receipt | `docs\research\condition_research\research_runs\seed_lattice_20260702\repair_composite_coverage_20260706\repair_composite_compile_token_receipt_20260706.json` |
| seed JSON | `docs\research\condition_research\research_runs\seed_lattice_20260702\repair_composite_coverage_20260706\repair_composite_coverage_candidates_20260706_seeds.json` |
| DB register receipt | `docs\research\condition_research\research_runs\seed_lattice_20260702\repair_composite_coverage_20260706\register_repair_composite_coverage_receipt_20260706.json` |
| pairs | `docs\research\condition_research\research_runs\seed_lattice_20260702\repair_composite_coverage_20260706\pairs_repair_composite_coverage_24_20260706.json` |
| preflight result | `docs\research\condition_research\research_runs\seed_lattice_20260702\repair_composite_coverage_20260706\repair_composite_coverage_preflight_result_20260706.json` |
| freeze draft | `docs\research\condition_research\research_runs\seed_lattice_20260702\repair_composite_coverage_20260706\repair_composite_freeze_preregistration_draft_20260706.md` |

## 3. ?? ???

| ?? | ? |
| --- | --- |
| hold raw | 37 |
| dedup groups | 7 |
| designed pairs | 24 |
| compile/token pass | True/True |
| DB inserted seeds/rows | 24/48 |
| honest rows | 24 |
| status_counts | {"ok": 24} |
| decision_counts | {"hold": 1, "go": 16, "no_go": 7} |
| gate_passed | 16 |

DB ??:

| ?? | ? |
| --- | --- |
| inserted_seed_count | 24 |
| inserted_row_count | 48 |
| unsafe_target_name_count | 0 |
| conflicts | [] |
| backup_path | `ai_strategy_loop\state\loop_strategies.db.bak.lattice_20260705T230006Z` |

## 4. preflight ??

| ?? | ? |
| --- | --- |
| run_id | `lat_repair_composite_coverage_24_official_full_warm64_20260706` |
| profile | min / full-period / warm64 |
| DB | `_database/stock_min_back.db` |
| ?? | 2025-04-07 ~ 2026-02-27 |
| rows | 24 |
| status_counts | {"ok": 24} |
| decision_counts | {"hold": 1, "go": 16, "no_go": 7} |
| sell_profile_decision_counts | {"sell_default_tp3_sl3_hold60": {"hold": 1, "go": 11}, "sell_protect_tp2p5_sl2_hold45": {"go": 5, "no_go": 7}} |

?? go ??:

| gen | profit | mdd | daily | trades | sell | condition_id |
| --- | --- | --- | --- | --- | --- | --- |
| 6 | 2,164,253 | 27.16 | 0.5 | 106 | sell_default_tp3_sl3_hold60 | `repair_v2_20260706_04_cov04_profitmax_fourcell_sell_default_tp3_sl3_hold60` |
| 4 | 2,055,640 | 28.11 | 0.5 | 111 | sell_default_tp3_sl3_hold60 | `repair_v2_20260706_03_cov03_sparse_positive_fourcell_sell_default_tp3_sl3_hold60` |
| 22 | 1,778,558 | 20.31 | 1.0 | 211 | sell_default_tp3_sl3_hold60 | `repair_v2_20260706_12_cov12_all_positive_plus_l14_sell_default_tp3_sl3_hold60` |
| 2 | 1,417,718 | 27.31 | 0.5 | 97 | sell_default_tp3_sl3_hold60 | `repair_v2_20260706_02_cov02_sparse_positive_balanced_sell_default_tp3_sl3_hold60` |
| 7 | 1,179,483 | 21.3 | 0.5 | 111 | sell_protect_tp2p5_sl2_hold45 | `repair_v2_20260706_04_cov04_profitmax_fourcell_sell_protect_tp2p5_sl2_hold45` |
| 5 | 1,133,643 | 21.3 | 0.5 | 116 | sell_protect_tp2p5_sl2_hold45 | `repair_v2_20260706_03_cov03_sparse_positive_fourcell_sell_protect_tp2p5_sl2_hold45` |
| 1 | 1,122,503 | 20.95 | 0.5 | 98 | sell_protect_tp2p5_sl2_hold45 | `repair_v2_20260706_01_cov01_sparse_positive_core_sell_protect_tp2p5_sl2_hold45` |
| 3 | 1,069,026 | 21.6 | 0.5 | 101 | sell_protect_tp2p5_sl2_hold45 | `repair_v2_20260706_02_cov02_sparse_positive_balanced_sell_protect_tp2p5_sl2_hold45` |
| 18 | 975,080 | 28.32 | 0.8 | 166 | sell_default_tp3_sl3_hold60 | `repair_v2_20260706_10_cov10_strength_momentum_1430_sell_default_tp3_sl3_hold60` |
| 14 | 934,589 | 19.31 | 0.8 | 175 | sell_default_tp3_sl3_hold60 | `repair_v2_20260706_08_cov08_sparse_pair_l14_sell_default_tp3_sl3_hold60` |
| 12 | 797,362 | 20.92 | 0.8 | 179 | sell_default_tp3_sl3_hold60 | `repair_v2_20260706_07_cov07_strength_pair_l14_sell_default_tp3_sl3_hold60` |
| 10 | 583,238 | 20.31 | 0.7 | 152 | sell_default_tp3_sl3_hold60 | `repair_v2_20260706_06_cov06_profitmax_l14_sell_default_tp3_sl3_hold60` |

??:

- default sell(`tp3/sl3/hold60`)? 12? ? 11? go, 1? hold? ?? ?????.
- protective sell(`tp2.5/sl2/hold45`)? sparse-positive core??? ???? late/L14/L13 ????? ?? ?? MDD? ???.
- composite ??? ?? ???? `daily_avg_trades` ??? ??? ????.
- ?? ??? `cov04`, `cov03`, `cov12`, `cov02` ????.

## 5. ???? ??

| ?? ?? | ?? |
| --- | --- |
| Plan D/P7 | ??? |
| full tick 288 | ??? |
| full min 288 | ??? |
| OOS | ??? |
| portfolio | ??? |
| DB UPDATE/DELETE | ??? |
| git add -A | ??? |
| A3/promotion/export/live/final | ??? |
| dashboard 7??/.gjc/unrelated .omo | ??/???? ? ? |

## 6. ?? ??

full chunk ?? ?? ??: `YES, but no-OOS freeze/expanded-preflight first`.

Plan D ?? ?? ??: `NO`.

??:

- go ??? 16? ????? composite repair ??? ????.
- ??? ?? ??? train/full-period preflight ????, OOS survivor? ???.
- Plan D? seed pool/OOS survivor/portfolio ??? ????? ?? ? ? ??.

## 7. ?? ?? ???

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

??? repair-composite-freeze-expanded-preflight-no-D??? ????.
??? composite coverage preflight? go ?? 16?? freeze/preregistration ???? ????,
?? ??? ???? ?? composite ??? ?? ??? full chunk ?? OOS? ?? ? ???? ? ? ? ???? ???.

??? ?? ?? ??:
- docs/update_log/2026-07-06_repair_composite_coverage_preflight_no_d_handoff.md
- docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_coverage_20260706/repair_composite_coverage_preflight_result_20260706.json
- docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_coverage_20260706/repair_composite_freeze_preregistration_draft_20260706.md

??:
1. go ?? 16?? buy/sell sha? DB mapping? freeze ledger ??? ????.
2. OOS/portfolio/Plan D? ???? ???.
3. default sell ??? L14/L13 ??? ??? ??? ?? composite ??? ????.
4. ?? preflight? min lane ?? 48???? ????.
5. ??? ????? ?? ???? OOS ?? ??? ?? ???? ? ??? preregistration ??? ????.

??:
- Plan D/P7 ?? ??
- OOS ?? ??
- portfolio ?? ??
- full tick 288 ?? ??
- full min 288 ?? ??
- DB UPDATE/DELETE ??
- git add -A ??
- A3/promotion/export/live/final ?? ?? ??
- dashboard 7??, .gjc, unrelated .omo ?? ???? ??
```
