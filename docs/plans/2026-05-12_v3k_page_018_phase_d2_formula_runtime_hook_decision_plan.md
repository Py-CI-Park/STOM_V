# V3K Page 018 — Phase D-2 formula/global guarded runtime hook decision 계획

작성일: 2026-05-12 KST
완료일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 commit: `c67fdf9b V3K formula/global 주입 후보를 dry-run으로 진단한다`

기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_d1_formula_global_dryrun_adapter.md`
- `docs/plans/2026-05-12_v3k_page_017_phase_d1_formula_global_dryrun_plan.md`
- `docs/update_log/2026-05-12_v3k_phase_d2_formula_runtime_hook_decision.md`
- `docs/plans/2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md`

---

## 0. 목적

Page 018의 목적은 Page 017 dry-run adapter 결과를 바탕으로 실제 formula/global runtime hook으로 진행할지, 아니면 hook 없이 callable 후보 제공 boundary를 유지할지 결정하는 것이다.

중요한 점은 이 페이지도 즉시 broad merge가 아니다. 현재 VERIFY-1A는 `trade/formula_manager.py`, `trade/base_strategy.py` 같은 runtime file 변경을 금지하고 있다. 따라서 실제 hook을 구현하려면 guardrail 완화/대체/추가 smoke가 먼저 필요하다.

---

## 1. Page 018 완료 결정

| Step | 작업 | 완료 결과 |
| ---: | --- | --- |
| 018-1 | runtime guard 재검토 | VERIFY-1A가 `trade/formula_manager.py`, `trade/base_strategy.py` 변경을 금지하고 있음을 확인했다. 현재 guard를 완화하지 않는다. |
| 018-2 | dry-run 결과 평가 | `V3KFormulaGlobalFacade.dry_run()`의 ready/collision contract는 future hook의 선행 조건으로 충분하지만, 그 자체가 runtime hook 승인은 아니다. |
| 018-3 | hook 방식 결정 | 직접 `globals().update` hook은 보류한다. Page 018에서는 hook 없이 callable 후보 제공 boundary를 유지한다. |
| 018-4 | rollback/test 조건 정의 | default-OFF, collision block, Kiwoom untouched, DB artifact clean 조건을 계속 필수 조건으로 유지한다. |
| 018-5 | 다음 phase 판단 | Phase D는 runtime hook 보류 결정으로 닫고, Page 019에서 남은 runtime activation gap을 종합 재검토한다. |

현재 진행률:

```text
Page 018: [██████████] 5 / 5 = 100%
```

---

## 2. 결론

Page 018의 결론은 다음과 같다.

```text
Direct FormulaManager.UpdateGlobalsFunc/globals().update hook: 보류
V3KFormulaGlobalFacade.dry_run() callable 후보 제공 boundary: 유지
VERIFY-1A runtime file guard: 유지
다음 단계: runtime activation gap review에서 무엇을 실제로 풀지 재판단
```

이 결정은 V3K 목적을 포기하는 것이 아니다. 현재 단계에서 V3K formula/global 기능은 후보 생성, collision 진단, default-OFF rollback contract까지 구현되었다. 다만 이것을 live strategy global namespace에 자동 주입하는 것은 Kiwoom live/order/exit runtime과 연결될 수 있으므로 별도 guardrail 완화 없이 진행하지 않는다.

---

## 3. 검증 기준

Page 018 완료 검증은 다음을 통과했다.

- `python -m py_compile scripts/smoke_v3k_formula_runtime_hook_decision.py`
- `python scripts/smoke_v3k_formula_runtime_hook_decision.py`
- `python -m py_compile strategy/v3k_formula_facade.py trade/formula_manager.py trade/base_strategy.py scripts/smoke_v3k_formula_facade.py scripts/smoke_v3k_formula_boundary_contract.py scripts/smoke_v3k_formula_runtime_hook_decision.py`
- `python scripts/smoke_v3k_formula_boundary_contract.py`
- `python scripts/smoke_v3k_formula_facade.py`
- `python scripts/smoke_v3k_gui_settings_preview.py`
- `python scripts/smoke_v3k_settings_surface.py`
- `python scripts/audit_v3k_verify_1a.py --base 57496d24`
- `python scripts/audit_v3k_verify_1b_closure.py`
- `python scripts/verify_nonrelease_sync.py`
- `git diff --check`
- `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph`

---

## 4. 다음 페이지

다음은 Page 019 / Phase E-0 `runtime activation gap review`다.

Page 019의 목적은 지금까지 의도적으로 보류한 runtime activation 항목을 다시 모아, 다음 중 무엇을 실제로 구현 대상으로 전환할지 결정하는 것이다.

- formula/global runtime hook
- GUI setting persistence
- analyzer DB constructor runtime use
- live order/exit rule consumption
- production learning DB read
- DB cutover/migration

---

## 5. 다음 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 019 Phase E-0 runtime activation gap review를 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md와 docs/update_log/2026-05-12_v3k_phase_d2_formula_runtime_hook_decision.md를 기준으로, 지금까지 intentionally held로 남긴 runtime activation 항목을 모두 재검토한다. formula/global runtime hook, GUI setting persistence, analyzer DB constructor runtime use, live order/exit rule consumption, production learning DB read, DB cutover/migration 중 어떤 항목을 다음 구현 대상으로 전환할지 위험도·검증 가능성·Kiwoom 유지 조건 기준으로 우선순위를 정한다. LS Securities 직접 의존성은 계속 제외하고, 운영 _database/setting.db schema/write 또는 sidecar write는 별도 migration/persistence plan 없이 변경하지 않는다. 완료 시 py_compile, V3K smoke 전체, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
