# Wide v1 v4 row-set diversity 후보 생성 설계

## 1. 목적

이번 설계의 목적은 Wide v1 v3에서 확인된 `rank_metric_tie + all_identical row-set` 문제를 반복하지 않는 v4 후보 생성/선별 흐름을 정의하는 것이다.

v3 결과는 다음 상태로 병합되었다.

```text
decision=HOLD_ROW_SET_EQUIVALENCE
candidate_count=10
row_set_identity_status=all_identical
group_count=1
selected_family=v3_tighten_secondary only
executed_family=v3_tighten_secondary only
next_command=$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계
```

따라서 v4의 1차 목표는 점수 최대화가 아니다. v4의 1차 목표는 같은 wide baseline과 같은 reference score 기준에서 실행 trade set이 서로 다른 후보를 확보하는 것이다.

이번 설계는 v4 후보 생성과 selection rule을 정의한다. 새 backtest 실행, promote, WFO, `strategy.db` 변경은 구현 계획 이후 별도 실행 단계에서 다룬다.

## 2. 현재 근거

PR #24 병합 후 기준 리포트:

```text
docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_tie_break_ranking.md
```

핵심 관찰:

```text
top_10_adjusted_score=13497.662902097409
top_10_trade_count_retention=0.8817451205510907
top_10_row_set_group_count=1
rows_per_candidate=36096
pool_type_counts:
  v3_repair_trade_amount=3
  v3_replace_secondary=15
  v3_tighten_secondary=15
retention_pass_type_counts:
  v3_repair_trade_amount=3
  v3_replace_secondary=15
  v3_tighten_secondary=15
selected_type_counts:
  v3_tighten_secondary=10
executed_type_counts:
  v3_tighten_secondary=10
```

퀀트 해석:

```text
1. v3 top 10은 점수 동률이 아니라 실행 row-set까지 동일하다.
2. tighten 조건은 표현식만 늘렸고 실제 체결 집합을 바꾸지 못했다.
3. repair/replace 후보는 retention pass까지는 도달했지만 selection에서 제외됐다.
4. 현재 selection은 estimated_retention 우선 정렬이라 1.0에 가까운 tighten 후보가 풀을 점유한다.
5. v4는 cosmetic condition 추가를 억제하고, 실행 trade set을 바꿀 가능성이 큰 후보를 강제로 포함해야 한다.
```

## 3. 설계 원칙

```text
1. v4 후보는 점수 후보가 아니라 row-set diversity 후보로 생성한다.
2. 실행 전에는 baseline CSV에 대한 retention mask를 row-set proxy로 사용한다.
3. 같은 proxy row-set을 만드는 후보는 후보군 단계에서 중복으로 본다.
4. selection은 estimated_retention 단일 정렬이 아니라 family quota + proxy row-set diversity를 먼저 본다.
5. 실행 후에는 실제 candidate CSV row-set으로 다시 검증한다.
6. v4 결과가 또 all_identical이면 v4 generation이 실패한 것으로 보고 promote/WFO로 진행하지 않는다.
```

## 4. 접근안 비교

### Approach A: v3 후보 풀만 확대

`candidate_count`와 secondary feature 수를 늘리고 현재 retention-aware selection을 그대로 둔다.

Rejected.

이 방식은 selection 편향을 그대로 유지한다. v3에서 이미 `repair/replace`가 retention pass했는데도 top 10이 tighten으로 몰렸으므로, 후보 풀만 늘리면 같은 구조의 cosmetic tighten 후보가 다시 상위권을 점유할 가능성이 높다.

### Approach B: 실행 후 row-set 분석만 강화

현행 selection으로 후보를 실행한 뒤, 결과 CSV에 대해 row-set equivalence를 분석한다.

Rejected as primary path.

후속 검증으로는 필요하지만, 실행 전에 diversity를 강제하지 않으므로 비용을 사용한 뒤에 같은 row-set이라는 사실만 다시 알게 된다.

### Approach C: 실행 전 proxy diversity + 실행 후 actual row-set 검증

baseline CSV에서 후보 expression을 평가해 예상 제거 mask와 예상 유지 row-set signature를 만들고, selection 단계에서 proxy row-set 다양성과 family quota를 반영한다. 실행 후에는 실제 candidate CSV row-set으로 검증한다.

Recommended.

