# Wide v1 v4 row-set diversity 후보 생성 PR 보고서

## 1. 이번 PR의 목적

이번 PR은 Wide v1 v3 결과에서 top 후보들이 점수상으로는 여러 개처럼 보였지만 실제 실행 row-set은 모두 동일했던 문제를 반복하지 않기 위해 `best_feature_mix_v4` 후보 생성과 검증 표면을 추가한다.

핵심 목표는 다음과 같다.

```text
1. v4 후보를 family별로 생성한다.
2. 실행 전 baseline CSV 기준 proxy row-set 다양성을 계산한다.
3. proxy row-set이 중복되는 후보를 selection 단계에서 제거한다.
4. CLI research loop에서 best_feature_mix_v4를 실행할 수 있게 연결한다.
5. report와 wrapper script로 v4 실행 후 실제 row-set 검증을 준비한다.
```

이번 PR은 실제 v4 backtest 실행, promote, WFO, `strategy.db` 변경을 수행하지 않는다. 구현 범위는 후보 생성/선택 규칙, CLI 연결, 보고서 노출, 실제 실행 후 분석 wrapper까지다.

## 2. 전체 방향성 플로우

```text
[v3 결과 분석]
        |
        v
[v3 top 후보 actual row-set 동일 확인]
        |
        v
[이번 PR: v4 proxy row-set diversity 후보 생성 구현]
        |
        v
[다음 단계: v4 candidate_count=10 실행 계획 작성]
        |
        v
[v4 runtime 실행]
        |
        v
[v4 actual row-set diversity 분석]
        |
        v
[promote / WFO 판단]
```

현재 위치는 `[이번 PR: v4 proxy row-set diversity 후보 생성 구현]` 완료 지점이다.

## 3. 현재 계획과 완료 상태

```text
Task 1. v4 pure helper와 proxy selection 추가: 완료
Task 2. best_feature_mix_v4 CLI/research loop 연결: 완료
Task 3. iteration_v4 report section 추가: 완료
Task 4. v4 actual row-set 분석 wrapper 추가: 완료
Task 5. 최종 검증과 PR 보고서 작성: 완료
```

커밋 흐름:

```text
bcbd8acf Wide v1 v4 행집합 다양성 helper를 추가한다
198cd735 Wide v1 v4 helper 리뷰 지적을 반영한다
88bc12cc Wide v1 v4 proxy 선택 계약을 계획과 맞춘다
116918e4 Wide v1 v4 원본 순서 tie-break를 살린다
e991b3e9 Wide v1 v4 후보 선택 경로를 CLI 연구 루프에 연결한다
46669fe0 Wide v1 v4 행집합 다양성 리포트 섹션을 추가한다
fc27055f Wide v1 v4 실제 행집합 검증 스크립트를 추가한다
```

## 4. 변경 사항

```text
cli/research_iteration_v4.py
tests/unit/test_research_iteration_v4.py
cli/research_loop.py
cli/subcommands.py
tests/unit/test_research_loop.py
tests/unit/test_subcommands.py
cli/research_report.py
tests/unit/test_research_report.py
scripts/analyze_wide_v1_v4_rowset_diversity.py
tests/unit/test_research_v3_tiebreak.py
docs/pr/2026-04-24_wide_v1_v4_row_set_diversity_candidate_generation_pr.md
```

구현 요약:

```text
- best_feature_mix_v4 후보 family:
  - v4_control_keep_best
  - v4_tighten_secondary
  - v4_replace_secondary
  - v4_repair_trade_amount
  - v4_relax_trade_amount

- proxy row-set selection:
  - baseline CSV에서 후보 expression이 제거할 행을 평가한다.
  - 남는 행 위치를 proxy signature로 만든다.
  - 동일 proxy signature 후보는 중복 그룹으로 보고 하나만 선택한다.
  - family quota와 target retention distance를 selection에 반영한다.

- CLI 연결:
  - `--iteration-v2-mode best_feature_mix_v4`를 허용한다.
  - v4 mode에서만 row-set proxy selector를 사용한다.
  - v3 mode는 기존 retention-aware selection을 유지한다.

- 보고서:
  - `Iteration Loop v4 Row-Set Diversity` 섹션을 추가했다.
  - family count, proxy group count, duplicate skip count, quota summary를 노출한다.

- 실제 실행 후 분석:
  - `scripts/analyze_wide_v1_v4_rowset_diversity.py`를 추가했다.
  - v4 runtime path/root를 명시 입력으로 받아 actual row-set 분석 보고서를 생성한다.
```

