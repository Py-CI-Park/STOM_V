# Plan D rank03 R2-05 selected OOS-style preregistration

작성시각: 2026-07-07 22:32 KST

## Scope

이번 실행은 rank03 R2 limited replay에서 유일하게 `improved`로 분류된 1개 후보만 대상으로 한다.

- label: `plan_d_r1_rank03_r2_05_l13_l1430_default_tp3_sl3_hold90`
- buy: `LAT_plan_d_r1_rank03_r2_05_l13_l1430_default_tp3_sl3_hold90_B`
- sell: `LAT_plan_d_r1_rank03_r2_05_l13_l1430_default_tp3_sl3_hold90_S`
- lane: `min`
- purpose: R2-05가 단순 replay 개선인지, Plan D 다음 라운드 입력으로 볼 수 있는 robustness가 있는지 확인한다.

## Freeze Verification

DB mapping은 `stockbuy`/`stocksell`을 읽기 전용으로 확인했다.

| item | value |
|---|---|
| freeze ledger | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/plan_d_rank03_r2_selected_freeze_ledger_20260707.jsonl` |
| freeze recheck | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/plan_d_rank03_r2_selected_freeze_recheck_20260708.json` |
| buy sha256 | `162391fa9848410b0771df5e558ba7af6014eb1a3a0c1ef521ecf80aaa559518` |
| sell sha256 | `5c02facbbb42d2072a699f054a86d79f31695ef5fc0fbdd9e1d902fb7be83271` |
| DB SHA match | true |

## Replay Protocol

| item | value |
|---|---|
| pairs | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/pairs_plan_d_rank03_r2_selected1_oos_20260708.json` |
| config | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/oos_config_min_plan_d_rank03_r2_selected1_20260708.json` |
| run_id | `lat_plan_d_rank03_r2_selected1_oos_min_warm64_20260708` |
| DB | `_database/stock_min_back.db` |
| OOS-style window | `2026-01-01~2026-02-27` |
| time window | `09:00~15:19` |
| warm engines | 64 |
| max pairs | 1 |

The runtime fields are inherited from the previous official min warm64 OOS-style config. A corrected config copy is used because the prior file retained stale rank03 R1 metadata in descriptive fields, while its execution fields were already min/OOS/warm64.

## Decision Rule

- `survivor`: status ok, gate_passed true, profit > 0, MDD <= 35, daily_avg_trades >= 0.5.
- `hold`: status ok and profit > 0, but at least one non-critical gate weakens the case.
- `no_go`: execution error, no trades, profit <= 0, or MDD > 35.

## Guardrails

- Execute only the selected R2-05 pair.
- Do not open R3 automatically even if it survives.
- Do not run portfolio, export/live/final promotion, full tick 288, or full min 288.
- Do not use DB UPDATE/DELETE.
- Append `oos_survivors` and `seed_pool` only if the selected candidate satisfies the survivor rule.

## Caveat

This is not a fully blind OOS discovery test. R2-05 was selected from a full-period min replay that already included the 2026-01-01 to 2026-02-27 window. Treat this run as a fixed OOS-style robustness check and as a boundary decision for whether Plan D should continue.
