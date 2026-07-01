# V3 dashboard UX/UI maturity planner stage

## Summary
Status: pending approval; planning only. The previous G007 package proves route safety, explicit V3 ownership, required DOM text, nonblank screenshots, and no hidden mutating traffic. It does not prove that humans can understand V3 faster than V2. The side-by-side contact sheet shows V3 is richer but also denser: oversized global chrome, many same-weight panels, small charts, crowded heatmaps, contract/safety proof competing with task flow, and weak first-glance next actions.

Recommendation: Option B, a task-first IA redesign inside the current explicit `/ui/remodel/*` surface. V2 remains default. V3 remains explicit/selectable until separately approved.

## Evidence inspected
- `final-report.md`: PASS, deterministic 100/100, visual 97.79, V2/V3 compare 100, runtime/safety 100, 607 dashboard-focused tests.
- `final-100-scorecard.json`: rewards visual gate, interaction presence, provenance text, V2 parity, process proof, safety, accessibility affordances, failure-state proof, and evidence packaging.
- `v2-v3-compare/compare-scorecard.json`: V2 default routes load V2 bundle; explicit V3 routes load remodel app; identity/text/safety/network/inventory all pass.
- `v2-v3-compare/side-by-side-contact-sheet.png`: V3 right side is visually dense across condition, process, history, lab, workbench, audit, backtest, and chart replay.
- `visual-gate/scorecard.json`: route text/safety/visual parity thresholds pass; scoring is dominated by required text, safety text, pixel/RMSE/histogram similarity, not human task success.
- `ai_strategy_loop/dashboard/frontend/remodel/src/app.js`: single no-framework V3 app with route mapping, shell, renderers, contract matrices, UX sweep panels, and safety footer.
- `styles/theme.css`: dense dark terminal visual system, grids, panels, charts, heatmaps, safety footer, responsive rules.
- `UI_IMPLEMENTATION_SPEC.md`, `TAB_CHECKLIST.md`, `CAPTURE_REVIEW.md`: inventory-oriented spec; capture review already notes dense 1920x1080 screens scroll and recommends sticky context.

## Why the 100/100 gate missed human UX issues
1. It checked contract presence, not task completion. Text such as `Human Approval`, `Strategy Inspector`, `Backtest API Contract Matrix`, and `/sim/ws 수동 게이트` can exist while the main task remains hard to find.
2. It proved V2/V3 ownership and parity, not superiority. Correct assets, headers, required text, and screenshots do not answer whether V3 is easier than V2.
3. Visual scoring was automated and shallow: required text, safety text, pixel similarity, RMSE, and histogram can pass a crowded page.
4. Interaction proof allowed tooltip or equivalent evidence; several browser-final rows had `activeDatumChanged=false` while still passing.
5. Safety proof was over-weighted as repeated labels rather than placed at the right decision point.
6. The gate rewarded having every promised panel, which can increase cognitive load.

## In scope / out of scope
In scope: explicit V3 remodel only; human-centered IA, hierarchy, chart readability, heatmap design, backtest condition editing, chart replay workflow, task completion, cognitive load, safety information hierarchy, new human rubric and focused verification.

Out of scope: V2 default cutover, live order, broker login, account trading, hidden production export, protected runtime writes, unapproved mutating calls, new frontend framework, direct `.gjc` edits, project-wide gates/formatters during planning.

## RALPLAN-DR short mode
### Principles
1. Task first, evidence second.
2. Safety is a hierarchy, not wallpaper.
3. Charts and heatmaps must answer named questions.
4. Progressive disclosure beats dashboard maximalism.
5. V3 wins only by measured usability over V2.

### Top 3 decision drivers
1. Human task success delta versus V2.
2. Safety/default preservation: no trading/broker/account/export surprises; V2 remains default.
3. Bounded implementation risk in the current remodel app.

### Options
**Option A: conservative hierarchy polish.** Keep layouts, improve spacing, typography, chart labels, sticky context, CTA emphasis. Pros: lowest churn, safest. Cons: likely insufficient because the IA remains crowded.

**Option B: task-first IA redesign inside current V3 surface. Recommended.** Common page frame: task header, primary work canvas, context rail, secondary evidence drawer, safety-at-action rail. Pros: directly fixes the gate blind spot and creates visible V3-over-V2 superiority. Cons: more screenshot/code churn and needs a new rubric harness.

