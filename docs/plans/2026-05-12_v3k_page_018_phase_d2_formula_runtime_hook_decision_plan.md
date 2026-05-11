# V3K Page 018 — Phase D-2 formula/global guarded runtime hook decision 계획

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_d1_formula_global_dryrun_adapter.md`
- `docs/plans/2026-05-12_v3k_page_017_phase_d1_formula_global_dryrun_plan.md`

---

## 0. 목적

Page 018의 목적은 Page 017 dry-run adapter 결과를 바탕으로 실제 formula/global runtime hook으로 진행할지, 아니면 hook 없이 callable 후보 제공 boundary를 유지할지 결정하는 것이다.

중요한 점은 이 페이지도 즉시 broad merge가 아니다. 현재 VERIFY-1A는 `trade/formula_manager.py`, `trade/base_strategy.py` 같은 runtime file 변경을 금지하고 있다. 따라서 실제 hook을 구현하려면 guardrail 완화/대체/추가 smoke가 먼저 필요하다.

---

## 1. Page 018 in-scope

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| 018-1 | runtime guard 재검토 | VERIFY-1A runtime file guard를 유지할지, 제한적으로 완화할지, 별도 hook boundary로 우회할지 문서화한다. |
| 018-2 | dry-run 결과 평가 | `V3KFormulaGlobalFacade.dry_run()`의 ready/collision contract가 future hook 조건으로 충분한지 판단한다. |
| 018-3 | hook 방식 결정 | 실제 `globals().update` 연결, callable 후보 제공 유지, 또는 추가 보류 중 하나를 선택한다. |
| 018-4 | rollback/test 조건 정의 | default-OFF, collision block, Kiwoom untouched, DB artifact clean 조건을 future hook 기준으로 재정의한다. |
| 018-5 | 다음 phase 판단 | Phase D를 닫을지, D-3 guarded hook implementation으로 갈지 결정한다. |

현재 진행률:

```text
Page 018: [░░░░░░░░░░] 0 / 5 = 0%
```

---

## 2. Out-of-scope 기본값

다음은 별도 판단 전까지 계속 금지한다.

- Kiwoom 주문/청산/live runtime 변경
- analyzer output trading decision 활성화
- operating `_database/setting.db` schema/write
- sidecar 설정 파일/DB write
- LS증권 직접 의존성
- feature flag default-ON 전환

---

## 3. 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 018 Phase D-2 formula/global guarded runtime hook decision을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_018_phase_d2_formula_runtime_hook_decision_plan.md와 docs/update_log/2026-05-12_v3k_phase_d1_formula_global_dryrun_adapter.md를 기준으로, Page 017 dry-run adapter 결과를 검토하여 실제 FormulaManager.UpdateGlobalsFunc/globals().update hook으로 갈지 또는 hook 없이 callable 후보 제공 boundary를 유지할지 결정한다. 먼저 VERIFY-1A runtime file guard, Kiwoom 주문/청산/live runtime, analyzer output trading decision, 운영 _database/setting.db schema/write, sidecar 파일 write, LS Securities 직접 의존성 변경 금지 조건을 재검토하고, hook을 구현하더라도 feature flag default-OFF와 collision-ready 조건이 깨지지 않도록 설계한다. 완료 시 py_compile, smoke_v3k_formula_boundary_contract.py, smoke_v3k_formula_facade.py, smoke_v3k_gui_settings_preview, smoke_v3k_settings_surface, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
