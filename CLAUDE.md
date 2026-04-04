# STOM Project Guidelines (STOM_Version_2U_C)

> **워크트리 위치**: `STOM_V.wt-2uc/`
> **브랜치 역할**: `2U` 결과를 커스텀 통합 규칙으로 정리하는 `2U_C` home lane
> **관련 문서**: `C:/System_Trading/STOM/STOM_V/docs/WORKTREE_STRATEGY.md`, `C:/System_Trading/STOM/STOM_V/docs/UPSTREAM_SYNC_STRATEGY.md`

## Read First

- Top-level lifecycle: `C:/System_Trading/STOM/STOM_V/docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`
- Carry-forward registry: `C:/System_Trading/STOM/STOM_V/docs/CARRY_FORWARD_REGISTRY.md`
- Current cycle status: `C:/System_Trading/STOM/STOM_V/docs/update_log/2026-04-05_v274_v277_cycle_status.md`
- Local baseline note: `C:/System_Trading/STOM/STOM_V.wt-2uc/docs/update_log/2026-04-04_v274_v277_2uc_baseline_note.md`

## Branch Gate
- `python scripts/verify_nonrelease_sync.py`
- `python -m pytest tests/unit/test_webcrawling_contract_text.py tests/unit/test_telegram_contract_text.py tests/unit/test_ui_runtime_wiring.py tests/unit/test_verify_nonrelease_sync.py tests/unit/test_webcrawling_network_noise.py tests/test_worktree_policy.py -q`

## 커밋 작성 규칙

- 모든 신규 커밋 제목은 한글로 작성한다.
- 모든 신규 커밋 본문은 한글 마크다운으로 작성한다.
- 기본 본문 구조는 `## 배경`, `## 변경 사항`, `## 검증`, 필요 시 `## 주의사항`을 사용한다.
- 영문 타입 접두사 제목은 더 이상 기본 형식으로 사용하지 않는다.
- 정식 버전 기록 커밋처럼 제목이 고정된 경우만 예외로 두고, 그 경우에도 본문은 한글 마크다운으로 작성한다.

## 레인 역할

`STOM_Version_2U_C`는 `STOM_Version_2U`에서 내려온 변경을
커스텀 보정 규칙과 non-release 계약에 맞게 통합하는 레인입니다.
이 레인은 `wt-dev`의 CLI_v267 레인보다 상위이며, `wt-dev`를 홈 브랜치처럼 다루면 안 됩니다.

상하류 관계:

- 상위 입력: `STOM_V.wt-2u/` → `STOM_Version_2U`
- 현재 레인: `STOM_V.wt-2uc/` → `STOM_Version_2U_C`
- 하위 전파: `STOM_V.wt-dev/` → `STOM_Version_2U_C_CLI_v267`

## 현재 워크트리 토폴로지

| 디렉토리 | 브랜치 | 역할 |
|----------|--------|------|
| `STOM_V/` | `STOM_Version_2` | 공식 ingress 레인 |
| `STOM_V.wt-2u/` | `STOM_Version_2U` | pyd→py 동기화 레인 |
| **`STOM_V.wt-2uc/`** | `STOM_Version_2U_C` | 커스텀 통합 레인 |
| `STOM_V.wt-dev/` | `STOM_Version_2U_C_CLI_v267` | CLI_v267 레인 |
| `STOM_V.wt-lab/` | `research/init` | formal research downstream 레인 |

전파 순서:
`V2 -> 2U -> 2U_C -> CLI_v267 -> research/init`

## 작업 규칙

- 공식 wave는 반드시 `2U`에서 받아서 이 레인으로 통합한다.
- 커스텀 보정은 여기서 결정하고, 그 결과를 CLI_v267로 넘긴다.
- `wt-dev`는 downstream CLI 레인이다. `STOM_Version_2U_C`의 홈 워크트리가 아니다.
- retired `CLI_v258` 기준 설명이나 경로를 다시 사용하지 않는다.

## 여기서 하는 일

- `2U` 결과를 커스텀 정책에 맞게 흡수
- non-release verifier가 요구하는 branch-local 계약 유지
- CLI 전파 전에 충돌/보정/carry-forward 여부를 정리
- UI/utility 쪽 custom correction 유지

## 여기서 하지 않는 일

- release ingress 수행
- `.pyd` 추론 자체를 주 레인처럼 처리
- `CLI_v267` 전용 운영 규칙을 이 레인과 혼동
- `research/init` 실험 운영을 대신 수행
