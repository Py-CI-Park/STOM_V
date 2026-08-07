# RALPLAN-DR revision 113: 조건식 AI 대시보드 강화 계획

상태: pending approval. 정본은 `.gjc/specs/deep-interview-condition-ai-dashboard-strengthening.md`이며 Architect 112와 Critic 112의 WATCH COMMENT를 반영한다. 실행 승인은 없으므로 제품 코드, 테스트, build, formatter는 실행하지 않는다.

## Summary

wt-dev 대시보드는 조건식 expression을 장기 identity로, 백테스트 result를 evidence unit으로 삼는 Condition AI 연구 플랫폼으로 재구성한다. 기존 구조는 `bt-tab-root.jsx`가 BacktestTab, `BtResultArea`, `BtRunPanel`, `BtResultLibrary`, 에디터, 진화세대 선택, 오버레이와 포트폴리오를 조합한다. `backtest_jobs.py`는 job JSON을 복원하지만 running 또는 pending 손실은 stale 성격의 error로 접는다. `/bt/result`는 job과 run/gen을 비슷하게 반환하지만 canonical ResultDetail 계약은 없다. Workbench의 `rp-heatmap.jsx`에는 `_RpHistory`와 `_RpRunCompare`가 있어 History와 Compare ownership을 중복시킬 수 있다. Phase 4 replay는 server frame, bars store, seek, export, signal logic을 authoritative로 유지하고 render input만 adaptive로 줄인다.

## RALPLAN-DR summary

### 원칙
1. Code hash first identity: 조건식 identity는 가능한 한 normalized buy/sell code hash에서 만든다. 이름은 표시와 legacy fallback일 뿐이다.
2. Evidence namespace: 백테스트 결과는 `job:<job_id>`, 진화 세대는 `gen:<run_id>:<gen_no>`, History archive 항목은 `history:<id>` namespace를 가진다.
3. One ResultDetail body: fetch/source container와 presentation을 분리하고 `ResultDetailBody`를 Backtest, run/gen, History가 공유한다.
4. History owns archive and compare: `_RpHistory`와 `_RpRunCompare`는 History로 이동하거나 Workbench에서 History 링크로 demote한다.
5. Render only replay adaptation: full bars, backend frames, seek, export, signal logic은 절대 truncate하지 않는다.

### Top 3 decision drivers
1. Mutable strategy name을 durable condition identity로 쓰면 old job, run/gen, rewritten strategy DB에서 잘못 병합될 수 있다.
2. Workbench 안의 `_RpHistory`와 `_RpRunCompare`를 그대로 두면 새 History와 Compare가 중복된다.
3. replay 성능 개선은 데이터 손실이 아니라 viewport, device, count budget 기반 render derivation이어야 한다.

### Options
- Option A, BacktestTab 중심 점진 통합: Phase 1 identity와 recovery, Phase 2 ResultDetailBody와 History, Phase 3 IA cleanup, Phase 4 editor replay variable BackFinder. 기존 `/bt/result`, `BtResultArea`, `BtResultLibrary`를 재사용한다. 선택한다.
- Option B, History 선행 구축: History를 먼저 만들지만 recovery와 code hash identity 전에는 unavailable evidence를 포장할 뿐이다. 기각한다.
- Option C, 신규 domain store 전면 재설계: identity DB는 깨끗하지만 protected path, DB cutover, V3K, live boundary 리스크가 커서 brownfield 범위를 넘는다. 기각한다.

## In scope / out of scope

In scope는 Phase 1 result identity와 library recovery, Phase 2 shared ResultDetailBody와 History, Phase 3 IA/home/lab/HOF/workbench ownership cleanup, Phase 4 editor/replay/variable/self.vars/BackFinder staged support이다. Out of scope는 승인 전 제품 코드 변경, 테스트/build/formatter 실행, live brokerage, V3K gate enablement, serial key, DB cutover, production export authority, old GUI pixel clone, backtest engine replacement, transformer/ML modeling이다.

## File-level changes

### Phase 1: result identity and library recovery

- `ai_strategy_loop/dashboard/backtest_jobs.py`: persisted job compatibility는 additive로 유지한다. restored running/pending은 generic error로만 표시하지 말고 `status_kind=stale`, `artifact_state=unknown_or_lost_tracking` 같은 derived semantics를 API에서 노출한다.
- `ai_strategy_loop/dashboard/backtest_api.py`: `/bt/jobs`, `/bt/job`, `/bt/result`에 additive identity와 action fields를 붙인다. 기존 fields인 `available`, `job_id`, `run_id`, `gen_no`, `status`, `metrics`, `analysis`, `mode_result`, `message`는 제거하거나 의미 변경하지 않는다.
- Identity contract:
  - `evidence_id`: `job:<job_id>` for web backtest jobs, `gen:<run_id>:<gen_no>` for evolution generations, `history:<id>` for History archive items.
  - `condition_identity.kind`: `code_hash` when normalized buy and sell code are available, else `name_only_legacy`.
  - `condition_identity.buy_hash` and `sell_hash`: normalized code hash, for example whitespace and line ending normalization before sha256. Hash derivation must be deterministic and documented in tests.
  - `condition_identity.display_name`: buy/sell names remain UI labels only.
  - `condition_identity.confidence`: `high` for code_hash, `medium` only when one side code hash exists and one side is legacy, `low` for pure `name_only_legacy`.
  - `condition_identity.artifact_note`: explicit user-visible note such as current strategy DB code matched, code snapshot missing, csv only, or legacy job JSON name only.
