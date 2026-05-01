# STOM Project Guidelines (STOM_Version_2U)

> **워크트리 위치**: `STOM_V.wt-2u/`
> **브랜치 역할**: `STOM_Version_2`의 공식 변경을 py-source 동기화 레인으로 번역하는 `2U`
> **관련 문서**: `C:/System_Trading/STOM/STOM_V/docs/WORKTREE_STRATEGY.md`, `C:/System_Trading/STOM/STOM_V/docs/UPSTREAM_SYNC_STRATEGY.md`

## Read First

- Top-level lifecycle: `C:/System_Trading/STOM/STOM_V/docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`
- Carry-forward registry: `C:/System_Trading/STOM/STOM_V/docs/CARRY_FORWARD_REGISTRY.md`
- Current cycle status: `C:/System_Trading/STOM/STOM_V/docs/update_log/2026-04-30_v279_update_resume_context.md`
- Local baseline note: `C:/System_Trading/STOM/STOM_V.wt-2u/docs/update_log/2026-04-04_v274_v277_2u_baseline_note.md`

## Branch Gate
- `python scripts/verify_nonrelease_sync.py`
- `python -m pytest tests/unit/test_verify_nonrelease_sync.py tests/test_worktree_policy.py -q`

## 커밋 작성 규칙

- 모든 신규 커밋 제목은 한글로 작성한다.
- 모든 신규 커밋 본문은 한글 마크다운으로 작성한다.
- 기본 본문 구조는 `## 배경`, `## 변경 사항`, `## 검증`, 필요 시 `## 주의사항`을 사용한다.
- 영문 타입 접두사 제목은 더 이상 기본 형식으로 사용하지 않는다.
- 정식 버전 기록 커밋처럼 제목이 고정된 경우만 예외로 두고, 그 경우에도 본문은 한글 마크다운으로 작성한다.

## 레인 역할

`STOM_Version_2U`는 공식 ingress 레인인 `STOM_Version_2` 바로 다음 단계입니다.
이 레인의 목적은 release 쪽 `.pyd` 기반 UI 변경을 유지 가능한 py-source 상태로 추론 반영하고,
그 결과를 다음 레인인 `2U_C`로 넘길 수 있게 만드는 것입니다.

핵심 책임:

- `STOM_Version_2`에서 들어온 변경만 받는다.
- `ui_mainwindow.pyd` 변경을 `ui_mainwindow.py`와 주변 py 코드에 추론 반영한다.
- py-source 인터페이스가 release 쪽 공개 인터페이스와 어긋나지 않도록 유지한다.
- gate가 녹색이 된 뒤에만 `STOM_Version_2U_C`로 전파한다.

## 현재 워크트리 토폴로지

| 디렉토리 | 브랜치 | 역할 |
|----------|--------|------|
| `STOM_V/` | `STOM_Version_2` | 공식 ingress 레인 |
| **`STOM_V.wt-2u/`** | `STOM_Version_2U` | pyd→py 동기화 레인 |
| `STOM_V.wt-dev/` | `STOM_Version_2U_C` | 활성 2U_C 통합 레인 |
| `STOM_V.wt-2uc/` | `integration/adopt-cli-v267-into-2uc` | 보관/전환 archive 레인 |

전파 순서:
`V2 -> 2U -> 2U_C`

## 작업 규칙

- 공식 업데이트는 반드시 `STOM_Version_2`에서 받아서 여기로 옮긴다.
- `wt-2u`에서 해결되지 않은 `.pyd`/py 추론 문제를 `wt-dev`의 `STOM_Version_2U_C`로 넘기지 않는다.
- `wt-2uc`는 archive/transition checkout이며 현재 전파 대상이 아니다.
- 자동 생성 스크립트로 `ui_mainwindow.py`를 확정하지 않는다. 추론과 검증이 우선이다.
- docs, scripts, tests는 필요할 때 같이 손볼 수 있지만 이 레인의 핵심 산출물은 py-source 동기화 결과다.

## 여기서 하는 일

- release 변경의 첫 downstream 수신
- `.pyd` 비공개 변경의 py-source 추론 반영
- non-release sync gate 복구
- 다음 레인(`STOM_Version_2U_C`)으로 넘길 버전 단위 정리

## 여기서 하지 않는 일

- release ingress 자체 수행 (`STOM_V/`에서 수행)
- `2U_C` 커스텀 정책 결정
- CLI_v267 child-lane 복원
- research/init 실험/하위 연구 브랜치 관리
- V3 업데이트 또는 V3 마이그레이션
