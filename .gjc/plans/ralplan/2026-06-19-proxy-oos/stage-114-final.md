# Pending Approval Plan: wt-dev 조건식 AI 대시보드 전면 강화

Status: **pending approval**. 이 문서는 실행 계획이며 제품 코드는 변경하지 않았다. 실행은 별도 승인 후에만 진행한다.

## Source Artifacts
- Deep Interview spec: `.gjc/specs/deep-interview-condition-ai-dashboard-strengthening.md`
- Planner: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-112-planner.md`
- Architect pass 1: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-112-architect.md` — WATCH / COMMENT
- Critic pass 1: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-112-critic.md` — ITERATE
- Planner revision: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-113-revision.md`
- Architect pass 2: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-113-architect.md` — CLEAR / APPROVE
- Critic pass 2: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-113-critic.md` — OKAY

## Objective
wt-dev 대시보드를 조건식 AI 연구 플랫폼으로 강화한다. 조건식 expression은 장기 identity이고, 백테스트 result는 evidence unit이다. 사용자는 결과를 복구·재실행·상세 분석·히스토리·명예의 전당·리서치랩·워크벤치·차트 리플레이·변수/백파인더 단계형 도구로 중복 없이 연결해 연구할 수 있어야 한다.

## RALPLAN-DR Summary

### Principles
1. **Code-hash-first identity**: 조건식 identity는 가능한 한 normalized buy/sell code hash로 만든다. 이름은 표시와 legacy fallback일 뿐이다.
2. **Evidence namespace**: evidence는 `job:<job_id>`, `gen:<run_id>:<gen_no>`, `history:<id>`로 구분한다.
3. **One ResultDetail body**: source container와 presentation을 분리하고 `ResultDetailBody`를 Backtest, History, run/gen, HOF 링크가 공유한다.
4. **History owns archive and Compare**: Workbench 안의 `_RpHistory`와 `_RpRunCompare`는 History로 이동하거나 History 링크로 demote한다.
5. **Render-only replay adaptation**: chart replay는 full bars/backend frames/seek/export/signal logic을 보존하고 render input만 adaptive로 줄인다.

### Decision Drivers
1. 현재 핵심 실패는 결과 라이브러리가 `취소됨` disabled rows에 갇히는 문제이므로 result identity/status/action 복구가 선행되어야 한다.
2. History, Backtest, Workbench, HOF가 각자 detail을 만들면 중복이 재발하므로 shared ResultDetail이 필요하다.
3. `self.vars`와 BackFinder는 legacy 제약이 강하므로 foundational result/history 작업 뒤 Phase 4에서 단계형으로 다룬다.

### Options Considered
| Option | Pros | Cons | Verdict |
|---|---|---|---|
| A. BacktestTab-centered incremental integration | 기존 `/bt/result`, `BtResultArea`, `BtResultLibrary`, run/gen 흐름 재사용. Phase order와 brownfield 안전성에 맞음. | identity adapter와 ownership migration이 여러 파일에 걸침. | **Chosen** |
| B. History-first repaint | 사용자가 원하는 최종 IA가 빨리 보임. | recovery 전에 unavailable/cancelled evidence를 보기 좋게 포장할 뿐이고 중복 위험 큼. | Rejected |
| C. New domain store redesign | ontology는 가장 깔끔함. | DB cutover/protected path/live boundary 리스크가 크고 spec 범위 초과. | Rejected |

## ADR

### Decision
Option A를 채택한다: Phase 1에서 identity/status/action을 additive API로 복구하고, Phase 2에서 shared `ResultDetailBody`와 History ownership을 확정하며, Phase 3에서 IA/home/lab/HOF를 정리하고, Phase 4에서 editor/replay/variable/self.vars/BackFinder를 단계적으로 구현한다.

### Why Chosen
기존 STOM dashboard는 이미 BacktestTab, BtResultArea, run/gen detail, ResearchLab, Workbench, Chart Replay를 갖고 있다. 완전 신규 store나 History-first repaint는 회귀와 중복 위험이 더 크다. incremental integration이 사용자의 “중복 없이 연구 가능한 조건식 AI 플랫폼” 목표와 가장 잘 맞는다.

### Consequences
- Phase 1 없이는 Phase 2+ UI 개편을 시작하지 않는다.
- `/bt/result`는 기존 필드를 유지하고 additive identity/action fields만 추가한다.
- Workbench의 history/compare ownership은 반드시 정리한다.
- Replay 최적화는 authoritative data를 줄이지 않는다.

### Follow-ups
- Phase 4 legacy `self.vars`와 BackFinder 전용 UI는 Phase 1~3 완료 후 adapter tests와 함께 진행한다.
- Transformer/ML 연구는 이번 plan 밖의 future research로 유지한다.

## Implementation Plan

### Phase 1 — Result identity and library recovery
**Goal:** 결과 라이브러리가 상태를 정확히 보여주고 open/recover/rerun 경로를 제공한다.

