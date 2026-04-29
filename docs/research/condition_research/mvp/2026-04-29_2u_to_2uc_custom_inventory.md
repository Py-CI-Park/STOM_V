# 2U to 2U_C custom inventory

## 목적

이 문서는 `STOM_Version_2U` 최신 코드와 `STOM_Version_2U_C`의 차이를 정리해, 이후 정규 업스트림 업데이트를 받을 때 CLI 커스텀 기능을 잃지 않도록 하기 위한 인벤토리다.

## 현재 브랜치 역할

```text
STOM_Version_2U
-> upstream 2U baseline

STOM_Version_2U_C
-> 2U 기반 CLI/조건식 개선 커스텀 baseline
```

`2U_C`의 CLI 커스텀은 `2U`에 없는 기능이다. 따라서 업스트림 동기화 시 overlay merge로 덮어쓰면 안 된다.

## 파일 수 요약

확인 명령:

```powershell
git diff --name-only STOM_Version_2U..STOM_Version_2U_C -- cli tests/unit docs/pr docs/research docs/superpowers utility/ai_agent stom_backtest.py
```

요약:

| 영역 | 파일 수 |
| --- | ---: |
| 주요 커스텀 전체 | `340` |
| `cli/` | `55` |
| `tests/unit/` | `84` |
| `docs/` | `234` |

## 보호 대상

업스트림 업데이트 시 다음 영역은 `2U_C` 커스텀 보호 대상으로 본다.

```text
cli/
stom_backtest.py
tests/unit/test_research_*
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

## 주요 CLI 커스텀 기능

| 영역 | 대표 파일 | 설명 |
| --- | --- | --- |
| CLI 진입점 | `stom_backtest.py` | STOM 백테스트 CLI entry point |
| command routing | `cli/subcommands.py` | discovery, research, WFO, strategy, runtime-preflight 명령 연결 |
| 백테스트 실행 | `cli/runner.py` | CLI에서 GUI 백테스트 흐름과 맞춰 실행 |
| 실행 전 검증 | `cli/runtime_preflight.py` | strategy/db/date/timeframe/engine 사전 점검 |
| WFO/OOS | `cli/wfo.py` | window 생성과 OOS 검증 |
| 조건식 생성 | `cli/condition_generator.py`, `cli/research_iteration_v2.py`~`v5.py` | 후보 조건식 생성 |
| 후보 부족 복구 | `cli/research_iteration_v5_recovery.py` | direct_v4/v5 shortfall recovery |
| 반복 개선 | `cli/research_optimizer.py` | Wide v2 multi-round coordinator |
| 결과 기록 | `cli/research_optimizer_report.py`, `cli/research_report.py`, `cli/research_runtime_output.py` | Markdown/JSON evidence |
| ranking/품질 | `cli/research_promotion.py`, `cli/research_retention.py`, `cli/research_rowdiff.py`, `cli/research_v3_tiebreak.py`, `cli/research_v4_rowset.py` | 후보 비교와 row-set 다양성 |

## 정규 업스트림 업데이트 원칙

업스트림 업데이트는 다음 원칙으로 진행한다.

```text
1. STOM_Version_2U_C에 직접 덮어쓰지 않는다.
2. 별도 update branch를 만든다.
3. upstream 변경은 cherry-pick 또는 파일 단위 검토로 반영한다.
4. cli/와 stom_backtest.py는 충돌 여부를 먼저 확인한다.
5. 테스트로 CLI 커스텀 동작을 확인한 뒤 PR merge한다.
```

추천 branch:

```text
feature/2uc-upstream-sync-prep
```

추천 검증:

```powershell
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol HEAD
```

시간이 오래 걸릴 때 최소 검증:

```powershell
python -m pytest tests/unit/test_subcommands.py tests/unit/test_research_loop.py tests/unit/test_wfo.py tests/unit/test_runtime_preflight.py -q
python scripts/verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol HEAD
```

## 커밋하지 않을 것

다음은 로컬 실행 결과 또는 보호 결과물이므로 PR에 포함하지 않는다.

```text
backtest/graph/
backtest/temp/
backtest/csv/
utility/strategy.db
```

## 다음 단계

1. 이 인벤토리를 `STOM_Version_2U_C`에 PR로 병합한다.
2. CLI research 리팩토링 계획을 만든다.
3. 리팩토링으로 커스텀 경계를 명확히 한다.
4. 그 다음 정규 업스트림 업데이트 준비 브랜치를 만든다.
