# Pending Approval RALPLAN Revision: Remaining Condition AI Dashboard Parity Gaps

Status: **pending approval**. Revision after architect BLOCK. Includes served bundle regeneration, stale process iframe contract/test updates, Research Lab fullscreen test-contract update, scoped fullscreen removal, and all prior remaining user scope. Planning-only: no product source edits, tests, builds, formatters, protected runtime path mutations, commits, or pushes were performed.

## Required Amendments Incorporated
1. **Served runtime generation**: approved execution must regenerate the served frontend bundle because `frontend/index.html` loads `/ui/bundle/app.js` and version-pinned assets, not raw `.jsx`. After source edits, run `npm run build:app` from `ai_strategy_loop/dashboard/webui-build`; if unavailable, run project-equivalent `npm run build`. Include generated `frontend/bundle/app.js`, changed `bundle/stom-ui.js` if any, and updated `index.html` or equivalent asset version pins.
2. **Stale Process iframe contracts**: add `dashboard-inventory.jsx`, `visual-quality.jsx`, and `tests/unit/dashboard/test_track_z_pr1_harness.py` to scope. Update them from iframe-required contracts to native Process tab contracts: `ProcessFlowPanel`/`ProcessFlowDiagram`, live strip, timing grid, logs, defaults/gates, and read-only `/process_flow` reference endpoint only.
3. **Research Lab fullscreen contract**: add `tests/unit/test_dashboard_validation_views.py`. Replace the current fullscreen-exists assertion with ResearchLabPanel-fullscreen-absent while preserving `opsStrip`, validation, equity, and route contracts.
4. **Fullscreen removal scope**: removal is scoped to `ai_strategy_loop/dashboard/frontend/rl-panel.jsx` / `ResearchLabPanel`. Do not remove `BtResultArea` fullscreen analysis unless separately requested.
5. **Previous constraints preserved**: no duplicate History/Compare/Workbench/Research Lab surfaces, additive `/bt/result` only if touched, render-only chart replay if touched, wt-dev, STOM 2U_C nonrelease, protected runtime paths untouched, pending approval.

## RALPLAN-DR Summary
### Principles
- Runtime truth over source-only truth: source JSX edits are incomplete until bundle and version pins are regenerated.
- One owner per surface: Lab owns exploration/edge/variables/correlation/combos/validation; History owns ResultDetail/Compare/archive; Workbench owns deep analysis; HOF owns promotion candidates; Home links and summarizes only.
- Contract repair with behavior removal: removing iframe/fullscreen behavior requires updating product-visible inventory and static/harness tests.
- Process motion reflects state evidence, preserving `current_step`, `step_timings`, timers, and logs.
- Scoped removal avoids unrelated regression: Lab fullscreen is removed, Backtest result fullscreen remains.

### Top Drivers
- Architect BLOCK found source-runtime drift: browser serves generated bundle, not edited JSX.
- Existing contracts still assert process iframe and Lab fullscreen.
- User still requires remaining parity: bounded edge heatmap, Process remodel/animation, research visualizations, no Research Lab fullscreen, readable Home research suite, Evolution GUI Parity one-column larger graphs.

### Options
| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Amend stage 115 with bundle and stale-contract repair | Fixes BLOCK while keeping focused brownfield scope | Broader file/test list | **Chosen** |
| Keep stage 115 unchanged | Shorter | Can serve stale runtime and fail old tests | Rejected |
| Keep iframe/fullscreen fallbacks | Preserves old tests | Violates requested remodel/removal | Rejected |
| Remove all fullscreen globally | Simple | Risks Backtest analysis regression | Rejected |

## File-Level Plan
- `analysis.jsx`: bound `_Heatmap`; derive canonical axes from `segments.time` and `segments.market_cap` when present; fill missing cross cells honestly; preserve counts/tooltips and legend.
- `rl-panel.jsx`: remove Research Lab fullscreen state/style/button only; preserve `opsStrip`, validation tabs, and SPA workbench navigation.
- `rl-analysis.jsx`: strengthen variable importance, correlation, and combo visuals with top-N, sorting/filtering, legends, selected-pair detail, and low-sample warnings.
- `phase-detail.jsx`: native process graph/cards/timing/log/defaults and stronger animation with reduced-motion.
- `app.jsx`: remove embedded process iframe; add Home Research Suite cards; keep Home navigation/summary only.
- `evolution-gui-parity-panel.jsx`: use one-column large `BtGuiParitySection`, not `columns={2}`.
- `bt-gui-parity.jsx`: make one-column mode explicit and preserve Backtest usage.
- `styles.css`: bounded heatmap, process animation/reduced-motion, Lab controls, Home cards, GUI parity one-column styles.
- `dashboard-pages.jsx`, `ui-contract.jsx`, `dashboard-inventory.jsx`, `visual-quality.jsx`: update Lab/Home/HOF/Process product text and owner contracts; no new routes.
- Served outputs after approved source edits: `frontend/bundle/app.js`, changed `bundle/stom-ui.js` if any, and `index.html`/manifest version pins.
- Optional backend only if needed: additive analysis-only fields in `app.py` / `fitness/correlation.py`; no writes or scorer/gate/export coupling.

