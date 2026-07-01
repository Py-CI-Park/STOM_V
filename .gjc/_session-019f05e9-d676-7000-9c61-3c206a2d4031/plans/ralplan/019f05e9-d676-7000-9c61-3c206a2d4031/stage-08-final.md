# Pending Approval Plan: V3 Dashboard Human UX/UI Maturity Redesign

Status: PENDING APPROVAL. This is a planning artifact only. No product source was mutated in this Ralplan phase.

## Decision
Adopt Option B: a task-first information-architecture redesign of the explicit V3 remodel, starting with a mandatory Tranche 0 human UX rubric/storyboard baseline before any UI churn. Preserve V2 as the default baseline. V3 remains explicit/selectable via `/ui/remodel/*` or `dashboard_version=v3` until a separate default-cutover approval.

The previous V3 100/100 package is treated as a safety/evidence success, not as proof of human-centered UX superiority. The next execution must add a falsifiable human UX gate and then redesign V3 around user task completion: Backtest condition editing, Chart Replay investigation, chart readability, heatmap information design, visual hierarchy, and cognitive-load reduction.

## Why the previous 100/100 missed the issue
The prior gate rewarded route ownership, required text, safety labels, nonblank screenshots, inventory coverage, and absence of hidden mutating traffic. It did not prove first-fold comprehension, scripted human task success, chart interpretation, guided Backtest editing, guided Replay investigation, or measurable V3 delta over V2. As a result, V3 could pass as safe and evidence-rich while still feeling less natural than V2.

## Drivers
1. Human usability must be measured before changing UI: V3 wins only by scripted V2 delta, not by widget count or safety text volume.
2. V2/default and safety constraints are tranche invariants: no default cutover, no live order, no broker login, no account trading, no hidden production export, no protected runtime writes, no unapproved mutating calls.
3. Backtest and Chart Replay are the highest-risk UX pages and require early storyboard proof before broad redesign.
4. Safety/provenance/contract evidence must remain discoverable, but should not dominate the primary task flow.
5. The redesign must stay bounded in the current no-new-framework remodel surface unless separately approved.

## Alternatives considered
| Option | Decision | Reason |
|---|---|---|
| A. Conservative polish | Fallback only | Lowest regression risk, but cannot prove human task success or V3-over-V2 superiority unless Tranche 0 shows small polish reaches thresholds. |
| B. Task-first IA + Tranche 0 rubric baseline | Chosen | Measures the actual UX gap before page churn, preserves safety hard caps, and targets the user complaints directly. |
| C. Full component-system rebuild | Deferred | Could improve long-term modularity but is too broad and risky for this maturity pass. |

## ADR
### Decision
Use a staged, measurable V3 maturity effort. Execution starts with Tranche 0 only, creating the human UX verifier, baseline captures, and machine-checkable storyboards. Subsequent tranches redesign shared IA and pages only after the rubric can prove improvement over V2.

### Consequences
- V2 stays default throughout this plan.
- V3 remains explicit/selectable and must preserve route identity and no-store remodel assets.
- Contract matrices may move into drawers/progressive disclosure, but DOM markers and manual-gate assertions remain hard requirements.
- The final claim changes from “has all required evidence text” to “beats V2 on scripted task orientation, visualization readability, workflow quality, and cognitive load.”

### Follow-ups
- Execute via Ultragoal or Team only after explicit approval.
- First approved slice must be Tranche 0 only.
- Architect/Critic review Tranche 0 before product UI churn.

## Consensus receipts
- Planner revision stage 2: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f1675-7246-7000-9215-83dbd4af3e27/plans/ralplan/019f1675-7246-7000-9215-83dbd4af3e27/stage-02-revision.md` (`df0ec3d4f896e14df142a3b6848528b91c3d6e284d3f73f051a460ba351f2038`)
- Architect pass 2: CLEAR / APPROVE, `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f168b-47cf-7000-8d83-1d60ad03b83b/plans/ralplan/019f168b-47cf-7000-8d83-1d60ad03b83b/stage-02-architect.md` (`9f5cf176581a5f8a2ab40cf93c8fcc1ca42f0bf9f963e39a6dc3faac5935578f`)
- Critic pass 2: OKAY / APPROVE, `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f1690-a156-7000-833d-8e88881958a1/plans/ralplan/019f1690-a156-7000-833d-8e88881958a1/stage-02-critic.md` (`385721c2d5115cd1281754b04055b45588e3e8e993f474742da5835e12ea4436`)
- Intent reconciliation: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/plans/ralplan/019f05e9-d676-7000-9c61-3c206a2d4031/stage-07-post-interview.md` (`6164d6b93c02d3857f0d0fe252d032b922975e4603eef3a74d78cad8eedaaea2`)

