# Wide v1 v5 actual row-set diversity selection 보강 설계

## 1. 목적

Wide v1 v4는 proxy row-set 기준으로 10개 후보를 잘 분산했지만, 실제 후보 CSV 기준으로는 10개 후보가 9개 actual row-set group으로만 분리됐다. 특히 `WideV1IterationV4_20260424__cand004`와 `WideV1IterationV4_20260424__cand005`가 같은 actual row-set으로 collapse 됐다.

v5의 목적은 proxy diversity를 더 복잡하게 만드는 것이 아니라, 실행된 후보 결과를 actual row-set 기준으로 다시 고르고 최종 후보군을 distinct row-set 대표들로 구성하는 것이다. promote/WFO는 actual row-set이 모두 distinct일 때만 다음 단계로 허용한다.

## 2. 현재 근거

직전 v4 실행 결과:

```text
runtime_name=WideV1IterationV4_20260424
status=ok
phase=candidates_evaluated
candidate_result_count=10
candidate_status_counts={'ok': 10}
best_candidate=WideV1IterationV4_20260424__cand002
cleanup_deleted_count=10
cleanup_kept_count=0
```

proxy selection:

```text
selected_count=10
proxy_group_count=10
skipped_duplicate_proxy_count=0
```

actual row-set result:

```text
row_set_identity_status=partially_distinct
candidate_count=10
group_count=9
decision=HOLD_V4_ROW_SET_REVIEW
next_command=$brainstorming Wide v1 v5 actual row-set diversity selection 보강 설계
```

중복 actual row-set group:

```text
representative=WideV1IterationV4_20260424__cand004
representative_family=v4_tighten_secondary
members=['WideV1IterationV4_20260424__cand004', 'WideV1IterationV4_20260424__cand005']
row_count=36096
```

v4 family 실행 분포:

```text
v4_replace_secondary=5
v4_relax_trade_amount=2
v4_repair_trade_amount=1
v4_tighten_secondary=2
```

해석:

```text
1. family 분산은 개선됐다.
2. proxy row-set group도 10개로 분리됐다.
3. 하지만 actual candidate CSV 기준으로는 1쌍이 같은 체결 집합이다.
4. 따라서 promote/WFO 전 단계에는 actual row-set distinct selection이 필요하다.
```

## 3. 접근 비교

### Approach A: candidate_count 또는 candidate_pool_multiplier만 키우기

후보 생성량을 늘리고 기존 v4 selection을 그대로 둔다.

Rejected.

이 방식은 더 많은 후보를 만들 수 있지만 최종 10개 선택이 여전히 proxy 기준이다. v4에서 proxy group은 이미 10개였는데 actual row-set은 9개였으므로, 후보 수만 늘리는 것은 직접 원인을 해결하지 못한다.

### Approach B: proxy row-set heuristic을 더 엄격하게 만들기

baseline CSV의 mask signature, retention target, family quota를 더 강하게 적용한다.

Rejected as primary path.

proxy는 실행 전 비용을 줄이는 1차 필터로 유용하지만, 실제 backtest 결과 CSV와 완전히 같은 정보가 아니다. proxy 개선은 유지하되 promote/WFO gate를 대신할 수 없다.

### Approach C: proxy로 oversample 실행 후 actual row-set 대표만 선택

v4 candidate pool과 proxy selection을 재사용하되, 요청한 `candidate_count`보다 더 많은 후보를 실행한다. 실행 후 실제 후보 CSV를 actual row-set으로 grouping하고, 각 group의 대표만 최종 후보군에 남긴다.

Recommended.

이 방식은 CLI 비용을 통제하면서도 실제 체결 row-set 중복을 직접 제거한다. v4에서 10개 중 1쌍만 중복이었으므로, v5 pilot은 10개보다 조금 더 많은 후보를 실행하고 actual distinct 대표 10개를 목표로 삼는 것이 타당하다.

## 4. 추천 아키텍처

새 mode를 추가한다.

```text
--iteration-v2-mode best_feature_mix_v5
```

v5는 v4를 대체하지 않고 별도 mode로 둔다. v4 결과와 테스트를 보존하면서, actual row-set distinct selection만 v5에서 검증한다.

주요 코드 경계:

