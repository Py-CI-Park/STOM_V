# Wide v1 CLI Baseline GUI Compare 및 Candidate Count 5 PR 보고서

## 1. 이번 PR의 목적

이번 PR은 PR #17 이후 남은 핵심 gate였던 Wide v1 full-year CLI baseline과 GUI 기준 결과 비교를 완료하고, 그 결과를 바탕으로 Retention-Aware 후보 5개 자동 백테스트를 재개한 결과를 문서화한다.

핵심 목적:

```text
1. Wide v1 ResearchTest 조건식의 full-year CLI 결과가 GUI 기준 결과와 일치하는지 확인
2. 일치가 확인된 CLI baseline CSV를 기준으로 candidate_count=5 실행 재개
3. 후보별 Retention-Aware 선별, actual backtest, ranking, cleanup 결과 기록
4. 다음 단계인 후보 결과 분석 및 반복 개선 루프 v2 설계로 넘어갈 근거 확보
```

전체 흐름:

```text
[PR #17: CLI child DB / timeout protocol / tick 설정 키 보강]
        |
        v
[이번 PR: Wide v1 full-year CLI baseline vs GUI 비교]
        |
        v
[이번 PR: candidate_count=5 Retention-Aware 후보 실행]
        |
        v
[다음: 후보 결과 분석 및 반복 개선 루프 v2 설계]
```

## 2. 이번 PR의 변경 사항

### 2.1 Wide v1 CLI baseline GUI compare 설계/계획/결과

추가 문서:

```text
docs/superpowers/specs/2026-04-22-wide-v1-cli-baseline-gui-compare-design.md
docs/superpowers/plans/2026-04-22-wide-v1-cli-baseline-gui-compare.md
docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_cli_baseline_gui_compare.md
docs/update_log/2026-04-22_wide_v1_cli_baseline_gui_compare.md
```

검증한 기준:

```text
buy=ResearchTest_Tick_B_090000_092800_Wide_20260419
sell=ResearchTest_Tick_S_090000_092800_Wide_20260419
start=20250101
end=20251231
timeframe=tick
avg_time=30
betting=20
start_time=090000
end_time=092800
engines=32
```

결과:

```text
preflight_status=ok
cli_status=success
checkpoint_status=success
last_checkpoint=csv_detected
back_count=1638
trade_count=40937
gui_trade_count=40937
decision=PASS
```

### 2.2 Retention-Aware candidate_count=5 실행 재개 설계/계획/결과

추가 문서:

```text
docs/superpowers/specs/2026-04-22-wide-v1-retention-aware-candidate-count-5-resume-design.md
docs/superpowers/plans/2026-04-22-wide-v1-retention-aware-candidate-count-5-resume.md
docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_retention_candidate_count_5.md
docs/update_log/2026-04-22_wide_v1_retention_candidate_count_5.md
```

결과:

```text
status=ok
phase=candidates_evaluated
candidate_count_observed=5
retention_selection.selected_count=5
retention_selection.fallback_count=0
decision=PASS_FOR_EXECUTION
```

Best candidate:

```text
strategy=WideV1RetentionCand5_20260422__cand003
trade_count=36918
trade_count_retention=0.9018247551115128
promotion_passed=True
promotion_score=10943.034141541459
retention_penalty=1.0
adjusted_score=10943.034141541459
```

Cleanup:

```text
loser_candidates_deleted=4
best_candidate_kept=1
cleanup_failed_count=0
remaining_candidate_rows=['WideV1RetentionCand5_20260422__cand003']
```

### 2.3 runtime DB override 안정화

이번 작업 중 feature worktree에서 full-year CLI baseline을 실행하면서 추가 원인을 확인했다.

```text
problem=utility.setting.py가 ./_database/setting.db를 직접 참조해 feature worktree의 빈 DB를 읽음
error=no such table: main
fix=utility.setting도 STOM_CLI_DATABASE_DIR 및 STOM_CLI_DB_* override를 따르게 보강
```

변경 파일:

```text
utility/setting.py
tests/unit/test_setting_base_cli_overrides.py
tests/unit/test_exit_codes.py
tests/unit/test_ui_jisu_cleanup.py
```

