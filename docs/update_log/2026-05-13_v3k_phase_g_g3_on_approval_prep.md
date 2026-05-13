# V3K Phase G G-3 ON approval prep

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 051 |
| source | Page039 Phase G G-2 parity/benchmark work, Page040 Phase G G-3 approval gate, Page050 Phase F F-4 ON approval prep |
| marker | `PHASE_G_G3_ON_APPROVAL_PREP` |
| 상태 | `completed-approval-prep` |
| next candidate | `phase-g-g3-on-await-user-approval` |

---

## 1. 요약

Phase G G-3 ON은 V3 microstructure engine output을 runtime consumption 후보로 올리는 critical gate이다. 이번 Page051에서는 actual ON을 하지 않고, 사용자가 승인해야 할 조건과 rollback/monitoring 조건을 명확한 감사 대상으로 고정했다.

No ON execution: Phase G G-3 ON, `V3K_PHASE_G_USER_ACK=1`, `V3K-PHASE-G-ENABLE` registry, Kiwoom live runtime, 운영 `_database/` write, DB 파일 commit, `.omx/reports` raw artifact commit, live order/exit rule 연결은 수행하지 않았다.

---

## 2. 준비된 근거

| 근거 | 설명 |
| --- | --- |
| `strategy/v3k_microstructure_engine.py` | Phase G microstructure engine default-OFF staging |
| `scripts/smoke_v3k_phase_g_engine_unit.py` | default-OFF/unit behavior smoke |
| `scripts/backtest_v3k_phase_g_parity.py` | synthetic/caller-owned parity proof |
| `scripts/benchmark_v3k_phase_g_engine.py` | synthetic benchmark proof |
| `scripts/audit_v3k_phase_g_ls_excise.py` | LS Securities/broker runtime dependency marker 금지 |
| `scripts/summarize_v3k_phase_g_evidence.py` | raw `.omx/reports`는 local ignored artifact로 유지 |

---

## 3. Prompt-to-artifact checklist

| 요구사항 | concrete evidence | 현재 판정 |
| --- | --- | --- |
| LS Securities 직접 의존 금지 | Phase G LS excise audit, VERIFY-1A | 유지 |
| Kiwoom 주문/청산/live runtime 유지 | VERIFY-1A | 유지 |
| Phase G feature flag default-OFF | unit smoke + VERIFY-1A | 유지 |
| parity baseline | `backtest_v3k_phase_g_parity.py` | actual ON 전 필수 |
| benchmark baseline | `benchmark_v3k_phase_g_engine.py` | actual ON 전 필수 |
| USER_ACK 없는 ON 금지 | Page051 + VERIFY-1B guard | `V3K_PHASE_G_USER_ACK=1` 필요 |
| enable registry 없는 ON 금지 | Page051 + runtime activation gap | `V3K-PHASE-G-ENABLE` 필요 |
| rollback/kill switch 없는 ON 금지 | Page051 + approval checklist | `V3K_PHASE_G_DISABLE=1` 또는 동등 rollback 필요 |
| 운영 DB write 금지 | audit suite artifact guard | 유지 |
| raw `.omx/reports` commit 금지 | summarizer + artifact guard | 유지 |

---

## 4. Actual ON 전 사용자 결정지

1. `Phase G G-3 ON` gate 명시 승인 여부
2. USER_ACK 형태: env, update_log, registry 중 어떤 것을 정식 승인 기록으로 삼을지 결정
3. enable registry 형태: `V3K-PHASE-G-ENABLE` 기록과 rollback pair 정의
4. rollback/kill switch 형태: `V3K_PHASE_G_DISABLE=1`, registry removal, feature flag default-OFF fallback 중 운영 기준 결정
5. monitoring 범위: 24h monitoring, error budget, fallback trigger 정의
6. live order/exit rule consumption 연결 여부: 연결 시 별도 critical gate로 분리

---

## 5. 남은 상태

현재 다음 후보는 `phase-g-g3-on-await-user-approval`이다. 사용자가 위 gate를 명시 승인하기 전까지 actual ON은 수행하지 않는다.

Directive: `PHASE_G_G3_ON_APPROVAL_PREP`는 승인 준비 기록이며 Phase G ON, USER_ACK 생성, enable registry 생성, DB cutover, Kiwoom live runtime 변경, live order/exit rule 연결로 해석하면 안 된다.
