# Wide v1 v3 tie-break 및 row-set ranking 보강 PR 보고서

## 1. 이번 PR의 목적

이번 PR의 목적은 PR #23에서 `row_set_identity_status=not_evaluated`로 남아 있던 Wide v1 v3 top 후보 동률 문제를 실제 후보 CSV row-set 기준으로 재검증하고, 다음 연구 분기를 안전하게 결정하는 것이다.

핵심 목적:

```text
1. v3 top 후보들의 실행 row-set이 같은지 재현 가능하게 비교
2. row-set이 같은 후보를 equivalence class로 묶기
3. 성능으로 구분할 수 없는 후보는 deterministic representative rule로 대표 후보 기록
4. selection/execution family 쏠림을 함께 기록
5. 다음 superpower 명령을 리포트에 명시
```

이번 PR은 v4 후보 생성, promote, WFO, 신규 백테스트 실행, `strategy.db` 변경을 수행하지 않는다. 목적은 "cand001이 정말 고유한 승자인가"를 확인하고, 아니라면 다음 설계 방향을 row-set diversity 쪽으로 고정하는 것이다.

## 2. 전체 개발 플로우와 현재 위치

```text
[0. Wide baseline CSV]
        |
        v
[1. Retention-Aware candidate_count=5]
        |
        v
[2. best_candidate=cand003]
        |
        v
[3. Iteration Loop v2: cand003 -> cand005]
        |
        v
[4. score baseline comparability 보강]
        |
        v
[5. v3 후보 생성 규칙 구현 + candidate_count=10 실행]
        |
        v
[6. v3 결과 분석 및 v4 여부 판단]
        |
        v
[7. 이번 PR: v3 tie-break 및 row-set ranking 보강]
        |
        v
[8. 다음: v4 row-set diversity 후보 생성 설계]
        |
        v
[9. 이후: v4 구현, 실행, promote/WFO 판단]
```

현재 위치는 `[7. v3 tie-break 및 row-set ranking 보강]`이다.

PR #23의 판단은 아래 상태에서 멈췄다.

```text
decision=HOLD_V3_TIE_REVIEW
tie_status=rank_metric_tie
tie_candidate_count=10
row_set_identity_status=not_evaluated
selected_family=v3_tighten_secondary only
```

이번 PR은 이 미평가 영역을 닫았다. 알려진 PR #22 runtime artifact 기준 top 10 후보는 모두 같은 실행 row-set을 만들었고, 따라서 top rank는 고유한 quant 승자가 아니라 동일 실행 결과를 만든 표현식 묶음으로 해석해야 한다.

## 3. 현재 계획

현재 완료된 계획:

```text
1. row-set equivalence helper 추가
2. 단일 후보를 tie-break로 오판하지 않도록 회귀 테스트 추가
3. 실제 PR #22 artifact를 읽는 분석 script 추가
4. row-set tie-break markdown pilot log 생성
5. --top-n 0 / 음수 입력을 CLI에서 조기 차단
6. spec review, code quality review, focused verification 통과
```

현재 판단:

```text
decision=HOLD_ROW_SET_EQUIVALENCE
row_set_identity_status=all_identical
group_count=1
candidate_count=10
row_count=36096
selected_family=v3_tighten_secondary only
executed_family=v3_tighten_secondary only
next_command=$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계
```

다음 계획:

```text
1. v4 후보 생성으로 바로 들어가지 않는다.
2. 먼저 row-set diversity를 목표로 하는 v4 후보 생성 설계를 한다.
3. v4 설계에서는 cosmetic 조건 추가가 아니라 실행 trade set을 바꾸는 후보를 우선한다.
4. repair/replace family가 retention pass 후 selection에서 밀린 원인을 v4 selection rule에 반영할지 검토한다.
5. promote/WFO는 v4 실행 결과가 나온 뒤 별도 gate에서 판단한다.
```

## 4. 이번 PR의 변경 사항

변경 파일:

```text
cli/research_v3_tiebreak.py
scripts/analyze_wide_v1_v3_tie_break.py
tests/unit/test_research_v3_tiebreak.py
docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_tie_break_ranking.md
docs/pr/2026-04-24_wide_v1_v3_tie_break_ranking_pr.md
```

구현 내용:

```text
1. Row-set equivalence helper
   - candidate_csv 경로를 runtime root 기준으로 해석
   - 기존 공개 trade-key 경로를 사용해 실행 row-set signature 생성
   - 후보들을 row-set equivalence group으로 묶음
   - missing CSV는 error status로 보고

2. Representative rule
   - 조건 수가 적은 후보 우선
   - family priority 적용
   - expression 길이, rank, index 순으로 tie-break
   - 성능이 같은 row-set에서는 더 단순하고 낮은 위험의 표현식을 대표로 기록

3. Decision routing
   - error / all_identical / partially_distinct -> HOLD_ROW_SET_EQUIVALENCE
   - all_distinct이지만 selected/executed family가 하나뿐이면 HOLD_SELECTION_DIVERSITY_REVIEW
   - distinct row-set이고 family diversity도 있으면 PROCEED_TO_V4_PLAN

4. CLI wrapper
   - `scripts/analyze_wide_v1_v3_tie_break.py` 추가
   - 기본 입력을 PR #22 runtime artifact로 설정
   - `--runtime-path`, `--runtime-root`, `--output`, `--top-n` 지원
   - `--top-n`은 양수만 허용

5. 실제 pilot log
   - known v3 artifact 기반 markdown report 생성
   - top 10 후보가 하나의 row-set equivalence class임을 기록
```

