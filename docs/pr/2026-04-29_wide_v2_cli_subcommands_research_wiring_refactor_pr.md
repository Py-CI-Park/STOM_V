# Wide v2 CLI subcommands research 명령 wiring 리팩터링

## 목적

이번 PR은 `cli/subcommands.py`에서 Wide v2 조건식 개선에 직접 연결된 `discovery research`와 `discovery optimize-wide-v2` 명령 wiring을 분리하는 동작 보존 리팩터링입니다.

최종 목표는 조건식 자동 개선 루프를 다시 개발하기 전에 CLI 커스텀 코드를 작게 나누고, 이후 2U 정규 업데이트를 cherry-pick 방식으로 받을 때 충돌 범위를 줄이는 것입니다.

## 전체 리팩터링 플로우

```text
e4981a14: Wide v2 개발 정리와 CLI 리팩터링 준비
-> PR #30: research_loop.py helper 책임 분리
-> 이번 PR: subcommands.py research 명령 wiring 분리
-> 다음 단계: WFO/runtime-preflight 등 남은 command family 분리 필요성 판단
-> 업스트림 준비: 2U 최신 코드와 2U_C 커스텀 diff 재검토
-> 최종 목표: 조건식 자동 개선 루프 후속 개발 재개
```

## 이번 PR에서 한 일

- `cli/commands/__init__.py` 추가
- `cli/commands/research.py` 추가
- `discovery research` parser 등록을 새 모듈로 이동
- `discovery optimize-wide-v2` parser 등록을 새 모듈로 이동
- `research_strategy_once()` payload 변환을 `build_research_strategy_payload()`로 분리
- `WideV2OptimizerConfig` 변환을 `build_wide_v2_optimizer_config()`로 분리
- `cli/subcommands.py`는 top-level parser/router 역할만 유지
- 직접 unit test로 새 wiring helper contract 고정

## 유지한 동작

- CLI 명령 이름 유지: `discovery research`
- CLI 명령 이름 유지: `discovery optimize-wide-v2`
- 옵션 이름, 기본값, choices 유지
- JSON 출력 포맷 유지
- 성공 exit code `0`, 실패 exit code `1` 유지
- 기존 `tests/unit/test_subcommands.py` contract 유지

## 하지 않은 일

- discovery command family 전체 분리
- WFO/runtime-preflight/formula/strategy/db 명령 분리
- 조건식 생성 알고리즘 변경
- 수익률 목적함수 추가
- full backtest 또는 WFO/OOS 재실행
- `backtest/graph/`, `backtest/temp/`, `backtest/csv/`, `utility/strategy.db` 변경

## 검증

```powershell
python -m pytest tests/unit/test_research_command_wiring.py -q
python -m pytest tests/unit/test_subcommands.py -q
python -m pytest tests/unit/test_research_loop.py -q
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q
python -m compileall -q cli
git diff --check --ignore-cr-at-eol HEAD
```

검증 결과:

- `tests/unit/test_research_command_wiring.py`: 6 passed
- `tests/unit/test_subcommands.py`: 81 passed
- `tests/unit/test_research_loop.py`: 85 passed
- `test_research_optimizer*`: 38 passed
- `python -m compileall -q cli`: passed
- `git diff --check --ignore-cr-at-eol HEAD`: passed

## 현재 단계와 남은 단계

```text
[완료] Wide v2 closeout
[완료] research_loop.py 1차 분리
[완료] subcommands.py research wiring 설계
[이번 PR] subcommands.py research wiring 구현
[다음] 남은 command family 분리 필요성 판단
[후속] 2U 최신 코드 대비 커스텀 diff 재검토
[최종] 조건식 자동 개선 루프 후속 개발 재개
```

## Merge 후 다음 추천 명령

```text
$brainstorming Wide v2 CLI 남은 command family 리팩터링 필요성 및 업스트림 업데이트 준비 순서 검토
```
