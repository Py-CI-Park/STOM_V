# V3 Phase 3 브랜치와 워크트리 생성 기록

- 작성일: 2026-05-05
- 작성 시각: 2026-05-05 16:29:28 +09:00
- 작업 위치: `C:\System_Trading\STOM\STOM_V`
- 생성 브랜치: `STOM_Version_3`
- 생성 워크트리: `C:\System_Trading\STOM\STOM_V.wt-3`
- 관련 계획: `.omx/plans/prd-v3-kickoff-phase-0-11.md`
- 관련 검증: `.omx/plans/test-spec-v3-kickoff-phase-0-11.md`

## 1. 목적

이 문서는 V3 전환 실행 계획의 **Phase 3. `STOM_Version_3` branch와 `STOM_V.wt-3` worktree 생성** 결과를 기록한다.

Phase 3의 목표는 V3 공식 업데이트를 실제 적용하기 전에, V2 기준선과 분리된 V3 공식 업데이트 반영 lane을 준비하는 것이다.

## 2. 실행 전 확인

다음 항목을 확인했다.

```powershell
git status --short --branch
git worktree list
git branch --list STOM_Version_3
Test-Path ..\STOM_V.wt-3
```

확인 결과:

- `STOM_Version_3` 브랜치는 존재하지 않았다.
- `C:\System_Trading\STOM\STOM_V.wt-3` 폴더는 존재하지 않았다.
- `STOM_Version_2` 작업트리는 깨끗했다.
- Phase 2 기준 commit은 `9e8b768531d3c8f5532dce2ed399ff7ba729392e`였다.

## 3. 실행한 명령

```powershell
git branch STOM_Version_3 STOM_Version_2
git worktree add ..\STOM_V.wt-3 STOM_Version_3
```

## 4. 생성 결과

생성 직후 확인된 값은 다음과 같다.

```text
STOM_Version_2: 9e8b768531d3c8f5532dce2ed399ff7ba729392e
STOM_Version_3: 9e8b768531d3c8f5532dce2ed399ff7ba729392e
```

워크트리 목록:

```text
C:/System_Trading/STOM/STOM_V         9e8b7685 [STOM_Version_2]
C:/System_Trading/STOM/STOM_V.wt-2u   09c73048 [STOM_Version_2U]
C:/System_Trading/STOM/STOM_V.wt-2uc  cf0e21c1 [integration/adopt-cli-v267-into-2uc]
C:/System_Trading/STOM/STOM_V.wt-3    9e8b7685 [STOM_Version_3]
C:/System_Trading/STOM/STOM_V.wt-dev  baefe77b [STOM_Version_2U_C]
```

`STOM_V.wt-3` 내부에서 확인한 항목:

- 현재 브랜치: `STOM_Version_3`
- `AGENTS.md` 존재
- `docs/V3_UPDATE_OPERATING_SYSTEM.md` 존재
- `docs/V3_KICKOFF_READINESS_PLAN.md` 존재
- `docs/update_log/2026-05-05_v3_phase2_upstream_source_confirmation.md` 존재

## 5. 현재 워크트리 구성 해석

Phase 3 완료 직후의 핵심 워크트리는 다음과 같다.

| 경로 | 브랜치 | 역할 |
| --- | --- | --- |
| `STOM_V` | `STOM_Version_2` | V2 공식 업데이트 반영 및 V3 전환 제어 기준선 |
| `STOM_V.wt-2u` | `STOM_Version_2U` | V2 pyd-to-py inference lane |
| `STOM_V.wt-dev` | `STOM_Version_2U_C` | 현재 2U_C custom 개발 lane |
| `STOM_V.wt-2uc` | `integration/adopt-cli-v267-into-2uc` | archive/transition lane |
| `STOM_V.wt-3` | `STOM_Version_3` | V3 공식 업데이트 반영 lane |

계획상 Phase 7에서 `STOM_Version_3U`와 `STOM_V.wt-3u`를 만들면, 사용자가 예상한 6개 워크트리 운영 구조에 도달한다.

## 6. 판정

Phase 3은 통과로 판정한다.

근거:

1. 기존 브랜치/경로 충돌 없이 `STOM_Version_3` 브랜치를 생성했다.
2. `STOM_V.wt-3` 워크트리를 정상 생성했다.
3. 새 워크트리에서 `git status --short --branch`가 깨끗하게 출력되었다.
4. 새 워크트리에 V3 운영 문서와 Phase 2 기준 ref 문서가 포함되어 있음을 확인했다.

## 7. 다음 Phase 입력값

다음은 **Phase 4. V3 runtime DB bootstrap**이다.

Phase 4에서 사용할 주요 입력값:

```text
V3 worktree: C:\System_Trading\STOM\STOM_V.wt-3
source DB candidate: C:\System_Trading\STOM\STOM_V\_database
V3 DB target candidate: C:\System_Trading\STOM\STOM_V.wt-3\_database
```

## 8. 주의사항

- 아직 V3 공식 업데이트 파일을 적용하지 않았다.
- 아직 `_database`를 복사하지 않았다.
- 아직 `STOM_Version_3U`를 만들지 않았다.
- `STOM_V.wt-3`는 V3 공식 업데이트 lane이며, 2U_C custom 개발을 직접 섞지 않는다.
- `STOM_Version_3`은 V3 공식 업데이트를 받기 위한 branch이므로, Phase 5 slicing plan 전에는 V3.0~V3.17 업데이트를 합산 적용하지 않는다.