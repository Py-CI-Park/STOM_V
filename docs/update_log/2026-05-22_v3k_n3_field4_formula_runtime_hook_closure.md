# N3 — 분야 ④ formula runtime hook 통합 100% closure 보고서

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `e566044c` (N2 분야 ③ closure 직후) |
| 마스터 plan | `docs/plans/2026-05-22_v3k_remaining_5fields_completion_master_plan.md` §3.3 N3 |
| 정책 amend | `docs/plans/2026-05-22_v3k_f1_bypass_phase_fg_on_policy_amend_plan.md` §3.4 |
| 본 commit 정체성 | 5분야 master **N3 (분야 ④ 75→100% closure)** — 트레이드 runtime 코드 변경 발생 |
| 코드 변경 | 4 파일 (trade/formula_manager.py + 3 audit/smoke) |
| 매매 영향 | 잠재 (default-OFF parity ±0% 유지) |

---

## §0. TL;DR

```text
분야 ④ formula runtime hook 통합 75% → 100% closure.

trade/formula_manager.py:77 UpdateGlobalsFunc에 V3KFormulaGlobalFacade hook 통합.
default-OFF 시 facade.has_globals=False → 기존 동작 보존 (parity ±0% 검증).
LH1 코드 invariant 부분 떨어냄: formula_manager.py만 V3K hook 허용,
base_strategy.py + trade/stock_korea/ + Kiwoom_OpenAPI/는 보존.

검증:
  - backtest_v3k_phase_f_parity (재실행): deltas loss/mdd/trades 모두 0% (T1과 동일)
  - audit_v3k_verify_1a: PASS (guard amend로 formula_manager.py 허용)
  - 3 formula smoke: 모두 PASS (boundary_contract + runtime_hook_decision은 amend 후)

F6 산식: 75.0% → 78.6% (+3.6%p)
```

---

## §1. 코드 변경 (4 파일)

### §1.1 `trade/formula_manager.py` — V3K facade hook 통합

**위치 1**: import block (line 11~)

```python
# V3K formula globals facade hook (default-OFF, side-effect-free)
try:
    from strategy.v3k_formula_facade import V3KFormulaGlobalFacade, V3KFormulaGlobalRequest
    _V3K_FACADE_AVAILABLE = True
except Exception:
    _V3K_FACADE_AVAILABLE = False
```

**위치 2**: `UpdateGlobalsFunc` 본문 (line 77~)

```python
def UpdateGlobalsFunc(self, dict_add_func):
    # V3K formula globals hook (default-OFF 시 facade가 빈 dict 반환 → 기존 동작 보존)
    if _V3K_FACADE_AVAILABLE:
        try:
            facade = V3KFormulaGlobalFacade()
            v3k_result = facade.build(V3KFormulaGlobalRequest(analyzer_values={}))
            if v3k_result.has_globals:
                dict_add_func = {**dict_add_func, **v3k_result.globals_dict}
        except Exception:
            # V3K facade 호출 예외 시 기존 동작 보존 (LH1 코드 invariant 보호)
            pass
    globals().update(dict_add_func)
```

**default-OFF 동작 보장**:
- `V3K_FORMULA_MANAGER_ADAPTER + V3K_STG_GLOBALS_FACADE` 둘 다 OFF → `facade.has_globals=False`
- → `dict_add_func` 변경 없음
- → `globals().update(dict_add_func)` 기존 호출 그대로
- → **default-OFF parity ±0%** 보장

**flag ON 시**:
- V3K_* prefix가 붙은 globals 추가
- 기존 globals은 그대로 + V3K_* 추가만

### §1.2 `scripts/audit_v3k_verify_1a.py` — guard amend

`_assert_no_v3k_imports_in_kiwoom_runtime` search_roots에서 `trade/formula_manager.py` 제거:

```python
search_roots = [
    ROOT / "trade" / "stock_korea",
    ROOT / "trade" / "base_strategy.py",
    # ROOT / "trade" / "formula_manager.py",  ← N3 amend로 제거
]
```

