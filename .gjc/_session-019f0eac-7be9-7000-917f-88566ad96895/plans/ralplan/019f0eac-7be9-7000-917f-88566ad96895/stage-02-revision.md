# Ralplan Revision Stage 2 — V2/V3 dashboard selectable preview

## Summary
Planning-only revision for `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel` after Critic ITERATE. Preserve V2 as default, make V3 explicit preview only, correct visual verification, add machine-readable inventory gate, and split preview acceptance from promotion/100% acceptance.

Evidence inspected: prior planner/architect/critic artifacts, root and `ai_strategy_loop/AGENTS.md`, `ai_strategy_loop/dashboard/app.py`, V2/V3 index files, `scripts/verify_dashboard_remodel_visual_gate.py`, `tests/unit/test_dashboard_route_parity.py`, `tests/unit/test_dashboard_remodel_baseline_contract.py`, remodel `TAB_CHECKLIST.md` and `DATA_CONTRACT.md`. Current code has V2 `_dashboard_index_response()` and V3 `_dashboard_remodel_index_response()`, but canonical `/ui/evolution`, `/ui/evolution/{subtab}`, `/ui/backtest`, `/ui/chart-replay` currently serve V3. V2 title/assets: `STOM AI · 조건식 자율 진화 대시보드`, `/ui/bundle/app.js`, `/ui/bundle/stom-ui.js`. V3 title/assets: `STOM AI · 조건식 AI 연구 대시보드`, `/ui/remodel/styles/theme.css?v=20260628canonical`, `/ui/remodel/src/data.js?v=20260628canonical`, `/ui/remodel/src/app.js?v=20260628canonical`, no-store/no-cache HTML. Visual verifier requires `--out` and has no `--compare-base-url`.

## Updated RALPLAN-DR
Principle 3: V2 continuity beats rollout speed. Principle 4: V3 selection must be explicit, visible, reversible, and test-owned. Principle 5: stay local-only/research-only: no broker login, live order, account trading, operating DB cutover, hidden export, automatic final approval, or bypass of Human Approval Gate / Append-Only Audit.

Decision: refined Option A. Main 8770 profile is V2 default. V3 is available only through hard `/ui/remodel/*`, a one-response `?dashboard_version=v3` selector, or an explicit 8776 preview profile such as `STOM_DASHBOARD_DEFAULT_VERSION=v3`. Option B, separate-port-only preview, is rollback fallback. Option C, canonical V3 replacement, is rejected until inventory closure plus explicit later human approval.

## In scope / out of scope
In scope: route/version matrix, selector priority, visual compare artifact contract, inventory schema, acceptance split, test commands, execution work units, rollback. Out of scope: source edits, formatters, tests, browser runs, broker login, live order, account trading, `_database/` writes, hidden export, promotion.

## Fix 1 — route/version ownership matrix
Version rules: V2 means old title + `/ui/bundle/*` assets + no V3 asset by default. V3 means remodel title + `/ui/remodel/*20260628canonical` assets + no V2 bundle + no-store/no-cache HTML.

Selector priority for HTML UI routes only: 1 hard `/ui/remodel/*` allowlisted route selects V3; 2 explicit server preview profile selects V3 for canonical routes on 8776 only; 3 exactly `?dashboard_version=v3|v2` selects one response; 4 default V2. Do not implement localStorage, cookie, or session selection for preview acceptance. Alias redirects preserve only the accepted `dashboard_version` query.

