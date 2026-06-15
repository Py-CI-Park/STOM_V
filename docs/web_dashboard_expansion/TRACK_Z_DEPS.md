# TRACK_Z_DEPS — 26 .jsx 파일 간 심볼 의존성 정밀 지도 (Story 2)

> Track Z(transform-concat → 실 ESM 번들) Story 2 감사 산출물. **코드 변경 없음 — 문서 전용.**
> 모든 행은 `ai_strategy_loop/dashboard/frontend/*.jsx` 26개 파일을 직접 grep/파싱해 근거를 확보했다(주석·문자열·동일파일 내부 사용 제외).
> 이 지도가 Story 3에서 어떤 파일에 `export` 가, 어떤 파일에 `import` 가 필요한지를 구동한다.
> 생성일: 2026-06-15. 재검증 클럭: PR-F 직전 재-grep 필수(Story 6 staleness 절).

---

## 0. 요약 (결론 먼저)

- **파일 간 공유 심볼 총 64개** (한 파일에서 정의→다른 파일에서 소비). 중복-정의(definer 모호) 심볼 **0개**.
- **역방향 참조 7건** (소비처 ORDER < 정의처 ORDER): 현재는 공유 스코프의 `function` 호이스팅 또는 방어적 `window.X` 참조로만 동작 → Story 3 변환 시 명시적 `import` 필요(최고 위험군).
- **stom-ui(format.ts) 호스팅 심볼 12개**는 HARD 규칙으로 **`window.` 참조 유지**(절대 import 변환 금지). §3 참조.
- **계획서 시드 정정:** `CodeBlock`(strategy-inspector) / `CvCodeBlock`(code-viewer)는 **파일 간 공유가 아니다** — 각자 정의 파일 *내부*에서만 소비된다. (`CvCodeBlock` 은 COLLISION_TAX #1 의 충돌 해소용 리네임이었고, 두 심볼은 의도적으로 분리됨.) Story 3에서 둘 다 `export` 불필요(cross-file 표면 0).

### 소비 스타일 표기

| 표기 | 의미 | Story 3 처리 |
|------|------|--------------|
| `bare` | 정의처와 다른 파일에서 bare JSX `<X/>` 또는 bare 식별자로 소비 (공유 스코프 의존) | 명시적 `import { X }` 추가 (definer가 in-bundle) |
| `window.X` | `<window.X/>` 멤버표현식 또는 `window.X`(typeof 가드 등) 방어적 참조 | definer가 in-bundle이면 import 로 전환 가능; stom-ui 호스팅이면 **유지** |
| `bare+window.X` | 같은 소비 파일이 두 스타일 모두 사용 | import 로 통일(in-bundle인 경우) |
| `!BWD` | 소비처 ORDER 인덱스 < 정의처 ORDER 인덱스 (역방향) | 명시적 import 가 특히 필수 |

ORDER 인덱스는 `webui-build/build-app.mjs` 의 `ORDER` 배열(O0=connection … O25=app) 기준.

---

## 1. 파일 간 공유 심볼 지도 (definer ORDER 순)

| 심볼 | 정의 파일 | O | 소비 파일(O, 스타일) |
|------|-----------|---|----------------------|
| ActiveConfigPanel | panels.jsx | O1 | app(O25):bare |
| ActiveStrategyPanel | panels.jsx | O1 | app(O25):bare |
| AutopsyPanel | panels.jsx | O1 | app(O25):bare |
| ConnBadge | panels.jsx | O1 | app(O25):bare |
| CostPanel | panels.jsx | O1 | app(O25):bare |
| CurrentGenPanel | panels.jsx | O1 | app(O25):bare |
| ExportStatusBanner | panels.jsx | O1 | app(O25):bare |
| FeedbackPanel | panels.jsx | O1 | app(O25):bare |
| HoldoutPanel | panels.jsx | O1 | app(O25):bare |
| LineagePanel | panels.jsx | O1 | app(O25):bare |
| MetaPanel | panels.jsx | O1 | app(O25):bare |
| PopulationPanel | panels.jsx | O1 | app(O25):bare |
| ResearchCriteriaBanner | panels.jsx | O1 | app(O25):bare |
| StatusBadge | panels.jsx | O1 | app(O25):bare |
| RunComparePanel | run-compare.jsx | O2 | app(O25):bare |
| EnginePanel | engine.jsx | O3 | app(O25):bare |
| LiveBacktestChart | engine.jsx | O3 | phase-detail(O10):window.X |
| BacktestDetailChart | chart.jsx | O4 | app(O25):bare |
| EquityOverlayChart | chart.jsx | O4 | app(O25):bare |
| FitnessChart | chart.jsx | O4 | app(O25):bare |
| HallOfFamePanel | chart.jsx | O4 | app(O25):bare |
| LegendDot | chart.jsx | O4 | backtest-charts(O18):bare; evolution-analysis(O23):bare |
| MetricHelpStrip | chart.jsx | O4 | backtest-charts(O18):bare |
| Mini | chart.jsx | O4 | backtest-charts(O18):bare; evolution-analysis(O23):bare |
| ProfitChart | chart.jsx | O4 | app(O25):bare |
| QualityTrendChart | chart.jsx | O4 | app(O25):bare |
| HypothesisPanel | hypothesis.jsx | O5 | app(O25):bare |
| GenerationsTable | table.jsx | O6 | app(O25):bare |
| ApprovalDialog | cards.jsx | O7 | app(O25):bare |
| BestCard | cards.jsx | O7 | app(O25):bare |
| MergedBestWinnerCard | cards.jsx | O7 | app(O25):bare |
| WinnerCard | cards.jsx | O7 | app(O25):bare |
| CodeViewer | code-viewer.jsx | O8 | app(O25):bare |
| StrategyInspectorTabs | strategy-inspector.jsx | O9 | code-viewer(O8 **!BWD**):bare |
| DemoBadge | phase-detail.jsx | O10 | ai-context(O16):window.X; analysis(O12):window.X; engine(O3 **!BWD**):bare+window.X; panels(O1 **!BWD**):window.X; research-wiki(O15):window.X; run-compare(O2 **!BWD**):window.X |
| LivePending | phase-detail.jsx | O10 | engine(O3 **!BWD**):bare+window.X |
| PhaseDetailPanel | phase-detail.jsx | O10 | app(O25):bare |
| PhaseTimeline | phase-detail.jsx | O10 | app(O25):bare |
| ProcessFlowPanel | phase-detail.jsx | O10 | app(O25):bare |
| SettingsModal | settings.jsx | O11 | app(O25):bare |
| EdgeRatioPanel | analysis.jsx | O12 | research-lab(O14):bare |
| FeatureImportancePanel | analysis.jsx | O12 | research-lab(O14):bare |
| ResearchHeatmapPanel | research-pro.jsx | O13 | app(O25):window.X |
| ResearchProPanel | research-pro.jsx | O13 | dashboard-pages(O24):window.X |
| ResearchLabPanel | research-lab.jsx | O14 | app(O25):bare; dashboard-pages(O24):window.X |
| VdtAlerts | research-lab.jsx | O14 | dashboard-pages(O24):window.X |
| VdtPromoteChecklist | research-lab.jsx | O14 | dashboard-pages(O24):window.X |
| VdtSummaryLines | research-lab.jsx | O14 | dashboard-pages(O24):window.X |
| ResearchWikiPanel | research-wiki.jsx | O15 | dashboard-pages(O24):bare+window.X |
| ResearchGlossaryPanel | glossary.jsx | O17 | app(O25):bare |
| BtResultArea | backtest-charts.jsx | O18 | backtest(O19):bare; research-pro(O13 **!BWD**):bare+window.X |
| BacktestTab | backtest.jsx | O19 | app(O25):bare |
| BtVarChips | backtest.jsx | O19 | research-pro(O13 **!BWD**):window.X |
| SimLiveChart | sim-live-chart.jsx | O20 | simulation(O22):window.X |
| SimCandleChart | simulation-charts.jsx | O21 | simulation(O22):window.X |
| SimCandleChartLWC | simulation-charts.jsx | O21 | simulation(O22):window.X |
| SimCandleChartSVG | simulation-charts.jsx | O21 | simulation(O22):window.X |
| SimOverlayChart | simulation-charts.jsx | O21 | simulation(O22):bare |
| SimSignalLog | simulation-charts.jsx | O21 | simulation(O22):bare |
| SimulationTab | simulation.jsx | O22 | app(O25):bare |
| EvolutionAnalysisPanel | evolution-analysis.jsx | O23 | app(O25):bare |
| LabPage | dashboard-pages.jsx | O24 | app(O25):window.X |
| ProPage | dashboard-pages.jsx | O24 | app(O25):window.X |
| VerdictPanel | dashboard-pages.jsx | O24 | app(O25):window.X |

**합계: 64개 파일 간 공유 심볼.**

### 정의처별 export 필요 파일 (Story 3 입력)

다음 16개 파일이 1개 이상 cross-file 심볼을 정의 → 모두 `export` 추가 대상:
panels(14), chart(8), cards(4), phase-detail(5), simulation-charts(5), research-lab(4), dashboard-pages(3), analysis(2), research-pro(2), backtest(2), run-compare(1), engine(2), hypothesis(1), table(1), code-viewer(1), strategy-inspector(1), settings(1), research-wiki(1), glossary(1), backtest-charts(1), sim-live-chart(1), simulation(1), evolution-analysis(1).

소비만 하고 cross-file 정의가 없는 파일(export 불필요): `app.jsx`(최종 소비처/엔트리), `ai-context.jsx`, `connection.jsx`. 단 app.jsx 는 엔트리로서 §4 의 FROZEN+shared `Object.assign(window,{…})` 재발행 책임을 진다.

---

## 2. 역방향 참조 (소비처 ORDER < 정의처 ORDER) — 최고 위험군

> 현재 동작 메커니즘: 공유 단일 스코프에서 (a) `function` 선언 호이스팅, 또는 (b) 방어적 `window.X` 참조(런타임 시점엔 이미 정의됨). 모듈 스코프 분리 후엔 **둘 다 명시적 import 없으면 ReferenceError.** Story 3에서 이 7건이 가장 먼저/신중히 처리돼야 한다.

| # | 심볼 | 정의처(O) | 소비처(O) | 현재 안전 메커니즘 |
|---|------|-----------|-----------|--------------------|
| 1 | StrategyInspectorTabs | strategy-inspector(O9) | code-viewer(O8) | `function` 호이스팅 (bare `<StrategyInspectorTabs/>`) |
| 2 | DemoBadge | phase-detail(O10) | engine(O3) | bare + 방어적 window.X 병용 |
| 3 | DemoBadge | phase-detail(O10) | panels(O1) | `<window.DemoBadge/>` 방어적 |
| 4 | DemoBadge | phase-detail(O10) | run-compare(O2) | `<window.DemoBadge/>` 방어적 |
| 5 | LivePending | phase-detail(O10) | engine(O3) | bare + 방어적 window.X 병용 |
| 6 | BtResultArea | backtest-charts(O18) | research-pro(O13) | bare + `<window.BtResultArea/>` 방어적 |
| 7 | BtVarChips | backtest(O19) | research-pro(O13) | `typeof window.BtVarChips === "function"` 가드 (research-pro.jsx:79-80) |

**관찰:** 역방향 참조 7건 중 6건은 이미 `window.X` 방어층을 가진다(엔트리가 `window` 재발행을 보장하면 import 없이도 안전). 유일하게 순수 bare(호이스팅 의존)인 것은 #1 `StrategyInspectorTabs`(code-viewer→strategy-inspector) — 이것이 모듈 분리 시 가장 깨지기 쉬운 단일 지점이다.

---

## 3. HARD 규칙 — stom-ui(format.ts) 호스팅 심볼: `window.` 유지 (절대 import 변환 금지)

> 근거: 이 심볼들은 `webui-build/src/format.ts` 에서 정의되어 별도 산출물 `bundle/stom-ui.js`(vite lib, `type=module`, app.js 보다 먼저 로드)가 `Object.assign(window, {...})` 로 발행한다(format.ts:119-126). app.js 번들은 이들을 import 할 수 없다(다른 번들·다른 캐시). import 변환 시 cross-bundle ReferenceError 또는 stom-ui 강제 fold-in(Story 0.A 위반).

### 3.1 format.ts 가 발행하는 정확한 window.* export 집합 (12개) — format.ts:120-125 검증

```
fmtScore, fmtPct, fmtMoney, fmtInt, fmtTime,
STATUS_KR, isDemoSource, livePanelPending,
_axisTicks, _priceTick, _hmsTimeLabel,
STOM_PIPELINE
```

이 12개는 Story 3에서 **`window.` 참조로 유지** — `import` 로 전환하지 않는다. (계획서가 나열한 `fmt*`/`STATUS_KR`/`_axisTicks`/`_priceTick`/`_hmsTimeLabel`/`STOM_PIPELINE`/`isDemoSource`/`livePanelPending` 와 정확히 일치.)

### 3.2 기존 `const X = window.X` 별칭 사이트 (verbatim 보존 대상) — 직접 grep 검증

| 파일:라인 | 별칭 선언 | 호스팅 심볼 |
|-----------|-----------|-------------|
| connection.jsx:914 | `const fmtScore = window.fmtScore;` | fmtScore |
| connection.jsx:915 | `const fmtPct = window.fmtPct;` | fmtPct |
| connection.jsx:916 | `const fmtMoney = window.fmtMoney;` | fmtMoney |
| connection.jsx:917 | `const fmtInt = window.fmtInt;` | fmtInt |
| connection.jsx:918 | `const fmtTime = window.fmtTime;` | fmtTime |
| connection.jsx:919 | `const STATUS_KR = window.STATUS_KR;` | STATUS_KR |
| chart.jsx:7 | `const _axisTicks = window._axisTicks;` | _axisTicks |
| backtest-charts.jsx:49 | `const _btAxisTicks = window._axisTicks;` | _axisTicks |
| sim-live-chart.jsx:46 | `const _slcTimeLabel = window._hmsTimeLabel;` | _hmsTimeLabel |
| sim-live-chart.jsx:47 | `const _slcPriceTick = window._priceTick;` | _priceTick |
| simulation-charts.jsx:157 | `const _simTimeLabel = window._hmsTimeLabel;` | _hmsTimeLabel |
| simulation-charts.jsx:158 | `const _simPriceTick = window._priceTick;` | _priceTick |
| research-pro.jsx:802 | `const PIPELINE = window.STOM_PIPELINE \|\| [];` | STOM_PIPELINE |
| research-lab.jsx:1046 | `const PIPELINE = window.STOM_PIPELINE \|\| [];` | STOM_PIPELINE |

> `isDemoSource`/`livePanelPending`/`fmt*` 의 직접 `window.fmt*(…)` 호출 사이트도 다수 존재(전 frontend 합계 70건/18파일) — 별칭을 거치지 않고 `window.` 직접 호출하는 형태 포함. 전부 stom-ui 계약이므로 동일하게 유지.

`test_p14_build_harness.py`(라인 107-109, 134 영역)가 connection.jsx + chart.jsx 의 이 별칭들을 계속 assert한다 → 보존 필수.

---

## 4. FROZEN 전역 재발행 책임 (엔트리)

> Story 3/4에서 IIFE 스코프가 bare `function` 선언을 숨기므로, 엔트리 모듈이 FROZEN + cross-consumed shared 심볼을 명시적 `Object.assign(window, {...})` 로 재발행해야 한다.

- **FROZEN(HTML mount-by-name) 필수:** `App`, `ErrorBoundary`(app.jsx:691 의 `Object.assign(window,{App, ErrorBoundary})` 경로), `LabPage`/`ProPage`/`VerdictPanel`(dashboard-pages.jsx). **`Object.assign(window, { LabPage, ProPage, VerdictPanel })` 문자열은 verbatim 보존** — `test_phase9_spa_tabs.py:59` 가 그대로 assert.
- **방어적 `window.X` 로 소비되는 shared 컴포넌트(재발행 안 하면 standalone 페이지 무음 깨짐):** `DemoBadge`, `LivePending`, `LiveBacktestChart`, `ResearchHeatmapPanel`, `ResearchProPanel`, `ResearchLabPanel`, `VdtAlerts`, `VdtPromoteChecklist`, `VdtSummaryLines`, `ResearchWikiPanel`, `BtResultArea`, `BtVarChips`, `SimLiveChart`, `SimCandleChart`, `SimCandleChartLWC`, `SimCandleChartSVG`. (§1 에서 스타일에 `window.X` 가 포함된 전부.)

이들 각각은 Story 1 런타임 하니스가 `typeof window.X === 'function'` 로 검증한다(소스 토큰 아님).

---

## 5. 검증 방법 (재현)

- 정의 추출: 26 .jsx 각 파일의 최상위 `function|class|const X =` 패턴 → PascalCase 컴포넌트 후보 154개.
- 소비 스캔: 각 심볼을 다른 25파일에서 `<X[\s/>]`(bare JSX), `<window.X[\s/>]`, `window.X\b`, bare 식별자(앞에 `.`/단어경계 아님)로 검색. **블록/라인 주석 제거 후** 판정(주석-only 오탐 2건 제거: ErrorBoundary→analysis, LiveBacktestChartInline→engine).
- 다중-라인 JSX 태그(`<X` 가 줄 끝)는 bare-ident 로 잡혀 수동 확인(SettingsModal/ApprovalDialog/CodeViewer→app, StrategyInspectorTabs→code-viewer 전부 실 JSX 소비 확인).
- 모호(multi-definer) 심볼: 0개.
