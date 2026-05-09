# V3 / V3U / 2U_C backport final handoff checkpoint

작성일: 2026-05-07 KST  
작성 위치: `STOM_Version_2` root orchestration lane  
미러 대상: `STOM_Version_2U_C` active custom/backport lane  
직전 root HEAD: `bd0033c0 BP-001과 BP-003 재평가 cycle을 final guard로 닫는다`  
직전 2U_C HEAD: `766bda63 BP-001과 BP-003 final guard 상태를 2U_C 미러에 남긴다`

## 1. 이 checkpoint의 목적

이 문서는 V3 / V3U / 2U_C 전환 및 선별 backport 흐름이 현재 어디까지 왔는지 다음 작업자가 즉시 판단할 수 있도록 남기는 최종 handoff checkpoint이다.

중요한 결론은 다음과 같다.

1. 최초 V3 전략 kick-off에서 정의한 주요 흐름은 완료되었다.
2. `STOM_Version_3` 공식 ingress, `STOM_Version_3U` pyd-free 전환, 3U parity audit은 완료 상태다.
3. `STOM_Version_2U_C`는 V3 branch가 아니라 V2/Kiwoom 유지 custom lane이며, V3 기능은 broker-neutral 후보만 선별 backport한다.
4. BP-005A는 적용 및 검증이 완료되었다.
5. BP-001/BP-003은 이번 재평가 cycle에서 추가 적용하지 않고 hold 완료로 닫았다.
6. 현재 전체 계획은 `56 / 56 page`, 즉 `100.0%` 완료 상태다.
7. 남은 작업은 코드 적용이 아니라 새 후보가 생길 때 별도 후보 ID와 새 read-only cycle을 시작하는 것이다.

## 2. 사용자 요청 흐름 요약

이번 checkpoint는 다음 사용자 요청 흐름을 보존하기 위해 작성한다.

- V2에서 V3로 넘어가면서 Kiwoom API에서 LS API로 바뀌는 큰 변화가 있으므로 branch/worktree 전략을 명확히 나누고 싶다는 요청이 있었다.
- `STOM_Version_3`는 `STOM_Version_2`에서 공식 V3 update lane으로 만들고, upstream `_update.txt` 기준으로 정규 반영하는 방향을 검토했다.
- `STOM_Version_3U`는 `STOM_Version_3`에서 분기하되, pyd 제거 구현은 기존 `STOM_Version_2U`의 pyd-to-py 추론 산출물과 검증 도구를 적극 참고하는 방향으로 정했다.
- `STOM_Version_3U_C`는 아직 만들지 않는 원칙을 세웠다.
- `STOM_Version_2U_C`는 계속 Kiwoom 유지 custom lane으로 운영하되, V3 기능 중 LS API / DB migration / pyd 결합이 없는 후보만 선별 backport하기로 했다.
- 각 단계는 문서화하고, root와 active 2U_C에 commit으로 남기며, 진행률과 다음 OMX 명령을 계속 안내하는 방식으로 운영하기로 했다.

## 3. 현재 worktree 지도

```text
STOM_V/          -> STOM_Version_2       # V2 공식 유지 / root orchestration / 문서 추적
STOM_V.wt-2u/    -> STOM_Version_2U      # V2 pyd-free 유지
STOM_V.wt-dev/   -> STOM_Version_2U_C    # Kiwoom 유지 custom/backport active lane
STOM_V.wt-3/     -> STOM_Version_3       # V3 공식 ingress 완료
STOM_V.wt-3u/    -> STOM_Version_3U      # V3 pyd-free 완료
STOM_V.wt-2uc/   -> integration archive  # active lane 아님
```

주의:

- `STOM_Version_3U_C`는 아직 만들지 않는다.
- V3 공식 lane에는 upstream `.pyd`를 보존한다.
- V3 pyd 제거는 `STOM_Version_3U`에서만 수행한다.
- 2U_C에 V3 기능을 반영할 때는 Kiwoom 유지 보정과 LS 의존성 제외 기록이 필수다.
- `_database`, `_log`, `*.db`, `backtest/graph/`는 commit하지 않는다.

## 4. 전체 진행률

```text
전체        [████████████████████] 100.0%   56 / 56 page
V3 본편     [████████████████████] 100.0%   11 / 11 page
백포트      [████████████████████] 100.0%   30 / 30 page
재정렬      [████████████████████] 100.0%    5 /  5 page
BP-005A     [████████████████████] 100.0%    5 /  5 page
BP-001/003 [████████████████████] 100.0%    5 /  5 page
남은 page   [--------------------]   0.0%    0 /  0 page
```

계산 기준:

```text
V3 본편 11 page
+ 완료된 backport cycle 30 page
+ 재정렬 cycle 5 page
+ BP-005A 적용 cycle 5 page
+ BP-001/BP-003 read-only 재평가 cycle 5 page
= 56 page 완료
```

## 5. 현재 단계 세부 상태

현재 단계는 별도 기능 적용 page가 아니라 `handoff checkpoint`이다.

```text
handoff checkpoint [████████████████████] 100.0%   1 / 1 step
```

