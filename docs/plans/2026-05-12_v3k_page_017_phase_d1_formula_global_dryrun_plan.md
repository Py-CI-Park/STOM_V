# V3K Page 017 — Phase D-1 formula/global dry-run adapter 계획

작성일: 2026-05-12 KST
완료일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 commit: `0b13abc1 V3K formula/global 경계를 runtime hook 전에 고정한다`

기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_d0_formula_global_boundary_design.md`
- `docs/plans/2026-05-12_v3k_page_016_phase_d_formula_global_boundary_plan.md`
- `docs/update_log/2026-05-12_v3k_phase_d1_formula_global_dryrun_adapter.md`
- `docs/plans/2026-05-12_v3k_page_018_phase_d2_formula_runtime_hook_decision_plan.md`

---

## 0. 목적

Page 017의 목적은 V3K formula/global 값을 실제 `globals().update(...)`에 주입하지 않고, 주입 후보와 충돌 진단만 산출하는 dry-run adapter/helper를 설계·구현하는 것이다.

이 단계는 V3K의 최종 목표인 "Kiwoom 유지 + LS증권 직접 의존성 제외 + V3 신기능 안전 이행"을 유지하면서, formula/global runtime 연결 전 마지막 안전장치 역할을 한다.

---

## 1. Page 017 완료 결과

| Step | 작업 | 완료 결과 |
| ---: | --- | --- |
| 017-1 | dry-run 입력 contract 정의 | `V3KFormulaGlobalFacade.dry_run(request, existing)`이 기존 key iterable 또는 mapping을 입력받되 runtime global namespace를 변경하지 않도록 구현했다. |
| 017-2 | V3K 후보 globals 산출 | 기존 `V3KFormulaGlobalFacade.build()` 결과를 활용해 `V3K_` prefixed callable 후보 key와 candidate globals를 산출한다. |
| 017-3 | collision diagnostics 구현 | 기존 key와 후보 key 교집합을 `collisions`와 diagnostic 문자열로 반환한다. |
| 017-4 | no-runtime-hook smoke 추가 | `smoke_v3k_formula_facade.py`와 `smoke_v3k_formula_boundary_contract.py`에 OFF no-op, ready no-collision, collision blocks ready 검사를 추가했다. |
| 017-5 | Page 018 판단 | 실제 `globals().update` 연결은 아직 하지 않고, Page 018에서 guarded runtime hook 여부를 별도 판단하기로 했다. |

현재 진행률:

```text
Page 017: [██████████] 5 / 5 = 100%
```

---

## 2. 구현된 dry-run contract

### 2.1 `V3KFormulaGlobalDryRunResult`

`strategy/v3k_formula_facade.py`에 side-effect-free 결과 dataclass를 추가했다.

반환 필드:

- `formula_result`: 기존 facade build 결과
- `existing_keys`: 기존 formula/global key 정규화 결과
- `candidate_keys`: V3K 후보 global key 목록
- `collisions`: 기존 key와 V3K 후보 key의 교집합
- `diagnostics`: disabled, ready, collision 상태 설명
- `enabled`: 후보 globals가 생성되었는지
- `ready`: enabled이며 collisions가 없는지
- `globals_dict`: 실제 주입 전 후보 dict. 이 값은 반환만 하며 runtime에 반영하지 않는다.

### 2.2 `V3KFormulaGlobalFacade.dry_run()`

`dry_run()`은 다음 순서로 동작한다.

1. 기존 `build(request)`로 V3K candidate globals를 만든다.
2. 기존 key iterable 또는 mapping을 정규화한다.
3. candidate key와 기존 key의 충돌을 계산한다.
4. disabled/ready/collision diagnostic을 반환한다.
5. `FormulaManager.UpdateGlobalsFunc`, `globals().update`, Kiwoom 주문/청산/live runtime, DB write, sidecar write는 호출하지 않는다.

---

## 3. 의도적으로 하지 않은 작업

| 보류 항목 | 이유 | 다음 검토 지점 |
| --- | --- | --- |
| `FormulaManager.UpdateGlobalsFunc` 수정 | 현재 VERIFY-1A에서 runtime file 변경 금지 대상으로 보호 중이며, 실제 global namespace 변경 위험이 있다. | Page 018 guarded hook decision |
| `globals().update` 호출 | Page 017은 dry-run adapter page다. | Page 018 이후 go/no-go 결정 |
| analyzer output trading decision 활성화 | formula/global 후보 생성과 거래 판단 연결은 별도 위험 단계다. | Phase F/G |
| Kiwoom 주문/청산/live runtime 변경 | V3K data가 live trading에 연결되는 고위험 영역이다. | Phase F/G mock/regression 이후 |
| 운영 DB/sidecar persistence | C2-7과 DB migration 정책상 별도 plan 전까지 보류다. | DB/persistence 전용 page |
| LS증권 직접 의존성 | V3K 정의상 영구 제외다. | 반영 대상 아님 |

---

## 4. 검증 기준

Page 017 완료 검증은 다음을 통과했다.

- `python -m py_compile strategy/v3k_formula_facade.py scripts/smoke_v3k_formula_facade.py scripts/smoke_v3k_formula_boundary_contract.py`
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

## 5. 다음 페이지

다음은 Page 018 / Phase D-2 `formula/global guarded runtime hook decision`이다.

Page 018의 목적은 Page 017 dry-run 결과를 바탕으로 실제 runtime hook으로 진행할지, 혹은 hook 없이 callable 후보만 제공하는 activation boundary로 유지할지 결정하는 것이다. 이 단계에서도 즉시 broad runtime merge를 하지 말고, VERIFY-1A의 runtime file guard를 어떻게 유지·완화·대체할지 먼저 문서화해야 한다.

---

## 6. 다음 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 018 Phase D-2 formula/global guarded runtime hook decision을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_018_phase_d2_formula_runtime_hook_decision_plan.md와 docs/update_log/2026-05-12_v3k_phase_d1_formula_global_dryrun_adapter.md를 기준으로, Page 017 dry-run adapter 결과를 검토하여 실제 FormulaManager.UpdateGlobalsFunc/globals().update hook으로 갈지 또는 hook 없이 callable 후보 제공 boundary를 유지할지 결정한다. 먼저 VERIFY-1A runtime file guard, Kiwoom 주문/청산/live runtime, analyzer output trading decision, 운영 _database/setting.db schema/write, sidecar 파일 write, LS Securities 직접 의존성 변경 금지 조건을 재검토하고, hook을 구현하더라도 feature flag default-OFF와 collision-ready 조건이 깨지지 않도록 설계한다. 완료 시 py_compile, smoke_v3k_formula_boundary_contract.py, smoke_v3k_formula_facade.py, smoke_v3k_gui_settings_preview, smoke_v3k_settings_surface, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