Matrix rows, each requiring status/title/asset/cache/redirect tests and rollback to V2/default or feature-flag-off preview:
- `/`: root owner, redirect to `/ui/`; target V2 by default; preview profile/query may affect target only.
- `/ui/`: V2 shell root by default; query/profile may select V3; 200; V2 title/bundles/no-cache default.
- `/ui/evolution`: V2 Condition AI overview default; explicit V3 equivalent `/ui/remodel/condition` or query/profile.
- `/ui/evolution/process`: V2 process default; explicit V3 `/ui/remodel/process` or query/profile.
- `/ui/evolution/records`: V2 records/history default; explicit V3 `/ui/remodel/history` or `/ui/remodel/records`.
- `/ui/evolution/history`: legacy alias, 307/308 to `/ui/evolution/records`, preserve selector query.
- `/ui/evolution/lab`: V2 lab default; explicit V3 `/ui/remodel/lab`.
- `/ui/evolution/workbench`: V2 workbench/pro default; explicit V3 `/ui/remodel/workbench`.
- `/ui/evolution/verdict`: V2 verdict/audit default; explicit V3 `/ui/remodel/audit` or `/ui/remodel/verdict`.
- `/ui/evolution/{bad}`: no owner; 307/308 to `/ui/evolution`, no broad shell catchall.
- `/ui/backtest`: V2 backtest default; explicit V3 `/ui/remodel/backtest`.
- `/ui/chart-replay`: V2 chart replay default; explicit V3 `/ui/remodel/chart-replay`.
- Legacy aliases `/ui/process`, `/ui/records`, `/ui/history`, `/ui/lab`, `/ui/pro`, `/ui/verdict`, `/ui/simulation`: redirect respectively to process, records, records, lab, workbench, verdict, chart-replay; preserve selector query; no shell body.
- Unknown `/ui/*`: 404, no V2/V3 shell.
- `/ui/remodel/`: V3 preview root; 200 or explicit 307 to `/ui/remodel/condition`, tested.
- `/ui/remodel/condition`, `/ui/remodel/evolution`, `/ui/remodel/process`, `/ui/remodel/history`, `/ui/remodel/records`, `/ui/remodel/lab`, `/ui/remodel/workbench`, `/ui/remodel/audit`, `/ui/remodel/verdict`, `/ui/remodel/backtest`, `/ui/remodel/chart-replay`, `/ui/remodel/simulation`, `/ui/remodel/settings`: hard V3 allowlist, V3 title/assets/no-store, 200, no V2 bundle; aliases may normalize client state but must be route-tested.
- `/ui/remodel/remodel-bootstrap.js`: V3 JavaScript asset, 200 if file exists, 404 if missing, never an HTML shell.
- `/ui/remodel/{bad}`: 404, not redirect, to avoid masking broken V3 routes.

Test ownership: `tests/unit/test_dashboard_route_parity.py` owns matrix, aliases, selectors, cache, 404s. `tests/unit/test_dashboard_remodel_baseline_contract.py` keeps hard-remodel assertions and moves current canonical-V3 assertions to explicit selector/profile coverage.

## Fix 2 — visual verification
Required command correction: include `--out`; compare target is 8776 V3 against 8770 V2; do not use unsupported `--compare-base-url`.

Implementation contract: extend `scripts/verify_dashboard_remodel_visual_gate.py` or add `scripts/verify_dashboard_v2_v3_compare.py` accepting `--v2-base-url`, `--v3-base-url`, and required `--out`. Required artifacts: `route-version-matrix.json`, `v2-captures/*`, `v2-dom/*`, `v3-captures/*`, `v3-dom/*`, `v2-v3-contact-sheet.png`, `compare-scorecard.json`, `forbidden-network-scan.json`. Scorecard must include base URLs, route IDs, titles, assets, cache headers, redirects/404s, console/page errors, and all network requests. Existing single-base visual gate remains V3 reference/safety evidence only, not parity proof.

Future commands:
`python scripts/verify_dashboard_remodel_visual_gate.py --base-url http://127.0.0.1:8776 --out artifacts/dashboard-v3-visual-20260628 --min-page-score 95 --min-average-score 97`
`python scripts/verify_dashboard_v2_v3_compare.py --v2-base-url http://127.0.0.1:8770 --v3-base-url http://127.0.0.1:8776 --out artifacts/dashboard-v2-v3-compare-20260628 --min-page-score 95 --min-average-score 97`

## Fix 3 — inventory/evidence schema
Before any 100% or promotion claim, generate `artifacts/dashboard-v2-v3-inventory/v2-v3-inventory.json` and optionally commit a schema under remodel docs. Top-level fields: `schema_version=dashboard-v2-v3-inventory.v1`, `generated_at`, `route_matrix_sha256`, `source_revision`, `items`, `failures`, `status`.

Each item requires: `id`, `stable_id` (`dash.<page>.<type>.<slug>.v1`), `page`, `route`, `item_type` (`route|section|button|form|modal|function|api_endpoint|data_field|network_call|asset|cache_policy`), `label`, `owner`, `source_refs`, `dom_selectors`, `button_action_endpoint` (`method`, `endpoint`, `trigger`, `auto_on_load`), `safety` (`classification=read_only_local|manual_mutation_gate|append_only_audit|export_boundary|fixture_only|forbidden`, `local_only`, `research_only`, `human_gate_required`, allowed/forbidden network), `v2.status/evidence`, `v3.status/evidence`, `parity.status`, `missing_or_changed_reason`, `failure_rules`, `closure_evidence`, `notes`.

Stable examples: `dash.condition.button.start_stop.v1`, `dash.audit.section.append_only_ledger.v1`, `dash.backtest.api.run.manual_gate.v1`, `dash.chart_replay.ws.sim_ws.manual_gate.v1`. Fail preview if default V2 disappears, canonical V3 appears without selector/profile, or forbidden action/network appears. Fail promotion if any V2-present item is V3 missing without acceptable reason and closure evidence; any item is unsafe, fixture-only, auto-mutating on load, blocked by unknown API, non-local, or missing Human Approval Gate / Append-Only Audit evidence.

