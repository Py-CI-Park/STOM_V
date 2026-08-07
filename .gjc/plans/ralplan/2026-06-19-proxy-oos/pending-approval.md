# Pending Approval Plan: Condition AI Dashboard Remaining Parity Closure

Status: **pending approval**. This is a RALPLAN consensus artifact only. No product source, tests, builds, formatters, protected runtime paths, commits, or pushes were changed by this planning pass.

## Source Artifacts
- Deep Interview spec: `.gjc/specs/deep-interview-condition-ai-dashboard-strengthening.md`
- Previous approved execution plan: `.gjc/plans/ralplan/2026-06-19-proxy-oos/pending-approval.md`
- Planner stage: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-115-planner.md`
- Architect pass 1: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-115-architect.md` — BLOCK / REQUEST CHANGES
- Planner revision 1: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-117-revision.md`
- Architect pass 2: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-117-architect.md` — CLEAR / APPROVE
- Critic pass 1: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-117-critic.md` — ITERATE
- Planner revision 2: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-118-revision.md`
- Architect pass 3: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-118-architect.md` — CLEAR / APPROVE
- Critic pass 2: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-118-critic.md` — OKAY
- Persisted Planner id: `119-DashboardParityPlanner`

## Objective
Bring the remaining Condition AI dashboard parity work to 100% against the user's original dashboard-strengthening brief: research surfaces must be readable from Condition AI Home without duplicate ownership, Edge Ratio and time×market-cap exploration must be a single bounded/internally consistent view, Process must become a native animated workflow page, Research Lab analysis views must be more useful, Lab fullscreen must be removed, and Evolution GUI Parity lower graphs must render as larger one-column charts.

## RALPLAN-DR Summary

### Principles
1. **100% closure for listed parity asks**: no listed remaining item may be demoted to advisory-only work or hidden as a future deferral.
2. **Served runtime truth**: JSX/CSS source edits are incomplete until served bundles and cache/version pins are regenerated and verified.
3. **One owner per surface**: Lab owns exploration/edge/variables/correlation/combos/validation; History owns ResultDetail/Compare/archive; Workbench owns deep analysis; HOF owns promotion candidates; Home summarizes/navigates only.
4. **Bounded visual density**: heatmaps and graphs must use consistent cell/card sizing, legends, counts, and responsive bounds before adding more content.
5. **Motion reflects evidence**: Process animations must reflect real current-step/timing/log state and respect reduced-motion.

### Decision Drivers
1. Current edge/heatmap merge technically exists, but sizing is oversized/inconsistent and must become a designed integrated analysis surface.
2. The Process page still has stale iframe/runtime-contract risk and must become a native, testable dashboard view.
3. The browser serves generated JS/CSS assets, so bundle and stylesheet cache pins are first-class deliverables, not optional build hygiene.

### Options Considered
| Option | Pros | Cons | Verdict |
|---|---|---|---|
| A. Focused brownfield frontend closure with served-runtime regeneration | Lowest blast radius, preserves existing routes and ownership boundaries, directly targets user-visible gaps | Requires contract/test updates across source, bundle, and static inventory | **Chosen** |
| B. New Research mega-page | Could visually unify everything quickly | Reintroduces duplicate Lab/Workbench/History ownership and breaks prior IA decisions | Rejected |
| C. Backend analytics redesign first | Cleaner long-term data model | Over-scoped, DB/runtime risk, unnecessary for current visualization parity | Rejected |
| D. Keep iframe/fullscreen fallbacks | Reduces old-test churn | Violates user request and leaves stale UI artifacts | Rejected |

## ADR

### Decision
Use a focused brownfield frontend closure plan with optional additive analysis-only backend fields. Do not create new routes or duplicate owners. Regenerate served JS/CSS runtime artifacts after approved source edits and verify cache pins for every served HTML entry.

### Why Chosen
The prior Ultragoal implementation already recovered result identity/detail/history foundations. Remaining gaps are UI/IA/visualization/runtime-serving mismatches. Focused closure minimizes risk while satisfying the exact user complaints.