## Current page deficiencies to address
| Page | Deficiency | Required maturity outcome |
|---|---|---|
| Condition | Dense cards and small chart cards compete with task meaning. | First-fold task header, primary run/candidate canvas, large readable primary charts, export/audit separation. |
| Process | Strongest V3 page, but still must avoid equal-weight evidence clutter. | Keep payload-driven cockpit while applying task-frame selectors and progressive evidence drawer. |
| History | Richer than V2 but can become comparison clutter. | Find/inspect/compare flow with one primary comparison canvas and visible lineage/provenance. |
| Lab | Heatmaps are small; some values hidden; tiny text and panel count are high. | Large heatmap with axes, scale, selectable cell, narrative, tooltip/active value, and clear holdout interpretation. |
| Workbench | Candidate/evidence cards lack clear priority. | Candidate-selection funnel, primary candidate comparison, review handoff, and evidence drawer. |
| Audit | Good audit semantics, but heavy for general users. | Keep as audit-specialized page with clear decision funnel and append-only evidence. |
| Backtest | V2 has large condition editors; V3 pushes editing below contract matrix and has no textarea/editor parity. | Backtest first fold must show strategy selection, large buy/sell editor or code panes, validation status, gated run/preview, and result path. |
| Chart Replay | V2 quick-start/playback/timeline is more intuitive; V3 leads with API/WS matrix. | Replay first fold must show source/date/symbol, strategy, preview, sticky playback/timeline, main candle chart, selected bar, and synchronized signal log. |

## Human-centered 100-point rubric
Final verifier command shape:
```powershell
python scripts/verify_dashboard_human_ux_rubric.py --v2-base-url http://127.0.0.1:8777 --v3-base-url http://127.0.0.1:8777 --out artifacts/dashboard-human-ux-v3/human-rubric-final --tranche final --min-v3-score 90 --min-delta 15
```

Categories:
| Category | Points | Falsifiable checks |
|---|---:|---|
| Task orientation | 20 | Task header appears in first-fold top <25%; purpose/state/action/risk/mode visible; primary action visible without scroll; scenario steps complete; tab stops to primary action <=8. |
| Visual hierarchy | 15 | No horizontal overflow; first fold has <=1 primary canvas, <=1 task header, <=2 rails, <=4 secondary panels, <=5 same-weight panels; primary canvas >=35% first-fold content. |
| Chart/heatmap readability | 15 | Main chart >=360x180; support chart >=260x120; title/axes/unit/legend/active value; risk threshold where relevant; heatmap axes/scale/selected narrative >=40 chars; focus updates text. |
| Workflow quality | 15 | Backtest select/edit/validate/gated-run/analyze passes; Replay source/date/symbol/strategy/preview/manual-start/investigate passes. |
| Cognitive load | 12 | Contract evidence drawer collapsed by default but markers present; endpoint terms preceded by human labels; repeated safety/provenance <=2 global blocks plus action-local gates. |
| Safety hierarchy | 10 | Six safety texts present; no forbidden DOM/network; manual-gate reason within 220px; mode visible in task header/drawer. |
| Accessibility/responsive | 8 | Keyboard reachable primary path/drawers; detectable focus; textual chart/heatmap active values; no primary-path horizontal scroll at 1440x900, 1920x1080, 1280x720. |
| V2 preservation/evidence | 5 | V2 loads V2 asset and not V3; V3 loads V3/no-store and not V2; JSON/screenshots written; protected paths clean. |

Hard failures cap V3 score at 69: V2 default broken, V3 not explicit, forbidden page-load mutating request, forbidden live/broker/account DOM marker, hidden production export marker, protected runtime path dirty, or progressive disclosure removes required DOM markers.

Final target: V3 total >=90, no category <70, and mean V3-V2 delta >=15 for task orientation, chart/heatmap readability, workflow quality, and cognitive load. Approval-time open confirmation: user may raise this threshold if they require literal 100/100 final score on the new rubric.

