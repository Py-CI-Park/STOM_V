# V3 dashboard UX/UI maturity plan revision

## Summary
Status: pending approval; planning only. This revision addresses Architect WATCH and Critic ITERATE while preserving V2 default and V3 explicit `/ui/remodel/*`. Recommendation remains Option B: task-first IA redesign, but execution must begin with Tranche 0 rubric/storyboard baseline before any UI churn.

Why revise: the prior 100/100 package proved route ownership, required text, safety labels, nonblank screenshots, inventory, and no hidden mutating traffic. It did not prove scripted human task success, first-fold clarity, chart interpretation, guided backtest editing, guided replay investigation, or measurable V3 delta over V2.

## In scope / out of scope
In scope: explicit V3 pages only; human-centered superiority over V2; falsifiable rubric script; V2/V3 baseline; page storyboards; per-tranche route/safety/rubric verification; preserved safety and contract DOM markers.

Out of scope: V2 cutover, live order, broker login, account trading, hidden production export, protected runtime writes, unapproved mutating calls, new framework, product-source edits during planning, tests/gates/formatters during planning.

## RALPLAN-DR short mode
Principles:
1. Measure the task before changing the page.
2. V3 wins only by scripted V2 delta, not widget count.
3. V2/default and safety evidence are tranche invariants.
4. Progressive disclosure may reduce clutter but must keep required DOM markers discoverable.
5. Backtest and Chart Replay require early storyboard/rubric proof.

Top decision drivers:
1. V3 task success and cognitive-load delta over V2.
2. Preservation of V2 default, explicit V3, route identity, safety, and contract markers.
3. Bounded implementation in current no-framework remodel files.

Options:
- A Conservative polish: safest, but insufficient because it keeps measurement subjective.
- B Task-first IA plus Tranche 0 rubric baseline: recommended; fixes the measurement gap before UI changes.
- C Full component-system rebuild: deferred due scope/risk.
No single-option invalidation applies; A remains fallback if Tranche 0 proves small polish is enough, C remains later work.

## Evidence basis
Inspected evidence: final report PASS 100/100; final scorecard rewards evidence/contract categories; V2/V3 compare proves V2 bundle default and explicit V3 remodel bundle/no-store; visual gate formula is required text + safety text + pixel/RMSE/histogram; contact sheet shows V3 is richer but denser; remodel app has central route dispatch/renderers plus safety footer and contract matrices.

## Tranche 0 required before implementation
Deliver after explicit execution approval and before UI redesign:
1. Add read-only `scripts/verify_dashboard_human_ux_rubric.py`.
2. Capture current V2 and current explicit V3 baseline under `artifacts/dashboard-human-ux-v3/tranche-0-baseline/`.
3. Produce machine-checkable storyboards under `artifacts/dashboard-human-ux-v3/storyboards/` for Condition, Backtest, and Chart Replay at minimum.
4. Document selector contract and preserved markers.
5. Architect/Critic review Tranche 0 before shared IA or page churn.

Tranche 0 passes when the script emits valid baseline JSON/contact sheet, route/safety hard failures are zero, and Backtest/Replay storyboards map each step to selectors, safety assertions, and rubric observations. Baseline scores may be below final target.

## Falsifiable human UX rubric script contract
Command shape:
```powershell
python scripts/verify_dashboard_human_ux_rubric.py --v2-base-url http://127.0.0.1:8777 --v3-base-url http://127.0.0.1:8777 --out artifacts/dashboard-human-ux-v3/human-rubric --viewports 1440x900,1920x1080,1280x720 --min-v3-score 90 --min-delta 15
```
Args: required `--v2-base-url`, `--v3-base-url`, `--out`; optional `--viewports`, `--pages`, `--tranche baseline|shared|a|b|c|final`, `--min-v3-score`, `--min-delta`, `--storyboard`.

