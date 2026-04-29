# Wide v2 CLI command family 리팩터링 필요성 및 업스트림 준비 설계

## 기준점

- 시작 기준 merge point: `e4981a143b9e75c725f48b77b69147245b10f499`
- 현재 기준 merge point: `fe55be1f30cb540f0628678024fa41481be82551`
- 현재 브랜치: `feature/cli-command-family-refactor-review`

`e4981a14` 이후 Wide v2 개발 정리와 CLI 리팩터링 준비가 시작되었다. 이후 PR #30에서 `research_loop.py` helper 책임을 분리했고, PR #31에서 `cli/subcommands.py`의 `discovery research`와 `discovery optimize-wide-v2` wiring을 `cli/commands/research.py`로 분리했다.

이번 설계는 남은 command family를 계속 리팩터링할지, 아니면 업스트림 업데이트 준비로 넘어갈지 판단하는 stop gate다.

## 전체 리팩터링 플로우

```text
[완료] 1. e4981a14
Wide v2 개발 정리 + CLI 리팩터링 준비

[완료] 2. PR #30 / 4f900fea
research_loop.py helper 책임 분리

[완료] 3. PR #31 / fe55be1f
subcommands.py research/optimize-wide-v2 wiring 분리

[현재] 4. 남은 command family 리팩터링 필요성 판단
추가 분리보다 업스트림 준비가 우선인지 결정

[다음] 5. 리팩터링 stop gate + 업스트림 sync 준비 문서/검증
2U 최신 코드와 2U_C 커스텀 diff를 안전하게 비교할 준비

[후속] 6. 업스트림 cherry-pick 준비 또는 보류 판단
충돌 위험과 테스트 범위를 문서화

[최종] 7. 조건식 자동 개선 루프 후속 개발 재개
수익률 개선 목적의 후보 생성/평가 로직 재설계
```

## 현재 상태 요약

`cli/subcommands.py`는 PR #31 이후 약 1,426줄이다. 여전히 여러 command family를 갖고 있지만, Wide v2 조건식 개선에서 가장 많이 변하던 `discovery research`와 `discovery optimize-wide-v2`는 별도 모듈로 이동했다.

남은 주요 command family:

- `runtime-preflight`
- `formula`
- `strategy`
- `discovery analyze/generate/create-strategy/promote/auto/batch/history/evolve/compare`
- `optimize`
- `sweep`
- `wfo`
- `setting`
- `report`
- `tune`
- `db`

이 중 업스트림 충돌 가능성과 조건식 개선 후속 개발 연관성이 높은 영역은 WFO, runtime-preflight, discovery 나머지 명령이다. 다만 현재 핵심 로직은 이미 `cli/wfo.py`, `cli/runtime_preflight.py`, `cli/auto_discovery.py`, `cli/optimizer.py`, `cli/sweep.py` 등으로 분리되어 있고, `subcommands.py`에는 parser/handler wiring이 주로 남아 있다.

## 접근안 비교

### A. WFO command wiring을 바로 분리

`wfo` parser와 `_handle_wfo()`를 `cli/commands/wfo.py`로 이동한다.

장점:

- WFO/OOS 검증 경계가 선명해진다.
- `cli/wfo.py`와 가까운 command wrapper를 만들 수 있다.
- WFO 관련 테스트가 이미 존재한다.

단점:

- 조건식 자동 개선 재개와 직접 연결된 작업은 아니다.
- WFO는 현재 후속 검증 수단이지 후보 생성 루프의 핵심이 아니다.
- 추가 PR이 필요해 업스트림 준비가 지연된다.

### B. runtime-preflight command wiring을 바로 분리

`runtime-preflight` parser, `_handle_runtime_preflight()`, `_normalize_avg_time()`, `_runtime_preflight_config_error()`를 `cli/commands/runtime_preflight.py`로 이동한다.

장점:

- 실행 전 검증 경계가 명확해진다.
- 업스트림 업데이트 후 CLI 런타임 안전성 검증에 도움이 된다.
- 테스트가 이미 존재한다.

단점:

- helper 함수의 기존 patch 경로와 테스트 호환성을 다시 확인해야 한다.
- 지금 당장 조건식 자동 개선 로직을 개선하지 않는다.
- WFO 분리와 마찬가지로 리팩터링 PR이 하나 더 늘어난다.

### C. 추가 코드 분리는 보류하고 업스트림 준비 stop gate를 만든다

남은 command family를 지금 바로 분리하지 않고, 현재 리팩터링 성과를 기준으로 업스트림 업데이트 준비 문서를 만든다. WFO/runtime-preflight 분리는 backlog로 남기고, 실제 업스트림 diff를 본 뒤 필요한 경우에만 분리한다.

장점:

- MVP 지연을 줄인다.
- 이미 가장 큰 research 충돌 면적을 줄였으므로 다음 판단 지점으로 넘어갈 수 있다.
- 2U 최신 코드와 2U_C 커스텀 diff를 먼저 보면 어떤 command family가 실제 충돌 위험인지 알 수 있다.
- 조건식 자동 개선 후속 개발로 돌아가는 경로가 짧아진다.

