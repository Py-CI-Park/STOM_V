# Wide v1 v5 실제 행집합 다양성 선택 PR 보고서

## 1. 목적

이번 PR은 Wide v1 v4 실행에서 확인된 실제 후보 CSV row-set 중복 문제를 v5 선택 단계에서 해결하기 위한 구현이다.

v4는 baseline 기반 proxy row-set 다양성으로 후보를 고르지만, 실제 backtest 실행 후 생성되는 후보 CSV에서는 서로 다른 proxy 후보가 같은 체결 행집합으로 collapse될 수 있었다. v5는 이 문제를 줄이기 위해 v4 후보군을 요청 수보다 넓게 실행한 뒤, 실제 후보 CSV row-set 기준으로 대표 후보를 다시 선택한다.

## 2. 전체 방향성 플로우

```text
v3 결과 분석
  -> top 후보 actual row-set 동일성 확인
  -> v4 proxy row-set diversity 후보 생성/선택
  -> v4 candidate_count=10 실제 실행
  -> v4 actual row-set 분석: partially_distinct
  -> 이번 PR: v5 actual row-set 대표 선택 구현
  -> 다음 단계: v5 candidate_count=10 실제 실행 및 분석
  -> all_distinct이면 promote/WFO 계획
  -> shortfall이면 v6 actual row-set generation expansion 설계
```

현재 위치는 `이번 PR: v5 actual row-set 대표 선택 구현` 완료 지점이다. 아직 v5 실거래 후보 10개 runtime 실행 결과는 만들지 않았다.

## 3. 현재 계획과 완료 상태

```text
Task 1. v5 actual row-set helper 추가: 완료
Task 2. research loop에 best_feature_mix_v5 연결: 완료
Task 3. CLI parser와 markdown report에 v5 노출: 완료
Task 4. v5 runtime 분석 스크립트 추가: 완료
Task 5. 전체 검증 및 PR 보고서 작성: 완료
```

커밋 흐름:

```text
57c1fedf Wide v1 v5 실제 행집합 선택 헬퍼를 분리한다
767d99e9 Wide v1 v5 실제 행집합 선택을 연구 루프에 연결한다
915e3e96 Wide v1 v5 CLI와 리포트 노출을 추가한다
01504056 Wide v1 v5 실제 행집합 판정 스크립트를 추가한다
c6b52cf4 Wide v1 v5 신규 파일의 타입 검증 노이즈를 정리한다
```

## 4. 변경 파일

```text
cli/research_iteration_v5.py
cli/research_loop.py
cli/subcommands.py
cli/research_report.py
scripts/analyze_wide_v1_v5_actual_rowset_selection.py
tests/unit/test_research_iteration_v5.py
tests/unit/test_research_loop.py
tests/unit/test_subcommands.py
tests/unit/test_research_report.py
tests/unit/test_wide_v1_v5_analysis.py
docs/pr/2026-04-24_wide_v1_v5_actual_rowset_diversity_selection_pr.md
```

## 5. 구현 요약

- `best_feature_mix_v5` 모드를 추가했다.
- v5는 v4 후보 생성과 proxy row-set selection을 재사용한다.
- v5에서는 최종 요청 수 `candidate_count`보다 넓은 후보 풀을 실행한다.
- 실행 수는 `min(eligible, max(candidate_count + 2, candidate_count * 2))`로 산정한다.
- 실행 완료 후 실제 후보 CSV row-set을 분석해 동일 row-set group당 rank 상위 대표 1개만 남긴다.
- 최종 `best_candidate`는 proxy rank 1이 아니라 `actual_rowset_selection.selected_strategy_names[0]`로 재지정한다.
- report에는 `Iteration Loop v5 Actual Row-Set Selection` 섹션을 추가했다.
- runtime 분석 스크립트는 다음 세 결정을 낸다.
  - `PROCEED_TO_PROMOTE_WFO_PLAN`
  - `HOLD_V5_RUNTIME_FAILURE`
  - `HOLD_V5_ACTUAL_ROW_SET_SHORTFALL`

## 6. 전문가 관점 검토

