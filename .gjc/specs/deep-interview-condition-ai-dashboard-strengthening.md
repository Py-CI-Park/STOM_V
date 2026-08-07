# Deep Interview Spec: wt-dev 조건식 AI 대시보드 전면 강화

## Metadata
- Interview ID: `019edda6-58ba-7000-ab80-318bc34f3b8a`
- Rounds: 11 including Round 0 topology and closure restate gate
- Final Ambiguity Score: 4%
- Type: brownfield
- Generated: 2026-06-21
- Threshold: 0.05
- Threshold Source: default
- Initial Context Summarized: no
- Status: PASSED
- Auto-Researched Rounds: []
- Auto-Answered Rounds: []
- Architect Failures: 0
- Lateral Reviews: 2 milestone panels: progress, refined
- Lateral Panel Failures: 0
- Refined Rounds: []
- Closure Overrides: none
- Restated Goal: wt-dev 대시보드를 조건식 AI 연구 플랫폼으로 재구성하여, 조건식을 장기 identity로 두고 백테스트 결과를 evidence 단위로 복구·재실행·상세 분석·히스토리·명예의 전당·리서치랩·워크벤치·차트 리플레이·변수/백파인더 단계형 도구까지 중복 없이 연결한다.

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.98 | 0.35 | 0.34 |
| Constraint Clarity | 0.96 | 0.25 | 0.24 |
| Success Criteria | 0.95 | 0.25 | 0.24 |
| Context Clarity | 0.94 | 0.15 | 0.14 |
| **Total Clarity** | | | **0.96** |
| **Ambiguity** | | | **0.04** |

## Topology
| Component | Status | Description | Coverage / Deferral Note |
|-----------|--------|-------------|--------------------------|
| Backtest Result Access | active | 백테스트 결과 라이브러리가 취소됨만 보이고 결과를 열 수 없는 문제를 복구한다. | 분류 정리, 기존 결과 복구 시도, 같은 조건 재실행/열기를 모두 포함한다. |
| Backtest GUI Parity | active | Python GUI 백테스트 핵심 결과 확인 흐름을 웹 대시보드에 반영한다. | 핵심 결과 테이블, 종목 클릭 차트, 조건식 확인은 동등하게 제공하고 나머지는 현대화한다. |
| Editor UX | active | 매수/매도 조건식 에디터의 높이와 단독 확대 보기를 개선한다. | 에디터 기본 높이를 키우고 매수/매도 각각만 크게 볼 수 있는 확대 모드를 제공한다. |
| Optimization / Variable Tools | active | 변수 설정, 자동 변수 변화, 변수 영향도 분석을 단계형으로 웹화한다. | 1차는 웹식 변수/영향도/결과 비교, 2차는 self.vars 변환과 전용 UI를 추가한다. |
| BackFinder | active | 기존 STOM 백파인더 기능을 조사하고 웹 기능으로 단계형 반영한다. | 1차에는 계획과 연결점을 만들고, 2차에 BackFinder 전용 UI와 실행/결과 흐름을 추가한다. |
| Chart Replay | active | 차트 리플레이 디자인, 속도 지연, 렉, 빠른 시작 도움말을 개선한다. | 데이터는 보존하되 화면 렌더는 adaptive로 줄이고 재생/정지/속도변경 반응은 즉시 유지한다. |
| Condition AI Home / Live Monitor | active | 진화 홈/개요를 조건식 AI 중심으로 재구성하고 실행 상태를 상단에서 이해하게 한다. | 상단 한 줄 전체 프로세스, 바로 아래 Live phase log와 현재 전략/세대, 그 아래 설정·게이트·엔진 접힘 섹션을 둔다. |
| Governance / Gate Visualization | active | 기본 설정, Research Criteria, scoring, MDD gate, backtest engine 정보를 시각화한다. | 상단 접힘 섹션, 아이콘 또는 테이블로 통합해 설정값과 판정 기준을 한눈에 보이게 한다. |
| Research IA Dedup | active | 리서치랩, 워크벤치, 히스토리, 명예의 전당, Compare 중복을 제거한다. | 리서치랩=탐색/변수/엣지, 워크벤치=심층 분석, 히스토리=결과 상세/Compare, 명예의 전당=승격 후보/좋은 결과 관리로 소유권을 잠근다. |
| History Archive | active | 기록 검색을 히스토리로 바꾸고 모든 세대/백테스트/조건식/종목/차트/결과를 다시 선택해 볼 수 있게 한다. | 조건식은 장기 identity, 백테스트 결과는 evidence 단위다. 기본 진입은 히스토리이며 실행 후 자동 상세는 BacktestTab으로 열린다. |

