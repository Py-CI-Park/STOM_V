# V3K Page 017 — Phase D-1 formula/global dry-run adapter 계획

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_d0_formula_global_boundary_design.md`
- `docs/plans/2026-05-12_v3k_page_016_phase_d_formula_global_boundary_plan.md`

---

## 0. 목적

Page 017의 목적은 V3K formula/global 값을 실제 `globals().update(...)`에 주입하지 않고, 주입 후보와 충돌 진단만 산출하는 dry-run adapter/helper를 설계·구현하는 것이다.

이 단계는 V3K의 최종 목표인 "Kiwoom 유지 + LS증권 직접 의존성 제외 + V3 신기능 안전 이행"을 유지하면서, formula/global runtime 연결 전 마지막 안전장치 역할을 한다.

---

## 1. Page 017 in-scope

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| 017-1 | dry-run 입력 contract 정의 | 기존 `dict_add_func` 또는 formula names 후보를 입력받되 runtime global namespace를 변경하지 않는다. |
| 017-2 | V3K 후보 globals 산출 | `V3KFormulaGlobalFacade`를 사용해 `V3K_` prefixed callable 후보를 만든다. |
| 017-3 | collision diagnostics 구현 | 기존 key와 V3K 후보 key 교집합을 diagnostic으로 반환한다. |
| 017-4 | no-runtime-hook smoke 추가 | dry-run이 `FormulaManager.UpdateGlobalsFunc`, `globals().update`, DB write를 호출하지 않음을 검사한다. |
| 017-5 | Page 018 판단 | collision-free dry-run 결과를 바탕으로 실제 hook 설계로 갈지, 추가 보류할지 결정한다. |

현재 진행률:

```text
Page 017: [░░░░░░░░░░] 0 / 5 = 0%
```

---

## 2. Out-of-scope

| 항목 | 이유 |
| --- | --- |
| `globals().update` runtime hook 호출 | Page 017은 dry-run adapter page다. |
| `FormulaManager.UpdateGlobalsFunc` 수정 | 실제 runtime update point 변경은 Page 018 이후 판단한다. |
| Kiwoom 주문/청산/live runtime | Phase F/G 전까지 금지 |
| analyzer output trading decision | dry-run/collision 검증 전 금지 |
| 운영 `_database/setting.db` schema/write | 별도 migration/cutover/rollback plan 전까지 금지 |
| sidecar 파일/DB write | C2-7에서 보류한 persistence 영역 |
| LS증권 직접 의존성 | V3K 정의상 제외 |

---

## 3. 권장 구현 방향

- 가능하면 `strategy/v3k_formula_facade.py` 안에 side-effect-free helper를 추가하거나, 별도 `strategy/v3k_formula_global_dryrun.py`를 만든다.
- helper는 다음 값을 반환하는 것이 좋다.
  - `enabled`: feature flag 기준 dry-run이 활성인지
  - `candidate_keys`: V3K 후보 global key 목록
  - `collisions`: 기존 key와 후보 key의 교집합
  - `diagnostics`: disabled/collision/ready 상태 설명
  - `globals_dict`: 실제 주입 전 후보 dict. 단, 호출자가 명시적으로 사용하기 전까지 runtime에 반영하지 않는다.
- smoke는 source-level 검사와 behavior 검사 모두 포함한다.

---

## 4. 검증 기준

Page 017 완료 검증은 최소 다음을 통과해야 한다.

```powershell
python -m py_compile strategy/v3k_formula_facade.py trade/formula_manager.py trade/base_strategy.py scripts/smoke_v3k_formula_facade.py scripts/smoke_v3k_formula_boundary_contract.py
python scripts/smoke_v3k_formula_boundary_contract.py
python scripts/smoke_v3k_formula_facade.py
python scripts/smoke_v3k_gui_settings_preview.py
python scripts/smoke_v3k_settings_surface.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph
```

---

## 5. 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 017 Phase D-1 formula/global dry-run adapter를 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_017_phase_d1_formula_global_dryrun_plan.md와 docs/update_log/2026-05-12_v3k_phase_d0_formula_global_boundary_design.md를 기준으로, FormulaManager.UpdateGlobalsFunc 또는 globals().update를 호출하지 않고 V3K_ prefixed globals 후보와 collision diagnostics만 산출하는 dry-run adapter/helper를 설계/구현한다. Kiwoom 주문/청산/live runtime, analyzer output trading decision, 운영 _database/setting.db schema/write, sidecar 파일 write, LS Securities 직접 의존성은 변경하지 않는다. 완료 시 py_compile, smoke_v3k_formula_boundary_contract.py, smoke_v3k_formula_facade.py, smoke_v3k_gui_settings_preview, smoke_v3k_settings_surface, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
