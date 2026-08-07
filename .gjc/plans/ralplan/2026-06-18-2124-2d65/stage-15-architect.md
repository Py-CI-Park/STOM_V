## Summary
The remodel is blocked on the product/navigation contract: `app.jsx` exposes seven top-level tabs and omits the required stable `records` key, while Records remains embedded inside the evolution dashboard. Most App-level shell contracts are preserved, including backend/base URL/theme/run selector/start-stop/approval dialog, simulation keep-alive, direct page globals, and `/process_flow` iframe compatibility; however, two exact target files (`ui-contract.jsx`, `ui-state.jsx`) are absent and therefore the shared UI primitive/state boundary cannot be reviewed.

## Analysis
Scope inspected: `ai_strategy_loop/dashboard/frontend/app.jsx`, `dashboard-pages.jsx`, and `phase-detail.jsx` were read. Attempts to read the exact target paths `ai_strategy_loop/dashboard/frontend/ui-contract.jsx` and `ai_strategy_loop/dashboard/frontend/ui-state.jsx` returned `Path ... not found`, so those requested review surfaces are missing from this checkout.

Spec compliance by lane:
- Product lane: **BLOCK**. The approved stable key set is eight keys (`evolution`, `process`, `backtest`, `simulation`, `records`, `lab`, `pro`, `verdict`), but `STOM_TABS` defines only seven keys and omits `records` (`app.jsx:442-449`). Records is imported and rendered as an evolution-panel child (`app.jsx:32`, `app.jsx:326`) rather than routed as a stable tab. The active-tab branch covers `lab`, `pro`, `verdict`, and `process` (`app.jsx:276-297`) but no `records` route; a persisted `stom_active_tab=records` would not select a valid tab and would fall through to the evolution content without the evolution control strip.
- Architecture lane: **BLOCK**. The App shell still centralizes backend state and cross-tab controls (`useBackend` at `app.jsx:59`, theme/base URL controls at `app.jsx:196-201`, run selector at `app.jsx:240-246`, start/stop/final approval actions at `app.jsx:130-147`, modals at `app.jsx:408-419`), but the stable tab interface is a public navigation contract and is currently broken. The missing `ui-contract.jsx`/`ui-state.jsx` files also prevent validating the intended shared-primitive/state boundary.
- Code lane: **WATCH**. The inspected code uses only relative imports in the target files (`app.jsx:3-33`, `dashboard-pages.jsx:17`), so no new dependency is visible in this review scope. Direct page globals are preserved through `Object.assign(window, { LabPage, ProPage, VerdictPanel })` and ESM exports (`dashboard-pages.jsx:482-485`), and App mounts those globals defensively (`app.jsx:276-292`). Simulation keep-alive is preserved with `simVisited` plus hidden rendering instead of unmounting (`app.jsx:56-57`, `app.jsx:262-265`). Process state display remains read-only in `phase-detail.jsx`, consuming `state.latest.current_step`, `recent_logs`, and `step_timings` (`phase-detail.jsx:665-678`) with no inspected backend writes, and the standalone process page compatibility is preserved by the iframe to `baseUrl + "/process_flow"` (`app.jsx:296-300`).

## Root Cause
The remodel treated Records as an in-dashboard panel instead of a first-class stable route and did not reconcile the IA rewrite with the approved eight-key navigation contract. The requested shared contract/state review surface is also missing, so the boundary intended to keep primitives presentation-only is either unimplemented or outside the submitted file set.

## Findings
1. **HIGH — `app.jsx:442-449`, `app.jsx:326` — Stable Records tab is missing.** Impact: approved deep-link/localStorage/navigation contract is broken; Records cannot be selected as one of the eight stable top-level tabs and a persisted `records` key falls through to the wrong content. Fix: add `{ key: "records", ... }` to `STOM_TABS` in the approved order (`evolution`, `process`, `backtest`, `simulation`, `records`, `lab`, `pro`, `verdict`) and add an `activeTab === "records"` route that renders the Records surface as inert/read-only detail, preserving existing props and runtime gates.
2. **HIGH — `ui-contract.jsx` and `ui-state.jsx` absent — Requested shared UI contract/state files cannot be reviewed.** Impact: the acceptance item for shared UI primitives being presentation-only and the UI state boundary cannot be validated; if other bundle paths expect these files, they would fail resolution. Fix: restore/add the intended files or update the approved scope; keep presentation primitives free of backend effects and keep stateful helpers explicit and tested.
3. **LOW — `app.jsx:51-56`, `app.jsx:439-441` — Navigation comments still describe older tab counts/shapes.** Impact: stale comments obscure the current contract and contributed to the seven-vs-eight mismatch. Fix: update comments when fixing the tab contract so they state the exact stable eight-key list and route ownership.

## Recommendations
1. Fix the top-level tab contract first: exact eight keys, approved order, and an explicit Records route.
2. Restore or formally descope `ui-contract.jsx` and `ui-state.jsx`; do not approve the shared primitive/state boundary until those exact files are inspectable.
3. After changes, run focused UI verification only: each stable tab key, persisted `stom_active_tab=records`, standalone Lab/Pro/Verdict globals, simulation tab keep-alive, and `/process_flow` iframe load. No formatter or project-wide test is required for this checkpoint.

## Architectural Status
`BLOCK`

## Code Review Recommendation
`REQUEST CHANGES`

## Trade-offs
| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| Add Records as a first-class tab using the existing `ResearchRecordsPanel` | Satisfies stable key contract with minimal product churn and reuses existing implementation | May duplicate visibility if the embedded evolution panel remains | Preferred; remove or clearly keep the embedded panel as secondary only after product sign-off |
| Keep Records embedded in Evolution | No routing change | Violates approved eight-key contract and breaks direct/persisted navigation semantics | Reject |
| Descope missing `ui-contract.jsx`/`ui-state.jsx` | Avoids adding files during a review checkpoint | Leaves acceptance item unverifiable and weakens boundary ownership | Only acceptable with explicit plan/scope update before approval |
