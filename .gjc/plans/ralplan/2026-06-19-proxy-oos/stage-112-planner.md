# RALPLAN-DR: 조건식 AI 대시보드 강화 계획

상태: pending approval. 정본은 `.gjc/specs/deep-interview-condition-ai-dashboard-strengthening.md`이다. 실행 승인은 없으므로 제품 코드는 변경하지 않는다.

## Summary

wt-dev 대시보드를 조건식 AI 연구 플랫폼으로 정리한다. 장기 identity는 조건식 expression이고, 백테스트 result는 evidence unit이다. 조사 근거: `bt-tab-root.jsx`가 BacktestTab과 `BtResultArea`, `BtRunPanel`, `BtResultLibrary`, 에디터, 진화세대 선택, 오버레이와 포트폴리오를 조합한다. `bt-tab-run.jsx` 결과 라이브러리는 현재 success와 no_trades 중심 클릭 흐름이다. `backtest_jobs.py`는 `state/webbt_jobs` JSON을 복원하고 running 또는 pending 손실을 stale 성격의 error로 바꾼다. `/bt/result`는 job 또는 run/gen을 유사 스키마로 반환하지만 shared ResultDetail 정본은 없다. `ui-contract.jsx` 라벨은 현재 `진화 홈`, `개요`, `기록 검색`, `연구실·위키`, `분석 워크벤치`이다. `ResearchRecordsPanel`은 campaign index라 History archive로 쓰려면 condition/result evidence 모델이 필요하다. `SimulationTab`은 WS replay, speed, pause, seek, quick preset을 이미 갖고 있으므로 Phase 4에서 adaptive rendering과 도움말을 고정한다. legacy 참조는 `ui/ui_vars_change.py`의 self.vars 변환과 `backtest/backfinder.py`의 BackFinder 실행 조건이다.

## RALPLAN-DR summary

### 원칙
1. Identity first: 조건식 identity와 result evidence identity를 먼저 확정한다.
2. One detail contract: Backtest, History, Workbench, HOF가 하나의 ResultDetail을 공유한다.
3. Recover before repaint: 라이브러리 status 분류, artifact 복구, 재실행 경로를 먼저 고친다.
4. IA ownership: 새 top level 화면을 늘리지 말고 Lab, Workbench, History, HOF 소유권을 잠근다.

### Top 3 decision drivers
1. 핵심 실패는 결과를 열 수 없는 라이브러리이므로 Phase 1 recovery가 선행되어야 한다.
2. 상세 화면 중복은 유지보수 리스크라 shared ResultDetail이 필요하다.
3. self.vars와 BackFinder는 legacy 제약이 강해 Phase 4에서 단계형으로 다룬다.

### Options
- Option A, BacktestTab 중심 점진 통합: Phase 1 identity와 recovery, Phase 2 shared ResultDetail과 History, Phase 3 IA cleanup, Phase 4 editor replay variable BackFinder. 장점은 기존 `BtResultArea`, `/bt/result`, `BtResultLibrary` 재사용과 phase order 준수이다. 단점은 초기 identity adapter가 여러 파일에 걸친다.
- Option B, History 선행 구축: History를 먼저 만들고 링크를 우회한다. 장점은 최종 IA가 빨리 보인다. 단점은 recovery 전에는 `취소됨`이나 unavailable evidence를 보기 좋게 나열할 뿐이라 Phase 1 계약과 충돌한다.
- Option C, 신규 domain store 재설계: condition/result/history/HOF/backfinder를 신규 service와 DB로 묶는다. 장점은 장기 모델이 깔끔하다. 단점은 brownfield 범위 초과이며 protected path, live broker, V3K, DB cutover 리스크가 크다.

선택: Option A. Phase 1부터 Phase 4 순서, existing architecture reuse, shared ResultDetail, BacktestTab post run auto detail을 동시에 만족한다. Option B는 recovery 결핍으로, Option C는 범위 초과로 기각한다.

## In scope / out of scope

In scope: Phase 1 result identity와 library recovery. Phase 2 shared ResultDetail과 History, result table, symbol click chart, condition view, Compare inside History, BacktestTab auto detail 유지. Phase 3 Condition AI naming, whole process progress, Live phase log/current generation/current strategy, collapsible settings/gates/engine summary, IA ownership cleanup. Phase 4 taller editors, buy/sell single side expand, adaptive chart replay, variable influence, staged self.vars와 BackFinder support.

