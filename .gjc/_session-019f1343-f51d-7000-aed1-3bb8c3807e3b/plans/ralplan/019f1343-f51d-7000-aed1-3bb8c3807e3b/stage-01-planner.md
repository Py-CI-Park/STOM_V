# V3 STOM Dashboard 100 Percent UX/UI Rebuild Plan

## Summary
Planning only. Stop at pending approval; later execution must use Ultragoal. V2 remains default, V3 remains explicit/selectable. Safety envelope remains local-only, research-only, no live order, no broker login, no account trading, Human Approval Gate, Append-Only Audit, no hidden export, no protected runtime writes.

Inspected evidence: final scorecard is PASS with V3 visual 97.93, route-function 100, runtime 100, safety 100, but user findings expose a false-complete risk. remodel/src/data.js is labeled dummy/offline prototype data. remodel/src/app.js has static SVG chart helpers with no hover/crosshair and a Process page that renders an absolute-position static map while labeling it React Flow. V2 bundle shows the missing depth: FitnessChart uses hover state, onMouseMove/onMouseLeave, vertical guide and tooltip; SimLiveChart uses canvas hover, cursor crosshair, OHLC tooltip and crosshair drawing.

## In scope / out of scope
In: make V3 feel real and better than V2; V2 parity plus improvement; interactive charts; real monitoring Process; provenance; safety; later testable Ultragoal phases. Out: source mutation now, tests/builds/formatters now, making V3 default, replacing V2, broker/account/live order, hidden export, protected writes.

## Principles
Truth before polish; interaction is completeness; V2 behavior is the floor; fixture/reference must be obvious; API 200 alone is never proof; safety controls are non-negotiable; use boring V3-native primitives rather than broad framework churn.

## Decision drivers
User trust, V2 interaction parity, real monitoring depth, safety invariants, regression containment, maintainable later execution, and browser-observable acceptance.

## Options
A. Directly port V2 interactive components. Pros: fastest parity, known hover/crosshair behavior. Cons: couples V3 to V2/React assumptions and may leave process/provenance fake.
B. Build V3-native interaction and provenance layer, using V2 behavior as the spec. Pros: coherent V3, lower V2 regression risk, solves charts/process/provenance together. Cons: more deliberate implementation and stronger tests needed.
C. Replace V3 with full React app. Pros: rich component ecosystem. Cons: highest scope/risk and unnecessary now.
Chosen: B.

## File-level changes for later execution
- ai_strategy_loop/dashboard/frontend/remodel/src/app.js: add reusable interactive chart primitives, nearest datum hover, crosshair, tooltip DOM, keyboard focus, legend highlight, Process monitoring cockpit, stronger provenance cues, tighter manual-gated actions.
- ai_strategy_loop/dashboard/frontend/remodel/src/data.js: rename dummy semantics to reference baseline; add referenceFixture/asOf/generatedFrom/field provenance and loading/stale/error/live-derived scenarios.
- ai_strategy_loop/dashboard/frontend/bundle/app.js: read-only parity reference only.
- ai_strategy_loop/dashboard/app.py: inspect only if endpoint inventory is needed for read-only Process/run monitoring.

## Deliverables by surface
Global: V2 default preserved; V3 explicit routes preserved; mode/source/freshness/run banners; always-visible safety strip.
Overview: interactive Fitness, Profit, Equity, Quality, Backtest charts; source-linked inspector preview; approval panel remains gated.
Process: real cockpit with run selector, node status, node drilldown, queue/logs, SLA, stale/error/loading states, boundary contracts tied to nodes, explicit fixture/live labels; remove or clearly manual-gate misleading Export Process Map.
History: interactive run/pass/PF/MDD charts; click-to-select run detail; lineage search returns source ids; compare blocks missing/fixture-only data unless labeled.
Lab: interactive correlation/importance/holdout/density; variable selection; freshness and data-quality provenance.
Workbench: selectable candidate cards, heatmaps, compare drawer, evidence source ids; review-queue only, no trading language.
Audit: append-only decision chain, required note validation, hash/record status, pending approval state.
Backtest: preserve contract matrix; hover/crosshair charts; mutating endpoints manual-gated and never auto-invoked.
Chart Replay: match/exceed V2 SimLiveChart with crosshair, OHLC/time/indicator/signal tooltips, keyboard focus; no auto /sim/ws.