→ `trade/formula_manager.py` V3K hook 허용, `trade/base_strategy.py` + `trade/stock_korea/`는 차단 유지.

### §1.3 `scripts/smoke_v3k_formula_boundary_contract.py` — runtime_paths amend

`_assert_trade_runtime_has_no_v3k_imports_yet`의 runtime_paths에서 formula_manager.py 제거:

```python
runtime_paths = (
    "trade/base_strategy.py",  # formula_manager.py는 N3에서 제외
)
```

### §1.4 `scripts/smoke_v3k_formula_runtime_hook_decision.py` — 두 assert amend

- `_assert_verify_1a_still_blocks_direct_runtime_edits`: trade/base_strategy.py + backtest/backengine_base.py만 검증
- `_assert_trade_runtime_remains_unhooked`: trade/base_strategy.py만 검증

---

## §2. LH1 코드 invariant 부분 amend 정합

| invariant | 변경 |
| --- | --- |
| L1 database schema unchanged | ✅ 보존 |
| L4 운영 DB write 제한 | ✅ 보존 (코드 변경, DB write 0건) |
| L7 LS direct dependency 0건 | ✅ 보존 |
| L9 STOM CLI surface 보존 | ✅ 보존 |
| LH1 *전체* (Kiwoom 주문/청산 경로 코드 무변경) | ⚠️ **부분 떨어냄** |
| LH1-A: trade/stock_korea/ 보존 | ✅ |
| LH1-B: trade/base_strategy.py 보존 | ✅ |
| LH1-C: trade/formula_manager.py 보존 | ❌ **N3 amend로 V3K hook 통합** |
| LH1-D: Kiwoom_OpenAPI/ + receiver/ 보존 | ✅ |

LH1 정합:
- formula_manager.py만 V3K hook 통합 허용 (default-OFF parity 보장 + exception guard)
- 다른 trade/ runtime 경로는 보존
- 정책 amend plan(f564d1a3) §3.4에서 명시적 결정

---

## §3. 검증 결과

### §3.1 정적 검증

| 파일 | py_compile |
| --- | --- |
| `trade/formula_manager.py` | ✅ OK |
| `scripts/audit_v3k_verify_1a.py` | ✅ OK |
| `scripts/smoke_v3k_formula_boundary_contract.py` | ✅ OK |
| `scripts/smoke_v3k_formula_runtime_hook_decision.py` | ✅ OK |

### §3.2 V3K audit suite

- `python scripts/audit_v3k_verify_1a.py --base 9423735e`: **PASS**
  - Kiwoom/runtime untouched audit passed
  - V3K feature flags default-OFF audit passed
  - Forbidden artifact guard passed
  - LS dependency marker audit passed
  - v3k verify-1a audit passed
- `python scripts/audit_v3k_phase_h_gate4_environment_status.py`: PASS
- `python scripts/verify_nonrelease_sync.py`: PASS
- `git diff --check`: PASS

### §3.3 Smoke 3건 (formula)

| smoke | 결과 |
| --- | --- |
| `smoke_v3k_formula_facade.py` | ✅ PASS |
| `smoke_v3k_formula_boundary_contract.py` | ✅ PASS (amend 후) |
| `smoke_v3k_formula_runtime_hook_decision.py` | ✅ PASS (amend 후) |

### §3.4 default-OFF parity 재검증 (T1 evidence 회귀 확인)

`scripts/backtest_v3k_phase_f_parity.py --report .omx/reports/v3k-phase-f-parity-n3-recheck.json` 실행 결과:

```
v3k phase f parity baseline passed
deltas: loss=0.00%/5.0%, mdd=0.00%/3.0%, trades=0.00%/10.0%
```

**N3 코드 변경 후에도 default-OFF parity ±0% 완벽 유지** — T1 evidence(`v3k-phase-f-parity-t1-9024e3b9.json`)와 동일한 결과.

---

## §4. 진척률 영향

### §4.1 분야 ④ 갱신

