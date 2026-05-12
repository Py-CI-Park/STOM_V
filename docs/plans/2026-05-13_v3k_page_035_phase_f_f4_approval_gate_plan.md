# V3K Page 035 — Phase F F-4 approval gate 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 034 / Phase F F-1/F-2/F-3 pre-ON work |
| f51 단계 | F3 F-4 ON 전환 승인 gate |
| 위험도 | critical |
| 구현 | 본 gate에서는 기본적으로 금지. 승인 조건 확인만 수행 |

---

## 0. 목적

Page035는 Phase F F-4 ON 전환을 실제로 실행하기 전에 승인 조건을 확인하는 gate다. Page034에서 default-OFF adapter, parity baseline, dual gate, rollback proof가 준비되었지만, 이는 ON 승인으로 해석하지 않는다.

---

## 1. F-4 실행 전 필수 조건

| 조건 | 필요 상태 |
| --- | --- |
| 사용자 명시 승인 | 별도 응답으로 “승인” 필요 |
| `V3K_PHASE_F_USER_ACK=1` | 승인 cycle에서만 허용 |
| parity PASS | Page034 parity + 필요 시 실제 sample 확대 |
| rollback audit PASS | `V3K_PHASE_F_DISABLE=1` 즉시 OFF 증거 |
| F1 actual cutover 또는 sidecar 경로 결정 | 운영 DB row를 쓸지 sidecar를 쓸지 확정 필요 |
| `V3K-PHASE-F-ENABLE` registry | ON commit과 함께 별도 기록 |
| 24h monitoring 계획 | ON 후 즉시 감시 가능해야 함 |

---

## 2. 본 page에서 금지

- 사용자 승인 없는 F-4 ON
- 운영 `_database/` write
- DB 파일 commit
- live 주문/청산 판단 연결
- Kiwoom 주문/청산/live runtime 변경
- LS Securities 직접 의존
- `V3K-PHASE-F-ENABLE` registry 선반영

---

## 3. 추천 OMX 명령

```powershell
omx ralph "force: V3K Phase F F-4 ON 전환 approval gate를 1단계만 수행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/update_log/2026-05-13_v3k_phase_f_f123_pre_on_work.md, docs/plans/2026-05-13_v3k_page_035_phase_f_f4_approval_gate_plan.md, docs/CARRY_FORWARD_REGISTRY.md, scripts/audit_v3k_runtime_activation_gap.py를 먼저 읽는다. 본 단계에서는 사용자 명시 승인, V3K_PHASE_F_USER_ACK=1, parity/rollback evidence, F1 actual cutover 또는 sidecar 경로, V3K-PHASE-F-ENABLE registry/24h monitoring 조건을 확인하고 gate 결과만 문서화한다. 승인 조건이 하나라도 없으면 F-4 ON을 실행하지 말고 BLOCK 사유와 다음 승인 조건만 update_log/registry/audit에 기록한다. 운영 _database write, DB 파일 commit, live 주문/청산 연결, Kiwoom live runtime 변경, LS Securities 직접 의존은 금지한다. 완료 시 py_compile, Phase F smoke/parity/rollback audit, audit_v3k_runtime_activation_gap, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB/sidecar artifact status를 통과시키고 한국어 Lore commit한다."
```

---

## 4. 예상 결과

현재 세션에는 사용자 명시 승인과 `V3K_PHASE_F_USER_ACK=1`이 없으므로, 특별한 추가 승인 없이는 F-4는 `blocked-awaiting-user-approval`로 남기는 것이 안전하다.
