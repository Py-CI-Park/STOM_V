# V3 STOM Dashboard 100 Percent UX/UI Rebuild Plan - Revision 2

## Summary
Read-only RALPLAN revision. No product source mutation, no tests, no builds, no formatters, no runtime or protected-path writes, no commit, no stage, no push. This artifact revises the planner plan with architect and critic feedback and remains pending approval for later Ultragoal execution.

Target outcome: V3 becomes genuinely 100 percent UX/UI complete and better than V2 while V2 remains the default and V3 remains explicit/selectable. Safety envelope remains local-only, research-only, no live order, no broker login, no account trading, Human Approval Gate, Append-Only Audit, no hidden export, and no protected runtime writes.

Inspected basis retained: final recheck scorecard passed numerically, but V3 still has qualitative false-pass risks. remodel/src/data.js is dummy/offline prototype data. remodel/src/app.js uses static SVG chart helpers without hover/crosshair and renders a static Process map. V2 bundle demonstrates required depth: FitnessChart hover state, onMouseMove/onMouseLeave, vertical guide and tooltip; SimLiveChart canvas hover, cursor crosshair, OHLC tooltip and crosshair drawing.

## In scope / out of scope
In scope: V3-native UX rebuild, V2 parity plus improvement, interactive charts, real Process monitoring, deterministic provenance, hard Phase 0 gates, safety matrices, 100-point observable rubric, API-200-not-enough acceptance, and later Ultragoal phases.

Out of scope: implementation now, product mutation now, tests now, making V3 default, replacing V2, broker login, account trading, live order, hidden export, protected runtime writes.

## Principles
Truth before polish. Interaction is part of completeness. V2 behavior is the floor. Fixture/reference data must be obvious. API 200 is never proof by itself. Safety controls are non-negotiable. Use V3-native primitives and adapters rather than broad framework churn.

## Decision drivers
User trust, V2 interaction parity, real monitoring depth, deterministic observable evidence, safety invariants, V2 regression containment, and clean Ultragoal handoff.

## Options and decision
Option A direct V2 port: fast parity, but risks React/V2 coupling and incomplete provenance. Option B V3-native interaction and provenance layer using V2 as behavioral spec: coherent, lower V2 risk, solves charts/process/provenance together, requires stronger tests. Option C full React rewrite: rich but too broad and risky. Chosen: Option B.

## File-level changes for later execution
- ai_strategy_loop/dashboard/frontend/remodel/src/app.js: add reusable interactive chart primitives, nearest datum hover, crosshair, accessible tooltip DOM, keyboard focus, legend highlight, Process monitoring cockpit, hard provenance cues, and manual-gated actions.
- ai_strategy_loop/dashboard/frontend/remodel/src/data.js: replace dummy semantics with reference baseline semantics, including referenceFixture, generatedFrom, asOf, and loading/stale/error/live-derived scenarios.
- ai_strategy_loop/dashboard/frontend/bundle/app.js: read-only V2 parity reference only.
- ai_strategy_loop/dashboard/app.py: inspect only if endpoint inventory confirmation is needed for read-only monitoring.

## Hard Phase 0 gates before any implementation
Phase 0 is not optional. Ultragoal execution cannot mutate product source until these gates are documented as pass/fail criteria in the ledger.

### Gate 0A - Process data-source matrix
Every Process row must define endpoint or feed, required fields, DOM assertions, fallback label, and missing-field failure rule. API 200 without required fields fails.

| Surface | Endpoint or feed | Required fields | DOM assertions | Fallback label | Missing-field failure rule |
| --- | --- | --- | --- | --- | --- |
| Shell health | GET /health | status | REST badge shows status and provenance says live-read | Backend unavailable - reference baseline | 200 without status fails live claim |
| Loop status | GET /status | run_id, status, current_gen, max_generations, latest.phase or latest.message, generations array | header run_id, run status, progress, overview phase, strategy counts change from fixture | Status fallback - fixture baseline | missing run_id or generations blocks live badge |
| Process nodes | GET /status or confirmed Process endpoint | process.nodes or derivable stage list with id, title, status, duration or time, items | each node renders status, count, duration, freshness, selected drilldown | Process reference map | any node missing id/status fails monitoring gate |
| Process logs | /ws state message or confirmed GET logs endpoint | timestamp, level, message, source or node id | log panel shows live row count, severity, last timestamp, pause state | Static reference logs | log array without timestamp or message fails live log claim |
| Process queues/workers | GET /status or confirmed metrics endpoint | queue_depth, active_workers, throughput or equivalent | KPI cards update from payload and carry age | Reference KPI baseline | 200 with unchanged fixture DOM fails |
| Boundary contracts | confirmed local schema or static reference contract | edge id, source, target, fields, SLA, owner | contract table matches rendered node edges and selected node detail | Reference contract | edge not tied to DOM nodes fails |
| Runs archive | GET /runs | runs array with run_id and status, optional label/provider/bt_timeframe | run selector options and History rows use run_id/status from payload | Fixture archive | 200 without runs array fails archive live state |
| Stale state | any above | payload timestamp or derived received_at | provenance shows age and stale badge when threshold exceeded | Stale live payload | no timestamp/received_at fails freshness gate |
| Error state | failed request or malformed JSON | error message, endpoint id | visible error row, no fake success, fixture fallback reason | Error - using reference baseline | hidden error or green live badge fails |