```
변경 전: 75%
변경 후: 100% (+25%p)
```

### §4.2 F6 산식 단독 영향

```
이전: (50+100+100+75+100+50+50)/700 = 525/700 = 75.0%   (N2 commit 후)
이후: (50+100+100+100+100+50+50)/700 = 550/700 = 78.6%   (N3 commit 후)
⊕ +3.6%p
```

### §4.3 5분야 master plan 진척

```
N1 ② 90→100%  ✅ 완료 (baed54f9)
N2 ③ 90→100%  ✅ 완료 (e566044c)
N3 ④ 75→100%  ✅ 완료 (본 commit)
N4 ⑥ 50→100%  ⏸ 다음 (~2시간 + 24h monitoring)
N5 ⑦ 50→100%  ⏸ 대기 (~2시간 + 48h monitoring)
N6 A5'        ⏸ 대기

진행: 3/6 (50%)
```

---

## §5. preparation-first §3 정합

| 허용 | 본 commit |
| --- | --- |
| docs 추가 | ✅ update_log + evidence |
| trade/ runtime hook 통합 (정책 amend) | ✅ formula_manager.py만 |
| audit guard amend | ✅ verify_1a search_roots |
| smoke amend (단계 졸업) | ✅ 2 smoke |
| default-OFF parity ±0% 검증 | ✅ |

| 금지 | 본 commit |
| --- | --- |
| 운영 `_database/` write | ❌ 0건 |
| feature flag default-ON | ❌ 0건 |
| trade/base_strategy.py 변경 | ❌ 0건 |
| trade/stock_korea/ 변경 | ❌ 0건 |
| backtest/backengine_base.py 변경 | ❌ 0건 (V3K hook은 strategy/v3k_analyzer_adapter.py에서) |
| LS direct dependency | ❌ 0건 |

→ 코드 P-lane 적격 (정책 amend 정합).

---

## §6. 검증

```powershell
python -m py_compile trade/formula_manager.py
python -m py_compile scripts/audit_v3k_verify_1a.py
python scripts/smoke_v3k_formula_facade.py
python scripts/smoke_v3k_formula_boundary_contract.py
python scripts/smoke_v3k_formula_runtime_hook_decision.py
python scripts/backtest_v3k_phase_f_parity.py
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
```

---

## §7. 다음 인계

5분야 master §3.4 **N4 (분야 ⑥ Phase F F-4 ON actual)** 진입 가능. 본 master에서 가장 큰 단계:

- 사용자 명시 phrase: `I approve phase-f-f4-on-await-user-approval only`
- USER_ACK env: `V3K_PHASE_F_USER_ACK=1`
- sidecar 토글 `phase_f_live_order_exit_wiring=true` 변경
- analyzer 7종이 매매 결정에 wiring
- **24h monitoring window** 필수

매매 영향 *고위험*. 진행 전 사용자 명시 ack 권장.

---

## §8. 관련 문서

- `docs/plans/2026-05-22_v3k_remaining_5fields_completion_master_plan.md` §3.3 N3
- `docs/plans/2026-05-22_v3k_f1_bypass_phase_fg_on_policy_amend_plan.md` §3.4 LH1 부분 떨어냄
- `docs/plans/2026-05-12_v3k_page_018_phase_d2_formula_runtime_hook_decision_plan.md` (Phase D-2 결정, N3에서 일부 졸업)
- `strategy/v3k_formula_facade.py` (line 113 V3KFormulaGlobalFacade)
- `trade/formula_manager.py:77` UpdateGlobalsFunc (변경 위치)
- `scripts/audit_v3k_verify_1a.py:129` _assert_no_v3k_imports_in_kiwoom_runtime (amend)
- `docs/evidence/v3k-n3-field4-formula-runtime-hook-9024e3b9.json` (본 evidence)
- `docs/evidence/v3k-phase-f-parity-t1-9024e3b9.json` (T1 parity baseline cross-ref)
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-N3-FIELD4-FORMULA-RUNTIME-HOOK-CLOSURE` 섹션)
