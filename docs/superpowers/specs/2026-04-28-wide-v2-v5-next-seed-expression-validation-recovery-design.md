# Wide v2 v5 next seed expression validation recovery design

## Purpose

이 설계는 Wide v2 v5 recovery smoke 이후 남은 병목인 `invalid_seed_expression` 중단을 해결한다.

현재 v5 후보 풀 recovery는 성공했다. `candidate_count=2` smoke의 round001은 `initial_v4_candidate_count=0`에서 recovery 후보 14개를 만들고 후보 backtest 4개와 leaderboard 4개를 생성했다. 그러나 round001 best candidate가 `시가총액 + 당일거래대금` 조건식으로 선택되면서 round002 seed 검증이 실패했다. optimizer 설정의 v5 `iteration_v2_trade_amount_feature`는 `B_등락율`이므로, 다음 seed는 `시가총액 + 등락율` 구조여야 한다.

목표는 global best 후보를 버리는 것이 아니다. global best는 WFO/OOS handoff 후보로 보존하되, 다음 round seed는 v5 후보 생성기가 안정적으로 해석할 수 있는 seed-compatible 후보를 선택한다.

## Current MVP Position

```text
v5 후보 풀 0개 문제
-> recovery 구현 완료
-> candidate_count=2 smoke 실행 완료
-> 후보 backtest 진입 성공
-> round002 seed 검증 실패 발견
-> next seed selection recovery 필요
```

이 설계 이후 남은 MVP 단계는 다음과 같다.

```text
1. next seed expression validation recovery 구현
2. candidate_count=2 smoke 재실행
3. candidate_count=10 full run
4. winner WFO/OOS handoff 계획 또는 검증
5. PR 보고서 작성 및 merge 판단
```

## Problem

현재 optimizer의 다음 seed 선택은 단순하다.

```text
round_result.best_candidate
-> strategy_name, expression 추출
-> _validate_seed_expression(config, expression)
-> 실패하면 optimizer 전체 중단
```

이 방식은 다음 상황에서 약하다.

```text
round best candidate = 수익성 기준 최고 후보
next round seed = v5 candidate generator가 해석할 수 있는 2조건 seed
```

두 역할이 같지 않을 수 있다. recovery 후보 family는 `등락율`, `당일거래대금`, `체결강도` 같은 여러 feature를 후보로 만들 수 있다. 이 중 `당일거래대금` 후보가 수익성 점수 1위가 될 수 있지만, optimizer 설정이 `B_등락율`을 trade amount feature로 유지하는 동안에는 다음 round seed로 사용할 수 없다.

따라서 “수익성 best”와 “다음 round seed”를 분리해야 한다.

## Design Alternatives

### Option A: Seed-compatible fallback selection

round best가 seed validation을 통과하면 그대로 다음 seed로 사용한다. 실패하면 같은 round의 ranked candidates를 순서대로 스캔해 `_validate_seed_expression()`을 통과하는 첫 후보를 다음 seed로 사용한다.

장점:

- 현재 optimizer 설정의 feature 축을 유지한다.
- full run 전에 필요한 최소 수정이다.
- global best와 next seed 역할을 분리할 수 있다.
- WFO 후보는 여전히 점수 기준 global best로 유지된다.

단점:

- round best와 next seed가 다를 수 있어 report에 명확한 설명이 필요하다.

### Option B: Winner expression에 맞춰 trade_amount_feature 자동 갱신

round best expression의 두 번째 feature를 감지해 다음 round config의 `iteration_v2_trade_amount_feature`를 바꾼다.

장점:

- round best를 항상 다음 seed로 사용할 수 있다.

단점:

- round마다 feature 축이 바뀌어 후보 생성 규칙과 비교 기준이 흔들린다.
- 조건식 자동 개선 루프가 탐색 공간을 급격히 넓힐 수 있다.
- v5의 “기준 seed 주변 개선”이라는 목적이 약해진다.

### Option C: v5 recovery 후보 생성에서 seed-incompatible family를 아예 제외

`primary_feature + configured trade_amount_feature`를 유지하지 않는 후보를 만들지 않는다.

장점:

- 다음 seed 문제는 사전에 차단된다.

단점:

- recovery의 후보 다양성이 줄어든다.
- smoke에서 실제 수익성 좋은 후보를 WFO 후보로 발견할 기회가 줄어든다.
- 이번 문제는 후보 생성 자체보다 다음 seed 선택 문제이므로 과도하게 좁힌다.

## Recommended Approach

Option A를 선택한다.

퀀트 관점에서 조건식 개선 루프는 비교 가능한 seed 축을 유지해야 한다. 다음 round seed가 매번 다른 feature 축으로 바뀌면 개선인지 탐색 방향 변경인지 구분하기 어렵다. CLI 관점에서도 Option A는 `research_optimizer.py` 안의 seed 선택 책임만 보강하면 되므로 변경 범위가 작고 검증이 명확하다.

핵심 정책은 다음과 같다.

```text
global_best_candidate = 수익성/품질 기준 최고 후보
next_round_seed = v5 seed validation을 통과하는 최고 순위 후보
```

두 값은 같을 수도 있고 다를 수도 있다.

## Proposed Flow

```text
round N 실행
-> 후보 backtest 완료
-> ranked candidates 생성
-> global leaderboard 갱신
-> final/global best 후보 유지
-> 다음 round 필요 여부 판단
-> seed-compatible next seed 선택
   -> round best expression이 유효하면 round best 사용
   -> 아니면 ranked candidates에서 유효한 첫 후보 사용
   -> 없으면 invalid_seed_expression으로 중단
-> round N+1 실행
```

smoke에서 기대되는 변화는 다음과 같다.

