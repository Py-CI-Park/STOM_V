# TRACK_Z_TEST_COUPLING — concat-모델 결합 테스트 인벤토리 (Story 2)

> Track Z Story 2 감사 산출물. **코드 변경 없음 — 문서 전용.**
> 재-grep 명령 3종으로 이 세션에서 직접 검증: `==== ` 마커, `appSources`, `.index(/.find(` (jsx 마커 한정).
> 이 목록이 Story 5a(전체 테스트 마이그레이션)가 건드릴 정확한 파일·라인이다.
> 생성일: 2026-06-15. **PR-F 직전 재-grep 필수**(새 .jsx/새 테스트가 마커를 추가해 목록을 stale 하게 만들 수 있음 — Story 6).

---

## 0. 요약 (결론 먼저)

- **concat-모델 결합 테스트 = 17개 파일** (계획서의 16개 + 신규 Track-Z PR-1 테스트 1개).
- 계획서의 16개 인벤토리는 **정확** — 16개 모두 실재하는 `==== X.jsx ====` 마커 또는 `appSources` assert 확인.
- **누락 1개 발견:** `tests/unit/dashboard/test_track_z_pr1_harness.py` (라인 87-88, `appSources==26`). Story 1 PR-1 이 신설한 *의도적* flag-OFF 가드. 계획서 16에 미포함 → flip 시점(Story 4/5b)에 함께 마이그레이션 필요.
- **오탐 제외 확인(결합 아님):** `test_other_tabs_phase7.py`, `test_p11_*`, `test_p13_*`, `test_p2_structural.py`, `test_p3_consolidation.py`, `test_p4_functional.py` 의 `==== ` 출현은 전부 **Python 주석 구분선**(`# === ... === research-lab.jsx`) 또는 **.jsx 소스-영역 마커**(`function _Foo(` 사이 슬라이스)이며 `bundle/app.js` 의 concat 마커 assert 가 아니다. 마이그레이션 불필요.
- **계획서 라인 정정:** `test_p14_build_harness` — 마커 결합은 164/167-168 + appSources 203-204. 계획서가 든 195-196 은 `test_content_hash_cache_consistency`(별도 함수)의 `?v=` 해시 assert 로 **모델-무관, 유지 대상**. `test_dashboard_validation_views` — 마커 결합은 494-511 블록(presence 501 + load-order 504/507/509/511); 계획서의 449·631-632 는 `bundle/app.js` *presence* assert(모델-무관, 유지).

---

## 1. concat-결합 테스트 인벤토리 (검증된 파일 + assert 라인 + 분류)

분류:
- **build-model guard → replace stronger**: 빌드 모델 자체를 검사 → 새 모델 불변식(엔트리가 모듈셋 import; `require("react")` 없음; 2번째 React 없음; manifest `model==bundle`)으로 교체.
- **feature proxy (presence)**: `assert "==== X.jsx ====" in app_bundle` 가 "X 가 번들에 존재"의 프록시 → `assert "<X-symbol>" in app_bundle`(X 가 실제 정의/export 하는 심볼, 모델-무관)로 마이그레이션.
- **feature proxy (load-order)**: `app.index("==== A ====") < app.index("==== B ====")` → drop(모듈 스코프에서 텍스트 순서 무의미) 또는, 실제 렌더 의존이면 Story-1 런타임 하니스의 런타임 assert 로 재표현.

