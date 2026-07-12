# Lattice V3 Failure Lesson Matrix (CL-D1)

- 계획: `.omo/plans/ai-condition-loop-canonical-rebuild-20260711.md` (todo 2 / CL-D1)
- 상위 실행계약: `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md` (T1)
- 목표 권한: `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md`
- 성격: 설계 전용(design-only) 실패 교훈 정리. 조건식 본문 생성·DB·replay·OOS 없음.

이 문서는 이전 조건식 연구의 8개 실패 근거를 유형별로 분리하고, 각각에서 재사용 가능한 자산과 금지 추론을 확정한다. 어떤 `no_go`/실패 행도 생존(survivor)·`go`·`hold`로 재해석하지 않는다.

## 요약 표

| # | 근거 family | 엔진/프로파일 | 핵심 결과 | 상태 |
|---:|---|---|---|---|
| 1 | tick 288 official warm64 | 공식 STOM, tick lane, warm64, full | gate_passed 0/288, MDD 수백~1000%+ | 실패 기준선 |
| 2 | min 288 official warm64 | 공식 STOM, min lane, warm64, full | gate_passed 0/288 (ok 281, error 7) | 실패 기준선 |
| 3 | integrated 576 | p6 통합 판정 (tick 288 + min 288) | go 0, hold 0, no_go 576 | 완전 실패 기준선 |
| 4 | repair composite | composite/seed 좁힌 후보, 제한 OOS-style | bounded 신호 산출, 승격 증명 아님 | 참고 자산 |
| 5 | bounded Plan D (rank01/02/03) | 제한 Plan D, seed passport | seed 증거 산출, portfolio/export 증명 아님 | 참고 자산 + 과적합 경고 |
| 6 | V2 eight-body limited replay | Failure-Guided-8, min 중심, 제한 replay | 8/7/1/0/0/8, 7 OK 전부 손실 | 종료·본문 재사용 금지 |
| 7 | corrected sell/risk clause audit | sell_code 임계값 재추출 감사 | 진단 보정, no_go 판정 불변 | 방법론 교훈 |
| 8 | batch-vs-autonomous distinction | fixed-pair batch eval vs run_loop | batch는 자율 학습 아님 | 소유권 교훈 |

각 family는 아래 7개 필드로 분리한다: engine/profile/process, gate threshold, entry structure, exit/risk, data leakage / blindness, reusable asset, forbidden inference.

---

## Family 1 — tick 288 official warm64
- **engine/profile/process**: 공식 STOM 백테스트, tick lane, warm64, full period, 288 pair(Broad-Grid-576의 tick 절반). 근거 `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_full_warm64_288_export_summary_20260705.json`.
- **gate threshold**: gate_passed 0/288. 게이트는 MDD cap 35, 비용 후 양의 수익, 일평균 거래 충분, payoff 목표. 통과 0.
- **entry structure**: lattice_v1 tick 진입 family(momentum_breakout, prevday_active, strength_surge, volume_surge 등) × 시간대 × size × strength 조합.
- **exit/risk**: tick 청산·리스크가 MDD를 전혀 통제하지 못함. no_go 표본 MDD가 280.1 / 801.6 / 1044 / 1157.6 등 수백~1000%+.
- **data leakage / blindness**: full-period 단일 결과이며 봉인 OOS나 시계열 분할이 아니다.
- **reusable asset**: 음성 기준선(negative baseline)과 tick MDD 폭발의 실패 분포. tick을 진단/스트레스 전용 lane으로 두어야 한다는 근거.
- **forbidden inference**: tick 격자를 재현하면 성과가 난다고 추론 금지. tick을 primary lane으로 삼기 금지.

