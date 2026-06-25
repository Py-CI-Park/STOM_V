# Process Research Pipeline 중간 점검 Q&A

작성일: 2026-06-25
브랜치: `loop/process-research-pipeline`
원격 브랜치: `origin/loop/process-research-pipeline`
커밋: `5dd626ded59a4f0bd055cfbad516292e57427d01` (`프로세스 연구 파이프라인 대시보드 확장`)
Ultragoal: `G001 complete`, final receipt `1cb38376-ed48-4d25-a281-016932d11cc7`
Dashboard 확인: `stom_dashboard.bat` 실행 후 `http://127.0.0.1:8770/health` = `200 {"status":"ok","contract_version":2}`

## 1. 이번 Ultragoal 작업 요약

| 구분 | 완료 내용 | 근거 |
|---|---|---|
| 브랜치/커밋 | `loop/process-research-pipeline` 브랜치에서 구현 후 push | commit `5dd626ded59a4f0bd055cfbad516292e57427d01` |
| 프로세스 카탈로그 | `1 fast-discovery`, `2 process-research`, `3 promotion-review` 번호/코드명 체계 추가 | `ai_strategy_loop/controller/condition_discovery.py`, `tests/unit/test_condition_discovery_policy.py` |
| 단일 authority | process/preset projection을 한 경로에서 검증하고 mismatch는 fail-closed | `resolve_condition_discovery_process_projection`, config tests |
| advisory 안전성 | fast/research는 `can_promote=false`, `can_export=false`, `can_live=false` | policy tests, final QA |
| promotion-review 안전성 | frozen snapshot, evidence health, hard gate, human approval 없이는 승격/내보내기/live 불가 | Ralplan mandatory constraints, policy blockers |
| warm timing | prepare/run elapsed, engine/back count, timeout/recovery metadata 추가 | `cli/warm_session.py`, `ai_strategy_loop/controller/loop.py`, warm tests |
| Dashboard Process | selector, full pipeline, capability pill, warm timing panel 추가 | `phase-detail.jsx`, `styles.css`, browser verification |
| 기존 호환성 | 기존 5-step graph와 `phase/current_step/step_timings` 유지 | dashboard/process timing tests |
| 검증 | targeted pytest `154 passed`, dashboard harness `allPass true`, nonrelease sync OK | verification artifacts and command output |

## 2. 안전 정책 상세

이번 작업의 핵심은 **연구 프로세스는 빠르게 만들되, 운영 승격 권한은 절대 열지 않는 것**이었다.

| 안전 정책 | 상세 의미 | 이번 구현/결정 | 왜 필요한가 |
|---|---|---|---|
| 단일 authority source | process selector가 preset과 별도 권한 체계가 되면 안 된다 | process는 `fast/research/promotion` preset projection으로 정규화하고 충돌 시 실패 | UI나 설정에 다른 값이 들어와도 실제 권한 해석이 갈라지지 않게 하기 위함 |
| mismatch fail-closed | `process=fast-discovery`인데 `preset=research` 같은 조합을 조용히 보정하지 않는다 | 명시 mismatch는 `ValueError` | 잘못된 모드로 백테스트/분석이 진행되는 침묵 실패 방지 |
| advisory lane 분리 | fast/research는 학습/탐색/분석용이지 운영 승격 근거가 아니다 | `can_promote/export/live=false` 고정 | 전체기간 반복 검증은 학습 신호로는 유용하지만 clean OOS/promotion proof가 아니기 때문 |
| research_validation 명명 | full-period 반복 분석을 promotion OOS로 부르지 않는다 | `research_validation` / `advisory_split` 성격 유지 | OOS leakage와 false confidence 방지 |
| promotion-review 제한 | promotion-review 선택 자체는 승인이나 export 권한이 아니다 | frozen snapshot, evidence health, hard gates, human approval blocker 유지 | 리뷰 모드를 눌렀다는 이유만으로 운영 반영되는 사고 방지 |
| prompt/autopsy feed 차단 | promotion-review 결과가 최종 결정 전 generation/autopsy로 역류하면 안 된다 | review 결과는 권한/상태로만 표시, 연구 루프 학습 feed와 분리 | frozen review가 다시 후보 생성에 영향을 주면 독립 검증이 깨짐 |
| UI는 설명 전용 | capability pill은 서버 권한을 보여줄 뿐 권한을 만들지 않는다 | `score_can_*` alias 제거, exact `can_promote/export/live`만 표시 | stale/malformed payload가 UI에서 권한처럼 보이는 문제 방지 |
| protected runtime path 유지 | `_database`, `_log`, `*.db`, `backtest/graph`, `v3k_settings*`를 건드리지 않는다 | status check에서 변경 없음 | 이 브랜치의 runtime/protected path 정책 준수 |

