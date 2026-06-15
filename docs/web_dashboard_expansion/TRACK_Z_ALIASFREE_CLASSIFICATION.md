# TRACK_Z_ALIASFREE_CLASSIFICATION — hook-alias 없는 10개 .jsx 분류 (Story 2)

> Track Z Story 2 감사 산출물(SHOULD-FIX 11). **코드 변경 없음 — 문서 전용.**
> 26개 .jsx 중 `const {…} = React` 훅 별칭이 *없는* 10개를 식별하고, 각각 `export` 필요 여부를 분류한다.
> 근거는 TRACK_Z_DEPS.md §1 의 definer 컬럼(직접 grep 검증)과 교차한다.
> 생성일: 2026-06-15.

---

## 0. 요약 (결론 먼저)

- **hook-alias 없는 파일 = 정확히 10개** (26 − 16). 16개는 `const {…}=React` 별칭을 가진다(18 라인/16 파일, chart.jsx 가 3개).
- **10개 전부가 1개 이상 cross-file 심볼을 정의 → 10개 전부 `export` 필요.**
- **"zero-cross-file-surface no-op" 파일은 0개.** 계획서가 가설한 self-contained no-op(예: hypothesis/analysis 가 no-op일 수 있다)은 실제로는 존재하지 않는다 — 이것이 계획서에 대한 주요 정정이다.

---

## 1. hook-alias 보유/미보유 식별

### 1.1 hook-alias 보유 16개 파일 (18 라인) — `import { useState } from "react"`(alias→shim) 전환 대상

ai-context(2), app(2), cards(2), **chart(2, 474, 1651 — 3라인)**, code-viewer(2), connection(2, 유일한 무접미사 destructure), dashboard-pages(16), engine(2), glossary(2), panels(2), phase-detail(2), research-wiki(2), run-compare(2), settings(2), strategy-inspector(2), table(2).

### 1.2 hook-alias 미보유 10개 파일 (이 문서의 대상)

`hypothesis`, `analysis`, `research-pro`, `research-lab`, `backtest-charts`, `backtest`, `sim-live-chart`, `simulation-charts`, `simulation`, `evolution-analysis`.

> 식별 방법: 26 파일에서 `const\s*\{[^}]*\}\s*=\s*React` grep → 16 파일만 매치 → 나머지 10개. (이 10개는 React 훅을 쓰지만 *접미사 별칭 없이* 다른 메커니즘으로 호출하거나, 컴포넌트 내부에서 `React.useState` 직접/접미사 별칭을 본 파일 상단에 두지 않는다 — 어느 쪽이든 충돌-회피 별칭이 없다는 사실이 핵심.)

---

## 2. 10개 파일 분류 (전부 `needs export`)

| 파일 | O | 정의하는 cross-file 심볼 (TRACK_Z_DEPS §1) | 분류 |
|------|---|---------------------------------------------|------|
| hypothesis.jsx | O5 | HypothesisPanel | **needs export** |
| analysis.jsx | O12 | EdgeRatioPanel, FeatureImportancePanel | **needs export** |
| research-pro.jsx | O13 | ResearchProPanel, ResearchHeatmapPanel | **needs export** |
| research-lab.jsx | O14 | VdtPromoteChecklist, VdtAlerts, VdtSummaryLines, ResearchLabPanel | **needs export** |
| backtest-charts.jsx | O18 | BtResultArea (+ chart.jsx 의 LegendDot/Mini/MetricHelpStrip 를 소비) | **needs export** |
| backtest.jsx | O19 | BtVarChips, BacktestTab | **needs export** |
| sim-live-chart.jsx | O20 | SimLiveChart | **needs export** |
| simulation-charts.jsx | O21 | SimCandleChartLWC, SimCandleChartSVG, SimCandleChart, SimOverlayChart, SimSignalLog | **needs export** |
| simulation.jsx | O22 | SimulationTab | **needs export** |
| evolution-analysis.jsx | O23 | EvolutionAnalysisPanel | **needs export** |

**zero-cross-file-surface no-op: 0개.**

---

## 3. 추가 참고 — 이 10개 파일이 소비하는 쪽 (import 필요 측면)

`export` 외에 Story 3 에서 이 파일들이 추가해야 할 `import` (definer 가 in-bundle 인 경우만; stom-ui 호스팅은 §HARD 규칙으로 window. 유지):

- **backtest-charts.jsx**: chart.jsx 의 `LegendDot`, `Mini`, `MetricHelpStrip` 를 bare 소비, chart.jsx 의 `BacktestDetailChart` 를 bare 소비 → import 추가. `_axisTicks`(stom-ui, line 49) → window. 유지.
- **research-pro.jsx**: backtest-charts 의 `BtResultArea`(역방향 O18→O13, bare+window.X) + backtest 의 `BtVarChips`(역방향, typeof window 가드, line 79-80) 소비. `STOM_PIPELINE`(stom-ui, line 802) → window. 유지.
- **research-lab.jsx**: analysis 의 `EdgeRatioPanel`/`FeatureImportancePanel` bare 소비, dashboard-pages 의 `VerdictPanel` bare 소비 → import. `STOM_PIPELINE`(stom-ui, line 1046) → window. 유지.
- **simulation.jsx**: simulation-charts 의 `SimCandleChart*`/`SimOverlayChart`/`SimSignalLog` + sim-live-chart 의 `SimLiveChart` 소비(혼합 bare/window.X) → import. `window._SIM_*`/`window._sim*`(런타임 동적 전역) 은 stom-ui 아님이나 별도 전역 — import 대상 아님(런타임 계산값).
- **sim-live-chart.jsx**: simulation-charts 의 `SimCandleChart`/`SimCandleChartLWC` bare 소비 → import. `_hmsTimeLabel`/`_priceTick`(stom-ui, line 46-47) → window. 유지.
- **backtest.jsx**: backtest-charts 의 `BtResultArea` bare 소비 → import.
- **analysis.jsx**: `<window.DemoBadge/>`(phase-detail) 소비 → import 가능(in-bundle) 또는 window. 유지 선택. (DemoBadge 는 stom-ui 아님 → import 권장.)
- **hypothesis.jsx**: panels 의 `AutopsyPanel`, chart 의 `QualityTrendChart` bare 소비 → import.
- **evolution-analysis.jsx**: chart 의 `LegendDot`/`Mini` bare 소비 → import.
- **simulation-charts.jsx**: sim-live-chart 의 `SimLiveChart` bare 소비 → import. `_hmsTimeLabel`/`_priceTick`(stom-ui, line 157-158) + `window.LightweightCharts`(벤더 전역, line 437) → window. 유지.

> 상세 definer→consumer 매트릭스는 TRACK_Z_DEPS.md §1·§2 참조. stom-ui HARD 규칙(절대 import 금지 12 심볼)은 TRACK_Z_DEPS.md §3 참조.
