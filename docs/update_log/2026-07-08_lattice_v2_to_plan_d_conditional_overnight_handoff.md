# Lattice V2 to Plan D Conditional Overnight Handoff

Date: 2026-07-08T22:31:00+09:00

## Scope

Executed the conditional overnight page requested by:

`$ulw-loop docs/research/condition_research/plans/lattice_condition_generation_v2_to_plan_d_conditional_overnight_20260708.md`

The requested plan file did not exist at session start. A conservative plan file was created and then executed.

## Result Summary

| Item | Result |
|---|---:|
| Source documents read | 6 |
| Planned body seeds | 8 |
| DB INSERT-only seeds | 8 |
| DB INSERT-only rows | 16 |
| DB UPDATE/DELETE | 0 |
| Official limited replay profile | min full-period warm64 |
| Replay period | 2025-04-07 ~ 2026-02-27 |
| Replay pair count | 8 |
| Honest rows | 8/8 |
| OK rows | 7 |
| Error rows | 1 |
| Gate-passed rows | 0 |
| survivor | 0 |
| hold | 0 |
| no_go | 8 |
| OOS executed | no |
| seed_pool appended | no |
| Plan D executed | no |

## Key Interpretation

The 8 v2 body candidates did not fail because daily trade coverage was too low. The 7 OK rows had daily average trades between 20.5 and 143.9, so the coverage objective was achieved.

They failed because every OK row had negative profit and MDD far above the official cap:

| Metric | Range |
|---|---:|
| profit | -881,171,389 ~ -101,728,684 |
| MDD | 89.63 ~ 441.67 |
| daily avg trades | 20.5 ~ 143.9 |
| payoff ratio | 1.025 ~ 1.307 |

This is not a simple gate-strictness issue. The candidates generated enough trades, but the entry/sell/risk structure produced large loss and drawdown under the official min full-period profile.

## Replay Rows

| gen | label | status | profit | MDD | trades | daily | decision |
|---:|---|---|---:|---:|---:|---:|---|
| 0 | body_01_lattice_v2_coverage_01_s09_s10_l13_l14_daily_bridge | ok | -514,545,798 | 312.19 | 21,987 | 103.20 | no_go |
| 1 | body_02_lattice_v2_coverage_03_l13_l14_l1430_daily_boost | ok | -373,908,892 | 188.20 | 12,981 | 60.90 | no_go |
| 2 | body_03_lattice_v2_coverage_06_momentum_strength_surge_coverage | ok | -288,376,184 | 207.91 | 11,249 | 52.80 | no_go |
| 3 | body_04_lattice_v2_risk_01_mdd10_l13_l14_default_diverse | ok | -106,616,341 | 127.28 | 5,015 | 23.50 | no_go |
| 4 | body_05_lattice_v2_risk_08_dailycovered_nonpositive_repair | ok | -881,171,389 | 441.67 | 30,653 | 143.90 | no_go |
| 5 | body_06_lattice_v2_seed_01_rank03_r2_l13_l1430_component_only | ok | -103,427,022 | 90.64 | 4,487 | 21.10 | no_go |
| 6 | body_07_lattice_v2_neg_01_tick_prevday_active_0900_loss_shape | error | 0 | 0 | 0 | 0.00 | no_go |
| 7 | body_08_lattice_v2_hold_04_holdout_rank03_r2_l13_l1430_default | ok | -101,728,684 | 89.63 | 4,365 | 20.50 | no_go |

## Artifacts

- Plan: `docs/research/condition_research/plans/lattice_condition_generation_v2_to_plan_d_conditional_overnight_20260708.md`
- Source read receipt: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/source_read_receipt_20260708.json`
- Insert preflight: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_body_insert_preflight_20260708.json`
- Register apply receipt: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/register_lattice_v2_body_apply_20260708.json`
- Insert postcheck: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_body_insert_postcheck_20260708.json`
- Pairs: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/pairs_lattice_v2_body_8_inserted_20260708.json`
- Mapping ledger: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_body_strategy_name_mapping_apply_20260708.jsonl`
- Provenance ledger: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/provenance_lattice_v2_body_register_apply_20260708.jsonl`
- Limited replay result: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_body8_min_warm64_limited_replay_result_20260708.json`
- Stop decision: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_to_plan_d_stop_decision_20260708.json`
- DB backup: `ai_strategy_loop/state/loop_strategies.db.bak.lattice_20260708T132014Z`

## Boundary Decision

Plan D is not opened from these 8 body seeds.

Reason: the preregistered branch required at least one limited replay survivor before OOS and seed_pool append. This page produced zero survivors and zero hold rows. Therefore:

- OOS was not executed.
- `oos_survivors.jsonl` was not appended.
- `seed_pool.jsonl` was not appended.
- Plan D intake/readiness was not executed.
- portfolio/export/live/final promotion remained untouched.

## What This Adds To The Research

This page gives a clean negative result:

1. v2 body generation can create syntactically valid and DB-registerable candidates.
2. coverage-oriented candidates can solve the daily-trade scarcity problem.
3. the current v2 body design still fails the performance problem because risk and sell-side loss control are insufficient.
4. Plan D should not be used as a rescue loop without a survivor seed.

## Recommended Next Command

```text
$ulw-plan docs/research/condition_research/plans/lattice_condition_generation_v2_risk_sell_repair_review_20260709.md

목표는 v2 body 8개 limited replay 실패 원인을 손실 구간, 매도 조건, 보유 시간, 시간대, family별로 재분석하고,
다음 후보 생성을 실행하기 전에 risk/sell-side 제약을 재설계할지 중단할지 결정하는 것이다.

반드시 먼저 읽을 문서:
- docs/update_log/2026-07-08_lattice_v2_to_plan_d_conditional_overnight_handoff.md
- docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_body8_min_warm64_limited_replay_result_20260708.json
- docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_to_plan_d_stop_decision_20260708.json

금지:
- DB INSERT/UPDATE/DELETE 금지
- replay/OOS/Plan D 실행 금지
- portfolio/export/live/final promotion 금지

완료 후 보고:
- 손실 원인 분석
- sell/risk 제약 재설계 필요 여부
- 다음 후보 생성 여부
- 전체 연구 중단/계속 추천
```