## Sequencing
1. **Phase 0 runtime and stale-contract preflight**: add bundle-generation requirement; update scope for `dashboard-inventory.jsx`, `visual-quality.jsx`, Track Z harness, and validation-view tests.
2. **Phase 1 Lab and heatmap**: remove Lab fullscreen only; preserve `BtResultArea` fullscreen; bound heatmap; canonical sparse axes; tests.
3. **Phase 2 research visualizations**: strengthen edge, feature importance, correlation, combos, validation with honest advisory-only states.
4. **Phase 3 Process tab**: remove app iframe; native process page; update inventory/visual-quality/harness; reduced-motion animation.
5. **Phase 4 Home**: Research Suite cards target existing routes/sections: Lab `/ui/evolution/lab`, History `/ui/evolution/records`, Workbench `/ui/evolution/workbench`, HOF existing Workbench/HOF section or overview anchor, Backtest `/ui/backtest`, Chart Replay `/ui/chart-replay`.
6. **Phase 5 Evolution GUI Parity**: one-column larger stacked charts.
7. **Phase 6 served bundle**: run `npm run build:app` or `npm run build`; include generated bundle/version-pin outputs.

## Acceptance Criteria
- Served dashboard runtime reflects source changes via regenerated bundle and version pins.
- No process iframe in `app.jsx`; `/process_flow` is read-only reference only if retained.
- `dashboard-inventory.jsx`, `visual-quality.jsx`, and Track Z harness no longer require embedded iframe.
- ResearchLabPanel has no fullscreen toggle/style/action; `BtResultArea` fullscreen remains.
- `tests/unit/test_dashboard_validation_views.py` asserts Lab fullscreen absence while preserving ops/validation contracts.
- Edge/time x market-cap heatmap is bounded, uses canonical axes, fills sparse cells honestly, and shows counts/tooltips/legend.
- Home Research Suite is readable and navigation-only; no new HOF route and no duplicate owner surfaces.
- Evolution GUI Parity no longer passes `columns={2}`.
- Existing route keys remain stable; `/bt/result` remains additive only if touched; chart replay remains render-only if touched; protected paths untouched.

## Verification Plan
Planning ran no tests/builds/formatters/gates. Approved execution must run served artifact generation, not as a formatter/gate but as required runtime output:

```powershell
cd ai_strategy_loop/dashboard/webui-build
npm run build:app
```

Fallback if unavailable:

```powershell
cd ai_strategy_loop/dashboard/webui-build
npm run build
```

Focused verification after approved implementation:

```powershell
pytest tests/unit/dashboard/test_dashboard_ui_remodel.py tests/unit/test_dashboard_research_lab_frontend.py tests/unit/dashboard/test_p11_process_flow.py tests/unit/test_process_timing.py tests/unit/dashboard/test_track_z_pr1_harness.py tests/unit/test_dashboard_validation_views.py tests/unit/dashboard/test_research_records_frontend.py tests/unit/dashboard/test_evolution_gui_parity.py tests/unit/dashboard/test_p14_build_harness.py -q
```

Add backend-focused tests only if additive backend analysis fields are added.

## Risks and Mitigations
| Risk | Mitigation |
|---|---|
| Source edits not served | Mandatory bundle build and version-pin outputs |
| Old tests force iframe/fullscreen back | Update inventory, visual-quality, Track Z, validation tests |
| Lab fullscreen removal breaks Backtest | Scope removal to ResearchLabPanel only |
| Sparse heatmap misleads | Canonical axes and honest blanks |
| HOF card adds route | Target existing section/anchor only |
| Protected paths mutate | No runtime DB/log/graph writes; tmp_path fixtures only |

## ADR
Decision: amend the focused brownfield plan to add served-runtime generation, stale-contract repairs, scoped fullscreen removal, exact Home card targets, and canonical heatmap axes. Consequence: file/test scope is broader, but execution can satisfy the architect BLOCK and user scope without new routes or duplicate owners.

## Handoff
Pending approval. Recommended execution after approval: Ultragoal ledger with bounded executor slices; architect review after Process remodel or any backend field addition.
