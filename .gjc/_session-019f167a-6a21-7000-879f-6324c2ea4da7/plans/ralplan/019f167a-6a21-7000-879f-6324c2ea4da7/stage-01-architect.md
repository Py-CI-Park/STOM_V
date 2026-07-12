## Summary
Planner artifact `stage-01-planner.md` is architecturally sound for a planning-stage V3 dashboard maturity pass: it attacks the demonstrated UX gap directly while preserving V2 default behavior and safety boundaries. Architectural status is `WATCH`, not `BLOCK`, because implementation must keep the new human rubric from becoming another static inventory gate and must protect route/safety evidence through large V3-only IA churn. Recommendation: approve Option B for explicit V3 only after the separate implementation approval checkpoint.

## Analysis
### Spec compliance
- The planner stays within planning scope and explicitly keeps V2 default / V3 explicit: `stage-01-planner.md` lines 6, 29, 84-99 require V2 default routes, explicit `/ui/remodel/*`, no product edits from planning, no live order/broker/account/hidden export/protected writes, and no unapproved mutating calls.
- Existing route evidence supports that boundary: `v2-v3-compare/compare-scorecard.json` lines 34-70 show V2 loading `/ui/bundle/app.js` while explicit V3 loads `/ui/remodel/src/app.js` with `no-store`; lines 832-835 document the score formula and identity checks.
- Safety evidence is strong but should remain a gate, not a layout objective: `safety-audit/safety-scorecard.json` reports 100.0 across source/DOM/runtime/export-separation evidence, and `app.js` line 1244 renders the global No Live Order / No Broker Login / No Account Trading / Research Only / Human Approval Gate / Append-Only Audit footer.

### UX strategy soundness
- The planner correctly identifies the root mismatch: prior gates proved presence/ownership/safety, not task success (`stage-01-planner.md` lines 18-24). The visual gate formula confirms this: `visual-gate/scorecard.json` lines 368-371 weights required text, safety text, pixel similarity, RMSE, and histogram; those can pass a crowded dashboard.
- The side-by-side contact sheet and docs support the density diagnosis. `UI_IMPLEMENTATION_SPEC.md` line 7 explicitly describes dense modular panels, and `docs/captures/CAPTURE_REVIEW.md` lines 46-53 notes dense 1920x1080 pages need vertical scroll and recommends sticky context.
- Option B is the right middle path: `stage-01-planner.md` line 47 proposes a common task header, primary work canvas, context rail, secondary evidence drawer, and action-local safety rail. This directly addresses first-glance orientation without jumping to the Option C component-system rebuild.

### Architectural fit
- The current V3 remodel is a no-build static SPA by design (`ARCHITECTURE.md` lines 5-14), so adding shared IA primitives in `app.js`, copy in `data.js`, and hierarchy CSS in `theme.css` is consistent with the architecture.
- The implementation surface is bounded: `app.js` has a central route-to-state mapping and render dispatch (`app.js` lines 137-176, 738-744) plus page renderers (`app.js` lines 1165-1511), matching the planner file-level change list (`stage-01-planner.md` lines 75-80).
- The main architecture risk is churn concentration in one large renderer file, not a conceptual boundary error. The planner mitigates this with tranches and no framework migration (`stage-01-planner.md` lines 83-91, 133).

### Strongest steelman antithesis
The best argument against the plan is that V3 already has deterministic 100/100 final evidence and traders often prefer dense, information-rich screens over simplified task funnels. Moving contract matrices and safety proof into drawers could hide critical compliance context, break required DOM/inventory gates, and add broad regression risk to a no-build `app.js` with many inline renderers. A subjective human rubric might be gamed just as easily as the old text/pixel gates, while Option A could deliver most perceived benefit with less risk.

### Synthesis / recommendation
The antithesis is valid about risk but loses on the evidence: the existing pass criteria rewarded presence and parity, while the contact sheet and docs show the actual human problem is orientation, hierarchy, and next-action clarity. Option B should proceed because it preserves the route/safety contract, avoids a framework rebuild, and introduces measurable V2 delta; however, the first approved implementation slice must make the human rubric scripted and falsifiable before treating visual polish as success.