| Step | 내용 | 상태 |
|---:|---|---|
| 1 | root / 2U_C clean 확인 | 완료 |
| 2 | 최근 HEAD와 문서 진행률 확인 | 완료 |
| 3 | 전체 완료 상태를 새 checkpoint 문서로 고정 | 완료 |
| 4 | root와 2U_C mirror commit 준비 | 진행 중 |
| 5 | commit 후 최종 guard 실행 | 예정 |

## 6. 완료된 주요 흐름

| 흐름 | 결과 | 현재 판단 |
|---|---|---|
| V3 전략 kick-off | 완료 | 6개 worktree 운영 원칙 확정 |
| V3 공식 ingress | 완료 | upstream V3 lane 보존 |
| V3U pyd-free 전환 | 완료 | 2U 추론 산출물과 검증 도구를 참고해 V3 구조에 맞게 이식 |
| 3U parity audit | 완료 | pyd 제거 lane 원칙 유지 |
| 2U_C backport queue | 완료 | broker-neutral 후보만 선별 |
| BP-005A | 완료 | 최소 patch 적용 및 검증 완료 |
| BP-001 | hold 완료 | 이번 cycle 적용 없음 |
| BP-003 | hold 완료 | 이번 cycle 적용 후보 미선정 |

## 7. 남은 작업과 재개 조건

현재 남은 page는 없다.

다만 다음 개발을 시작하려면 아래 조건 중 하나가 필요하다.

1. 새 V3 기능 후보가 식별된다.
2. 그 후보가 LS API / DB migration / pyd 결합 없이 Kiwoom 유지 2U_C에 이식 가능한지 read-only로 확인된다.
3. 후보 ID를 새로 부여한다. 예: `2UC-V3-BP-006A`.
4. 새 후보는 기존 56 page denominator에 억지로 끼우지 않고, 별도 cycle denominator로 시작한다.
5. Page 1에서는 반드시 V3 source commit, 2U_C target file, 제외할 LS 의존성, mock 가능한 검증 단위를 기록한다.

즉, 다음 cycle의 안전한 시작 형태는 다음과 같다.

```text
새 후보 ID 생성
-> read-only Page 1
-> 적용 가능성 판단 Page 2
-> 최소 patch 또는 hold Page 3
-> 문서 동기화 Page 4
-> final guard Page 5
```

## 8. 금지 사항

아래 항목은 계속 금지한다.

- `git add -A` 사용
- V3U_C branch 생성
- V3 공식 lane에서 `.pyd` 제거
- 2U_C에 LS API 전제 변경을 직접 반영
- DB schema migration을 사전 spec 없이 반영
- `_database`, `_log`, `*.db`, `backtest/graph/` commit
- 파일 단위 cherry-pick으로 V3 변경을 크게 가져오는 방식
- BP-001/BP-003 hold 결론을 새 근거 없이 재개하는 방식

## 9. handoff 후 다음 작업자가 읽을 문서 순서

1. `docs/update_log/2026-05-07_v3_2uc_backport_final_handoff_checkpoint.md`
2. `docs/update_log/2026-05-06_v3_2uc_backport_midpoint_checkpoint.md`
3. `docs/update_log/2026-05-06_v3_v3u_final_handoff.md`
4. `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md`
5. `docs/update_log/2026-05-06_2uc_v3_backport_phase11_final_decision.md`
6. `docs/V3_UPDATE_OPERATING_SYSTEM.md`
7. `docs/WORKTREE_STRATEGY.md`
8. `docs/CARRY_FORWARD_REGISTRY.md`

## 10. 다음 OMX 확인 명령

다음 작업자는 아래 명령으로 현재 상태를 먼저 확인한다.

```powershell
omx sparkshell powershell -NoProfile -Command "Write-Output 'ROOT_STATUS'; git -C C:\System_Trading\STOM\STOM_V status --short; Write-Output 'WTDEV_STATUS'; git -C C:\System_Trading\STOM\STOM_V.wt-dev status --short; Write-Output 'ROOT_LOG'; git -C C:\System_Trading\STOM\STOM_V log -8 --oneline; Write-Output 'WTDEV_LOG'; git -C C:\System_Trading\STOM\STOM_V.wt-dev log -8 --oneline; Write-Output 'HANDOFF_DOC'; git -C C:\System_Trading\STOM\STOM_V grep -n -e '56 / 56 page' -e 'handoff checkpoint' -e '새 후보 ID' -- docs/update_log/2026-05-07_v3_2uc_backport_final_handoff_checkpoint.md; Write-Output 'WORKTREES'; git -C C:\System_Trading\STOM\STOM_V worktree list"
```

## 11. 최종 판단

현재는 더 진행할 code 적용 page가 없다.

안전한 다음 단계는 다음 둘 중 하나다.

1. **종료 / handoff 유지**: 현재 완료 상태를 기준으로 다음 명시적 후보 요청을 기다린다.
2. **새 후보 탐색**: V3와 2U_C를 다시 read-only 비교해 새 후보 ID를 만든 뒤, 기존 BP-001/BP-003이 아닌 새 cycle로 시작한다.

이 checkpoint의 stop condition은 다음과 같다.

```text
root clean
+ 2U_C clean
+ release sync 통과
+ runtime artifact 미추적
+ 3U_C 미생성
+ 전체 진행률 56 / 56 page 유지
= handoff 가능
```