| # | 파일 | assert 라인 | 분류 |
|---|------|------------|------|
| 1 | tests/unit/dashboard/test_p14_build_harness.py | 164, 167, 168, 203, 204 | build-model guard → replace |
| 2 | tests/unit/dashboard/test_phase9_spa_tabs.py | 185-187 (`Object.assign` 리터럴 :59 와 별개 — :59 는 유지) | feature proxy (load-order) |
| 3 | tests/unit/dashboard/test_research_pro.py | 127, 128 | feature proxy (presence) |
| 4 | tests/unit/dashboard/test_sim_phase6_1.py | 169 | feature proxy (presence) |
| 5 | tests/unit/dashboard/test_tab_shell.py | 86, 87, 88, 89, 91 | feature proxy (presence 86-87 + load-order 88-91) |
| 6 | tests/unit/test_dashboard_validation_views.py | 501, 504, 507, 509, 511 (presence 501 + load-order 504/507/509/511) | feature proxy (presence+load-order) |
| 7 | tests/unit/test_dashboard_ai_context_pack.py | 172 | feature proxy (load-order) |
| 8 | tests/unit/test_dashboard_hypotheses.py | 135, 136 | feature proxy (presence 135 + load-order 136) |
| 9 | tests/unit/test_dashboard_integrated_layout.py | 49, 51, 53 | feature proxy (load-order) |
| 10 | tests/unit/test_dashboard_research_glossary_frontend.py | 46, 47 | feature proxy (load-order) |
| 11 | tests/unit/test_dashboard_research_lab_frontend.py | 57, 58 | feature proxy (presence 57 + load-order 58) |
| 12 | tests/unit/test_dashboard_run_compare_frontend.py | 54, 55, 56 | feature proxy (load-order) |
| 13 | tests/unit/test_dashboard_strategy_prompt_frontend.py | 67, 68, 69 | feature proxy (load-order) |
| 14 | tests/unit/test_dashboard_wiki_frontend.py | 38 | feature proxy (load-order) |
| 15 | tests/unit/test_tmap.py | 514 | feature proxy (presence) |
| 16 | tests/unit/test_analysis_gen_filter.py | 142 | feature proxy (presence) |
| 17 | tests/unit/dashboard/test_track_z_pr1_harness.py | 87, 88 (`test_default_concat_path_still_26_sources`) | build-model guard (flag-OFF 의도) → flip 시 갱신 |

