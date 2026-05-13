# V3K Page 054 - live order/exit rule consumption approval prep 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 053 / F1 actual DB cutover approval prep |
| 현재 page | Page 054 / live order/exit rule consumption approval prep |
| 상태 | `completed-approval-prep` |
| 다음 후보 | `live-order-exit-rule-consumption-await-user-approval` |
| 목적 | V3K analyzer/microstructure/learning output을 실제 주문·청산 판단 경로에 연결하기 전 필요한 사용자 승인, USER_ACK, enable registry, kill switch, shadow/dryrun proof, staged rollout, monitoring 조건을 문서와 감사 도구에 고정한다. |
| 위험도 | approval prep은 낮음, actual live decision wiring은 critical |
| 실제 주문/청산 연결 여부 | 아님. Kiwoom live runtime과 주문/청산 로직을 변경하지 않고 approval prep만 수행한다. |

---

## 1. 목표 재확인

V3K의 목표는 **LS Securities 직접 의존성을 제외하고 Kiwoom API/주문/청산/live runtime을 유지한 채 V3의 학습/분석/DB/backtest/realtime 기능을 `STOM_Version_2U_C`에 이행**하는 것이다.

live order/exit rule consumption은 V3K safe-staged 산출물을 실제 거래 판단에 연결하는 최후 critical gate다. Phase F/G/H와 F1이 각각 ON, live dry-run, DB cutover 승인을 요구하더라도, 그 결과를 주문·청산 규칙에 소비하는 것은 별도 승인 없이는 수행할 수 없다.

---

## 2. 현재 준비 상태

| 증거 | 역할 | 현재 상태 |
| --- | --- | --- |
| `scripts/audit_v3k_verify_1a.py --base 57496d24` | Kiwoom 주문/청산/live runtime 변경 감시 | PASS 대상 |
| `scripts/smoke_v3k_phase_f_default_off.py` | Phase F analyzer strategy default-OFF/rollback proof | PASS 대상 |
| `scripts/backtest_v3k_phase_f_parity.py --sample-period 7d` | Phase F parity baseline | PASS 대상 |
| `scripts/smoke_v3k_phase_g_engine_unit.py` | Phase G microstructure default-OFF/unit behavior | PASS 대상 |
| `scripts/backtest_v3k_phase_g_parity.py` | Phase G parity proof | PASS 대상 |
| `scripts/benchmark_v3k_phase_g_engine.py` | Phase G benchmark proof | PASS 대상 |
| `scripts/audit_v3k_phase_h_env_check.py --stdout` | KHOPENAPI live connect 없이 environment/sentinel report | PASS 대상 |
| `scripts/run_v3k_audit_suite.py` | 전체 V3K default-OFF, LS excise, artifact guard | PASS 대상 |

---

## 3. Prompt-to-artifact checklist

| 요구사항 | concrete evidence | Page054 처리 |
| --- | --- | --- |
| Kiwoom 주문/청산/live runtime 유지 | VERIFY-1A, runtime activation gap | actual runtime 미변경 |
| LS Securities 직접 의존 금지 | VERIFY-1A / LS marker audit | live decision prep에도 LS broker 의존성 금지 |
| Phase F ON 전 live consumption 금지 | Page050, Phase F smoke/parity/rollback | F-4 승인 전 소비 금지 |
| Phase G ON 전 live consumption 금지 | Page051, Phase G parity/benchmark/LS excise | G-3 승인 전 소비 금지 |
| H-2/H-3 dry-run 전 live consumption 금지 | Page052, H hook/env sentinel | KHOPENAPI/zero-order evidence 전 소비 금지 |
| F1 DB cutover 전 live consumption 금지 | Page053, cutover dry-run/health | DB source-of-truth 확정 전 소비 금지 |
| USER_ACK 없는 live decision 금지 | Page054 + VERIFY-1B guard | `V3K_LIVE_DECISION_USER_ACK=1` 필요 |
| enable registry 없는 live decision 금지 | Page054 + runtime gap guard | `V3K-LIVE-ORDER-EXIT-ENABLE` 필요 |
| kill switch 없는 live decision 금지 | Page054 + STOP condition | `V3K_LIVE_DECISION_DISABLE=1` 필요 |
| shadow/dryrun proof 없는 live decision 금지 | Page054 approval checklist | shadow/dryrun proof 필수 |
| 운영 DB/raw artifact commit 금지 | audit suite artifact guard | 유지 |

---

## 4. Actual live order/exit consumption 전 필수 승인 조건

1. 사용자가 `live order/exit rule consumption` gate를 명시적으로 승인한다.
2. `V3K_LIVE_DECISION_USER_ACK=1` 또는 동등한 승인 기록이 생성된다.
3. `V3K-LIVE-ORDER-EXIT-ENABLE` registry 또는 동등 enable record가 생성되고 commit된다.
4. `V3K_LIVE_DECISION_DISABLE=1` 또는 동등 kill switch/rollback path가 실제로 검증된다.
5. Phase F F-4 ON, Phase G G-3 ON, H-2/H-3 dry-run, F1 DB cutover 중 해당 live decision이 의존하는 gate가 먼저 승인·검증된다.
6. shadow/dryrun proof가 주문 API 0건, 포지션 변화 0건, 기존 전략 대비 손실/MDD/거래횟수 허용 범위 이내임을 증명한다.
7. staged rollout 범위, monitoring 기간, alert owner, rollback owner, fallback trigger가 승인된다.
8. 아래 검증이 모두 PASS한다.

```powershell
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/smoke_v3k_phase_f_default_off.py
python scripts/backtest_v3k_phase_f_parity.py --sample-period 7d
python scripts/smoke_v3k_phase_g_engine_unit.py
python scripts/backtest_v3k_phase_g_parity.py
python scripts/benchmark_v3k_phase_g_engine.py
python scripts/audit_v3k_phase_h_env_check.py --stdout
python scripts/run_v3k_audit_suite.py
```

---

## 5. STOP condition

다음 중 하나라도 충족되지 않으면 live order/exit rule consumption을 수행하지 않는다.

- 사용자 명시 gate 승인 부재
- `V3K_LIVE_DECISION_USER_ACK=1` 또는 동등 승인 기록 부재
- `V3K-LIVE-ORDER-EXIT-ENABLE` registry 부재
- `V3K_LIVE_DECISION_DISABLE=1` 또는 동등 kill switch 부재
- shadow/dryrun proof 부재
- Phase F/G/H/F1 선행 gate 미충족
- 주문 API 0건/포지션 변화 0건 증거 부재
- staged rollout/monitoring/rollback owner 부재
- Kiwoom 주문/청산/live runtime 코드 변경 발생
- LS Securities 직접 의존 발생
- 운영 `_database/`, DB 파일, live artifact, `.omx/reports` raw artifact commit 위험 발생

---

## 6. 다음 단계

현재 Page054의 결론은 `live-order-exit-rule-consumption-await-user-approval`이다. 다음 실제 실행은 사용자 승인, 선행 gate 승인, kill switch, shadow/dryrun proof, staged rollout, monitoring 조건이 모두 확정되기 전에는 수행하지 않는다. 승인 전 안전 작업으로는 전체 approval gate closeout review와 사용자 승인 handoff 재정리만 허용한다.