Out of scope: 승인 전 제품 코드 변경, 테스트/build/formatter 실행, live brokerage, V3K gate enablement, serial key, DB cutover, production export authority 변경, old GUI pixel clone, backtest engine replacement, transformer/ML modeling.

## File-level changes

### Phase 1
- `ai_strategy_loop/dashboard/backtest_jobs.py`: public status taxonomy를 명확히 한다. restored running/pending은 generic error가 아닌 stale/artifact state로 설명한다. persisted JSON은 additive compatibility만 사용한다.
- `ai_strategy_loop/dashboard/backtest_api.py`: `/bt/jobs`, `/bt/job`, `/bt/result`에 condition_identity, evidence_id, source_type, status_kind, artifact_state, open_actions, rerun_spec 성격의 파생 필드를 추가한다. csv/report/mode_result 존재 여부를 무예외로 판정한다.
- `ai_strategy_loop/dashboard/frontend/bt-tab-run.jsx`: result library row를 status aware actions로 바꾼다. success, no_trades, openable, recoverable, rerunable, cancelled, failed, stale을 구분한다.
- `ai_strategy_loop/dashboard/frontend/bt-tab-utils.jsx`: `_BT_JOB_BADGE`를 cancelled, failed, no_trades, success, stale, artifact_missing까지 명확화한다.

### Phase 2
- `ai_strategy_loop/dashboard/frontend/bt-result-area.jsx`: 현재 aggregate 중심 `BtResultArea`를 shared ResultDetail body 또는 wrapper로 재사용한다. top summary plus buy/sell condition, middle trade symbol table plus symbol click chart, bottom analysis variable compare validation을 갖춘다.
- 선택적 `ai_strategy_loop/dashboard/frontend/result-detail.jsx`: 기존 파일이 과도하게 커질 때만 thin orchestrator로 신설한다.
- `ai_strategy_loop/dashboard/backtest_api.py`: job, run/gen, history item이 같은 ResultDetail payload를 만들게 한다. 필요하면 `/bt/result_detail`을 추가하되 `/bt/result` 호환 필드는 유지한다.
- `ui-contract.jsx`: `기록 검색`을 `히스토리` 또는 History archive로 rename하고 alias는 유지한다. Compare ownership은 History로 고정한다.
- `research-records-panel.jsx`: campaign records에서 condition/result evidence archive 진입점으로 remodel한다.
- `app.jsx`: home links와 route labels를 History와 Condition AI 용어로 정리한다. BacktestTab auto detail hook은 유지한다.

### Phase 3
- `ui-contract.jsx`: Condition AI home 라벨과 owner contract를 명시한다. Lab은 탐색/변수/엣지, Workbench는 심층 분석, History는 결과 상세/Compare, HOF는 승격 후보/좋은 결과 관리이다.
- `app.jsx`: home top을 whole process progress, Live phase log/current generation/current strategy, collapsible settings/gates/engine summary 순서로 재배치한다. 기존 `CurrentGenPanel`, `ResearchCriteriaBanner`, `ActiveStrategyPanel`, `PhaseTimeline`, `ProcessFlowPanel`, `PhaseDetailPanel`, `EnginePanel`을 우선 재사용한다.
- `rl-panel.jsx`, `research-lab.jsx`, `research-pro.jsx`, `rp-panel.jsx`, `dashboard-pages.jsx`, `dashboard-inventory.jsx`, `hof-inventory.jsx`, `chart-hall-of-fame.jsx`: 중복 ownership 문구를 제거하고 shared ResultDetail/History 링크로 맞춘다.

### Phase 4
- `bt-tab-library.jsx`: editor minHeight 200px를 상향하고 buy only/sell only large view를 추가한다.
- `sim-tab-root.jsx`, `sim-tab-controls.jsx`, `sim-chart-engines.jsx`, `sim-chart-shell.jsx`, `sim-tab-utils.jsx`, `replay_engine.py`, `simulation_api.py`: full bars는 보존하고 render input만 adaptive로 줄인다. play/pause/speed는 즉시 WS 제어와 optimistic UI를 유지한다. `최근 거래일`, `최대 상승일` help를 명확히 한다.
- `bt-tab-run.jsx`, `bt-tab-mode-results.jsx`, `bt-tab-analysis.jsx`, `backtest_api.py`: sweep/WFO 결과를 재사용해 variable influence와 result comparison을 제공한다.
- `ui/ui_vars_change.py`: reversible conversion 테스트 이후 self.vars adapter로 연결한다.
- `backtest/backfinder.py`: `self.tickcols`, `self.tickdata` precondition을 문서화하고 dedicated UI는 Phase 4 후반에 연결한다.

