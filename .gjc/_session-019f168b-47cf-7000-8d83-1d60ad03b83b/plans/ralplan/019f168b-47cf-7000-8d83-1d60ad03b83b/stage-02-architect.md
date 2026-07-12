## Summary
The revised planner artifact is architecturally sound and executable after explicit approval, provided execution starts with Tranche 0 only. It converts the previous subjective UX gap into a scripted baseline, storyboard, and rubric contract with routes, selectors, viewports, thresholds, V2 deltas, hard safety caps, and durable artifacts while preserving V2 default and explicit V3 safety constraints.

Recommendation: proceed with the plan as CLEAR / APPROVE; no UI churn should occur until Tranche 0 rubric and storyboard evidence receives Architect/Critic review.

## Analysis
### Spec compliance
- The requested Tranche 0 baseline is now explicit: the plan requires a read-only human UX verifier, V2/current V3 baseline captures, machine-checkable Condition/Backtest/Chart Replay storyboards, selector-contract documentation, and Architect/Critic review before shared IA or page churn. Evidence: stage-02-revision.md lines 35-43.
- The human UX rubric is falsifiable enough for approved execution: command shape and args are defined, all eight V2/V3 scenarios are mapped, three viewports are specified, selector contracts cover task frame/safety/charts/heatmaps/backtest/replay, scripted actions include network capture, first-fold geometry, tab stops, chart focus, evidence drawer markers, screenshots, and contact sheet. Evidence: stage-02-revision.md lines 45-70.
- Subjective criteria were replaced by measurable thresholds: task header top less than 25 percent viewport, tab stops no more than 8, first-fold panel/rail limits, chart/heatmap minimum sizes, heatmap narrative at least 40 chars, repeated safety/provenance no more than 2 global blocks plus local gates, manual-gate reason within 220 px, and final V3 at least 90 with no category below 70 and mean V3-V2 delta at least 15 in named human-flow categories. Evidence: stage-02-revision.md lines 72-84.
- The JSON/artifact contract is durable: required fields include schema/version/status/tranche/thresholds/viewports/routes/scenarios/steps/scores/network/screenshots/failures/category deltas/hard failures/contact sheet/trace. Evidence: stage-02-revision.md line 86.
- Backtest and Chart Replay risks are addressed through early storyboard proof: Backtest must cover select, edit, validate, diff/variable helper, manual-gated run/save, and analyze with no page-load POSTs; Replay must cover source/date/symbol, strategy, preview, manual start, and signal investigation with no /sim/ws on load. Evidence: stage-02-revision.md lines 88-93.
- Progressive disclosure is bounded by a preservation contract: global six safety texts, route identity, compare-gate page text, Backtest endpoint contract markers, and Replay endpoint/action/message markers must remain discoverable in DOM even inside drawers/tabs. Evidence: stage-02-revision.md lines 95-101.

### Existing-system grounding
- Current V3 is a no-framework remodel app with central route mapping and explicit V3 routes. routeToState maps condition/process/history/lab/workbench/audit/backtest/chart-replay, and pushRouteFromState preserves the current query string. Evidence: ai_strategy_loop/dashboard/frontend/remodel/src/app.js lines 64-161.
- Existing safety mechanics align with the plan: manual gates are centralized in manualGateAttrs, current shell displays mode/run/route boundary state, and the safety footer renders the six global safety cues. Evidence: app.js lines 223-229, 680-710, 1243-1246.
- Existing Backtest/Replay contracts provide a concrete preservation source: Backtest enumerates /bt/health, strategies, validate/save/delete, extract vars, data range, /bt/run, jobs, cancel, meta, ws job, portfolio, and report; Replay enumerates /sim/health, days, demo, stocks, signals, /sim/ws, start/pause/resume/speed/seek/stop, meta/bars/history/done/error. Evidence: app.js lines 64-128. Current renderers still place contract matrices prominently, validating the risk that contract proof can compete with task flow. Evidence: app.js lines 1429-1511.
- Existing route/default preservation is already testable: route parity tests assert V2 deep links load /ui/bundle/app.js and not /ui/remodel/src/app.js, explicit V3 selectors load remodel assets, and direct /ui/remodel routes with demo=reference are served. Evidence: tests/unit/test_dashboard_route_parity.py lines 31-40, 104-143.
- Existing compare/safety scripts already encode V2/V3 ownership and unsafe request boundaries: compare requires the global six safety texts, bans unsafe URL/DOM markers, and captures eight V2/V3 route pairs; safety audit bans unsafe source/runtime patterns including /bt/run, /bt/strategy/validate, /sim/ws, broker/account/order paths, and only allows /ws as an auto websocket. Evidence: scripts/verify_dashboard_v2_v3_compare.py lines 27-145; scripts/verify_dashboard_safety_audit.py lines 21-105.
- Prior evidence supports the premise: the G007 final report passed 100/100 but focused on evidence/contract/route/safety categories rather than human task success, and the V2/V3 contact sheet shows V3 is richer but visually denser across all eight surfaces. Evidence: artifacts/ultragoal-g007-final-evidence/final-report.md; final-100-scorecard.json lines 1-47; v2-v3-compare/side-by-side-contact-sheet.png.

