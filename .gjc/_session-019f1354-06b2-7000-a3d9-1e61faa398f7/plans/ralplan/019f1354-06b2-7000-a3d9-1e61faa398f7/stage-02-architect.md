## Summary
Revision 2 resolves the prior WATCH/ITERATE blockers for the purpose of starting Ultragoal: the Process source contract, action/WebSocket safety contract, deterministic 100-point rubric, and API-200-not-enough acceptance are now hard Phase 0 gates before any product mutation. This is architecturally ready for Ultragoal Phase 0, not direct implementation; Phase 0 must turn the seeded matrices into checked endpoint/field/selector evidence before executors edit source.

Verdict fields: architectureStatus=`CLEAR`; productStatus=`READY_FOR_ULTRAGOAL_PHASE_0`; codeStatus=`PLANNING_ONLY_READ_ONLY`; recommendation=`APPROVE`.

## Analysis
Spec compliance: the revision preserves the planning-only boundary and repeats the non-negotiables: no product mutation now, no tests/builds/formatters now, V2 remains default, V3 remains explicit/selectable, no broker login, no account trading, no live order, no hidden export, and no protected runtime writes. It also keeps execution pending explicit approval and routes later work through Ultragoal.

Prior review resolution: Architect pass 1 marked WATCH because Process ownership and action/WebSocket authority were implicit. Critic pass 1 required mandatory Process data-source and action/WebSocket safety matrices, deterministic scoring, API-200-not-enough acceptance, and V2/V3 safety assertions. Revision 2 now contains Gate 0A Process data-source matrix, Gate 0B action/WebSocket safety matrix, Gate 0C deterministic 100-point rubric, explicit API-200-not-enough acceptance, V2 parity/inheritance, and Ultragoal Phase 0 ordering. That directly resolves the planning artifact blockers.

File-backed defect context remains correct. `artifacts/ultragoal-recheck-final/final-recheck-scorecard.json` reports PASS with V3 visual 97.93, route-function 100, runtime 100, and safety 100, while Process has `graphItemCount: 0`, proving the old gate could pass without real Process graph depth. `ai_strategy_loop/dashboard/frontend/remodel/src/data.js` begins as dummy/offline prototype data and contains fixture Process KPIs/nodes/logs. `remodel/src/app.js` still has static chart helpers (`lineSvg`, `chart`, `barLineChart`, `candleSvg`) and `renderProcess` renders fixture nodes under “프로세스 맵 (React Flow)” plus an Export Process Map action. `remodel/src/app.js` also binds shell Start/Stop to `sendControl`, and `connectStateSocket` connects `/ws` in live backend mode. `ai_strategy_loop/dashboard/app.py` keeps V2 default unless `dashboard_version=v3|remodel|preview` or `/ui/remodel/*` is used, exposes read-only sources such as `/status`, `/runs`, `/ops_status`, `/pipeline_status`, and `/run_state`, and accepts `/ws` inbound `start`, `stop`, and `final_approval`; `_do_final_approval` calls `export_winner` to the deterministic production strategy DB. `frontend/bundle/app.js` shows the V2 floor: `FitnessChart` uses hover state, nearest generation lookup, guide/tooltip behavior, and `SimLiveChart` uses canvas hover refs, crosshair cursor, OHLC hover model, and requestAnimationFrame drawing.

Steelman antithesis: reject the broader V3-native rebuild. Directly port the V2 chart interactions, relabel Process as a static reference page until a single canonical monitoring endpoint exists, disable shell Start/Stop/final approval in V3, and avoid adapter/WS work. This is the fastest, least risky way to address the visible static chart complaint and it minimizes safety surface.

Synthesis: the antithesis is useful as a fallback, but insufficient. The observed failure is not only missing hover/crosshair; it is a truthfulness problem across fixture provenance, live/fallback ambiguity, Process monitoring claims, and side-effect-capable controls. Revision 2 Option B is the right architecture: V3-native primitives/adapters using V2 as behavioral spec, with Phase 0 contracts preventing another polished-but-false pass.

Tradeoff tensions are now explicit enough for Ultragoal. The plan balances speed versus correctness by deferring actual endpoint/selector inventory to mandatory Phase 0 while forbidding mutation before that inventory exists. It balances safety versus useful live status by distinguishing status reads from replay/control channels and requiring network assertions. It balances V2 parity versus V3 independence by using V2 as a spec/reference, not as a code dependency.