## V2 parity/inheritance list
Inherit or exceed: chart hover state, nearest point/bar lookup, tooltip richness, vertical/full crosshair, crosshair cursor, explanatory help/data-tip, live pending honesty, process phase explanation, React Flow equivalent pan/select/drilldown or honest relabeling, replay canvas OHLC hover, safety banners. V3 must add consistent styling, provenance, accessibility, and tests.

## 100-point UX/UI expert rubric
100 required; any miss blocks completion. Visual hierarchy 12; interaction depth 16; provenance/truthfulness 14; V2 parity plus improvement 12; Process monitoring reality 12; safety/governance 12; accessibility 8; performance/responsiveness 6; visual compare evidence 4; failure-state quality 4.

## Ultragoal phases after approval
0 approval and ledger setup with this plan path and safety invariants. 1 inventory V2/V3 parity and baseline screenshots. 2 V3 chart primitive rebuild. 3 Process monitoring rebuild. 4 provenance and safety hardening. 5 page completion sweep across all eight routes. 6 verification and 100-point scoring. 7 final evidence package and completion only after all gates pass.

## Test plan
Unit: chart geometry, nearest lookup, crosshair coords, empty/single/negative/multi-series, tooltip formatters, provenance mapper, safety label/action guards.
Integration: adapters change DOM from read-only payloads; Process updates node/log/queue/freshness/drilldown; fixture mode remains inert/labeled; no mutating endpoints or auto WebSocket; approval/audit validation.
E2E/browser visual: visit all V3 routes; hover/focus each chart; assert tooltip/crosshair/value correctness; click Process nodes/logs/run selector/candidates/audit/inspector; capture screenshots and V2/V3 contact sheets; cover loading/empty/stale/network/malformed states.
Provenance: every page shows source, mode, backend, run id when available, timestamp/age, fixture/live/fallback. 200 with missing fields fails.
Safety: static/runtime checks for broker login, account trading, live order, hidden export, protected writes; network asserts no mutating page-load calls and no auto /sim/ws.
V2/V3 compare: prove V3 has all V2 hover/tooltip/crosshair/selection/help/pending-live honesty and V2 remains default.

## Acceptance criteria
Current RALPLAN acceptance: artifact persisted by gjc ralplan --write and no mutation. Later execution acceptance: V2 default unchanged; V3 explicit; no dummy feel through honest reference/live provenance; every decision chart has hover/tooltip/crosshair/focus; Process is real monitoring with drilldowns and freshness; rubric score is 100/100; API-200-only false pass impossible because payload must visibly change DOM/provenance/state and stale/missing fields fail; safety invariants pass; browser interaction evidence covers all routes; final package includes tests, screenshots, interaction traces, provenance, safety audit, V2/V3 compare.

## Risks and mitigations
Risk fake-looking V3 passes numeric gates: require payload-to-DOM, provenance, hover and visual evidence. Risk inconsistent charts: shared primitives first. Risk Process remains poster: require live/read-only values, drilldowns, logs, stale/error states. Risk safety erosion: read-only allowlist, no auto WS, no mutating page-load calls, gate assertions. Risk V2 regression: route/version tests.

## Pre-mortem
1 polished screenshots but static UX: hover/click tests and tooltip/crosshair assertions fail the run. 2 Process claims live while using fixtures: freshness/run/source assertions and changed-payload DOM tests fail. 3 monitoring adds unsafe authority: network/safety audits catch auto WS, mutating calls, export bypass, broker/account/order wording.

## Handoff
Use architect for endpoint/boundary review if needed; executor only after approval for bounded slices; critic if scope expands; team only for approved parallel lanes; Ultragoal owns execution ledger and evidence. Pending approval: no implementation, tests, builds, formatting, commits, staging, pushing, runtime mutation, or protected writes now.
