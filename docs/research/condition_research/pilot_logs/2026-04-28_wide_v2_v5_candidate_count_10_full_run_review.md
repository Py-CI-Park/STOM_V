# Wide v2 v5 candidate_count=10 full run 검토

## 실행 목적

Wide v2 v5 자동 개선 루프에서 full candidate count인 `candidate_count=10`을 실제 2025년 백테스트 데이터로 실행하고, WFO/OOS 검증으로 넘길 final best 후보를 선정할 수 있는지 확인했다.

이번 실행은 WFO/OOS가 아니다. 실행 목적은 후보 생성, 후보 선정, ranking, global best 선정, WFO handoff metadata 기록까지 이어지는지 검증하는 것이다.

## 실행 조건

- run_id: `WideV2V5CandidateCount10FullRun_20260428`
- candidate_count: `10`
- max_rounds: `1`
- start/end: `20250101-20251231`
- seed_candidate: `WideV1Final_B_20260425`
- seed_expression: `66.999 <= 시가총액 < 2_580 and 등락율 > 4.83`
- sell_strategy: `ResearchTest_Tick_S_090000_092800_Wide_20260419`
- elapsed: `00:06:19.5446378`
- exit_code: not captured because the run was monitored via `Start-Process`; structured summary JSON was generated and used for decision.

## 결과 요약

- status: `error`
- stop_reason: `insufficient_candidates`
- completed_round_count: `0`
- failed_round: `1`
- failure_phase: `insufficient_retention_candidates`
- failure_message: `candidate_count=10 requested but only 4 candidates selected after retention filtering`
- requested_candidate_count: `10`
- selected_candidate_count: `4`
- leaderboard_count: `0`
- final_best_candidate: 없음
- wfo_candidate: 없음

## 후보 생성/선정 상태

- initial_v4_candidate_count: `4`
- recovery_attempted: `False`
- recovery_reason: `direct_v4_available`
- final_candidate_pool_count: `4`
- eligible_count: `4`
- execution_count: `4`
- planned_execution_count: `4`

이번 실패의 핵심은 runtime failure가 아니라 후보 풀 shortfall이다. v4 후보가 4개 존재했기 때문에 v5 recovery가 실행되지 않았고, 그 결과 `candidate_count=10` 요청을 만족하지 못했다. 기존 recovery는 v4 후보가 0개일 때의 복구에는 대응했지만, v4 후보가 존재하더라도 요청 수보다 부족한 경우까지 확장하지 않았다.

## Round 상태

```text
round001
-> status=error
-> phase=insufficient_retention_candidates
-> source_candidate=WideV1Final_B_20260425
-> failure_message=candidate_count=10 requested but only 4 candidates selected after retention filtering
```

## Markdown report 확인

생성된 optimizer Markdown report는 다음 섹션을 포함했다.

- `# Wide v2 optimizer summary`
- `## Global leaderboard top candidates`
- `## Next seed selection`
- `## WFO handoff`
- `The final candidate is a WFO candidate, not a live-trading approval.`

즉, 출력/보고서 작성 경로는 정상이다. 문제는 보고서 생성이 아니라 후보 수 부족이다.

## 퀀트 관점 판정

`candidate_count=10` 단계는 더 넓은 후보군을 실제 백테스트로 비교해 WFO 후보를 고르기 위한 단계다. 그런데 현재는 후보가 10개까지 확장되지 못해 WFO 후보를 선정할 수 없다.

이 상태에서 WFO/OOS로 넘어가면 안 된다. final best 후보가 없고, leaderboard도 비어 있기 때문이다. 먼저 v5 후보 생성/복구 정책을 보강해야 한다.

필요한 개선 방향은 다음과 같다.

```text
v4 후보가 0개일 때만 recovery
-> v4 후보가 요청 수보다 적을 때도 recovery
-> direct_v4 후보 + recovery 후보를 합쳐 candidate_count=10 충족
-> actual row-set/retention gate 통과 후보 확보
-> candidate_count=10 full run 재실행
```

## CLI 관점 판정

CLI는 실패를 traceback이 아니라 구조화된 summary JSON으로 기록했다. 따라서 이번 실패는 복구 가능한 설계 분기다.

확인된 metadata:

- `status=error`
- `stop_reason=insufficient_candidates`
- `failure_phase=insufficient_retention_candidates`
- `requested_candidate_count=10`
- `selected_candidate_count=4`
- `recovery_attempted=False`
- `recovery_reason=direct_v4_available`

다음 설계에서는 `direct_v4_available`이어도 `final_candidate_pool_count < candidate_count`이면 recovery를 추가 실행하는 정책을 검토해야 한다.

## 결정

- decision: `HOLD_CANDIDATE_COUNT_10_SHORTFALL`
- next_command: `$brainstorming Wide v2 v5 direct_v4 shortfall recovery 설계`

## 남은 MVP 단계

```text
1. direct_v4 shortfall recovery 설계
2. v4 후보 1~9개 상태에서도 recovery 후보를 보강하도록 구현
3. candidate_count=10 full run 재실행
4. final_best_candidate WFO/OOS 검증
5. WFO/OOS 결과를 기준으로 MVP freeze 또는 후보 생성 보강 분기
6. PR 보고서 작성 및 merge point 생성
```