**합계: 17개 파일** (계획서 16 + #17 신규).

### 1.1 각 행 상세 (검증된 assert 내용)

- **#1 test_p14_build_harness.py**
  - 164: `missing = [f for f in order if f"==== {f} ====" not in app_js]` → 전 ORDER 마커 존재 검사.
  - 167: `assert order[-1] == "app.jsx"`; 168: `assert "ReactDOM.createRoot" in app_js`.
  - 203: `assert manifest["appSources"][-1] == "app.jsx"`; 204: `assert len(manifest["appSources"]) == 26`.
  - **유지(결합 아님):** 195-196(`bundle/app.js?v={app_v}`/`stom-ui.js?v={stom_v}` 해시 일치, `test_content_hash_cache_consistency`) — 모델-무관 content-hash 가드. Story 5b 에서 KEEP.
- **#2 test_phase9_spa_tabs.py** 185-187: `pos_lab/pos_pro/pos_dp = app_bundle.find("==== research-lab/pro/dashboard-pages.jsx ====")` (그 다음 순서 비교). **:59 의 `Object.assign(window, { LabPage, ProPage, VerdictPanel })` 리터럴 assert 는 FROZEN 계약 — verbatim 유지.**
- **#3 test_research_pro.py** 127-128: `assert "==== research-pro.jsx ====" in app_bundle` / `"==== backtest-charts.jsx ===="`.
- **#4 test_sim_phase6_1.py** 169: `assert f"==== {dep} ====" in app_bundle` (루프).
- **#5 test_tab_shell.py** 86-87 presence(backtest/simulation), 88-89/91 load-order(`< app.jsx`, backtest-charts `<` backtest).
- **#6 test_dashboard_validation_views.py** `test_index_html_cache_bumped`: 501 presence 루프, 504 `_ord` 정의, 507/509/511 load-order 비교. **유지:** 449(`bundle/app.js` in lab.html), 492-493(`bundle/app.js?v=`/`stom-ui.js?v=` presence), 631-632(`bundle/app.js?v=` in lab.html) — 전부 모델-무관 presence.
- **#7 test_dashboard_ai_context_pack.py** 172: `app_bundle.index("==== ai-context.jsx ====") < app_bundle.index("==== app.jsx ====")`.
- **#8 test_dashboard_hypotheses.py** 135 presence, 136 load-order.
- **#9 test_dashboard_integrated_layout.py** 49 `app_pos = app.index("==== app.jsx ====")`, 51 `marker = f"==== {script} ===="`, 53 `assert app.index(marker) < app_pos`. **유지(결합 아님):** 29-32 의 `src.index('text="..."') < src.index("<Component")` 는 app.jsx *소스* 내 JSX 순서 검사(모델-무관, 마커 아님).
- **#10 test_dashboard_research_glossary_frontend.py** 46-47: glossary/app `.find("==== … ====")` (이후 순서 비교).
- **#11 test_dashboard_research_lab_frontend.py** 57 presence, 58 load-order.
- **#12 test_dashboard_run_compare_frontend.py** 54-56: panels/run-compare/app `.index("==== … ====")` (순서 비교).
- **#13 test_dashboard_strategy_prompt_frontend.py** 67-69: code-viewer/strategy-inspector/app `.index(…)` (순서 비교).
- **#14 test_dashboard_wiki_frontend.py** 38: research-wiki `<` app load-order.
- **#15 test_tmap.py** 514: `assert "==== research-lab.jsx ====" in app_bundle`.
- **#16 test_analysis_gen_filter.py** 142: `assert "==== research-lab.jsx ====" in app_bundle`.
- **#17 test_track_z_pr1_harness.py** 87-88: `appSources[-1]=="app.jsx"` / `len==26`. PR-1 이 "flag-OFF 기본값이 26-source concat 유지"를 보장하는 의도적 가드 → flip(Story 4) 시 갱신/제거.

---

## 2. 클래스별 마이그레이션 레시피

### A. build-model guard → strictly-stronger (대상: #1, #17 일부)

`==== {f} ====` 마커 존재 + `appSources==26` 검사를 새 모델 불변식으로 교체:
- `test_app_bundle_contains_all_ordered_sources` (26 마커, appSources==26) → **`test_app_bundle_single_entry_graph`**: 엔트리가 모듈셋을 import; `require("react")` 없음; 2번째 React sentinel(`react.development`/`__SECRET_INTERNALS_DO_NOT_USE`) 없음; manifest `model=="bundle"`.
- `test_content_hash_cache_consistency`: appSources==26/마커 assert 만 제거. **content-hash + 5개 HTML `?v=` 일치 assert 는 전부 KEEP.**
- 신규 `test_track_z_entry_exports_frozen_globals`: 엔트리 소스가 FROZEN+shared 명단을 `Object.assign(window, {…})` 로 발행 + phase9 verbatim 보존.
- `test_no_duplicate_globals` → **`test_no_window_global_leakage`**: 화이트리스트 FROZEN/shared 만 window 에 착지, 나머지 모듈-private.

### B. feature proxy (presence) → model-agnostic 심볼 assert (대상: #3, #4, #15, #16)

`assert "==== X.jsx ====" in app_bundle` → `assert "<X 가 실제 정의/export 하는 심볼>" in app_bundle`. 예: research-lab → `"function ResearchLabPanel("` 또는 `"VdtPromoteChecklist"`; research-pro → `"function ResearchProPanel("`; backtest-charts → `"function BtResultArea("`. (TRACK_Z_DEPS §1 의 definer 컬럼에서 심볼 선택 — 두 모델 모두에서 통과.)

### C. feature proxy (load-order) → drop 또는 런타임 재표현 (대상: #2, #5(88-91), #6(504-511), #7, #8(136), #9, #10, #11(58), #12, #13, #14)

`app.index("==== A ====") < app.index("==== B ====")` → **drop**(모듈 스코프에서 텍스트 순서 무의미). 단 실제 렌더 의존(예: research-* 가 dashboard-pages 보다 먼저 정의돼야 마운트)인 경우만 Story-1 런타임 하니스에서 `typeof window.X==='function'` + 마운트 무에러로 재표현. (대부분 단순 "정의가 app 보다 먼저" 류 → 모듈 모델에선 무의미하므로 drop.)

> Story 5a 는 위 **17개 전부**를 마이그레이션해야 한다. flip(PR-F) 직전 재-grep 으로 라인/목록 drift 재확인(Story 6 staleness 절).