```text
round001 global best = cand003, 시가총액 + 당일거래대금
round001 next seed = cand001, 시가총액 + 등락율
round002 시작 가능
```

## Component Design

### `cli/research_optimizer.py`

새 helper를 추가한다.

```text
_candidate_seed_tuple(candidate, fallback_candidate)
```

역할:

- candidate dict에서 `strategy_name`, `expression`을 추출한다.
- 비어 있으면 `None`을 반환한다.

새 helper를 추가한다.

```text
_seed_from_ranked_candidates(config, round_result, fallback_candidate)
```

역할:

- `best_candidate`를 먼저 검사한다.
- best candidate expression이 `_validate_seed_expression()`을 통과하면 그대로 반환한다.
- 실패하면 `round_result['candidates']`를 rank 순서로 정렬해 seed-compatible 후보를 찾는다.
- 성공 시 다음 값을 반환한다.

```text
strategy_name
expression
selection_status
rejected_best_strategy_name
rejected_best_expression
rejected_best_reason
```

`selection_status` 값은 다음 중 하나다.

```text
round_best
compatible_fallback
not_found
```

기존 `_seed_from_previous()`는 유지하지 않거나 새 helper의 얇은 wrapper로 축소한다.

### Optimizer result metadata

round state에 다음 metadata를 남긴다.

```text
next_seed_strategy_name
next_seed_expression
next_seed_selection_status
rejected_round_best_seed_strategy_name
rejected_round_best_seed_expression
rejected_round_best_seed_reason
```

최상위 result에는 마지막 seed 선택 상태를 남긴다.

```text
next_seed_selection_status
next_seed_strategy_name
next_seed_expression
```

실패 시에는 기존 `invalid_seed_expression`에 다음 metadata를 추가한다.

```text
failed_round
failure_phase=invalid_seed_expression
failure_message
next_seed_selection_status=not_found
rejected_round_best_seed_expression
```

### `cli/research_optimizer_report.py`

Markdown report의 round summary 또는 Stop reason 주변에 next seed selection 정보를 노출한다.

필수 표시 항목:

```text
next_seed_selection_status
next_seed_strategy_name
next_seed_expression
rejected_round_best_seed_reason
```

이 섹션은 full run 중단 원인을 바로 볼 수 있게 만드는 관찰성 보강이다.

## Error Handling

다음 seed 후보가 없으면 기존처럼 `status=error`, `stop_reason=invalid_seed_expression`으로 중단한다. 단, 이번에는 왜 실패했는지 구조화해서 남긴다.

```text
round best seed invalid
fallback candidates scanned
no compatible candidate found
```

이는 silent fallback보다 안전하다. v5 기준 feature 축을 유지할 후보가 하나도 없다면 full run을 계속하는 것이 아니라 후보 생성 정책을 다시 봐야 한다.

## Test Strategy

### Unit tests

`tests/unit/test_research_optimizer.py`

1. round best가 seed-compatible이면 기존처럼 round best를 다음 seed로 사용한다.
2. round best가 seed-incompatible이고 ranked candidates에 compatible 후보가 있으면 fallback 후보로 다음 round를 실행한다.
3. compatible 후보가 없으면 `invalid_seed_expression`으로 중단하고 `next_seed_selection_status=not_found`를 남긴다.
4. fallback이 발생해도 `final_best_candidate`는 점수 기준 global best를 유지한다.

`tests/unit/test_research_optimizer_report.py`

1. Markdown report가 next seed selection metadata를 표시한다.
2. pipe/newline escaping은 기존 report 규칙을 따른다.

### Smoke verification

구현 후 같은 smoke를 재실행한다.

```text
candidate_count=2
max_rounds=2
seed_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 4.83
iteration_v2_trade_amount_feature=B_등락율
```

성공 기준:

```text
round001 recovery 후보 backtest 진입
round002 시작 또는 완료
stop_reason이 invalid_seed_expression이 아님
leaderboard_count >= 4
next_seed_selection_status가 round_best 또는 compatible_fallback
```

## Out of Scope

이 설계에서는 다음을 하지 않는다.

```text
WFO/OOS 검증 구현
candidate_count=10 full run 실행
Wide v6/v7 추가
v5 recovery 후보 family 추가
trade_amount_feature 자동 변경
CLI 전체 리팩토링
```

## Risks

1. fallback seed가 global best보다 수익성이 낮을 수 있다.
   - 의도된 trade-off다. 다음 round seed는 탐색 안정성을 위한 값이고, WFO 후보는 global best로 유지한다.

2. fallback seed 선택 기준이 rank 순서에 의존한다.
   - 현재 optimizer가 이미 rank를 후보 품질 순서로 사용하므로 동일 기준을 재사용한다.

3. report에 표시하지 않으면 사용자가 왜 best가 아닌 후보로 다음 round가 시작됐는지 이해하기 어렵다.
   - next seed selection metadata를 report에 반드시 노출한다.

## Acceptance Criteria

```text
1. 기존 optimizer 성공 테스트가 유지된다.
2. seed-incompatible round best가 있어도 compatible fallback 후보가 있으면 다음 round가 시작된다.
3. fallback이 발생해도 final_best_candidate는 global leaderboard 기준 best를 유지한다.
4. fallback 후보가 없으면 invalid_seed_expression으로 명확하게 중단한다.
5. summary JSON과 Markdown report에 next seed selection metadata가 남는다.
6. candidate_count=2 smoke에서 기존 round002 invalid_seed_expression 중단이 재현되지 않는다.
```

## Next Command

설계 승인 후 구현 계획은 다음 명령으로 작성한다.

```text
$writing-plans Wide v2 v5 next seed expression validation recovery 구현 계획 작성
```