### Consequences
- File/test scope expands to include served bundle and static contract artifacts.
- Home must become a readable research-suite gateway, not a full duplicate Lab.
- Lab fullscreen removal is scoped only to ResearchLabPanel; Backtest result fullscreen remains.
- CSS changes require stylesheet cache/version pin verification, not just source tests.

### Follow-ups
None of the listed remaining parity items may be deferred. Future-only work is limited to unrelated large backend research redesigns, live brokerage, V3K, and production export flows.

## Implementation Plan

### Phase 0 — Runtime and stale-contract preflight
**Goal:** Prevent source/runtime drift and old contracts from forcing regressions.

**Files/surfaces**
- `ai_strategy_loop/dashboard/frontend/index.html`
- `ai_strategy_loop/dashboard/frontend/lab.html`
- `ai_strategy_loop/dashboard/frontend/pro.html`
- `ai_strategy_loop/dashboard/frontend/verdict.html`
- `ai_strategy_loop/dashboard/frontend/STOM AI Dashboard.html`
- `ai_strategy_loop/dashboard/frontend/dashboard-inventory.jsx`
- `ai_strategy_loop/dashboard/frontend/visual-quality.jsx`
- `tests/unit/dashboard/test_track_z_pr1_harness.py`
- `tests/unit/dashboard/test_p14_build_harness.py`

**Required contract**
- Any JS source change requires served JS bundle/version-pin regeneration.
- Any `styles.css` change requires `/ui/styles.css?v=...` or equivalent cache-busting update in all five served HTML entries.
- Process contracts must describe the native Process page, not an embedded iframe.
- `/process_flow` may remain only as read-only reference evidence, not the primary Process tab body.

**Acceptance**
- Static contracts no longer require process iframe or Lab fullscreen.
- Served runtime freshness checks cover both JS and CSS.

### Phase 1 — Research Lab ownership cleanup and bounded Edge/heatmap integration
**Goal:** Fix the currently oversized/inconsistent merged heatmap while preserving one integrated Edge Ratio + time×market-cap exploration view.

**Files/surfaces**
- `ai_strategy_loop/dashboard/frontend/analysis.jsx`
- `ai_strategy_loop/dashboard/frontend/rl-panel.jsx`
- `ai_strategy_loop/dashboard/frontend/styles.css`
- `tests/unit/test_dashboard_research_lab_frontend.py`
- `tests/unit/test_dashboard_validation_views.py`

**Required contract**
- Remove ResearchLabPanel `fullscreen` state, fixed fullscreen shell style, and fullscreen button.
- Do **not** remove Backtest/BtResultArea fullscreen behavior.
- Edge/heatmap panel remains a single owner and single integrated view.
- Heatmap derives canonical axes from `segments.time` and `segments.market_cap` when available; sparse cross cells render honestly as blanks, not fabricated values.
- Cells use clamped responsive sizing, consistent typography, legend, count/tooltips, and controlled horizontal scroll only when needed.

**Acceptance**
- No Lab fullscreen user action exists.
- Edge/time×market-cap heatmap is readable in Condition AI Home and Lab without dominating the page.
- Stats, heatmap cells, and segment bars use consistent visual scale.

### Phase 2 — Research visualization/functionality strengthening
**Goal:** Make exploration heatmap, variable importance, correlation, and variable-combination views analytically useful, not merely present.

**Files/surfaces**
- `ai_strategy_loop/dashboard/frontend/analysis.jsx`
- `ai_strategy_loop/dashboard/frontend/rl-analysis.jsx`
- Optional additive-only backend: `ai_strategy_loop/dashboard/app.py`, `ai_strategy_loop/fitness/correlation.py`