**Option C: full component-system rebuild.** Split into reusable modules/design system. Pros: best long-term maintainability. Cons: too broad for the initial maturity pass and higher route/safety regression risk.

No single-option invalidation applies because multiple viable options remain. Option C is deferred, not permanently invalidated.

## New human-centered 100-point rubric
Approval target: V3 >= 90/100, no category below 70, and V3 beats V2 by >= 15 points in comparable task-flow categories. Existing route/safety gates still pass separately.

1. Task orientation and completion, 20: first-fold purpose/current state; obvious primary next action; scripted task completion without hunting; recovery language for empty/loading/stale/error.
2. Visual hierarchy and navigation, 15: compact shell; one focal region; readable scan order at 1440x900 and 1920x1080; sticky active route/run/status context.
3. Chart and heatmap readability, 15: title/axis/unit/legend/value/threshold; readable size; selected-cell explanation and colorblind-safe scale; explicit question per visualization; keyboard value parity.
4. Workflow quality, 15: guided backtest condition editing; clear replay source-to-signal sequence; audit evidence-to-decision path; process blockers/owners/recovery before raw logs.
5. Cognitive load, 12: no more than five competing same-weight first-fold panels; secondary evidence collapsible; human labels before internal contract terms; repeated safety/provenance summarized.
6. Safety information hierarchy, 10: global non-trading boundary; action-local manual gates; visible reference/demo/live mode; no confusion between approval/export/audit.
7. Accessibility/responsive usability, 8: keyboard order, focus rings/aria values, contrast beyond color-only status, no horizontal scroll for primary tasks.
8. V2 preservation/evidence integrity, 5: V2 default, V3 explicit/no-store, durable artifacts, protected paths clean.

## Page-by-page deficiencies and priorities
1. Condition overview: too many equal panels; winner/export path buried; charts small. Redesign around active run, best candidate, risk, evidence charts, code/diff preview, human-gated decision.
2. Process: graph/logs/queues/workers/contracts compete. Add blocker-first summary, larger graph, persistent node side rail, collapsible logs/contracts.
3. History: archive, records, detail, compare, lineage compete. Sequence as Find run -> Inspect run -> Compare/export request.
4. Lab: heatmaps and research panels form a dense wall; color meaning is under-explained. Add experiment decision header, legends, axis labels, selected-cell narrative, operational rail for stalls/queue.
5. Workbench: candidate cards, heatmap, charts, metrics, handoff, notes, review queue are equal-weight. Make selected candidate focal; tie evidence and CTAs to that candidate.
6. Decision audit: checklist, OOS CI, alerts, regimes, evidence, decision form, ledger are crowded. Use evidence -> unresolved risks -> decision -> append-only preview funnel; make PROMOTE visually stricter than safer choices.
7. Backtest: contract matrix is too prominent; condition editor is raw split code boxes; run params/optimize/WFO/sweep/logs/results crowd each other. Workflow should be Select strategy/data -> Edit condition -> Validate -> Gated run/preview -> Analyze result. Move API matrix to evidence drawer; add validation diagnostics, variable helper, diff preview, manual-gated save/run.
8. Chart replay: selectors, protocol proof, controls, charts, signal log, minimap/indicators are dense. Workflow should be Choose source/date/symbol -> Choose strategy -> Preview bars/signals -> Start manual replay -> Investigate signal. Make playback controls sticky, main candle chart larger, selected bar and signal log synchronized, protocol matrix collapsible.

## File-level changes for approved implementation
- `ai_strategy_loop/dashboard/frontend/remodel/src/app.js`: add shared task header, canvas, rail, drawer, safety-at-action helpers; rework renderers for condition/process/history/lab/workbench/audit/backtest/replay; preserve route mapping, mode detection, manual gates.
- `ai_strategy_loop/dashboard/frontend/remodel/styles/theme.css`: add hierarchy tokens, compact shell, sticky task context, readable chart/heatmap layouts, responsive first-fold rules, focus states.
- `ai_strategy_loop/dashboard/frontend/remodel/src/data.js`: add reference copy for task headers, selected-cell explanations, editor diagnostics, replay step labels, selected-candidate narratives; no live trading/account/broker data.
- `ai_strategy_loop/dashboard/frontend/remodel/docs/UI_IMPLEMENTATION_SPEC.md` and `TAB_CHECKLIST.md`: replace inventory-only success language with task-first rubric/checklist.
- Add `scripts/verify_dashboard_human_ux_rubric.py`: score V2/V3 screenshots, DOM markers, and scripted task paths against the new rubric.
- Update focused dashboard tests for route/default preservation, task markers, chart/heatmap labels, condition editor workflow, replay workflow, and action-local safety.