## Established Facts
- Round 0: 사용자는 10개 top-level component 전체를 이번 범위로 확정했다.
- Round 1: 결과 라이브러리 복구는 분류 정리, 기존 결과 복구 시도, 재실행/열기를 모두 포함한다.
- Round 2: GUI parity는 결과 테이블, 종목 클릭 차트, 조건식 확인은 동등하게 하고 나머지는 현대화한다.
- Round 3: canonical model은 조건식 장기 identity + 백테스트 결과 evidence unit이며, 기본 진입은 결과/히스토리다.
- Round 4: 최적화/변수/백파인더는 단계형으로 진행한다. 먼저 웹식 변수/영향도/결과 비교, 그 다음 self.vars와 BackFinder 전용 UI다.
- Round 5: 히스토리 상세는 상단 요약+조건식, 중단 거래 종목 테이블/종목 클릭 차트, 하단 전체 분석 시각화·변수·비교·검증으로 구성한다.
- Round 6: 내부 구현은 공유 ResultDetail이며 기본 진입은 히스토리, 실행 후 자동 상세는 BacktestTab이다.
- Round 7: 차트 리플레이는 데이터 보존 + adaptive 렌더 + 즉시 조작 반응을 성공 기준으로 한다.
- Round 8: 조건식 AI 홈 상단은 전체 프로세스 → Live phase log/현재 전략·세대 → 설정·게이트·엔진 접힘 섹션 순서다.
- Round 9: IA 소유권은 리서치랩=탐색/변수/엣지, 워크벤치=심층 분석, 히스토리=결과 상세/Compare, 명예의 전당=승격 후보/좋은 결과 관리다.
- Round 10: 실행 순서는 Phase 1 result identity+라이브러리 복구, Phase 2 공유 ResultDetail+히스토리, Phase 3 IA/home/lab 정리, Phase 4 editor/replay/variable/backfinder다.

## Trigger Metadata
No contradiction, internal inconsistency, low-quality/evasive answer, or unresolved scope expansion remains. Scope was expanded through the initial topology and explicitly confirmed by the user.

## Lateral Review Panel
- Progress milestone panel: researcher, contrarian, and simplifier lenses warned that 10 capabilities must not become 10 new screens. They recommended one canonical condition/result identity and reuse of existing BacktestTab/BtResultArea surfaces.
- Refined milestone panel: researcher, contrarian, and simplifier lenses identified the remaining risk as result-detail ownership. The accepted synthesis is shared ResultDetail, History as default entry, and BacktestTab as post-run auto-detail.

## Goal
Rebuild the wt-dev dashboard into a coherent Condition AI research platform where a condition expression is the long-term identity, each backtest result is evidence, and users can recover, rerun, inspect, compare, replay, and promote results without duplicated research surfaces.

## Constraints
- Work happens in `C:/System_Trading/STOM/STOM_V.wt-dev`.
- Do not recreate duplicate top-level pages for every capability.
- Keep one shared result-detail contract instead of separate result-detail implementations in Backtest, History, Workbench, and Hall of Fame.
- Preserve existing dashboard architecture where useful, especially `BacktestTab`, `BtResultArea`, Research Lab, Research Pro/Workbench, and existing backend result-analysis APIs.
- BackFinder and legacy `self.vars` support are staged, not the first blocking path.
- Existing Python GUI behavior is a parity reference for core workflows, not a mandate to clone every old layout.
- No live brokerage, V3K, serial-key, DB cutover, or runtime-protected path mutation is in scope.

## Non-Goals
- Full exact pixel clone of the old Python GUI.
- Replacing the backtest engine with a new engine.
- Transformer/ML research work; this remains a future research track.
- Production trading or broker live-order enablement.
- Making advisory scores or research screens grant promotion/export authority by themselves.

## Acceptance Criteria
- [ ] Backtest result library distinguishes cancelled/failed/success/no-trades states clearly and no longer traps users in disabled `취소됨` rows only.
- [ ] If existing result artifacts are present, the dashboard attempts to recover/open them; if not recoverable, it offers same-condition rerun/open flow.
- [ ] Shared ResultDetail can render from a backtest job, evolution run/generation, and history item using one contract.
- [ ] ResultDetail shows top summary+buy/sell condition, middle trade-symbol table with symbol-click chart, and bottom full analysis visualizations including variable/compare/validation where data exists.
- [ ] History is renamed from 기록 검색 and becomes the default archive entry for condition/result evidence.
- [ ] BacktestTab still auto-opens result detail after a run completes.
- [ ] GUI parity core is present: result table, symbol-click chart, condition view.
- [ ] Editor default height is increased and buy/sell each support large single-side view.
- [ ] Condition AI home naming replaces 진화 홈/개요 where applicable.
- [ ] Condition AI home top area shows whole-process progress, Live phase log/current generation/current strategy, and collapsible settings/gates/engine summary.
- [ ] Research Lab owns exploration/edge/variable/correlation/combos/validation; Workbench owns deep analysis; History owns result detail and Compare; Hall of Fame owns promotion candidates/good results.
- [ ] Compare is either inside History or clearly explained as a History/result comparison mode.
- [ ] Chart replay supports data-preserving adaptive rendering and responsive play/pause/speed changes.
- [ ] Quick start controls such as 최대 상승일 and 최근 거래일 have understandable hover/help text.
- [ ] Phase 1 through Phase 4 execution order is preserved to avoid building UI over a missing result identity.

