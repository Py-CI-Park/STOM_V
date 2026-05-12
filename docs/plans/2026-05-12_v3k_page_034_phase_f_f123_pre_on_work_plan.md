# V3K Page 034 — Phase F F-1/F-2/F-3 pre-ON work 계획 / 완료 기록

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| 완료일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 033 / Phase F analyzer pre-ralplan |
| f51 단계 | C2 / F3 Phase F sub-phase F-1+F-2+F-3 |
| 위험도 | high |
| 결과 | `completed-pre-on-proof` |
| 다음 page | Page 035 / Phase F F-4 approval gate |

---

## 0. 목표

Page034는 Phase F의 ON 전 사전작업만 수행한다. 목표는 analyzer output을 `V3K_` prefix formula surface에 **default-OFF**로 노출하고, parity / dual gate / rollback proof를 준비하는 것이다.

이 page는 F-4 ON 전환이 아니다. 실제 live 주문·청산 판단에 analyzer output을 반영하지 않는다.

---

## 1. 수행 범위

| sub-phase | 수행 결과 |
| --- | --- |
| F-1 | `strategy/v3k_formula_facade.py`에 Phase F 전용 `build_phase_f(...)` dual-gate facade 추가 |
| F-1 | `strategy/v3k_analyzer_adapter.py`에 Phase F env/DB gate, rollback gate, output contract helper 추가 |
| F-2 | `scripts/backtest_v3k_phase_f_parity.py` 추가. pre-ON synthetic no-runtime-hook parity report 생성 |
| F-3 | `scripts/smoke_v3k_phase_f_default_off.py`와 `scripts/audit_v3k_phase_f_rollback.py` 추가 |
| 관리 | update_log, registry, runtime activation audit, VERIFY-1B closure audit 갱신 |

---

## 2. 금지 범위 준수

다음은 수행하지 않았다.

- F-4 ON 전환
- `V3K-PHASE-F-ENABLE` registry 추가
- live 주문/청산 판단 반영
- Kiwoom 주문/청산/live runtime 변경
- 운영 `_database/` write 또는 DB 파일 commit
- LS Securities 직접 의존
- 사용자 승인 없는 feature flag ON

---

## 3. Gate 설계

Phase F pre-ON helper는 caller-owned mapping만 평가한다. 실제 `os.environ`이나 운영 DB를 직접 읽지 않는다.

| 조건 | 의미 |
| --- | --- |
| `V3K_PHASE_F_ENABLE=1` | env gate |
| `phase_f_analyzer_strategy.enabled=1` | DB row gate를 시뮬레이션하는 mapping key |
| `V3K_PHASE_F_DISABLE=1` | rollback gate. env+DB enable보다 우선 |

ON 후보 callable은 env gate와 DB row gate가 모두 true이고 rollback flag가 false일 때만 생성된다. 이 후보 callable도 runtime `globals().update(...)`에 주입하지 않는다.

---

## 4. Parity 결과

`scripts/backtest_v3k_phase_f_parity.py --sample-period 7d` 결과:

| 지표 | 한계 | 결과 |
| --- | ---: | ---: |
| loss delta | ±5.0% | 0.00% |
| MDD delta | ±3.0% | 0.00% |
| trade count delta | ±10.0% | 0.00% |

주의: Page034 parity는 **pre-ON synthetic no-runtime-hook baseline**이다. 아직 strategy/backtest runtime이 analyzer output을 소비하지 않기 때문에, candidate formula values가 생성되더라도 trade metric은 변하지 않아야 한다. 실제 runtime 소비는 F-4 승인 cycle 이후 별도 검증 대상이다.

---

## 5. 검증

```powershell
python -m py_compile strategy/v3k_analyzer_adapter.py strategy/v3k_formula_facade.py scripts/smoke_v3k_phase_f_default_off.py scripts/backtest_v3k_phase_f_parity.py scripts/audit_v3k_phase_f_rollback.py scripts/audit_v3k_verify_1a.py scripts/audit_v3k_verify_1b_closure.py
python scripts/smoke_v3k_phase_f_default_off.py
python scripts/backtest_v3k_phase_f_parity.py --sample-period 7d
python scripts/audit_v3k_phase_f_rollback.py
```

모두 PASS.

---

## 6. 다음 단계

다음 candidate는 `phase-f-f4-approval-gate`다.

Page035에서는 실제 ON을 수행하지 않고 다음 gate 충족 여부만 문서화한다.

1. 사용자 명시 승인 존재 여부
2. `V3K_PHASE_F_USER_ACK=1` 허용 여부
3. F-4 ON 전환 조건 충족 여부
4. `V3K-PHASE-F-ENABLE` registry를 추가할 수 있는지 여부
5. 24h monitoring 착수 가능 여부

사용자 승인과 운영 조건이 없으면 F-4는 계속 BLOCK 상태로 유지한다.
