## Summary
G005 safety/provenance is not blocked: the inspected implementation keeps reference/demo fetches inert, live probes use GET-only reads for /bt and /sim discovery, and the supplied browser transcript reports zero WebSockets, zero mutating requests, zero forbidden WS, and all pass criteria true. The result should remain WATCH/COMMENT because several provenance and UI-affordance concerns can mislead users or leave future safety regressions under-tested.

## Analysis
Evidence inspected: `ai_strategy_loop/dashboard/frontend/remodel/src/app.js`, `tests/unit/test_dashboard_remodel_static.py`, `artifacts/ultragoal-g005-safety-hardening/browser-transcript.json`, `verification-summary.json`, and `image-evidence.json`.

Core safety evidence is positive. `app.js` detects `reference`, `demo`, and `live` modes from the `demo` query and only enables backend fetch helpers in live mode (`fetchJson` / `fetchText` reject outside live). Backtest and replay adapters mark contracts `INERT` in non-live modes, mark POST/WS/action/message paths manual or user-gated, and auto-probe only declared safe GETs in live mode. `verification-summary.json` records 47 requests, 0 WebSockets, 0 mutating, 0 forbiddenWs, 0 liveUnsafe, all pass criteria true, and verdict `passed`. `image-evidence.json` shows six non-uniform screenshots with hashes, covering reference condition/backtest/replay/audit and live backtest/replay.

The WATCH concerns are about provenance truthfulness and review strength rather than an observed unsafe live-order path. Reference pages still render shell status from fixture data as `REST UP`, `WebSocket 연결됨`, and `Run Status running`; Start/Stop and many backtest/replay buttons remain enabled even when the mode is reference/demo inert or live read-only; and the live verification URL includes a `backend=` query that the app does not parse, so the evidence only proves same-origin backend behavior. The static tests mostly assert source substrings and forbidden literals; they do not execute DOM/network behavior or disabled-control state.

## Root Cause
G005 hardening is implemented as an overlay of labels, contract matrices, and static guards on a prototype UI that still renders reusable fixture shell state and enabled preview/action buttons. The code prevents the observed network mutations, but the UI/provenance model has not fully separated inert preview controls from live/manual controls, and the unit tests mostly check markers rather than behavior.

## Findings
- MEDIUM — `ai_strategy_loop/dashboard/frontend/remodel/src/app.js:34-42`, `:666-671`; `browser-transcript.json:310`, `:489`, `:708`: reference mode is inert, but status chips/body samples still show `REST UP`, `WebSocket 연결됨`, and `Run Status running`. Impact: users can mistake fixture/reference state for an actual connected backend despite the provenance cue. Fix: normalize reference as well as demo to explicit static/inert shell values, or derive shell health from live payload/socket state only.
- MEDIUM — `app.js:687`, `:711-712`, `:1385-1387`, `:1416-1422`; `browser-transcript.json:423-481`, `:603-707`, `:986-1043`, `:1165-1269`: Start/Stop, save/delete/cancel, instant replay, playback, and `/sim/ws` protocol buttons remain enabled in inert/read-only pages. Many are no-op previews, and forbidden live-order controls are absent, but enabled affordances undercut the read-only safety story and create regression risk if handlers are later attached. Fix: disable/no-op-label preview buttons in reference/demo, isolate real live/manual controls behind explicit user-gated handlers, and test disabled state.
- MEDIUM — `app.js:10-17`, `:34-36`, `:725-748`; `browser-transcript.json:877`, `:1056`, `:1397-1555`: live evidence URLs pass `backend=http://127.0.0.1:8777`, but the app only reads `demo` and otherwise uses stored base URL or same-origin default. Impact: verification does not prove the documented backend override path or URL sanitization behavior; all observed fetches target same-origin 127.0.0.1:8777. Fix: either parse/validate the backend query explicitly and test it, or remove it from verification claims.
- LOW — `verification-summary.json:13-18`, `browser-transcript.json:1796-1800`, `app.js:100-111`, `:914-919`, `:1413-1422`: zero WebSockets is correct for safety, but it means `/sim/ws` manual start/recovery and message handling remain documented rather than exercised. Impact: product readiness for user-gated replay streaming is unproven. Fix: keep it documented as protocol-only until a separate manual-gate E2E verifies open/send/close/error behavior without auto-open.
- LOW — `tests/unit/test_dashboard_remodel_static.py:390-478`, `:485-509`: G005 tests are primarily source-substring and forbidden-literal checks. Impact: future code can satisfy marker checks while changing runtime behavior, disabled state, or provenance truthfulness. Fix: add a focused executable DOM/network test that loads reference/live routes, asserts no reference fetch/WS/localStorage, asserts safe live GET allowlist, and checks inert buttons are disabled/labeled preview.

## Recommendations
1. Keep G005 at WATCH/COMMENT, not BLOCK: no observed unsafe mutation or forbidden live-order path appears in the supplied evidence.
2. Before checkpointing as durable completion, fix or explicitly waive the misleading reference shell status and enabled inert controls.
3. Add behavioral tests for mode-derived shell state, disabled preview controls, backend base selection, and network allowlists.
4. Treat `/sim/ws` as protocol documentation until a separate manual-gated E2E proves real stream behavior.

## Architectural Status
WATCH

## Code Review Recommendation
COMMENT

## Trade-offs
| Option | Pros | Cons |
|---|---|---|
| Accept G005 now with advisories | Preserves current no-mutation safety evidence; avoids blocking on prototype polish | Leaves misleading status/buttons and static-test brittleness |
| Fix status/buttons/tests before checkpoint | Stronger provenance and future regression protection | Requires UI/test changes before checkpoint |
| Implement `/sim/ws` manual stream now | Proves product replay path | Expands scope beyond safety hardening and risks introducing live WS behavior before gates are mature |
