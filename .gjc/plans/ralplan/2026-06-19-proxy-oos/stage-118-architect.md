## Summary
Stage 118 resolves the prior architect and critic blockers at planning level: it makes JS and CSS served artifacts first-class deliverables, names all five stylesheet-linked HTML entries, requires P14/equivalent CSS freshness verification, preserves stale-contract repairs, and explicitly commits to 100% closure of the remaining parity asks. Architecture, product, and code-contract statuses are CLEAR for pending-approval execution; recommendation is APPROVE with no blockers.

## Analysis
Reviewed artifact: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-118-revision.md`. Planning-only review; no tests, builds, formatters, product-source edits, commits, pushes, or protected runtime mutations were performed.

### Status matrix
- Architecture status: CLEAR — Stage 118 keeps one-owner-per-surface boundaries (`stage-118-revision.md:16-18`), uses existing routes/sections for Home cards (`stage-118-revision.md:53`), and preserves no-new-route/no-duplicate-owner constraints (`stage-118-revision.md:12,67,69`).
- Product status: CLEAR — The top-level commitment forbids deferring any remaining parity ask (`stage-118-revision.md:6`) and the acceptance criteria restate full closure (`stage-118-revision.md:58`).
- Code/contract status: CLEAR — The plan now treats served JS bundle pins and CSS stylesheet pins as runtime deliverables (`stage-118-revision.md:43,45,55,59-61,92`) and keeps stale Process/Lab contract-test updates in scope (`stage-118-revision.md:62-65`).

### Prior issue closure
- Critic issue 1, stylesheet cache-busting, is resolved. The critic required explicit CSS pin updates for `index.html`, `lab.html`, `pro.html`, `verdict.html`, and `STOM AI Dashboard.html` (`stage-117-critic.md:21-23`). Stage 118 adds the criterion in the critic amendments, file-level plan, acceptance criteria, verification plan, and risk table (`stage-118-revision.md:9-10,43,59-60,92,97`). Current repository inspection confirms those five entries all link `/ui/styles.css?v=20260620g004` (`frontend/index.html:12`, `lab.html:12`, `pro.html:12`, `verdict.html:8`, `STOM AI Dashboard.html:12`).
- Critic issue 2, P14/equivalent CSS freshness verification, is resolved at plan level. Stage 118 requires `tests/unit/dashboard/test_p14_build_harness.py` or an equivalent static/source check, plus post-build inspection proving the stylesheet pin changed when `styles.css` changed (`stage-118-revision.md:10,46,60,92`). This is the right harness family: current P14 already checks committed bundle/runtime freshness for `stom-ui.js`, `app.js`, manifest, and HTML pins (`test_p14_build_harness.py:71-93,162-195`), but its existing content-hash check is JS-focused (`test_p14_build_harness.py:174-195`), so extending it for stylesheet freshness is concrete and non-speculative.
- Critic issue 3, top-level 100% closure, is resolved. Stage 118 adds the explicit non-deferral commitment for heatmap sizing, native Process remodel/animation, research visual strengthening/functionality, ResearchLab fullscreen removal, Home readability/suite exposure, and Evolution GUI Parity one-column graphs (`stage-118-revision.md:6,58`).
- Prior architect issue, served JS bundle regeneration/version pins, remains resolved. Stage 118 preserves the requirement (`stage-118-revision.md:11`), lists served outputs (`stage-118-revision.md:45`), and requires `npm run build:app`/`npm run build` as runtime artifact generation rather than a gate (`stage-118-revision.md:55,73-82`). Repository evidence supports this: `webui-build/package.json:9,11` exposes those scripts, and `build-app.mjs:76-118` writes `app.js`/`stom-ui.js` hashes into all five HTML entries and manifest metadata.
- Prior architect issue, stale Process iframe contracts/tests, remains resolved. Current source still has an embedded `/process_flow` iframe in `app.jsx:372-377`, inventory/visual-quality still mention iframe evidence (`dashboard-inventory.jsx:9`, `visual-quality.jsx:8`), and Track Z still asserts `iframePresent` (`test_track_z_pr1_harness.py:225-226,285`). Stage 118 explicitly requires removing the iframe, keeping `/process_flow` read-only only if retained, and updating inventory/visual-quality/Track Z to native contracts (`stage-118-revision.md:39,52,62-63,99`).
- Prior architect issue, scoped ResearchLab fullscreen removal, remains resolved. Current `ResearchLabPanel` still contains fullscreen state/style/action (`rl-panel.jsx:108-110,218-260`), the validation test still asserts `전체 화면` (`test_dashboard_validation_views.py:442-443`), and `BtResultArea` has a separate fullscreen analysis path (`bt-result-area.jsx:49-63,269-334`). Stage 118 scopes removal to ResearchLabPanel, preserves `BtResultArea`, and requires the validation test to assert absence while preserving ops/validation contracts (`stage-118-revision.md:37,50,64-65,100`).
- Remaining parity asks are concretely represented. Heatmap work names canonical axes, sparse blanks, counts/tooltips/legend (`stage-118-revision.md:34,66`) and is grounded in current fixed cell sizing at `analysis.jsx:264-316`. Evolution GUI Parity removal of `columns={2}` is explicit (`stage-118-revision.md:40,68`) and grounded in current `evolution-gui-parity-panel.jsx:115` plus `bt-gui-parity.jsx:535-538`. Home/HOF route discipline is explicit (`stage-118-revision.md:53,67`) and grounded in current Home/Lab/Workbench labels at `app.jsx:775-778` and `ui-contract.jsx:16-18,27-29`.

### Steelman antithesis
The strongest case against approval is that Stage 118 still relies on execution discipline for CSS freshness: `build-app.mjs` updates JS bundle pins, not `/ui/styles.css?v=...` (`build-app.mjs:88-109`), so an executor could update source CSS and the JS bundle while forgetting the stylesheet query string. A stricter plan could require automating CSS hash injection inside `build-app.mjs` rather than allowing an equivalent static check and post-build inspection.

That objection is not strong enough to block this planning artifact. The critic asked for an explicit served-style acceptance criterion and concrete verification; Stage 118 does both, names every affected HTML entry, names the P14/equivalent verification location, and requires proof that the stylesheet pin changes when `styles.css` changes (`stage-118-revision.md:9-10,43,59-60,92`). For planning approval, this is actionable without guessing; whether execution implements CSS hashing in `build-app.mjs` or a static/diff check is an implementation tradeoff.

### Tradeoff tension
- Automated CSS hashing vs bounded plan scope: extending `build-app.mjs` would reduce manual risk but broadens build-tool mutation; Stage 118 accepts either a pin update plus P14/static proof or equivalent cache-busting, which is sufficient for planning.
- Runtime truth vs diff size: generated bundle and HTML pins expand the implementation diff, but they are the deployed UI contract.
- Native Process tab vs reference endpoint: retaining `/process_flow` only as read-only reference preserves historical access without keeping the duplicate iframe owner in the tab.
- Scoped fullscreen removal vs global simplification: removing only ResearchLabPanel avoids an unrelated Backtest result fullscreen regression.
- Home discoverability vs duplicate ownership: Research Suite cards improve navigation only because the plan keeps Home summary/link-only and uses existing routes/sections.
- One-column parity vs density: larger stacked graphs cost vertical space but directly address readability.

### Synthesis
Stage 118 is the right synthesis: keep the brownfield dashboard topology stable, remove stale behaviors with their contracts/tests, and treat every served runtime artifact touched by source changes as part of the deliverable. The remaining execution watch is not architectural uncertainty; it is a concrete acceptance item for the implementation review.

## Root Cause
The root defect in earlier stages was served-runtime/source-contract drift: plans could edit `.jsx`/`styles.css` while the browser kept serving generated JS and version-pinned CSS, and stale iframe/fullscreen tests could force removed behavior back. Stage 118 repairs that by making both JS and CSS runtime pins, stale contract updates, and non-deferral of all parity asks explicit acceptance criteria.

## Findings
### Resolved HIGH — Require both JS and CSS served-runtime freshness
Reference: `stage-118-revision.md:9-10,43,45,55,59-61,92`; `frontend/*.html` stylesheet pins; `build-app.mjs:76-118`; `package.json:9,11`.

Impact: Without this, users can receive stale dashboard visuals even after source changes. Stage 118 now requires regenerated JS bundle/version pins and refreshed CSS pins across all five served entries, with P14/equivalent freshness verification.

Fix suggestion: Approve the plan as written; during execution, keep source CSS, HTML stylesheet pins, generated JS bundle outputs, and P14/static verification in the same slice.

### Resolved MEDIUM — Pair Process iframe removal with contract and harness repairs
Reference: `stage-118-revision.md:39,52,62-63,99`; `app.jsx:372-377`; `dashboard-inventory.jsx:9`; `visual-quality.jsx:8`; `test_track_z_pr1_harness.py:225-226,285`; `phase-detail.jsx:641-744,865-919`.

Impact: Removing only the iframe would leave product-visible contracts/tests asserting the old duplicate surface. Stage 118 names the stale files and converts the expected contract to native `ProcessFlowPanel`/`ProcessFlowDiagram`, live strip, timing grid, logs, and defaults.

Fix suggestion: Execute Process UI and contract-test updates together; do not leave `/process_flow` embedded in `app.jsx`.

### Resolved MEDIUM — Scope Research Lab fullscreen removal and preserve Backtest fullscreen
Reference: `stage-118-revision.md:37,50,64-65,100`; `rl-panel.jsx:108-110,218-260`; `test_dashboard_validation_views.py:442-443`; `bt-result-area.jsx:49-63,269-334`.

Impact: Over-removing fullscreen would break unrelated Backtest analysis, while under-updating tests would force ResearchLab fullscreen back. Stage 118 makes the boundary explicit.

Fix suggestion: Remove only ResearchLabPanel fullscreen state/style/action, update the validation-view assertion to absence, and leave `BtResultArea` untouched.

### Resolved MEDIUM — Make all remaining parity asks non-advisory
Reference: `stage-118-revision.md:6,34-46,51,58,66-68,101`.

Impact: The prior broad UI scope could be diluted by treating research visual improvements or Home readability as advisory. Stage 118 explicitly forbids punting any listed item and binds them to file-level targets and acceptance criteria.

Fix suggestion: Use the 100% closure acceptance as the execution checklist; any omitted parity item should fail implementation review.

## Recommendations
1. Approve Stage 118 for separately approved execution; no architecture blocker remains.
2. Prefer implementing CSS freshness as an automated P14/static check that enumerates all five HTML entries and compares stylesheet pins when `styles.css` changed; build-script CSS hash injection is optional, not required by the plan.
3. Keep JS build outputs, CSS pin updates, and contract-test repairs in the same implementation branch to avoid partial served-runtime drift.
4. After implementation, run only the focused verification named by Stage 118; this review intentionally skipped tests/builds/formatters/gates per planning-only constraints.

## Architectural Status
CLEAR

## Code Review Recommendation
APPROVE

## Trade-offs
| Option | Strength | Weakness | Verdict |
|---|---|---|---|
| Approve Stage 118 | Resolves prior architect and critic issues, keeps topology stable, makes CSS/JS served runtime verifiable | Requires disciplined execution across generated artifacts and tests | Recommended |
| Require build-app CSS hash automation before approval | Strongest cache-bust automation | Over-constrains implementation choice; broader build-tool mutation than necessary for planning | Not required |
| Rely on JS build pins only | Smaller execution surface | Leaves stale CSS risk for heatmap/process/Home/parity visuals | Rejected |
| Keep Process iframe as fallback | Preserves old harness behavior | Violates native remodel and duplicate-surface cleanup | Rejected for tab UI |
| Remove all fullscreen globally | Simple product rule | Risks unrelated Backtest result regression | Rejected |

## Blockers
None.
