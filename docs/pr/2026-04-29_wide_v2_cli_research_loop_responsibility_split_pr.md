# Wide v2 CLI research_loop 책임 분리 1차 리팩터링

## 목적

이번 PR은 조건식 자동 개선 기능을 더 확장하기 전에, 가장 커진 `cli/research_loop.py`의 낮은 위험도 helper 책임을 분리하는 1차 리팩터링입니다.

조건식 개선 MVP의 현재 우선순위는 새 조건식 알고리즘을 계속 추가하는 것이 아니라, 지금까지 만든 CLI 기반 후보 생성, 백테스트 반복, 결과 기록 경로를 유지보수 가능한 구조로 정리하는 것입니다. 그래야 이후 2U 정규 업데이트를 cherry-pick으로 받아도 커스텀 기능의 충돌 범위를 줄일 수 있습니다.

## 전체 흐름

```text
Wide v2 개발 성과 정리
-> CLI 커스텀 범위 inventory
-> research_loop.py 책임 분리 1차 리팩터링
-> subcommands.py 명령 wiring 정리
-> 2U 최신 코드와 custom diff 재검토
-> 업스트림 업데이트 준비
-> 조건식 자동 개선 루프 후속 개발 재개
```

## 이번 PR에서 한 일

- `cli/research_ranking.py` 추가
  - 후보별 promotion score, retention penalty, tie-break ranking helper를 분리했습니다.
- `cli/research_cleanup.py` 추가
  - 후보 전략 삭제, 실패 후보 보존/삭제, cleanup summary helper를 분리했습니다.
- `cli/research_runtime_metadata.py` 추가
  - runtime output의 checkpoint/candidate duration 요약 helper를 분리했습니다.
- `cli/research_loop.py` 정리
  - 이동한 helper 본문을 제거하고 import 기반으로 연결했습니다.
  - 기존 테스트와 외부 호출자가 `research_loop.delete_strategy_from_db`를 monkeypatch하던 호환성을 유지하기 위해 cleanup 삭제 함수만 얇은 wrapper로 남겼습니다.

## 의도적으로 하지 않은 일

- `cli/subcommands.py` 분리
- 조건식 수익률 목적함수 추가
- v6/v7 후보 생성 추가
- WFO/OOS 재실행
- full backtest 재실행
- `backtest/graph/`, `backtest/temp/`, `backtest/csv/`, `utility/strategy.db` 변경

## 검증

기준 테스트:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q
python -m pytest tests/unit/test_subcommands.py -q
```

리팩터링 후 검증:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q
python -m pytest tests/unit/test_subcommands.py -q
python -m compileall -q cli
git diff --check --ignore-cr-at-eol HEAD
```

결과:

- `tests/unit/test_research_loop.py`: 85 passed
- `tests/unit/test_research_optimizer.py`, `test_research_optimizer_report.py`, `test_research_optimizer_state.py`: 38 passed
- `tests/unit/test_subcommands.py`: 81 passed
- `python -m compileall -q cli`: passed
- `git diff --check --ignore-cr-at-eol HEAD`: passed

## 현재 완성도

리팩터링 준비 단계 기준으로는 첫 번째 코드 분리가 완료되었습니다.

조건식 자동 개선 전체 MVP 관점에서는 새 수익 조건식을 안정적으로 찾는 단계가 아직 완성된 것이 아닙니다. Wide v2는 반복 백테스트와 후보 생성 흐름을 만들었지만 수익률 개선 폭이 작았기 때문에, 현재 단계는 후속 개발을 더 안전하게 하기 위한 구조 정리입니다.

## 남은 리스크

- `cli/subcommands.py`가 여전히 큽니다.
- `research_loop.py`에는 아직 runtime finalization, checkpoint flush, iteration orchestration 책임이 남아 있습니다.
- 이번 PR은 동작 보존 리팩터링이므로 수익률 개선을 만들지 않습니다.
- 실제 full backtest를 재실행하지 않았기 때문에, 검증 범위는 unit/compile/static 수준입니다.

## Merge 후 다음 단계

다음 추천 브랜치:

```text
feature/cli-subcommands-refactor-plan
```

다음 추천 명령:

```text
$brainstorming Wide v2 CLI subcommands 명령 wiring 리팩터링 및 업스트림 업데이트 충돌 축소 설계
```

이 다음 단계의 목적은 `cli/subcommands.py`의 research 명령 wiring을 얇게 분리해, 이후 정규 2U 업데이트를 받을 때 CLI 커스텀 충돌 가능성을 더 줄이는 것입니다.