## Sequencing and dependencies

1. Phase 1 result identity plus library recovery: identity contract, backend derived fields, library status/actions, old JSON compatibility.
2. Phase 2 shared ResultDetail plus History: shared payload, ResultDetail rendering, History archive/Compare, BacktestTab auto detail 보존.
3. Phase 3 IA/home/lab cleanup: labels/contracts, home top order, collapsible settings/gates/engine, owner cleanup.
4. Phase 4 editor/replay/variable/backfinder: editor expansion, replay adaptive/help, variable influence, self.vars adapter, BackFinder staged UI.

Phase 2는 Phase 1 identity에 의존한다. Phase 3는 Phase 2 ownership 확정 뒤 진행한다. Phase 4 legacy tools는 foundation을 막지 않는다.

## Acceptance criteria

- Result library가 cancelled/failed/success/no-trades/stale/artifact-missing을 구분하고 disabled `취소됨` rows에 갇히지 않는다.
- 기존 artifact가 있으면 recover/open을 시도하고, 불가하면 same-condition rerun/open guidance를 제공한다.
- condition identity와 backtest evidence identity가 backend payload와 UI에 드러난다.
- shared ResultDetail이 job, run/generation, History item에서 같은 계약으로 렌더된다.
- ResultDetail은 top summary plus condition, middle trade symbol table plus symbol chart, bottom analysis variable compare validation을 포함한다.
- History가 archive default entry가 되고 Compare를 소유한다.
- BacktestTab은 run 완료 후 detail을 자동으로 연다.
- GUI parity core인 result table, symbol click chart, condition view가 존재한다.
- editor height 증가와 buy/sell single side large view가 있다.
- Condition AI home naming과 top layout 순서가 spec과 일치한다.
- Lab, Workbench, History, HOF ownership이 중복 없이 명확하다.
- Chart replay는 data preserving adaptive rendering과 responsive play/pause/speed를 만족한다.
- `최근 거래일`, `최대 상승일` help가 이해 가능하다.
- Phase 1, Phase 2, Phase 3, Phase 4 순서를 보존한다.

## Verification

계획 단계에서는 테스트/build/formatter를 실행하지 않았다. 승인 후 focused verification: backend identity/status는 `pytest tests/unit/test_dashboard_run_state.py tests/unit/test_dashboard_backtest_detail.py -q` plus new classification tests. ResultDetail/History는 `pytest tests/unit/dashboard/test_dashboard_ui_remodel.py tests/unit/test_dashboard_backtest_detail.py tests/unit/test_dashboard_run_compare_frontend.py -q` plus static tests for History label, Compare ownership, shared ResultDetail import, BacktestTab auto-open hook. IA/HOF/Lab은 `pytest tests/unit/test_dashboard_hall_of_fame.py tests/unit/test_dashboard_research_lab_frontend.py tests/unit/dashboard/test_dashboard_ui_remodel.py -q`. Phase 4는 `pytest tests/unit/test_dashboard_chart_explanations.py tests/unit/test_dashboard_strategy_prompt_frontend.py -q` plus editor, quick help, adaptive render, variable influence, BackFinder staged tests. Manual QA는 `/ui/backtest` post run detail, `/ui/evolution/records` History label, `/ui/chart-replay` preset/speed/pause/resume 확인이다.

## Risks and mitigations

Persisted job schema break는 additive fields와 derived API fields로 막는다. Duplicate ResultDetail은 BacktestTab과 History가 같은 body를 소비하게 해서 막는다. History rename route break는 `/ui/records` alias를 유지한다. Symbol chart payload growth는 bounded rows 또는 lazy per symbol fetch로 완화한다. BackFinder 오해는 `backtest/backfinder.py` precondition tests로 막는다. Replay downsampling은 full bars store와 render only sampling으로 데이터 손실을 막는다. IA cleanup은 삭제보다 reorder/collapse를 우선한다.

## Handoff guidance

승인된 실행은 executor가 Phase 1만 먼저 맡는다. Phase 1과 Phase 2 뒤 architect review를 받는다. ResultDetail payload가 애매하면 Phase 2 전 critic을 사용한다. team은 승인된 coordinated multi worker 실행에만 사용한다. ultragoal은 네 phase가 durable ledger 작업으로 커질 때만 사용한다.
