## Summary
The stage-117 revision resolves the prior architect BLOCK: served runtime generation/version pins, stale Process iframe contracts/tests, Research Lab fullscreen test repair, and scoped fullscreen removal are now explicit execution requirements. Architecture/product/code statuses are CLEAR for planning approval; the only execution watch is to treat every changed version-pinned asset, including CSS when touched, as part of the served-output check.

Recommendation: APPROVE the revised plan for separately approved execution. No blockers remain.

## Analysis
### Spec compliance
The reviewed artifact is `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-117-revision.md`. It directly incorporates all prior blockers in Required Amendments: served bundle regeneration, `dashboard-inventory.jsx`/`visual-quality.jsx`/Track Z harness updates for Process, `tests/unit/test_dashboard_validation_views.py` update for Research Lab fullscreen absence, and explicit preservation of `BtResultArea` fullscreen.

Evidence that these amendments target real repository contracts:
- Served runtime is generated, not raw JSX: `ai_strategy_loop/dashboard/frontend/index.html:23-43` loads `/ui/bundle/stom-ui.js` and `/ui/bundle/app.js`; `ai_strategy_loop/dashboard/webui-build/package.json:9-11` exposes `build` and `build:app`; `ai_strategy_loop/dashboard/webui-build/build-app.mjs:12,76-118` writes HTML hash pins and `frontend/bundle/manifest.json`; `tests/unit/dashboard/test_p14_build_harness.py:198-223` asserts manifest/hash/HTML consistency.
- Process iframe removal is a real contract repair: `app.jsx:371-377` still embeds `/process_flow` under the Process tab, while `phase-detail.jsx:641-744,865-868` exposes native `ProcessFlowDiagram`/`ProcessFlowPanel` over `current_step`, `step_timings`, and live timing state. Stale contracts are present at `dashboard-inventory.jsx:9`, `visual-quality.jsx:8`, and `tests/unit/dashboard/test_track_z_pr1_harness.py:225,285`.
- Research Lab fullscreen removal must be scoped: `rl-panel.jsx:108-110,218-260` contains ResearchLabPanel fullscreen state/style/button; `tests/unit/test_dashboard_validation_views.py:442-443` currently asserts `전체 화면`; `bt-result-area.jsx:49-50,269-334` contains a separate Backtest fullscreen analysis path that should remain.
- The remaining user scope is grounded: heatmap axes and fixed cell sizing are in `analysis.jsx:104-129,264-274`; counts are rendered at `analysis.jsx:312-316`; Evolution GUI Parity still passes `columns={2}` at `evolution-gui-parity-panel.jsx:115` while `bt-gui-parity.jsx:535-538` supports a two-column switch; Home still has research links such as `리서치 Wiki` at `app.jsx:769-778`; Lab/Workbench/HOF ownership text is present in `ui-contract.jsx:15-19`, `dashboard-inventory.jsx:13`, and `dashboard-pages.jsx:171-203`.

### Steelman antithesis
The strongest argument against broadening the plan is that source-only frontend edits plus a narrow happy-path test list would be faster and less noisy. Keeping `/process_flow` embedded as a fallback and leaving the existing fullscreen assertion could also appear to preserve backwards compatibility while the native Process panel and Lab controls evolve.

That argument fails for this repository. The browser serves generated bundle artifacts, so JSX-only edits can pass static review while users still see stale behavior. The stale iframe/fullscreen contracts are not harmless compatibility: they either force removed behavior back into the product or guarantee harness/test drift after implementation.

### Tradeoff tension
- Runtime truth vs planning speed: generated `bundle/app.js`, manifest, and asset pins increase execution surface, but they are the deployed UI contract.
- Native Process tab vs reference endpoint: keeping `/process_flow` as read-only reference is useful; embedding it in the tab preserves the duplicate surface the user asked to remove.
- Scoped fullscreen removal vs global simplification: removing only ResearchLabPanel avoids an unrelated Backtest result regression.
- Home readability vs duplicate owners: navigation cards improve discoverability only if they summarize/link and do not render Lab/History/Workbench/HOF internals on Home.
- One-column GUI parity vs vertical density: stacked charts cost height but match the readability ask.
- Frontend-only research strengthening vs invented data: top-N/sorting/legends/detail are safe; any missing analytics fields must remain additive and honest.

### Synthesis
Stage 117 turns the previous architecture gap into explicit deliverables: runtime bundle/version outputs, contract-test repairs, and scoped behavior removal. The plan should proceed after user approval with those deliverables treated as product artifacts, not optional gates.

### Status matrix
- Architecture status: CLEAR — ownership boundaries remain stable, no new routes are required, and `/process_flow` is demoted to read-only reference rather than a duplicate Process owner.
- Product status: CLEAR — the plan covers bounded edge/heatmap sizing, Process remodel/animations, research visualization strengthening, Home readability, and one-column GUI parity without adding duplicate surfaces.
- Code/contract status: CLEAR — the plan names the stale contract files/tests and served outputs required to make implementation observable. Execution watch: because `styles.css` is in scope and `index.html:12` has a versioned stylesheet URL, CSS pin/hash handling must be included whenever CSS changes.

