# Wide v2 v5 direct_v4 shortfall recovery design

## Purpose

Wide v2 v5의 다음 수정 목표는 `candidate_count=10` full run이 후보 4개에서 중단된 문제를 해결하는 것이다.

이번 문제는 백테스트 엔진 장애나 WFO/OOS 검증 문제가 아니다. v4 후보가 0개일 때만 v5 recovery가 실행되고, v4 후보가 존재하지만 요청 수보다 부족한 경우에는 recovery가 생략되는 후보 풀 부족 문제다.

최종 목적은 기존 Wide v2 MVP 흐름을 유지하면서 다음 경로가 실제로 실행되게 만드는 것이다.

```text
기준 조건식
-> 백테스트
-> 결과 분석
-> 후보 조건식 자동 생성
-> 후보 백테스트
-> 후보 성능/row-set 비교
-> best 후보 선택
-> 다음 round seed로 반복
-> final_best_candidate 선정
-> WFO/OOS 검증 대상으로 handoff
```

이번 설계는 그중 `후보 조건식 자동 생성 -> 후보 백테스트` 사이의 후보 수 부족을 보강한다.

## Current Failure

직전 full run 검증 결과는 다음과 같다.

```text
run_id: WideV2V5CandidateCount10FullRun_20260428
candidate_count: 10
max_rounds: 1
status: error
stop_reason: insufficient_candidates
failure_phase: insufficient_retention_candidates
failure_message: candidate_count=10 requested but only 4 candidates selected after retention filtering
requested_candidate_count: 10
selected_candidate_count: 4
initial_v4_candidate_count: 4
recovery_attempted: False
recovery_reason: direct_v4_available
final_candidate_pool_count: 4
eligible_count: 4
execution_count: 4
planned_execution_count: 4
leaderboard_count: 0
final_best_candidate: none
wfo_candidate: none
```

현재 흐름은 다음과 같이 실패한다.

```text
v4 후보 pool count=4
-> direct_v4_available
-> v5 recovery skipped
-> retention/row-set selected=4
-> candidate_count=10 shortfall
-> 후보 백테스트 시작 전 중단
```

목표 흐름은 다음과 같다.

```text
v4 후보 pool count=4
-> direct_v4_shortfall
-> direct_v4 후보 4개 보존
-> 부족분을 recovery 후보로 보강
-> direct_v4 + recovery 후보 dedupe
-> retention/row-set selected >= 10
-> candidate_count=10 후보 백테스트 진입
```

## Design Alternatives

### Option A: direct_v4 부족분만 recovery로 보강

`0 < direct_v4_count < candidate_count`일 때 direct_v4 후보를 유지하고 recovery 후보를 추가 생성한다.

장점:

- 현재 v4 후보를 버리지 않는다.
- v4 후보 0개 복구와 같은 recovery 생성 경로를 재사용한다.
- 변경 범위가 `cli/research_iteration_v5_recovery.py`와 관련 테스트 중심으로 작다.
- `candidate_count=10` full run 재검증 목적과 가장 직접적으로 연결된다.

단점:

- direct 후보와 recovery 후보가 중복될 수 있어 dedupe 우선순위가 필요하다.
- recovery를 추가해도 retention 통과 후보가 여전히 부족할 수 있다. 이 경우 다음 문제는 후보 family 확장으로 분리한다.

### Option B: direct_v4가 있어도 항상 recovery 후보를 추가

v4 후보 수와 관계없이 recovery 후보를 항상 섞는다.

장점:

- 후보 다양성이 늘어날 수 있다.
- candidate_count가 커져도 더 많은 후보를 확보할 수 있다.

단점:

- 이미 충분한 direct_v4 후보가 있을 때도 후보 분포가 바뀐다.
- 기존 검증 통과 경로까지 불필요하게 흔든다.
- metadata에서 "복구가 필요한 상태"와 "항상 보강하는 상태"가 섞인다.

### Option C: 부족하면 candidate_count를 동적으로 낮춤

사용 가능한 후보가 4개면 `candidate_count=4`처럼 실행 수를 낮춘다.

장점:

- 가장 빠르게 run을 진행할 수 있다.

단점:

- `candidate_count=10` full run 검증 목적을 포기한다.
- WFO/OOS로 넘길 후보 경쟁 폭이 줄어든다.
- 조건식 자동 개선 루프의 핵심 목표인 후보 확장 능력을 검증하지 못한다.

## Recommended Approach

Option A를 선택한다.

퀀트 관점에서는 후보 수를 임의로 낮추면 탐색 폭이 줄어들고, 후보 자동 개선 루프가 실제로 좋은 조건식을 찾을 가능성도 낮아진다. CLI 개발 관점에서는 이미 있는 v5 recovery 생성 경로를 재사용하는 것이 가장 작고 검증 가능한 수정이다. 전체 프로그램 관점에서도 이번 문제는 WFO나 v6/v7이 아니라 Wide v2 MVP 후보 생성 단계의 shortfall이므로, 부족한 direct_v4 후보를 보강하는 것이 맞다.

