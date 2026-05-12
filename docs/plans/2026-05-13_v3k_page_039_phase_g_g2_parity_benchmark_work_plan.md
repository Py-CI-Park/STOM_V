# V3K Page 039 — Phase G G-2 parity/benchmark work 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 038 / Phase G G-2 parity·benchmark plan |
| 현재 page | Page 039 / Phase G G-2 parity·benchmark work |
| 목적 | Page038에서 고정한 한계와 report schema에 따라 Phase G engine parity·benchmark script를 구현하고 실행한다. |
| 위험도 | high |
| ON 여부 | 금지. Page039는 proof 생성까지만 수행한다. |

---

## 1. 실행 범위

Page039에서 허용되는 작업은 아래로 제한한다.

1. `scripts/backtest_v3k_phase_g_parity.py` 구현
2. `scripts/benchmark_v3k_phase_g_engine.py` 구현
3. synthetic/caller-owned fixture 생성 또는 script 내부 fixture 정의
4. ignored `.omx/reports/v3k-phase-g-parity-latest.json` 생성
5. ignored `.omx/reports/v3k-phase-g-benchmark-latest.json` 생성
6. audit/closure script에 두 신규 script를 요구 대상으로 추가
7. docs/update_log 및 `docs/CARRY_FORWARD_REGISTRY.md` 갱신

---

## 2. parity script 요구사항

`scripts/backtest_v3k_phase_g_parity.py`는 다음을 만족해야 한다.

- `strategy.v3k_microstructure_engine.V3KMicrostructureEngine(enabled=True)`를 명시적으로 사용한다.
- 운영 DB, Kiwoom API, LS API, live runtime을 호출하지 않는다.
- fixture row는 Kiwoom field name 또는 engine mapping contract에 맞춘 caller-owned dict로 구성한다.
- output contract 5개 값을 모두 검사한다.
- 기준값 대비 ±15%를 넘으면 non-zero exit한다.
- 결과 JSON은 `.omx/reports/v3k-phase-g-parity-latest.json`에만 쓴다.

---

## 3. benchmark script 요구사항

`scripts/benchmark_v3k_phase_g_engine.py`는 다음을 만족해야 한다.

- fixed synthetic rows와 fixed iteration count를 사용한다.
- `time.perf_counter()` 기반 wall-clock 측정을 수행한다.
- 가능하면 `tracemalloc` peak memory를 기록한다.
- 기준 budget 대비 ±20% 초과 시 non-zero exit한다.
- 결과 JSON은 `.omx/reports/v3k-phase-g-benchmark-latest.json`에만 쓴다.
- benchmark 결과가 환경에 과민하지 않도록 budget은 Windows/Python 3.13 로컬 실행을 고려한 보수적 값으로 시작한다.

---

## 4. 금지 범위

아래는 Page039에서 금지한다.

- `V3K_PHASE_G_MICROSTRUCTURE_ENGINE` 기본값 ON 변경
- `V3K-PHASE-G-ENABLE` registry 생성
- `V3K_PHASE_G_USER_ACK=1` 사용
- `trade/base_strategy.py`, order/exit rule, live strategy path 변경
- KHOPENAPI login/connect 또는 주문 API 호출
- 운영 `_database/` read/write
- DB 파일 또는 `.omx/reports/` commit
- LS Securities 직접 의존 import/call 추가

---

## 5. 검증 명령

Page039 완료 시 최소 아래 명령을 통과해야 한다.

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
python scripts/audit_v3k_db_artifact_status.py
python scripts/audit_v3k_sidecar_artifact_status.py
git diff --check
```

---

## 6. 예상 다음 후보

Page039가 완료되면 다음 후보는 Page040 / `phase-g-g3-approval-gate`이다. 단, 이는 ON 실행이 아니라 “G-2 proof가 있어도 왜 바로 ON 할 수 없는지, 어떤 사용자 승인과 monitoring 조건이 필요한지”를 고정하는 gate page로 시작해야 한다.

Directive: Page039 PASS는 Phase G ON 승인과 동의어가 아니다. G-3에서 사용자 명시 승인, rollback, monitoring, registry 조건이 충족되기 전까지 default-OFF 상태를 유지한다.
