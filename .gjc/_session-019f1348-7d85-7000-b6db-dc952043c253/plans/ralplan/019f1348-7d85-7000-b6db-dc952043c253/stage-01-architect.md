## Summary
The planner artifact is sound in direction: it moves the V3 dashboard definition of done from visual pass to observable UX truthfulness, V2 interaction parity, Process monitoring depth, provenance, and safety evidence. It is concrete enough to seed Ultragoal, but Phase 0 must make two implicit contracts explicit before implementation: a Process data-source matrix and a complete action/WebSocket safety matrix.

Verdict fields: architectureStatus=`WATCH`; productStatus=`READY_WITH_WATCH`; codeStatus=`PLANNING_ONLY_READ_ONLY`; recommendation=`COMMENT`.

## Analysis
Spec compliance: the plan keeps the current phase read-only, preserves V2 as default, makes V3 explicit/selectable, and carries the required safety envelope: local-only, research-only, no live order, no broker login, no account trading, no hidden export, and no protected runtime writes. It also stops at pending approval and routes later execution through Ultragoal.

Evidence supports the diagnosis. `artifacts/ultragoal-recheck-final/final-recheck-scorecard.json` reports PASS with V3 visual 97.93, route-function 100, runtime 100, and safety 100, yet Process has graphItemCount 0. That validates the false-complete risk: existing gates can pass while missing interaction depth and real monitoring behavior.

Current V3 evidence matches the plan. `ai_strategy_loop/dashboard/frontend/remodel/src/data.js` is explicitly dummy/offline prototype data. `remodel/src/app.js` renders charts via static SVG helpers such as `lineSvg`, `chart`, `barLineChart`, and `candleSvg`, with no pointer-state owner, nearest-datum lookup, crosshair, tooltip model, or keyboard focus. The Process page renders fixture `DATA.process` nodes/logs as absolute-position cards while labeling the panel React Flow and exposing an Export Process Map action.

V2 is a valid floor. `ai_strategy_loop/dashboard/frontend/bundle/app.js` has `FitnessChart` hover state, `onMouseMove`, `onMouseLeave`, nearest generation selection, vertical guide, and tooltip. `SimLiveChart` has canvas hover refs, crosshair cursor, OHLC tooltip, requestAnimationFrame drawing, and drawn vertical/horizontal crosshair lines. The plan correctly treats these as inherited minimum behaviors, not optional polish.

V2 default preservation is also file-backed: `ai_strategy_loop/dashboard/app.py` selects V3 only for `dashboard_version=v3|remodel|preview` or direct `/ui/remodel/*` routes, otherwise returning V2.

Strongest steelman antithesis: avoid a broad V3-native rebuild. Directly port the V2 interactive charts, relabel the Process map as a static reference until live sources are known, and avoid touching live adapters or WebSocket behavior. This is lower risk and faster for the visible hover/crosshair complaint.

Synthesis: the chosen V3-native path is still better because the defect is wider than charts. V3 currently mixes static fixture polish, live/fallback state, and monitoring claims. A narrow shared V3 interaction/provenance layer can fix charts, Process, failure states, and evidence gates together while leaving V2 untouched. The antithesis should influence sequencing: inventory first, then one minimal chart primitive, then Process data contracts, then page sweep.

UX/UI architecture risks: a reusable chart layer can become a mini-framework if it tries to solve every chart shape. Keep it to scales, nearest datum, crosshair model, tooltip formatter, keyboard focus, empty/single/negative cases, and legend highlight. Accessibility must include focus rings, keyboard equivalents, ARIA labels, and non-hover discovery.

Data-flow risks: `provenanceFor` currently permits live mode without payload as backend loading/fallback with fixture baseline. That state is acceptable as an honest preview, but must never pass live acceptance. Current mapping mainly updates shell/overview/history from `/status`, `/runs`, and `/ws`; Process-specific monitoring should use a declared source contract, likely including read-only `/ops_status` and `/pipeline_status` where applicable.

Safety boundary risks: current V3 shell has Start and Stop controls bound to `sendControl`; in live mode they can send control frames over `/ws`, and the backend `/ws` endpoint accepts inbound control messages. The plan bans protected runtime writes, but must explicitly classify these global controls. It also says both no auto WebSocket and no auto `/sim/ws`; execution should distinguish allowed read-only status streaming from prohibited replay/control/trading streams.