## Deferrals
- Deep legacy `self.vars` conversion UI and BackFinder dedicated UI are Phase 4, after result identity/history/detail foundations exist.
- Transformer/ML modeling is out of this implementation and remains future research.
- Convergence pacing deferral: no artificial min-round floor or score-drop cap was used; bidirectional scoring is the pacing mechanism.

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| Result library bug is just a display bug | It may be classification, missing artifacts, or disabled old records. | Include state classification cleanup, existing result recovery attempt, and rerun/open flow. |
| GUI parity means clone all old screens | Full cloning would overbuild and duplicate. | Keep core parity only: result table, symbol chart on symbol click, condition view. |
| History can be a search list | User needs systematic research replay. | History becomes the default archive and result-detail entry. |
| Condition or run should be the only canonical identity | Research needs both condition continuity and backtest evidence. | Condition is long-term identity; backtest result is evidence unit. |
| BackFinder must be first-class immediately | It has special legacy strategy requirements. | Stage it after web-style variable/result analysis foundations. |
| More screens solve duplicate features | More screens risk recreating the exact problem. | Use shared ResultDetail and explicit IA ownership. |

## Technical Context
- `ai_strategy_loop/dashboard/frontend/bt-tab-root.jsx` owns BacktestTab edit/result subtabs, run panel, result library, `BtResultArea`, mode result panels, multi-job overlay, and portfolio analysis.
- `ai_strategy_loop/dashboard/frontend/bt-tab-run.jsx` supports backtest/optimize/WFO/sweep. Optimize/WFO rely on param-space JSON, while sweep has a variable row builder.
- `ai_strategy_loop/dashboard/frontend/bt-result-area.jsx` renders rich aggregate charts and insights, but symbol-click table/chart parity must be strengthened.
- `ai_strategy_loop/dashboard/frontend/research-pro.jsx` documents history/Hall of Fame/compare reuse of `BtResultArea`, making it a candidate for shared ResultDetail integration.
- `ai_strategy_loop/dashboard/frontend/rl-panel.jsx` groups edge, feature importance, correlation, variable combos, and validation; this remains the Research Lab ownership boundary.
- `ui/ui_vars_change.py` contains legacy `self.vars` conversion/sorting logic.
- `backtest/backfinder.py` requires special buy strategies containing `self.tickcols` and `self.tickdata`, then saves BackFinder tables to backtest DB.

## Ontology (Key Entities)
| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| Condition Expression | core domain | buy code, sell code, variable refs, identity, pattern metadata | Has many Backtest Results; may enter Hall of Fame. |
| Backtest Result | evidence | job id, run id, generation, status, metrics, csv/report paths, conditions | Evidence for a Condition Expression; opened by ResultDetail. |
| ResultDetail | UI contract | summary, condition, trade table, symbol chart, full analysis, compare, validation | Shared by History, BacktestTab, Workbench, and Hall of Fame links. |
| History Archive | UI surface | searchable results, generations, conditions, evidence links | Default entry to ResultDetail and Compare. |
| Research Lab | UI surface | edge heatmap, feature importance, correlation, combos, validation | Exploratory lens over run/result data. |
| Workbench | UI surface | deep analysis tools, large heatmaps, drilldowns | Uses result/history context for deeper analysis. |
| Hall of Fame | UI surface | good results, promotion candidates, condition details | Manages strong results but does not replace History. |
| BackFinder | legacy tool | strategy name, tickcols, tickdata, found rows, DB table | Phase 4 dedicated UI after foundational result flow. |
| Variable Tool | analysis/optimization | named params, self.vars mapping, sweep specs, influence reports | Feeds optimization and research insight. |
| Chart Replay | visualization | bars, speed, adaptive render state, quick start presets | Visualizes result/market behavior responsively. |

## Ontology Convergence
Entities stabilized after Round 5. The final entity set is stable across result identity, history, lab, workbench, Hall of Fame, variable tools, BackFinder, and replay surfaces.

## Execution Phases
| Phase | Objective | Key Deliverables |
|-------|-----------|------------------|
| Phase 1 | Result identity and library recovery | status classification cleanup, recover/open old artifacts when possible, rerun/open action, condition/result identity fields. |
| Phase 2 | Shared ResultDetail and History | ResultDetail contract, History rename/remodel, result table, symbol-click chart, condition view, Compare inside History. |
| Phase 3 | IA and Condition AI home/lab cleanup | Condition AI naming, upper process/live monitor/settings gate sections, Research Lab/Workbench/HOF ownership cleanup. |
| Phase 4 | Editor, replay, variable tools, BackFinder | taller editors and single-side expand, adaptive chart replay, variable influence/web-style optimization, self.vars and BackFinder dedicated follow-up UI. |

## Interview Transcript Summary
Round 0 confirmed 10 top-level components. Rounds 1-10 resolved result recovery, GUI parity depth, canonical identity, variable/BackFinder phasing, history detail composition, result-detail owner, replay performance budget, home top layout, IA ownership, and execution phasing. Closure restate was confirmed with “Yes, crystallize”.