```text
cli/research_iteration_v4.py
  기존 v4 candidate pool, proxy annotation, proxy diverse selection 유지

cli/research_v4_rowset.py
  actual candidate CSV row-set grouping helper 재사용 또는 확장

cli/research_iteration_v5.py
  v5 execution pool sizing, actual row-set representative selection, summary 생성

cli/research_loop.py
  best_feature_mix_v5 mode 연결

cli/subcommands.py
  best_feature_mix_v5 parser choice 추가

cli/research_report.py
  v5 actual row-set selection section 추가

tests/unit/test_research_iteration_v5.py
  v5 selection helper 단위 테스트
```

## 5. 데이터 흐름

v5 runtime 흐름:

```text
1. 기존 분석 CSV에서 candidate expression pool 생성
2. build_v4_candidate_pool로 v4 family 후보 생성
3. annotate_candidate_rowset_proxy로 proxy row-set metadata 부여
4. select_rowset_diverse_candidates로 실행 후보 pool 선택
5. 실행 후보 pool은 candidate_count보다 크게 잡음
6. 선택된 후보를 기존 CLI backtest runner로 실행
7. 실행 결과 CSV를 actual row-set signature로 grouping
8. group마다 최고 ranking candidate를 representative로 선택
9. representative 중 상위 candidate_count개를 final selected candidates로 기록
10. actual row-set group_count가 candidate_count보다 작으면 HOLD 상태로 보고
```

## 6. Execution Pool Size

v5는 실제 실행 후보 수와 최종 후보 수를 분리한다.

```text
requested_candidate_count = config.candidate_count
execution_candidate_count = min(
    eligible_proxy_candidate_count,
    max(requested_candidate_count + 2, requested_candidate_count * 2)
)
```

예시:

```text
candidate_count=10
execution_candidate_count target=20
available v4 eligible candidates=17
actual execution_candidate_count=17
```

이 기본값은 첫 구현에서 새 CLI option 없이 고정한다. 이미 `candidate_pool_multiplier=3`으로 생성 pool을 넓히고 있으므로, v5는 그 pool 안에서 더 많은 후보를 실행해 actual distinct 대표를 확보한다.

향후 runtime 비용이 과하면 별도 option을 추가한다.

```text
--actual-rowset-execution-multiplier
```

첫 구현에서는 이 option을 만들지 않는다.

## 7. Actual Row-Set Representative Selection

대표 선택 helper:

```text
select_actual_rowset_representatives(
    ranked_candidates,
    runtime_root,
    requested_count,
)
```

입력:

```text
ranked_candidates: _rank_candidate_results 이후 결과
runtime_root: relative candidate_csv path 해석용 root
requested_count: 최종 distinct 대표 목표 수
```

출력:

```text
selected_candidates: list[dict]
summary:
  status
  phase
  requested_count
  executed_count
  actual_group_count
  selected_count
  duplicate_actual_rowset_count
  skipped_duplicate_actual_count
  selected_strategy_names
  duplicate_groups
  row_set_identity_status
```

대표 선택 규칙:

```text
1. 기존 rank 순서를 우선한다.
2. 같은 actual row-set signature 안에서는 가장 높은 rank 후보를 representative로 둔다.
3. 이미 사용한 actual row-set signature 후보는 final selected에서 제외한다.
4. final selected가 requested_count보다 작으면 status=shortfall로 기록한다.
5. shortfall은 runtime failure가 아니라 research decision hold 사유다.
```

## 8. Ranking and Best Candidate Contract

기존 `_rank_candidate_results`는 실행된 모든 후보를 rank 한다. v5는 rank 이후 actual row-set representative selection을 적용한다.

계약:

```text
1. candidates에는 실행된 후보 전체를 남긴다.
2. actual_rowset_selection에 final representative 목록을 남긴다.
3. selected_as_best=True는 actual_rowset_selection의 첫 번째 representative에만 부여한다.
4. duplicate actual row-set 후보는 selected_as_best=False로 유지한다.
5. cleanup_best_candidate=True이면 기존처럼 전략 DB 임시 후보는 삭제한다.
```

이 계약을 쓰면 runtime 분석 보고서는 실행 전체와 최종 distinct 선택을 모두 볼 수 있다.