Scenarios:
- UX-S01 condition review: V2 `/ui/evolution`, V3 `/ui/remodel/condition?demo=reference`.
- UX-S02 process diagnose: V2 `/ui/evolution/process`, V3 `/ui/remodel/process?demo=reference`.
- UX-S03 history compare: V2 `/ui/evolution/records`, V3 `/ui/remodel/history?demo=reference`.
- UX-S04 lab heatmap: V2 `/ui/evolution/lab`, V3 `/ui/remodel/lab?demo=reference`.
- UX-S05 workbench handoff: V2 `/ui/evolution/workbench`, V3 `/ui/remodel/workbench?demo=reference`.
- UX-S06 audit decision: V2 `/ui/evolution/verdict`, V3 `/ui/remodel/audit?demo=reference`.
- UX-S07 backtest edit/validate: V2 `/ui/backtest`, V3 `/ui/remodel/backtest?demo=reference`.
- UX-S08 replay investigate signal: V2 `/ui/chart-replay`, V3 `/ui/remodel/chart-replay?demo=reference`.

V3 selector contract after implementation:
- Task frame: `[data-ux-task-header=PAGE]`, `[data-ux-field=purpose|state|primary-action|risk|mode]`, `[data-ux-primary-canvas=PAGE]`, `[data-ux-context-rail=PAGE]`, `[data-ux-evidence-drawer=PAGE]`, `[data-ux-primary-action=SCENARIO_ID]`.
- Safety/contract: `[data-safety-boundary]`, `[data-manual-gate=ACTION_ID]`, `[data-contract-marker=MARKER_ID]`.
- Charts: `[data-ux-chart]`, `[data-chart-title]`, `[data-chart-axis-x]`, `[data-chart-axis-y]`, `[data-chart-unit]`, `[data-chart-legend]`, `[data-chart-active-value]`, optional `[data-chart-threshold]`.
- Heatmaps: `[data-ux-heatmap]`, `[data-heatmap-axis-x]`, `[data-heatmap-axis-y]`, `[data-heatmap-scale]`, `[data-heatmap-cell]`, `[data-heatmap-selected-narrative]`.
- Backtest: `[data-backtest-step=select|edit|validate|gated-run|analyze]`, `[data-backtest-validation-status]`, `[data-backtest-diff-preview]`.
- Replay: `[data-replay-step=source|strategy|preview|manual-start|investigate]`, `[data-replay-playback-sticky]`, `[data-replay-selected-bar]`, `[data-replay-signal-log]`.

Script actions: navigate routes, capture requests/websockets, assert route identity/safety text, measure first-fold bounding boxes at all viewports, count same-weight panels, count tab stops to primary action, focus chart/heatmap and read active value, open evidence drawer and assert markers, save V2/V3 screenshots plus annotated contact sheet.

Scoring, 100 points:
- Task orientation, 20: task header first fold top <25 percent viewport with purpose/state/action/risk/mode; primary action visible without scroll; scenario steps complete; state proof for empty/loading/stale/error; tab stops to primary action <=8.
- Visual hierarchy, 15: no horizontal overflow; first fold <=1 primary canvas, <=1 task header, <=2 rails, <=4 secondary panels; <=5 same-weight panels; route/run/mode visible before and after scrollY=700; primary canvas >=35 percent first-fold content at 1440x900 and 1920x1080.
- Chart/heatmap readability, 15: main chart >=360x180; support chart >=260x120; charts have title/axes or exemption/unit/legend/active value; risk charts have threshold; heatmaps have axes/scale/selected cell/narrative >=40 chars; focus updates active value or aria-live.
- Workflow quality, 15: scripted step groups pass; Backtest requires select, edit, validate, gated run/preview, analyze; Replay requires source/date/symbol, strategy, preview, manual start gate, investigate.
- Cognitive load, 12: contract evidence drawer collapsed by default but DOM markers present; secondary panels not visually equal to primary canvas; internal endpoint terms preceded by human labels; repeated safety/provenance <=2 global blocks plus action-local gates.
- Safety hierarchy, 10: global six safety texts present; no forbidden DOM markers; no forbidden page-load requests; manual-gated actions have visible reason within 220 px; mode visible in task header/drawer.
- Accessibility/responsive, 8: primary actions/drawers keyboard reachable; focus indicator detectable; chart/heatmap active values textual; primary task path no horizontal scroll at all viewports.
- V2 preservation/evidence, 5: V2 loads V2 asset and not V3 asset; V3 loads V3 asset/no-store and not V2 asset; JSON/screenshots written; protected paths clean.

Hard failures cap V3 score at 69: V2 default broken, V3 not explicit, forbidden page-load mutating request, forbidden live/broker/account DOM marker, hidden production export marker, protected runtime path dirty, or progressive disclosure removes required marker from DOM.

