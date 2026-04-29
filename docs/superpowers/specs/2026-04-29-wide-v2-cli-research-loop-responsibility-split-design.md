# Wide v2 CLI research_loop 책임 분리 및 업스트림 보호 설계

## 목적

이번 설계의 목적은 조건식 개선 기능을 새로 추가하는 것이 아니라, 이미 `STOM_Version_2U_C`에 병합된 CLI research 커스텀 기능을 리팩토링하기 위한 1차 범위를 정하는 것이다.

현재 최우선 목표는 다음이다.

```text
기존 동작 보존
-> research_loop.py 책임 분리
-> 테스트로 회귀 방지
-> CLI 커스텀 경계 명확화
-> 이후 정규 업스트림 업데이트 준비
```

이번 단계는 실거래, WFO 재실행, 수익률 목적함수 구현, v6/v7 후보 생성과 무관하다.

## 현재 상태

현재 브랜치:

```text
feature/cli-research-refactor-plan
```

현재 기준 커밋:

```text
e4981a14 Wide v2 개발 정리 및 CLI 리팩토링 준비
```

주요 리팩토링 후보:

| 파일 | 줄 수 | 판단 |
| --- | ---: | --- |
| `cli/research_loop.py` | 1,961 | 후보 생성, 실행, ranking, cleanup, runtime metadata 책임이 섞여 있음 |
| `cli/subcommands.py` | 1,464 | parser와 handler 연결 책임이 큼 |
| `cli/research_optimizer.py` | 539 | Wide v2 반복 개선 coordinator |
| `cli/research_report.py` | 523 | research report rendering |

첫 리팩토링 대상은 `cli/research_loop.py`다. 이유는 다음과 같다.

- `tests/unit/test_research_loop.py`가 내부 함수와 주요 흐름을 넓게 보호한다.
- `subcommands.py`를 먼저 나누면 CLI surface 전체가 흔들릴 수 있다.
- `research_loop.py`의 ranking, cleanup, runtime metadata는 독립성이 비교적 높다.
- 코드 이동 중심의 작은 PR로 시작할 수 있다.

## 설계 대안

### A. `research_loop.py` 내부 책임을 먼저 분리

`research_loop.py`에서 ranking, cleanup, runtime metadata helper를 작은 모듈로 이동한다.

장점:

- CLI 명령 계약을 거의 건드리지 않는다.
- 기존 `run_research_iteration()` 외부 동작을 유지하기 쉽다.
- 테스트 기반 회귀 확인이 쉽다.
- 다음 업스트림 업데이트 전에 커스텀 경계를 더 선명하게 만들 수 있다.

단점:

- `subcommands.py`의 크기 문제는 다음 PR로 남는다.
- 함수 이동 중 import 순환을 조심해야 한다.

### B. `subcommands.py`를 command family별로 먼저 분리

`discovery`, `wfo`, `runtime-preflight`, `strategy` handler를 `cli/commands/` 아래로 분리한다.

장점:

- CLI 폴더 구조가 바로 명확해진다.
- command family별 소유권을 분리하기 좋다.

단점:

- parser와 handler 표면을 동시에 건드린다.
- CLI regression 위험이 크다.
- 현재 단계의 첫 리팩토링 PR로는 범위가 넓다.

### C. 대용량 report/artifact 관리 정책을 먼저 정리

`docs/research/condition_research/pilot_logs/`의 큰 JSON report 관리 정책을 먼저 정리한다.

장점:

- 저장소 크기와 PR review 부담을 줄이는 방향을 빨리 잡을 수 있다.
- 업스트림 업데이트 전 문서/결과물 경계 정리에 도움된다.

단점:

- CLI 코드 구조 개선은 미뤄진다.
- 이미 커밋된 큰 파일을 다루는 정책 문제라 별도 설계가 필요하다.

## 추천안

추천은 A다.

1차 리팩토링은 `research_loop.py`의 외부 동작을 유지하면서 내부 helper 책임을 분리한다.

이번 1차 범위:

```text
cli/research_loop.py
-> cli/research_ranking.py
-> cli/research_cleanup.py
-> cli/research_runtime_metadata.py
```

이번 1차 범위에서 제외:

```text
cli/subcommands.py 분리
수익률 목적함수 구현
후보 생성 v6/v7 확장
WFO/OOS 재실행
대용량 pilot_logs 정리
```

## 모듈 설계

### `cli/research_ranking.py`

역할:

- 후보 ranking score 계산
- retention penalty 적용 전후의 rank score 구성
- best candidate 선택

이동 후보:

```text
_numeric_value()
_rank_score()
_rank_key()
_rank_candidate_results()
```

주의:

- `apply_retention_penalty()`는 현재 `cli.research_retention`에 있다.
- `ResearchLoopConfig` 타입을 직접 import하면 순환 import 위험이 있으므로, 필요한 config 속성만 protocol 또는 duck typing으로 사용한다.
- 함수명은 1차 PR에서 유지한다. public API를 새로 만들지 않는다.

예상 import 방향:

```text
research_loop.py -> research_ranking.py
research_ranking.py -> research_retention.py
```

