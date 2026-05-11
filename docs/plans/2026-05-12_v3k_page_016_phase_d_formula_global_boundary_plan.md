# V3K Page 016 — Phase D-0 formula/global runtime boundary design 계획

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 commit: `0949f31d V3K session-only preview를 Alt+V로 노출한다`
연결 문서:
- `docs/update_log/2026-05-12_v3k_phase_c2_7_gui_preview_closeout.md`
- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md`
- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md`

---

## 0. 목적

Page 016의 목적은 Phase D의 첫 단계로, V3K formula/global runtime 연결을 바로 구현하기 전에 충돌/주입/rollback 경계를 설계하는 것이다.

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

위 상태는 안전하지만 아직 실제 runtime의 `globals().update(...)`에는 연결하지 않았다.

---

## 2. Page 016 in-scope

| 항목 | 내용 |
| --- | --- |
| FormulaManager 경계 조사 | `trade/formula_manager.py::UpdateGlobalsFunc`의 기존 `globals().update` 사용 조건 확인 |
| BaseStrategy 경계 조사 | `trade/base_strategy.py`의 동적 formula function 생성과 충돌 가능성 확인 |
| V3K prefix collision 설계 | 기존 formula/global 이름과 `V3K_` prefixed names 충돌 여부 검사 기준 설계 |
| flag/rollback 설계 | OFF 기본값, session-only flag, future rollback flag 조건을 문서화 |
| smoke 계획 | source-level collision smoke 또는 dry-run smoke를 추가할지 판단 |

---

## 3. Out-of-scope

| 항목 | 이유 |
| --- | --- |
| `globals().update` runtime hook 구현 | Page 016은 design/inventory page다. |
| Kiwoom 주문/청산/live runtime | Phase E/F/G 전까지 금지 |
| analyzer output trading decision | Phase F/G 전까지 금지 |
| operating `_database/setting.db` schema/write | 별도 DB migration/cutover/rollback plan 전까지 금지 |
| sidecar 설정 파일/DB write | C2-7에서 보류 |
| LS Securities 직접 의존성 | V3K 정의상 영구 제외 |

---

## 4. 권장 진행 순서

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| 016-1 | formula runtime inventory | `FormulaManager.UpdateGlobalsFunc`, `BaseStrategy` formula func, `v3k_formula_facade` 경계 요약 |
| 016-2 | collision contract 작성 | `V3K_` prefix, 기존 formula names, callable keys 충돌 기준 문서화 |
| 016-3 | activation gate 설계 | feature flag, session-only preview, future rollback flag 조건 정리 |
| 016-4 | smoke 후보 결정 | source-level collision smoke를 추가할지 결정 |
| 016-5 | 다음 구현 page 판단 | Phase D-1 dry-run hook 설계/구현 또는 추가 inventory로 진행 |

현재 진행률:

```text
Page 016: [░░░░░░░░░░] 0 / 5 = 0%
```

---

## 5. 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 016 Phase D-0 formula/global runtime boundary design을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_016_phase_d_formula_global_boundary_plan.md와 docs/update_log/2026-05-12_v3k_phase_c2_7_gui_preview_closeout.md를 기준으로 trade/formula_manager.py의 UpdateGlobalsFunc, trade/base_strategy.py의 formula function 생성, strategy/v3k_formula_facade.py의 V3K_ prefixed globals facade 사이 충돌/주입 경계를 설계한다. 첫 단계에서는 globals().update runtime hook, Kiwoom 주문/청산/live runtime, analyzer output trading decision, 운영 _database/setting.db schema/write, sidecar 파일 write, LS Securities 직접 의존성을 변경하지 않는다. 결과를 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록하고 필요한 경우 source-level collision smoke 계획을 추가한 뒤 py_compile, smoke_v3k_formula_facade.py, smoke_v3k_gui_settings_preview, smoke_v3k_settings_surface, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 한국어 Lore commit한다."
```