운영 정책:

```text
STOM_CLI_DATABASE_DIR는 STOM_V.wt-dev 같은 폴더명에 의미적으로 의존하지 않는다.
항상 실제 운용 _database 폴더를 가리켜야 한다.
운용 폴더명이 바뀌면 env 값만 새 _database 경로로 바꾼다.
```

## 3. 검증 결과

### 3.1 full-year CLI baseline gate

```text
runtime-preflight=ok
CLI full-year baseline=success
back_count=1638
trade_count=40937
GUI trade_count=40937
decision=PASS
```

### 3.2 candidate_count=5 실행

```text
candidate_count_observed=5
best_candidate=WideV1RetentionCand5_20260422__cand003
all_candidates_backtested=True
all_candidates_promotion_passed=True
cleanup_failed_count=0
decision=PASS_FOR_EXECUTION
```

### 3.3 테스트

```text
focused tests:
  python -m pytest tests/unit/test_research_retention.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py tests/unit/test_setting_base_cli_overrides.py -q
  result=158 passed

full unit tests:
  python -m pytest tests/unit/ -q
  result=1053 passed, 1 skipped, 10 warnings

sync guard:
  python scripts/verify_nonrelease_sync.py
  result=PASS

diff check:
  git diff --check
  result=PASS
```

### 3.4 리뷰

```text
final code review:
  Critical/Important issues=0
```

## 4. 전체 개발 단계와 현재 위치

```text
[0. 기준 전략 / 기준 CSV]
        |
        v
[1. CSV 분석]
        |
        v
[2. 후보 expression pool 생성]
        |
        v
[3. Retention-Aware 후보 선별]
        |
        v
[4. CLI/GUI baseline gate]             완료: 이번 PR
        |
        v
[5. 후보 5개 백테스트 / ranking]       완료: 이번 PR
        |
        v
[6. best_candidate 분석]               다음 단계
        |
        v
[7. 반복 개선 루프 v2]
        |
        v
[8. 최종 promote/WFO 검증]
```

## 5. 남은 리스크

- `best_candidate`는 최종 채택이 아니다.
- 이번 PR은 WFO/promote 검증이 아니다.
- row-level CSV parity는 아직 별도 검증으로 남아 있다.
- 후보 표현식의 한글 컬럼명이 일부 CLI JSON에서 mojibake로 보인다.
- 최종 실전 채택 전에는 반복 개선 루프 v2, `discovery promote` 또는 WFO 검증이 필요하다.

## 6. 다음 단계 안내

PR merge 후 다음 superpower 명령:

```text
$brainstorming Wide v1 후보 결과 분석 및 반복 개선 루프 v2 설계
```

다음 설계에서 결정할 내용:

```text
1. best_candidate인 WideV1RetentionCand5_20260422__cand003의 개선 포인트 분석
2. 후보별 trade_count_retention, adjusted_score, 수익/손실 개선 원인 비교
3. 반복 개선 루프 v2에서 어떤 기준으로 조건식을 재생성할지 결정
4. row-level CSV 비교를 이번 v2 전 단계에 포함할지 판단
5. promote/WFO로 넘어가기 전 추가 gate 정의
```

## 7. PR 본문 요약

```markdown
## Summary
- Wide v1 full-year CLI baseline과 GUI 기준 결과를 비교해 back_count=1638, trade_count=40937 일치를 확인했습니다.
- Retention-Aware candidate_count=5 실행을 재개해 후보 5개 모두 full-year backtest/ranking/cleanup까지 완료했습니다.
- feature worktree에서도 실제 운용 _database를 일관되게 보도록 legacy utility.setting DB override와 관련 테스트를 보강했습니다.

## Test Plan
- python -m pytest tests/unit/ -q
- python scripts/verify_nonrelease_sync.py
- git diff --check
- runtime-preflight
- Wide v1 full-year CLI baseline
- discovery research --run-candidates --candidate-count 5

## Remaining Risk
- best_candidate는 최종 채택이 아니며 promote/WFO 검증이 필요합니다.
- row-level CSV parity와 후보 결과 상세 원인 분석은 다음 단계로 남깁니다.
```