- `ai_strategy_loop/dashboard/frontend/bt-tab-run.jsx`: result library rows expose status-aware `open`, `recover`, `rerun_same_condition`, `open_report`, and explanation actions. `success` and `no_trades` open detail. failed, cancelled, timeout, stale, artifact missing do not silently open detail but show available open/recover/rerun actions.
- `ai_strategy_loop/dashboard/frontend/bt-tab-utils.jsx`: `_BT_JOB_BADGE` includes cancelled, failed/error, timeout, no_trades, success, stale, artifact_missing, recoverable.

### Phase 2: shared ResultDetailBody and History

- `ai_strategy_loop/dashboard/frontend/bt-result-area.jsx`: split fetching from rendering. Create or extract a presentational `ResultDetailBody` that receives canonical payload and actions. Backtest job, run/gen, and History containers fetch/resolve source-specific data and pass it to the body.
- Optional `ai_strategy_loop/dashboard/frontend/result-detail.jsx`: use only as a thin shared module if it prevents `bt-result-area.jsx` from becoming a source-specific tangle. It must not become a duplicate detail implementation.
- `ai_strategy_loop/dashboard/backtest_api.py`: preserve `/bt/result` additively. If `/bt/result_detail` is added, it composes from the same adapter and keeps `/bt/result` compatibility.
- `ai_strategy_loop/dashboard/frontend/ui-contract.jsx`: rename `기록 검색` semantics to `히스토리` or History archive while preserving aliases such as `/ui/records`.
- `ai_strategy_loop/dashboard/frontend/research-records-panel.jsx`: remodel as History archive for condition/result evidence, with campaign/update-log lookup demoted to secondary archive material.
- `ai_strategy_loop/dashboard/frontend/rp-heatmap.jsx`: migrate `_RpHistory` and `_RpRunCompare` into History ownership or demote them to Workbench links that open History modes. Workbench must not own result detail or Compare after this phase.
- `ai_strategy_loop/dashboard/frontend/bt-stat-panels.jsx`: reuse `BtCompareView`, but canonical Compare entry belongs to History.
- `app.jsx`: BacktestTab post-run auto-detail must include both `success` and `no_trades` terminal states.

### Phase 3: IA, home, lab, workbench, HOF cleanup

- `ui-contract.jsx`: Condition AI home labels and owner contracts are explicit. Research Lab owns exploration, variable, edge, correlation, validation. Workbench owns deep analysis only. History owns archive, ResultDetail, Compare. HOF owns promotion candidates and good result management but links to shared detail.
- `app.jsx`: home top order is whole-process progress, then Live phase log/current generation/current strategy, then collapsible settings/gates/engine summary. Reuse `CurrentGenPanel`, `ResearchCriteriaBanner`, `ActiveStrategyPanel`, `PhaseTimeline`, `ProcessFlowPanel`, `PhaseDetailPanel`, `EnginePanel` before adding UI.
- `rl-panel.jsx`, `research-lab.jsx`, `research-pro.jsx`, `rp-panel.jsx`, `rp-heatmap.jsx`, `dashboard-pages.jsx`, `dashboard-inventory.jsx`, `hof-inventory.jsx`, `chart-hall-of-fame.jsx`: remove or rewrite conflicting ownership text. `_RpHistory` and `_RpRunCompare` are not allowed as Workbench-owned archive and compare after migration.

### Phase 4: editor, replay, variable, self.vars, BackFinder

- `bt-tab-library.jsx`: increase editor height and add buy-only and sell-only large view.
- `sim-tab-root.jsx`, `sim-tab-controls.jsx`, `sim-chart-engines.jsx`, `sim-chart-shell.jsx`, `sim-tab-utils.jsx`: derive `renderBars` per engine using viewport, device capability, and count budget. Do not mutate or truncate `barsRef`.
- `replay_engine.py`, `simulation_api.py`: server frames, history snapshots, seek protocol, export, and signal calculations remain authoritative and unchanged except for additive metadata if needed.
- `bt-tab-run.jsx`, `bt-tab-mode-results.jsx`, `bt-tab-analysis.jsx`, `backtest_api.py`: variable influence starts from existing sweep/WFO results and comparison surfaces.
- `ui/ui_vars_change.py`: self.vars support is staged behind reversible adapter tests.
- `backtest/backfinder.py`: BackFinder UI is staged after explicit `self.tickcols` and `self.tickdata` precondition handling.