V2 delta: compute same category scores for V2 and V3 per scenario/viewport. Missing V2 selector becomes `baseline_missing_selector` and may use text/geometry fallback only when observed. Final requires V3 >=90, no category <70, and mean V3-V2 delta >=15 for task orientation, chart/heatmap readability, workflow quality, and cognitive load.

Required JSON fields: schemaVersion, generatedAt, status, tranche, thresholds, viewports, routes, scenarios with steps/scores/network/screenshots/failures, categoryScores v2/v3/delta, totals v2/v3/delta, hardFailures, artifacts contactSheet and trace.

## Early storyboard proof
Condition storyboard: active run/state -> best candidate/risk -> evidence chart/active value -> code/diff preview -> human-gated export and audit separation.

Backtest storyboard before implementation: select strategy/data -> edit buy/sell condition -> validate with visible status -> review diff/variable helper -> manual-gated run/save with no POST `/bt/run`, `/bt/strategy/validate`, `/bt/strategy`, `/bt/strategy/delete` on load -> analyze result. Contract markers remain in `[data-ux-evidence-drawer=backtest]`.

Chart Replay storyboard before implementation: choose source/date/symbol -> choose strategy -> preview bars/signals -> see manual start gate with no `/sim/ws` on load -> inspect main candle chart, selected bar, synchronized signal log. Protocol markers remain in `[data-ux-evidence-drawer=replay]`.

## Preserved route, safety, and contract markers
Keep discoverable in DOM even inside drawers/tabs:
- Global safety: No Live Order, No Broker Login, No Account Trading, Research Only, Human Approval Gate, Append-Only Audit.
- Route identity: V2 loads `/ui/bundle/app.js`, not `/ui/remodel/src/app.js`; V3 loads `/ui/remodel/src/app.js`, not `/ui/bundle/app.js`; V3 no-store and distinct owner/header version.
- Page required text from compare gate: Condition BEST/WINNER, Human Approval, Strategy Inspector; Process Generation/Backtest/Scoring/Autopsy/Repeat; History Research Records/ResultDetail/Compare/Lineage; Lab Edge Ratio/variables/correlation/combinations/holdout; Workbench Hall of Fame/History Compare/Backtest Result Review/review queue; Audit Decision Audit/Append-Only/PROMOTE/OOS CI/ledger; Backtest REFERENCE mode/API Contract Matrix/parameters/optimize/WFO/sweep/editor/results/report; Replay data source/playback/replay chart `/sim/ws` manual gate/signal log.
- Backtest contract endpoints including `/bt/health`, strategies, validate, strategy save/delete, extract vars, data range, `/bt/run`, jobs, cancel, meta, ws job, portfolio plus manual-gated reasons.
- Replay contract endpoints/actions including `/sim/health`, days, demo, stocks, signals, `/sim/ws`, start/pause/resume/speed/seek/stop, meta/bars/history/done/error plus recovery text.

## File-level changes after approval
- Add `scripts/verify_dashboard_human_ux_rubric.py`.
- Update `ai_strategy_loop/dashboard/frontend/remodel/src/app.js` with stable selectors and task frame helpers; preserve route mapping, mode detection, inert reference/demo behavior, manual gates.
- Update `theme.css` for hierarchy, sticky task context, chart/heatmap readability, focus, drawers.
- Update `data.js` for storyboard copy, selected-cell explanations, validation diagnostics, replay labels, candidate narratives; no trading/account/broker data.
- Update remodel docs/checklists from inventory-only to thresholded task outcomes and preserved marker list.
- Add focused tests for selectors, markers, route/default identity, and forbidden actions.

## Sequencing and dependencies
0. Approval checkpoint: no implementation before explicit approval.
1. Tranche 0 rubric/storyboard/baseline: implement verifier, baseline, storyboards; run baseline in non-gating mode; architect/critic review.
2. Tranche 1 shared IA primitives: task frame helpers/selectors; verify route/safety and storyboard pages.
3. Tranche 2A Condition/Process/History: orientation, blocker diagnosis, find-inspect-compare; verify touched pages plus all-route safety/default.
4. Tranche 2B Lab/Workbench/Audit: heatmap narratives, selected candidate evidence, decision funnel; verify touched pages plus all-route safety/default.
5. Tranche 2C Backtest/Chart Replay: implement storyboard workflows; verify these pages before final pass.
6. Final review: focused tests, visual gate, V2/V3 compare, safety audit, human rubric final, diff check, protected path check, architect/critic review. Default switch remains out of scope.

