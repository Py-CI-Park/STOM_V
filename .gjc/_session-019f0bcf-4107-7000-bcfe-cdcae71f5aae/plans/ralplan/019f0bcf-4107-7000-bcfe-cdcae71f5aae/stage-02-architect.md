## Summary
The G002 mode-gate implementation is architecturally scoped correctly: reference/demo modes are separated from live mode, browser evidence records zero reference/demo network/storage/timer side effects, and live mode still reaches `/health`, `/status`, `/runs`, and `/ws`. G002 cannot be fully accepted because the required screenshot artifact `artifacts/ultragoal-g002-reference/g002-reference-condition.png` is absent from the target worktree even though the browser transcript/evidence references it.

## Analysis
- Spec compliance, fail-closed reference: `ai_strategy_loop/dashboard/frontend/remodel/src/app.js:10-25` detects `?demo=reference`, maps demo aliases, derives `isLiveBackendMode`, and exposes `window.__STOM_REMODEL_MODE__`, `window.__STOM_REMODEL_REFERENCE__`, and `window.__STOM_REMODEL_LIVE_BACKEND__` debug flags. `app.js:26-36` keeps localStorage reads/writes behind live-mode guards and returns fixture backend values for reference/demo.
- REST, WebSocket, and timer isolation: `app.js:330-337` rejects `fetchJson` before creating the abort timer or calling fetch when outside live mode; `app.js:444-497` guards backend refresh, `/health`, `/status`, `/runs`, WebSocket construction, and reconnect timers behind live mode; `app.js:736-737` only auto-connects in live mode.
- Control mutation isolation: `app.js:500-511` returns immediately for reference mode, treats demo mode as disabled fixture feedback, and only sends WebSocket control messages in live mode when a socket is open.
- Live-mode preservation: `app.js:444-452` still calls `/health`, `/status`, and `/runs`; `app.js:467-490` still constructs `/ws`; `app.js:439-456` exposes the visible fallback text `백엔드 미연결 · 정적 프리뷰` on backend failure; `app.js:26-36` preserves the localStorage base URL behavior in live mode.
- Determinism: no `Math.random` usage was found in `src/app.js`; `deterministicLineageValue` is used for lineage display. `tests/unit/test_dashboard_remodel_static.py:88-112` statically asserts the side-effect guard markers, `Math.random` absence, and deterministic lineage marker.
- Static test coverage: `tests/unit/test_dashboard_remodel_static.py:61-68` checks live backend markers and no new export-path strings; `tests/unit/test_dashboard_remodel_static.py:71-112` checks mode-gate markers, side-effect guards, localStorage/fetch/WebSocket/timer markers, and deterministic rendering; `tests/unit/test_dashboard_remodel_static.py:121-142` checks safety cues and forbidden live-order/broker/account controls.
- Browser evidence: `artifacts/ultragoal-g002-mode-gate/browser-transcript.json:7-14` records reference navigation, mode `reference`, zero fetch/ws/timer/storage side effects, demo zero side effects, and live `/health,/status,/runs` plus `/ws` and `stom_remodel_base_url`; `browser-evidence.json:3-48` records the same structured results; `browser-evidence.json:49-175` records all reference routes as `liveBackend:false` with empty fetch/ws/timer/storage arrays and `allPassed:true`.
- Safety contract: inspected `app.js` and tests show no `data-action="live-order"`, `data-action="broker-login"`, `data-action="account-trade"`, `final_approval`, or automatic production export marker. Safety/footer and modal language remain human-gated and research-only (`app.js:582-591`, `app.js:663-668`, `app.js:724-728`).
- Evidence gap: direct read of `artifacts/ultragoal-g002-reference/g002-reference-condition.png` failed with not found, and a filename lookup for that exact artifact under the worktree found no match. The browser transcript (`browser-transcript.json:10`) and browser evidence (`browser-evidence.json:17`) both reference that missing screenshot path.

## Root Cause
The product code mode gate appears aligned with G002, but the durable evidence package is incomplete: the screenshot artifact recorded by the browser automation was not present at the exact required path in the reviewed worktree. That breaks independent review of the reference rendering artifact even though the JSON evidence says the run passed.

## Findings
1. HIGH — `artifacts/ultragoal-g002-reference/g002-reference-condition.png`: Required reference screenshot artifact is missing. Impact: G002 cannot be fully accepted because the requested visual artifact cannot be inspected and the JSON evidence points to a non-existent file. Fix: restore or regenerate the screenshot at the exact path, then update the evidence package so JSON references resolve to an existing artifact.

## Recommendations
1. Restore/regenerate `artifacts/ultragoal-g002-reference/g002-reference-condition.png` at the exact requested path and keep the transcript/evidence JSON in sync.
2. Add an artifact-existence check to the evidence packaging step so a `verdict: passed` browser transcript cannot reference a missing screenshot.
3. Keep the current mode-gate code structure; no product-source blocker was found in the inspected files for the G002 fail-closed objective.

## Architectural Status
BLOCK

## Code Review Recommendation
REQUEST CHANGES

## Trade-offs
- Accepting JSON-only evidence would avoid a rerun but weakens the audit chain because the visual reference artifact is missing.
- Blocking until the screenshot is restored preserves G002 evidence integrity and does not require speculative product-code changes.
