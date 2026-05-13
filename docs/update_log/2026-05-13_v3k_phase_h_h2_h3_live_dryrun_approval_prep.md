# V3K Phase H H-2/H-3 Kiwoom live dry-run approval prep

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 052 |
| source | Page026 Phase H H-1 contract-only hook, Page032 Phase H H-2/H-3 approval gate, Page051 Phase G G-3 ON approval prep |
| marker | `PHASE_H_H2_H3_LIVE_DRYRUN_APPROVAL_PREP` |
| 상태 | `completed-approval-prep` |
| next candidate | `phase-h-h2-h3-live-dryrun-await-user-approval` |

---

## 1. 요약

Phase H H-2/H-3는 Kiwoom live runtime에 가장 가까운 gate다. 이번 Page052에서는 actual live dry-run을 하지 않고, KHOPENAPI 환경, 사용자 승인, USER_ACK, zero-order evidence, rollback, monitoring 조건을 명확한 감사 대상으로 고정했다.

No live dry-run execution: KHOPENAPI connect/login, Phase H H-2 live dry-run, Phase H H-3 ON, `V3K_PHASE_H_USER_ACK=1`, Kiwoom 주문/청산/live runtime 변경, 운영 `_database/` write, DB 파일 commit, `.omx/reports` raw artifact commit, live order/exit rule 연결은 수행하지 않았다.

---

## 2. 준비된 근거

| 근거 | 설명 |
| --- | --- |
| `strategy/v3k_kiwoom_dryrun_hook.py` | H-1 contract-only dry-run hook |
| `scripts/smoke_v3k_phase_h_hook_unit.py` | default-OFF, login-only registration, idempotent diagnostic, sentinel guard 검증 |
| `scripts/audit_v3k_phase_h_env_check.py --stdout` | KHOPENAPI 환경 유무를 보고하되 live connect를 시도하지 않는 sentinel audit |
| `scripts/audit_v3k_verify_1a.py --base 57496d24` | Kiwoom 주문/청산/live runtime 보존, LS Securities 직접 의존 금지, artifact guard |
| `scripts/run_v3k_audit_suite.py` | 전체 V3K audit suite |

---

## 3. Prompt-to-artifact checklist

| 요구사항 | concrete evidence | 현재 판정 |
| --- | --- | --- |
| LS Securities 직접 의존 금지 | VERIFY-1A, LS marker audit | 유지 |
| Kiwoom 주문/청산/live runtime 유지 | VERIFY-1A | 유지 |
| KHOPENAPI 없는 live dry-run 금지 | env sentinel audit | 유지 |
| H feature flag default-OFF | `V3K_PHASE_H_KIWOOM_DRYRUN` contract | 유지 |
| USER_ACK 없는 live dry-run 금지 | Page052 + VERIFY-1B guard | `V3K_PHASE_H_USER_ACK=1` 필요 |
| rollback/kill switch 없는 실행 금지 | Page052 approval checklist | `V3K_PHASE_H_DISABLE=1` 또는 동등 rollback 필요 |
| zero-order evidence 필요 | Page052 post-health 조건 | 주문 API 0건 증거 필요 |
| 운영 DB write 금지 | audit suite artifact guard | 유지 |
| live order/exit rule 연결 금지 | VERIFY-1A guarded runtime files | 유지 |

---

## 4. Actual H-2 live dry-run 전 사용자 결정지

1. `Phase H H-2 Kiwoom live dry-run` gate 명시 승인 여부
2. KHOPENAPI compatible environment 사용 가능 여부
3. USER_ACK 형태: `V3K_PHASE_H_USER_ACK=1`, update_log, registry 중 어떤 것을 정식 승인 기록으로 삼을지 결정
4. sentinel 형태: `V3K_KHOPENAPI_DLL` 또는 동등한 KHOPENAPI path 확인 방식
5. 실행 범위: read-only diagnostic 1회, 주문 API 0건, 계좌/주문/포지션 변화 0건
6. rollback/kill switch 형태: `V3K_PHASE_H_DISABLE=1`, feature flag OFF, registry removal 중 운영 기준 결정
7. post-health와 7일 monitoring 범위 결정

---

## 5. Actual H-3 ON 전 사용자 결정지

H-3 ON은 H-2 live dry-run과 별도 승인 gate다. H-2가 통과해도 H-3 ON에는 사용자 명시 승인, rollback owner, monitoring owner, fallback trigger, live order/exit rule consumption 분리 여부가 필요하다.

---

## 6. 남은 상태

현재 다음 후보는 `phase-h-h2-h3-live-dryrun-await-user-approval`이다. 사용자가 위 gate를 명시 승인하고 KHOPENAPI 호환 환경을 제공하기 전까지 actual live dry-run 또는 ON은 수행하지 않는다.

Directive: `PHASE_H_H2_H3_LIVE_DRYRUN_APPROVAL_PREP`는 승인 준비 기록이며 KHOPENAPI connect/login, H-2 live dry-run, H-3 ON, USER_ACK 생성, Kiwoom live runtime 변경, live order/exit rule 연결로 해석하면 안 된다.