## Root Cause
The prior BLOCK came from source-runtime and source-contract drift: the plan treated raw `.jsx` edits as the served UI and omitted contracts/tests that still required removed iframe/fullscreen behavior. Stage 117 fixes the root planning defect by making served artifact generation and stale contract repair first-class execution steps.

## Findings
### Resolved HIGH — Served frontend bundle/version-pin regeneration is now required
**Reference:** stage-117 Required Amendment 1, Phase 6, Acceptance Criteria; `index.html:23-43`; `package.json:9-11`; `build-app.mjs:76-118`; `test_p14_build_harness.py:198-223`.

The revised plan requires `npm run build:app` or `npm run build`, includes `frontend/bundle/app.js`, changed bundle outputs, and version pins/manifest outputs. This closes the prior risk that browser users would keep receiving stale `/ui/bundle/app.js` despite JSX edits.

### Resolved MEDIUM — Process iframe contracts/tests are in scope
**Reference:** stage-117 Required Amendment 2 and Acceptance Criteria; `app.jsx:371-377`; `phase-detail.jsx:641-744`; `dashboard-inventory.jsx:9`; `visual-quality.jsx:8`; `test_track_z_pr1_harness.py:225,285`.

The plan now explicitly updates product inventory, visual baseline text, and Track Z harness expectations from iframe-required to native `ProcessFlowPanel`/`ProcessFlowDiagram` contracts while preserving `/process_flow` only as read-only reference.

### Resolved MEDIUM — Research Lab fullscreen test contract is repaired and Backtest fullscreen is preserved
**Reference:** stage-117 Required Amendments 3-4; `rl-panel.jsx:108-110,218-260`; `test_dashboard_validation_views.py:442-443`; `bt-result-area.jsx:49-50,269-334`.

The plan updates the validation-view test to assert ResearchLabPanel fullscreen absence while preserving ops/validation/equity/route contracts, and it explicitly prevents accidental removal of Backtest fullscreen analysis.

### Resolved MEDIUM — Remaining user scope is represented without route or ownership sprawl
**Reference:** stage-117 File-Level Plan and Acceptance Criteria; `analysis.jsx:104-129,264-274`; `rl-analysis.jsx:88-145,171-211`; `app.jsx:769-778`; `ui-contract.jsx:15-19`; `evolution-gui-parity-panel.jsx:115`; `bt-gui-parity.jsx:535-538`.

The plan covers canonical sparse heatmap axes, bounded sizing, Process motion/reduced-motion, research visualization controls/detail/low-sample warnings, readable Home cards, and one-column GUI parity while retaining owner boundaries: Lab explores, History archives, Workbench/HOF analyze/promote, Home summarizes.

### LOW execution watch — Include stylesheet cache pin handling when CSS changes
**Reference:** `index.html:12`; stage-117 File-Level Plan includes `styles.css`; `build-app.mjs:76-118` updates bundle pins/manifest.

The plan says served runtime must include version pins, which is enough for planning approval. During execution, ensure the `styles.css` version pin or equivalent cache-busting mechanism is updated if stylesheet changes are made, because the bundle build machinery primarily handles `app.js` and `stom-ui.js` pins.

## Recommendations
1. Approve stage 117 for execution after the user explicitly approves implementation.
2. Execute with bundle/version outputs as required deliverables, including CSS cache pin handling if `styles.css` changes.
3. Keep Process iframe removal and Research Lab fullscreen removal paired with their contract-test updates in the same implementation slice.
4. Preserve Backtest `BtResultArea` fullscreen unless a separate product decision changes that scope.
5. Run only the focused verification listed by the plan after implementation; no gates/builds/tests were run during this planning review.

## Architectural Status
CLEAR

## Code Review Recommendation
APPROVE

## Trade-offs
| Option | Strength | Weakness | Verdict |
|---|---|---|---|
| Approve stage 117 as revised | Resolves prior BLOCK, aligns runtime artifacts and contracts, covers remaining user scope | Slightly broader execution surface | Recommended |
| Keep stage 115 source-only focus | Smaller diff and less generated output | Can ship stale served UI and stale iframe/fullscreen contracts | Rejected |
| Keep `/process_flow` embedded as fallback | Familiar legacy view remains visible | Duplicates Process ownership and conflicts with native remodel | Rejected for tab UI; keep endpoint as reference only |
| Remove all fullscreen globally | Simple rule | Breaks unrelated Backtest fullscreen analysis | Rejected |
| Add new HOF route from Home | Direct navigation | Violates stable-route/no-duplicate-owner constraint | Use existing Workbench/HOF section or overview anchor |

## Blockers
None.
