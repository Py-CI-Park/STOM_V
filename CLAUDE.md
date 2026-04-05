# STOM Project Guidelines (STOM_Version_2U_C)

> **워크트리 위치**: `STOM_V.wt-dev/`
> **브랜치 역할**: CLI_v267 승격 이후 활성 단일 기준선 `STOM_Version_2U_C`
> **관련 문서**: `C:/System_Trading/STOM/STOM_V/docs/WORKTREE_STRATEGY.md`, `C:/System_Trading/STOM/STOM_V/docs/UPSTREAM_SYNC_STRATEGY.md`

## Read First

- Top-level lifecycle: `C:/System_Trading/STOM/STOM_V/docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`
- Carry-forward registry: `C:/System_Trading/STOM/STOM_V/docs/CARRY_FORWARD_REGISTRY.md`
- Current cycle status: `C:/System_Trading/STOM/STOM_V/docs/update_log/2026-04-05_v274_v277_cycle_status.md`
- Promotion record: `C:/System_Trading/STOM/STOM_V.wt-2uc/docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md`

## Branch Gate

- `python scripts/verify_nonrelease_sync.py`
- `python -m pytest tests/unit/ -q`
- `backtest/graph/` is protected result data

## 레인 역할

`STOM_Version_2U_C`는 CLI_v267 승격이 흡수된 뒤의 활성 단일 기준선입니다.
현재 `wt-dev`가 이 브랜치의 유일한 active checkout이며, `wt-2uc`는 `integration/adopt-cli-v267-into-2uc`에 남아 승격 로그와 transition 기록을 보관합니다.

상하류 관계:

- 상위 입력: `STOM_V.wt-2u/` → `STOM_Version_2U`
- 현재 활성 레인: `STOM_V.wt-dev/` → `STOM_Version_2U_C`
- 보관 레인: `STOM_V.wt-2uc/` → `integration/adopt-cli-v267-into-2uc`
- 하위 전파: `STOM_V.wt-lab/` → `research/init`

## 현재 워크트리 상태

`V2 -> 2U -> STOM_Version_2U_C -> research/init`

| 디렉토리 | 브랜치 | 역할 |
|----------|--------|------|
| `STOM_V/` | `STOM_Version_2` | 공식 ingress 레인 |
| `STOM_V.wt-2u/` | `STOM_Version_2U` | pyd→py 동기화 레인 |
| `STOM_V.wt-2uc/` | `integration/adopt-cli-v267-into-2uc` | 승격 로그와 transition 이력을 보관하는 archive 레인 |
| **`STOM_V.wt-dev/`** | `STOM_Version_2U_C` | 활성 single-baseline 레인 |
| `STOM_V.wt-lab/` | `research/init` | formal research downstream 레인 |

## 작업 규칙

- 활성 기준선 작업은 `wt-dev`의 `STOM_Version_2U_C`에서 수행한다.
- `wt-2uc`는 archive/transition checkout이므로 같은 시점에 `STOM_Version_2U_C`를 다시 점유하지 않는다.
- CLI 계약, unit test, runtime wiring, result-data 경계는 이제 `2U_C` 기준선에서 유지한다.
- `backtest/graph/`는 보호된 결과 데이터다. git 전파 소스처럼 다루지 않는다.
- retired CLI child-lane flow를 현재 live canonical chain으로 복원하지 않는다.

## 여기서 하는 일

- `2U_C` 기준선 유지 및 후속 동기화
- non-release verifier와 unit test 기준선 유지
- downstream `research/init`으로 넘길 공식 propagation 기준선 유지

## 여기서 하지 않는 일

- 별도 CLI child lane 재도입
- `.pyd` 추론 / release ingress 수행
- `backtest/graph/`를 소스 자산으로 취급
- archive 레인(`wt-2uc`)을 활성 baseline처럼 사용하는 일
