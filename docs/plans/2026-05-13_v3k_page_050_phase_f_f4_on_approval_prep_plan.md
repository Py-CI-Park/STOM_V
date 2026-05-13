# V3K Page 050 - Phase F F-4 ON approval prep 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 049 / GUI sidecar write approval prep |
| 현재 page | Page 050 / Phase F F-4 ON approval prep |
| 상태 | `completed-approval-prep` |
| 다음 후보 | `phase-f-f4-on-await-user-approval` |
| 목적 | Phase F analyzer strategy ON 전에 필요한 사용자 승인, USER_ACK, enable registry, rollback, monitoring, 검증 checklist를 문서와 감사 도구에 고정한다. |
| 위험도 | approval prep은 낮음, actual ON은 critical |
| 실제 ON 여부 | 아님. approval prep 문서화만 수행한다. |

---

## 1. 목표 재확인

V3K의 목표는 **LS Securities 직접 의존성을 제외하고 Kiwoom API/주문/청산/live runtime을 유지한 채 V3의 학습/분석/DB/backtest/realtime 기능을 `STOM_Version_2U_C`에 이행**하는 것이다.

Phase F F-4 ON은 V3 analyzer output을 live formula/strategy consumption 후보로 올리는 critical gate이다. 따라서 Page050에서는 actual ON을 수행하지 않고, 승인 전에 반드시 만족해야 하는 조건만 명확히 잠근다.

---

## 2. 현재 Phase F 준비 상태

| 증거 | 역할 | 현재 상태 |
| --- | --- | --- |
| `scripts/smoke_v3k_phase_f_default_off.py` | default/env-only/db-only/dual-gate/rollback matrix 검증 | PASS 대상 |
| `scripts/backtest_v3k_phase_f_parity.py` | synthetic pre-ON parity baseline | PASS 대상 |
| `scripts/audit_v3k_phase_f_rollback.py` | rollback flag가 env+DB enable보다 우선하는지 검증 | PASS 대상 |
| `strategy/v3k_analyzer_adapter.py` | `V3K_PHASE_F_ENABLE`, `V3K_PHASE_F_DISABLE`, `phase_f_analyzer_strategy.enabled` dual gate | staged |
| `strategy/v3k_formula_facade.py` | Phase F formula candidate builder | staged |
| `scripts/audit_v3k_verify_1a.py` | Kiwoom/runtime untouched, default-OFF, LS dependency exclusion, artifact guard | PASS 대상 |

---

## 3. Prompt-to-artifact checklist

| 요구사항 | concrete evidence | Page050 처리 |
| --- | --- | --- |
| Kiwoom 주문/청산/live runtime 유지 | VERIFY-1A, runtime activation gap | actual runtime 미변경 |
| LS Securities 직접 의존 금지 | VERIFY-1A / LS marker audit | Phase F ON prep에도 LS broker 의존성 금지 |
| Phase F default-OFF 유지 | default-OFF smoke, DEFAULT_FLAGS audit | actual ON 없이 유지 |
| env-only/db-only 단독 ON 금지 | smoke matrix | dual gate 조건 유지 |
| rollback flag 우선 | rollback audit | `V3K_PHASE_F_DISABLE=1` 조건 명시 |
| parity baseline 확보 | Phase F parity script | actual ON 전 필수 검증으로 명시 |
| USER_ACK 없는 ON 금지 | Page050 docs + VERIFY-1B guard | `V3K_PHASE_F_USER_ACK=1` 필요 조건 명시 |
| enable registry 없는 ON 금지 | Page050 docs + runtime gap guard | `V3K-PHASE-F-ENABLE` 필요 조건 명시 |
| live order/exit rule 연결 금지 | VERIFY-1A guarded runtime files | actual live decision path 미연결 |
| 운영 DB write 금지 | audit suite artifact guard | `_database/`, DB 파일, sidecar raw artifact commit 금지 |

---

## 4. Actual F-4 ON 전 필수 승인 조건

1. 사용자가 `Phase F F-4 ON` gate를 명시적으로 승인한다.
2. `V3K_PHASE_F_USER_ACK=1` 또는 동등한 승인 기록이 생성된다.
3. `V3K-PHASE-F-ENABLE` registry 또는 동등한 enable record가 생성되고 commit된다.
4. `V3K_PHASE_F_DISABLE=1` rollback path가 실제로 검증된다.
5. 24h monitoring 범위, error budget, fallback trigger가 승인된다.
6. F1 DB cutover/GUI sidecar source-of-truth가 연결되는 경우 별도 gate로 분리한다.
7. 아래 검증이 모두 PASS한다.

```powershell
python scripts/smoke_v3k_phase_f_default_off.py
python scripts/backtest_v3k_phase_f_parity.py --sample-period 7d
python scripts/audit_v3k_phase_f_rollback.py
python scripts/run_v3k_audit_suite.py
```

---

## 5. STOP condition

다음 중 하나라도 충족되지 않으면 Phase F F-4 ON을 수행하지 않는다.

- 사용자 명시 gate 승인 부재
- `V3K_PHASE_F_USER_ACK=1` 또는 동등 승인 기록 부재
- `V3K-PHASE-F-ENABLE` registry 부재
- rollback/monitoring 계획 부재
- Phase F parity/default-OFF/rollback 검증 실패
- Kiwoom live runtime, 주문/청산, live order/exit rule에 닿는 변경 발생
- LS Securities 직접 의존 발생
- 운영 `_database/`, DB 파일, `.omx/reports` raw artifact commit 위험 발생

---

## 6. 다음 단계

현재 Page050의 결론은 `phase-f-f4-on-await-user-approval`이다. 다음 실제 실행은 사용자 승인 전에는 수행하지 않는다. 승인 전 안전 작업으로는 Phase G G-3 ON approval prep 또는 남은 gate의 조건 문서화만 허용한다.
