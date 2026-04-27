# Wide v2 smoke/full run 검증 계획 PR 보고서

## 목적

이번 PR은 Wide v2 optimizer 구현 이후 바로 실제 full run으로 들어가지 않고, 먼저 실행 검증 절차를 고정하기 위한 계획 문서 PR이다.

핵심 목적은 다음과 같다.

1. `discovery optimize-wide-v2`가 실제 실행에서 정상 진입하는지 smoke로 확인한다.
2. smoke 결과로 runtime 예산과 후보 다양성을 먼저 판단한다.
3. `candidate_count=10` 검증은 smoke gate를 통과한 뒤 실행한다.
4. `final_best_candidate`는 실전 승인 후보가 아니라 WFO/OOS 검증 대상으로만 다룬다.
5. 실패 시 traceback 추정이 아니라 `status`, `stop_reason`, `failure_phase`, `failure_message` 기준으로 다음 복구 작업을 결정한다.

## 전체 방향성

현재 개발 방향은 조건식 자동 개선 시스템이다.

```text
기준 조건식/seed
  -> 후보 조건식 생성
  -> 후보별 백테스트
  -> 결과 JSON/Markdown 기록
  -> leaderboard 비교
  -> round best 선정
  -> 다음 round seed로 승격
  -> 반복 개선
  -> final best 후보 선정
  -> WFO/OOS 검증
  -> 운영 후보 판단
```

이번 PR은 이 흐름 중 `반복 개선 -> final best 후보 선정`이 실제 실행에서 검증 가능한지 확인하기 위한 실행 계획이다. WFO는 아직 실행하지 않는다.

## 현재 위치

직전 PR #26에서 Wide v2 자동 개선 루프가 구현되어 `STOM_Version_2U_C`에 merge되었다.

이번 PR은 그 다음 단계다.

```text
PR #26 Wide v2 optimizer 구현 완료
  -> 이번 PR: smoke/full run 실행 검증 계획 고정
  -> 다음 PR: 계획에 따라 smoke 및 candidate_count=10 실행 결과 기록
  -> 이후: final_best_candidate WFO 검증 계획
```

## 이번 PR 포함 범위

- `docs/superpowers/plans/2026-04-27-wide-v2-smoke-full-run-validation.md` 추가
- smoke 실행 명령 고정
- smoke 성공/실패 판정 기준 고정
- runtime budget gate 추가
- `candidate_count=10` 실행 명령과 round 수 선택 기준 고정
- leaderboard, expression diversity, WFO handoff 후보 확인 절차 추가
- 실행 결과 리뷰 문서와 PR 보고서 작성 절차 추가

## 제외 범위

- 실제 smoke/full run 실행
- WFO 실행
- candidate generation/scoring 코드 변경
- GUI 변경
- `utility/strategy.db` 변경
- `backtest/temp`, `backtest/csv`, `backtest/graph` 커밋

## 퀀트 관점 검토

이 계획은 수익률 하나만 보고 후보를 승인하지 않는다.

검증 순서는 다음 기준을 따른다.

1. 먼저 CLI가 구조화된 실행 결과를 남기는지 확인한다.
2. 후보가 모두 같은 row set으로 붕괴하는지 확인한다.
3. leaderboard에서 실제 비교 가능한 후보가 생기는지 확인한다.
4. `final_best_candidate`를 WFO 후보로만 넘긴다.

따라서 현재 목표인 “백테스트 결과를 바탕으로 조건식을 반복 개선하고 더 좋은 조건식을 찾는 시스템”에 맞다.

## CLI 개발 관점 검토

이 계획은 긴 실행 전에 실패 지점을 분리한다.

- parser/import 문제
- optimizer runtime 문제
- candidate backtest 문제
- output write 문제
- duplicate row-set 문제
- runtime 과다 문제

각 문제를 분리해서 다음 브랜치의 작업 대상을 명확히 만든다.

## 검증

```text
python -m pytest tests/unit/test_research_optimizer_state.py tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_subcommands.py -q
-> 113 passed in 3.52s
```

```text
python scripts/verify_nonrelease_sync.py
-> 모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

```text
git diff --check --ignore-cr-at-eol HEAD
-> no output
```

## 결론

이번 단계는 PR로 관리할 만큼 충분히 분리되어 있다. 코드 구현 PR과 실제 runtime 실행 PR 사이에 검증 계획을 고정해, 다음 실행에서 시간이 과도하게 늘어나거나 실패 원인이 섞이는 문제를 줄인다.

## 다음 단계

이번 PR merge 후 다음 명령으로 실제 실행 검증 브랜치를 진행한다.

```text
$executing-plans docs/superpowers/plans/2026-04-27-wide-v2-smoke-full-run-validation.md
```

실행 결과가 정상이라면 그 다음 추천 명령은 다음과 같다.

```text
$writing-plans Wide v2 final_best_candidate WFO 검증 계획 작성
```

실행 결과가 `duplicate_rowset_only` 또는 runtime 초과라면 WFO로 넘어가지 않고 후보 다양성 또는 실행시간 복구 설계를 먼저 진행한다.
