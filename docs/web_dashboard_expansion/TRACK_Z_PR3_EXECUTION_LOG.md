# Track Z — PR-3 실행 로그 (Story 3: FULL 변환)

> 2026-06-16 · 브랜치 `feature/webbt-track-z-pr3-convert` · 워크트리 `STOM_V.wt-webbt`
> 범위: **Story 3 only** — 26개 `frontend/*.jsx` 전부를 **dual-safe ESM**으로 변환. FLAGGED(STOM_BUNDLE=1) 번들이 실 per-module-scope 그래프가 되고, 기본 concat 빌드는 **바이트 불변**(운영 안전). **전환(flip)·concat 은퇴 없음 — Story 4는 미착수.**
> 입력: `TRACK_Z_DEPS.md`(64 cross-file edges, definer→consumer, ORDER) · `TRACK_Z_ALIASFREE_CLASSIFICATION.md`.

## 한 줄 결과
26개 전부 dual-safe ESM 변환 완료. FLAGGED 전체 번들이 **클린 빌드 + `require("react")` 0 + 2nd-React 센티넬 0 + App 마운트(#root 10,988자) + FROZEN 전역 재발행 + 단일 React 정체성 + 0 errors**(하네스 V2). 기본 빌드(플래그 OFF) **app.js 바이트 불변**(v=5d10d7ab, baseline 동일). 전체 unit: **신규 실패 0**(8개 사전존재 실패 유지). `verify_nonrelease_sync.py` exit 0.

---

## 변환 파일 (26/26)

### EXPORT 추가 (definer files — 말미 단일라인 `export { … };`)
panels(14), run-compare(1), engine(2, 스파이크), chart(9), hypothesis(1), table(1), cards(4), code-viewer(1), strategy-inspector(1), phase-detail(5 — PR-1 2개에서 확장), settings(1), analysis(2), research-pro(2), research-lab(4), research-wiki(1), glossary(1), backtest-charts(1), backtest(2), sim-live-chart(1), simulation-charts(5), simulation(1), evolution-analysis(1), dashboard-pages(3), app(2: App/ErrorBoundary).

### IMPORT 추가 (consumer files — top-level 단일라인 `import { … } from "./def.jsx";`)
| 소비 파일 | import | 정의 파일 | 비고 |
|-----------|--------|-----------|------|
| engine.jsx | DemoBadge, LivePending | phase-detail.jsx | 스파이크(기존) · bare+window |
| code-viewer.jsx | StrategyInspectorTabs | strategy-inspector.jsx | **!BWD 최고위험(순수 bare 호이스팅)** |
| research-lab.jsx | EdgeRatioPanel, FeatureImportancePanel | analysis.jsx | bare |
| backtest-charts.jsx | LegendDot, Mini, MetricHelpStrip | chart.jsx | bare(57건) |
| backtest.jsx | BtResultArea | backtest-charts.jsx | bare |
| simulation.jsx | SimOverlayChart, SimSignalLog | simulation-charts.jsx | bare(나머지 Sim*는 window.X 유지) |
| evolution-analysis.jsx | LegendDot, Mini | chart.jsx | bare |
| dashboard-pages.jsx | ResearchWikiPanel | research-wiki.jsx | bare(window 가드 하위) |
| app.jsx | 34 컴포넌트(15 import 라인) | panels/chart/cards/… | 최종 소비처 — bare 소비 전부 import |

### import 불필요(0개)
- **connection.jsx / ai-context.jsx**: cross-file 정의 없음(DEPS §1 line 106). connection은 stom-ui 별칭 + 자체 헬퍼만, ai-context는 DemoBadge를 window.X로 소비 → import 불필요.
- **research-pro.jsx**: 소비 심볼(BtResultArea/BtVarChips) 전부 `<window.X/>` + `typeof window.X` 가드(방어적 의도 보존) → import 강제 안 함, 엔트리 window 재발행으로 해소.
- **순수 definer leaves**(panels/run-compare/chart/hypothesis/table/cards/strategy-inspector/phase-detail/settings/analysis/research-wiki/glossary/sim-live-chart/simulation-charts): export만.

### DEPS 정정(grep 재검증으로 ALIASFREE §3 prose 일부 기각)
- sim-live-chart ↔ simulation-charts 상호 소비는 **주석 전용**(실 소비처는 simulation.jsx) → **순환 의존 없음**.
- hypothesis.jsx의 AutopsyPanel/QualityTrendChart, research-lab.jsx의 VerdictPanel, backtest-charts.jsx의 BacktestDetailChart 소비도 **주석 전용** → 해당 import 미추가.
- 권위 소스 = `TRACK_Z_DEPS.md §1`(grep·주석제거 검증) 테이블. ALIASFREE §3 산문은 보조.

### HARD 규칙 — stom-ui 12심볼 절대 import 금지(전부 window 유지)
`fmtScore/fmtPct/fmtMoney/fmtInt/fmtTime`, `STATUS_KR`, `isDemoSource`, `livePanelPending`, `_axisTicks`, `_priceTick`, `_hmsTimeLabel`, `STOM_PIPELINE` — 기존 `const X = window.X` 별칭 사이트(connection:914-919, chart:7, backtest-charts:49, sim-live-chart:46-47, simulation-charts:157-158, research-pro:802, research-lab:1046) **verbatim 보존**. 번들에서 bare 호출은 **런타임 전역 조회로 해소**(esbuild가 미선언 bare read를 global lookup으로 남김; stom-ui.js가 app.js보다 먼저 window 발행).

---

## 가드 완화 (의도 보존)

### 1. `test_p11_engine_gauges.py::TestInBrowserBabelConstraints::test_no_import_export_no_ts` (engine.jsx)
- **완화**: `startswith("import")`/`startswith("export")` 전면금지 → **dual-safe 단일라인만 허용**: `^import { … } from "./x.jsx";` + `^export { … };` (정규식). 그 외 모든 import/export 형태(`import X from`, `import * as`, `export default`, `export const/function`, `import type`)는 **계속 금지**. TS 문법 금지(`import type`/`export type`/`interface X {`/`enum X {`) **신규 추가**로 가드 핵심 의도(브라우저 babel/concat이 못 다루는 TS·임의 ESM 확산 차단) 강화.
- docstring에 RELAXED 사유 명시.

### 2. `test_phase9_spa_tabs.py::TestDashboardPages::test_no_import_export_no_ts` (dashboard-pages.jsx)
- 위와 동일한 완화·TS 가드 추가. docstring 갱신.

### 3. `test_track_z_pr1_harness.py` 스냅샷 3건 갱신(현실 반영, 의도 불변)
- `test_build_app_has_flag_path_and_export_stripper`: `_stripTopLevelExports` → **`_stripTopLevelEsm`**(rename; 이제 import+export 둘 다 strip).
- `test_pilot_entry_republishes_symbols`: 파일럿 republish 문자열 핀(`Object.assign(window,{DemoBadge,LivePending})`) → **불변식 단언**(phase-detail.jsx import 유지 + DemoBadge/LivePending republish + `Object.assign(window,` 존재)으로 완화(엔트리가 full-graph root로 확장됨).
- `test_phase_detail_is_esm_dual_safe`: `export { DemoBadge, LivePending };` 정확문자열 → **단일라인 export가 DemoBadge+LivePending 포함** 불변식(phase-detail export가 5심볼로 확장됨).

### 가드 외 import/export 금지 사이트 전수조사
`grep -rn 'startswith("import "\|startswith("export "' tests/unit` → **정확히 2건**(위 1·2). 그 외 모든 `import`/`export` 매치는 (a) stom-ui format.ts/mjs의 `export function …`(stom-ui 계약, 무관), (b) esbuild transform 테스트(loader:jsx, ESM 무해), (c) 주석/문서. 추가 완화 대상 없음.

---

## 엔트리 최종 형태 (`webui-build/src/track-z-entry.pilot.js`)
PR-1 파일럿(phase-detail만) → **full app-graph root**로 확장. 두 책임:
1. **Side-effect import**(window.X로만 소비돼 app.jsx 그래프에 미포함된 모듈의 `Object.assign(window,…)` 실행): `connection`(window.useBackend/DEFAULT_BASE/isDemoSource/livePanelPending), `ai-context`, `research-pro`(ResearchProPanel/ResearchHeatmapPanel), `research-wiki`(ResearchWikiPanel), `sim-live-chart`(SimLiveChart).
2. **Named import + FROZEN republish**: `App, ErrorBoundary`(app.jsx — 전체 bare 그래프를 끌어옴), `LabPage, ProPage, VerdictPanel`(dashboard-pages), DemoBadge/LivePending/Phase*/Engine*/Research*/Vdt*/BtResultArea/BtVarChips/SimCandleChart* → `Object.assign(window, { … })`.
- dashboard-pages.jsx의 verbatim `Object.assign(window, { LabPage, ProPage, VerdictPanel })`(test_phase9:59 단언) **소스에 보존**.
- esbuild가 충돌 심볼(connection `useBackend` → `useBackend2`)을 **모듈 스코프 내 리네임 + window 키는 원명 유지**(`useBackend: useBackend2`)로 발행 → app.jsx의 bare `useBackend`는 global lookup으로 window.useBackend 해소.

## 하네스 V2 갱신 (`track-z-harness.mjs`)
- V2: legacy `bundle/app.js` → **FLAGGED `.track-z/app.pilot.js`(전체 번들)** 로드. App 자동마운트 + FROZEN 전역(App/ErrorBoundary/LabPage/ProPage/VerdictPanel) + 단일 React 정체성 + lightweight-charts + dynamic-require 0 + errors 0 + #root 비어있지 않음 단언.
  - ⚠️ **범위 한정(아키텍트 nit — 정직성)**: V2는 index App을 **IDLE 상태**로 마운트한다 = *기본 탭(진화)의 idle 셸*만 렌더. backtest/simulation/lab/pro/verdict 탭과 비-idle 데이터 컴포넌트는 렌더되지 않는다. 따라서 "V2 통과"는 "전체 cross-file 와이어링이 런타임에 실행됨"이 아니라 **"idle index 셸이 단일-React로 0-error 렌더됨"**을 의미한다. 정적 와이어링은 esbuild `bundle:true`(잘못된/미존재 export import면 빌드 실패) + 독립 bare-usage 스윕(누락 import 0 확인)으로 닫혔고, **런타임 탭별 커버리지는 "Story 4 진입 게이트"로 이연**(flag OFF라 production 미도달).
    - ✅ **2026-06-16 해소**: 그 갭을 **V3(per-tab 6/6) + V4(standalone 3/3)** 로 닫음 — 아래 "Story 4 진입 게이트" 참조. 이제 하네스는 비-idle 진화탭 데이터 컴포넌트 + 5개 비-기본 탭 + 3개 standalone 페이지를 **전부 런타임 0-error로 렌더 검증**한다.
- V1: pilot 번들이 이제 full-graph라 stom-ui+lightweight-charts 선로드(전역 해소) → 깔끔한 단일-React/no-require 메커니즘 증명 유지.

---

## 게이트 증거 (배치별)

| 게이트 | Batch1(leaf export-only 14) | Batch2(consumer import+export 8) | app.jsx + 엔트리 |
|--------|------|------|------|
| flag-OFF `build-app.mjs` → app.js diff | EMPTY (v=5d10d7ab) | EMPTY | EMPTY |
| esbuild transform 26/26 | — | — | OK=26 BAD=0 |
| `pytest tests/unit/dashboard/` | 1 failed(사전존재 stale) / 527 passed | 1 failed / 527 passed | 1 failed / 527 passed |

### 최종 게이트
- **flag-OFF byte-unchanged**: `bundle/app.js` diff EMPTY (v=5d10d7ab = baseline). manifest.json·index.html 무변경.
- **FLAGGED `STOM_BUNDLE=1 node build-app.mjs`**: exit 0, v=dbebe317, `require("react")`=0, `react.development`=0, `__SECRET_INTERNALS`=0. (980KB 전체 앱)
- **`node track-z-harness.mjs`**: V1 pass(0 errors) + V2 pass(**0 errors, #root 10,988자, App 마운트, FROZEN 전역 ready, 단일 React 정체성**) → allPass=true.
- **`python scripts/verify_nonrelease_sync.py`**: exit 0.
- **full `pytest tests/unit/`**: (아래 표 참조) 8 failed = baseline floor, 신규 0.

### 사전존재 실패 floor (8 = 7 backend/CLI/PyQt + 1 stale)
1. `test_backtest_button_contract.py::test_backtest_constructor_contract_is_small_and_queue_driven`
2-3. `test_backtest_process_protocol_diagnostics.py::{test_backtest_start,test_total}_emits_key_protocol_checkpoints`
4-5. `test_backtest_spawn_contract_audit.py::test_{stock,coin}_backtest_spawn_does_not_pass_legacy_long_signature`
6. `test_runner_helpers.py::TestCliDictSetProcessArgs::test_backtest_process_passes_dict_set_to_constructor`
7. `test_ui_jisu_cleanup.py::test_v270_removed_jisu_chart_references_are_fully_cleaned`
8. `test_phase9_spa_tabs.py::TestDashboardPages::test_verdict_append_only_post_and_checklist` (stale — `const ICON = {` 부재; HEAD에도 없음 → PR-3 무관)

PR-1 스파이크가 유발했던 3개 실패(engine guard + PR-1 스냅샷 2)는 가드 완화로 해소(신규 실패 아님).

---

## Story 4 진입 게이트 (flip 전 필수 — 아키텍트 합의)
비가역 default-flip(Story 4) **착수 전에 반드시** 완료. PR-3의 유일한 잔여 리스크(비-기본탭 bare-consumer 누락 import → flip 시점에만 표면화)를 닫는다:
1. ✅ **DONE — 하네스 탭별 렌더 커버리지 (V3)**: `activeTab`을 evolution(비-idle)/backtest/simulation/lab/pro/verdict 6개 전부로 구동, 각 0 errors + #root 비어있지 않음 + ErrorBoundary 미발동 단언. 비-idle `/status` 픽스처(`RUNNING_STATE` — `controller/contract.py` LoopState/GenerationInfo/BestInfo/WinnerInfo/LatestInfo 정합)로 진화탭 데이터 컴포넌트(CurrentGenPanel·FitnessChart/ProfitChart/QualityTrendChart·GenerationsTable·BestCard/WinnerCard/MergedBestWinnerCard·HypothesisPanel 등)까지 실제 렌더. → **누락 import 0 발견**(전 탭 GREEN).
2. ✅ **DONE — lab/pro/verdict standalone 마운트 (V4)**: `window.__STOM_NO_AUTO_MOUNT__=true` + flagged 번들 로드 후 `ReactDOM.createRoot(...).render(React.createElement(window.LabPage/ProPage/VerdictPanel,{baseUrl}))`로 각 HTML 마운트를 그대로 재현, 3개 전부 0 errors + #root 비어있지 않음 단언. → **전부 GREEN**.
3. (선택·미착수) flagged 번들 esbuild metafile/no-undef 정적 넷 — bare ReferenceError 조기 포착. **V3/V4의 런타임 전탭 0-error 스윕으로 잔여 리스크는 실질 해소**(정적 넷은 보강용 옵션으로 남김).

### Story 4 진입 게이트 증거 (2026-06-16 · `track-z-harness.mjs` V3/V4 추가)
- **flag-OFF byte-unchanged**: `node build-app.mjs` → `git diff --stat bundle/app.js` **EMPTY**(운영 번들 불변).
- **FLAGGED 하네스**: `STOM_BUNDLE=1 node build-app.mjs` → `node track-z-harness.mjs` → exit 0, **allPass=true**.
  - V1 pass · V2 pass(idle index 셸).
  - **V3 per-tab(6/6 GREEN)**: evolution(rootLen 72,033 = 데이터 컴포넌트 렌더 확인) · backtest(12,244) · simulation(9,579) · lab(8,439) · pro(6,994) · verdict(5,301). 전부 errs=0 · boundary 미발동.
  - **V4 standalone(3/3 GREEN)**: lab(4,282) · pro(2,835) · verdict(1,142). 전부 errs=0 · mountError=None.
- **pytest 래퍼**: `tests/unit/dashboard/test_track_z_pr1_harness.py` **11 passed**(기존 9 + V3 `test_track_z_v3_per_tab_render_sweep` + V4 `test_track_z_v4_standalone_page_mounts`; node/esbuild/jsdom 게이트는 기존과 동일).
- **full `pytest tests/unit/`**: 신규 실패 0(8 사전존재 floor 유지).
- **`python scripts/verify_nonrelease_sync.py`**: exit 0.
- **변경 파일**: `webui-build/track-z-harness.mjs`(V3/V4 + `makeDom(opts)` 파라미터화 + `RUNNING_STATE` 픽스처) · `tests/unit/dashboard/test_track_z_pr1_harness.py`(V3/V4 래퍼 2건) · 본 실행 로그. **.jsx·app.py·번들 무변경**(번들은 테스트 대상이지 변경 대상 아님).

## STOP 조건
**26/26 변환 + ALL 게이트 GREEN.** 워킹트리 GREEN 상태. 본 PR(Story 3) 범위 완료 — Story 4 flip/concat 은퇴는 범위 외이며 위 진입 게이트 충족 후 별도 PR. 아키텍트 검증 = APPROVE-WITH-NITS(정적 와이어링 정확·완전; 하네스 커버리지 갭은 Story 4 진입 게이트로 이연).
