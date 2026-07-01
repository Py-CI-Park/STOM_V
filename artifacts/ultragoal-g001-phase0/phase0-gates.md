# Ultragoal G001 Phase 0 Gates

- Generated: 2026-06-29T12:57:36Z
- Plan: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/plans/ralplan/019f05e9-d676-7000-9c61-3c206a2d4031/pending-approval.md`
- Scope: matrices/selectors only; no product-source mutation in this story.

## Hard rules
- HTTP 200 alone never satisfies a live dashboard check; required fields must visibly drive DOM assertions.
- Reference/demo fixture data is allowed only when explicitly labeled and must never pass as live evidence.
- No mutating POST, export, protected write, /sim/ws connection, or outbound WS control frame may occur on page load.
- V2 remains default until all deterministic V3 UX/UI gates pass 100/100 with no zero category.
- No live order, broker login, account trading, hidden production export, or serial-key behavior may be introduced.

## Process data-source matrix

| ID | Endpoint/feed | Required fields | Target DOM assertions | Missing-field failure |
|---|---|---|---|---|
| `shell-health` | GET /health<br>GET /status | health.status<br>health.contract_version<br>status.status<br>status.run_id<br>status.provider<br>status.bt_timeframe | [data-testid="shell-rest-health"]: text and badge tone reflect health.status; HTTP 200 alone is insufficient<br>[data-testid="shell-run-status"]: text reflects status.status or explicit stale/error label<br>[data-testid="shell-run-id"]: run id is populated from status.run_id or shows unavailable, never fixture-as-live | fail Phase 0C data provenance and block completion until DOM shows honest unavailable state |
| `loop-status` | GET /status<br>WS /ws inbound state frames | status.status<br>status.run_id<br>status.current_gen<br>status.max_generations<br>status.generations[]<br>status.latest.message<br>status.latest.phase | [data-testid="condition-generation-progress"]: progress value equals current_gen/max_generations and changes when payload changes<br>[data-testid="condition-live-message"]: message text comes from latest.message or explicit missing label<br>[data-testid="condition-generation-table"]: row count equals validated generations length, not fixture length in live mode | show stale/malformed payload banner; do not reuse DATA.overview fixture values as live success |
| `process-nodes` | GET /status<br>GET /runs<br>target: derived process model from validated phase/status fields | process.nodes[].id<br>process.nodes[].title<br>process.nodes[].status<br>process.nodes[].started_at|updated_at<br>process.nodes[].items|count<br>process.nodes[].source | [data-testid="process-node"]: node count and each status derive from validated payload or explicit reference model label<br>[data-testid="process-node-active"]: active node matches current phase/status from live payload<br>[data-testid="process-provenance"]: shows source=live|reference|demo and payload timestamp | do not render fixed Generation/Backtest/Scoring poster as live; mark as reference/static and score process reality 0 until fixed |
| `process-logs` | GET /status latest/error fields<br>GET /runs<br>target: future logs feed if exposed | logs[].time<br>logs[].level<br>logs[].message<br>logs[].source<br>selected_node.id | [data-testid="process-log-row"]: row text and level come from payload; empty log state is explicit<br>[data-testid="process-node-drilldown"]: clicking a node filters or annotates logs for that node<br>[data-testid="process-log-stale-state"]: stale/no-log states are visible and not hidden behind fixture text | logs panel must show no-live-logs state; fixture logs cannot satisfy live monitoring completion |
| `queues-workers` | GET /status resources if present<br>GET /ops_status<br>target: queue/worker payload | workers.total<br>workers.active<br>workers.idle<br>queue.depth<br>queue.throughput<br>resource.cpu|memory optional | [data-testid="process-worker-summary"]: worker counts equal payload or unavailable label<br>[data-testid="process-queue-depth"]: queue depth equals payload and changes under fixture-injection test<br>[data-testid="process-resource-health"]: health cards cite source endpoint and timestamp | mark telemetry unavailable; do not invent 16 workers / queue 1000 in live mode |
| `boundary-contracts` | static contract matrix artifact<br>frontend runtime assertions | contract.id<br>method<br>endpoint<br>autoLoadPolicy<br>owner<br>modeBehavior<br>reason for gated actions | [data-testid="contract-matrix-row"]: every gated endpoint has owner/reason/mode behavior<br>[data-testid="contract-mode-note"]: reference/demo/live behavior is visible<br>[data-testid="contract-autoload-verdict"]: auto-load allowed only for safe GET/read endpoints | block safety/governance score until matrix is visible and machine-checked |
| `runs-archive` | GET /runs<br>GET /run_state?run_id=<br>GET /runs/compare?ids= | runs[].run_id<br>runs[].status<br>runs[].started_at|created_at<br>runs[].best_graded|profit|mdd optional but labeled | [data-testid="history-run-row"]: rows reflect /runs, not fixed data, and preserve selected run id<br>[data-testid="run-selector"]: selection drives dependent detail/chart panels<br>[data-testid="run-compare-launcher"]: compare controls require selected real run ids | history page shows empty/error state and cannot pass V2 parity if rows are fixture-only in live mode |
| `stale-error-loading` | fetchJson/fetchText failures<br>malformed payload injection<br>timestamp freshness check | source<br>mode<br>backendUrl<br>fetchedAt|payloadTimestamp<br>error.message when failed | [data-testid="page-loading-state"]: visible while required reads are pending<br>[data-testid="page-stale-state"]: visible when freshness threshold is exceeded<br>[data-testid="page-error-state"]: visible with actionable endpoint/message on failed/malformed data | no page can substitute fixture values without a visible source/fallback label |

## Action/WebSocket safety matrix

| ID | Trigger | Auto on load | Allowed when | Forbidden | Blocker |
|---|---|---:|---|---|---|
| `shell-start` | user click [data-action="start"] | False | live mode + explicit user click only | auto start on page load<br>reference/demo control frame | any start frame is observed during load or reference/demo |
| `shell-stop` | user click [data-action="stop"] | False | live mode + explicit user click only | auto stop on load<br>hidden STOP flag write | stop frame or STOP write occurs without user action |
| `state-ws` | live page load may open receive-only status socket | True | live mode receive-only; outbound control frames only after explicit user actions | final_approval/start/stop sent on load<br>reference/demo /ws connection | control frame sent before user action or reference/demo opens /ws |
| `final-approval-export` | explicit approval modal action with required names/check/note | False | manual human approval only; export destination not client-selectable | hidden export<br>client-selected dest_strategy_db<br>export without approval | export/final_approval occurs without explicit validated user action |
| `record-decision` | manual audit note submit | False | manual append-only governance record | auto decision write<br>edit/delete ledger<br>fake USER_ACK | record_decision POST observed without user submit |
| `generic-exports` | explicit user action behind human gate | False | read-only report download if non-production; production export only after human approval | hidden production export<br>protected runtime writes<br>auto file write | hidden export or protected path write occurs |
| `backtest-post-endpoints` | manual researcher action | False | explicit user action only after parameter validation; never reference/demo | POST /bt/run on load<br>POST /bt/job/cancel on load<br>POST strategy save/delete/portfolio/meta on load | any /bt POST is observed during load or hidden probe |
| `replay-sim-ws` | manual replay start/connect | False | manual live replay only; reference/demo never opens stream | auto /sim/ws on page load<br>fake stream success in reference/demo | /sim/ws opens on page load or reference/demo |
| `settings-localStorage` | explicit input change | False | live mode explicit user change only for stom_remodel_base_url | credential storage<br>strategy/export state stored in localStorage<br>reference/demo writes | unexpected key write or protected data in localStorage |
| `theme-local-ui` | user click [data-action="theme"] | True | local class toggle only; no backend/network mutation | backend call<br>protected write | theme action calls backend or writes protected data |

## Deterministic 100-point UX/UI rubric

| Category | Points | Selectors/evidence | Zero blocks? |
|---|---:|---|---:|
| `visual-hierarchy` | 10 | selectors: [data-testid="page-root"]<br>[data-testid="panel"]<br>[data-testid="chart-container"]<br>evidence: per-route screenshot<br>no overlap detector<br>readability/density checklist | True |
| `interaction-depth` | 16 | selectors: [data-testid="interactive-chart"]<br>[data-testid="chart-tooltip"]<br>[data-testid="chart-crosshair"]<br>[data-testid="process-node"]<br>evidence: hover/focus/click transcript<br>keyboard navigation transcript | True |
| `data-provenance` | 14 | selectors: [data-testid="provenance-cue"]<br>[data-testid="source-mode"]<br>[data-testid="freshness"]<br>evidence: payload-to-DOM assertion report<br>source/mode/backend/run/timestamp screenshot | True |
| `v2-parity-plus-improvement` | 12 | selectors: [data-testid="v2-parity-row"]<br>evidence: V2/V3 comparison table<br>inherited/improved behavior list | True |
| `process-monitoring-reality` | 14 | selectors: [data-testid="process-node"]<br>[data-testid="process-log-row"]<br>[data-testid="process-worker-summary"]<br>evidence: process payload injection test<br>node drilldown transcript<br>stale/error state screenshots | True |
| `safety-governance` | 14 | selectors: [data-testid="safety-footer"]<br>[data-testid="human-approval-gate"]<br>[data-testid="append-only-audit"]<br>evidence: network denylist report<br>no protected write report<br>manual gate screenshots | True |
| `accessibility` | 8 | selectors: [tabindex]<br>[aria-label]<br>[role]<br>evidence: keyboard focus transcript<br>contrast report<br>non-hover value audit | True |
| `performance-responsiveness` | 4 | selectors: [data-testid="interaction-performance"]<br>evidence: large dataset hover/render timing report | False |
| `failure-state-quality` | 4 | selectors: [data-testid="page-loading-state"]<br>[data-testid="page-stale-state"]<br>[data-testid="page-error-state"]<br>evidence: empty/loading/stale/malformed/network state screenshots | True |
| `evidence-package` | 4 | selectors: artifact manifest<br>evidence: screenshots<br>trace artifacts<br>scorecard<br>V2/V3 compare<br>network assertions | True |

## Route coverage targets

| Page | V3 route | V2 route | Required surfaces |
|---|---|---|---|
| `condition` | `/ui/remodel/condition` | `/ui/evolution` | overview charts<br>generation table<br>strategy inspector<br>approval gate |
| `process` | `/ui/remodel/process` | `/ui/evolution/process` | process nodes<br>logs<br>queue/workers<br>contracts<br>run selector |
| `history` | `/ui/remodel/history` | `/ui/evolution/records` | run table<br>filters<br>details<br>compare |
| `lab` | `/ui/remodel/lab` | `/ui/evolution/lab` | research docs<br>criteria<br>glossary<br>experiment output |
| `workbench` | `/ui/remodel/workbench` | `/ui/evolution/workbench` | candidate grid<br>heatmap<br>metric compare<br>review queue |
| `audit` | `/ui/remodel/audit` | `/ui/evolution/verdict` | append-only ledger<br>hashes<br>note validation<br>approval/export separation |
| `backtest` | `/ui/remodel/backtest` | `/ui/backtest` | jobs<br>result<br>report<br>compare<br>overlay<br>montecarlo |
| `chart-replay` | `/ui/remodel/chart-replay` | `/ui/chart-replay` | OHLCV tooltip<br>signals<br>seek<br>crosshair<br>manual /sim/ws gate |

## Exit criteria
- Every process matrix row has endpoint/feed, required fields, target DOM assertions, fallback label, and missing-field failure rule.
- Every safety row has trigger, auto-load decision, forbidden behavior, target assertions, and blocker rule.
- The rubric totals 100 points and every zero-blocking category is explicit.
- Later implementation may mutate product frontend only after these matrices are used as selectors for tests/reviews.
