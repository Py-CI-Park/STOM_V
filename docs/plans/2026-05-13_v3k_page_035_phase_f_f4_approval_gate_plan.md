# V3K Page 035 — Phase F F-4 approval gate 완료 기록

| 항목 | 값 |
| --- | --- |
| 작성/갱신일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 034 / Phase F F-1·F-2·F-3 pre-ON work |
| 현재 page | Page 035 / Phase F F-4 approval gate |
| 다음 page | Page 036 / Phase G G-1 pre-ralplan |
| f51 단계 | C2 이후 F-4 ON 전환 승인 gate, 다음 C3 Phase G deliberate planning |
| 위험도 | critical |
| 결과 | `blocked-awaiting-user-approval` |
| 구현 범위 | 실제 ON 없음. 승인 조건·미충족 사유·다음 조건만 문서화 |

---

## 0. 목적

Page035의 목적은 Page034에서 준비된 Phase F analyzer output pre-ON 증거를 실제 운영/전략 결정에 연결하기 전에, F-4 ON 전환 조건이 충족되었는지 확인하는 것이다. 이번 cycle에서는 사용자 명시 승인, `V3K_PHASE_F_USER_ACK=1`, F1 actual cutover/sidecar 경로, `V3K-PHASE-F-ENABLE` registry, 24h monitoring 계획이 모두 갖춰지지 않았으므로 F-4는 실행하지 않는다.

중요: Page034의 default-OFF adapter, parity baseline, dual gate, rollback proof는 “ON 준비 증거”이지 “ON 승인”이 아니다.

---

## 1. F-4 실행 전 필수 조건과 현재 판정

| 조건 | 필요 상태 | 현재 판정 | 조치 |
| --- | --- | --- | --- |
| 사용자 명시 승인 | 별도 응답으로 “F-4 ON 승인” 필요 | BLOCK | 승인 전 ON 금지 |
| `V3K_PHASE_F_USER_ACK=1` | 승인 cycle에서만 허용 | BLOCK | 환경변수 미설정 유지 |
| parity PASS | Page034 synthetic parity PASS, 실제 sample 확장 필요 | PARTIAL PASS | ON 직전 재검증 필요 |
| rollback audit PASS | `V3K_PHASE_F_DISABLE=1` 우선 OFF 증거 | PASS | rollback invariant 유지 |
| F1 actual cutover 또는 sidecar 경로 결정 | 운영 DB row 또는 sidecar source-of-truth 결정 필요 | BLOCK | 별도 승인·경로 결정 필요 |
| `V3K-PHASE-F-ENABLE` registry | ON commit과 함께 별도 기록 | BLOCK | 이번 commit에서 생성 금지 |
| 24h monitoring 계획 | ON 직후 즉시 감시 가능해야 함 | BLOCK | 승인 cycle에서 계획·담당·rollback 조건 확정 |

---

## 2. 이번 page에서 실제로 수행한 결정

1. F-4 ON 전환은 `blocked-awaiting-user-approval`로 고정한다.
2. `V3K-PHASE-F-ENABLE` registry는 추가하지 않는다.
3. `V3K_PHASE_F_ENABLE`, `phase_f_analyzer_strategy.enabled` dual gate는 Page034 구현 상태를 보존하지만, 운영 runtime 연결은 하지 않는다.
4. `V3K_PHASE_F_DISABLE=1` rollback 우선권은 유지한다.
5. 다음 안전 단계는 Phase G microstructure engine 구현이 아니라 `Phase G G-1 pre-ralplan` 합의 재실행으로 넘긴다.

---

## 3. 금지 사항

- 사용자 명시 승인 없는 F-4 ON
- `V3K_PHASE_F_USER_ACK=1`을 임의 설정한 검증
- 운영 `_database/` write
- DB 파일 commit
- `V3K-PHASE-F-ENABLE` registry 선반영
- live 주문/청산/전략 runtime 연결
- Kiwoom 주문/청산/live runtime 변경
- LS Securities REST/TR/REAL 직접 의존 추가

---

## 4. 검증 기대값

Page035는 코드 활성화가 아니라 gate 문서화 단계이므로 다음 검증이 통과해야 한다.

- `scripts/audit_v3k_runtime_activation_gap.py`가 다음 후보를 `phase-g-g1-pre-ralplan`로 보고한다.
- `phase-f-f4-approval-gate`는 `blocked-awaiting-user-approval` 상태로 남는다.
- `audit_v3k_verify_1b_closure.py`는 F-4 ON 전환이 사용자 승인 필요 항목임을 계속 출력한다.
- 운영 `_database/`, `_database_v3k_shadow/`, `_log/`, backup, DB 파일, sidecar artifact 상태가 깨끗해야 한다.
- `verify_nonrelease_sync.py`가 2U_C non-release custom lane invariant를 통과해야 한다.

---

## 5. 완료 결과

이번 Page035에서는 F-4 ON 전환을 수행하지 않았다. Page034에서 준비한 Phase F analyzer output proof는 유지하지만, 실제 전략 결정·runtime hook·운영 설정 source-of-truth 연결은 사용자 승인 전까지 모두 보류한다.

최종 상태:

```text
phase-f-f4-approval-gate = blocked-awaiting-user-approval
next candidate = phase-g-g1-pre-ralplan
V3K-PHASE-F-ENABLE registry = not created
operating database write = none
live Kiwoom runtime change = none
LS direct dependency = none
```

---

## 6. 다음 OMX 명령

다음 단계는 Phase G G-1 구현이 아니라 고위험 microstructure engine 이식 전 합의 재실행이다.

```powershell
omx ralplan --deliberate "V3K F4 Phase G G-1 (V3 microstructure engine 2U_C 이식, docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md §C T01–T05)을 실행하기 전에 Planner/Architect/Critic 합의를 재실행한다. LG1(LS 의존 자동 제거) / LG2(Kiwoom OPT* data shape mapping 정본화) / LG3(parity ±15%) / LG4(성능 ±20%) / LG5(ON 단일 commit + 사용자 승인) invariant가 충분한지 pre-mortem 3 시나리오(LS 의존 잔존 / Kiwoom data shape mismatch / parity 한계 이탈)와 expanded test plan을 추가 검증한다. V3 engine inventory (T01)와 Kiwoom OPT* mapping 표 (T02)는 G-1의 핵심 산출물임을 명시한다. 2U_C 검증에서는 verify_release_sync.py가 아니라 scripts/verify_nonrelease_sync.py를 사용한다."
```

만약 로컬 `omx ralplan` 서브커맨드가 지원되지 않으면 Codex 대화창에서 동일 내용을 `$ralplan --deliberate ...`로 호출한다.