## 9. Decision Gate

v5 decision은 promote/WFO를 직접 실행하지 않고 다음 계획으로만 연결한다.

```text
PROCEED_TO_PROMOTE_WFO_PLAN:
  actual_rowset_selection.status=ok
  actual_rowset_selection.selected_count >= candidate_count
  actual_rowset_selection.row_set_identity_status=all_distinct
  executed known family count >= 2

HOLD_V5_ACTUAL_ROW_SET_SHORTFALL:
  actual row-set group_count < candidate_count

HOLD_V5_RUNTIME_FAILURE:
  candidate execution failed before actual row-set analysis

HOLD_V5_FAMILY_CONCENTRATION_REVIEW:
  actual row-set은 distinct이나 known family가 1개뿐임
```

다음 명령:

```text
PROCEED_TO_PROMOTE_WFO_PLAN -> $writing-plans Wide v1 v5 promote 및 WFO 검증 계획 작성
HOLD_V5_ACTUAL_ROW_SET_SHORTFALL -> $brainstorming Wide v1 v6 actual row-set generation expansion 설계
HOLD_V5_RUNTIME_FAILURE -> $brainstorming Wide v1 v5 runtime failure recovery 설계
HOLD_V5_FAMILY_CONCENTRATION_REVIEW -> $brainstorming Wide v1 v5 family concentration selection 보강 설계
```

## 10. CLI and Report Changes

CLI parser:

```text
--iteration-v2-mode choices:
  best_feature_mix
  best_feature_mix_v3
  best_feature_mix_v4
  best_feature_mix_v5
```

Runtime JSON 추가 field:

```text
iteration_v5:
  status
  mode
  requested_candidate_count
  execution_candidate_count
  source_mode=best_feature_mix_v4
  proxy_selection_summary

actual_rowset_selection:
  status
  phase
  requested_count
  executed_count
  actual_group_count
  selected_count
  row_set_identity_status
  selected_strategy_names
  duplicate_groups
```

Report section:

```text
## Iteration Loop v5 Actual Row-Set Selection
- requested_count
- execution_candidate_count
- actual_group_count
- selected_count
- duplicate_actual_rowset_count
- selected_strategy_names
- next verification command
```

## 11. Testing Requirements

Unit tests:

```text
1. select_actual_rowset_representatives keeps one representative per actual row-set group.
2. representative selection preserves rank order across distinct groups.
3. duplicate actual row-set candidates remain in candidates but are not final selected representatives.
4. shortfall is reported when actual_group_count < requested_count.
5. best_feature_mix_v5 parser choice is accepted.
6. research_loop best_feature_mix_v5 executes more than candidate_count when eligible proxy pool is larger.
7. research_loop best_feature_mix_v5 records actual_rowset_selection.
8. research_report renders iteration_v5 and actual_rowset_selection sections.
9. existing best_feature_mix_v4 tests remain unchanged.
```

Focused verification:

```text
python -m pytest tests/unit/test_research_iteration_v5.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
python -m ruff check cli/research_iteration_v5.py cli/research_loop.py cli/research_report.py cli/subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py
basedpyright cli\research_iteration_v5.py cli\research_loop.py tests\unit\test_research_iteration_v5.py
python scripts\verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol
```

## 12. Out of Scope

```text
- promote 실행
- WFO 실행
- GUI 변경
- serial-key 관련 로직
- backtest/graph 결과물 staging
- 기존 v4 behavior 변경
- 새 외부 dependency 추가
```

## 13. Acceptance Criteria

```text
1. best_feature_mix_v5 mode가 CLI에서 선택 가능하다.
2. v5는 candidate_count보다 큰 execution pool을 실행할 수 있다.
3. final selected best는 actual row-set 대표 후보 중에서만 나온다.
4. actual row-set duplicate 후보는 runtime JSON에 duplicate group으로 기록된다.
5. v4 기존 테스트와 behavior가 유지된다.
6. PR 보고서는 promote/WFO로 갈지 hold할지 actual row-set 기준으로 판단한다.
```

## 14. 추천 다음 명령

```text
$writing-plans Wide v1 v5 actual row-set diversity selection 보강 구현 계획 작성
```