## Sequencing and dependencies

1. Phase 1: define code-hash-first identity and evidence namespace, add additive API fields, status/action taxonomy, and no_trades auto-open behavior.
2. Phase 2: introduce ResultDetailBody, source containers, History archive, and migrate/demote `_RpHistory` and `_RpRunCompare` from Workbench ownership.
3. Phase 3: update labels, home layout, route contracts, dashboard inventory, Lab/Workbench/HOF ownership.
4. Phase 4: editor expansion, render-only replay adaptation, variable influence, self.vars adapter, BackFinder staged UI.

Phase 2 depends on Phase 1 identity. Phase 3 depends on Phase 2 ownership cleanup. Phase 4 must not block identity, recovery, or History.

## Acceptance criteria

- `condition_identity` is code-hash-first and exposes `name_only_legacy` confidence and artifact notes when code is missing.
- Every evidence source has a namespaced `evidence_id`.
- Result library distinguishes success, no_trades, failed, cancelled, timeout, stale, artifact missing, recoverable states.
- `success` and `no_trades` post-run completions auto-open ResultDetail. failed/cancelled/stale expose status-aware open/recover/rerun actions.
- `ResultDetailBody` is presentational and source containers handle job, run/gen, and History item resolution.
- `/bt/result` existing fields remain additive-compatible.
- History owns ResultDetail and Compare. Workbench `_RpHistory` and `_RpRunCompare` are migrated or demoted to History links.
- ResultDetail shows top summary plus buy/sell condition, middle trade-symbol table plus symbol-click chart, and bottom analysis/variable/compare/validation where data exists.
- Condition AI home naming and top layout match the spec.
- Replay adaptation is render-only. Full bars, server frames, seek, export, and signal logic remain authoritative.
- Phase 1, Phase 2, Phase 3, Phase 4 order is preserved.

## Verification

No tests/builds/formatters are run in planning. Approved execution verification must include:

- Identity legacy confidence: unit tests for `condition_identity.kind`, buy/sell hash stability, `name_only_legacy` confidence, and artifact_note for old job JSON, current strategy DB code, missing code, and run/gen evidence.
- Additive API fields: tests that `/bt/result` still returns `available`, `job_id`, `run_id`, `gen_no`, `status`, `metrics`, `analysis`, `mode_result` as before plus new identity/action fields.
- no_trades auto-open: frontend static or component test that terminal `no_trades` follows the same auto-detail hook as success, while failed/cancelled/stale render action affordances only.
- ResultDetail split: static tests assert `ResultDetailBody` has no fetch/source decision and job/run-gen/history containers pass canonical payload to it.
- rp-heatmap ownership: static tests assert `_RpHistory` and `_RpRunCompare` are moved to History or demoted to History links, and Workbench no longer owns History/Compare detail.
- History/Compare routing: tests in `test_dashboard_ui_remodel.py` or focused frontend tests for History label, alias preservation, and Compare ownership.
- Replay render-only adaptation: tests assert `barsRef`, server frame handling, seek/history, export, and signal logic use full data while per-engine render arrays are windowed/decimated.
- Suggested focused suites after implementation: `pytest tests/unit/test_dashboard_run_state.py tests/unit/test_dashboard_backtest_detail.py -q`, `pytest tests/unit/dashboard/test_dashboard_ui_remodel.py tests/unit/test_dashboard_run_compare_frontend.py -q`, `pytest tests/unit/test_dashboard_hall_of_fame.py tests/unit/test_dashboard_research_lab_frontend.py -q`, and Phase 4 chart/editor tests.

## Risks and mitigations

- Identity drift: mitigate with code-hash-first identity, namespaced evidence_id, explicit legacy confidence and artifact notes.
- Workbench duplicate History/Compare: mitigate by including `rp-heatmap.jsx` in Phase 2 and Phase 3 and requiring migration or demotion.
- API breakage: mitigate by additive fields and compatibility tests for `/bt/result`.
- ResultDetail duplication: mitigate with presentational `ResultDetailBody` plus source containers.
- Replay data loss: mitigate by render-only adaptation and tests that authoritative full data remains intact.
- BackFinder/self.vars legacy risk: mitigate with Phase 4 adapter tests before UI execution.

## Handoff guidance

Executor should start with Phase 1 identity/status/action work only. Architect review is required after Phase 1 and Phase 2. Critic review is required before Phase 2 execution if `ResultDetailBody` payload remains ambiguous. Use team only after explicit execution approval for coordinated backend/frontend/test slices. Use ultragoal only if this becomes a durable multi-goal ledger.