## 3. 32 vs 64 엔진을 직접 백테스트로 결정하지 않은 이유

사용자 아이디어는 타당하다. 64엔진이 이 워크스테이션에서 더 빠를 가능성은 있다. 다만 이번 Ultragoal에서는 **64를 기본값으로 결정하는 실제 비교 백테스트를 수행하지 않고, 먼저 비교 가능한 timing 계측 기반만 추가**했다.

| 질문 | 답변 |
|---|---|
| 왜 직접 여러 백테스트를 돌려 32/64를 비교하지 않았나? | 승인된 Ralplan은 `bt_warm_engine_count=32` 유지와 timing metadata 추가를 구현 범위로 두고, 실제 32-vs-64 benchmark는 별도 명시 승인 후 수행하도록 분리했다. 계획 본문에도 `Run controlled 32-vs-64 benchmark only after explicit approval to run backtests/benchmarks`라고 되어 있다. |
| 사용자가 “비교 후 결정”을 원했는데 왜 보류했나? | 맞다. 최종 목적은 비교 후 결정이다. 다만 기본값 변경은 resource/time/protected output side effect가 큰 결정이라, 동일 입력·동일 기간·반복 횟수·timeout·recovery·메모리 기준을 먼저 확정해야 한다고 판단했다. 이번 커밋은 그 비교를 위한 관측값을 남길 수 있게 만든 준비 단계다. |
| plan 승인으로 benchmark도 승인된 것 아닌가? | 보수적으로 해석했다. plan 승인/Ultragoal 승인으로 구현은 승인됐지만, plan 내부에서 benchmark는 추가 explicit approval 대상으로 분리되어 있었다. 따라서 장시간/다중 백테스트를 즉시 실행하지 않았다. |
| 64 기본값을 바로 바꾸면 어떤 위험이 있나? | prepare/load overhead, process spawn 비용, timeout/recovery 증가, 메모리 압박, DB/graph/runtime artifact 증가, 실제 amortized loop time 악화 가능성이 있다. 빠른 단일 run이 전체 연구 루프의 p50/p95 개선을 보장하지 않는다. |
| 이번에 무엇을 준비했나? | `prepare_elapsed`, `run_elapsed`, `engine_count`, `back_count`, `timeout_count`, recovery counters 등 warm timing metadata를 추가했다. 이제 controlled benchmark를 실행하면 32/64 비교 기록이 가능하다. |
| 기본값 전환 기준은? | Ralplan 기준: 64가 amortized research-loop time을 15% 이상 개선하거나 steady-state p50/p95를 20% 이상 개선하고, prepare overhead/timeout/recovery/resource regression이 없어야 한다. |

### 32/64 benchmark 후속 실행안

| 단계 | 실행 내용 | 기록해야 할 증거 |
|---|---|---|
| 1. 입력 고정 | 동일 run config, 동일 기간, 동일 전략/조건식, 동일 back_count 고정 | config snapshot |
| 2. 32 warm baseline | `bt_warm_engine_count=32`로 prepare/run 반복 | prepare/run elapsed, timeout/recovery, 성공률 |
| 3. 64 candidate | `bt_warm_engine_count=64`로 동일 반복 | 동일 지표 + memory/process stability |
| 4. p50/p95 비교 | 단일 평균이 아니라 p50/p95와 timeout 비율 비교 | benchmark summary JSON/MD |
| 5. default decision | 기준 충족 시에만 64 default PR | 결정 근거 + rollback 조건 |