퀀트 트레이더 관점에서는 이번 단계가 타당하다. v4의 문제는 후보 점수나 family 분산이 아니라 실제 체결 row-set이 중복되는 것이었다. 따라서 promote/WFO 전에 실제 후보 CSV 기준으로 대표성을 다시 확인하는 gate가 필요하다. v5는 후보 생성 자체를 과하게 바꾸지 않고, 실행 후 실제 행집합 선택만 강화하므로 과최적화 위험을 넓히지 않는 보수적 개선이다.

CLI 개발 관점에서도 타당하다. 기존 `discovery research` entrypoint와 `iteration_v2_mode` 옵션 체계를 유지했고, v3/v4 경로를 깨지 않도록 v5 분기를 좁게 추가했다. 사용자는 기존 명령 구조에서 `--iteration-v2-mode best_feature_mix_v5`만 선택하면 된다.

전체 프로그램 관점에서도 적절하다. serial-key 정책, strategy DB promotion, WFO 실행 경로는 건드리지 않았다. `backtest/graph` 보호 데이터와 runtime 산출물을 stage하지 않았고, non-release sync guard도 통과했다.

## 7. 검증 결과

```text
python -m pytest tests/unit/ -q
1172 passed, 1 skipped, 10 warnings
```

경고 10개는 기존 SciPy precision warning과 websockets/binance deprecation warning이다.

```text
python -m ruff check cli\research_iteration_v5.py cli\research_loop.py cli\research_report.py cli\subcommands.py scripts\analyze_wide_v1_v5_actual_rowset_selection.py tests\unit\test_research_iteration_v5.py tests\unit\test_research_loop.py tests\unit\test_research_report.py tests\unit\test_subcommands.py tests\unit\test_wide_v1_v5_analysis.py
All checks passed
```

```text
basedpyright cli\research_iteration_v5.py scripts\analyze_wide_v1_v5_actual_rowset_selection.py tests\unit\test_research_iteration_v5.py tests\unit\test_wide_v1_v5_analysis.py
0 errors, 0 warnings, 0 notes
```

```text
python scripts\verify_nonrelease_sync.py
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

```text
git diff --check --ignore-cr-at-eol
passed
```

참고: `basedpyright cli\research_loop.py`는 기존 대형 untyped dict 부채 때문에 전체 파일 기준으로 통과하지 않는다. 이번 PR에서 해당 파일 전체에 광범위한 suppress를 걸어 숨기지 않았고, 신규 v5 helper/script 범위는 0/0/0으로 맞췄다.

## 8. 남은 리스크

- v5 실제 runtime은 아직 실행하지 않았다. 구현 검증은 unit/integration 성격의 테스트이며, 실제 Wide v1 후보 10개 실행 결과는 다음 단계에서 확인해야 한다.
- v5가 실제 row-set 대표를 고르더라도 distinct 대표 수가 요청 수보다 부족하면 v6 후보 생성 확장이 필요하다.
- `research_loop.py`의 기존 타입 부채는 남아 있다. 이번 변경 범위에서는 기능 회귀를 막는 테스트로 통제했다.

## 9. Merge 판단

현재 변경은 merge 가능한 상태로 판단한다.

근거:

```text
- 전체 unit test 통과
- 변경 파일 ruff 통과
- 신규 v5 파일 basedpyright 0/0/0
- non-release sync guard 통과
- whitespace check 통과
- v3/v4 회귀 테스트 포함
- serial-key, WFO, strategy promotion 경로 비변경
```

이 워크트리는 이미 `STOM_Version_2U_C` 활성 baseline 브랜치에서 작업 중이므로, 별도 feature branch를 base branch로 병합하는 단계는 없다. PR 보고서와 커밋을 현재 baseline에 고정하는 방식으로 처리한다.

## 10. 다음 단계 추천

다음 단계는 v5 구현을 실제 Wide v1 runtime으로 검증하는 계획 작성이다.

```text
$writing-plans Wide v1 v5 candidate_count=10 실제 실행 및 actual row-set 검증 계획 작성
```

그 실행 결과에서 `actual_rowset_selection.status=ok`, `row_set_identity_status=all_distinct`, `selected_count >= requested_count`가 확인되면 그때 promote/WFO 계획으로 넘어가는 것이 맞다.
