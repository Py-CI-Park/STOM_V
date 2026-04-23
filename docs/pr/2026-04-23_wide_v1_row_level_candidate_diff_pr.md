# Wide v1 Row-Level 후보 차이 분석 PR 보고서

## 1. 이번 PR의 목적

이번 PR은 PR #19의 `Wide v1 Iteration Loop v2` 실행 결과가 `HOLD`로 끝난 이유를 거래 단위(row-level)로 분석하기 위한 작업입니다.

v2 best 후보 `WideV1IterationV2_20260423__cand005`는 실행에는 성공했지만 기존 best 후보 `WideV1RetentionCand5_20260422__cand003`보다 adjusted_score가 낮았습니다. 따라서 다음 후보 생성으로 바로 넘어가기 전에, v2가 어떤 거래를 유지/제거/추가했는지 확인하는 것이 필요했습니다.

## 2. 전체 개발 흐름과 현재 위치

```text
[0. Wide v1 baseline]
        |
        v
[1. GUI/CLI baseline backtest parity]
        |
        v
[2. Retention-Aware candidate_count=5 실행]
        |
        v
[3. best_candidate=cand003 확인]
        |
        v
[4. Iteration Loop v2 실행]
        |
        v
[5. v2 결과 HOLD]
        |
        v
[6. 이번 PR: row-level 후보 차이 분석]
        |
        v
[7. 다음: row-level key 정합성 보강 또는 v3 후보 생성 규칙]
        |
        v
[8. 최종 promote/WFO 검증]
```

현재 위치는 `[6. row-level 후보 차이 분석]`입니다. 즉, 자동 조건식 연구 루프의 개발 방향은 유지되고 있지만, 이번 결과만으로는 v3 생성 규칙을 확정하기에 근거가 부족해 다음 단계는 key 정합성 보강이 더 적절합니다.

## 3. 이번 PR의 변경 사항

추가/변경 파일:

```text
docs/superpowers/specs/2026-04-23-wide-v1-row-level-candidate-diff-design.md
docs/superpowers/plans/2026-04-23-wide-v1-row-level-candidate-diff.md
cli/research_rowdiff.py
tests/unit/test_research_rowdiff.py
docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_row_level_candidate_diff.md
docs/update_log/2026-04-23_wide_v1_row_level_candidate_diff.md
docs/pr/2026-04-23_wide_v1_row_level_candidate_diff_pr.md
```

구현 내용:

```text
1. cand003 CSV와 v2 cand005 CSV를 로드
2. 거래 key 기반으로 common / left_only / right_only 분리
3. 각 set의 trade_count, avg_return, total_profit 등 요약
4. feature bucket 요약과 top loss/profit row 추출 helper 추가
5. all-winning 구간의 profit_factor=Infinity를 strict JSON 안전값(None)으로 정규화
6. 상수 numeric feature가 qcut에서 사라지지 않도록 constant bucket으로 보존
7. 실제 cand003/v2 cand005 CSV 분석 결과 문서화
```

## 4. 실제 분석 결과

분석 대상:

```text
left=WideV1RetentionCand5_20260422__cand003
right=WideV1IterationV2_20260423__cand005
```

row-level set:

```text
left=36918
right=36096
common=32575
left_only=4343
right_only=3521
```

수익 요약:

```text
left.avg_return=-0.653625331816458
left.total_profit=-4835431554.0
right.avg_return=-0.645012189716312
right.total_profit=-4665122733.0
common.avg_return=-0.6435475057559479
common.total_profit=-4200336872.0
common_avg_return_delta=0.0
common_total_profit_delta=0.0
left_only.avg_return=-0.7292148284595902
left_only.total_profit=-635094682.0
right_only.avg_return=-0.6585629082646975
right_only.total_profit=-464785861.0
```

판정:

```text
decision=HOLD
reason=row-level sets were built but score decline cause is not conclusive
```

해석:

```text
row-level 분리는 성공했습니다.
다만 common 거래의 성능 차이는 0이고, right_only 손실이 left_only보다 명확히 나쁘다는 근거도 부족합니다.
따라서 현재 key와 요약값만으로는 v2 adjusted_score 하락 원인을 충분히 설명하지 못했습니다.
```

## 5. 검증 결과

```text
focused tests:
  python -m pytest tests/unit/test_research_rowdiff.py tests/unit/test_research_compare.py tests/unit/test_research_report.py -q
  result=35 passed

full unit tests:
  python -m pytest tests/unit/ -q
  result=1077 passed, 1 skipped, 10 warnings

ruff:
  python -m ruff check cli/research_rowdiff.py tests/unit/test_research_rowdiff.py
  result=All checks passed

sync guard:
  python scripts/verify_nonrelease_sync.py
  result=PASS

diff check:
  git diff --check
  result=PASS

runtime rowdiff JSON:
  backtest/temp/wide_v1_row_level_candidate_diff_20260423.json
  result=strict JSON allow_nan=False generation PASS
```

실행하지 않은 항목:

```text
GUI 수동 백테스트 재실행
신규 후보 조건식 생성
candidate_count=10 실행
promote/WFO 검증
```

## 6. 남은 리스크

- 현재 trade key는 `종목명/매수시간/매수가` 중심이라, 매도시간/매도가/보유시간/매도조건까지 포함한 더 강한 key 정합성 검토가 필요합니다.
- 이번 row-level 요약만으로는 v2 score 하락 원인이 확정되지 않았습니다.
- `best_candidate`와 `promotion_passed=True`는 최종 전략 채택을 의미하지 않습니다.
- runtime JSON과 backtest CSV는 Git에 커밋하지 않았습니다.
- 컬럼명이 mojibake로 보이는 환경이 있어 feature alias/key 정규화가 다음 분석 품질에 중요합니다.
- 최종 채택 전에는 여전히 `discovery promote` 또는 WFO 검증이 필요합니다.

## 7. 다음 단계 안내

이번 PR merge 후 다음 superpower 명령은 아래가 적절합니다.

```text
$brainstorming Wide v1 row-level key 정합성 보강 설계
```

다음 단계에서 결정할 것:

```text
1. row-level trade key에 포함할 컬럼 확정
2. cand003/v2 cand005의 common 판정이 실제 GUI/CSV 기준과 일치하는지 검증
3. key 보강 후에도 HOLD인지, v3 후보 생성 규칙으로 넘어갈 수 있는지 재판정
4. 필요하면 feature bucket과 top loss/profit drill-down을 더 상세화
```

## 8. PR 본문 요약

```markdown
## Summary
- cand003와 v2 cand005 결과 CSV를 거래 단위로 비교하는 rowdiff helper와 테스트를 추가했습니다.
- common / cand003_only / v2_only set을 분리하고, 각 set의 수익 요약과 feature bucket/top row 분석 근거를 문서화했습니다.
- 실제 분석 결과는 HOLD이며, v2 score 하락 원인은 현재 key/요약만으로 확정되지 않았습니다.

## Test Plan
- python -m pytest tests/unit/test_research_rowdiff.py tests/unit/test_research_compare.py tests/unit/test_research_report.py -q
- python -m pytest tests/unit/ -q
- python -m ruff check cli/research_rowdiff.py tests/unit/test_research_rowdiff.py
- python scripts/verify_nonrelease_sync.py
- git diff --check
- runtime rowdiff JSON strict generation

## Remaining Risk
- row-level key 정합성 보강이 필요합니다.
- 이번 분석만으로는 v2 score 하락 원인이 확정되지 않았습니다.
- WFO/promote는 아직 실행하지 않았습니다.
```
