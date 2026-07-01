# Pending Approval Plan: STOM Dashboard V2/V3 Selectable 100% Rollout

Status: pending approval
Mode: RALPLAN deliberate consensus
Worktree: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel`
V2 baseline: `http://127.0.0.1:8770/`
V3 preview: `http://127.0.0.1:8776/`

## Decision / ADR
Adopt refined Option A: preserve V2 as the default dashboard contract and expose V3 only as an explicit selectable preview until inventory, visual, API, and safety gates prove complete parity/improvement.

Drivers: V2 continuity, reversible V3 selection, evidence-backed 100% claims, local-only/research-only safety. Rejected: separate-port-only as insufficient for selectability; immediate canonical V3 replacement as premature; static fixture-only V3 as insufficient for production function depth.

## Consensus receipts
- Planner 1: `.gjc/_session-019f0e61-4f56-7000-ba53-f9da5065b2d4/plans/ralplan/019f0e61-4f56-7000-ba53-f9da5065b2d4/stage-01-planner.md`
- Architect 1: WATCH/COMMENT `.gjc/_session-019f0ea5-5f6a-7000-b167-2c85a73d3635/plans/ralplan/019f0ea5-5f6a-7000-b167-2c85a73d3635/stage-01-architect.md`
- Critic 1: ITERATE `.gjc/_session-019f0ea7-9e18-7000-881d-3241fa26473c/plans/ralplan/019f0ea7-9e18-7000-881d-3241fa26473c/stage-01-critic.md`
- Revision 2: `.gjc/_session-019f0eac-7be9-7000-917f-88566ad96895/plans/ralplan/019f0eac-7be9-7000-917f-88566ad96895/stage-02-revision.md`
- Architect 2: CLEAR/CLEAR/WATCH APPROVE `.gjc/_session-019f0eb6-7d81-7000-994a-89b836acf055/plans/ralplan/019f0eb6-7d81-7000-994a-89b836acf055/stage-02-architect.md`
- Critic 2: OKAY `.gjc/_session-019f0ebb-e7bc-7000-bfa4-ae08e079c9e3/plans/ralplan/019f0ebb-e7bc-7000-bfa4-ae08e079c9e3/stage-02-critic.md`

## Current route facts
8770 serves V2 on `/`, `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`; `/ui/remodel/*` is 404. 8776 serves V3/remodel on canonical and `/ui/remodel/*` routes with `/ui/remodel/src/app.js?v=20260628canonical`, no V2 bundle, and no-cache HTML; 8776 root still serves the old shell. Recent focused checks passed after local route fixes: 28 route/remodel tests, py_compile, node check, git diff check.

## Route/version ownership matrix
V2 = old title `STOM AI · 조건식 자율 진화 대시보드`, V2 bundle assets, no V3 assets by default. V3 = title `STOM AI · 조건식 AI 연구 대시보드`, `/ui/remodel/*20260628canonical`, no V2 bundle, no-store/no-cache HTML.

Selector priority for approved execution: hard `/ui/remodel/*` selects V3; explicit preview profile may select V3 on canonical routes; exact `?dashboard_version=v3|v2` selects one response only; otherwise V2 default. No localStorage/cookie/session selection for preview acceptance.

Coverage: V2 default for `/`, `/ui/`, `/ui/evolution`, `/ui/evolution/process`, `/ui/evolution/records`, `/ui/evolution/lab`, `/ui/evolution/workbench`, `/ui/evolution/verdict`, `/ui/backtest`, `/ui/chart-replay`. Legacy aliases redirect and preserve selector query. V3 preview for `/ui/remodel/condition`, `process`, `history`, `records`, `lab`, `workbench`, `audit`, `verdict`, `backtest`, `chart-replay`, `simulation`, `settings`. Unknown `/ui/*` and `/ui/remodel/*` must not mask broken routes with a shell.

## Machine-readable inventory gate
Before any 100% or promotion claim, generate `artifacts/dashboard-v2-v3-inventory/v2-v3-inventory.json` with stable IDs for every route, section, button, form, modal, function, API endpoint, data field, network call, asset, and cache policy. Required fields include stable_id, page, route, item_type, label, owner, source_refs, dom_selectors, endpoint/action, safety classification, v2/v3 evidence, parity status, failure rules, and closure evidence.

