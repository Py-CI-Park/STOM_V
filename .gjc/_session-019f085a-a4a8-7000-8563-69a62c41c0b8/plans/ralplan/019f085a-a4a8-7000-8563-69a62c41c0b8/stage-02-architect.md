## Summary
Planner revision pass 2 is architecturally sound for Critic pass 2. It closes the prior WATCH concerns by converting route namespace and deep-linking, build/bootstrap drift, final_approval/export safety, CSS token scoping, and behavior E2E coverage into non-negotiable gates with acceptance evidence.

The hybrid remodel-shell direction remains the right tradeoff because the inspected production React/FastAPI dashboard owns the real /bt/*, /sim/*, condition, audit, and WebSocket behavior, while the current /ui/remodel/ preview is still a static/no-build shell with partial live bridge. No product files were edited and no tests, builds, formatters, or project verification gates were run.

## Analysis
Stage 1 found five architectural risks: remodel route escape, stale or parallel bundle bootstrap, unsafe inheritance of the production final_approval export path, global CSS bleed, and insufficient behavior E2E gates. Revision 2 addresses them directly:

- Route ownership: stage-02-revision.md adds Gate A for /ui/remodel/ as the replacement namespace, explicit remodel subpage/deep-link refresh expectations, no route escape to /ui/evolution, /ui/backtest, /ui/chart-replay, and preserved canonical-route tests/screenshots.
- Build/bootstrap: Gate B requires /ui/remodel/ to bootstrap the production React component graph or shared entry, forbids the vanilla remodel/src/app.js renderer as an accepted production renderer, and requires a manifest/hash or equivalent drift guard.
- Safety/export: Gate C keeps final_approval as human approval only, separates /record_decision append-only audit governance from export approval, forbids hidden export/broker/account/live-order controls, and requires source plus DOM guards.
- CSS scoping: Gate D requires a scoped token bridge over existing styles.css, remodel-root scoping, before/after preserved-route screenshots, and failure on unapproved canonical-route layout drift.
- E2E evidence: Gate E enumerates preserved routes, /bt/*, /sim/*, condition WS/inspector, audit append/refresh, and DOM safety coverage.

File-backed evidence confirms those gates target the real seams:

- Backend route preservation currently exists: ai_strategy_loop/dashboard/app.py:2694-2711 serves /ui/evolution, /ui/backtest, and /ui/chart-replay; app.py:3405-3414 mounts /ui/remodel before /ui.
- The existing production route contract is canonical-route biased: frontend/ui-contract.jsx:65-116 maps tabs to /ui/evolution, /ui/backtest, and /ui/chart-replay; frontend/app.jsx:139-149 pushes/replaces those paths and app.jsx:180-185 canonicalizes on load. Gate A is therefore necessary and now explicit.
- The current remodel preview is not a production replacement: frontend/remodel/index.html:8-14 loads styles/theme.css, src/data.js, and src/app.js; frontend/remodel/src/app.js:1-6 reads window.STOM_DATA; app.js:342-407 only bridges /health, /status, /runs, and /ws with preview fallback behavior. Gate B correctly blocks this renderer from being accepted as production.
- The production build already has a single served-bundle model and manifest/hash machinery: webui-build/build-app.mjs:1-19 documents bundle-only output, build-app.mjs:45-58 builds frontend/bundle/app.js, and build-app.mjs:75-130 injects content hashes plus manifest.json. Gate B aligns with this existing architecture.
- Export safety is a real boundary: app.py:3419-3464 handles WebSocket final_approval by calling export_winner to the production strategy DB after human-gated fields are provided. Gate C now makes that explicit and prevents hidden remodel paths.
- Append-only audit is separate in source: app.py:2434-2452 defines _record_decision governance behavior and app.py:2948-2952 exposes /record_decision. Revision 2 keeps that separate from export approval.
- CSS bleed risk is real: production frontend/styles.css:1-80 defines --bg-*, --line-*, and --ink-*; remodel frontend/remodel/styles/theme.css:1-80 defines --bg, --panel, --border, --text plus global :root, body, button, and input rules. Gate D root scoping and preserved-route screenshots close the prior WATCH concern.
- Production behavior reuse is justified: frontend/app.jsx:23-25 imports BacktestTab and SimulationTab, app.jsx:359-366 mounts them, bt-tab-root.jsx:111-112 consumes /bt/health, and sim-tab-root.jsx:76-77,196-198 consumes /sim/health and /sim/ws; backtest_api.py:252-1969 and simulation_api.py:127-683 expose the API/WS surfaces. This supports the hybrid shell rather than a greenfield rewrite.
- The 2026-06-27 scorecard and parity assessment document the current gap: docs/update_log/2026-06-27_dashboard_remodel_detailed_100_point_scorecard.md rates current parity at about 55/100 and standalone completeness at about 71/100, while docs/update_log/2026-06-27_dashboard_remodel_parity_assessment.md identifies the current state as Phase A visual preview with static /bt/* and /sim/* gaps.

Spec compliance: Revision 2 stays inside the requested planning-only lane, preserves existing routes and safety constraints, avoids product edits, and does not propose tests/builds during planning. It does not add unrelated broker/account/live-trading behavior and does not promote /ui/remodel/ over canonical routes before evidence gates pass.

Architecture: The plan now makes the adapter seams first-class: route adapter, shared bootstrap, bundle drift guard, CSS token bridge, and export/audit guard. That is the right architectural control point for replacing a static remodel preview with a production-backed shell.

## Root Cause
The root architectural risk was not the hybrid direction; it was the seam between a production dashboard that assumes /ui/*, a single hashed React bundle, broad global CSS, and an explicit production export action, versus a static /ui/remodel/ prototype that uses dummy data and separate styling. Revision 2 repairs the plan by making those seams non-negotiable gates instead of leaving them as executor discretion.

## Findings
No open blocking findings.

Resolved prior WATCH items:
1. MEDIUM route namespace and deep-link behavior - CLOSED. Gate A defines /ui/remodel/ ownership, refresh behavior, no escape to canonical routes, and preserved-route evidence.
2. MEDIUM build/bootstrap drift - CLOSED. Gate B requires shared production React bootstrap/component graph, retires or quarantines the vanilla renderer from production, and requires manifest/hash drift evidence.
3. MEDIUM final_approval/export safety - CLOSED. Gate C separates human export approval from append-only audit and forbids hidden automatic export, broker, live-order, account, and account-trading controls with source/DOM guards.
4. MEDIUM CSS token bridge/scoping - CLOSED. Gate D requires remodel-root scoping, token bridging over production styles, and before/after canonical-route screenshot gates.
5. LOW E2E gates - CLOSED. Gate E expands acceptance to preserved routes, backtest API/WS, replay API/WS, condition inspector/status WS, audit append/refresh, and DOM/action safety.

## Recommendations
1. Proceed to Critic pass 2 with the revision as the consensus candidate.
2. Preserve Gates A-E verbatim in the final pending-approval plan; do not demote them to optional test suggestions during Critic consolidation.
3. On execution approval, make Gate B and Gate A the first implementation decisions before page-level parity work: the route adapter and shared bootstrap/hash proof must exist before replacing static backtest/replay panels.
4. Keep /ui/evolution, /ui/backtest, and /ui/chart-replay as preserved controls until the full evidence matrix passes.

## Architectural Status
CLEAR

## Code Review Recommendation
APPROVE

## Trade-offs
| Option | Benefit | Risk | Status |
|---|---|---|---|
| Hybrid remodel shell over production components | Reuses mature /bt/*, /sim/*, condition, audit, and WS behavior; fastest real parity | Needs route, bootstrap, CSS, and safety adapters | Chosen; now gated explicitly |
| Greenfield remodel app | Cleaner new route/CSS/type model | Rebuilds deep state machines and prolongs mock behavior | Still rejected |
| Iframe/embed canonical pages | Fast visual containment | Not a standalone replacement; weak deep links/focus/theme | Still rejected |
| Disable export entirely in remodel | Maximum research-only safety | Reduces parity with existing approval UX | Not required because Gate C permits only explicit human approval and forbids hidden export |