## 4. 남은 항목 1 — 연구실 heatmap 미표시

| 항목 | 내용 |
|---|---|
| 상태 | 미해결 |
| 왜 이번에 하지 않았나 | 최종 Ralplan/Ultragoal G001 범위가 Dashboard **Process** 상세화와 process research pipeline 권한/metadata였고, Lab heatmap restoration은 포함되지 않았다. 초기 대화에는 heatmap 문제가 있었지만 승인된 plan으로 수렴되는 과정에서 별도 Lab defect로 분리된 상태가 되었다. |
| 관련 코드 후보 | `ai_strategy_loop/dashboard/frontend/analysis.jsx`, `research-lab.jsx`, `rl-panel.jsx`, `rp-heatmap.jsx`, `rp-panel.jsx`, `styles.css` |
| 현재 구조 근거 | `EdgeRatioPanel`은 `/edge_ratio?run_ids=...&fine_time=true`를 fetch하고, run이 없거나 cross segment가 없으면 empty state를 보여준다. `_RpBigHeatmap`도 같은 `/edge_ratio` cross segment를 재사용한다. |
| 먼저 확인할 것 | ① 선택된 `runId`가 있는지 ② `/edge_ratio` 응답에 `segments.cross`가 있는지 ③ Lab route가 해당 component를 mount하는지 ④ CSS 때문에 가려지는지 ⑤ bundle cache가 최신인지 |
| 왜 바로 CSS만 고치면 안 되나 | “안 보임”은 데이터 부재, fetch 실패, route/mount 실패, empty state, CSS clipping, bundle stale 중 하나일 수 있다. 원인 분리 없이 수정하면 다른 화면을 깨뜨릴 수 있다. |
| 권장 후속 | `loop/lab-heatmap-followup` 같은 별도 브랜치에서 browser evidence + API payload snapshot + component/static tests로 해결 |

## 5. 남은 항목 2 — edge ratio heatmap 크기 문제

| 항목 | 내용 |
|---|---|
| 상태 | 미해결 |
| 왜 이번에 하지 않았나 | Process pipeline 작업과 다른 surface다. 이번 커밋은 `phase-detail.jsx` 중심의 Process route 변경이고, edge ratio heatmap은 Lab/ResearchPro/analysis chart layout 문제다. |
| 관련 코드 후보 | `analysis.jsx::_Heatmap`, `rp-heatmap.jsx::_RpHeatmapGrid`, `styles.css` `.edge-heatmap-scroll`, `.rp-heatmap*` |
| 현재 크기 근거 | `analysis.jsx::_Heatmap`은 SVG cell width/height를 계산하고 `.edge-heatmap-scroll`은 `max-height: 360px; overflow: auto`를 적용한다. `rp-heatmap.jsx::_RpHeatmapGrid`는 CSS grid로 `120px repeat(n, minmax(64px, 1fr))`를 쓴다. |
| 가능한 원인 | SVG 고정 width/height가 큰 화면에서 과도하게 커짐, scroll container max-height와 panel layout 충돌, grid minmax가 column 수에 따라 과도한 폭을 만듦, Lab/Pro 두 heatmap 구현이 서로 달라 일관성이 없음 |
| 권장 수정 방향 | Lab/Pro heatmap sizing contract를 하나로 정하고, `max-height`, responsive width, min cell size, dense/large mode를 명시적으로 나눈다. ECharts heatmap pilot도 후보가 될 수 있다. |

## 6. 현재 프론트엔드 기술 스택 점검