단점:

- `cli/subcommands.py`는 여전히 큰 파일로 남는다.
- WFO/runtime-preflight wiring은 후속 backlog로 남는다.
- 업스트림 diff에서 실제 충돌이 크면 다시 리팩터링 PR을 열어야 할 수 있다.

## 선택 설계

권장안은 C안이다.

현재 단계에서는 WFO나 runtime-preflight를 바로 분리하지 않는다. 대신 `feature/cli-command-family-refactor-review`에서 다음 산출물을 만든다.

```text
docs/research/condition_research/mvp/2026-04-30_wide_v2_cli_refactor_stop_gate.md
docs/research/condition_research/mvp/2026-04-30_2uc_upstream_sync_preflight.md
docs/pr/2026-04-30_wide_v2_cli_refactor_stop_gate_and_upstream_prep_pr.md
```

목표는 다음과 같다.

- PR #30/#31로 줄어든 충돌 면적을 기록한다.
- 남은 command family별 추가 분리 필요성을 backlog로 분류한다.
- 업스트림 업데이트 전에 확인할 diff/test/checklist를 고정한다.
- 더 이상의 리팩터링을 무기한 계속하지 않도록 stop gate를 만든다.
- 조건식 자동 개선 후속 개발 재개 전 필요한 최소 안전장치를 정의한다.

## command family별 판단

| 영역 | 현재 판단 | 이유 |
| --- | --- | --- |
| `discovery research`, `optimize-wide-v2` | 완료 | PR #31에서 `cli/commands/research.py`로 분리됨 |
| `research_loop.py` helper | 완료 | PR #30에서 ranking/cleanup/runtime metadata 분리됨 |
| `wfo` | backlog | 후속 검증 수단이며 지금 즉시 분리하지 않음 |
| `runtime-preflight` | backlog | 업스트림 업데이트 후 안전 검증에 중요하지만 현재 로직은 이미 `cli/runtime_preflight.py`에 있음 |
| `discovery promote/auto/evolve` | backlog | discovery family 전체 분리는 범위가 크므로 지금 보류 |
| `formula`, `strategy`, `db`, `setting`, `report`, `tune` | 보류 | 조건식 자동 개선 핵심 경로와 직접 관련 낮음 |
| `optimize`, `sweep` | 보류 | 별도 CLI 기능이며 현 단계 우선순위 낮음 |

## 업스트림 준비 순서

```text
1. 현재 2U_C 기준 clean 상태 확인
   git status --short --branch

2. 최신 2U와 2U_C diff 범위 재확인
   git diff --name-only STOM_Version_2U..STOM_Version_2U_C -- cli stom_backtest.py tests/unit docs/research docs/superpowers docs/pr utility/ai_agent

3. 보호 대상 재확인
   cli/
   stom_backtest.py
   tests/unit/test_research_*
   tests/unit/test_wfo*
   tests/unit/test_runtime_preflight.py
   docs/research/condition_research/
   docs/superpowers/
   utility/ai_agent/Wide*

4. 최소 검증 명령 고정
   python -m pytest tests/unit/test_subcommands.py tests/unit/test_research_command_wiring.py tests/unit/test_research_loop.py tests/unit/test_wfo.py tests/unit/test_runtime_preflight.py -q
   python scripts/verify_nonrelease_sync.py
   git diff --check --ignore-cr-at-eol HEAD

5. 전체 검증 명령 고정
   python -m pytest tests/unit/ -q
   python scripts/verify_nonrelease_sync.py

6. 업스트림 반영 브랜치 후보 생성
   feature/2uc-upstream-sync-prep

7. cherry-pick 또는 파일 단위 반영 전 충돌 위험을 먼저 문서화
```

## 하지 않을 일

- 이번 단계에서 WFO/runtime-preflight 코드를 이동하지 않는다.
- 조건식 후보 생성 v6/v7을 추가하지 않는다.
- 수익률 목적함수를 추가하지 않는다.
- full backtest 또는 WFO/OOS를 재실행하지 않는다.
- `backtest/graph/`, `backtest/temp/`, `backtest/csv/`, `utility/strategy.db`를 커밋하지 않는다.
- `STOM_Version_2U_C`에 직접 커밋하지 않는다.

## 성공 기준

- 리팩터링 stop gate가 문서로 남는다.
- 남은 command family가 `backlog`, `보류`, `완료`로 분류된다.
- 업스트림 업데이트 전 실행할 최소/전체 검증 명령이 고정된다.
- 다음 단계가 “추가 리팩터링 PR”인지 “업스트림 sync 준비 PR”인지 명확해진다.
- 조건식 자동 개선 후속 개발로 돌아가기 위한 경로가 더 짧아진다.

## 다음 추천 명령

```text
$writing-plans Wide v2 CLI 리팩터링 stop gate 및 2U_C 업스트림 업데이트 준비 계획 작성
```