### Strongest steelman antithesis
The strongest contrary case is that Option B may overcorrect: the current package already proves route ownership, safety, inert reference/demo behavior, contract matrices, and 607 dashboard-focused tests, so a task-first IA redesign could create more regression risk than value. A conservative Option A polish would preserve the known-good safety/contract layout, avoid large app.js churn, and avoid a bespoke rubric that implementers might game by adding selectors rather than improving comprehension.

That antithesis is credible because progressive disclosure can hide compliance proof, V2 lacks many proposed selectors so delta scoring can become unfair, and measuring same-weight panels or primary canvas can drift back into subjective judgment unless Tranche 0 externalizes the heuristic.

### Tradeoff tension
The central tension is auditability versus usability. Current V3 has strong safety and contract visibility, but that visibility consumes first-fold attention; moving details into drawers improves task flow but risks weakening compliance evidence unless DOM markers, local gates, and hard caps remain first-class. The revised plan resolves this by making route/safety hard failures score-capping and non-negotiable while measuring human task success separately.

### Synthesis
Option B is the right path because it does not start by rewriting the UI; it starts by measuring the current task gap. Tranche 0 makes the redesign falsifiable before page churn, and the hard-failure caps preserve the safety/default contract that made the current package reliable. Execution can proceed after approval without guessing, as long as Tranche 0 is treated as a real checkpoint rather than a paperwork prelude.

## Root Cause
The root defect is not broken routing or missing safety text; it is a measurement mismatch. The previous 100/100 package rewarded required text, route ownership, screenshot non-blankness, contract/inventory presence, and safety labels, allowing a dense V3 to pass without proving first-fold comprehension, task completion, chart interpretation, Backtest editing, Replay investigation, or measurable superiority over V2. The revised plan addresses the root cause by requiring a task-based rubric and V2 delta before UI churn.

## Findings
- LOW / WATCH: stage-02-revision.md lines 70-78. Some rubric terms still need exact implementation heuristics, especially same-weight panels, primary canvas, secondary panels not visually equal, and focus indicator detectable. Impact: a shallow verifier could pass selector-compliant but still cluttered layouts, recreating the old gate blind spot. Fix: Tranche 0 should emit detector definitions and annotated overlays in JSON/contact sheet evidence, and Architect/Critic should reject scores that cannot be reproduced from DOM geometry, CSS class roles, and screenshots.
- LOW / WATCH: stage-02-revision.md lines 84-86. V2 fallback scoring is appropriately allowed for missing V2 selectors, but fairness depends on recording when text/geometry fallback is used. Impact: V3 could appear to win merely because it was designed for the new selectors. Fix: include per-step selectorObserved, fallbackUsed, and fallbackReason fields so V2 delta remains auditable.
- LOW / WATCH: stage-02-revision.md lines 88-93 and 120-125. Storyboards are required and tranche thresholds are concrete, but the storyboard file schema is not fully spelled out. Impact: executor could produce narrative storyboards that are harder to machine-check. Fix: Tranche 0 should define storyboards.json as scenario -> ordered steps -> route -> selector assertions -> safety assertions -> expected observation -> artifact links.
- LOW / WATCH: stage-02-revision.md lines 95-101 and 142-148. Progressive disclosure is architecturally acceptable only if contract/safety markers remain in DOM and human labels precede endpoint terms. Impact: drawers could accidentally demote safety proof below usability goals. Fix: keep data-contract-marker and data-manual-gate assertions as hard failures, not optional category deductions.

No MEDIUM, HIGH, or CRITICAL blockers were found in the revised plan.

## Recommendations
1. Approve the plan for post-approval execution with a strict first slice: implement Tranche 0 only, produce baseline JSON/contact sheet/storyboards, then stop for Architect/Critic review before shared IA or page churn.
2. In Tranche 0, require the verifier to fail closed on V2 default regression, V3 explicit-route regression, forbidden page-load POST/WS, forbidden broker/account/order DOM markers, protected runtime dirtiness, and missing DOM markers inside drawers.
3. Require Tranche 0 verifier output to include reproducible scoring evidence: geometry boxes, tab-stop counts, request/websocket logs, selector/fallback status, viewport-specific screenshots, annotated contact sheet, and hard-failure trace.
4. Keep Backtest and Replay as early high-risk pages: do not defer storyboard validation to the final pass; their page-load no-POST/no-WS assertions and action-local manual-gate reason checks should run before broader IA changes.
5. Preserve current route/default/safety tests and compare/safety scripts as independent gates; the new human rubric should add a human-task dimension, not replace existing safety evidence.

## Architectural Status
CLEAR

## Code Review Recommendation
APPROVE

## Trade-offs
| Option | Strength | Risk | Architect disposition |
|---|---|---|---|
| A. Conservative polish | Lowest regression risk; preserves known-good contract-heavy layout | Does not directly prove human task success or V3-over-V2 superiority | Acceptable fallback only if Tranche 0 shows small polish reaches thresholds |
| B. Task-first IA plus Tranche 0 rubric | Measures before changing UI; targets actual human workflow gap; preserves hard safety caps | More implementation churn; scorer can be gamed if heuristics are vague | Recommended and approved, with Tranche 0 checkpoint mandatory |
| C. Component-system rebuild | Best long-term modularity | Too broad; high route/safety regression risk; not needed for UX maturity proof | Defer |

Residual watch items: scorer heuristic reproducibility, V2 fallback fairness, strict storyboard schema, and drawer-based marker preservation. Blocker count: 0.