## Family 2 — min 288 official warm64
- **engine/profile/process**: 공식 STOM, min lane, warm64, full period, 288 pair. 근거 `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_official_full_warm64_288_export_summary_20260705.json`.
- **gate threshold**: gate_passed 0/288. ok 281, error 7. negative_profit 271, mdd_excess 215(pure 200 + combined 15), low_daily_trades 58.
- **entry structure**: min lane lattice_v1 진입 family × 시간대/size/strength.
- **exit/risk**: min은 tick보다 MDD가 작지만(avg 70.99, median 55.82) 여전히 cap 35 초과 다수이고 수익은 음수 지배.
- **data leakage / blindness**: full-period 단일 결과. 봉인 OOS 아님.
- **reusable asset**: min이 tick보다 덜 폭발적이라는 사실 → min-primary 설계 근거. feature family별 실패 분포.
- **forbidden inference**: min 288 재현을 성과로 추론 금지. 게이트 완화로 통과시키기 금지.

## Family 3 — integrated 576 go/no-go/hold
- **engine/profile/process**: p6 통합 판정(tick 288 + min 288 = 576). 근거 `docs/research/condition_research/research_runs/seed_lattice_20260702/p6_lattice_go_no_go_hold_20260705.json`.
- **gate threshold**: go 0, hold 0, no_go 576. 주 실패 사유(primary_fail) 대부분 mdd_excess.
- **entry structure**: Broad-Grid-576 전체 진입 family 격자.
- **exit/risk**: 진입·청산 결합이 MDD를 통제하지 못함.
- **data leakage / blindness**: full-period 단일 결과. OOS 아님.
- **reusable asset**: 완전 실패 기준선. 넓은 격자 탐색이 edge를 내지 못한다는 증거.
- **forbidden inference**: Broad-Grid-576 재개 금지. 격자 축 확장이 해답이라고 추론 금지.

## Family 4 — repair composite
- **engine/profile/process**: repair composite(coverage/risk-balanced composite로 좁힌 후보), 제한 OOS-style 실행. 근거 `docs/update_log/2026-07-08_condition_research_full_result_and_analysis.md`, `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md`.
- **gate threshold**: bounded OOS-style 신호를 냈으나 승격 게이트 통과 증명이 아니다.
- **entry structure**: composite/seed 기반으로 좁힌 진입.
- **exit/risk**: 좁힌 리스크로 bounded signal이 가능했음.
- **data leakage / blindness**: same-CSV holdout 위험. 봉인 미래 OOS가 아님.
- **reusable asset**: composite/seed narrowing이 bounded signal을 낼 수 있다는 증거 → feature family 참고 자산.
- **forbidden inference**: repair composite 결과를 승격/성과 증명으로 간주 금지.

## Family 5 — bounded Plan D (rank01/rank02/rank03)
- **engine/profile/process**: 제한 Plan D 실행, rank01/rank02/rank03, seed passport. 근거 `docs/update_log/2026-07-08_condition_research_full_result_and_analysis.md`(Plan D rank 비교·과적합 절), `docs/update_log/2026-07-09_condition_research_cross_agent_handoff.md`.
- **gate threshold**: seed 증거를 산출했으나 portfolio/export 증명이 아니다.
- **entry structure**: rank별 seed 후보.
- **exit/risk**: seed 과적합 위험.
- **data leakage / blindness**: seed 과적합·holdout 조기 열람 위험.
- **reusable asset**: seed passport 패턴과 overfit-risk 교훈.
- **forbidden inference**: Plan D seed를 portfolio/export/promotion 증명으로 간주 금지. 무제한 Plan D 루프 금지.

## Family 6 — V2 eight-body limited replay
- **engine/profile/process**: Failure-Guided-8, min 중심, 공식 제한 replay, 8 body. 근거 `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md`, `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_closeout_or_new_design_decision_20260709.json`.
- **gate threshold**: 카운트 `8/7/1/0/0/8` = total 8 / OK 7 / error(no_metrics) 1 / survivor 0 / hold 0 / no_go 8. OK 7개 전부 음수익, MDD 89.63~441.67(cap 35 초과).
- **entry structure**: V1 실패지도 + repair composite + 제한 Plan D 단서로 재설계한 min 진입.
- **exit/risk**: 매수+매도 결합 실패. ablation이 없어 진입/청산 중 어느 쪽 원인인지 미분리.
- **data leakage / blindness**: 제한 replay로 OOS/Plan D/portfolio/full-288 누수가 없음(정직한 실행).
- **reusable asset**: 이 브랜치의 종료 기준. syntax/registration hygiene 참고.
- **forbidden inference**: 실패 본체의 미세 변형으로 성과가 난다고 추론 금지. no_go를 survivor/hold로 재해석 금지.