| 항목 | 현재 상태 | 근거/메모 |
|---|---|---|
| 프레임워크 | React | `vendor-react.js`, `vendor-react-dom.js`를 로컬 vendored script로 로드 |
| 빌드 | esbuild bundle + Vite workspace | `webui-build/build-app.mjs`, `vite.config.mjs` |
| 런타임 | runtime npm-free, generated bundle committed | HTML 주석과 build script가 `bundle/app.js`, `bundle/stom-ui.js` 산출물 커밋 계약 명시 |
| JSX 소스 | 여러 `.jsx` 모듈을 build 시점에 단일 classic script로 번들 | `track-z-entry.pilot.js`가 app graph import/re-publish |
| 그래프/플로우 | `@xyflow/react` + `dagre` | `phase-detail.jsx` ProcessFlowDiagram |
| 캔들/시뮬레이션 chart | TradingView `lightweight-charts` vendored global, SVG fallback | `index.html` vendor script 주석 |
| 일반 chart | 대부분 순수 SVG custom components | `chart.jsx`, `backtest-charts.jsx`, `analysis.jsx` 등 주석상 외부 chart library 금지/순수 SVG 중심 |
| 디자인 | 단일 `styles.css` + CSS variables + dark workstation theme | dashboard styles |
| ECharts | 현재 미사용 | `package.json` dependencies에 없음 |
| D3 | 현재 미사용 | `package.json` dependencies에 없음 |
| TypeScript | build workspace에 `typescript` devDependency는 있으나 앱 소스는 주로 `.jsx` | `package.json`, frontend files |

## 7. 프론트엔드를 더 화려하게 하려면 기술 스택을 바꿔야 하나?

결론: **전면 스택 교체는 지금 필요하지 않다.** 현재 구조는 local desktop/workstation dashboard에 맞게 runtime npm-free, local vendored React, committed bundle, harness 검증으로 안정성을 확보하고 있다. 더 화려한 UI는 먼저 현재 React/CSS/esbuild 구조 안에서 충분히 개선 가능하다.

| 선택지 | 장점 | 단점/위험 | 판단 |
|---|---|---|---|
| 현 스택 유지 + CSS/컴포넌트 강화 | 가장 안전, 기존 harness/번들 계약 유지, offline/local runtime 유지 | 고급 chart interaction은 직접 구현 비용 증가 | 1차 권장 |
| ECharts 부분 도입 | heatmap, tooltip, zoom, large data, Canvas/SVG renderer, progressive rendering 등 dashboard chart 강화에 유리 | bundle 크기 증가, theme/tooltip/resize wrapper 작성 필요 | 2차 권장: heatmap/chart pilot에 적합 |
| D3 부분 도입 | custom scale/layout/brush/zoom/shape에 강함, bespoke visualization 자유도 높음 | React와 DOM ownership 충돌 가능, 구현 난이도 높음 | 계산/scale/layout 유틸 중심으로 제한 도입 권장 |
| Admin template 전면 도입 | 카드/레이아웃/애니메이션을 빠르게 화려하게 만들 수 있음 | 현재 CSS/route/build/runtime 계약과 충돌, 불필요한 router/state/theme 의존성 유입 | 전면 교체 비권장, 패턴만 참고 |
| Next/Vue 등 프레임워크 전환 | 장기 웹앱 제품화에는 장점 가능 | 현재 PyQt/로컬 FastAPI-style dashboard와 산출물 커밋 계약에 큰 충격 | 지금은 비권장 |

외부 검토 근거:
- Apache ECharts는 20개 이상 chart type, Canvas/SVG renderer, progressive/stream rendering, dataset transform을 제공한다고 설명한다: https://echarts.apache.org/en/index.html
- D3는 bespoke data visualization, scales/axes/shapes/interactions/layouts를 제공한다: https://d3js.org/
- React Flow는 node/edge 기반 UI, custom nodes/edges, layouting, interaction 예제를 제공한다: https://reactflow.dev/

## 8. ECharts / D3 / dashboard template 강화 방향

