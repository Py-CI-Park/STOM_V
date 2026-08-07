# Pending Approval RALPLAN: Remaining Condition AI Dashboard Parity Gaps

Status: **pending approval**. Planning-only artifact for `C:/System_Trading/STOM/STOM_V.wt-dev`. No product source, tests, builds, formatters, protected runtime paths, commits, or pushes were mutated.

## Summary
Create the next implementation plan for the remaining Condition AI dashboard parity gaps after prior ultragoal work. Evidence anchors: `.gjc/plans/ralplan/2026-06-19-proxy-oos/pending-approval.md`, `.gjc/specs/deep-interview-condition-ai-dashboard-strengthening.md`, and inspected current files `app.jsx`, `rl-panel.jsx`, `analysis.jsx`, `phase-detail.jsx`, `evolution-gui-parity-panel.jsx`, `bt-gui-parity.jsx`, `styles.css`, `ui-contract.jsx`, `rl-analysis.jsx`, `app.py`, `fitness/{edge_ratio,feature_importance,correlation}.py`, and dashboard tests under `tests/unit/`.

## RALPLAN-DR Summary
### Principles
1. One owner per job: Research Lab owns exploration/edge/variables/correlation/combos/validation; History owns ResultDetail/Compare/archive; Workbench owns deep analysis; HOF owns promotion candidates. Home links and summarizes only.
2. Fix sizing before adding density: bounded heatmaps, consistent chart scale, and readable cards come first.
3. Research APIs stay read-only and additive; no generation, scoring, hard-gate, export, live broker, or protected-path coupling.
4. Process animation must reflect real state, preserving `current_step`, `step_timings`, phase timers, and logs.
5. Research views are advisory and never promotion/final-approval authority.

### Top Drivers
1. Prior work recovered result/detail ownership; remaining scope is UX/IA/visualization parity.
2. Current Lab fullscreen and home-embedded ResearchLabPanel risk duplicate ownership.
3. Current edge heatmap fixed sizing and Evolution GUI Parity `columns={2}` make key charts oversized or cramped.

### Options
| Option | Pros | Cons | Verdict |
|---|---|---|---|
| A. Focused brownfield frontend remodel; backend only if additive analysis fields are required | Lowest blast radius; preserves routes and owner boundaries; directly targets gaps | Requires test marker updates | **Chosen** |
| B. New Lab/Workbench shell | Fast visual unification | High duplicate-surface and routing churn risk | Rejected |
| C. Backend data-model expansion first | Strong long-term analytics | Over-scoped, DB/runtime risk | Rejected |

## In Scope / Out of Scope
In scope: edge/time x market-cap sizing, Lab fullscreen removal, Research Lab visualization/functionality strengthening, native Process tab remodel and animations, Condition AI home research-suite readability, Evolution GUI Parity one-column larger graphs, focused tests.

Out of scope: new top-level pages; duplicate History/Compare/Workbench/Lab surfaces; backtest engine replacement; live brokerage; V3K gates; serial-key behavior; DB cutover; runtime state writes; chart replay except render-only incidental changes; gates/formatters/builds; commits/pushes.

## File-Level Changes
- `ai_strategy_loop/dashboard/frontend/analysis.jsx`: bound `_Heatmap` sizing; use CSS classes and clamped cells; keep one merged edge/time x market-cap exploration view with compact stats, legend, counts, and stable empty/error/loading states.
- `ai_strategy_loop/dashboard/frontend/rl-panel.jsx`: remove `fullscreen` state, fixed shell style, and Lab fullscreen button; clarify method/axis/run context; keep SPA workbench navigation.
- `ai_strategy_loop/dashboard/frontend/rl-analysis.jsx`: strengthen correlation/combo views with top-N controls, sorted/filterable views, legends, selected-pair detail, low-sample warnings, and honest insufficient-data states.
- `ai_strategy_loop/dashboard/frontend/phase-detail.jsx`: build native Process tab composition around `ProcessFlowPanel` and `ProcessFlowDiagram`; strengthen active node/edge animation while preserving timing/state contracts.
- `ai_strategy_loop/dashboard/frontend/app.jsx`: replace process iframe embedding with native process content; add home Research Suite cards; remove full interactive Lab duplication from home or reduce it to navigation/summary; update idle/home copy.
- `ai_strategy_loop/dashboard/frontend/evolution-gui-parity-panel.jsx`: render `BtGuiParitySection` in one-column large mode, not `columns={2}`.
- `ai_strategy_loop/dashboard/frontend/bt-gui-parity.jsx`: make one-column large mode explicit while preserving Backtest result usage.
- `ai_strategy_loop/dashboard/frontend/styles.css`: add bounded research heatmap, Lab controls, process animation/reduced-motion, home research-suite, and GUI parity one-column styles; remove stale Lab fullscreen styling.
- `ai_strategy_loop/dashboard/frontend/ui-contract.jsx`: text-only updates if needed; no route additions.
- Optional only: `ai_strategy_loop/dashboard/app.py` and `ai_strategy_loop/fitness/correlation.py` for additive analysis-only combo/correlation fields if existing payload is insufficient.
- Tests: update `tests/unit/dashboard/test_dashboard_ui_remodel.py`, `tests/unit/test_dashboard_research_lab_frontend.py`, `tests/unit/dashboard/test_p11_process_flow.py`, `tests/unit/test_process_timing.py`, `tests/unit/dashboard/test_research_records_frontend.py`, and `tests/unit/dashboard/test_evolution_gui_parity.py`.

## Sequencing and Dependencies
### Phase 1: Lab ownership cleanup and heatmap sizing
Remove Lab fullscreen state/action. Convert edge heatmap from fixed SVG sizing to bounded responsive frame. Keep one primary cross heatmap plus secondary segment bars. Update CSS and tests.

