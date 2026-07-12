# Ultragoal G004 — Process monitoring cockpit rebuild

## Result
G004 rebuilt `/ui/remodel/process` from a fixed fixture-poster into a payload-driven monitoring cockpit, with both honest reference/demo behavior and live `/status`-derived DOM updates.

## Implemented evidence
- Run selector renders `runs` payload and changes selected run/drilldown in the DOM.
- State strip renders `data-process-state`, source, run_id, phase, freshness, missing and malformed counts.
- Required-field grid renders `data-process-required` for `kpis`, `nodes`, `logs`, `runs`, `queue`, `workers`, and `contracts`.
- Phase map renders clickable `data-process-node` buttons and node drilldown modal with `payload_source`.
- Logs, queue, workers, and route boundary contracts render from explicit `data-source-key` containers.
- Empty/loading/stale/error/malformed matrix is visible.
- Reference/demo mode is honestly labeled: `reference/demo honest fixture · not live`.
- Live mode adapts backend `/status` into a process payload (`backend /status process monitor`) instead of always reusing static `DATA.process`.
- Idle/unknown live state is neutral: no fake active Generation node and no running queue count.
- Live contracts are not force-marked OK without backend contract evidence; fixture contract health is UNKNOWN/PENDING in live synthetic mode.
- Negative backend generation values are clamped for shell and Process payload display.
- Safety labels remain visible: No Live Order, No Broker Login, No Account Trading, Human Approval Gate, Append-Only Audit, Research Only.

## Verification
- `node --check ai_strategy_loop/dashboard/frontend/remodel/src/app.js`
- `python -m pytest tests/unit/test_dashboard_remodel_static.py tests/unit/test_dashboard_route_parity.py -q` → 25 passed
- `git diff --check -- ai_strategy_loop/dashboard/frontend/remodel/src/app.js ai_strategy_loop/dashboard/frontend/remodel/styles/theme.css ai_strategy_loop/dashboard/frontend/remodel/src/data.js tests/unit/test_dashboard_remodel_static.py` → PASS
- Browser automation transcript: `artifacts/ultragoal-g004-process-cockpit/browser-transcript.json`
- Screenshots: `process-cockpit.png`, `process-node-modal.png`, `process-cockpit-live.png`
- Image evidence: `artifacts/ultragoal-g004-process-cockpit/image-evidence.json`

## Verdict
Passed implementation verification pending final independent architect/executor QA gates after live adapter, idle, contract, selector, and negative-generation fixes.