## 5. 실제 분석 결과

입력:

```text
runtime_path=C:\System_Trading\STOM\STOM_V.wt-wide-v3\backtest\temp\wide_v1_iteration_v3_20260423.json
runtime_root=C:\System_Trading\STOM\STOM_V.wt-wide-v3
top_n=10
```

결과:

```text
decision=HOLD_ROW_SET_EQUIVALENCE
next_command=$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계
candidate_count=10
row_set_identity_status=all_identical
group_count=1
row_count=36096
```

대표 후보:

```text
representative=WideV1IterationV3_20260423__cand004
representative_family=v3_tighten_secondary
```

row-set group:

```text
members:
  WideV1IterationV3_20260423__cand001
  WideV1IterationV3_20260423__cand002
  WideV1IterationV3_20260423__cand003
  WideV1IterationV3_20260423__cand004
  WideV1IterationV3_20260423__cand005
  WideV1IterationV3_20260423__cand006
  WideV1IterationV3_20260423__cand007
  WideV1IterationV3_20260423__cand008
  WideV1IterationV3_20260423__cand009
  WideV1IterationV3_20260423__cand010
```

Family diagnostics:

```text
pool:
  v3_repair_trade_amount=3
  v3_replace_secondary=15
  v3_tighten_secondary=15
  v3_control_keep_best=1

retention_pass:
  v3_repair_trade_amount=3
  v3_replace_secondary=15
  v3_tighten_secondary=15

selected/executed:
  v3_tighten_secondary=10
```

퀀트 해석:

```text
- top 10 v3 후보는 점수만 같은 것이 아니라 실행 row-set도 같다.
- cand001은 고유한 quant winner가 아니다.
- 추가 tighten 조건들은 실제 체결 row-set을 바꾸지 못했다.
- v4는 같은 패턴의 조건을 더 붙이는 방향보다 row-set diversity를 직접 목표로 해야 한다.
```

## 6. 검증 결과

Focused verification:

```text
python -m pytest tests/unit/test_research_v3_tiebreak.py tests/unit/test_research_v3_decision.py tests/unit/test_research_compare.py -q
result=51 passed
```

Lint:

```text
python -m ruff check cli/research_v3_tiebreak.py scripts/analyze_wide_v1_v3_tie_break.py tests/unit/test_research_v3_tiebreak.py
result=All checks passed
```

Type diagnostics:

```text
basedpyright cli\research_v3_tiebreak.py scripts\analyze_wide_v1_v3_tie_break.py tests\unit\test_research_v3_tiebreak.py
result=0 errors, 0 warnings, 0 notes
```

Sync guard:

```text
python scripts/verify_nonrelease_sync.py
result=모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

Whitespace:

```text
git diff --check
result=pass
```

Script:

```text
python scripts/analyze_wide_v1_v3_tie_break.py
result=decision=HOLD_ROW_SET_EQUIVALENCE
```

Invalid input guard:

```text
python scripts/analyze_wide_v1_v3_tie_break.py --top-n 0
result=argparse error: --top-n must be a positive integer

python scripts/analyze_wide_v1_v3_tie_break.py --top-n -1
result=argparse error: --top-n must be a positive integer
```

Review:

```text
Task 1 spec review=APPROVED
Task 1 code quality review=APPROVED
Task 2 spec review=APPROVED
Task 2 code quality review=APPROVED after top-n validation fix
```

## 7. 남은 리스크

```text
1. 이번 PR은 기존 PR #22 artifact를 분석한다. 새 v4 후보 생성이나 새 백테스트 결과는 없다.
2. direct Python API 호출자가 top_n에 비양수 값을 넣는 경우는 CLI와 달리 별도 검증하지 않는다. 현재 공개 실행 경로는 script CLI이다.
3. top 10이 모두 같은 row-set이라는 결론은 known artifact 기준이다. v4 설계 후 새 runtime에서는 다시 같은 분석을 실행해야 한다.
4. representative는 promote 후보가 아니라 reporting/routing 대표다.
```

## 8. PR 판단

이번 PR은 merge 가능하다.

근거:

```text
1. PR #23의 미해결 위험인 row-set identity 미평가를 실제 artifact 기준으로 닫았다.
2. known v3 top 10이 모두 같은 실행 row-set임을 재현 가능한 script와 report로 기록했다.
3. 잘못된 CLI 입력이 조용히 잘못된 리포트를 만들 수 있는 경로를 차단했다.
4. promote/WFO/strategy.db 변경 없이 분석 계층만 추가했다.
5. 테스트, lint, type diagnostics, sync guard, diff check가 통과했다.
```

따라서 이번 PR 이후 다음 단계는 아래 명령으로 시작하는 것이 맞다.

```text
$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계
```