### Phase 2: Research visualization strengthening
Single-source axis/method/run controls. Improve variable importance with segment counts, selected segment, capped rows/show-more, Cohens d legend, and low-sample warnings. Improve correlation with sorted top rows, matrix/list option if needed, top-N cap, sample counts, and insufficient states. Improve combos with selected-pair detail and no fabricated stats. Add backend fields only additively if required.

### Phase 3: Process tab remodel and animation
Remove `app.jsx` process iframe. Compose native process page from graph, status cards, timing grid, defaults/gates table, logs, and explanations. Add active pulse, completed-path glow, current-edge motion, completion freeze, and `prefers-reduced-motion`. Preserve current-step/timing contracts.

### Phase 4: Condition AI home research suite
Add readable Home cards linking to Research Lab, History, Workbench, HOF, Backtest, and Chart Replay. Keep Home as navigation/summary, not Lab/History/Workbench owner. Reorder first screen: process progress, live phase/current generation/current strategy, settings/gates/engine summary, research-suite entry points. Preserve route keys.

### Phase 5: Evolution GUI Parity graph enlargement
Switch Evolution GUI Parity to one-column larger stacked graphs. Make `BtGuiParitySection` copy/style explicit for one-column vs two-column. Update tests and perform duplicate-surface audit.

## Acceptance Criteria
- Edge/time x market-cap panel has bounded responsive cells, readable labels/counts, consistent typography, and scroll only when data volume requires it.
- Research Lab has no fullscreen toggle, fixed fullscreen shell style, or user-facing full-screen action.
- Home does not render duplicate full Lab/History/Compare/Workbench owners; it links/summarizes only.
- Research views show sample counts, legends, selected axis/method/run context, low-sample warnings, and honest empty/error states.
- Variable-combination detail does not invent statistics absent from payloads.
- Process tab is native with no embedded iframe in `app.jsx`; active step, completed path, timing, logs, defaults/gates, and explanations are visible and animated with reduced-motion support.
- Condition AI home clearly exposes the research suite with readable cards/links and first-screen ordering.
- Evolution GUI Parity no longer passes `columns={2}` and renders one-column larger stacked charts.
- Route keys remain stable: top-level `evolution`, `backtest`, `simulation`; subtabs `overview`, `process`, `records`, `lab`, `workbench`, `verdict`.
- `/bt/result`, if touched, remains additive only and preserves existing fields/consumers.
- Chart replay remains untouched; if touched incidentally, changes are render-only.
- wt-dev, STOM 2U_C nonrelease policy, and protected runtime paths remain untouched.

## Verification
Planning ran no tests/builds/formatters/gates. Approved execution should use focused tests only and skip gates/formatters:

```powershell
pytest tests/unit/dashboard/test_dashboard_ui_remodel.py tests/unit/test_dashboard_research_lab_frontend.py tests/unit/dashboard/test_p11_process_flow.py tests/unit/test_process_timing.py tests/unit/dashboard/test_research_records_frontend.py tests/unit/dashboard/test_evolution_gui_parity.py -q
```

If Phase 2 adds backend fields:

```powershell
pytest tests/unit/test_analysis_gen_filter.py tests/unit/dashboard/test_backtest_report.py tests/unit/test_dashboard_research_lab_frontend.py -q
```

If `BtGuiParitySection` affects backtest detail beyond Evolution parity:

```powershell
pytest tests/unit/test_dashboard_backtest_detail.py tests/unit/dashboard/test_research_records_frontend.py -q
```

Manual QA after approved implementation: open `/ui/evolution`, `/ui/evolution/process`, `/ui/evolution/lab`, and a selected Evolution GUI Parity generation; confirm no Lab fullscreen, no process iframe, bounded heatmap, clear research-suite cards, and stacked large GUI parity charts.

## Risks and Mitigations
| Risk | Mitigation |
|---|---|
| Home cards become duplicate owners | Cards navigate/summarize only; tests reject ResultDetail, Compare, full Lab, and Workbench internals on Home. |
| Heatmap becomes too small | Clamp min/max cells; keep counts, legend, and controlled scroll. |
| Process animation hurts performance | Animate only active path/node, freeze idle/complete, add reduced-motion. |
| Research UI implies promotion authority | Copy says advisory only; HOF/final approval remain separate. |
| Backend fields affect loop behavior | Keep changes in analysis endpoints/modules only; no writes or hot-path coupling. |
| Static tests are brittle | Update tests with source changes while preserving route keys and exports. |
| `/bt/result` regression | Avoid touching it; if touched, add fields only and run focused detail tests. |
| Protected path mutation | Do not write runtime DB/log/graph paths; use tmp_path fixtures only. |

## ADR
Decision: use a focused brownfield frontend remodel with optional additive analysis-only backend fields. Keep routes and owner boundaries stable. Remove duplicate/fullscreen surfaces, make Process native instead of iframe-based, and render Evolution GUI Parity stacked and large.

Consequences: some prior static expectations must change, especially overview Lab embedding and process iframe allowance. Users get clearer surfaces without another research page or duplicate Compare/History owner. Backend risk remains low because existing `/edge_ratio`, `/feature_importance`, `/variable_correlation`, and `/evolution_gui_parity` already provide most data.

## Handoff
This plan is pending approval. Recommended execution after approval: Ultragoal ledger with executor slices for Phase 1/2 Research Lab and Phase 3 Process tab. Architect review after Phase 2 if backend fields are added, and after Phase 3 if React Flow animation changes grow substantial. Team/tmux is unnecessary unless requested.
