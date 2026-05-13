# V3K Phase F F-4 ON approval prep

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 050 |
| source | Page035 Phase F F-4 approval gate, Page048 approval gate selection |
| marker | `PHASE_F_F4_ON_APPROVAL_PREP` |
| 상태 | `completed-approval-prep` |
| next candidate | `phase-f-f4-on-await-user-approval` |

---

## 1. 요약

Phase F F-4 ON은 V3 analyzer output을 live formula/strategy consumption 후보로 올리는 critical gate이다. 이번 Page050에서는 actual ON을 하지 않고, 사용자가 승인해야 할 조건과 rollback/monitoring 조건을 명확한 감사 대상으로 고정했다.

No ON execution: Phase F F-4 ON, `V3K_PHASE_F_USER_ACK=1`, `V3K-PHASE-F-ENABLE` registry, Kiwoom live runtime, 운영 `_database/` write, DB 파일 commit, `.omx/reports` raw artifact commit, live order/exit rule 연결은 수행하지 않았다.

---

## 2. 준비된 근거

| 근거 | 설명 |
| --- | --- |
| `scripts/smoke_v3k_phase_f_default_off.py` | default/env-only/db-only/dual-gate/rollback matrix 검증 |
| `scripts/backtest_v3k_phase_f_parity.py` | synthetic pre-ON parity baseline |
| `scripts/audit_v3k_phase_f_rollback.py` | rollback flag priority 검증 |
| `strategy/v3k_analyzer_adapter.py` | Phase F env+DB dual gate helper |
| `strategy/v3k_formula_facade.py` | Phase F formula candidate builder |
| `scripts/audit_v3k_verify_1a.py` | Kiwoom/runtime untouched, default-OFF, LS dependency exclusion, artifact guard |

---

## 3. Prompt-to-artifact checklist

| 요구사항 | concrete evidence | 현재 판정 |
| --- | --- | --- |
| LS Securities 직접 의존 금지 | VERIFY-1A, LS marker audit | 유지 |
| Kiwoom 주문/청산/live runtime 유지 | VERIFY-1A | 유지 |
| Phase F feature flag default-OFF | smoke + VERIFY-1A | 유지 |
| env-only/db-only 단독 ON 금지 | `smoke_v3k_phase_f_default_off.py` | 유지 |
| rollback flag 우선 | `audit_v3k_phase_f_rollback.py` | 유지 |
| parity baseline | `backtest_v3k_phase_f_parity.py --sample-period 7d` | actual ON 전 필수 |
| USER_ACK 없는 ON 금지 | Page050 + VERIFY-1B guard | `V3K_PHASE_F_USER_ACK=1` 필요 |
| enable registry 없는 ON 금지 | Page050 + runtime activation gap | `V3K-PHASE-F-ENABLE` 필요 |
| 운영 DB write 금지 | audit suite artifact guard | 유지 |

---

## 4. Actual ON 전 사용자 결정지

1. `Phase F F-4 ON` gate 명시 승인 여부
2. USER_ACK 형태: env, update_log, registry 중 어떤 것을 정식 승인 기록으로 삼을지 결정
3. enable registry 형태: `V3K-PHASE-F-ENABLE` 기록과 rollback pair 정의
4. monitoring 범위: 24h monitoring, error budget, fallback trigger 정의
5. rollback 경로: `V3K_PHASE_F_DISABLE=1`, registry 제거, default-OFF fallback 확인
6. F1 DB cutover/GUI sidecar source-of-truth와의 연결 여부 결정

---

## 5. 남은 상태

현재 다음 후보는 `phase-f-f4-on-await-user-approval`이다. 사용자가 위 gate를 명시 승인하기 전까지 actual ON은 수행하지 않는다.

Directive: `PHASE_F_F4_ON_APPROVAL_PREP`는 승인 준비 기록이며 Phase F ON, USER_ACK 생성, enable registry 생성, DB cutover, Kiwoom live runtime 변경으로 해석하면 안 된다.