**Files/surfaces**
- `ai_strategy_loop/dashboard/backtest_jobs.py`
- `ai_strategy_loop/dashboard/backtest_api.py`
- `ai_strategy_loop/dashboard/frontend/bt-tab-run.jsx`
- `ai_strategy_loop/dashboard/frontend/bt-tab-utils.jsx`

**Required contract**
- `evidence_id`: `job:<job_id>` for web backtest jobs, `gen:<run_id>:<gen_no>` for evolution generations, `history:<id>` for History archive items.
- `condition_identity.kind`: `code_hash` when normalized buy/sell code are available, else `name_only_legacy`.
- `condition_identity.buy_hash` / `sell_hash`: deterministic normalized code hashes.
- `condition_identity.display_name`: UI label only.
- `condition_identity.confidence`: `high` for full code hash, `medium` for partial hash, `low` for pure legacy name-only evidence.
- `condition_identity.artifact_note`: code snapshot matched, code missing, csv only, legacy job JSON name-only, etc.
- Preserve `/bt/result` existing fields: `available`, `job_id`, `run_id`, `gen_no`, `status`, `metrics`, `analysis`, `mode_result`, `message`.
- Add status/action fields additively: `status_kind`, `artifact_state`, `open_actions`, `rerun_spec`, `recoverable`.
- `success` and `no_trades` are openable and should auto-open detail after completion. failed/cancelled/stale/artifact-missing expose status-aware open/recover/rerun actions instead of silent detail open.

**Acceptance**
- Result library no longer traps users in disabled `취소됨` rows only.
- Existing artifacts are opened when available; missing artifacts show recovery/rerun guidance.
- Existing consumers of `/bt/result` still receive old fields.

### Phase 2 — Shared ResultDetailBody and History
**Goal:** Backtest, History, run/gen, Workbench/HOF links share one result detail contract.

**Files/surfaces**
- `ai_strategy_loop/dashboard/frontend/bt-result-area.jsx`
- optional `ai_strategy_loop/dashboard/frontend/result-detail.jsx`
- `ai_strategy_loop/dashboard/backtest_api.py`
- `ai_strategy_loop/dashboard/frontend/ui-contract.jsx`
- `ai_strategy_loop/dashboard/frontend/research-records-panel.jsx`
- `ai_strategy_loop/dashboard/frontend/rp-heatmap.jsx`
- `ai_strategy_loop/dashboard/frontend/bt-stat-panels.jsx`
- `ai_strategy_loop/dashboard/frontend/app.jsx`

**Required contract**
- Extract presentational `ResultDetailBody` with no fetch/source branching.
- Source containers resolve job, run/gen, and History item payloads, then pass canonical payload/actions to the body.
- History replaces “기록 검색” semantics as the default archive entry while preserving `/ui/records` compatibility.
- Compare belongs to History. `_RpHistory` and `_RpRunCompare` in `rp-heatmap.jsx` must be moved or demoted to links opening History modes.
- ResultDetail must show top summary + buy/sell condition, middle trade-symbol table + symbol-click chart, and bottom full analysis/variable/compare/validation when data exists.
- BacktestTab still opens detail automatically after success/no_trades completion.

**Acceptance**
- One shared ResultDetail path renders job, run/gen, and History evidence.
- Workbench no longer owns archive/Compare detail.
- History is the default archive entry and owns Compare.

### Phase 3 — IA, Condition AI home, Lab/Workbench/HOF cleanup
**Goal:** 대시보드 중복을 제거하고 사용자에게 현재 실행·설정·연구 위치를 명확히 보여준다.

**Files/surfaces**
- `ai_strategy_loop/dashboard/frontend/ui-contract.jsx`
- `ai_strategy_loop/dashboard/frontend/app.jsx`
- `ai_strategy_loop/dashboard/frontend/rl-panel.jsx`
- `ai_strategy_loop/dashboard/frontend/research-lab.jsx`
- `ai_strategy_loop/dashboard/frontend/research-pro.jsx`
- `ai_strategy_loop/dashboard/frontend/rp-panel.jsx`
- `ai_strategy_loop/dashboard/frontend/rp-heatmap.jsx`
- `ai_strategy_loop/dashboard/frontend/dashboard-pages.jsx`
- `ai_strategy_loop/dashboard/frontend/dashboard-inventory.jsx`
- `ai_strategy_loop/dashboard/frontend/hof-inventory.jsx`
- `ai_strategy_loop/dashboard/frontend/chart-hall-of-fame.jsx`

**Required contract**
- “진화 홈/개요” user-facing naming becomes Condition AI where applicable.
- Home top order: whole-process progress → Live phase log/current generation/current strategy → collapsible settings/gates/engine summary.
- Reuse existing panels first: `CurrentGenPanel`, `ResearchCriteriaBanner`, `ActiveStrategyPanel`, `PhaseTimeline`, `ProcessFlowPanel`, `PhaseDetailPanel`, `EnginePanel`.
- Research Lab owns exploration/edge/variable/correlation/combos/validation.
- Workbench owns deep analysis only.
- History owns archive/ResultDetail/Compare.
- Hall of Fame owns promotion candidates and good result management; it links to shared detail.