Ultragoal readiness: clear. The revision is not pretending the endpoint schemas are already finalized; it requires Phase 0A output to become a checked matrix with actual endpoint inventory, fields, selectors/data-testids, stale thresholds, and screenshots/assertions. It requires Phase 0B allowlist/denylist, browser network assertions, static search terms, and per-action DOM selectors. That is exactly the right handoff shape for a durable Ultragoal ledger.

No tests, builds, formatters, mutations, staging, commits, pushes, or protected runtime writes were run during this review, per assignment.

## Root Cause
The original false-complete state measured route reachability, visual fit, broad runtime coverage, and broad safety text, but not semantic UX behavior or provenance truth. As a result, static SVG charts, fixture-backed Process data, a poster-like Process map, and live/fallback ambiguity could pass despite V2 already having richer interaction behavior. Revision 2 addresses the root cause by making payload-to-DOM evidence, interaction traces, provenance/freshness, failure states, and network safety mandatory before completion.

## Findings
1. LOW — `stage-02-revision.md` Gate 0A still contains seed rows such as “confirmed Process endpoint” rather than final endpoint schemas. Impact: if an executor skips Phase 0 discipline, Process could again become richer fixture UI instead of monitoring. Fix: Ultragoal Phase 0 must persist the checked matrix with actual endpoints, required fields, selectors/data-testids, stale thresholds, changed-payload DOM assertions, and missing-field failure rules before any source mutation.

2. LOW — `stage-02-revision.md` Gate 0B allows shell Start/Stop as clicked live `/ws` actions, while `app.py` shows those actions can start/stop the loop and `final_approval` can export to production strategy DB. Impact: manual engine controls could be mistaken for harmless UI unless classified against the protected-runtime boundary. Fix: Phase 0B must explicitly classify Start/Stop/final_approval as allowed non-protected manual actions or forbidden protected writes; if not explicitly approved, V3 must disable/gate them and network tests must prove no control frames.

3. LOW — `stage-02-revision.md` Gate 0C defines deterministic scoring categories but not final selectors. Impact: scoring could drift if selectors are not locked before implementation. Fix: Phase 0 must attach selectors/data-testids, screenshots, interaction trace names, network trace assertions, and pass/fail thresholds to each scoring bucket.

No MEDIUM, HIGH, or CRITICAL issues remain in the planning artifact for Ultragoal entry.

## Recommendations
1. Approve the revised Ralplan for Ultragoal Phase 0.
2. Do not begin implementation slices until Phase 0A and Phase 0B are checked into the Ultragoal ledger with endpoint/field/selector/network evidence.
3. Keep Option B: V3-native interaction/provenance primitives using V2 as the behavioral spec and V2 files as read-only reference unless a later approved plan deliberately changes them.
4. Treat fixture/reference rendering as an honest labeled state only; live acceptance must fail on missing fields, unchanged fixture DOM, hidden errors, stale timestamps without stale labels, or green live badges without payload evidence.
5. Preserve safety assertions for V2 default, V3 explicit selection, no hidden export, no protected writes, no page-load POSTs, no auto `/sim/ws`, and no control `/ws` frames unless explicitly classified and user-triggered.

## Architectural Status
CLEAR

## Code Review Recommendation
APPROVE

## Trade-offs
| Option / tension | Benefit | Cost or risk | Architect verdict |
|---|---|---|---|
| Direct V2 interaction port | Fastest chart parity; proven UX behavior | Does not solve fixture provenance, Process truthfulness, or safety/control inventory | Valid fallback tactic, not sufficient as main architecture |
| V3-native primitives + adapters | Unified interaction, provenance, failure states, accessibility, and evidence gates while keeping V2 isolated | Requires strong Phase 0 contracts and selector discipline | Preferred and now ready for Ultragoal |
| Full React rewrite | Rich ecosystem and likely easier interactive components | High churn, risks V2/default boundary, unnecessary for static remodel shell | Reject |
| Disable every WebSocket | Simple safety story | Breaks legitimate read-only status streaming | Too blunt; classify `/ws` status reads separately from `/sim/ws` and control frames |
| Allow fixture fallback | Useful offline/reference UX | Can mask absent live data | Accept only with visible fixture/fallback labels and failing live acceptance |
| Put all detail in Ralplan now | Less Phase 0 work later | Requires endpoint/schema certainty not yet proven and risks planning guesswork | Better to make actual inventory a mandatory Ultragoal Phase 0 gate |