## Component Design

### `cli/research_iteration_v5_recovery.py`

`build_v5_recovery_candidate_pool()`의 early return 조건을 세분화한다.

현재는 direct_v4 후보가 1개라도 있으면 즉시 반환한다.

```text
if existing_candidates:
    return direct_v4_available
```

변경 후 판단은 다음과 같다.

```text
requested_count = max(int(candidate_count), 0)
existing_count = len(existing_candidates)

if existing_count >= requested_count:
    return direct_v4_available

if existing_count == 0:
    build recovery candidates with reason=v4_candidate_pool_empty

if 0 < existing_count < requested_count:
    keep direct_v4 candidates
    build recovery candidates with reason=direct_v4_shortfall
    combine direct_v4 + recovery candidates
    dedupe with direct_v4 priority
    return combined pool
```

`candidate_count <= 0`은 기존 의미를 유지하기 위해 recovery를 강제로 늘리지 않는다. 이 경우 direct_v4가 있으면 direct 경로를 유지하고, direct_v4가 없으면 기존 빈 v4 recovery 경로의 최소 동작을 따른다.

### Recovery 후보 생성 경로

빈 v4 pool일 때 쓰던 recovery 생성 로직을 함수 안에서 재사용한다.

사용하는 family는 기존과 같다.

```text
recovered_trade_feature
auto_secondary_feature
safe_recommended_fallback
```

`direct_v4_shortfall`에서는 다음 순서를 유지한다.

```text
direct_v4 candidates first
-> recovered_trade_feature
-> auto_secondary_feature
-> safe_recommended_fallback
```

초기 direct_v4 후보는 실제 v4 생성기가 만든 결과이므로 우선 보존한다. recovery 후보는 부족분 보강과 다양성 확보 용도다.

### Dedupe priority

현재 `_dedupe_candidates()`는 `v5_candidate_source` 문자열과 점수를 기준으로 정렬한 뒤 중복 제거한다. direct_v4 후보와 recovery 후보가 같은 expression 또는 signature를 만들면 direct_v4가 항상 살아남는다는 보장이 약하다.

수정 설계는 source priority를 명시한다.

```text
direct_v4 = 0
recovered_trade_feature = 1
auto_secondary_feature = 2
safe_recommended_fallback = 3
unknown = 9
```

중복 제거는 source priority, combined_score, score, expression 순으로 안정적으로 처리한다. direct_v4와 recovery가 같은 후보를 만들면 direct_v4를 남긴다.

중복 key는 source를 제외한 후보 정체성 중심이어야 한다. source를 key에 포함하면 같은 조건식이 family만 다르게 중복 실행될 수 있다.

```text
dedupe_key = expression + candidate_signature
```

### Metadata

`build_v5_recovery_candidate_pool()` 결과에는 다음 metadata를 남긴다.

```text
recovery_attempted: true
recovery_reason: direct_v4_shortfall
initial_v4_candidate_count: <기존 v4 후보 수>
requested_candidate_count: <요청 후보 수>
recovery_needed_count: <요청 수 - 기존 v4 후보 수>
recovery_family_counts:
  direct_v4: <보존된 direct 후보 수>
  recovered_trade_feature: <생성 수>
  auto_secondary_feature: <생성 수>
  safe_recommended_fallback: <생성 수>
final_candidate_pool_count: <dedupe 이후 총 후보 수>
candidate_count: <dedupe 이후 총 후보 수>
```

`research_loop.py`는 이미 `recovery_attempted`, `recovery_reason`, `recovery_family_counts`, `final_candidate_pool_count`, `initial_v4_candidate_count`를 failure metadata로 전달한다. 구현 중 누락이 확인되지 않으면 report 계층 변경은 최소화한다.

### Retention and row-set selection

combined 후보 pool은 `requested_count`로 미리 자르지 않는다.

v5에는 이미 eligible 후보 수에 따라 실행 후보를 oversampling하는 `planned_v5_execution_count()`가 있다. 후보 pool을 일찍 자르면 retention/row-set 단계에서 다양성을 잃는다. 따라서 recovery pool은 넉넉히 만들고, 최종 실행 후보 수는 기존 retention/row-set selection이 결정한다.

## Error Handling

`best_context.expression` 파싱 실패는 기존 invalid seed 또는 parse failure 경로를 유지한다.

recovery를 시도했지만 combined 후보가 여전히 `candidate_count`보다 적을 수 있다. 이 경우 억지로 성공 처리하지 않고 기존 `insufficient_retention_candidates` 경로를 사용한다. 다만 metadata는 반드시 다음 상태를 보여야 한다.