## Sequencing and dependencies
1. Approval checkpoint: this artifact remains pending until explicit implementation approval.
2. Baseline lock: capture current V2/V3 human issues; preserve V2 default.
3. Shared IA primitives in V3 only; verify route identity and forbidden action absence.
4. Tranche A: condition, process, history for orientation and next-action clarity.
5. Tranche B: lab, workbench, audit for readable analysis and decision funnels.
6. Tranche C: backtest and chart replay for guided editing/replay workflows.
7. Human rubric harness and annotated artifacts.
8. Architect review for safety/IA regression; critic review for rubric loopholes; executor implements tranches after approval. Team only if pages are parallelized; ultragoal only for a longer durable execution ledger.

## Acceptance criteria
- Plan remains pending approval; no product source edits from this planner stage.
- V2 default routes still load V2 assets; V3 remains explicit `/ui/remodel/*` and no-store.
- V3 human rubric >= 90, no category < 70, and >= 15 point V2 delta on task orientation, visualization readability, workflow quality, and cognitive load.
- Page outcomes: condition first fold shows run/best candidate/evidence/decision; process shows phase/blocker/owner/recovery; history supports find-inspect-compare-export; lab heatmaps have legends/selected explanation; workbench selected candidate drives evidence/CTAs; audit funnels evidence to append-only decision; backtest has guided buy/sell edit, validation, diff, gated save/run; replay has obvious selection/playback/signal investigation.
- No live order, broker login, account trading, hidden production export, protected runtime writes, or unapproved mutating calls. Backtest/replay mutating endpoints remain manual-gated and not page-load triggered.
- Durable human-rubric JSON/contact sheet plus existing visual/compare/safety evidence are produced after implementation.

## Verification commands for approved implementation only
Focused tests:
```powershell
python -m pytest tests/unit/test_dashboard_remodel_static.py tests/unit/test_dashboard_route_parity.py tests/unit/dashboard -q
```
Visual gate:
```powershell
python scripts/verify_dashboard_remodel_visual_gate.py --base-url http://127.0.0.1:8777 --out artifacts/dashboard-human-ux-v3/visual-gate
```
V2/V3 preservation:
```powershell
python scripts/verify_dashboard_v2_v3_compare.py --v2-base-url http://127.0.0.1:8777 --v3-base-url http://127.0.0.1:8777 --out artifacts/dashboard-human-ux-v3/v2-v3-compare
```
Safety audit:
```powershell
python scripts/verify_dashboard_safety_audit.py --v2-base-url http://127.0.0.1:8777 --v3-base-url http://127.0.0.1:8777 --out artifacts/dashboard-human-ux-v3/safety-audit
```
New human rubric gate:
```powershell
python scripts/verify_dashboard_human_ux_rubric.py --v2-base-url http://127.0.0.1:8777 --v3-base-url http://127.0.0.1:8777 --out artifacts/dashboard-human-ux-v3/human-rubric --min-v3-score 90 --min-delta 15
```
Diff/protected path checks:
```powershell
git diff --check -- ai_strategy_loop/dashboard/frontend/remodel tests/unit/test_dashboard_remodel_static.py tests/unit/test_dashboard_route_parity.py tests/unit/dashboard scripts/verify_dashboard_human_ux_rubric.py
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

## Risks and mitigations
- Safety proof hidden too deeply: keep global boundary visible and action-local gates mandatory; run safety audit.
- Route/default regression: do not touch V2 routes/assets; run compare after each tranche.
- Inventory gates fail after progressive disclosure: keep required DOM markers stable inside drawers/tabs.
- Human rubric becomes another superficial checklist: include scripted task paths, first-fold checks, chart semantics, and V2 delta.
- Large `app.js` churn: implement in tranches with explicit helpers; avoid framework migration.
- Accidental live/backend calls: preserve reference/demo inert behavior and safe GET-only probing; mutating POST/WS actions stay manual-gated.