이 방식은 CLI 비용을 쓰기 전에 같은 row-set 후보를 걸러낼 수 있고, v3에서 제외된 repair/replace family를 의도적으로 포함할 수 있다. 또한 실제 실행 후 검증 리포트를 기존 `cli.research_v3_tiebreak` 계열과 연결할 수 있다.

## 5. 추천 아키텍처

새 helper를 추가한다.

```text
cli/research_iteration_v4.py
```

주요 역할:

```text
1. build_v4_candidate_pool(...)
2. annotate_candidate_rowset_proxy(...)
3. select_rowset_diverse_candidates(...)
4. summarize_v4_generation(...)
```

기존 연결 지점:

```text
cli.research_iteration_v3.build_v3_candidate_pool
cli.research_retention.annotate_candidate_retention
cli.research_retention.estimate_candidate_retention
cli.research_loop.run_research_iteration
cli.research_v3_tiebreak.build_v3_tie_break_analysis
```

CLI mode:

```text
--iteration-v2-mode best_feature_mix_v4
```

기존 옵션 이름은 `iteration_v2_*`로 남아 있으므로 새 전용 옵션명으로 큰 CLI 재구성을 하지 않는다. 이번 단계에서는 choices에 `best_feature_mix_v4`를 추가하는 좁은 변경이 낫다.

## 6. 후보 생성 규칙

v4는 v3의 best context를 그대로 사용한다.

```text
reference_best=WideV1IterationV2_20260423__cand005
best_expression=<primary market-cap condition> and <daily trade-amount condition>
primary_feature=시가총액 계열
trade_amount_feature=당일거래대금 계열
```

후보 family:

```text
v4_control_keep_best:
  기존 best expression을 control metadata로 보존한다.

v4_repair_trade_amount:
  primary condition은 유지하고 trade_amount condition 후보를 교체한다.
  v3에서 retention pass했지만 selection에서 제외된 family이므로 최소 2개를 selection 후보에 남긴다.

v4_replace_secondary:
  primary condition은 유지하고 trade_amount condition 대신 secondary condition을 사용한다.
  trade amount 의존도를 낮춰 row-set이 바뀌는지 확인한다.

v4_tighten_secondary:
  v3와 같은 3조건 tighten 후보지만, proxy row-set이 기존 selected tighten과 같으면 제외한다.

v4_relax_trade_amount:
  기존 trade_amount bound를 넓히거나 인접 quantile 후보로 이동해 retention을 지나치게 높게 유지하지 않는 후보를 만든다.
  목표는 row count retention을 0.80~0.95 범위에서 다양화하는 것이다.
```

기본 pool 생성은 v3 후보 생성 결과를 재사용하되, v4 전용 family metadata와 diversity proxy를 덧붙인다. 완전히 새로운 조건 문법을 만들지 않는다.

## 7. 실행 전 row-set proxy

실행 전 diversity 판정은 baseline CSV의 row index를 사용한다.

```text
proxy_removed_mask = expression을 baseline frame에서 eval한 boolean mask
proxy_kept_signature = frozenset(baseline row index where proxy_removed_mask is False)
proxy_removed_count
proxy_kept_count
proxy_retention = proxy_kept_count / baseline_count
```

현재 `estimate_candidate_retention()`은 estimated retention만 반환한다. v4 구현에서는 동일한 평가 경로를 재사용하되, mask signature까지 돌려주는 작은 helper를 추가한다.

권장 helper:

```text
def estimate_candidate_rowset_proxy(frame, expression) -> dict:
    return {
        "baseline_trade_count": int,
        "proxy_removed_count": int,
        "proxy_kept_count": int,
        "proxy_retention": float,
        "proxy_signature": frozenset[int],
        "evaluation_error": str | None,
    }
```

이 helper는 production report에는 `proxy_signature` 원문을 노출하지 않고, hash와 count만 노출한다.

## 8. Selection rule

v4 selection은 아래 순서로 동작한다.

```text
1. evaluation_error가 있는 후보 제외
2. proxy_retention이 min_estimated_retention보다 낮은 후보 제외
3. proxy_signature가 같은 후보는 같은 proxy group으로 묶음
4. family quota를 먼저 적용
5. 각 family 안에서 proxy group이 다른 후보를 우선 선택
6. 남은 자리는 adjusted proxy score로 채움
```

기본 quota:

```text
candidate_count=10
v4_repair_trade_amount >= 2
v4_replace_secondary >= 2
v4_tighten_secondary <= 4
v4_relax_trade_amount >= 2
```

