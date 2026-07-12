## Summary
G005 safety/provenance hardening is substantially compliant with the hard safety goal: inspected source and artifacts show no mutating POST, export, /sim/ws, /bt/ws_job, or outbound WS control frame during page load, and no live order, broker login, or account trading affordance. Recommendation is COMMENT rather than full APPROVE because reference mode still inherits shell fixture defaults that display REST UP, WebSocket connected, and running status, which weakens the provenance separation even though it does not create a side effect.

## Analysis
Stage 1 — Spec compliance:
- Mode separation is implemented at the top of `ai_strategy_loop/dashboard/frontend/remodel/src/app.js`: `detectRemodelMode` recognizes `reference`, demo aliases, and live; `fetchJson`, `fetchText`, `refreshBackend`, `connectStateSocket`, and `sendControl` all gate backend work on live or explicit user action.
- Backtest and replay contracts are explicit matrices in `src/app.js:59-113`. Backtest POST endpoints are marked manual-gated and not auto-invoked; Replay `/sim/ws` and its start/pause/resume/speed/seek/stop protocol are marked USER-GATED and never auto-opened.
- The static tests in `tests/unit/test_dashboard_remodel_static.py:229-469` cover live bridge presence without export paths, reference/demo inert markers, forbidden backtest actions, replay `/sim/ws` non-autoload, and safety labels/forbidden controls.
- Browser evidence in `artifacts/ultragoal-g005-safety-hardening/verification-summary.json` reports 47 requests, 0 websockets, 0 referenceForbidden, 0 mutating, 0 forbiddenWs, and 0 liveUnsafe; all six captured routes had `safetyAll: true` and `forbiddenAny: false`.
- `image-evidence.json` records six non-uniform screenshots for reference condition/backtest/replay/audit plus live backtest/replay; the update log records focused pytest, node syntax, diff-check, and browser probe evidence.

Stage 2 — Architecture:
- The boundary is simple and maintainable: a single early mode detector feeds common fetch/socket helpers; adapters expose contract matrices instead of hidden alternate paths; reference/demo short-circuit before network, localStorage, or WS activity.
- Live mode allows safe GET/read probes only for page evidence, with conditional reads requiring discovered IDs and visible NOT-USED or LIVE ERROR states instead of fake success. This matches the Phase 0 safety matrix distinction between safe read telemetry and gated mutations.
- Remaining architecture watchpoint: reference mode does not normalize shell defaults the way demo mode does. `src/data.js` defaults still say REST `UP`, WebSocket `연결됨`, and run status `running`; browser transcript body samples confirm those labels are visible under `REFERENCE mode`. This is a provenance-display defect, not a mutation path.

Stage 3 — Code quality/security/performance:
- Source search found no `record_decision`, `final_approval`, `dest_strategy_db`, automatic production export, live-order/broker/account actions, or `fetch` calls with mutating methods in the remodel app.
- `localStorage` is limited to the live-only `stom_remodel_base_url` setter and getter. Reference/demo do not read or write it.
- `stateSocket.send` is reachable only through explicit Start/Stop clicks and is a no-op in reference/demo. No page-load caller sends a control frame.

## Root Cause
The only issue found is a provenance-label mismatch: `src/data.js` supplies live-looking shell fixture defaults, and `src/app.js` only rewrites them for demo mode. Reference mode correctly disables side effects, but it does not rewrite those shell status labels to fixture/reference equivalents.

## Findings
- MEDIUM/LOW, `ai_strategy_loop/dashboard/frontend/remodel/src/app.js:38-42`: Reference mode leaves shell status defaults as REST UP, WebSocket connected, and running. Impact: auditors can see a reference fixture page that appears connected/running despite no backend calls. Fix: normalize `isReferenceMode || isDemoMode` shell labels to explicit non-live values, ideally `REFERENCE` or `정적 fixture` and `reference`, while preserving live mode behavior.

## Recommendations
1. Before final default-route promotion, normalize reference shell status labels so fixture connectivity cannot be mistaken for live evidence.
2. Keep the current centralized mode gate and contract matrices; do not add separate per-page fallback paths.
3. Maintain the browser network denylist and static forbidden-control tests as required gates for future backtest/replay or audit changes.

## Architectural Status
WATCH

## Code Review Recommendation
COMMENT

## Trade-offs
| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| Keep current implementation | No additional change; safety side effects already blocked | Reference shell status can look live/connected | Accept only as non-blocking watch |
| Normalize reference and demo shell labels together | Honest provenance and tiny change at source | Requires one focused code/test update | Preferred |
| Remove shell status widgets in reference mode | Avoids false live status entirely | Loses useful layout parity and visual comparison | Not needed |
