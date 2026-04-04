# STOM Project Guidelines (STOM_Version_2U_C_CLI_v267)

> **워크트리 위치**: `STOM_V.wt-dev/`
> **브랜치 역할**: `2U_C`를 부모로 받아 CLI 계약과 운영 호환성을 유지하는 `CLI_v267` 레인
> **관련 문서**: `C:/System_Trading/STOM/STOM_V/docs/WORKTREE_STRATEGY.md`, `C:/System_Trading/STOM/STOM_V/docs/UPSTREAM_SYNC_STRATEGY.md`

## Read First

- Top-level lifecycle: `C:/System_Trading/STOM/STOM_V/docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`
- Carry-forward registry: `C:/System_Trading/STOM/STOM_V/docs/CARRY_FORWARD_REGISTRY.md`
- Current cycle status: `C:/System_Trading/STOM/STOM_V/docs/update_log/2026-04-05_v274_v277_cycle_status.md`
- Local baseline note: `C:/System_Trading/STOM/STOM_V.wt-dev/docs/update_log/2026-04-04_v274_v277_cli_v267_baseline_note.md`

## Branch Gate
- `python scripts/verify_nonrelease_sync.py`
- `python -m pytest tests/unit/ -q`
- `backtest/graph/` is protected result data

## 커밋 작성 규칙

- 모든 신규 커밋 제목은 한글로 작성한다.
- 모든 신규 커밋 본문은 한글 마크다운으로 작성한다.
- 기본 본문 구조는 `## 배경`, `## 변경 사항`, `## 검증`, 필요 시 `## 주의사항`을 사용한다.
- 영문 타입 접두사 제목은 더 이상 기본 형식으로 사용하지 않는다.
- 정식 버전 기록 커밋처럼 제목이 고정된 경우만 예외로 두고, 그 경우에도 본문은 한글 마크다운으로 작성한다.

## 레인 역할

`STOM_Version_2U_C_CLI_v267`는 `STOM_Version_2U_C`를 부모로 받는 downstream CLI 레인입니다.
이 레인의 기준 부모는 `2U_C`이며, 공식 전파 체인에서는 `research/init` 바로 앞 단계입니다.
이 문서는 retired `CLI_v258`이 아니라 현재 살아 있는 `CLI_v267` 기준으로 읽어야 합니다.

상하류 관계:

- 상위 입력 / canonical parent: `STOM_V.wt-2uc/` → `STOM_Version_2U_C`
- 현재 레인: `STOM_V.wt-dev/` → `STOM_Version_2U_C_CLI_v267`
- 하위 전파: `STOM_V.wt-lab/` → `research/init`

## 현재 워크트리 토폴로지

| 디렉토리 | 브랜치 | 역할 |
|----------|--------|------|
| `STOM_V/` | `STOM_Version_2` | 공식 ingress 레인 |
| `STOM_V.wt-2u/` | `STOM_Version_2U` | pyd→py 동기화 레인 |
| `STOM_V.wt-2uc/` | `STOM_Version_2U_C` | 커스텀 통합 레인 |
| **`STOM_V.wt-dev/`** | `STOM_Version_2U_C_CLI_v267` | CLI_v267 레인 |
| `STOM_V.wt-lab/` | `research/init` | formal research downstream 레인 |

전파 순서:
`V2 -> 2U -> 2U_C -> CLI_v267 -> research/init`

## 작업 규칙

- 공식 wave는 반드시 `2U_C`에서 한 단계씩 받아온다.
- CLI 계약, unit test, runtime wiring, result-data 경계는 이 레인에서 보존한다.
- `backtest/graph/`는 보호된 결과 데이터다. git 전파 소스처럼 다루지 않는다.
- `CLI_v258` 명칭, 브랜치, 작업 흐름은 더 이상 이 레인의 기준이 아니다.

## 여기서 하는 일

- `2U_C` 기반 CLI 호환성 유지
- CLI 관련 테스트와 branch-local verifier 유지
- downstream `research/init`으로 넘길 formal non-release 기준선 유지
- feature 작업이 필요하면 `CLI_v267` 기준으로 분기

## 여기서 하지 않는 일

- `2U_C` 홈 레인처럼 동작
- `.pyd` 추론 / release ingress 수행
- `backtest/graph/`를 소스 자산으로 취급
- research lane 문서/실험 규칙을 대신 소유
