# Wide v2 CLI 리팩터링 Stop Gate 및 2U_C 업스트림 준비

## 목적

이번 PR은 코드 변경 없이 Wide v2 CLI 리팩터링을 어디에서 멈출지 정하고, 다음 `2U_C` 업스트림 업데이트 준비 순서를 문서로 고정하는 documentation checkpoint입니다.

PR #30과 PR #31을 통해 조건식 자동 개선에서 가장 자주 변경되는 research 경계의 충돌 면적을 줄였습니다. 따라서 지금은 WFO/runtime-preflight 등 남은 command family를 계속 분리하기보다, 실제 2U 업스트림 diff를 보기 위한 준비 단계로 넘어갑니다.

## 전체 단계

```text
[완료] e4981a14
Wide v2 개발 정리 및 CLI 리팩터링 준비

[완료] PR #30
research_loop.py helper 책임 분리

[완료] PR #31
subcommands.py research/optimize-wide-v2 wiring 분리

[이번 PR]
CLI 리팩터링 stop gate 및 2U_C upstream sync preflight

[다음]
feature/2uc-upstream-sync-prep 에서 실제 diff 분석

[최종]
조건식 자동 개선 루프 후속 개발 재개
```

## 이번 PR에서 기록한 내용

- 추가 command family 리팩터링은 현재 보류
- WFO/runtime-preflight/discovery 나머지는 backlog로 분류
- `cli/subcommands.py`는 아직 크지만 research 충돌 면적은 PR #31에서 축소 완료
- 업스트림 업데이트 때 보호해야 할 CLI/조건식 개선 파일 목록 정리
- 최소 검증과 전체 검증 명령 고정
- 다음 브랜치 `feature/2uc-upstream-sync-prep` 고정

## 추가 문서

- `docs/research/condition_research/mvp/2026-04-30_wide_v2_cli_refactor_stop_gate.md`
- `docs/research/condition_research/mvp/2026-04-30_2uc_upstream_sync_preflight.md`
- `docs/superpowers/specs/2026-04-30-wide-v2-cli-command-family-refactor-and-upstream-prep-design.md`
- `docs/superpowers/plans/2026-04-30-wide-v2-cli-refactor-stop-gate-upstream-prep.md`

## 검증

```powershell
python -m pytest tests/unit/test_subcommands.py tests/unit/test_research_command_wiring.py tests/unit/test_research_loop.py tests/unit/test_wfo.py tests/unit/test_runtime_preflight.py -q
python scripts/verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol HEAD
```

merge 후 기준 브랜치 검증:

```powershell
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
```

## 하지 않은 일

- WFO/runtime-preflight 코드 이동
- 조건식 후보 생성 v6/v7 추가
- 수익률 목적함수 추가
- full backtest 또는 WFO/OOS 재실행
- upstream cherry-pick
- `backtest/graph/`, `backtest/temp/`, `backtest/csv/`, `utility/strategy.db` 변경

## Merge 후 다음 추천 명령

```text
$brainstorming 2U_C 업스트림 업데이트 diff 분석 및 cherry-pick 준비
```
