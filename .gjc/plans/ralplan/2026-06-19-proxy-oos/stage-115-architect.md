## Summary
Stage 115 is directionally strong: it targets the remaining Condition AI dashboard gaps without adding new top-level surfaces, and it preserves the core ownership split from the deep-interview spec. It is not approval-ready as an execution plan because it omits two load-bearing implementation facts: the served frontend is the generated bundle, and several source contracts/tests still explicitly require the iframe/fullscreen behavior the plan intends to remove.

Recommendation: **REQUEST CHANGES**. Add the required bundle/build, stale-contract, and test-plan amendments before execution approval.

## Analysis
### Request and spec compliance
The reviewed artifact is `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-115-planner.md`. It covers the named remaining scope at a planning level:

- Edge Ratio / time x market-cap sizing: plans bounded responsive `_Heatmap` work in `analysis.jsx` and one merged exploration view with counts, legend, and stable states.
- Fullscreen removal: targets `rl-panel.jsx` fullscreen state/action removal.
- Condition AI home readability: moves Home toward summary/navigation cards rather than rendering full owner surfaces.
- Process tab remodel/animation: removes the `app.jsx` iframe and composes native `ProcessFlowPanel`/`ProcessFlowDiagram` with timing/log/defaults/gates.
- Research visualization/functionality: strengthens feature/correlation/combo views while keeping APIs read-only/additive.
- Evolution GUI Parity: switches `EvolutionGuiParityPanel` away from `columns={2}` to a one-column large layout.
- Original deep-interview gaps: keeps IA ownership boundaries: Lab exploration, Workbench deep analysis, History archive/ResultDetail/Compare, HOF promotion candidates.

The plan is also correctly brownfield: it avoids new top-level pages, avoids DB/runtime/protected path writes, and keeps research views advisory.

### Evidence from current source
- `analysis.jsx:264-333` currently hard-codes heatmap cell sizing with `cellW = 112`, `cellH = 46`, and `minWidth: W`, so the sizing target is real.
- `rl-panel.jsx:109-260` currently has `fullscreen` state, a fixed full-window shell style, and a visible `⛶ 전체 화면` action, so the fullscreen-removal target is concrete.
- `app.jsx:371-377` still embeds `<iframe src={baseUrl + "/process_flow"}>`, while `phase-detail.jsx:641-910` already has the native React Flow/Dagre process graph reading `current_step`, `step_timings`, and logs. Removing the iframe while preserving the native state contract is architecturally right.
- `evolution-gui-parity-panel.jsx:115` still passes `columns={2}` to `BtGuiParitySection`; the one-column lower-graph plan is grounded.
- `index.html:23-43` states the operating dashboard loads `/ui/bundle/app.js` and that `.jsx` source edits require `webui-build npm run build` to regenerate the served bundle and version pins. Stage 115 changes many `.jsx` files but does not include the bundle regeneration step or generated bundle/HTML version updates.
- `dashboard-inventory.jsx:9`, `visual-quality.jsx:8`, and `tests/unit/test_track_z_pr1_harness.py:225,285` still document/assert the process iframe. Stage 115 says to remove the iframe but does not list these contracts/tests.
- `tests/unit/test_dashboard_validation_views.py:442-443` still asserts the Research Lab fullscreen text exists. Stage 115 removes that text but does not list this test for update.
- `dashboard-pages.jsx:185-203`, `ui-contract.jsx:16,27`, and `dashboard-inventory.jsx:13` still frame Lab as wiki/context plus analysis. Stage 115 improves ownership principles but under-specifies how those product-visible labels/contracts are changed.

### Steelman antithesis
The strongest case for approving Stage 115 unchanged is that it is intentionally a focused brownfield UI plan. Avoiding bundle/build instructions and broad contract-test updates can look like reducing blast radius: executors could first make JSX source changes, update the obvious focused tests, and preserve `/process_flow` as a read-only fallback route even when no iframe is embedded. Likewise, leaving HOF under Workbench and wiki/context under Lab avoids a route churn spiral while still improving readability.

That antithesis is not strong enough here. In this dashboard, source JSX is not the served artifact; a source-only execution can pass static tests while the browser still runs stale `bundle/app.js`. Also, retaining test/doc contracts that assert the removed iframe/fullscreen behavior is not a harmless fallback; it either forces the old behavior back in or leaves the branch with known failing/static-inconsistent contracts.

