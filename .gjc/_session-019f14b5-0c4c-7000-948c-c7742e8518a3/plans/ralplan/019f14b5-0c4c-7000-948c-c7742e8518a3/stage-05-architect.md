## Summary
G005 safety/provenance hardening is approved for the inspected dashboard remodel scope. The reviewed implementation and artifacts show reference/demo inert behavior, live read-only loopback probes, visible safety/provenance labeling, and human-gated/manual controls without mutating/export/order/broker/account runtime paths.

## Analysis
- Spec compliance: app.js separates reference, demo, and live; reference/demo shell state is normalized to REST INERT, WebSocket 정적 fixture, and Run Status reference/demo; browser evidence shows reference condition/backtest/replay/audit pages generated only static /ui/* document/style/script requests and no WebSockets.
- Backend provenance: live backend= parsing is live-only and permits only http(s) loopback hostnames 127.0.0.1, localhost, [::1], ::1, and the browser transcript shows live baseInput plus network fetches against http://localhost:8777.
- Network safety: fetchJson/fetchText reject outside live mode; Backtest/Replay adapters mark reference/demo contracts INERT; live backtest/replay probes are declared as GET safeAuto reads, while mutating POST and /sim/ws paths are marked manual/user gated and not auto-opened.
- UI/product safety: manual controls use data-inert-control plus disabled/aria-disabled outside live and data-manual-gate in live; CSS visibly dims/not-allowed inert controls; safety footer labels include No Live Order, No Broker Login, No Account Trading, Research Only, Human Approval Gate, and Append-Only Audit.
- Verification artifacts: verification-summary.json reports passed, websocketCount 0, mutating 0, liveBackendQueryEvidence true, referenceManualDisabled true, safetyLabelsOnEveryRoute true, and forbiddenAffordancesAbsent true; image evidence includes six non-empty non-uniform screenshots.

## Root Cause
The prior WATCH risk was ambiguous provenance: the reference shell and manual controls could look live, and live backend selection needed constrained provenance. The implementation fixes that at the mode boundary with explicit inert state, loopback query parsing, contract matrices, and visible manual-gate attributes rather than adding hidden fallback paths.

## Findings
None.

## Recommendations
Approve G005 for the inspected scope. Keep future backend-base expansion explicit and tested if non-loopback development targets are ever required.

## Architectural Status
CLEAR

## Code Review Recommendation
APPROVE

## Trade-offs
- Explicit mode gates in the remodel client keep the safety boundary easy to audit, at the cost of repeated guard strings in static tests.
- Contract matrices document unavailable/manual endpoints without invoking them, which is safer than exercising mutation paths in browser QA.
