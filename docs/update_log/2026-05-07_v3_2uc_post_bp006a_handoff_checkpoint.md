# V3 / V3U / 2U_C post-BP006A handoff checkpoint

작성일: 2026-05-07 KST
작성 위치: `STOM_Version_2` root orchestration lane
미러 대상: `STOM_Version_2U_C` active custom/backport lane
직전 root HEAD: `6a247d08 BP-006A final guard로 dormant backport cycle을 닫는다`
직전 2U_C HEAD: `f3d48ed0 BP-006A final guard 상태를 2U_C에 미러링한다`

## 1. 이 checkpoint의 목적

이 문서는 BP-006A final guard 이후의 handoff 기준점이다.

현재 상태는 다음과 같다.

1. V3 도입, V3U pyd-free 전환, 2U_C 선별 backport 기본 계획은 완료되어 있다.
2. 추가로 열린 `2UC-V3-BP-006A` cycle도 5 / 5 page 완료되었다.
3. 확장 추적 기준은 `61 / 61 page`, `100.0%` 완료 상태다.
4. 2U_C에는 BP-005A와 BP-006A가 실제 code 변경으로 반영되어 있다.
5. BP-006A는 runtime 연결이 아니라 dormant module 보존 상태로 닫혔다.
6. 다음 code 변경은 새 후보 ID 또는 BP-006A runtime wiring 별도 cycle 없이는 시작하지 않는다.

## 2. 전체 진행률

```text
기존 완료 기준선 [████████████████████] 100.0%   56 / 56 page
BP-006A cycle   [████████████████████] 100.0%    5 /  5 page
확장 전체       [████████████████████] 100.0%   61 / 61 page
남은 page       [--------------------]   0.0%    0 / 61 page
```

## 3. 2U_C에 실제 반영된 code 변경

### 3.1 BP-005A - progressbar 표시 보정

| 항목 | 내용 |
|---|---|
| 후보 ID | `2UC-V3-BP-005A` |
| 2U_C code commit | `f942ed2f BP-005A 프로그레스바 표시 보정을 적용한다` |
| 변경 파일 | `.gitignore`, `ui/ui_update_progressbar.py` |
| 성격 | runtime UI 표시 보정 |
| 주요 내용 | progressbar `setRange()` / `setValue()` 순서 보정, 경과/남은 시간 표시 단축, `backtest/graph/` ignore 보호 |
| 상태 | 완료 |

### 3.2 BP-006A - V3 risk analyzer dormant 보존

| 항목 | 내용 |
|---|---|
| 후보 ID | `2UC-V3-BP-006A` |
| source version | `STOM V3.18` |
| source file | `strategy/analyzer_risk.py` |
| 2U_C code commit | `15467b43 BP-006A risk analyzer를 dormant module로 보존한다` |
| 2U_C whitespace fix commit | `0ea00ea4 BP-006A risk analyzer의 diff check 공백을 보정한다` |
| 변경 파일 | `strategy/__init__.py`, `strategy/analyzer_risk.py` |
| 성격 | dormant module 보존 |
| runtime wiring | 없음 |
| 상태 | 완료 |

## 4. 2U_C에 반영하지 않은 것

아래 항목은 의도적으로 반영하지 않았다.

| 항목 | 상태 | 이유 |
|---|---|---|
| `2UC-V3-BP-001` backtest 대규모 구조 변경 | hold 완료 | V3 backtest 변경 범위가 넓고 2U_C custom / parity 구조와 충돌 가능성 큼 |
| `2UC-V3-BP-003` trade / receiver / REST / websocket 구조 변경 | hold 완료 | V3 LS/API 구조와 2U_C Kiwoom/min/tick/websocket 구조가 1:1 대응하지 않음 |
| LS API 도입 | 제외 | 2U_C는 Kiwoom 유지 lane |
| DB migration | 제외 | 별도 migration spec 전에는 금지 |
| V3 전체 merge | 제외 | micro-candidate 선별 원칙 위반 |
| `STOM_Version_3U_C` 생성 | 제외 | 아직 만들지 않는 원칙 유지 |
| BP-006A runtime wiring | 제외 | 호출 지점, `dict_findex`, array shape, test spec이 별도 필요 |

## 5. 최종 검증 증거

직전 final guard와 post-BP006A preflight에서 확인한 증거:

| 검증 | 결과 |
|---|---|
| root status | clean |
| 2U_C status | clean |
| `python -m py_compile STOM_V.wt-dev/strategy/analyzer_risk.py` | passed |
| root release sync | `release sync preflight passed` |
| 2U_C release sync | `release sync preflight passed` |
| root forbidden runtime artifact | 없음 |
| 2U_C forbidden runtime artifact | 없음 |
| `STOM_Version_3U_C` branch | 없음 |
| worktree map | 6개 worktree 유지, active 2U_C는 `STOM_V.wt-dev` |

## 6. 현재 worktree map

```text
STOM_V/          -> STOM_Version_2       # root orchestration / V2 공식 유지
STOM_V.wt-2u/    -> STOM_Version_2U      # V2 pyd-free 유지
STOM_V.wt-dev/   -> STOM_Version_2U_C    # Kiwoom 유지 custom/backport active lane
STOM_V.wt-3/     -> STOM_Version_3       # V3 official ingress 완료
STOM_V.wt-3u/    -> STOM_Version_3U      # V3 pyd-free 완료
STOM_V.wt-2uc/   -> integration archive  # active lane 아님
```

## 7. 다음 작업 시작 조건

현재는 더 진행할 page가 없다.

다음 작업은 아래 중 하나로만 시작한다.

### 7.1 새 V3 기능 backport 후보

새 후보 ID 예:

```text
2UC-V3-BP-007A
```

필수 조건:

1. V3 source commit / file 확인
2. 2U_C target path 확인
3. LS / DB / pyd / GUI / runtime wiring 위험 조사
4. mock 가능한 검증 단위 정의
5. Page 1 read-only inventory부터 시작

### 7.2 BP-006A runtime wiring 후보

BP-006A의 `AnalyzerRisk`를 실제 runtime에 연결하려면 기존 BP-006A cycle을 다시 열지 말고 별도 후보 ID를 만든다.

예:

```text
2UC-V3-BP-006B
```

필수 조건:

1. 호출 지점 후보
2. `dict_findex` mapping 근거
3. array shape mock
4. 실패 시 fallback 정책
5. unit / smoke test spec

## 8. 금지 사항

계속 금지:

- `git add -A`
- V3 broad merge
- V3U_C branch 생성
- 2U_C에 LS API 직접 도입
- 사전 spec 없는 DB migration
- runtime wiring과 dormant 보존을 한 commit에 섞기
- `_database`, `_log`, `*.db`, `backtest/graph/` commit
- BP-001/BP-003 hold 결론을 새 후보 ID 없이 재개

## 9. 다음 OMX 확인 명령

현재는 완료 상태이므로 다음 명령은 handoff 확인용이다.

```powershell
omx sparkshell powershell -NoProfile -Command "Write-Output 'POST_BP006A_HANDOFF'; git -C C:\System_Trading\STOM\STOM_V status --short; git -C C:\System_Trading\STOM\STOM_V.wt-dev status --short; Write-Output 'ROOT_LOG'; git -C C:\System_Trading\STOM\STOM_V log -10 --oneline; Write-Output 'WTDEV_LOG'; git -C C:\System_Trading\STOM\STOM_V.wt-dev log -12 --oneline; Write-Output 'HANDOFF_DOC'; git -C C:\System_Trading\STOM\STOM_V grep -n -e '61 / 61 page' -e 'BP-005A' -e 'BP-006A' -e '2UC-V3-BP-006B' -- docs/update_log/2026-05-07_v3_2uc_post_bp006a_handoff_checkpoint.md; Write-Output 'VERIFY'; python C:\System_Trading\STOM\STOM_V\scripts\verify_release_sync.py; python C:\System_Trading\STOM\STOM_V\scripts\verify_release_sync.py --root C:\System_Trading\STOM\STOM_V.wt-dev; Write-Output 'WORKTREES'; git -C C:\System_Trading\STOM\STOM_V worktree list"
```

## 10. stop condition

이 checkpoint는 아래 조건이 유지되면 완료다.

```text
확장 전체 61 / 61 page
+ root clean
+ 2U_C clean
+ BP-005A / BP-006A code 반영 기록 존재
+ BP-001 / BP-003 hold 기록 존재
+ release sync 통과
+ runtime artifact 미추적
+ 3U_C 미생성
= handoff 가능
```