Examples: `dash.condition.button.start_stop.v1`, `dash.audit.section.append_only_ledger.v1`, `dash.backtest.api.run.manual_gate.v1`, `dash.chart_replay.ws.sim_ws.manual_gate.v1`.

## V3 page checklist
1. Condition AI: shell/status tabs, live generation, active strategy, phase timeline/detail, criteria/glossary/config/engine/cost/charts, HoF, generation table, inspector, approval/export separation.
2. Process: selector/menu, governance, generation->backtest->scoring->autopsy map, KPIs, logs, catalogs, boundary metadata.
3. History/Records: archive, filters/sort/windowing, research records, ResultDetail, Compare, lineage search, export status.
4. Lab: active runs, warnings, queue, Edge Ratio, variables, correlation, combinations, holdout, data quality, visual quality.
5. Workbench: candidates, HoF, heatmap, equity/IC/risk charts, metrics, exposure, evidence notes, review queue, no approval/export authority.
6. Decision Audit: append-only ledger, PROMOTE checklist, OOS CI, alerts, regime/revival/V6/M4, decision form, note validation, audit metadata.
7. Backtest: `/bt/*` matrix, strategy selectors/editor, dates, WFO, sweep/self.vars, jobs/logs, results, compare, portfolio, reports; mutations manual-gated.
8. Chart Replay: `/sim/*` and WS matrix, days/stocks/strategies/signals, playback controls, chart modes/layout, indicators, logs, minimap; `/sim/ws` manual-gated.

## Acceptance split
Selectable-preview acceptance: 8770 canonical routes default to V2; V3 reachable only by `/ui/remodel/*`, one-response selector, or explicit 8776 preview profile; route matrix passes; V3 visibly local-only/research-only; no broker login/live order/account trading/hidden export/automatic final approval; `/bt/*` mutations, `/bt/ws_job`, `/sim/ws` not invoked on load; visual commands include `--out`; 8770 V2 vs 8776 V3 compare artifacts exist.

Promotion/100% acceptance: all preview criteria plus stable-ID inventory PASS, append-only audit persistence proof, export separation proof, local/read-only API evidence, forbidden-network scan PASS, zero fixture-only/unexplained-missing/unsafe/auto-mutating blockers, and explicit later human approval.

## Verification commands after approval
```powershell
python -m pytest tests/unit/test_dashboard_route_parity.py tests/unit/test_dashboard_remodel_baseline_contract.py tests/unit/test_dashboard_remodel_static.py tests/unit/dashboard/test_dashboard_ui_remodel.py -q
python -m py_compile ai_strategy_loop/dashboard/app.py
node --check ai_strategy_loop/dashboard/frontend/remodel/src/app.js
python scripts/verify_dashboard_remodel_visual_gate.py --base-url http://127.0.0.1:8776 --out artifacts/dashboard-v3-visual-20260628 --min-page-score 95 --min-average-score 97
python scripts/verify_dashboard_v2_v3_compare.py --v2-base-url http://127.0.0.1:8770 --v3-base-url http://127.0.0.1:8776 --out artifacts/dashboard-v2-v3-compare-20260628 --min-page-score 95 --min-average-score 97
python scripts/verify_dashboard_inventory_gate.py --inventory artifacts/dashboard-v2-v3-inventory/v2-v3-inventory.json --route-matrix artifacts/dashboard-v2-v3-compare-20260628/route-version-matrix.json --out artifacts/dashboard-v2-v3-inventory/gate-result.json
git diff --check
```

## Approved-execution work units
1. Route selector/manifest and tests. 2. Test inversion from canonical V3 to V2 default + explicit V3. 3. Passive V3 preview link/badge in V2. 4. Two-base V2/V3 visual/DOM compare script. 5. Stable-ID inventory gate. 6. Safety/evidence gate for audit/export/local APIs/forbidden network/manual gates. 7. Architect review and executor QA/red-team.

## Intent Reconciliation
Open confirmations: V2 remains default until promotion approval; V3 selector is preview-only/non-persistent; 100% means inventory plus evidence; V3 can improve layout if V2 functions are preserved/superseded/out-of-scope with evidence; no trading/export/broker/account boundary crossing is allowed.

## Final status
Critic stage 2 returned OKAY with no blockers. This plan is pending approval only. No implementation, commit, PR, or execution-skill handoff has been performed by this Ralplan step.
