# V3K Phase F F-1/F-2/F-3 pre-ON 작업 기록

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 커밋 | `2ce5f45c` / Phase F analyzer pre-ralplan |
| page plan | `docs/plans/2026-05-12_v3k_page_034_phase_f_f123_pre_on_work_plan.md` |
| 결과 | `completed-pre-on-proof` |
| 다음 candidate | `phase-f-f4-approval-gate` |

---

## 1. 목적

Page034는 V3 analyzer output을 Kiwoom 유지 2U_C에서 사용할 준비를 하되, 아직 live 주문·청산 판단에 연결하지 않는 단계다. 이번 작업은 F-1/F-2/F-3까지만 수행했다.

---

## 2. 구현 요약

### F-1 — default-OFF analyzer formula surface

- `strategy/v3k_analyzer_adapter.py`
  - `V3K_PHASE_F_ENABLE`
  - `V3K_PHASE_F_DISABLE`
  - `phase_f_analyzer_strategy.enabled`
  - `evaluate_phase_f_analyzer_gate(...)`
  - `phase_f_formula_output_contract(...)`
- `strategy/v3k_formula_facade.py`
  - `V3KPhaseFFormulaResult`
  - `V3KFormulaGlobalFacade.build_phase_f(...)`

`build_phase_f(...)`는 env+DB dual gate가 모두 true이고 rollback flag가 false일 때만 `V3K_` prefix callable 후보를 만든다. 이 후보는 runtime globals에 주입되지 않는다.

### F-2 — parity baseline

- `scripts/backtest_v3k_phase_f_parity.py`

Page034 parity는 pre-ON synthetic no-runtime-hook baseline이다. 아직 runtime hook이 없으므로 analyzer candidate values가 생성되어도 loss/MDD/trade count는 변하지 않아야 한다.

결과:

| 지표 | 한계 | 결과 | 판정 |
| --- | ---: | ---: | --- |
| loss delta | ±5.0% | 0.00% | PASS |
| MDD delta | ±3.0% | 0.00% | PASS |
| trade count delta | ±10.0% | 0.00% | PASS |

### F-3 — dual gate / rollback proof

- `scripts/smoke_v3k_phase_f_default_off.py`
- `scripts/audit_v3k_phase_f_rollback.py`

검증한 matrix:

| case | 결과 |
| --- | --- |
| default | OFF |
| env only | OFF |
| DB row only | OFF |
| env + DB row | candidate ON 가능 |
| env + DB row + rollback | OFF |

---

## 3. 안전 경계

이번 작업에서 다음은 변경하지 않았다.

- Kiwoom 주문/청산/live runtime
- `trade/base_strategy.py`
- `trade/formula_manager.py`
- receiver/trader/order 경로
- 운영 `_database/`
- `_database_v3k_shadow/`
- DB 파일
- LS Securities 직접 의존
- STOM CLI surface

---

## 4. 산출물

| 파일 | 목적 |
| --- | --- |
| `strategy/v3k_analyzer_adapter.py` | Phase F dual gate와 rollback gate helper |
| `strategy/v3k_formula_facade.py` | Phase F gated formula candidate builder |
| `scripts/smoke_v3k_phase_f_default_off.py` | default-OFF, env-only, DB-only, rollback matrix smoke |
| `scripts/backtest_v3k_phase_f_parity.py` | pre-ON parity baseline report 생성 |
| `scripts/audit_v3k_phase_f_rollback.py` | rollback flag 우선순위 audit |
| `docs/plans/2026-05-12_v3k_page_034_phase_f_f123_pre_on_work_plan.md` | Page034 완료 기록 |
| `docs/plans/2026-05-13_v3k_page_035_phase_f_f4_approval_gate_plan.md` | 다음 승인 gate 계획 |

---

## 5. 검증

```powershell
python -m py_compile strategy/v3k_analyzer_adapter.py strategy/v3k_formula_facade.py scripts/smoke_v3k_phase_f_default_off.py scripts/backtest_v3k_phase_f_parity.py scripts/audit_v3k_phase_f_rollback.py scripts/audit_v3k_verify_1a.py scripts/audit_v3k_verify_1b_closure.py
python scripts/smoke_v3k_phase_f_default_off.py
python scripts/backtest_v3k_phase_f_parity.py --sample-period 7d
python scripts/audit_v3k_phase_f_rollback.py
```

초기 검증 PASS.

최종 commit 전후에는 추가로 다음을 통과해야 한다.

```powershell
python scripts/audit_v3k_runtime_activation_gap.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph v3k_settings*.json _database.backup.TEST
```

---

## 6. 다음 단계

다음은 Page035 / `phase-f-f4-approval-gate`다.

중요: Page035도 실제 ON 전환이 아니라 승인 gate 확인 단계다. 사용자 명시 승인, `V3K_PHASE_F_USER_ACK=1`, `V3K-PHASE-F-ENABLE` registry, 24h monitoring 조건이 없으면 F-4는 BLOCK으로 남겨야 한다.
