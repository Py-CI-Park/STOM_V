# 2U_C 업스트림 업데이트 Preflight

## 목적

이 문서는 `STOM_Version_2U` 최신 코드와 `STOM_Version_2U_C` 커스텀 baseline을 비교하기 전에 실행할 preflight checklist다.

업스트림 업데이트는 overlay merge가 아니라 cherry-pick 또는 파일 단위 검토로 진행한다. `2U_C`에는 CLI와 조건식 개선 커스텀이 포함되어 있고, 이를 덮어쓰면 지금까지 만든 백테스트 반복 개선 경로가 손상될 수 있기 때문이다.

## 현재 기준

```text
STOM_Version_2U
-> upstream 2U baseline

STOM_Version_2U_C
-> 2U 기반 CLI/조건식 개선 custom baseline

현재 2U_C 기준 merge:
fe55be1f30cb540f0628678024fa41481be82551
```

## 보호 대상

업스트림 업데이트 전 다음 영역은 먼저 보호 대상으로 본다.

```text
cli/
stom_backtest.py
tests/unit/test_research_*
tests/unit/test_research_command_wiring.py
tests/unit/test_wfo*
tests/unit/test_runtime_preflight.py
tests/unit/test_strategy_generator.py
tests/unit/test_strategy_loader.py
docs/research/condition_research/
docs/superpowers/
docs/pr/*wide*
utility/ai_agent/WideV1Final_B_20260425.py
utility/ai_agent/WideV2Final_B_20260428.py
```

## 업스트림 업데이트 전 확인 명령

### 1. 현재 상태 확인

```powershell
git status --short --branch
git log --oneline --decorate -8
```

예상:

```text
현재 브랜치는 feature/2uc-upstream-sync-prep 또는 그 준비 브랜치여야 한다.
backtest/graph/ 외 의도하지 않은 변경이 없어야 한다.
```

### 2. 2U 대비 2U_C 커스텀 diff 확인

```powershell
git diff --name-only STOM_Version_2U..STOM_Version_2U_C -- cli stom_backtest.py tests/unit docs/research docs/superpowers docs/pr utility/ai_agent
```

확인 포인트:

```text
cli/subcommands.py
cli/commands/research.py
cli/research_loop.py
cli/research_ranking.py
cli/research_cleanup.py
cli/research_runtime_metadata.py
cli/research_optimizer.py
cli/research_optimizer_report.py
cli/research_runtime_output.py
cli/research_iteration_v2.py~v5*.py
tests/unit/test_research_*
tests/unit/test_subcommands.py
tests/unit/test_research_command_wiring.py
```

### 3. 최소 검증

시간을 줄여야 할 때는 다음을 먼저 실행한다.

```powershell
python -m pytest tests/unit/test_subcommands.py tests/unit/test_research_command_wiring.py tests/unit/test_research_loop.py tests/unit/test_wfo.py tests/unit/test_runtime_preflight.py -q
python scripts/verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol HEAD
```

### 4. 전체 검증

업스트림 반영 PR merge 전에는 다음을 실행한다.

```powershell
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol HEAD
```

## 반영 원칙

```text
1. STOM_Version_2U_C에 직접 커밋하지 않는다.
2. feature/2uc-upstream-sync-prep 브랜치에서만 작업한다.
3. upstream 변경은 cherry-pick 또는 파일 단위 검토로 반영한다.
4. cli/와 stom_backtest.py는 덮어쓰기 금지다.
5. 충돌이 발생하면 먼저 충돌 파일과 커스텀 기능을 문서화한다.
6. 테스트가 통과하기 전에는 PR merge를 하지 않는다.
```

## 다음 브랜치

```text
feature/2uc-upstream-sync-prep
```

## 다음 추천 명령

```text
$brainstorming 2U_C 업스트림 업데이트 diff 분석 및 cherry-pick 준비
```