## Fix 4 — split acceptance
Selectable-preview acceptance: 8770 canonical routes default to V2; V3 reachable only by `/ui/remodel/*`, one-response `?dashboard_version=v3`, or explicit 8776 preview profile; no persistent selector; all matrix routes asserted; current V3-on-canonical tests inverted or relocated; V3 preview is visibly local-only/research-only; source/DOM/network scans show no broker login, live order, account trading, automatic final approval, hidden export; `/bt/*` mutations, `/bt/ws_job`, and `/sim/ws` are not invoked on load; audit and export are separated; visual commands include `--out`; compare artifact proves 8776 V3 vs 8770 V2. This does not authorize canonical V3 replacement or 100% parity.

Promotion/100% acceptance: all preview criteria plus inventory PASS, append-only audit persistence proof, export separation proof, local/read-only API evidence, forbidden-network scan PASS, zero fixture-only/unexplained-missing/unsafe/auto-mutating blockers, and explicit later human approval.

## File-level changes for approved execution
- `ai_strategy_loop/dashboard/app.py`: route/version manifest, selector helper, V2 default canonical routes, hard V3 remodel allowlist, invalid remodel 404, alias query preservation.
- `ai_strategy_loop/__main__.py` or `stom_dashboard.bat`: optional explicit preview-profile flag/env for 8776; default remains 8770/V2.
- V2 frontend: passive V3 preview link/badge only; keep V2 title/assets/functions.
- V3 frontend: preserve no-store HTML, cache-busted assets, safety cues, manual gates, fixture/live provenance, no automatic trading/export.
- Tests: invert canonical-V3 expectations in route parity and baseline contract; add matrix, selector, cache, alias, unknown-route, preview-profile coverage.
- Visual/inventory scripts: add two-base compare support and inventory gate.

## Sequencing and work units
1 Route contract first: Executor A implements manifest, selector/profile, aliases, 404/cache tests. 2 Test inversion: Executor B moves V3 canonical assertions to explicit selector/profile tests. 3 Selector UI: minimal non-persistent V2 preview link. 4 Visual tooling: Executor C adds 8770/8776 compare artifacts and corrected docs. 5 Inventory: Executor D generates stable-ID inventory and gate. 6 Safety: Executor E proves append-only audit, export separation, local/read-only APIs, forbidden-network scan. Architect review after route+visual+inventory foundations; Critic review before promotion or 100% claim; Team/ultragoal only after execution approval for parallel/durable closure.

## Verification commands after approval
`python -m pytest tests/unit/test_dashboard_route_parity.py tests/unit/test_dashboard_remodel_baseline_contract.py tests/unit/test_dashboard_remodel_static.py tests/unit/dashboard/test_dashboard_ui_remodel.py -q`
`python -m py_compile ai_strategy_loop/dashboard/app.py`
`node --check ai_strategy_loop/dashboard/frontend/remodel/src/app.js`
`python scripts/verify_dashboard_remodel_visual_gate.py --base-url http://127.0.0.1:8776 --out artifacts/dashboard-v3-visual-20260628 --min-page-score 95 --min-average-score 97`
`python scripts/verify_dashboard_v2_v3_compare.py --v2-base-url http://127.0.0.1:8770 --v3-base-url http://127.0.0.1:8776 --out artifacts/dashboard-v2-v3-compare-20260628 --min-page-score 95 --min-average-score 97`
`python scripts/verify_dashboard_inventory_gate.py --inventory artifacts/dashboard-v2-v3-inventory/v2-v3-inventory.json --route-matrix artifacts/dashboard-v2-v3-compare-20260628/route-version-matrix.json --out artifacts/dashboard-v2-v3-inventory/gate-result.json`
`git diff --check`

## Risks, mitigations, rollback
Risks: accidental V3 default, catchall masking, visual-only false parity, fixture data mistaken as live, audit/export/trading drift, cache contamination. Mitigations: V2 default tests, explicit selector priority, allowlisted routes, stable-ID inventory, provenance/failure rules, forbidden-network scan, manual gates, distinct asset/cache assertions. Rollback: force/default V2 profile, remove V3 preview link, keep `/ui/remodel/*` hard preview only or feature-flag it off, verify canonical V2 title/assets and no V3 assets, fall back to separate-port-only preview until all route, visual, inventory, and safety artifacts pass.

## Persistence note
Optional planner/fallback metadata flags were attempted and rejected in this restricted session. Persisted without those optional flags for planner id `61-DashboardV3Plan`, fallback reason `not_found`, attempted id `61-DashboardV3Plan`, fallback stage 2.