quota는 hard gate가 아니라 selection target이다. 특정 family가 min retention을 통과한 proxy group을 충분히 만들지 못하면, summary에 shortfall을 기록하고 남은 자리는 다른 proxy group으로 채운다.

정렬 기준:

```text
1. family quota shortfall 우선
2. proxy_signature 신규성
3. proxy_retention이 0.80~0.95 target band에 가까운 후보
4. combined_score
5. estimated_retention
6. original index
```

이 순서는 기존 retention 우선 정렬보다 의도적으로 낮은 retention 후보를 일부 포함한다. 단, min retention 아래로 내려가는 후보는 제외한다.

## 9. 실행 후 검증

v4 실행 후에는 기존 tie-break 분석을 재사용하되 report 명칭을 v4로 분리한다.

권장 후속 script:

```text
scripts/analyze_wide_v1_v4_rowset_diversity.py
```

판정:

```text
PASS_ROW_SET_DIVERSITY:
  actual row_set_group_count >= 2
  best candidate가 단일 row-set tie에 갇히지 않음

HOLD_ROW_SET_EQUIVALENCE:
  actual row_set_identity_status=all_identical

HOLD_SELECTION_DIVERSITY_REVIEW:
  actual row-set은 distinct이지만 selected/executed family가 하나뿐임
```

v4 결과가 `PASS_ROW_SET_DIVERSITY`여야만 promote/WFO 논의를 시작할 수 있다. 다만 PASS는 실전 채택 승인이 아니라 다음 검증 단계 진입 승인이다.

## 10. CLI/리포트 변경

CLI parser:

```text
--iteration-v2-mode choices:
  best_feature_mix
  best_feature_mix_v3
  best_feature_mix_v4
```

Research result에 추가할 항목:

```text
iteration_v4:
  status
  mode
  candidate_count
  type_counts
  proxy_group_count
  proxy_family_group_counts
  quota_summary
  selected_proxy_groups
  skipped_duplicate_proxy_count
```

Report markdown에 추가할 항목:

```text
## Iteration Loop v4 Row-Set Diversity
- mode
- candidate_count
- proxy_group_count
- family quota summary
- selected candidate family distribution
- proxy retention range
- next verification command
```

## 11. 테스트 요구사항

Focused tests:

```text
1. build_v4_candidate_pool이 v4 family metadata를 생성한다.
2. estimate_candidate_rowset_proxy가 같은 mask를 같은 signature로 묶는다.
3. select_rowset_diverse_candidates가 same-signature tighten 후보를 중복 선택하지 않는다.
4. repair/replace/relax family quota가 candidate_count 안에서 반영된다.
5. quota shortfall은 error가 아니라 summary로 기록된다.
6. CLI parser가 best_feature_mix_v4를 허용한다.
7. research_loop가 best_feature_mix_v4일 때 iteration_v4 metadata를 반환한다.
8. report가 iteration_v4 proxy diversity section을 출력한다.
9. v4 실행 후 analysis script가 actual row-set group_count를 보고 next decision을 낸다.
```

Regression tests:

```text
1. best_feature_mix_v3 기존 경로는 변경하지 않는다.
2. 기존 retention-aware selection 기본 동작은 v4 mode 밖에서 변경하지 않는다.
3. candidate_count < 1 validation은 유지한다.
4. v3 tie-break script 결과는 known artifact 기준 HOLD_ROW_SET_EQUIVALENCE를 유지한다.
```

## 12. Out of Scope

```text
- 새 v4 runtime 실행
- promote
- WFO
- strategy.db 직접 변경
- GUI 경로 변경
- serial-key 관련 코드
- 기존 v3 artifact 재작성
```

## 13. Acceptance Criteria

구현 계획은 아래 기준을 만족해야 한다.

```text
1. v4 selection이 estimated_retention 단일 정렬을 사용하지 않는다.
2. selected 후보에 최소 2개 이상의 proxy row-set group이 포함된다.
3. selected 후보 family가 tighten only로 몰리지 않는다.
4. known v3 artifact 분석 결과는 변경되지 않는다.
5. v4 실행 결과 분석 script가 actual row-set group_count를 보고 다음 분기를 결정한다.
6. unit tests, ruff, basedpyright, verify_nonrelease_sync.py, git diff --check가 통과한다.
```

## 14. 추천 다음 명령

이 설계가 맞다면 다음 단계는 구현 계획 작성이다.

```text
$writing-plans Wide v1 v4 row-set diversity 후보 생성 구현 계획 작성
```
