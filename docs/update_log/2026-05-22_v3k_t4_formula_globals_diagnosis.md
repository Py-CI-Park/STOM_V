# T4 — 분야 ④ 수식 전역값 공유 진단 보고서

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `397390f1` (T3 F5 closure 확인 직후) |
| 마스터 plan | `docs/plans/2026-05-22_v3k_backtest_track_5fields_sequential_execution_plan.md` §3.4 T4 |
| 본 commit 정체성 | 5개 분야 순차 plan T4 (분야 ④ 수식 전역값 공유) 진단 결과 정본화 |
| 코드 변경 | 0건 |
| 매매 영향 | 0건 |

---

## §0. TL;DR

```text
분야 ④ 수식 전역값 공유는 master plan 추정 50%보다 훨씬 풍부한 진척 상태.

핵심 자산:
  - strategy/v3k_formula_facade.py (313줄, 5 클래스)
  - Phase D0/D1/D2 3 sub-phase plan 모두 100% closure
  - Phase D2 (Page 018) 결정: runtime hook 보류 (VERIFY-1A guardrail 보존)
  - V3K-IMPL-5 registry 섹션 완비
  - smoke 3건 모두 PASS (facade / boundary_contract / runtime_hook_decision)

진척률 실측: 50% → 75% (+25%p)
잔여: runtime hook 통합 (Phase E0 이연, 매매 트랙에서 다룸)
```

---

## §1. 진단 산출 의도

5개 분야 순차 plan §3.4:

> 진단 대상: `strategy/v3k_formula_facade.py`
> 본 단계 목표: formula globals의 백테스트 read path 진척 측정 + 잔여 작업 plan
> 예상 시간: ~30분 진단 + ~15분 plan

본 commit은 진단 결과만 정본화하고 plan 작성은 *불필요*로 판정 (이유 §5 참조).

---

## §2. v3k_formula_facade.py 모듈 구조

`strategy/v3k_formula_facade.py` (313줄):

| line | 항목 | 역할 |
| ---: | --- | --- |
| 20 | `V3K_FORMULA_GLOBAL_PREFIX = "V3K_"` | namespace prefix |
| 54 | `V3KFormulaGlobalRequest` | 요청 dataclass |
| 63 | `V3KFormulaGlobalResult` | 결과 dataclass |
| 75 | `V3KFormulaGlobalDryRunResult` | dry-run 결과 |
| 98 | `V3KPhaseFFormulaResult` | Phase F 통합 결과 |
| 113 | **`V3KFormulaGlobalFacade`** | **메인 facade 클래스** |
| 181 | `build_values()` | V3 analyzer output → numeric values |
| 199 | `build_globals()` | values → prefixed globals dict (V3K_* namespace) |
| 230 | `build_phase_f()` | Phase F analyzer 통합 |
| 289 | `dry_run()` | ready/collision 검증 |

핵심 정책 (line 113-118 인용):

```python
"""Build a safe formula/global facade for staged V3K analyzer outputs.

The facade returns prefixed callable names that are suitable for a future
`globals().update(...)` boundary. It intentionally does not import or call
Kiwoom strategy, receiver, trader, order, or formula-manager runtime code.
"""
```

**핵심 invariant**: side-effect-free, runtime `globals().update()` 호출 안 함.

---

## §3. Feature flag 정책 (2단 게이트)

`strategy/v3k_analyzer_adapter.py` line 50-51:

```python
FLAG_FORMULA_MANAGER_ADAPTER = "V3K_FORMULA_MANAGER_ADAPTER"
FLAG_STG_GLOBALS_FACADE      = "V3K_STG_GLOBALS_FACADE"
```

`V3K-IMPL-5` registry §Decision 인용:

> The implementation follows the existing design flag names: `V3K_FORMULA_MANAGER_ADAPTER` and `V3K_STG_GLOBALS_FACADE`. **Both must be ON before prefixed globals are built.**

→ **2단 게이트** (두 flag 모두 ON 필요). 둘 다 default-OFF 유지.

---

## §4. Phase D 3 sub-phase closure 상태

기존 plan/update_log 7건 인용 + closure 확인:

| Sub-phase | Plan | 상태 |
| --- | --- | --- |
| Phase D0 boundary design | `2026-05-12_v3k_phase_d0_formula_global_boundary_design.md` | ✅ 완료 |
| Phase D 본체 | `2026-05-12_v3k_page_016_phase_d_formula_global_boundary_plan.md` | ✅ 완료 |
| Phase D1 dry-run adapter | `2026-05-12_v3k_phase_d1_formula_global_dryrun_adapter.md` + page_017 | ✅ 완료 |
| Phase D2 runtime hook decision | `2026-05-12_v3k_phase_d2_formula_runtime_hook_decision.md` + page_018 | ✅ **결정: 보류** |
| V3K-IMPL-5 본체 | `2026-05-09_v3k_impl_5_formula_global_facade.md` | ✅ 완료 |

### §4.1 Phase D2 (Page 018) 결정 — 핵심

Page 018 plan 본문 인용:

```
| Step | 작업 | 완료 결과 |
| ---: | --- | --- |
| 018-1 | runtime guard 재검토 | VERIFY-1A가 trade/formula_manager.py, trade/base_strategy.py
                              변경을 금지. 현재 guard를 완화하지 않는다. |
| 018-2 | dry-run 결과 평가 | V3KFormulaGlobalFacade.dry_run()의 ready/collision
                              contract는 future hook 선행 조건으로 충분하지만,
                              그 자체가 runtime hook 승인은 아니다. |
| 018-3 | hook 방식 결정 | 직접 globals().update hook은 보류. Page 018에서는 hook
                            없이 callable 후보 제공 boundary를 유지. |
| 018-4 | rollback/test 조건 | default-OFF, collision block, Kiwoom untouched,
                              DB artifact clean 조건 필수 |
| 018-5 | 다음 phase 판단 | Phase D는 runtime hook 보류 결정으로 닫고,
                            Page 019에서 남은 runtime activation gap을 종합 재검토 |

Page 018 진행률: [██████████] 5 / 5 = 100%
```

→ Phase D2 결정: **runtime hook 보류 + facade boundary 유지**. Phase E0(Page 019)로 이연.

### §4.2 Phase E0 이연 plan

```
docs/plans/2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md
```

Phase E0는 V3K 운영 활성화 gap을 종합 재검토하는 단계로, 매매 트랙(트랙 D) 활성화 시점에 함께 다뤄짐. 본 백테스트 트랙(트랙 A)에서는 다루지 않음.

---

## §5. Smoke 3건 실행 결과 (직접 검증)

본 PC `STOM_Version_2U_C` worktree에서 read-only 실행:

| # | smoke | 결과 | 검증 항목 |
| ---: | --- | --- | --- |
| 1 | `smoke_v3k_formula_facade.py` | ✅ PASS | dry-run ready no-collision + collision blocks ready |
| 2 | `smoke_v3k_formula_boundary_contract.py` | ✅ PASS | default-OFF no globals + dry-run adapter collision-only |
| 3 | `smoke_v3k_formula_runtime_hook_decision.py` | ✅ PASS | facade side-effect-free + dry-run boundary |

**총 3건 모두 PASS** — facade boundary + collision detection + side-effect-free 모두 동작 확인.

---

## §6. 백테스트 측 통합 위치

`scripts/backtest_v3k_phase_f_parity.py` (T1에서 실행한 그것)의 본문 head에서 다음 import 확인:

```python
from strategy.v3k_formula_facade import (
    V3KFormulaGlobalFacade,
    V3KFormulaGlobalRequest,
)
```

→ **T1 분석기 parity가 v3k_formula_facade를 이미 사용**. T1 결과 `candidate_formula_values` 13건이 facade를 통해 산출된 것이 증거.

다만 `backtest/backengine_base.py` 또는 `trade/base_strategy.py` runtime에서는 직접 import 안 함 (VERIFY-1A guard 정합).

---

## §7. 진척률 영향

### §7.1 분야 ④ 갱신

```
변경 전 (master plan 추정): 50%
변경 후 (T4 실측):          75% (+25%p)
```

산정 근거:

| 항목 | 점수 |
| --- | ---: |
| facade 본체 + 5 클래스 + 4 메서드 | 25점 |
| Phase D0/D1/D2 3 sub-phase plan closure | 20점 |
| V3K-IMPL-5 registry 등록 | 10점 |
| smoke 3건 모두 PASS | 15점 |
| 2단 game 정책 + namespace prefix | 5점 |
| **소계 (백테스트 영역)** | **75점** |
| runtime hook (Phase E0~) | 0점 (이연) |
| `globals().update()` 직접 통합 | 0점 (보류) |
| trade/formula_manager.py 통합 | 0점 (VERIFY-1A guard) |

