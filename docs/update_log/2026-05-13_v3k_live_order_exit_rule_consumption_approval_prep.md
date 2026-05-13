# V3K live order/exit rule consumption approval prep

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 054 |
| source | Page050 Phase F F-4 ON approval prep, Page051 Phase G G-3 ON approval prep, Page052 Phase H H-2/H-3 live dry-run approval prep, Page053 F1 actual DB cutover approval prep |
| marker | `LIVE_ORDER_EXIT_RULE_CONSUMPTION_APPROVAL_PREP` |
| 상태 | `completed-approval-prep` |
| next candidate | `live-order-exit-rule-consumption-await-user-approval` |

---

## 1. 요약

live order/exit rule consumption은 V3K output을 실제 거래 판단 경로에 연결하는 최종 critical gate다. 이번 Page054에서는 actual live decision wiring을 하지 않고, 사용자 승인, USER_ACK, enable registry, kill switch, shadow/dryrun proof, staged rollout, monitoring 조건을 명확한 감사 대상으로 고정했다.

No live order/exit execution: Kiwoom 주문/청산/live runtime 변경(`Kiwoom live runtime` 포함), live order/exit rule 연결, Phase F/G/H ON, DB cutover, `V3K_LIVE_DECISION_USER_ACK=1`, `V3K-LIVE-ORDER-EXIT-ENABLE` registry, 운영 `_database/` write, DB 파일 commit, `.omx/reports` raw artifact commit, LS Securities 직접 의존 추가는 수행하지 않았다.

---

## 2. 준비된 근거

| 근거 | 설명 |
| --- | --- |
| `scripts/audit_v3k_verify_1a.py --base 57496d24` | Kiwoom 주문/청산/live runtime 보존, LS Securities 직접 의존 금지, artifact guard |
| `scripts/smoke_v3k_phase_f_default_off.py` | Phase F default-OFF/dual gate/rollback proof |
| `scripts/backtest_v3k_phase_f_parity.py --sample-period 7d` | Phase F parity baseline |
| `scripts/smoke_v3k_phase_g_engine_unit.py` | Phase G default-OFF/unit behavior |
| `scripts/backtest_v3k_phase_g_parity.py` | Phase G parity proof |
| `scripts/benchmark_v3k_phase_g_engine.py` | Phase G benchmark proof |
| `scripts/audit_v3k_phase_h_env_check.py --stdout` | KHOPENAPI connect 없이 environment/sentinel report |
| `scripts/run_v3k_audit_suite.py` | 전체 V3K audit suite |

---

## 3. Prompt-to-artifact checklist

| 요구사항 | concrete evidence | 현재 판정 |
| --- | --- | --- |
| LS Securities 직접 의존 금지 | VERIFY-1A, LS marker audit | 유지 |
| Kiwoom 주문/청산/live runtime 유지(`Kiwoom live runtime`) | VERIFY-1A | 유지 |
| Phase F/G/H/F1 선행 gate 미충족 시 소비 금지 | Page050~Page053 approval prep | 유지 |
| USER_ACK 없는 live decision 금지 | Page054 + VERIFY-1B guard | `V3K_LIVE_DECISION_USER_ACK=1` 필요 |
| enable registry 없는 live decision 금지 | Page054 + runtime activation gap | `V3K-LIVE-ORDER-EXIT-ENABLE` 필요 |
| kill switch 없는 live decision 금지 | Page054 STOP condition | `V3K_LIVE_DECISION_DISABLE=1` 필요 |
| shadow/dryrun proof 없는 live decision 금지 | Page054 approval checklist | shadow/dryrun proof 필요 |
| staged rollout/monitoring 없는 live decision 금지 | Page054 approval checklist | monitoring/rollback owner 필요 |
| 운영 DB write 금지 | audit suite artifact guard | 유지 |
| raw `.omx/reports` commit 금지 | artifact guard | 유지 |

---

## 4. Actual live decision 전 사용자 결정지

1. `live order/exit rule consumption` gate 명시 승인 여부
2. USER_ACK 형태: `V3K_LIVE_DECISION_USER_ACK=1`, update_log, registry 중 어떤 것을 정식 승인 기록으로 삼을지 결정
3. enable registry 형태: `V3K-LIVE-ORDER-EXIT-ENABLE` 기록과 rollback pair 정의
4. kill switch 형태: `V3K_LIVE_DECISION_DISABLE=1`, registry removal, feature flag default-OFF fallback 중 운영 기준 결정
5. 선행 gate 범위: Phase F F-4, Phase G G-3, H-2/H-3, F1 중 어떤 산출물을 소비할지 결정
6. shadow/dryrun proof 범위: 주문 API 0건, 포지션 변화 0건, 손실/MDD/거래횟수 허용 범위
7. staged rollout 범위: 종목/전략/시간/계좌 범위와 monitoring/rollback owner

---

## 5. 남은 상태

현재 다음 후보는 `live-order-exit-rule-consumption-await-user-approval`이다. 사용자가 위 gate를 명시 승인하고 kill switch, shadow/dryrun proof, staged rollout, monitoring 조건을 확정하기 전까지 actual live order/exit consumption은 수행하지 않는다.

Directive: `LIVE_ORDER_EXIT_RULE_CONSUMPTION_APPROVAL_PREP`는 승인 준비 기록이며 Kiwoom 주문/청산/live runtime 변경(`Kiwoom live runtime` 변경), live order/exit rule 연결, USER_ACK 생성, enable registry 생성, Phase F/G/H ON, DB cutover로 해석하면 안 된다.