### Real tradeoff tension
- **Source-only focus vs runtime truth:** avoiding `npm run build:app` is faster in a planning discussion, but runtime behavior depends on the generated bundle and HTML `?v=` pins.
- **Iframe fallback vs native process ownership:** keeping `/process_flow` as a read-only endpoint is useful historical reference, but embedding it in the Process tab preserves the duplicate surface the user asked to remodel away.
- **Home density vs owner clarity:** Home research-suite cards improve discoverability, but rendering Lab/HOF/History internals there would recreate duplicate ownership. Cards must navigate/summarize only.
- **One-column parity vs density:** stacked GUI parity charts cost vertical space, but the user request is graph readability; one-column is the right tradeoff for the Evolution parity surface.
- **Frontend-only research controls vs backend fields:** top-N/filtering can start in the client, but any controls exceeding existing payload caps must be additive backend fields, not invented client statistics.

### Synthesis
Approve the design direction after amendments: keep the focused frontend remodel, keep `/process_flow` as a read-only endpoint but remove it from Process tab embedding, keep Lab fullscreen removal scoped to `ResearchLabPanel`, and keep HOF as a navigable/workbench-owned candidate surface unless a new route is explicitly approved. Add the generated bundle/build and stale contract/test updates as required execution steps.

## Root Cause
The root planning defect is source-contract drift. Stage 115 correctly identifies the visible UX defects, but it treats the source `.jsx` files as if they are the runtime artifact and misses existing repository contracts that still encode the old iframe/fullscreen behavior. Without explicitly repairing those contracts, execution can either ship no visible UI change or fail the repository static/harness expectations.

## Findings
### HIGH - Add generated frontend bundle regeneration to the execution plan
**Reference:** `ai_strategy_loop/dashboard/frontend/index.html:23-43`; `ai_strategy_loop/dashboard/webui-build/package.json:7-12`; Stage 115 Verification section.

The plan changes many frontend source files (`app.jsx`, `analysis.jsx`, `rl-panel.jsx`, `phase-detail.jsx`, `evolution-gui-parity-panel.jsx`, `bt-gui-parity.jsx`, `styles.css`) but does not require regenerating the served bundle. The runtime HTML explicitly loads `/ui/bundle/app.js` and comments that source `.jsx` edits require the webui build. If execution follows the plan verification as written, the dashboard can keep serving stale behavior: iframe still embedded, Lab fullscreen still present, and GUI parity still two-column.

**Impact:** high correctness risk; implemented source changes may not reach users.

**Required fix:** Add `ai_strategy_loop/dashboard/frontend/bundle/app.js` and the HTML version-pin/manifest outputs generated by `npm run build:app` to the file-level/verification plan, or explicitly require the approved executor to run `npm run build:app` from `ai_strategy_loop/dashboard/webui-build` after source edits. This is not a gate or formatter; it is the served artifact generation step.

### MEDIUM - Update stale iframe contracts and tests alongside Process tab removal
**Reference:** `app.jsx:371-377`; `dashboard-inventory.jsx:9`; `visual-quality.jsx:8`; `tests/unit/test_track_z_pr1_harness.py:225,285`; `phase-detail.jsx:641-910`.

Stage 115 correctly removes the Process iframe from `app.jsx`, but it only lists `app.jsx`, `phase-detail.jsx`, `styles.css`, and a few process tests. The repository still has product-visible inventory/visual-quality text and a Track Z harness unit test that assert iframe presence.

**Impact:** implementation will either fail existing tests or leave product-visible contracts saying the removed iframe is still the process surface.

**Required fix:** Add `dashboard-inventory.jsx`, `visual-quality.jsx`, and `tests/unit/test_track_z_pr1_harness.py` to the plan. The new contract should say the Process tab is native (`ProcessFlowPanel`/`ProcessFlowDiagram`, timing grid, logs, defaults/gates), while `/process_flow` remains a read-only reference endpoint only if kept.

### MEDIUM - Update the fullscreen test contract and clarify scope
**Reference:** `rl-panel.jsx:109-260`; `tests/unit/test_dashboard_validation_views.py:442-443`; `bt-result-area.jsx:49-63,268-339`.

The plan removes Research Lab fullscreen but does not include the test that currently asserts the Korean fullscreen label exists. It also does not explicitly state whether fullscreen removal is limited to Research Lab. There is another fullscreen path in `BtResultArea`; leaving it may be correct, but the plan should make that boundary explicit to avoid accidental over-removal.