## Required selector contracts
- Task frame: `[data-ux-task-header=PAGE]`, `[data-ux-field=purpose|state|primary-action|risk|mode]`, `[data-ux-primary-canvas=PAGE]`, `[data-ux-context-rail=PAGE]`, `[data-ux-evidence-drawer=PAGE]`, `[data-ux-primary-action=SCENARIO_ID]`.
- Safety/contract: `[data-safety-boundary]`, `[data-manual-gate=ACTION_ID]`, `[data-contract-marker=MARKER_ID]`.
- Charts: `[data-ux-chart]`, `[data-chart-title]`, `[data-chart-axis-x]`, `[data-chart-axis-y]`, `[data-chart-unit]`, `[data-chart-legend]`, `[data-chart-active-value]`, optional `[data-chart-threshold]`.
- Heatmaps: `[data-ux-heatmap]`, `[data-heatmap-axis-x]`, `[data-heatmap-axis-y]`, `[data-heatmap-scale]`, `[data-heatmap-cell]`, `[data-heatmap-selected-narrative]`.
- Backtest: `[data-backtest-step=select|edit|validate|gated-run|analyze]`, `[data-backtest-validation-status]`, `[data-backtest-diff-preview]`.
- Replay: `[data-replay-step=source|strategy|preview|manual-start|investigate]`, `[data-replay-playback-sticky]`, `[data-replay-selected-bar]`, `[data-replay-signal-log]`.

## Sequencing after approval
| Tranche | Scope | Exit criteria |
|---|---|---|
| 0 | Add human UX verifier; capture current V2/current V3 baseline; create machine-checkable Condition/Backtest/Replay storyboards; document selector/marker preservation. | Valid JSON/contact sheet/storyboards; zero route/safety hard failures; Backtest/Replay storyboards map steps to selectors/safety/rubric observations. |
| 1 | Shared IA primitives: task frame helpers, selectors, compact global safety strip, evidence drawer pattern. | No hard failures; affected V3 pages >=70; no category <50; route/default/safety tests pass. |
| 2A | Condition, Process, History. | Touched pages >=82; no category <60; no route/safety regression; V2 delta >=5 unless documented for final. |
| 2B | Lab, Workbench, Audit. | Heatmap/candidate/decision flows pass touched-page thresholds and preserve safety/contract markers. |
| 2C | Backtest and Chart Replay. | Backtest/Replay >=86; no category <65; storyboard steps demonstrated; no forbidden page-load POST/WS; manual gates within 220px. |
| Final | Full evidence pass. | V3 >=90, no category <70, mean V3-V2 delta >=15 in named categories; existing dashboard tests, visual gate, V2/V3 compare, safety audit, diff check, and protected-path check pass. |

## File-level work after approval
- Add `scripts/verify_dashboard_human_ux_rubric.py`.
- Update `ai_strategy_loop/dashboard/frontend/remodel/src/app.js` with task-frame helpers/selectors and task-first Backtest/Replay/Lab/Condition layouts while preserving route mapping, mode detection, inert reference/demo behavior, and manual gates.
- Update `ai_strategy_loop/dashboard/frontend/remodel/styles/theme.css` for hierarchy, sticky task context, larger chart/heatmap readability, focus states, and drawers.
- Update `ai_strategy_loop/dashboard/frontend/remodel/src/data.js` for storyboard copy, selected-cell explanations, validation diagnostics, replay labels, candidate narratives, with no trading/account/broker data.
- Update docs/checklists from inventory-only to thresholded task outcomes and preserved marker list.
- Add focused unit/static tests for selectors, markers, route/default identity, forbidden actions, and rubric fixtures.

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

## Intent Reconciliation
Open confirmations pending because this Ralplan ran automated:
1. V2 remains default and V3 remains explicit/selectable until separate default-cutover approval.
2. Execution starts with Tranche 0 only before UI churn.
3. The new human-centered rubric complements existing safety/route/visual gates.
4. Contract/safety/provenance detail can move into drawers only if required DOM markers remain discoverable and hard-fail if missing.
5. Backtest and Chart Replay are first high-risk UX pages after Tranche 0.
6. Final human-rubric threshold is proposed as V3 >=90, no category <70, and mean V3-V2 delta >=15 in named categories; user may raise to literal 100/100 at approval time.
7. Default switch, live trading, broker login, account trading, hidden production export, protected writes, and unapproved mutating calls remain out of scope.

Prior-context conflict check: no deep-interview specs were found. The plan is consistent with the original V3 rebuild constraints and refines the original 100/100 gate by adding human task success and V2 delta checks.

## Approval gate
This plan is pending approval. No implementation, source mutation, execution skill handoff, or worker delegation is authorized until the user explicitly approves execution.