Phase 0A output required before implementation: a checked matrix with actual endpoint inventory, field schema, DOM selector or data-testid for each assertion, stale threshold, and screenshot/assertion plan.

### Gate 0B - Action and WebSocket safety matrix
Every action must be classified as safe auto-read, user-gated read, manual research action, or forbidden. Page load must not call mutating endpoints. Reference/demo modes must be inert.

| Action or channel | Current/expected authority | Allowed behavior | Network assertion | UI assertion | Failure rule |
| --- | --- | --- | --- | --- | --- |
| Shell Start | sends WS control action start only in live mode | user click only; no order/trading semantics | no network on reference/demo; live sends one /ws message only after click | state says control pending or live run control, not trading | auto-send on load fails |
| Shell Stop | sends WS control action stop only in live mode | user click only | no network on reference/demo; live sends one /ws message after click | stop is engine control, not order cancel | auto-send or order language fails |
| State /ws | dashboard status WebSocket | live mode may connect only after explicit live backend mode or reconnect policy; never in reference/demo | no WS in reference/demo; bounded reconnect in live | websocket badge shows connected/error/reconnect with age | hidden long-lived WS in reference/demo fails |
| final_approval/export | Human Approval Gate | modal only; requires checkbox/comment; no hidden export | no export request on modal open; export request only after explicit confirm if endpoint is approved | clear research export wording, no trade wording | export before approval fails |
| record_decision | Append-Only Audit | explicit submit only with required note and decision | no request on page load; one append action after submit if endpoint exists | ledger appends visually and cannot overwrite prior row | overwrite or silent success fails |
| generic exports | local visible download or approved endpoint only | user click only, visible file/type, no protected path | no request/write on load; no protected runtime path | label says local research export and approval status | hidden export or protected write fails |
| backtest POSTs | /bt/strategy/validate, /bt/strategy, /bt/strategy/delete, /bt/extract_vars, /bt/run, /bt/job/cancel, /bt/job/meta, /bt/portfolio | manual research action only; never auto | zero POSTs on page load; POST only after explicit control and confirmation where destructive | contract matrix marks not auto-invoked | any auto POST fails |
| replay /sim/ws | manual replay stream | never auto-open; user-gated start/pause/resume/speed/seek/stop | no /sim/ws on page load; one WS only after explicit start | panel says user-gated, no live order | auto WS fails |
| settings/localStorage | UI preference only | localStorage only in live mode for base URL or harmless preferences; no protected writes | no network; no protected path writes | settings values labeled local UI preferences | storing secrets, account data, or export paths fails |
| theme/local UI | UI-only | allowed local DOM/class change | no network | visible theme/focus state | network or storage side effect fails |

Phase 0B output required before implementation: allowlist and denylist, browser network assertion plan, static search terms, and per-action DOM selectors.

### Gate 0C - Deterministic observable 100-point UX/UI rubric
The rubric is deterministic. Each point maps to observable evidence, not reviewer vibes. Score must equal 100. API 200 never earns points unless required fields drive visible DOM state.

| Category | Points | Deterministic evidence |
| --- | ---: | --- |
| Visual hierarchy | 10 | screenshots for all V3 routes show no overlap, readable density, clear page purpose, consistent panel rhythm |
| Interaction depth | 16 | hover/focus/click tests prove tooltip, crosshair or marker, selected state, and cleanup on every decision chart and Process node |
| Data provenance | 14 | each page shows source, mode, backend, run id when available, timestamp/age, fixture/live/fallback, and required payload fields |
| V2 parity plus improvement | 12 | V2/V3 compare proves inherited hover, tooltip, crosshair, help, pending-live honesty, and V3 adds provenance/accessibility |
| Process monitoring reality | 14 | run selector, nodes, logs, queue/workers, contracts, drilldowns, stale/error/loading states are payload-driven and asserted |
| Safety/governance | 14 | network and static audits prove no broker login, account trading, live order, hidden export, protected writes, auto mutating calls, or auto /sim/ws |
| Accessibility | 8 | keyboard access, focus states, aria/labels or equivalent, no hover-only essential values, contrast pass |
| Performance/responsiveness | 4 | hover and render remain smooth under large fixture/live arrays, no obvious layout jank |
| Failure-state quality | 4 | empty, loading, stale, malformed, network error states are visible and useful |
| Evidence package | 4 | scorecard, screenshots, contact sheet, network trace, interaction assertions, provenance assertions, V2/V3 compare included |

