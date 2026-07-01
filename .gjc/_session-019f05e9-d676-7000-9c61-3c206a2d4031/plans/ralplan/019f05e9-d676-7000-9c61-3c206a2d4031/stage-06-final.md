# Pending Approval Plan: STOM Dashboard V3 UX/UI 100% Rebuild Better Than V2

Status: PENDING APPROVAL. This is a planning artifact only. No product source was mutated in this Ralplan phase.

## Decision
Rebuild V3 as a genuinely live-data-driven, interactive, UX/UI-expert-grade dashboard while preserving V2 as the default baseline until V3 passes deterministic 100/100 gates. V3 remains explicit/selectable through `dashboard_version=v3` and `/ui/remodel/*` until separately approved for default use.

## Drivers
1. User trust: V3 must stop looking like dummy/fixture output.
2. V2 is the floor: V3 must inherit or exceed V2 hover, tooltip, crosshair, replay, and process clarity.
3. API 200 is insufficient: visible DOM must be driven by validated payload fields.
4. Safety envelope is mandatory: no live order, broker login, account trading, hidden export, protected runtime writes.
5. Evidence must be deterministic: screenshots, interaction transcripts, network assertions, provenance checks, V2/V3 compare.

## ADR
### Alternatives considered
| Option | Decision | Reason |
| --- | --- | --- |
| Direct V2 port | Rejected as primary | Fast but couples V3 to V2 bundle assumptions and does not solve provenance/process truthfulness. |
| V3-native interaction/provenance layer using V2 as behavioral spec | Chosen | Fixes charts, process, provenance, safety, and evidence together while preserving V2. |
| Full React rewrite | Rejected | Too broad and high churn for this stage. |
| Keep current V3 visual shell with minor polish | Rejected | Would preserve the dummy/static UX failure. |

### Consequences
- Phase 0 matrices are mandatory before implementation.
- Current static SVG helpers are not acceptable as final chart UX.
- Reference/demo fixture data remains allowed only when explicitly labeled; live mode must fail if required data is absent.
- V2 remains default until V3 deterministic gates pass.

## Consensus receipts
- Planner revision: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f1343-f51d-7000-aed1-3bb8c3807e3b/plans/ralplan/019f1343-f51d-7000-aed1-3bb8c3807e3b/stage-02-revision.md`
- Architect pass 2: CLEAR / APPROVE, `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f1354-06b2-7000-a3d9-1e61faa398f7/plans/ralplan/019f1354-06b2-7000-a3d9-1e61faa398f7/stage-02-architect.md`
- Critic pass 2: APPROVE, `C:/System_Trading/STOM/STOM_V.wt-dev/.gjc/_session-019f1358-4fc2-7000-9b51-c15fc131d130/plans/ralplan/019f1358-4fc2-7000-9b51-c15fc131d130/stage-02-critic.md`
- Intent reconciliation: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/plans/ralplan/019f05e9-d676-7000-9c61-3c206a2d4031/stage-04-post-interview.md`

## Current diagnosis
Previous gates passed because they measured route access, visual resemblance, broad runtime responses, graph containment, and safety text. They did not prove UX/UI completeness. Current V3 issues are real blockers:
- `remodel/src/data.js` is explicitly dummy/offline prototype data.
- `remodel/src/app.js` renders static SVG charts without pointer-state owner, nearest-datum lookup, crosshair, accessible tooltip, or keyboard chart exploration.
- Process renders fixed fixture nodes/logs and can look like a static poster rather than live monitoring.
- V2 has real hover/canvas behavior and therefore remains a stronger UX floor.

## Hard Phase 0 gates before any product-source mutation
### Gate 0A: Process data-source matrix
For Shell health, Loop status, Process nodes, Process logs, queues/workers, boundary contracts, runs archive, stale state, and error state, document endpoint/feed, required fields, DOM assertion selector/test id, fallback/reference label, and missing-field failure rule. Hard rule: 200 OK without required fields and visible DOM change fails.

### Gate 0B: Action/WebSocket safety matrix
Classify Shell Start/Stop, `/ws`, final approval/export, record_decision, generic exports, backtest POST endpoints, replay `/sim/ws`, settings/localStorage, and theme/local UI. Hard rule: no mutating POST, export, `/sim/ws`, protected write, or WS control frame on page load.

