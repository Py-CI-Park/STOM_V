# V3K Phase D-0 formula/global runtime boundary design 기록

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
이전 기준 commit: `5ed8cd2b V3K C2를 session-only GUI preview로 닫는다`

---

## 1. 이번 작업의 목적

C2 GUI preview는 session-only `Alt+V` launcher까지 완료되었다. 다음 위험 지점은 V3K analyzer/formula 값을 실제 전략 runtime의 전역 함수 공간에 연결하는 일이다.

Phase D-0의 목적은 바로 runtime hook을 붙이는 것이 아니라, 다음 네 가지를 먼저 고정하는 것이다.

1. 기존 STOM runtime에서 `globals().update(...)`가 어디에서 발생하는지 확인한다.
2. V3K formula facade가 side-effect-free 상태인지 검사한다.
3. V3K global name이 기존 formula/function 이름과 충돌하지 않도록 prefix contract를 확정한다.
4. 다음 Phase D-1 dry-run adapter에서 구현해야 할 진입/중단 조건을 문서화한다.

---

## 2. 실행 방식

먼저 권장 Ralph 명령을 실행했다.

```powershell
omx ralph "force: V3K Page 016 Phase D-0 formula/global runtime boundary design ..."
```

결과는 다음과 같이 Codex CLI TTY 제약으로 중단되었다.

```text
[ralph] Ralph persistence mode active. Launching Codex...
Error: stdin is not a terminal
```

따라서 동일 범위를 수동 실행으로 전환했다. 범위와 금지 조건은 Ralph prompt와 동일하게 유지했다.

---

## 3. 확인한 runtime boundary

### 3.1 `trade/formula_manager.py`

- `FormulaManager.UpdateGlobalsFunc(self, dict_add_func)`가 기존 `globals().update(dict_add_func)` 실행 지점이다.
- 이 함수는 실제 전략 formula callable을 Python global namespace에 반영하는 민감한 runtime hook이다.
- Page 016에서는 이 함수에 V3K import, V3K dict merge, V3K flag check를 추가하지 않았다.

### 3.2 `trade/base_strategy.py`

- `BaseStrategy.SetGlobalsFunc`는 `self.fm_list`를 순회하면서 `dict_add_func[fm[0]] = create_func(fm[-1])` 형태로 callable을 만든다.
- `fm[0]`은 사용자 formula 이름이므로 future V3K global name과 충돌할 수 있다.
- 기본 `BaseStrategy.UpdateGlobalsFunc`는 `pass`이고 실제 주입은 하위 runtime manager 경계에 위임된다.

### 3.3 `strategy/v3k_formula_facade.py`

- V3K facade는 `V3K_FORMULA_GLOBAL_PREFIX = "V3K_"`를 사용한다.
- feature flag가 OFF이면 globals를 만들지 않는다.
- feature flag가 ON이면 analyzer field를 `V3K_risk`, `V3K_score`, `V3K_pattern`, `V3K_weight`, `V3K_confidence` 같은 callable 후보로 만든다.
- trade runtime import, `FormulaManager` call, `globals().update` call, DB write, Kiwoom 주문 호출은 없다.

---

## 4. 확정한 contract

| 영역 | 결정 |
| --- | --- |
| Runtime hook | Page 016에서는 추가하지 않는다. 기존 `FormulaManager.UpdateGlobalsFunc`만 runtime update point로 인정한다. |
| V3K global name | 반드시 `V3K_` prefix를 사용한다. analyzer field 원본 이름을 그대로 global에 올리지 않는다. |
| Collision | future hook은 기존 `dict_add_func` key와 V3K 후보 key의 교집합을 먼저 검사해야 한다. 충돌 시 주입하지 않고 diagnostic 처리한다. |
| Default OFF | `FLAG_FORMULA_GLOBAL_FACADE`와 `FLAG_STG_GLOBALS_FACADE`가 모두 ON일 때만 후보 dict를 만든다. |
| Persistence | session-only flag만 사용한다. `setting.db`, sidecar, shadow DB에는 쓰지 않는다. |
| Broker | LS증권 직접 의존성은 추가하지 않는다. Kiwoom runtime도 Page 016에서는 건드리지 않는다. |

---

## 5. 추가한 검증 스크립트

추가 파일:

- `scripts/smoke_v3k_formula_boundary_contract.py`

검사 내용:

1. 기존 runtime update point가 예상 위치에 남아 있는지 확인한다.
2. V3K facade가 trade runtime import, `FormulaManager` call, 실제 `globals().update` call을 하지 않는지 AST 기반으로 확인한다.
3. `trade/formula_manager.py`, `trade/base_strategy.py`에 아직 V3K import/hook이 없는지 확인한다.
4. V3K global 후보가 모두 `V3K_` prefix를 사용하고 원본 analyzer field name과 충돌하지 않는지 확인한다.
5. feature flag default-OFF에서 globals가 생성되지 않는지 확인한다.
6. 검사 전후 `_database`, `_database_v3k_shadow`, `_log`, `backup`, `*.db`, `backtest/graph` 상태가 바뀌지 않는지 확인한다.

초기 smoke 작성 중 docstring/comment의 `globals().update`와 `Kiwoom` 설명 문구까지 runtime injection으로 오탐하는 문제가 있었다. 이를 AST 기반 실제 call/import 검사로 수정했다.

---

## 6. 의도적으로 하지 않은 작업과 이유

| 하지 않은 작업 | 이유 | 다음 검토 지점 |
| --- | --- | --- |
| `FormulaManager.UpdateGlobalsFunc`에 V3K dict merge 추가 | 실제 global namespace 변경이며 기존 전략 실행 결과에 영향을 줄 수 있다. | Page 017 dry-run adapter 후 Page 018 이후 hook 여부 판단 |
| Kiwoom 주문/청산/live runtime 연결 | V3K 학습/분석 값이 거래 실행으로 이어지는 고위험 영역이다. | Phase F/G에서 별도 mock/regression과 함께 검토 |
| analyzer output trading decision 활성화 | 학습 데이터의 매매 의사결정 반영은 rollback·audit·성능 검증이 필요하다. | formula dry-run, backtest dry-run 이후 검토 |
| 운영 `_database/setting.db` schema/write | DB migration/cutover/rollback 계획 전까지 금지다. | 별도 DB migration page |
| sidecar 설정 파일 write | C2-7에서 path/ignore/backup/corruption recovery 정책 전까지 보류했다. | sidecar persistence 전용 page |
| LS증권 직접 의존성 | V3K의 핵심 정의가 Kiwoom 유지이므로 영구 제외다. | 반영 대상 아님 |

---

## 7. 검증 결과

이번 단계에서 실행하고 통과한 검증:

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

결과:

- formula boundary contract smoke 통과
- formula/global facade smoke 통과
- GUI preview smoke 통과
- settings surface smoke 통과
- VERIFY-1A Kiwoom/runtime untouched, default-OFF, forbidden artifact, LS dependency marker audit 통과
- VERIFY-1B closure audit 통과
- nonrelease sync guard 통과
- `git diff --check` 통과
- DB/runtime artifact status 변경 없음

---

## 8. 현재 위치

```text
전체 V3K staged activation 진행률: [█████████░] 16 / 17 = 94.1%
현재 Page 016 진행률:          [██████████] 5 / 5 = 100%
다음 Page 017 진행률:          [░░░░░░░░░░] 0 / 5 = 0%
```

Page 016은 runtime hook 전 안전 경계 확정 단계로 완료한다. 다음은 Page 017에서 실제 `globals().update`를 호출하지 않는 dry-run adapter/helper를 만들어 collision diagnostics를 산출하는 단계다.
