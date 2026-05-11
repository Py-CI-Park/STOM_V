# V3K Phase D-2 formula/global guarded runtime hook decision 기록

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
이전 기준 commit: `c67fdf9b V3K formula/global 주입 후보를 dry-run으로 진단한다`

---

## 1. 이번 작업의 목적

Page 017에서 `V3KFormulaGlobalFacade.dry_run()`을 구현해 candidate globals와 collision diagnostics를 산출할 수 있게 되었다. Page 018의 목적은 이 결과를 근거로 실제 `FormulaManager.UpdateGlobalsFunc` 또는 `globals().update` hook으로 들어갈지 결정하는 것이다.

---

## 2. 실행 방식

먼저 권장 Ralph 명령을 실행했다.

```powershell
omx ralph "force: V3K Page 018 Phase D-2 formula/global guarded runtime hook decision ..."
```

결과는 Codex CLI TTY 제약으로 중단되었다.

```text
[ralph] Ralph persistence mode active. Launching Codex...
Error: stdin is not a terminal
```

따라서 동일 범위를 수동 실행으로 전환했다. 범위와 금지 조건은 Ralph prompt와 동일하게 유지했다.

---

## 3. 핵심 검토

### 3.1 VERIFY-1A runtime guard

`audit_v3k_verify_1a.py`는 다음 파일을 forbidden runtime changed file로 보호한다.

- `trade/base_strategy.py`
- `trade/formula_manager.py`

또한 Kiwoom/runtime 경로에 `V3K` 또는 `v3k_` 문자열이 들어가는 것도 금지한다.

이는 지금까지 V3K를 안전하게 누적해 온 핵심 invariant다. Page 018에서 이 guard를 완화하면 Kiwoom live/order/exit runtime까지 영향을 줄 수 있으므로 이번 단계에서는 완화하지 않는다.

### 3.2 dry-run contract 평가

`V3KFormulaGlobalFacade.dry_run()`은 다음 조건을 만족한다.

- feature flag OFF이면 candidate key가 없다.
- feature flag ON이고 collision이 없으면 `ready=True`다.
- collision이 있으면 `ready=False`다.
- candidate globals는 반환하지만 runtime namespace에 반영하지 않는다.
- `globals()`와 `globals().update`를 호출하지 않는다.

이 contract는 future runtime hook의 선행 조건으로는 충분하다. 그러나 live strategy global namespace에 자동 주입할 승인 조건은 아직 아니다.

---

## 4. 결정

Page 018의 결정은 다음과 같다.

| 항목 | 결정 | 이유 |
| --- | --- | --- |
| `FormulaManager.UpdateGlobalsFunc` 수정 | 보류 | VERIFY-1A guard 위반이며 live formula namespace 변경 위험이 있다. |
| 직접 `globals().update` hook | 보류 | collision-ready contract는 있지만 runtime rollback/guard 완화가 아직 없다. |
| `V3KFormulaGlobalFacade.dry_run()` | 유지 | mutation 없이 candidate/collision 진단을 제공한다. |
| VERIFY-1A runtime guard | 유지 | Kiwoom 유지 custom lane의 안전 invariant다. |
| 다음 단계 | runtime activation gap review | 보류 항목 전체를 다시 우선순위화해야 한다. |

---

## 5. 추가한 검증 스크립트

추가 파일:

- `scripts/smoke_v3k_formula_runtime_hook_decision.py`

검사 내용:

1. VERIFY-1A가 여전히 `trade/base_strategy.py`, `trade/formula_manager.py`를 forbidden changed file로 보호하는지 확인한다.
2. trade runtime 파일에 V3K hook/import가 없는지 확인한다.
3. `strategy/v3k_formula_facade.py` AST에 `globals()` call과 trade runtime import가 없는지 확인한다.
4. dry-run이 OFF, ready, collision 상태를 정확히 반환하는지 확인한다.
5. 검사 전후 DB/runtime artifact status가 바뀌지 않는지 확인한다.

---

## 6. 의도적으로 보류한 내용

| 보류 항목 | 보류 이유 |
| --- | --- |
| formula/global runtime hook | VERIFY-1A runtime guard와 충돌하고 live formula namespace를 변경한다. |
| GUI setting persistence | C2-7에서 sidecar/DB persistence plan 전까지 보류했다. |
| analyzer DB constructor runtime use | 운영 DB read/write와 연결될 수 있어 별도 boundary가 필요하다. |
| live order/exit rule consumption | 실제 매매 판단에 영향을 주므로 Phase F/G 전까지 별도 검증이 필요하다. |
| production learning DB read | 운영 DB 내용/성능/락/rollback 검증이 아직 없다. |
| DB cutover/migration | migration/cutover/rollback plan이 별도로 필요하다. |
| LS증권 직접 의존성 | V3K 정의상 영구 제외다. |

---

## 7. 검증 결과

이번 단계에서 실행하고 통과한 검증:

```powershell
python -m py_compile scripts/smoke_v3k_formula_runtime_hook_decision.py
python scripts/smoke_v3k_formula_runtime_hook_decision.py
python -m py_compile strategy/v3k_formula_facade.py trade/formula_manager.py trade/base_strategy.py scripts/smoke_v3k_formula_facade.py scripts/smoke_v3k_formula_boundary_contract.py scripts/smoke_v3k_formula_runtime_hook_decision.py
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

결과:

- runtime hook decision smoke 통과
- formula boundary contract smoke 통과
- formula/global facade smoke 통과
- GUI preview/settings surface smoke 통과
- VERIFY-1A/1B 통과
- nonrelease sync guard 통과
- `git diff --check` 통과
- DB/runtime artifact status 변경 없음

---

## 8. 현재 위치

```text
전체 V3K staged activation 진행률: [█████████░] 18 / 19 = 94.7%
현재 Page 018 진행률:          [██████████] 5 / 5 = 100%
다음 Page 019 진행률:          [░░░░░░░░░░] 0 / 5 = 0%
```

Page 018은 direct runtime hook 보류 및 dry-run boundary 유지 결정으로 완료한다. 다음은 Page 019에서 intentionally held runtime activation 항목 전체를 다시 모아 다음 실제 구현 대상을 고르는 단계다.