**Required contract**
- Variable importance: top-N controls, segment counts, selected segment, show-more, Cohen's d legend, low-sample warnings.
- Correlation: sorted/filterable rows, matrix/list toggle if needed, top-N cap, sample counts, method/axis/run context, honest insufficient-data states.
- Variable combinations: selected-pair detail, score/explanation when available, no invented statistics when payload lacks fields.
- All outputs remain advisory; HOF/final approval authority remains separate.

**Acceptance**
- Each research subview shows context, legend, sample/count information, and honest empty/error/loading states.
- No research panel implies automatic promotion/export authority.

### Phase 3 — Native Process tab remodel and animation
**Goal:** Replace stale iframe-style Process page with a native, animated, auditable workflow view.

**Files/surfaces**
- `ai_strategy_loop/dashboard/frontend/app.jsx`
- `ai_strategy_loop/dashboard/frontend/phase-detail.jsx`
- `ai_strategy_loop/dashboard/frontend/styles.css`
- `ai_strategy_loop/dashboard/frontend/dashboard-inventory.jsx`
- `ai_strategy_loop/dashboard/frontend/visual-quality.jsx`
- `tests/unit/dashboard/test_p11_process_flow.py`
- `tests/unit/test_process_timing.py`
- `tests/unit/dashboard/test_track_z_pr1_harness.py`

**Required contract**
- Remove embedded process iframe from `app.jsx` Process route.
- Compose native Process page from `ProcessFlowPanel`/diagram, current status cards, timing grid, phase logs, defaults/gates table, and explanatory notes.
- Add active node pulse, completed-path glow, current-edge motion, idle/complete freeze, and `prefers-reduced-motion` fallback.
- Preserve `current_step`, `step_timings`, phase timers, logs, and existing process route keys.

**Acceptance**
- Process tab is self-contained and native.
- Animation improves understanding without requiring motion for accessibility.
- Static and timing tests cover the native contract.

### Phase 4 — Condition AI Home research-suite readability
**Goal:** Make Home clearly expose the research suite without duplicating Lab/History/Workbench/HOF ownership.

**Files/surfaces**
- `ai_strategy_loop/dashboard/frontend/app.jsx`
- `ai_strategy_loop/dashboard/frontend/dashboard-pages.jsx`
- `ai_strategy_loop/dashboard/frontend/ui-contract.jsx`
- `ai_strategy_loop/dashboard/frontend/dashboard-inventory.jsx`
- `ai_strategy_loop/dashboard/frontend/styles.css`

**Required contract**
- Home first screen remains: process progress → live/current generation/current strategy → settings/gates/engine summary.
- Add readable Research Suite cards/anchors for Lab, History, Workbench, HOF, Backtest, and Chart Replay.
- Home cards summarize/navigate only; they must not render full ResultDetail, Compare, Workbench internals, or duplicate Lab owners.
- HOF target must use an existing HOF section/anchor, not a new top-level route.

**Acceptance**
- User can find research capabilities from Condition AI Home.
- Ownership stays single-source and no duplicate surfaces reappear.

### Phase 5 — Evolution GUI Parity one-column large graph mode
**Goal:** Make lower GUI parity graphs larger and readable by stacking them in one column.

**Files/surfaces**
- `ai_strategy_loop/dashboard/frontend/evolution-gui-parity-panel.jsx`
- `ai_strategy_loop/dashboard/frontend/bt-gui-parity.jsx`
- `ai_strategy_loop/dashboard/frontend/styles.css`
- `tests/unit/dashboard/test_evolution_gui_parity.py`
- `tests/unit/test_dashboard_backtest_detail.py` if shared parity rendering changes affect Backtest detail

**Required contract**
- Evolution GUI Parity must not pass `columns={2}` for lower graphs.
- `BtGuiParitySection` must support explicit one-column large mode while preserving BacktestTab's existing behavior.

**Acceptance**
- Evolution GUI Parity charts render as larger stacked one-column graphs.
- Backtest result GUI parity remains stable.

### Phase 6 — Served runtime generation and verification
**Goal:** Ensure the browser at `http://127.0.0.1:8770` serves the approved source changes.