Ultragoal readiness: yes, with WATCH conditions. The seven phases are coherent and testable. Phase 0 must record the Process source matrix and action/WebSocket safety matrix so executors cannot interpret real monitoring or manual gate inconsistently.

Deliberate-mode principle check: no planning-phase mutation observed; truth before polish is honored; interaction as completeness is honored; V2 as floor is honored; API 200 alone is rejected as proof. Safety is honored in principle but needs explicit control/WebSocket inventory. The plan does not add a masking fallback; it attacks the existing fallback-as-success risk through payload-to-DOM, stale, and missing-field failures.

## Root Cause
Previous completion evidence measured renderability, visual scoring, route access, and broad safety checks, but not semantic interaction depth or provenance truthfulness. That allowed V3 to pass with static SVG charts, fixture-backed Process data, a poster-like React Flow map, and fallback/live ambiguity despite V2 already having richer hover, crosshair, and tooltip behavior.

## Findings
1. MEDIUM — Process monitoring source contract is implicit. The plan makes `app.py` endpoint inventory optional, while current V3 Process renders from fixture `DATA.process`. Impact: Ultragoal could build a richer fixture cockpit instead of payload-derived monitoring. Fix: Phase 0 must map run selector, node status, drilldown, queue, logs, SLA, freshness, stale/error/loading, and boundary contracts to exact read-only sources or explicit reference labels; changed payloads must change DOM and missing fields must fail.

2. MEDIUM — Action/WebSocket safety boundary is under-specified. Current V3 Start/Stop can send live `/ws` control frames, and backend `/ws` accepts inbound control messages. Impact: protected runtime control could remain while no-live-order checks pass. Fix: inventory every side-effect-capable control: global Start/Stop, Process export, Lab export, Audit export, approval/export, Backtest mutations, replay controls, settings writes. Define allowed reads, forbidden protected writes, user-gated non-protected actions, and network assertions for no hidden POST or WS control frames.

3. LOW — The 100-point UX/UI rubric needs deterministic scoring. Impact: 100/100 can become subjective across Ultragoal lanes. Fix: convert each bucket into binary or weighted observable checks with DOM assertions, screenshots, interaction traces, and reviewer signoff.

4. LOW — Shared chart primitives need a hard scope ceiling. Impact: over-general primitives could delay the UX fix. Fix: begin with the minimal interaction contract and add specialized replay candle behavior only where V2 parity requires it.

## Recommendations
1. Proceed to Ultragoal Phase 0 only after recording the Process data-source matrix and action/WebSocket safety matrix.
2. Keep the V3-native approach, but implement chart primitives narrowly and prove parity against V2 FitnessChart and SimLiveChart before page sweeps.
3. Treat fallback/reference rendering as labeled state, never as live pass evidence.
4. Make Process either genuinely interactive with pan/select/drilldown or honestly relabeled; do not keep a static map under the React Flow label.
5. Add network assertions for no hidden export, no protected runtime writes, no auto `/sim/ws`, and no live Start/Stop control frames unless explicitly approved as non-protected.

## Architectural Status
WATCH

## Code Review Recommendation
COMMENT

## Trade-offs
| Option | Benefit | Cost/Risk | Architect view |
|---|---|---|---|
| Direct V2 port | Fastest parity; proven interactions | Couples V3 to V2 React/bundle assumptions; does not solve provenance/Process truthfulness | Good fallback tactic, not best architecture |
| V3-native primitives using V2 as spec | Unified interaction, provenance, accessibility, V2 isolation | Needs stronger tests and scope control | Preferred with strict Phase 0 matrices |
| Full React rewrite | Component ecosystem | Highest churn; unnecessary for static remodel; risks V2/default boundary | Reject |
| Disable all WebSockets | Simple safety story | Breaks read-only live status streaming | Too blunt; distinguish status `/ws` from `/sim/ws` and control frames |
| Allow fixture fallback | Useful offline/reference UX | Can mask missing live data | Accept only with visible mode/freshness labels and failing live acceptance when fields are missing |