## Per-tranche thresholds
- Tranche 0: valid JSON/artifacts; zero route/safety hard failures; Backtest/Replay storyboards validate. Baseline may fail final UX target.
- Tranche 1: no hard failures; affected V3 pages >=70, no category <50.
- Tranche 2A/2B: touched pages >=82, no category <60, no route/safety regression, V2 delta >=5 unless documented for final.
- Tranche 2C: Backtest and Replay >=86, no category <65, all storyboard steps demonstrated, no forbidden page-load POST/WS, manual gates within 220 px.
- Final: V3 total >=90, no category <70, mean V3-V2 delta >=15 for task orientation, visualization readability, workflow quality, and cognitive load; existing visual/compare/safety/focused tests pass.

## Verification commands after approval only
```powershell
python scripts/verify_dashboard_human_ux_rubric.py --v2-base-url http://127.0.0.1:8777 --v3-base-url http://127.0.0.1:8777 --out artifacts/dashboard-human-ux-v3/tranche-0-baseline --tranche baseline --viewports 1440x900,1920x1080,1280x720
python scripts/verify_dashboard_human_ux_rubric.py --v2-base-url http://127.0.0.1:8777 --v3-base-url http://127.0.0.1:8777 --out artifacts/dashboard-human-ux-v3/storyboard-check --tranche baseline --pages condition,backtest,chart_replay --storyboard artifacts/dashboard-human-ux-v3/storyboards/storyboards.json
python scripts/verify_dashboard_human_ux_rubric.py --v2-base-url http://127.0.0.1:8777 --v3-base-url http://127.0.0.1:8777 --out artifacts/dashboard-human-ux-v3/tranche-2c --tranche c --pages backtest,chart_replay --min-v3-score 86 --min-delta 5
python scripts/verify_dashboard_human_ux_rubric.py --v2-base-url http://127.0.0.1:8777 --v3-base-url http://127.0.0.1:8777 --out artifacts/dashboard-human-ux-v3/human-rubric-final --tranche final --min-v3-score 90 --min-delta 15
python -m pytest tests/unit/test_dashboard_remodel_static.py tests/unit/test_dashboard_route_parity.py tests/unit/dashboard -q
python scripts/verify_dashboard_remodel_visual_gate.py --base-url http://127.0.0.1:8777 --out artifacts/dashboard-human-ux-v3/visual-gate
python scripts/verify_dashboard_v2_v3_compare.py --v2-base-url http://127.0.0.1:8777 --v3-base-url http://127.0.0.1:8777 --out artifacts/dashboard-human-ux-v3/v2-v3-compare
python scripts/verify_dashboard_safety_audit.py --v2-base-url http://127.0.0.1:8777 --v3-base-url http://127.0.0.1:8777 --out artifacts/dashboard-human-ux-v3/safety-audit
git diff --check -- scripts/verify_dashboard_human_ux_rubric.py ai_strategy_loop/dashboard/frontend/remodel tests/unit/test_dashboard_remodel_static.py tests/unit/test_dashboard_route_parity.py tests/unit/dashboard
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

## Risks and mitigations
- Rubric becomes shallow: require scripted steps, geometry, keyboard, network, annotations, V2 delta.
- Drawers hide compliance: preserved marker list, `data-contract-marker`, drawer tests, hard cap.
- V2 default regresses: compare after every tranche.
- Backtest/Replay slip late: Tranche 0 storyboard and Tranche 2C thresholds.
- Expert detail lost: move detail to drawers/rails, do not delete.
- `app.js` churn: shared helpers first and page tranches.
- Unsafe live/backend calls: keep reference/demo inert, safe GET-only probes, manual gates, forbidden request hard caps.

## Handoff guidance
Executor starts with Tranche 0 only after approval. Architect reviews Tranche 0 and shared IA for route/safety/contract preservation. Critic reviews rubric loopholes and storyboard adequacy before page churn and final approval. Team only if tranches parallelize after rubric stability. Ultragoal only for a longer durable execution ledger.
