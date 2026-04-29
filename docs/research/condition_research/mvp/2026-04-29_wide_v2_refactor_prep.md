# Wide v2 CLI 리팩토링 준비

## 목적

이번 문서는 리팩토링을 바로 수행하기 위한 문서가 아니라, 다음 리팩토링 브랜치에서 무엇을 어떤 순서로 나눌지 고정하는 준비 문서다.

현재 우선순위는 다음이다.

```text
문서-only closeout PR
-> 리팩토링 계획 PR
-> 테스트로 기존 동작 고정
-> 작은 단위 리팩토링
-> 정규 업스트림 업데이트 준비
```

## 리팩토링이 필요한 이유

Wide v1/Wide v2 조건식 개선 기능이 빠르게 확장되면서 CLI 커스텀 코드가 커졌다.

특히 다음 파일이 커졌다.

| 파일 | 크기 | 판단 |
| --- | ---: | --- |
| `cli/research_loop.py` | 약 84KB | 후보 생성, 실행, ranking, cleanup, report 책임이 섞여 있음 |
| `cli/subcommands.py` | 약 81KB | parser, validation, handler 연결 책임이 커짐 |
| `cli/ai_controller.py` | 약 49KB | optimizer/history/controller 책임이 넓음 |
| `cli/auto_discovery.py` | 약 36KB | 자동 탐색과 evolution 흐름이 큼 |
| `cli/runner.py` | 약 27KB | 백테스트 실행 연결과 프로세스 제어 책임이 큼 |
| `cli/research_report.py` | 약 24KB | report 생성 책임이 확장됨 |
| `cli/research_optimizer.py` | 약 24KB | Wide v2 반복 개선 coordinator |

## 리팩토링 원칙

다음 브랜치에서 리팩토링할 때는 이 원칙을 지킨다.

```text
1. 기존 동작을 테스트로 먼저 고정한다.
2. 기능을 삭제하지 않는다.
3. 파일 분리는 동작 변경 없이 한다.
4. CLI command contract를 유지한다.
5. raw runtime output은 계속 커밋하지 않는다.
6. 한 PR에서 한 책임만 줄인다.
7. STOM_Version_2U_C에 직접 커밋하지 않는다.
```

## 우선 분리 대상

### 1. `cli/subcommands.py`

현재 역할:

- CLI parser 구성
- action dispatch
- command별 validation
- research/wfo/runtime-preflight/strategy 관련 handler 연결

분리 후보:

```text
cli/subcommands.py
-> cli/commands/research.py
-> cli/commands/wfo.py
-> cli/commands/runtime.py
-> cli/commands/strategy.py
-> cli/commands/common.py
```

첫 PR에서는 parser와 handler의 동작을 바꾸지 않고 command family별 함수 이동만 검토한다.

### 2. `cli/research_loop.py`

현재 역할:

- 후보 생성 orchestration
- 후보 백테스트 실행
- promotion/ranking
- retention penalty
- row-set selection 연결
- cleanup
- runtime metadata 정리

분리 후보:

```text
cli/research_loop.py
-> cli/research_execution.py
-> cli/research_ranking.py
-> cli/research_cleanup.py
-> cli/research_runtime_metadata.py
```

첫 PR에서는 ranking 계산과 leaderboard metadata 정리를 분리하는 것이 가장 작다.

### 3. 보고서와 대용량 결과물 관리

현재 `docs/research/condition_research/pilot_logs/`에는 큰 JSON report가 포함되어 있다. 예를 들어 Wide v2 WFO/OOS report는 매우 크다.

다음 원칙을 검토한다.

```text
1. 커밋 대상은 curated summary와 manifest 중심으로 제한한다.
2. raw runtime JSON은 backtest/temp 또는 외부 artifact로 둔다.
3. 이미 커밋된 큰 결과물은 별도 정리 PR에서 유지/압축/요약 여부를 검토한다.
```

## 리팩토링 전 필수 테스트

다음 리팩토링 계획에서 최소한 이 테스트를 먼저 통과시킨다.

```powershell
python -m pytest tests/unit/test_subcommands.py -q
python -m pytest tests/unit/test_research_loop.py -q
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q
python scripts/verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol HEAD
```

## 다음 리팩토링 브랜치

추천 브랜치:

```text
feature/cli-research-refactor-plan
```

추천 명령:

```text
$brainstorming Wide v2 CLI research 리팩토링 범위와 업스트림 업데이트 보호 설계
```

그 다음:

```text
$writing-plans Wide v2 CLI research 리팩토링 1차 구현 계획 작성
```