### `cli/research_cleanup.py`

역할:

- 후보 전략 cleanup 결정
- best/loser/failed candidate 삭제 또는 보존 판단
- cleanup summary 생성

이동 후보:

```text
_cleanup_candidate_by_name()
_candidate_not_created_cleanup()
_cleanup_summary()
_apply_iteration_cleanup()
```

주의:

- `delete_strategy_from_db()`와 `DB_STRATEGY` 의존성이 있다.
- `_CLEANUP_SAFE_FAILURE_PHASES` 상수 사용 여부를 확인해 함께 이동하거나 함수 인자로 주입한다.
- config 전체 타입 import를 피하고 필요한 속성만 사용한다.

예상 import 방향:

```text
research_loop.py -> research_cleanup.py
research_cleanup.py -> cli.paths, cli.strategy_generator 또는 기존 delete helper 위치
```

### `cli/research_runtime_metadata.py`

역할:

- candidate runtime timing summary 생성
- runtime checkpoint/finalize metadata 구성 보조
- runtime write failure 구조화

이동 후보:

```text
_elapsed_value()
_candidate_field()
_candidate_expression()
_runtime_timing_summary()
_runtime_write_failure()
_finalize_research_runtime_result()
_flush_research_runtime_checkpoint()
```

주의:

- 이 모듈은 `ResearchRuntimeRecorder`와 깊게 연결되어 있다.
- `_finalize_research_runtime_result()`와 `_flush_research_runtime_checkpoint()`는 config/asdict/recorder/failure_policy/result 구조를 많이 사용한다.
- 1차 구현 계획에서는 `runtime_timing_summary` 계열부터 분리하고, finalize/checkpoint 함수는 복잡도에 따라 2차로 미룰 수 있다.

권장 1차 최소 분리:

```text
_elapsed_value()
_candidate_field()
_candidate_expression()
_runtime_timing_summary()
```

## 1차 PR 권장 범위

1차 PR은 너무 넓히지 않는다.

권장 순서:

```text
1. research_ranking.py 생성 및 ranking helper 이동
2. research_cleanup.py 생성 및 cleanup helper 이동
3. research_runtime_metadata.py 생성 및 timing summary helper 이동
4. research_loop.py에서 import로 연결
5. 기존 test_research_loop.py / optimizer / subcommands 테스트 통과 확인
```

`_finalize_research_runtime_result()`와 `_flush_research_runtime_checkpoint()`는 1차 PR에서 무리하게 이동하지 않는다. 두 함수는 runtime recorder와 error handling에 깊게 연결되어 있어, 첫 PR에서는 risk가 크다.

## 업스트림 업데이트 보호 기준

리팩토링 후 업스트림 업데이트를 준비하려면 다음 기준을 지킨다.

```text
1. STOM_Version_2U_C에 직접 커밋하지 않는다.
2. feature branch -> PR -> merge 루틴을 유지한다.
3. cli/research_*.py는 2U_C 커스텀 보호 영역으로 본다.
4. 함수 이동 전후 test_research_loop.py를 반드시 통과시킨다.
5. raw runtime output은 계속 커밋하지 않는다.
```

보호 대상:

```text
cli/research_loop.py
cli/research_ranking.py
cli/research_cleanup.py
cli/research_runtime_metadata.py
cli/research_optimizer.py
cli/subcommands.py
tests/unit/test_research_loop.py
tests/unit/test_research_optimizer.py
tests/unit/test_subcommands.py
```

## 검증 전략

리팩토링 전 baseline 검증:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q
python -m pytest tests/unit/test_subcommands.py -q
python scripts/verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol HEAD
```

리팩토링 후 동일 검증:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q
python -m pytest tests/unit/test_subcommands.py -q
python scripts/verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol HEAD
```

시간이 오래 걸릴 경우 최소 검증:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
python -m pytest tests/unit/test_research_optimizer_state.py tests/unit/test_research_optimizer_report.py -q
python scripts/verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol HEAD
```

## 완료 기준

설계가 맞다면 다음 구현 계획은 다음 기준을 만족해야 한다.

- `research_loop.py`의 public entrypoint는 유지한다.
- 기존 CLI 명령 이름과 옵션은 변경하지 않는다.
- ranking/cleanup/timing helper 이동 후 기존 테스트가 통과한다.
- 새 모듈은 독립 책임을 가진다.
- 수익률 목적함수나 후보 생성 기능을 섞지 않는다.
- PR 설명에는 "동작 변경 없는 구조 정리"를 명확히 쓴다.

## 다음 명령

이 설계가 맞다면 다음 명령은 구현 계획 작성이다.

```text
$writing-plans Wide v2 CLI research_loop 책임 분리 1차 리팩토링 구현 계획 작성
```

## 자체 검토

- 첫 PR 범위를 `research_loop.py` 책임 분리로 제한했다.
- `subcommands.py` 분리는 다음 단계로 미뤘다.
- 업스트림 업데이트 보호 대상과 검증 명령을 포함했다.
- 수익률 개선 개발과 후보 생성 확장은 범위에서 제외했다.
- 코드 변경 없이 설계만 기록한다.