### Principle violations
- Planner artifact: no principle violations found. It preserves V2 default, keeps V3 explicit, respects safety constraints, and ties success to V2 usability delta.
- Current V3 evidence: the current dashboard strains the planner principles: task-first is diluted by same-weight inventory panels, safety appears repeatedly as wallpaper rather than primarily at action points, charts/heatmaps do not consistently answer named questions, and progressive disclosure is underused. These are the defects the plan is designed to fix.

## Root Cause
The root cause is a measurement/IA mismatch, not missing widgets: the previous dashboard program optimized for route ownership, required text, safety labels, screenshot nonblankness, and inventory coverage. That created a V3 that is richer and safer on paper but not proven faster or more intuitive than V2 for concrete human tasks.

## Findings
1. **MEDIUM — Human rubric can become another shallow gate.** Reference: `stage-01-planner.md` lines 53-63 and 118-132. Impact: V3 could pass by adding labels/markers without improving task completion, repeating the prior 100/100 blind spot. Fix: define scripted task paths, first-fold assertions, observable action traces, V2 baseline scoring, and annotated contact sheets as required rubric evidence.
2. **MEDIUM — Large `app.js` churn requires strict tranche boundaries.** Reference: `app.js` route/render structure at lines 137-176, 738-744, 1165-1511; planner file list at `stage-01-planner.md` lines 75-80. Impact: shared IA helpers can regress route identity, manual-gated controls, or page-specific affordances across all eight pages. Fix: implement shared frame helpers first, migrate pages in tranches, and run route/safety compare after each approved tranche.
3. **LOW — Progressive disclosure can hide safety and contract evidence if implemented too aggressively.** Reference: `app.js` line 1244 and `stage-01-planner.md` lines 128-134. Impact: moving matrices and labels into drawers could make safety less visible or break DOM/inventory checks. Fix: keep global boundary visible, put manual gates next to actions, and retain required DOM markers inside accessible drawers/tabs.
4. **LOW — Existing docs/checklists are inventory-oriented.** Reference: `UI_IMPLEMENTATION_SPEC.md` line 7, `TAB_CHECKLIST.md` lines 57-62, and `docs/captures/CAPTURE_REVIEW.md` lines 46-53. Impact: implementers may recreate the dense inventory layout while claiming compliance. Fix: update docs/checklists to task-first outcomes in the same approved implementation tranche as UI changes.

## Recommendations
1. Approve Option B as the planning direction, with zero implementation until explicit execution approval.
2. Make the human UX rubric script the first deliverable of execution: task scenarios, scoring method, V2 baseline, failure examples, and artifact schema.
3. Preserve V2 untouched and keep V3 under explicit `/ui/remodel/*`; route identity and forbidden-action scans stay mandatory after each tranche.
4. Keep safety as hierarchy: global non-trading boundary remains visible, while export/save/run/replay gates are action-local and manual.
5. Carry a watch item that backtest and chart replay must receive early storyboard/rubric proof even if full implementation lands in a later tranche, because they are the clearest places where V3 can feel immediately better or worse.

## Architectural Status
`WATCH`

## Code Review Recommendation
`APPROVE`

## Trade-offs
| Tension | Option / Benefit | Cost / Risk | Recommendation |
|---|---|---|---|
| Dense expert dashboard vs task-first flow | Dense layouts maximize simultaneous context for power users | Same-weight panels hide next actions and make V3 feel harder than V2 | Use task-first first fold with collapsible evidence drawers, not removal of expert detail |
| Safety visibility vs safety wallpaper | Repeated labels make audits easy | Repetition competes with workflow and dulls warning salience | Keep one global boundary plus action-local gates at save/export/run/replay points |
| Small polish vs IA remodel | Option A has lower churn | It leaves the root hierarchy/task-flow issue intact | Choose Option B, but tranche it tightly |
| Full design system vs current no-build SPA | Option C improves long-term maintainability | Too much migration risk for a maturity pass | Defer; extract helpers only where needed in current app |
| Automated score vs human task proof | Automation is repeatable | It can be gamed by text/DOM markers | Combine scripted browser tasks, annotated screenshots, and V2 delta thresholds |

Blockers: 0.