본 분야의 *백테스트 영역*은 사실상 closure 상태이며, 잔여 25%는 모두 매매 트랙에서 다뤄짐.

### §7.2 F6 산식 단독 영향

```
이전: (50+90+75+50+100+50+50)/700 = 465/700 = 66.4%  (T3 commit 후)
이후: (50+90+75+75+100+50+50)/700 = 490/700 = 70.0%  (T4 진단 후)

⊕ +3.6%p
```

---

## §8. 잔여 작업 정리

### §8.1 분야 ④에서 미진행 (Phase E0 이연)

| 항목 | 보류 사유 |
| --- | --- |
| runtime hook (`globals().update()` 직접 통합) | VERIFY-1A guard가 `trade/formula_manager.py`, `trade/base_strategy.py` 변경 금지 |
| `V3K_FORMULA_MANAGER_ADAPTER` flag ON 전환 | 매매 결정 경로 영향, 트랙 D 활성화 시점 |
| `V3K_STG_GLOBALS_FACADE` flag ON 전환 | 동일 |

### §8.2 분야 ④ 진행 plan 작성 필요 여부

**불필요**. 이유:

1. Phase D0/D1/D2 + Phase E0 plan 4건이 이미 정본화되어 있음
2. 본 T4 진단 결과 분야 ④의 백테스트 영역은 사실상 완료
3. 잔여 runtime hook은 매매 트랙(트랙 D) 활성화 시점에 Phase E0 plan을 직접 인용

본 T4 commit은 진척률 실측 + Phase D 종결 확인 + Phase E0 이연 명시 baseline 역할.

---

## §9. preparation-first §3 정합

| 허용 | 본 commit |
| --- | --- |
| docs 추가 | ✅ update_log 1건 |
| read-only smoke 실행 | ✅ 3건 모두 default-OFF |
| 진단 read-only | ✅ |

| 금지 | 본 commit |
| --- | --- |
| 코드 변경 | ❌ 0건 |
| 운영 `_database/` write | ❌ 0건 |
| `V3K_FORMULA_*` flag ON 전환 | ❌ 0건 |
| LS direct dependency | ❌ 0건 |

→ P-lane 적격.

---

## §10. 검증

```powershell
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
```

---

## §11. 다음 인계

5개 분야 순차 plan 진척:

```
T1 ⑥ 분석기 parity            ✅ 완료 (26a10919)
T2 ⑦ 엔진 parity + benchmark  ✅ 완료 (26a10919)
T3 ② F5 마무리                ✅ 완료 (397390f1)
T4 ④ 수식 전역값 진단         ✅ 완료 (본 commit)
T5 ③ 사이드카 진단            ⏸ 다음 작업
```

4/5 완료 (80%). T5 (분야 ③ 사이드카 진단) 1건만 잔여.

---

## §12. 관련 문서

- `docs/plans/2026-05-22_v3k_backtest_track_5fields_sequential_execution_plan.md` §3.4 T4
- `strategy/v3k_formula_facade.py` (본 진단 대상, 313줄)
- `docs/update_log/2026-05-09_v3k_impl_5_formula_global_facade.md` (V3K-IMPL-5 본체)
- `docs/plans/2026-05-12_v3k_phase_d0_formula_global_boundary_design.md` (D0)
- `docs/plans/2026-05-12_v3k_page_016_phase_d_formula_global_boundary_plan.md` (D 본체)
- `docs/plans/2026-05-12_v3k_page_017_phase_d1_formula_global_dryrun_plan.md` (D1)
- `docs/plans/2026-05-12_v3k_page_018_phase_d2_formula_runtime_hook_decision_plan.md` (D2 결정)
- `docs/plans/2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md` (Phase E0 이연)
- `scripts/smoke_v3k_formula_facade.py`
- `scripts/smoke_v3k_formula_boundary_contract.py`
- `scripts/smoke_v3k_formula_runtime_hook_decision.py`
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-IMPL-5` line 518 + 본 commit `V3K-T4-FORMULA-GLOBALS-DIAGNOSIS` 섹션)
