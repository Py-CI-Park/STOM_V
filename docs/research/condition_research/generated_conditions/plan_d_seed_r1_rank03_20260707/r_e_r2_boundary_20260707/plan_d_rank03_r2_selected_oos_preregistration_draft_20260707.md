# Plan D Rank03 R2 Selected OOS Preregistration Draft

작성시각: 2026-07-07T21:24:00+09:00

## Scope

- 대상: `plan_d_r1_rank03_r2_05_l13_l1430_default_tp3_sl3_hold90`
- 목적: rank03 R2 limited replay에서 유일하게 `profit 증가 + MDD 감소 + daily 증가`를 동시에 만족한 후보 1개만 OOS-style robustness replay 대상으로 고정한다.
- 이번 문서는 preregistration 초안이다. 이 문서 작성 시점에는 OOS, portfolio, export/live/final promotion을 실행하지 않았다.

## Freeze

| 항목 | 값 |
|---|---|
| label | `plan_d_r1_rank03_r2_05_l13_l1430_default_tp3_sl3_hold90` |
| buy | `LAT_plan_d_r1_rank03_r2_05_l13_l1430_default_tp3_sl3_hold90_B` |
| sell | `LAT_plan_d_r1_rank03_r2_05_l13_l1430_default_tp3_sl3_hold90_S` |
| buy_sha256 | `162391fa9848410b0771df5e558ba7af6014eb1a3a0c1ef521ecf80aaa559518` |
| sell_sha256 | `5c02facbbb42d2072a699f054a86d79f31695ef5fc0fbdd9e1d902fb7be83271` |
| parent baseline | `plan_d_r1_rank03_r1_08_parent_buy_default_tp3_sl3_hold90` |

## Replay Basis

| 지표 | R1 parent preflight | R2-05 limited replay | 변화 |
|---|---:|---:|---:|
| profit | 1,652,322 | 1,912,728 | +260,406 |
| MDD | 15.79 | 10.79 | -5.00 |
| trades | 181 | 439 | +258 |
| daily_avg_trades | 0.8 | 2.1 | +1.3 |
| payoff | 1.44498 | 1.31644 | -0.12854 |

## OOS Protocol

- pairs: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/pairs_plan_d_rank03_r2_selected1_oos_20260707.json`
- config: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/oos_config_min_plan_d_rank03_r2_selected1_20260707.json`
- lane: `min`
- DB: `_database/stock_min_back.db`
- OOS window: `2026-01-01~2026-02-27`
- engine: `warm64`
- time window: min full session, runtime resolves to `09:00~15:19`

## Guardrails

- OOS 실행 전 이 freeze/preregistration 문서를 다시 확인한다.
- selected 1개 외 후보 OOS 금지.
- portfolio 산출 금지.
- export/live/final promotion 금지.
- full tick 288/full min 288 실행 금지.
- DB UPDATE/DELETE 금지.

## Caveat

R2-05는 공식 전체기간 min replay에서 선별되었고, 그 전체기간에는 2026-01-01~2026-02-27도 포함되어 있다. 따라서 다음 실행은 완전한 blind OOS가 아니라 고정 후보 robustness/OOS-style 재검증으로 해석해야 한다.