**Acceptance**
- No “연구실 안에 또 연구실/위키” or duplicate Workbench/History/Compare ownership.
- Home first screen answers: current phase, current strategy/generation, process position, gate/engine settings.

### Phase 4 — Editor, chart replay, variable tools, self.vars, BackFinder
**Goal:** 연구 UX를 완성하되 legacy-heavy tools는 safe adapter path로 구현한다.

**Files/surfaces**
- `ai_strategy_loop/dashboard/frontend/bt-tab-library.jsx`
- `ai_strategy_loop/dashboard/frontend/sim-tab-root.jsx`
- `ai_strategy_loop/dashboard/frontend/sim-tab-controls.jsx`
- `ai_strategy_loop/dashboard/frontend/sim-chart-engines.jsx`
- `ai_strategy_loop/dashboard/frontend/sim-chart-shell.jsx`
- `ai_strategy_loop/dashboard/frontend/sim-tab-utils.jsx`
- `ai_strategy_loop/dashboard/replay_engine.py`
- `ai_strategy_loop/dashboard/simulation_api.py`
- `ai_strategy_loop/dashboard/frontend/bt-tab-run.jsx`
- `ai_strategy_loop/dashboard/frontend/bt-tab-mode-results.jsx`
- `ai_strategy_loop/dashboard/frontend/bt-tab-analysis.jsx`
- `ai_strategy_loop/dashboard/backtest_api.py`
- `ui/ui_vars_change.py`
- `backtest/backfinder.py`

**Required contract**
- Increase editor height and add buy-only/sell-only large view.
- Chart replay derives render arrays by viewport/device/count budget only; authoritative data remains full.
- Quick start help for `최근 거래일`, `최대 상승일` is clear.
- Variable influence starts from existing sweep/WFO results and comparison surfaces.
- `self.vars` support is behind reversible adapter tests.
- BackFinder UI is staged after explicit `self.tickcols` and `self.tickdata` precondition handling.

**Acceptance**
- Replay play/pause/speed feels immediate while preserving data correctness.
- Editor readability improves without breaking save/validate/delete flows.
- BackFinder and legacy variable features do not block foundational phases.

## Verification Plan
Planning phase ran no tests, builds, formatters, or product mutations.

Approved execution must include:
- Identity tests for `condition_identity.kind`, deterministic hash stability, `name_only_legacy` confidence, and `artifact_note` across old job JSON, current strategy DB code, missing code, and run/gen evidence.
- Additive API tests proving `/bt/result` still returns existing fields plus new identity/action fields.
- UI/static tests for result library status/action taxonomy and `no_trades` auto-open.
- ResultDetail split tests proving `ResultDetailBody` has no fetch/source decisions and job/run-gen/history containers pass canonical payload.
- `rp-heatmap.jsx` ownership tests proving `_RpHistory` and `_RpRunCompare` are migrated/demoted from Workbench ownership.
- History/Compare routing tests for label, alias preservation, and Compare ownership.
- Replay tests proving render-only adaptation: full `barsRef`, server frames, seek/history snapshots, export, and signal logic remain authoritative.
- Suggested focused suites after implementation: `pytest tests/unit/test_dashboard_run_state.py tests/unit/test_dashboard_backtest_detail.py -q`, `pytest tests/unit/dashboard/test_dashboard_ui_remodel.py tests/unit/test_dashboard_run_compare_frontend.py -q`, `pytest tests/unit/test_dashboard_hall_of_fame.py tests/unit/test_dashboard_research_lab_frontend.py -q`, plus Phase 4 chart/editor tests.

## Risks and Mitigations
| Risk | Mitigation |
|---|---|
| Identity drift from mutable strategy names | Code-hash-first identity, namespaced evidence_id, visible legacy confidence/artifact notes. |
| Duplicate History/Compare after remodel | Include `rp-heatmap.jsx` in Phase 2/3 and require migration/demotion of `_RpHistory`/`_RpRunCompare`. |
| API regression | Additive fields only; old `/bt/result` fields preserved and tested. |
| ResultDetail branching tangle | Presentational `ResultDetailBody` plus source-specific containers. |
| Replay data loss | Render-only adaptation; full bars/backend frames/seek/export/signal logic preserved. |
| Legacy self.vars/BackFinder instability | Phase 4 adapter tests before UI wiring. |

## Execution Handoff Shape
- Start with Phase 1 only. Do not implement later-phase UI before identity/status/action contract exists.
- After Phase 1 and Phase 2, run Architect review before continuing.
- Use Critic review before Phase 2 execution if the ResultDetail payload contract is still ambiguous.
- Use Ultragoal for durable execution tracking after explicit approval. Use Team only if the user explicitly requests tmux-based coordinated workers.

## Approval Boundary
This plan is **pending approval**. No source files were modified by RALPLAN. Execution requires a separate explicit approval path.
