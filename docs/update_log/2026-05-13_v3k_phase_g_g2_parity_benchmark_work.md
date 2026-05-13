# V3K Phase G G-2 parity/benchmark work 기록

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 039 |
| phase | Phase G / G-2 parity·benchmark work |
| source | Page038 parity·benchmark plan |
| 결과 | `completed-proof` |
| next candidate | `phase-g-g3-approval-gate` |

---

## 1. 배경

Phase G는 V3 microstructure 기능을 2U_C에 이식하되 LS Securities 직접 의존을 제외하고 Kiwoom field/runtime 방향을 유지하는 작업이다. Page037에서 default-OFF engine staging을 완료했고, Page038에서 G-2 검증 기준을 문서화했다. Page039는 이 계획에 따라 proof-only script를 구현·실행하는 단계다.

---

## 2. 구현 내용

### 2.1 parity script

`script/backtest_v3k_phase_g_parity.py`가 아니라 정확히 `scripts/backtest_v3k_phase_g_parity.py`를 추가했다.

- `V3KMicrostructureEngine(enabled=True)`를 명시적으로 사용한다.
- 기본 constructor와 feature flag는 계속 default-OFF인지 확인한다.
- Kiwoom field name은 `KIWOOM_OPT_FIELD_MAPPING`을 통해 가져온다.
- 운영 DB, broker runtime, live decision path를 호출하지 않는다.
- report는 `.omx/reports/v3k-phase-g-parity-latest.json`에만 기록한다.

### 2.2 benchmark script

`scripts/benchmark_v3k_phase_g_engine.py`를 추가했다.

- fixed synthetic rows 120개와 50회 반복으로 6,000 operations를 측정한다.
- wall-clock 기준은 3.00초 baseline, 허용 최대 3.60초다.
- `tracemalloc` peak 기준은 8,000,000 bytes baseline, 허용 최대 9,600,000 bytes다.
- report는 `.omx/reports/v3k-phase-g-benchmark-latest.json`에만 기록한다.

---

## 3. 검증 결과

아래 검증을 통과했다.

```powershell
python -m py_compile strategy/v3k_microstructure_engine.py scripts/backtest_v3k_phase_g_parity.py scripts/benchmark_v3k_phase_g_engine.py scripts/audit_v3k_phase_g_ls_excise.py scripts/smoke_v3k_phase_g_engine_unit.py scripts/audit_v3k_runtime_activation_gap.py scripts/audit_v3k_verify_1a.py scripts/audit_v3k_verify_1b_closure.py
python scripts/backtest_v3k_phase_g_parity.py
python scripts/benchmark_v3k_phase_g_engine.py
python scripts/audit_v3k_phase_g_ls_excise.py
python scripts/smoke_v3k_phase_g_engine_unit.py
python scripts/audit_v3k_runtime_activation_gap.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
```

---

## 4. 안전 경계

Page039는 실제 Phase G ON을 수행하지 않았다. `V3K_PHASE_G_MICROSTRUCTURE_ENGINE` 기본값은 OFF이며, `V3K-PHASE-G-ENABLE` registry도 만들지 않았다. Kiwoom 주문/청산/live runtime, 운영 `_database/`, DB 파일, GUI/pyd wrapper도 변경하지 않았다.

---

## 5. 다음 단계

다음 후보는 Page040 / `phase-g-g3-approval-gate`이다. 이 단계도 ON 실행이 아니라 승인 gate 문서화로 시작해야 한다. G-3에서 사용자 승인, rollback, monitoring, registry 조건이 명시적으로 충족되기 전까지 Phase G는 default-OFF 상태를 유지한다.

Directive: Page039 proof 결과를 live strategy consumption 또는 ON approval로 승격하지 말 것.