### Gate 0C: Deterministic 100-point UX/UI rubric
| Category | Points | Completion evidence |
| --- | ---: | --- |
| Visual hierarchy | 10 | all V3 routes screenshot-clean, no overlap, readable density |
| Interaction depth | 16 | hover/focus/click tooltip/crosshair/selection on every required chart and process node |
| Data provenance | 14 | source/mode/backend/run/timestamp/freshness/fallback visible and asserted |
| V2 parity plus improvement | 12 | V3 inherits/exceeds V2 hover, tooltip, crosshair, help, pending-live honesty |
| Process monitoring reality | 14 | run selector, nodes, logs, queues/workers, contracts, stale/error/loading states payload-driven |
| Safety/governance | 14 | no broker/account/live order/hidden export/protected write/auto mutating calls/auto sim WS |
| Accessibility | 8 | keyboard focus, aria/labels, non-hover essential values, contrast |
| Performance/responsiveness | 4 | smooth hover/render under large data |
| Failure-state quality | 4 | empty/loading/stale/malformed/network states visible and useful |
| Evidence package | 4 | screenshots, traces, scorecards, V2/V3 compare, network assertions |

Hard rule: any zero category blocks completion.

## Implementation phases after approval
| Phase | Goal | Output |
| --- | --- | --- |
| 0 | Gate matrices and scoring selectors | Process source matrix, action/WS safety matrix, deterministic rubric selectors |
| 1 | V2/V3 baseline inventory | exact V2 behaviors to preserve/exceed, screenshots, route map |
| 2 | Interactive chart primitives | shared scales, nearest point, tooltip, crosshair, keyboard focus, legend highlight |
| 3 | Process monitoring rebuild | payload-driven process cockpit with drilldown/logs/queue/worker/contracts/stale/error states |
| 4 | Provenance and safety hardening | live/reference/demo separation, no fallback-as-success, network denylist |
| 5 | Page sweep | condition, process, history, lab, workbench, audit, backtest, chart replay complete UX pass |
| 6 | Verification | unit/integration/browser/network/visual/V2 compare gates all deterministic |
| 7 | Final evidence | 100/100 scorecard, screenshots/contact sheet, trace artifacts, PR-ready report |

## Page deliverables
| Page | Required UX/UI completion |
| --- | --- |
| Condition AI | interactive fitness/profit/equity/quality/backtest charts, source-linked inspector, real generation table, gated approval panel |
| Process | actual monitoring cockpit, payload-driven nodes/logs/queue/workers/contracts, node drilldown, stale/error/loading states |
| History | filter/sort/detail/compare run records, interactive charts, selected run provenance |
| Lab | research docs/criteria/glossary/experiment output connected to real or labeled reference data |
| Workbench | selectable candidates, heatmaps, metric compare, review queue, evidence source ids |
| Audit | append-only decision chain, required note validation, hashes, approval/export separation |
| Backtest | job/result/report/compare/overlay/montecarlo exploration, no auto mutating endpoints |
| Chart Replay | OHLCV tooltip, buy/sell marker tooltip, seek/crosshair, keyboard focus, no auto `/sim/ws` |

## Verification plan
- Unit: chart nearest lookup, scales, tooltip formatting, crosshair coords, provenance mapping, safety classifier.
- Integration: payload-to-DOM assertions, fixture inertness, Process matrix checks, action/WS network classifier.
- Browser: hover/focus/click every chart and Process node; capture screenshots/contact sheets; test empty/loading/stale/error/malformed payload states.
- Network: assert no POST/export/`/sim/ws` on load; no reference/demo WS; live WS bounded and labeled.
- V2/V3 compare: V3 must match or exceed V2 feature depth while V2 remains default.
- Safety: no live order, broker login, account trading, hidden export, protected runtime writes.

## Acceptance criteria
Execution cannot be complete until Phase 0 matrices are complete, V2 remains default, V3 live mode uses validated payload-to-DOM mappings, every core chart has tooltip/crosshair/focus or accessible equivalent, Process is real monitoring or honestly labeled reference mode, safety audits pass, deterministic score is 100/100 with no zero category, browser evidence includes screenshots and interaction transcripts, and final report lists V2 behavior inherited plus V3 improvements.

## Intent Reconciliation
Open confirmations pending because this Ralplan ran automated:
1. V2 remains default until V3 passes 100/100 deterministic UX/UI gate.
2. V3 implementation may use V3-native interactive primitives rather than direct V2 bundle port.
3. Live mode completion fails when data does not visibly drive DOM, even if API returns 200.
4. Start/Stop, export, approval, `/ws`, `/sim/ws`, backtest POSTs, settings/localStorage are classified before mutation.

## Follow-ups after approval
Invoke Ultragoal with this pending plan. Execution should start with Phase 0 only; product source mutation begins only after Phase 0 matrices are recorded and reviewed.
