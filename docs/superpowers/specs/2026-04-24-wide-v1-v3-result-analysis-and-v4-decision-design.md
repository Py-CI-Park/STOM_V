# Wide v1 v3 결과 분석 및 v4 여부 판단 설계

## 1. 목적

이 설계의 목적은 PR #22에서 실행한 `WideV1IterationV3_20260423` 결과를 퀀트 관점과 CLI 재현성 관점에서 다시 판정하고, v4 후보 생성 계획으로 넘어갈지 결정하는 기준을 고정하는 것이다.

이번 단계는 최종 전략 채택, promote, WFO 검증이 아니다. 현재 증거는 `status=ok` runtime을 보여주지만, top 10 후보가 모두 같은 reference score로 tie이고 `control_reference_adjusted_score`가 `null`이다. 따라서 이 단계의 핵심은 "v3 후보가 좋아졌는가"가 아니라 "v3 결과를 신뢰 가능한 비교로 해석할 수 있는가"를 확인하는 것이다.

## 2. 현재 증거

기준 흐름:

```text
Wide baseline
  -> Retention-Aware candidate_count=5
  -> cand003 best
  -> Iteration Loop v2: cand003 -> cand005
  -> score_reference_csv 기준 보강
  -> cand005를 새 reference best로 인정
  -> PR #22: best_feature_mix_v3 구현 및 candidate_count=10 실행
  -> 이번 단계: v3 결과 분석 및 v4 여부 판단
```

PR #22 runtime 요약:

```text
status=ok
phase=candidates_evaluated
candidate_count_observed=10
best_candidate=WideV1IterationV3_20260423__cand001
best_reference_adjusted_score=13497.662902097409
best_trade_count=36096.0
best_trade_count_retention=0.8817451205510907
control_candidate=WideV1IterationV2_20260423__cand005
control_reference_adjusted_score=null
derived_decision=PASS_TO_V3_EXECUTION_RESULT_ANALYSIS
```

중요 해석:

```text
- `derived_decision`은 runtime JSON의 원본 필드가 아니라 계획 규칙을 적용한 파생 판단이다.
- `control_reference_adjusted_score=null`이므로 cand001이 cand005를 이겼다는 증거가 아니다.
- top 10 후보가 모두 같은 reference score였으므로 cand001은 "첫 번째 동점 후보"에 가깝다.
- promote/WFO로 바로 이동하면 과최적화와 오판 위험이 크다.
```

## 3. 관점별 판단

### 3.1 퀀트 트레이더 관점

v3 결과는 개선 확정이 아니라 tie 상태로 봐야 한다. reference score가 같다면 다음을 분리해야 한다.

```text
1. 실제 거래 집합이 동일해 같은 점수가 나온 것인지
2. 다른 거래 집합이지만 평가 metric이 같은 점수로 수렴한 것인지
3. ranking 기준이 tie-break 정보를 충분히 반영하지 못한 것인지
```

특히 control score가 비어 있는 상태에서는 cand005 대비 우위를 주장할 수 없다. 따라서 v3 best를 최종 후보로 채택하지 않고, control score 재확인과 top-10 tie 분석을 먼저 수행한다.

### 3.2 CLI 개발 전문가 관점

현재 repository의 실제 discovery research entrypoint는 `python .\stom_backtest.py discovery research ...`이다. `python -m cli.main ...`은 현재 worktree에서 `No module named cli.main`으로 실패한다. 후속 실행 명령과 문서는 실제 동작하는 entrypoint 기준으로 통일해야 한다.

runtime artifact는 `Tee-Object` 영향으로 UTF-16 LE BOM으로 기록되었고, 한국어 expression metadata 일부는 mojibake 상태다. 분석 구현은 artifact 인코딩과 metadata 신뢰도를 명시적으로 다뤄야 한다.

### 3.3 전체 프로그램 관점

이 프로젝트는 `discovery research`를 빠른 후보 생성/비교 루프로 유지하고, 최종 검증은 `discovery promote` 또는 WFO 경로로 분리해 왔다. 따라서 이번 단계는 research loop 내부의 판정 품질을 높이는 단계다. promote/WFO gate 설계는 이후 단계로 미루되, "promote/WFO 금지 조건"은 이번 설계에서 명확히 둔다.

## 4. 분석 데이터 흐름

```text
[wide baseline CSV]
        |
        v
[cand003 CSV / score]
        |
        v
[cand005 CSV / score]
        |
        v
[v3 runtime JSON + v3 candidate CSVs]
        |
        v
[control score 재확인]
        |
        v
[top-10 tie 원인 분석]
        |
        v
[family 편향 분석]
        |
        v
[v3 유지 / v4 설계 / 재검증 보류 판정]
```

입력 데이터:

```text
wide_reference_csv:
  C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv

cand005_csv:
  C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv

v3_runtime_artifact:
  C:\System_Trading\STOM\STOM_V.wt-wide-v3\backtest\temp\wide_v1_iteration_v3_20260423.json
```

## 5. 분석 게이트

### 5.1 Control Score Gate

목표는 cand005 control을 wide baseline 기준으로 non-null score로 재확인하는 것이다.