**Impact:** focused execution can fail static tests or remove unrelated backtest analysis behavior.

**Required fix:** Add `tests/unit/test_dashboard_validation_views.py` to the affected tests and update it to assert absence of Lab fullscreen while preserving `opsStrip` and validation contracts. Add an acceptance note: fullscreen removal is scoped to `ResearchLabPanel` unless the user separately asks to remove `BtResultArea` fullscreen analysis.

### MEDIUM - Tighten Home/HOF/Lab ownership text and card targets
**Reference:** `ui-contract.jsx:16,27`; `dashboard-pages.jsx:185-203`; `dashboard-inventory.jsx:13`; `app.jsx:769-778`.

The plan says Home will expose cards for Research Lab, History, Workbench, HOF, Backtest, and Chart Replay, but the current route contract has no HOF subtab key and Lab still includes wiki/context as owner language. The plan principle says Lab owns exploration/edge/variables/correlation/combos/validation, which is cleaner than the current product text, but the file list only mentions `ui-contract.jsx` as text-only and does not cover `dashboard-pages.jsx`, `dashboard-inventory.jsx`, or `visual-quality.jsx` for the same product-visible labels.

**Impact:** Home may remain a “리서치 Wiki” entry point, HOF may be linked through an undefined route, or Lab may continue owning wiki/context in a way that violates the stated IA principle.

**Required fix:** Define exact card targets: e.g. HOF card navigates to Workbench/HOF section or existing overview HOF panel, not a new route; Lab card navigates to Research Lab analysis, while wiki/context are secondary details or links. Add `dashboard-pages.jsx`, `dashboard-inventory.jsx`, and `visual-quality.jsx` to the Home/IA text update scope.

### LOW - Specify normalized/canonical heatmap axes for sparse cross data
**Reference:** `analysis.jsx:107-130,264-333`; `ai_strategy_loop/fitness/edge_ratio.py:198-202`.

Stage 115 calls for bounded responsive sizing, which is necessary, but the current heatmap builds row/column labels only from `segments.cross`. For sparse data, this can drop time or market-cap labels that exist in `segments.time`/`segments.market_cap` but not in cross cells. The user phrasing includes “normalized merged Edge Ratio/time x market-cap panel sizing,” so the plan should specify canonical axis derivation and sparse-cell behavior, not only CSS sizing.

**Impact:** lower-severity product/data readability issue; sparse runs can still show a misleading incomplete grid.

**Required fix:** Require `_Heatmap` to derive ordered axes from `segments.time` and `segments.market_cap` when available, fill missing cross cells honestly, clamp cell min/max dimensions, preserve counts/tooltips, and keep a legend/scale explanation.

## Recommendations
1. Amend Stage 115 before approval with the bundle/build requirement, generated served-artifact outputs, and a runtime QA note that checks the rebuilt `/ui/bundle/app.js` behavior.
2. Add missing contract/test files: `dashboard-inventory.jsx`, `visual-quality.jsx`, `tests/unit/test_track_z_pr1_harness.py`, and `tests/unit/test_dashboard_validation_views.py`.
3. Clarify product routing for the Home Research Suite, especially HOF card targeting and Lab vs wiki/context ownership.
4. Tighten heatmap acceptance around canonical axes and sparse cells.
5. Keep the rest of the sequencing: Lab/heatmap cleanup first, research views second, Process native remodel third, Home cards fourth, Evolution GUI Parity one-column fifth.

## Architectural Status
BLOCK

## Code Review Recommendation
REQUEST CHANGES

## Trade-offs
| Option | Strength | Weakness | Verdict |
|---|---|---|---|
| Stage 115 as written | Good UX direction, low backend blast radius, respects owner boundaries | Misses served bundle/build and stale contracts/tests | Not approval-ready |
| Amend focused plan | Keeps the same architecture while adding runtime truth and contract repair | Slightly broader file/test list | Recommended |
| Keep iframe as fallback in Process tab | Preserves prior harness expectations | Violates requested native remodel and duplicate-surface cleanup | Reject for tab UI; keep endpoint only |
| Remove all fullscreen actions globally | Simple product rule | Risks unrelated Backtest result analysis regression | Reject unless separately scoped; remove Lab fullscreen now |
| New HOF route/card | Direct Home navigation | Adds route surface contrary to stable route-key constraint | Prefer deep-link/anchor to existing Workbench or overview HOF |
