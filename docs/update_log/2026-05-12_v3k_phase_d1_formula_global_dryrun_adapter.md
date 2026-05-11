# V3K Phase D-1 formula/global dry-run adapter 기록

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
이전 기준 commit: `0b13abc1 V3K formula/global 경계를 runtime hook 전에 고정한다`

---

## 1. 이번 작업의 목적

Page 016에서 formula/global runtime boundary를 고정했으므로, Page 017에서는 실제 runtime global namespace를 변경하지 않고 V3K formula/global 후보와 충돌 진단만 산출하는 dry-run adapter를 구현했다.

핵심 목적은 다음과 같다.

1. `FormulaManager.UpdateGlobalsFunc` 또는 `globals().update`를 호출하지 않는다.
2. V3K formula/global 후보 key를 계산한다.
3. 기존 formula/global key와 충돌하는지 확인한다.
4. 충돌이 없을 때만 future hook의 ready 상태로 판단할 수 있게 한다.
5. Kiwoom 유지, LS증권 직접 의존성 제외, default-OFF, no-DB-write contract를 유지한다.

---

## 2. 실행 방식

먼저 권장 Ralph 명령을 실행했다.

```powershell
omx ralph "force: V3K Page 017 Phase D-1 formula/global dry-run adapter ..."
```

결과는 Codex CLI TTY 제약으로 중단되었다.

```text
[ralph] Ralph persistence mode active. Launching Codex...
Error: stdin is not a terminal
```

따라서 동일 범위를 수동 실행으로 전환했다. 범위와 금지 조건은 Ralph prompt와 동일하게 유지했다.

---

## 3. 변경 내용

### 3.1 `strategy/v3k_formula_facade.py`

추가한 contract:

- `V3KFormulaGlobalDryRunResult`
- `V3KFormulaGlobalFacade.normalize_existing_keys()`
- `V3KFormulaGlobalFacade.dry_run()`

`dry_run()`은 기존 `build()` 결과를 재사용하되 다음 정보만 계산한다.

- 기존 key 정규화 결과
- V3K candidate key 목록
- collision 목록
- enabled/ready 상태
- diagnostic 메시지

중요하게도 `dry_run()`은 다음을 하지 않는다.

- `globals()` 호출
- `globals().update(...)` 호출
- `FormulaManager` import/call
- Kiwoom 주문/청산/live runtime 호출
- DB/sidecar 파일 write
- LS증권 직접 의존성 추가

### 3.2 `scripts/smoke_v3k_formula_facade.py`

추가한 behavior smoke:

- dry-run OFF no-op
- dry-run ready no-collision
- dry-run collision blocks ready

### 3.3 `scripts/smoke_v3k_formula_boundary_contract.py`

추가한 boundary smoke:

- V3K facade AST에 `globals()` call 자체가 없는지 검사
- dry-run collision-only 결과가 runtime artifact를 만들지 않는지 검사

---

## 4. 의도적으로 보류한 내용

| 보류 항목 | 이유 |
| --- | --- |
| `FormulaManager.UpdateGlobalsFunc` 수정 | VERIFY-1A runtime guard가 보호하는 고위험 runtime file이다. |
| `globals().update` 호출 | dry-run page의 범위를 넘어선다. |
| Kiwoom 주문/청산/live runtime 연결 | 거래 실행에 영향을 주므로 Phase F/G 전까지 금지다. |
| analyzer output trading decision 연결 | 학습/분석 데이터가 매매 판단에 직접 반영되는 고위험 단계다. |
| operating `_database/setting.db` 또는 sidecar write | 별도 migration/persistence plan 전까지 금지다. |
| LS증권 직접 의존성 | V3K의 Kiwoom 유지 목표와 충돌한다. |

---

## 5. 검증 결과

이번 단계에서 실행하고 통과한 검증:

```powershell
python -m py_compile strategy/v3k_formula_facade.py scripts/smoke_v3k_formula_facade.py scripts/smoke_v3k_formula_boundary_contract.py
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

- formula boundary contract smoke 통과
- formula/global facade smoke 통과
- dry-run OFF no-op 통과
- dry-run ready no-collision 통과
- dry-run collision blocks ready 통과
- GUI preview/settings surface smoke 통과
- VERIFY-1A/1B 통과
- nonrelease sync guard 통과
- `git diff --check` 통과
- DB/runtime artifact status 변경 없음

---

## 6. 현재 위치

```text
전체 V3K staged activation 진행률: [█████████░] 17 / 18 = 94.4%
현재 Page 017 진행률:          [██████████] 5 / 5 = 100%
다음 Page 018 진행률:          [░░░░░░░░░░] 0 / 5 = 0%
```

Page 017은 dry-run adapter 구현 단계로 완료한다. 다음은 Page 018에서 실제 runtime hook으로 진행할지, 혹은 hook 없이 callable 후보 제공 boundary를 유지할지 결정하는 단계다.