## Family 7 — corrected sell/risk clause audit
- **engine/profile/process**: 원본 sell_code에서 임계값을 재추출한 감사. 근거 `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_corrected_sell_risk_clause_audit_20260709.md`, 리뷰의 'Corrected Sell/Risk Finding' 절.
- **gate threshold**: 감사 결과 판정 변화 없음. no_go 불변.
- **entry structure**: 해당 없음(청산/리스크 절 감사).
- **exit/risk**: 이전 표의 `90`/`120`은 stop/take-profit이 아니라 hold-time(분) 임계값이었다. 보정: stop-loss = 음수 `<=` 수익률 임계값(예 -3, -2), take-profit = 소폭 양수 `>=`(1~4), late-session exit = 시간 임계값(예 145500).
- **data leakage / blindness**: 감사만 수행, 실행/누수 없음.
- **reusable asset**: 임계값 provenance를 절(clause) 종류별로 분리 기록해야 한다는 교훈.
- **forbidden inference**: 임계값 표 보정이 손실 결과를 되돌린다고 추론 금지. 결론 토큰: `v2_sell_risk_table_superseded_but_decision_unchanged`.

## Family 8 — batch-vs-autonomous distinction
- **engine/profile/process**: `ai_strategy_loop/scripts/claude_candidate_batch_eval.py`는 고정 후보쌍을 평가해 provider=batch 결과를 발행하며 생성/부검을 호출하지 않는다. `ai_strategy_loop/controller/loop.py::run_loop`만 실제 provider를 만들어 생성 → 공식 평가 → 부검 → 다음 세대 폐루프를 수행한다. 근거 `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md`(sec8 단일 실행 소유권), `docs/AGENT_HANDOFF.md`.
- **gate threshold**: batch run은 통과/실패를 기록하지만 자율 세대 진행을 만들지 않는다.
- **entry structure**: batch는 고정 입력 후보쌍. 다음 세대의 자율 생성은 run_loop만 수행.
- **exit/risk**: 해당 없음(프로세스 구분).
- **data leakage / blindness**: batch 평가 결과를 세대 학습 증명으로 오인하는 것이 위험.
- **reusable asset**: batch는 정적/회귀 평가 도구이자 음성 대조군으로 유용.
- **forbidden inference**: batch 평가 완료를 자율 학습 완료로 간주 금지. 결론 토큰: `provider_batch_is_not_autonomous_learning`.

---

## 필수 결론 (mandatory conclusions)

1. `gate_relaxation_is_not_sufficient`
   Broad-Grid-576, tick 288, min 288, V2 8-body가 모두 음수익이며 MDD가 cap 35를 크게 초과한다. 게이트를 완화하면 손실 전략을 통과시킬 뿐이다. 실패의 성격은 게이트 엄격성 문제가 아니라 후보 자체의 성과 문제다.

2. `v2_sell_risk_table_superseded_but_decision_unchanged`
   이전 sell/risk 임계값 표는 hold-time(분) 값을 stop/take-profit으로 오추출했다. 재추출로 표는 보정(superseded)됐지만 제한 replay 지표가 그대로 음수라 V2 종료 판정(no_go, archive_v2_branch_and_stop)은 불변이다.

3. `provider_batch_is_not_autonomous_learning`
   최신 provider=batch run은 고정 후보 평가이며 생성/부검을 호출하지 않는다. 따라서 평가 인프라 작동은 증명됐어도 자율 조건식 개선(세대 간 학습)은 증명되지 않았다.

## 재해석 금지 선언

- Broad-Grid-576: go 0, hold 0, no_go 576. 어떤 행도 생존/보류로 승격하지 않는다.
- Failure-Guided-8(V2): survivor 0, hold 0, no_go 8. `8/7/1/0/0/8`를 유지한다.
- repair composite / Plan D의 bounded 신호·seed는 참고 자산일 뿐 승격 증명이 아니다.