**Files/surfaces**
- `ai_strategy_loop/dashboard/frontend/bundle/app.js`
- `ai_strategy_loop/dashboard/frontend/bundle/stom-ui.js` if changed by build
- HTML version/cache pins listed in Phase 0

**Required contract**
- Run `npm run build:app` from `ai_strategy_loop/dashboard/webui-build` after source edits; if unavailable, use project-equivalent `npm run build`.
- Verify JS app version and CSS cache/version pins changed when their sources changed.

**Acceptance**
- Browser-served runtime reflects source code and CSS changes.

## Verification Plan
Planning ran no tests/builds/formatters/gates. Approved execution must run focused verification after implementation:

```powershell
pytest tests/unit/dashboard/test_dashboard_ui_remodel.py tests/unit/test_dashboard_research_lab_frontend.py tests/unit/dashboard/test_p11_process_flow.py tests/unit/test_process_timing.py tests/unit/dashboard/test_track_z_pr1_harness.py tests/unit/test_dashboard_validation_views.py tests/unit/dashboard/test_research_records_frontend.py tests/unit/dashboard/test_evolution_gui_parity.py tests/unit/dashboard/test_p14_build_harness.py -q
```

If additive backend analysis fields are added:

```powershell
pytest tests/unit/test_analysis_gen_filter.py tests/unit/dashboard/test_backtest_report.py tests/unit/test_dashboard_research_lab_frontend.py -q
```

If shared GUI parity rendering changes Backtest detail:

```powershell
pytest tests/unit/test_dashboard_backtest_detail.py tests/unit/dashboard/test_research_records_frontend.py -q
```

Served runtime generation after approved source edits:

```powershell
cd ai_strategy_loop/dashboard/webui-build
npm run build:app
```

Fallback only if `build:app` is unavailable:

```powershell
cd ai_strategy_loop/dashboard/webui-build
npm run build
```

Manual QA after approved execution:
- `http://127.0.0.1:8770/ui/evolution`
- `http://127.0.0.1:8770/ui/evolution/lab`
- `http://127.0.0.1:8770/ui/evolution/process`
- `http://127.0.0.1:8770/ui/evolution/workbench`
- an Evolution GUI Parity generation detail

Confirm: no Lab fullscreen; bounded integrated heatmap; strengthened variable/correlation/combo views; native animated Process page; readable Home research cards; large one-column GUI parity graphs; no duplicate History/Compare/Workbench/Lab owner surfaces.

## Risks and Mitigations
| Risk | Mitigation |
|---|---|
| Source edits not served | Mandatory JS bundle and CSS cache/version pin generation + P14/static verification |
| Heatmap becomes too small after bounding | Clamp min/max cells and provide scroll only when data volume requires it |
| Home cards become duplicate owners | Cards navigate/summarize only; tests reject ResultDetail/Compare/full Lab/Workbench internals on Home |
| Process animation hurts performance/accessibility | Animate active path only, freeze idle/complete, respect `prefers-reduced-motion` |
| Variable-combo UI fabricates insight | Render selected-pair detail only from payload fields; honest insufficient-data state otherwise |
| Fullscreen removal regresses Backtest result detail | Scope removal to ResearchLabPanel only; keep BtResultArea fullscreen tests stable |
| Protected paths mutate | No `_database`, `_log`, `.db`, `backtest/graph`, or V3K settings writes; fixtures use temp paths only |

## Execution Handoff Shape
- Recommended execution path after approval: Ultragoal, not Team, because the phases are sequential but can use bounded executor slices inside the Ultragoal leader.
- Phase order is mandatory: Phase 0 → 1 → 2 → 3 → 4 → 5 → 6.
- Run architect review after Phase 3 if Process animation or React Flow changes grow beyond the planned surface.
- Run architect review after Phase 2 if backend analysis fields are added.

## Approval Boundary
This plan is **pending approval**. Execution requires a separate explicit approval path. Do not mutate product source from this RALPLAN planning artifact.