| 대상 | 권장 도입 방식 | 적용 후보 | 이유 |
|---|---|---|---|
| ECharts heatmap | 한 컴포넌트 pilot로 시작, 기존 SVG fallback 유지 | Lab edge ratio heatmap, correlation heatmap, calendar/monthly heatmap | tooltip/zoom/visualMap/responsive가 기본 제공되어 heatmap 품질 개선에 직접적 |
| ECharts line/bar | 기존 SVG 차트 중 hover/zoom이 복잡한 것부터 선택적 대체 | equity curve, rolling metrics, distribution | 빠른 시각 품질 개선 가능 |
| D3 scale/layout | DOM 렌더링은 React가 유지하고 D3는 scale/color/binning/shape 계산만 사용 | custom color scale, brush range, hierarchical process analysis | React DOM 충돌 없이 D3 장점만 사용 |
| D3 full chart | 매우 bespoke한 연구 시각화에 한정 | force/chord/parallel sets 등 | 구현 복잡도가 높아 범용 chart에는 과함 |
| Dashboard template | 코드 복붙이 아니라 layout/design token 참고 | KPI card, glass panel, sidebar, command palette, dense table | 현 CSS와 충돌을 줄이기 위해 internal component로 흡수 |
| React Flow 강화 | 이미 도입된 stack을 더 활용 | custom process nodes, minimap, edge labels, group nodes | Process 화면은 stack 교체 없이 더 화려하게 만들 수 있음 |

## 9. 중간 점검 Q&A

| 질문 | 답변 |
|---|---|
| 이번 Ultragoal은 정확히 무엇을 끝냈나? | process research pipeline의 backend authority, warm timing metadata, Dashboard Process detailed view, 테스트/검증/커밋/푸시를 완료했다. |
| 64엔진 기본값도 바뀌었나? | 아니다. 기본값은 `32` 유지다. 64는 benchmark-only 후보로 남겼다. |
| 왜 64 benchmark를 안 돌렸나? | plan에서 benchmark는 별도 explicit approval 대상으로 분리했고, 장시간/다중 backtest는 동일 입력과 resource 기준이 필요하기 때문이다. 이번 작업은 benchmark를 가능하게 하는 timing metadata를 추가한 단계다. |
| 연구실 heatmap이 안 보이는 문제는 해결됐나? | 아니다. 이번 범위 밖이다. Lab route/API/CSS/bundle 문제로 별도 조사해야 한다. |
| edge ratio heatmap size는 해결됐나? | 아니다. 관련 코드는 `analysis.jsx`, `rp-heatmap.jsx`, `styles.css` 쪽이며 별도 visual/layout follow-up이 필요하다. |
| 프론트엔드 스택을 바꿔야 더 화려해지나? | 전면 교체는 필요 없다. 현재 React/esbuild/CSS 구조에서 충분히 개선 가능하다. chart-heavy 영역은 ECharts pilot 도입이 가장 현실적이다. |
| D3가 필요한가? | 전체 chart를 D3로 갈아엎기보다는 scale/layout/interaction 유틸로 제한 도입하는 것이 안전하다. |
| dashboard template을 써도 되나? | 디자인 패턴은 참고 가능하지만, admin template 전면 도입은 현재 local/offline bundle 계약과 충돌 가능성이 커서 비권장이다. |
| 다음으로 무엇을 해야 하나? | ① Lab heatmap 표시 원인 분리 ② edge ratio heatmap sizing 정리 ③ 32/64 controlled benchmark ④ ECharts heatmap pilot 순서가 안전하다. |

## 10. 권장 후속 작업 분해

| 우선순위 | 후속 작업 | 완료 기준 |
|---:|---|---|
| 1 | Lab heatmap visibility fix | Lab route browser screenshot에서 heatmap 표시, `/edge_ratio` payload/empty/error 상태 구분, focused tests 통과 |
| 2 | Edge ratio heatmap sizing cleanup | 작은/큰 화면 screenshot 비교, scroll/height/width contract 고정, Lab/Pro heatmap sizing 일관화 |
| 3 | 32 vs 64 controlled benchmark | 동일 입력 기준 32/64 반복 결과 JSON/MD 기록, p50/p95/timeout/recovery/resource 비교, default decision 작성 |
| 4 | ECharts heatmap pilot | 기존 SVG fallback 유지하면서 one-panel ECharts heatmap 도입, bundle/harness/browser 검증 |
| 5 | Visual system refinement | card hierarchy, color scale, animation, dense table, skeleton/empty state를 internal components로 정리 |
