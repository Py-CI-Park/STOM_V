# Wide v2 v5 recovery smoke 리뷰

## 목적

Wide v2 v5 recovery 구현 후 `candidate_count=2`, `max_rounds=2` smoke가 v5 후보 풀 0개 실패를 벗어나 후보 backtest 단계까지 진입하는지 확인했다.

## 실행 요약

| 항목 | 값 |
| --- | --- |
| run_id | WideV2V5RecoverySmoke_20260428 |
| candidate_count | 2 |
| max_rounds | 2 |
| exit_code | 1 |
| elapsed_minutes | 29.88 |
| status | error |
| stop_reason | invalid_seed_expression |
| completed_round_count | 1 |
| failed_round | 2 |
| failure_phase | invalid_seed_expression |
| failure_message | next seed expression is invalid |

## Recovery 판정

| 항목 | 값 |
| --- | --- |
| round001_status | ok |
| initial_v4_candidate_count | 0 |
| recovery_attempted | True |
| recovery_reason | v4_candidate_pool_empty |
| recovery_family_counts | auto_secondary_feature=4, recovered_trade_feature=10 |
| final_candidate_pool_count | 14 |
| eligible_count | 14 |
| planned_execution_count | 4 |
| execution_count | 4 |
| actual_selected_count | 2 |
| row_set_identity_status | all_distinct |
| leaderboard_count | 4 |

## 결과 해석

v5 recovery 자체는 성공했다. 이전 smoke의 핵심 실패였던 `v4_candidate_count=0`, `final_candidate_pool_count=0`, `execution_count=0` 상태를 벗어났고, round001에서 후보 backtest 4개와 leaderboard 4개가 생성됐다.

전체 optimizer는 실패로 종료됐다. round001 best candidate가 `66.999 <= 시가총액 < 2_580 and 546.999 <= 당일거래대금 < 2_173`로 선택되었는데, 현재 optimizer 설정의 v5 `iteration_v2_trade_amount_feature`는 `B_등락율`이다. 따라서 round002 seed 검증에서 seed expression이 `시가총액 + 등락율` 2조건 형태가 아니라고 판단되어 `invalid_seed_expression`으로 중단됐다.

## 결론

PARTIAL PASS: v5 후보 풀 recovery 구현 목표는 달성했다. 그러나 Wide v2 반복 루프 관점에서는 다음 round seed 검증 정책과 recovery 후보 family의 seed 호환성 문제가 남아 있으므로 `candidate_count=10` full run으로 바로 넘어가면 같은 유형의 중단이 반복될 가능성이 높다.

## 다음 단계

다음 작업은 full run이 아니라 `Wide v2 v5 next seed expression validation recovery` 설계가 맞다. 선택지는 두 가지다.

1. v5 반복 루프에서 다음 seed로 사용할 후보는 `primary_feature + trade_amount_feature`를 유지하는 family만 허용한다.
2. optimizer가 v5 winner를 다음 round seed로 사용할 때 winner expression의 실제 feature 구성을 감지해 `iteration_v2_trade_amount_feature`를 함께 갱신한다.

퀀트/CLI 관점에서는 1번이 더 보수적이다. 조건식 자동 개선 루프의 비교 기준을 안정적으로 유지하고, seed feature 축이 round마다 바뀌는 문제를 막을 수 있다.