Hard rule: any zero in a category blocks completion even if total is mathematically 100 through other points. No manual override.

## API-200-not-enough acceptance
A 200 response counts only when all are true: required schema fields exist; values are mapped into visible DOM; provenance changes to live-read with endpoint and age; fixture fallback is removed or explicitly marked as mixed; stale/malformed cases show warnings; tests assert at least one payload value that differs from fixture. 200 with missing required fields, unchanged fixture DOM, hidden error, stale timestamp without stale label, or green live badge without payload evidence fails.

## Deliverables by surface
Global: V2 default preserved, V3 explicit routes preserved, mode/source/freshness/run banners, always-visible safety strip.
Overview: interactive Fitness, Profit, Equity, Quality, Backtest charts; source-linked inspector; approval panel remains gated.
Process: monitoring cockpit with data-source matrix coverage, run selector, node status, node drilldown, logs, queue/workers, contracts, freshness and failure states.
History: interactive run/pass/PF/MDD charts, click-to-select run detail, lineage source ids, compare guarded by data availability labels.
Lab: interactive correlation/importance/holdout/density, variable selection, freshness and quality provenance.
Workbench: selectable candidates, heatmaps, compare drawer, evidence source ids, review-queue only.
Audit: append-only decision chain, required note validation, hash/record status, pending approval.
Backtest: preserve contract matrix, chart hover/crosshair, no auto mutating endpoints.
Chart Replay: V2 SimLiveChart parity or better: crosshair, OHLC/time/indicator/signal tooltips, keyboard focus, no auto /sim/ws.

## V2 parity and inheritance list
Inherit or exceed V2 chart hover state, nearest point/bar lookup, rich tooltip, vertical/full crosshair, crosshair cursor, explanatory help/data-tip, live pending honesty, process phase explanation, React Flow equivalent select/pan/drilldown or honest relabeling, replay OHLC hover, and safety banners. V3 adds consistent provenance, accessibility, and deterministic tests.

## Ultragoal phases after approval
Phase 0 hard gates above: document actual Process data-source matrix, action/WebSocket safety matrix, and deterministic rubric selectors before mutation. Phase 1 inventory V2/V3 parity and baseline screenshots. Phase 2 V3 interactive chart primitives. Phase 3 Process monitoring rebuild. Phase 4 provenance and safety hardening. Phase 5 page completion sweep. Phase 6 verification and 100-point scoring. Phase 7 final evidence package and completion only after every criterion passes.

## Verification plan for later execution
Unit: chart geometry, nearest lookup, crosshair coords, tooltip formatters, provenance mapper, safety classifiers. Integration: payload-to-DOM changes, Process matrix assertions, fixture inertness, no auto mutating endpoints, approval/audit validation. Browser/e2e: visit all routes, hover/focus/click every chart and Process node, capture screenshots/contact sheet, test loading/empty/stale/network/malformed states. Network: assert no POST or /sim/ws on page load, no reference/demo /ws, bounded live /ws behavior, explicit-click-only actions. V2/V3 compare: V3 must match or exceed V2 feature depth and V2 remains default.

## Acceptance criteria
This revision is accepted when persisted through gjc ralplan --write stage revision stage_n 2 with no product mutation. Later execution is accepted only when Phase 0 gates are completed first, V2 default remains unchanged, V3 is explicit, every required payload has schema-to-DOM assertions, every safety-sensitive action has network assertions, V3 scores deterministic 100/100, API 200 alone cannot pass, Process is real monitoring, charts are interactive, safety invariants pass, and final evidence package proves all claims.

## Risks and mitigations
Fake-looking V3 despite numeric pass: block on payload-to-DOM, provenance, interaction, and visual evidence. Static Process with better styling: block on matrix-driven run/node/log/queue/contract assertions. Safety erosion: block on action/WebSocket safety matrix and network audit. Inconsistent charts: shared primitives first. V2 regression: route/version compare gate.

## Pre-mortem
1. Polished screenshots but static UX: hover/click/crosshair tests fail. 2. Process claims live while using fixtures: data-source matrix and changed-payload DOM assertions fail. 3. Monitoring adds unsafe authority: safety matrix catches auto WS, POST on load, export bypass, broker/account/order wording, or protected writes.

## Handoff
Use architect for endpoint/boundary review before Phase 0 signoff if schemas are unclear. Use critic to review Phase 0 gates before mutation. Use executor only after explicit approval for bounded slices. Use Ultragoal for execution ledger and evidence. Pending approval remains in force now.