판정:

```text
PASS:
  cand005 control reference score가 non-null이고 v3 top 후보와 같은 기준으로 비교 가능하다.

FAIL:
  cand005 control reference score가 계속 null이거나 reference CSV/후보 CSV 해석이 실패한다.
```

FAIL이면 v4로 가지 않는다. 결과는 `RECHECK_CONTROL`로 고정한다.

### 5.2 Tie Gate

top 10 후보에 대해 아래 값을 비교한다.

```text
reference_adjusted_score
trade_count
trade_count_retention
date_concentration
symbol_concentration
candidate CSV row-set identity
```

판정:

```text
실질 동률:
  score와 거래 집합 또는 핵심 rank metric이 모두 사실상 동일하다.

랭킹 동률:
  score는 같지만 거래 집합이나 concentration이 다르며 tie-break 기준이 부족하다.

의미 있는 차이:
  score 외 metric이나 row-set 차이가 뚜렷하고 다음 후보 생성 규칙에 반영할 수 있다.
```

실질 동률 또는 랭킹 동률이면 v3 best 채택을 보류한다.

### 5.3 Candidate Family Gate

PR #22 결과에서 실행 top 10은 모두 `v3_tighten_secondary`로 기록됐다. 이 현상이 후보 생성 자체의 편향인지, retention-aware selection의 결과인지 분리해야 한다.

확인 항목:

```text
1. 전체 pool family 분포
2. retention filter 통과 후보 family 분포
3. 최종 실행 top 10 family 분포
4. repair/replace 후보가 selection에서 밀린 이유
5. candidate score와 estimated_retention 정렬 기준의 영향
```

repair/replace 후보가 충분히 생성됐지만 selection에서 거의 실행되지 않았다면, v4는 새 feature를 추가하기보다 selection/ranking 조정 설계가 우선이다.

### 5.4 Quant Validity Gate

reference score만으로 promote/WFO를 허용하지 않는다.

금지 조건:

```text
- control score가 null이다.
- top 후보가 control과 동점이다.
- top 10이 실질 동률이다.
- 거래 집합 차이가 거의 없다.
- 손실 구조가 개선됐다는 row-level 근거가 없다.
```

위 조건 중 하나라도 해당하면 최종 채택 단계로 가지 않는다.

## 6. 최종 판정 상태

이번 분석 설계의 output은 아래 셋 중 하나다.

```text
RECHECK_CONTROL:
  control score null 또는 reference 비교 실패가 남아 있다.
  다음 단계는 control score 재계산/entrypoint/artifact 보강이다.

HOLD_V3_TIE_REVIEW:
  v3 runtime은 성공했지만 top-10 tie, tie-break 부족, family 편향 때문에 채택을 보류한다.
  다음 단계는 v4 설계 전 tie-break/ranking 보강 검토다.

PROCEED_TO_V4_PLAN:
  control 비교가 가능하고, tie 원인이 분석됐으며, v4 후보 생성 또는 selection 조정의 명확한 근거가 있다.
  다음 단계는 v4 구현 계획 작성이다.
```

현재 문서 증거만 기준으로 한 기본 추정은 `HOLD_V3_TIE_REVIEW`다. 단, implementation plan에서는 `Control Score Gate`를 먼저 실행해 `RECHECK_CONTROL` 여부를 확정해야 한다.

## 7. 산출물

구현 계획에서 생성할 문서는 다음 하나를 기본 산출물로 둔다.

```text
docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md
```

문서에 포함할 내용:

```text
1. 사용한 입력 CSV/JSON과 인코딩 처리
2. cand005 control score 재계산 결과
3. v3 top-10 tie 비교표
4. candidate family별 pool/pass/selected/executed 분포
5. row-set 차이 또는 동일성 요약
6. 최종 판정 상태
7. 다음 분기 명령
```

## 8. 비목표

이번 설계에서 제외하는 작업:

```text
- v4 후보 생성 규칙 구현
- v3 후보 재실행
- promote 실행
- WFO 실행
- strategy.db 정리 또는 과거 runtime 산출물 삭제
- backtest/graph 보호 결과 데이터 수정
```

## 9. 다음 분기

분석 결과에 따른 다음 명령은 아래와 같이 고정한다.

```text
RECHECK_CONTROL:
  $brainstorming Wide v1 v3 control score 재검증 설계

HOLD_V3_TIE_REVIEW:
  $brainstorming Wide v1 v3 tie-break 및 ranking 보강 설계

PROCEED_TO_V4_PLAN:
  $writing-plans Wide v1 v4 후보 생성 또는 selection 조정 구현 계획 작성
```

## 10. 성공 기준

이 설계의 성공 기준:

```text
1. cand005 control score null 문제를 판정 상태로 분류한다.
2. v3 top-10 tie가 실질 동률인지 ranking 기준 부족인지 구분한다.
3. repair/replace 후보가 실행 후보에서 밀린 이유를 설명한다.
4. promote/WFO로 가지 말아야 할 조건을 명확히 문서화한다.
5. v4 계획 작성 여부를 증거 기반으로 결정한다.
```
