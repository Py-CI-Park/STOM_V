# STOM Project Guidelines (research/init)

> **워크트리 위치**: `STOM_V.wt-lab/`
> **브랜치 역할**: formal downstream research baseline인 `research/init`
> **관련 문서**: `C:/System_Trading/STOM/STOM_V/docs/WORKTREE_STRATEGY.md`, `C:/System_Trading/STOM/STOM_V/docs/UPSTREAM_SYNC_STRATEGY.md`

## Read First

- Top-level lifecycle: `C:/System_Trading/STOM/STOM_V/docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`
- Carry-forward registry: `C:/System_Trading/STOM/STOM_V/docs/CARRY_FORWARD_REGISTRY.md`
- Current cycle status: `C:/System_Trading/STOM/STOM_V/docs/update_log/2026-04-05_v274_v277_cycle_status.md`
- Local baseline note: `C:/System_Trading/STOM/STOM_V.wt-lab/docs/update_log/2026-04-04_v274_v277_research_init_baseline_note.md`

## Branch Gate
- `python scripts/verify_nonrelease_sync.py`
- `python -m pytest tests/unit/ -q`
- canonical base: `CLI_v267`

## 레인 역할

이 워크트리는 generic `research/*` 안내문이 아니라
formal downstream propagation의 마지막 보호 레인인 `research/init` 기준선입니다.
새 연구 브랜치는 여기서 분기할 수 있지만, 공식 전파 체인의 종착점은 `research/init` 자체입니다.

상하류 관계:

- canonical base: `STOM_V.wt-dev/` → `STOM_Version_2U_C_CLI_v267`
- 현재 레인: `STOM_V.wt-lab/` → `research/init`
- 실험 브랜치: 필요 시 `research/*`는 여기서 분기

## 현재 워크트리 토폴로지

| 디렉토리 | 브랜치 | 역할 |
|----------|--------|------|
| `STOM_V/` | `STOM_Version_2` | 공식 ingress 레인 |
| `STOM_V.wt-2u/` | `STOM_Version_2U` | pyd→py 동기화 레인 |
| `STOM_V.wt-2uc/` | `STOM_Version_2U_C` | 커스텀 통합 레인 |
| `STOM_V.wt-dev/` | `STOM_Version_2U_C_CLI_v267` | CLI_v267 레인 |
| **`STOM_V.wt-lab/`** | `research/init` | formal research downstream 레인 |

전파 순서:
`V2 -> 2U -> 2U_C -> CLI_v267 -> research/init`

## 작업 규칙

- 공식 wave는 반드시 `CLI_v267`를 통과한 뒤에만 이 레인으로 들어온다.
- branch-local 연구 문서, carry-forward 보정, 연구 전용 safe subset은 여기서 유지한다.
- `research/init`을 generic scratch branch처럼 취급하지 않는다.
- 새 실험이 필요하면 `research/init`에서 `research/...` 브랜치를 분기하고, baseline은 별도로 보존한다.

## 여기서 하는 일

- formal propagation의 마지막 downstream 기준선 유지
- research 문맥에 맞는 branch-local 보정 반영
- 실험 브랜치의 출발점 제공
- carry-forward 문서와 연구 호환성 유지

## 여기서 하지 않는 일

- release ingress / 2U / 2U_C / CLI_v267 역할을 대신 수행
- generic `research/*` 안내문으로 baseline을 흐리기
- 상위 레인 검증 없이 공식 변경을 직접 흡수
- 실험 브랜치와 baseline 레인을 혼동