## 5. 검증 결과

Focused tests:

```text
python -m pytest tests/unit/test_research_iteration_v4.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py tests/unit/test_research_v3_tiebreak.py -q
result=189 passed
```

Full unit tests:

```text
python -m pytest tests/unit/ -q
result=1158 passed, 1 skipped, 10 warnings
```

Lint:

```text
python -m ruff check cli/research_iteration_v4.py cli/research_loop.py cli/subcommands.py cli/research_report.py scripts/analyze_wide_v1_v4_rowset_diversity.py tests/unit/test_research_iteration_v4.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py tests/unit/test_research_v3_tiebreak.py
result=All checks passed
```

Type diagnostics:

```text
basedpyright cli\research_iteration_v4.py scripts\analyze_wide_v1_v4_rowset_diversity.py tests\unit\test_research_iteration_v4.py
result=0 errors, 0 warnings, 0 notes
```

Non-release sync guard:

```text
python scripts\verify_nonrelease_sync.py
result=모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

Whitespace:

```text
git diff --check
result=pass
```

v3 row-set regression:

```text
python scripts\analyze_wide_v1_v3_tie_break.py
result=decision=HOLD_ROW_SET_EQUIVALENCE
```

```text
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v3_tie_break_ranking.md -Pattern 'decision=|row_set_identity_status|group_count'
result:
decision=HOLD_ROW_SET_EQUIVALENCE
row_set_identity_status=all_identical
group_count=1
```

참고: 전체 unit test warning 10개는 기존 SciPy precision warning과 websockets/binance deprecation warning이다.

## 6. 전문가 관점 검토

퀀트 트레이더 관점:

```text
- v3 top 후보가 같은 actual row-set으로 접힌 문제를 직접 겨냥한다.
- 단순 점수 순위 대신 후보가 실제로 다른 거래 집합을 만들 가능성을 selection 전에 제어한다.
- proxy row-set은 예측치이므로 promote/WFO 전에 actual row-set 분석을 별도 gate로 둔 점이 타당하다.
```

CLI 개발 관점:

```text
- 기존 iteration_v2_* 옵션군을 재사용해 사용 표면을 넓히지 않았다.
- parser, handler payload, research loop metadata, markdown report가 같은 mode 이름을 사용한다.
- v4 actual 분석 script는 runtime path/root를 required로 받아 잘못된 기본 artifact 사용을 피한다.
```

전체 프로그램 관점:

```text
- v2/v3 경로는 회귀 테스트로 보호했다.
- strategy.db, promote, WFO, serial-key 정책을 건드리지 않았다.
- nonrelease sync guard가 통과했다.
- 보호 대상 backtest/graph 결과물은 staging하지 않았다.
```

## 7. 남은 리스크

```text
1. proxy row-set diversity는 baseline CSV 기반 사전 추정이다. 실제 v4 backtest 후 actual candidate CSV로 다시 검증해야 한다.
2. v4 candidate_count=10 실행은 아직 하지 않았다.
3. promote/WFO 판단은 actual row-set diversity 분석 이후로 미뤄야 한다.
4. basedpyright 전체 파일군은 기존 타입 부채가 남아 있어 clean pass 대상이 아니다. 이번 PR에서는 새 helper와 새 script 중심으로 0/0/0을 확인했다.
```

## 8. PR 판단

이번 변경은 merge 가능한 상태다.

근거:

```text
- v4 후보 생성/선택 규칙이 단위 테스트로 보호된다.
- CLI research loop에서 v4 mode가 실행 가능하다.
- v3 retention selection 회귀가 테스트로 보호된다.
- 보고서와 wrapper script로 다음 실행/분석 단계가 연결된다.
- 전체 unit test, lint, sync guard, whitespace check가 통과했다.
```

## 9. 다음 단계

다음 단계는 실제 v4 실행 계획을 별도로 작성하는 것이다.

```text
$writing-plans Wide v1 v4 candidate_count=10 실행 및 actual row-set diversity 분석 계획 작성
```
