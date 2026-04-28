# Wide v2 smoke/full run 검증 리뷰

## 목적

Wide v2 optimizer가 실제 백테스트 실행에서 후보 생성, 후보 백테스트, leaderboard 기록, final best 선정, WFO handoff 후보 기록까지 이어질 수 있는지 확인한다.

## 실행 요약

| 구분 | candidate_count | max_rounds | 완료 round | 소요 시간 | status | stop_reason |
| --- | ---: | ---: | ---: | --- | --- | --- |
| smoke | 2 | 2 | 0 | 4.82분 | error | insufficient_candidates |
| candidate_count=10 | 10 | 미실행 | 미실행 | 미실행 | 미실행 | smoke gate 미통과 |

## Smoke 판정

- run_id: `WideV2Smoke_20260427`
- final_best_candidate: 없음
- wfo_candidate: 없음
- leaderboard_count: 0
- failed_round: 1
- failure_phase: `insufficient_retention_candidates`
- failure_message: `candidate_count=2 requested but only 0 candidates selected after retention filtering`
- 판정: `recovery-needed`

## 확인된 세부 원인

Smoke는 Python traceback 없이 구조화된 실패로 종료했다. 백테스트 엔진은 baseline backtest를 완료했고 CSV도 생성했다.

- baseline_csv: `backtest/csv\stock_bt_WideV1Final_B_20260425_20260427160214.csv`
- baseline trade_count: 27416
- baseline elapsed_seconds: 277.782
- iteration runtime elapsed_seconds: 285.25

후보 생성/선택 단계의 상태는 다음과 같다.

| 항목 | 값 |
| --- | ---: |
| requested_candidate_count | 2 |
| selected_candidate_count | 0 |
| v4_candidate_count | 0 |
| eligible_count | 0 |
| execution_count | 0 |
| planned_execution_count | 0 |
| retention pool_count | 0 |
| retention selected_count | 0 |

즉, 실패의 직접 원인은 후보 백테스트 실패가 아니라 `best_feature_mix_v5`가 실행할 v4 후보 풀을 만들지 못한 것이다. 분석 결과에는 `B_등락율` 추천 후보가 존재하지만, smoke 기본 인자 조합에서는 v4/v5 실행 후보로 전달되지 않았다.

## Candidate Count 10 판정

`candidate_count=10` full run은 실행하지 않았다.

이유는 smoke gate가 실패했기 때문이다. 현재 상태에서 full run을 실행하면 같은 후보 생성 shortfall이 반복될 가능성이 높고, 실행 시간이 늘어도 검증 정보가 추가되지 않는다.

## 퀀트 관점 검토

- 현재 실패는 수익성 평가 실패가 아니라 후보 생성 루프의 입력/선택 실패다.
- final_best_candidate가 없으므로 WFO/OOS 검증으로 넘어가면 안 된다.
- 조건식 자동 개선 루프의 다음 개선점은 "백테스트를 더 많이 실행"이 아니라 "v5가 최소 후보 풀을 안정적으로 생성하도록 만드는 것"이다.
- `B_등락율` 후보 자체는 분석 결과에 존재하므로, 후보 전달 범위, `top_n`, secondary feature, retention/fallback 정책을 함께 검토해야 한다.

## CLI 개발 관점 검토

- 장점: 실패가 traceback이 아니라 `status`, `stop_reason`, `failure_phase`, `failure_message`로 남았다.
- 장점: `summary_output`, `leaderboard_output`, Markdown report가 생성되었다.
- 문제: `requested_candidate_count`와 `selected_candidate_count`가 optimizer summary 최상위에서는 `null`이고, round runtime JSON에는 각각 2와 0으로 존재한다. 실행 리뷰에는 round runtime JSON 기준 값을 사용했다.
- 문제: full run 계획의 기본 명령은 `top_n=1`이라 v5 후보 생성에 충분하지 않을 수 있다.

## 다음 단계

다음 단계는 WFO 검증이 아니다. 먼저 후보 풀 shortfall recovery 설계를 해야 한다.

추천 명령:

```text
$brainstorming Wide v2 smoke insufficient_candidates recovery 및 v5 후보 풀 생성 보강 설계
```

검토할 설계 후보:

1. `optimize-wide-v2` smoke/full run 기본 명령에 `--top-n`을 명시해 v4 후보 생성 입력을 넓힌다.
2. `best_feature_mix_v5`에서 v4 후보가 0개일 때 분석 결과의 `recommended_candidates` 또는 fallback family를 사용하는 복구 경로를 추가한다.
3. `iteration_v2_secondary_features` 기본값 또는 실행 명령에 보조 feature를 명시해 `replace_secondary`/`tighten_secondary` 후보군을 보장한다.
4. optimizer summary 최상위에 `requested_candidate_count=2`, `selected_candidate_count=0`을 보존하도록 실패 metadata 전달을 보강한다.