```text
recovery_attempted: true
recovery_reason: direct_v4_shortfall
initial_v4_candidate_count: <기존 후보 수>
final_candidate_pool_count: <보강 후 후보 수>
```

이렇게 남기면 다음 판단이 "direct_v4 shortfall recovery가 안 돌았다"가 아니라 "recovery family 자체가 부족하다"로 정확히 분리된다.

## Tests

### `tests/unit/test_research_iteration_v5_recovery.py`

기존 `test_v5_recovery_keeps_existing_v4_candidates_without_recovery()`는 direct_v4 후보 수가 요청 수를 충족하는 경우로 바꾼다.

추가 테스트:

```text
test_v5_recovery_supplements_direct_v4_shortfall
```

검증:

- existing direct_v4 후보 1개, requested candidate_count 3
- full recommended candidates에 trade feature와 secondary feature 제공
- `recovery_attempted is True`
- `recovery_reason == direct_v4_shortfall`
- `recovery_family_counts.direct_v4 == 1`
- `final_candidate_pool_count >= 3`
- direct_v4 후보가 결과에 보존됨
- recovery source가 함께 포함됨

추가 테스트:

```text
test_v5_recovery_dedupe_prefers_direct_v4
```

검증:

- direct_v4와 recovery 후보가 같은 expression/signature를 만들 때 direct_v4가 남음
- 같은 조건식이 family만 다르게 중복 실행되지 않음

### `tests/unit/test_research_loop.py`

추가 테스트:

```text
test_run_research_iteration_uses_v5_recovery_when_direct_v4_pool_is_short
```

검증:

- fake v4 결과가 requested_count보다 적은 후보를 반환
- v5 recovery가 `direct_v4_shortfall`로 실행됨
- iteration metadata와 top-level failure/success metadata에 recovery 상태가 남음
- selected candidates에 direct_v4와 recovery source가 함께 포함됨

필요하면 shortfall 지속 케이스도 추가한다.

```text
test_run_research_iteration_reports_direct_v4_shortfall_recovery_metadata_when_still_short
```

검증:

- recovery를 시도했지만 후보가 여전히 부족할 때도 원인이 `direct_v4_shortfall`로 기록됨

### Regression command

구현 후 우선 다음을 실행한다.

```powershell
python -m pytest tests/unit/test_research_iteration_v5_recovery.py tests/unit/test_research_loop.py tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py -q
```

그 다음 전체 단위 테스트를 실행한다.

```powershell
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol HEAD
```

## Runtime Verification

단위 테스트가 통과하면 직전 실패 조건을 그대로 다시 검증한다.

```text
candidate_count=10
max_rounds=1
seed_candidate=WideV1Final_B_20260425
period=20250101-20251231
```

성공 기준:

```text
recovery_attempted: true
recovery_reason: direct_v4_shortfall
initial_v4_candidate_count: 4
final_candidate_pool_count >= 10 또는 selected_candidate_count >= 10
leaderboard_count > 0
candidate backtest entered
```

만약 여전히 shortfall이 발생하더라도 다음 조건이면 이번 수정은 올바른 방향으로 본다.

```text
recovery_attempted: true
recovery_reason: direct_v4_shortfall
final_candidate_pool_count > initial_v4_candidate_count
```

그 경우 다음 문제는 direct_v4 shortfall trigger가 아니라 recovery family 확장 또는 retention gate 완화로 분리한다.

## Non-goals

이번 단계에서 하지 않는다.

- v6/v7 단계 신설
- WFO/OOS 검증 실행
- candidate_count 동적 하향
- ranking/scoring 체계 재설계
- PR 생성 또는 `STOM_Version_2U_C` merge
- 대규모 CLI 리팩토링

## Acceptance Criteria

구현 완료 판단 기준은 다음과 같다.

```text
1. direct_v4 후보 수가 requested candidate_count 이상이면 기존처럼 recovery를 생략한다.
2. direct_v4 후보 수가 0개이면 기존 v4_candidate_pool_empty recovery가 유지된다.
3. direct_v4 후보 수가 1개 이상이고 requested candidate_count보다 적으면 recovery가 실행된다.
4. direct_v4_shortfall metadata가 summary/report/failure metadata에 남는다.
5. direct_v4 후보가 recovery 후보보다 dedupe 우선순위를 가진다.
6. candidate_count=10 재실행이 더 이상 "4 candidates selected" 상태로 같은 지점에서 즉시 중단되지 않는다.
```

## Next Step

다음 명령은 구현 계획 작성이다.

```text
$writing-plans Wide v2 v5 direct_v4 shortfall recovery 구현 계획 작성
```
