# V3K Page 016 — Phase D-0 formula/global runtime boundary design 계획

작성일: 2026-05-12 KST
완료일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 commit: `5ed8cd2b V3K C2를 session-only GUI preview로 닫는다`

연결 문서:
- `docs/update_log/2026-05-12_v3k_phase_c2_7_gui_preview_closeout.md`
- `docs/update_log/2026-05-12_v3k_phase_d0_formula_global_boundary_design.md`
- `docs/plans/2026-05-12_v3k_page_017_phase_d1_formula_global_dryrun_plan.md`
- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md`
- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md`

---

## 0. 목적

Page 016의 목적은 Phase D의 첫 단계로, V3K formula/global runtime 연결을 바로 구현하기 전에 충돌·주입·rollback 경계를 설계하고 source-level smoke로 고정하는 것이다.

전체 V3K 목적은 계속 동일하다.

```text
STOM_Version_2U_C에서 Kiwoom 증권 API를 유지한다.
LS증권 직접 의존성은 제외한다.
V3의 분석·학습·DB·백테스트·실시간 사전학습 기능은 안전한 단계로 반영한다.
```

---

## 1. Phase D 배경

기존 V3K formula facade는 이미 `strategy/v3k_formula_facade.py`에 존재한다.

핵심 contract:

- `V3K_` prefix가 붙은 callable만 생성한다.
- `FLAG_FORMULA_GLOBAL_FACADE`와 `FLAG_STG_GLOBALS_FACADE`가 모두 켜져야 globals가 생성된다.
- feature flag가 OFF이면 globals가 생성되지 않는다.
- facade 자체는 Kiwoom runtime, formula manager runtime, 주문/청산 runtime을 import/call하지 않는다.
- 위 상태는 안전하지만 아직 실제 runtime의 `globals().update(...)`에는 연결하지 않았다.

---

## 2. Page 016 완료 결정

| Step | 작업 | 완료 결과 |
| ---: | --- | --- |
| 016-1 | formula runtime inventory | `trade/formula_manager.py::UpdateGlobalsFunc`가 현재 유일하게 `globals().update(dict_add_func)`를 수행하는 경계임을 확인했다. |
| 016-2 | BaseStrategy formula inventory | `trade/base_strategy.py`는 `dict_add_func[fm[0]] = create_func(fm[-1])`로 사용자 formula 이름을 callable key로 추가하고, 기본 `UpdateGlobalsFunc`는 `pass` 상태임을 확인했다. |
| 016-3 | collision contract 작성 | V3K global 후보는 반드시 `V3K_` prefix를 사용하고, 원본 analyzer field 이름과 직접 충돌하지 않아야 한다는 기준을 확정했다. |
| 016-4 | activation gate 설계 | feature flag OFF가 기본이며, ON이어도 facade는 dict 생성만 수행한다. runtime `globals().update` 호출은 Phase D-1/D-2 전까지 금지한다. |
| 016-5 | smoke 후보 결정 | `scripts/smoke_v3k_formula_boundary_contract.py`를 추가해 runtime hook 미주입, prefix/non-collision, default-OFF no-op, DB artifact 무변경을 검사한다. |

현재 진행률:

```text
Page 016: [██████████] 5 / 5 = 100%
```

---

## 3. 확정된 boundary contract

### 3.1 허용된 기존 runtime update point

- 기존 공식 runtime update point는 `FormulaManager.UpdateGlobalsFunc(self, dict_add_func)` 내부의 `globals().update(dict_add_func)`다.
- Page 016에서는 이 지점을 수정하지 않는다.
- V3K helper/facade는 이 지점을 직접 import하거나 호출하지 않는다.

### 3.2 BaseStrategy formula callable key 경계

- `BaseStrategy.SetGlobalsFunc`는 `self.fm_list` 기반으로 동적 formula callable을 만든다.
- callable key는 `fm[0]`이므로 사용자 정의 formula 이름과 전역 함수 이름 충돌 가능성이 존재한다.
- 따라서 V3K가 future runtime hook을 붙일 때는 기존 `dict_add_func` key와 충돌하지 않는지 dry-run으로 먼저 판단해야 한다.

### 3.3 V3K prefix contract

- V3K analyzer-derived callable은 `V3K_` prefix만 사용한다.
- 원본 analyzer field 이름(`risk`, `score`, `pattern`, `weight`, `confidence`)을 그대로 global에 주입하지 않는다.
- V3K prefix가 붙은 key라도 기존 runtime dict에 같은 key가 이미 있으면 future hook은 skip 또는 diagnostic 처리해야 한다.

### 3.4 activation/rollback contract

- default-OFF: `FLAG_FORMULA_GLOBAL_FACADE`와 `FLAG_STG_GLOBALS_FACADE`가 모두 켜지지 않으면 globals 후보를 만들지 않는다.
- session-only: 현재 GUI preview/flag는 session-only이며 operating `setting.db`나 sidecar에 저장하지 않는다.
- runtime hook 금지: Page 016에서는 `globals().update` 호출 경로를 추가하지 않는다.
- rollback 우선: future runtime hook 전에는 dry-run adapter, collision diagnostic, OFF regression smoke가 먼저 필요하다.

---

## 4. Page 016에서 하지 않은 것

| 보류 항목 | 보류 이유 |
| --- | --- |
| `FormulaManager.UpdateGlobalsFunc`에 V3K dict 주입 | 기존 전략 전역 namespace를 실제로 바꾸는 runtime hook이므로 Phase D-1/D-2 검증 전 금지 |
| Kiwoom 주문/청산/live runtime 변경 | Phase E/F/G 전까지 금지된 거래 runtime 영역 |
| analyzer output으로 매수/매도 판단 변경 | 학습 데이터가 거래 판단에 직접 연결되는 것은 별도 dry-run/rollback이 필요 |
| operating `_database/setting.db` schema/write | DB migration/cutover/rollback plan 전까지 금지 |
| sidecar 설정 파일/DB write | C2-7에서 의도적으로 보류한 persistence 영역 |
| LS증권 직접 의존성 | V3K 정의상 영구 제외 |

---

## 5. 검증 기준

Page 016 완료 검증은 다음을 통과했다.

- `python -m py_compile strategy/v3k_formula_facade.py trade/formula_manager.py trade/base_strategy.py scripts/smoke_v3k_formula_facade.py scripts/smoke_v3k_formula_boundary_contract.py`
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

## 6. 다음 페이지

다음은 Page 017 / Phase D-1 `formula/global dry-run adapter`다.

Page 017의 목적은 `FormulaManager.UpdateGlobalsFunc` 또는 `globals().update`를 호출하지 않고, V3K prefixed globals 후보와 collision diagnostics만 산출하는 dry-run adapter/helper를 만드는 것이다.

---

## 7. 다음 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 017 Phase D-1 formula/global dry-run adapter를 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_017_phase_d1_formula_global_dryrun_plan.md와 docs/update_log/2026-05-12_v3k_phase_d0_formula_global_boundary_design.md를 기준으로, FormulaManager.UpdateGlobalsFunc 또는 globals().update를 호출하지 않고 V3K_ prefixed globals 후보와 collision diagnostics만 산출하는 dry-run adapter/helper를 설계/구현한다. Kiwoom 주문/청산/live runtime, analyzer output trading decision, 운영 _database/setting.db schema/write, sidecar 파일 write, LS Securities 직접 의존성은 변경하지 않는다. 완료 시 py_compile, smoke_v3k_formula_boundary_contract.py, smoke_v3k_formula_facade.py, smoke_v3k_gui_settings_preview, smoke_v3k_settings_surface, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
