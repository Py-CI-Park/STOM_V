# TICK P7 Timeout Unblock And Live Strategy Visibility 20260605

## TL;DR
> **Summary**: Continue from the blocked P7 observability page. First make the dashboard show the active buy/sell strategy names, code, previous-generation diff, and honest empty/stale/error states on the main page. Then run a bounded seed-timeout diagnostic ladder before any 2023-2025 training retry.
> **Deliverables**:
> - Source-route parity proof for `/strategy_code`, `/strategy_diff`, `/status`, and frontend fetches.
> - Additive route payload status fields for missing/stale/empty strategy-code and diff states.
> - Main-page Active Strategy panel with buy/sell names, bounded code preview, code viewer link, previous diff summary, and AI context link.
> - P3 timeout unblock evidence using small seed diagnostics before the full January preflight retry.
> - Final decision card with page progress, terminal verdict, and next command.
> **Effort**: L
> **Parallel**: YES - route/frontend work can run while diagnostic configs are prepared after P0.
> **Critical Path**: P0 safety/route baseline -> P1 route contract -> P2 active strategy resolver -> P3 main-page panel -> P5 diagnostic ladder -> P7 decision card

## Context
### Source Request
The user asked to directly proceed with the recommended `$ulw-plan` for:

- unblocking the TICK P7 seed warm-backtest timeout before retrying 2023-2025 training;
- improving the dashboard so the currently active buy/sell strategy names and code are visible on the main page;
- showing previous-generation diff and clear stale/empty/error states;
- preserving official engines, hard gates, protected paths, final approval/export restrictions, and OOS restrictions.

### Canonical Evidence
- `.omo/evidence/tick-p7-observability-bounded-training-20260605/p3-preflight-blocked.md`
  - `tick_p7_preflight_observable_20260605`
  - `2025-01-01..2025-01-31`, tick, `09:00:00..09:30:00`
  - seed `C_T_900_920_U2_B` / `C_T_900_920_U2_S`
  - warm timeout `300s`, elapsed `328.3s`, no CSV, DB status `error`
- `.omo/evidence/tick-p7-observability-bounded-training-20260605/p4-train-blocked.md`
  - 2023-2025 training was not started because the bounded preflight timed out.
- `.omo/evidence/tick-p7-observability-bounded-training-20260605/p7-decision-card.md`
  - observability improved, but there is no training pool, no OOS, and no human-level claim.

### Current Code Findings
- Backend full-code route exists:
  - `ai_strategy_loop/dashboard/app.py:667` `_strategy_code_payload`
  - `ai_strategy_loop/dashboard/app.py:1525` `GET /strategy_code`
- Backend previous-diff route exists:
  - `ai_strategy_loop/dashboard/app.py:792` `_strategy_diff_payload`
  - `ai_strategy_loop/dashboard/app.py:1546` `GET /strategy_diff`
- Main dashboard currently opens full code through a modal:
  - `ai_strategy_loop/dashboard/frontend/code-viewer.jsx:87`
  - `ai_strategy_loop/dashboard/frontend/strategy-inspector.jsx:94`
  - `ai_strategy_loop/dashboard/frontend/app.jsx:291`
- Main page currently shows only streaming partial generation code, not finalized active full code:
  - `ai_strategy_loop/dashboard/frontend/phase-detail.jsx:186`
- Generations table shows gist plus a code-view button:
  - `ai_strategy_loop/dashboard/frontend/table.jsx:172`
- Warm timeout flow:
  - `ai_strategy_loop/controller/loop.py:1037` prepares `WarmBacktestSession`
  - `ai_strategy_loop/controller/loop.py:1238` passes `config.bt_warm_run_timeout`
  - `cli/warm_session.py:360` resolves runtime timeout
  - `cli/warm_session.py:377` enforces `proc.join(timeout=timeout)`
  - `cli/warm_session.py:459` recovers after timeout/failure

### Metis Review Incorporated
- Define "active strategy" explicitly instead of leaving it to executor judgment.
- Preserve `/strategy_code` compatibility: keep HTTP 200/no-throw behavior and add status fields instead of replacing current keys.
- Avoid putting full strategy code into `/status` polling; expose identity in state and fetch code through `/strategy_code`.
- Define exact timeout diagnostic bounds and pass/fail thresholds.
- Keep main-page code height-bounded to avoid layout degradation.
- Do not start 2023-2025 training until the diagnostic ladder passes.

## Non-Negotiable Constraints
- Do not edit official backtest engines:
  - `backtest/backengine_*.py`
  - `backtest/back_static.py`
- Do not relax hard gates or edit `compute_fitness` for this page.
- Do not modify protected/runtime paths:
  - `_database/`
  - `_database_v3k_shadow/`
  - `_log/`
  - `backup/`
  - `*.db`
  - `backtest/graph/`
  - `.omx/reports/`
  - `v3k_settings*.json`
  - `_v3k_sidecar/v3k_gui_settings.json`
- Do not call or wire:
  - `final_approval`
  - `export_winner`
  - live broker/KHOPENAPI connect/login/order paths
  - V3K gate actions
  - blanket `taskkill`
- New behavior must be additive/default-safe.
- No 2022/2026 OOS until a single frozen promotion candidate exists.
- Existing dirty worktree changes are baseline context; do not revert them.
- If committing later, stage files explicitly and use Korean commit title/body per repo rules.

## Definitions
### Active Strategy Resolution
Use this deterministic source order for the main-page Active Strategy panel:

1. If `state.status == "complete"` and `state.winner.gen_no` is a number, active source is `winner`.
2. Else if `state.best.gen_no` is a number, active source is `best`.
3. Else use the newest finalized generation row by `gen_no` from `state.generations`.
4. Else, if the loop is currently generating and `state.current_run.generation` has partial code, show it as `streaming_partial`.
5. Else show `status=no_strategy`.

Only names and identity may be derived from `/status`. Full code must be fetched through `/strategy_code?run=<run_id>&gen=<gen_no>` to avoid heavy DB reads on every status poll.

### Route Error Contract
Do not turn missing code/diff into HTTP 404 for dashboard use. Preserve current HTTP 200/no-throw behavior and add fields:

```json
{
  "ok": true,
  "code_status": "ok|missing_run|missing_generation|empty_code|db_error|streaming_partial|no_strategy",
  "diff_status": "ok|no_previous_generation|missing_run|missing_generation|empty_code|db_error",
  "reason": "",
  "run_id": "",
  "gen_no": 0,
  "base_gen": null,
  "buy_name": "",
  "sell_name": "",
  "buy_code": "",
  "sell_code": ""
}
```

Keep existing `buy_code`, `sell_code`, `buy_name`, and `sell_name` keys backward compatible.

### Timeout Diagnostic Ladder
Do not start the 2023-2025 training retry in this plan unless all diagnostic gates pass.

Use evidence root:

```text
.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/
```

Diagnostic run IDs:

1. `tick_p7_seed_diag_5m_20260605`
   - period: `2025-01-01..2025-01-03`
   - timeframe: `tick`
   - window: `09:00:00..09:05:00`
   - seed buy/sell: `C_T_900_920_U2_B` / `C_T_900_920_U2_S`
   - `max_generations=1`
   - `bt_engine_mode=warm`
   - `bt_warm_run_timeout=120`
   - wall-clock cap: `240s`
   - expected pass: process exits, CSV exists, DB row status is `success` or explicit non-timeout terminal status
2. `tick_p7_seed_diag_10m_20260605`
   - period: `2025-01-01..2025-01-10`
   - window: `09:00:00..09:10:00`
   - `bt_warm_run_timeout=180`
   - wall-clock cap: `360s`
   - start only if 5m diagnostic passes
3. `tick_p7_seed_preflight_jan_retry_20260605`
   - period: `2025-01-01..2025-01-31`
   - window: `09:00:00..09:30:00`
   - `bt_warm_run_timeout=300`
   - wall-clock cap: `600s`
   - start only if 10m diagnostic passes

If any diagnostic fails, stop and write blocker evidence. Do not start `2023-01-01..2025-12-31` training.

## Deliverables
- `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p0-safety-route-baseline.md`
- `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p1-route-contract.md`
- `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p2-active-strategy-contract.md`
- `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p3-main-page-active-strategy-smoke.md`
- `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p4-stale-empty-error-state-smoke.md`
- `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p5-timeout-diagnostic-ladder.md`
- `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p6-training-retry-gate.md`
- `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p7-decision-card.md`
- Optional configs under the same evidence root:
  - `p5-seed-diag-5m-config.json`
  - `p5-seed-diag-10m-config.json`
  - `p5-seed-preflight-jan-retry-config.json`

## Terminal Outcomes
Exactly one terminal verdict must be written in `p7-decision-card.md`:

- `READY_FOR_2023_2025_TRAINING_RETRY`
  - route/UI contracts pass;
  - full January seed preflight retry passes;
  - no protected paths changed;
  - no OOS/export/final approval occurred.
- `BLOCKED_WITH_TIMEOUT_EVIDENCE_NO_OOS`
  - route/UI contracts may pass, but one diagnostic timeout or reset failure blocks training;
  - evidence identifies the first failing diagnostic gate.
- `BLOCKED_WITH_ROUTE_OR_UI_REGRESSION_NO_TRAINING`
  - route parity, strategy-code/diff payloads, or main-page visibility regressions remain.

## Verification Strategy
Use focused tests first, then final guard commands.

```powershell
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_dashboard_strategy_prompt_frontend.py tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_profit_codeview.py tests/unit/test_dashboard_route_parity.py -q
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_dashboard_engine_progress_contract.py tests/unit/test_dashboard_phase_mapping.py tests/unit/test_process_timing.py -q
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_loop_robustness.py tests/unit/test_dashboard_backtest_detail.py tests/unit/test_dashboard_chart_explanations.py -q
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json
```

If a fresh dashboard smoke is needed, use an owned alternate port first, not the existing user-facing `8770` process:

```powershell
$env:PYTHONUTF8='1'; python -m ai_strategy_loop.dashboard.app --host 127.0.0.1 --port 8796
```

If that command is not the correct server entry point in this workspace, discover the existing dashboard launcher from current scripts before starting anything.

## TODOs

- [x] P0 - Safety Snapshot And Route Baseline
- [x] P1 - Additive Strategy Route Contract Hardening
- [x] P2 - Active Strategy Identity Contract
- [x] P3 - Main-Page Active Strategy Panel
- [x] P4 - Previous Diff And AI Context Linkage
- [x] P5 - Seed Timeout Diagnostic Ladder
- [x] P6 - Training Retry Gate
- [x] P7 - Decision Card And Page Progress

### P0 - Safety Snapshot And Route Baseline
**Goal**: Prove current source/routes and runtime status before edits.

**Files to inspect only**:
- `ai_strategy_loop/dashboard/app.py`
- `ai_strategy_loop/dashboard/frontend/app.jsx`
- `ai_strategy_loop/dashboard/frontend/code-viewer.jsx`
- `ai_strategy_loop/dashboard/frontend/strategy-inspector.jsx`
- `ai_strategy_loop/dashboard/frontend/table.jsx`
- `ai_strategy_loop/dashboard/frontend/phase-detail.jsx`
- `.omo/evidence/tick-p7-observability-bounded-training-20260605/*.md`

**Actions**:
- Capture branch, HEAD, dirty worktree, and protected-path status.
- Capture whether source `create_app()` contains `/strategy_code`, `/strategy_diff`, and `/status`.
- If `http://127.0.0.1:8770/ui/` still shows `strategy_diff HTTP 404`, treat it as likely stale/wrong live server until proven otherwise.
- Do not kill or restart existing `8770` unless the process is proven to be owned by this work item.

**Acceptance Criteria**:
- `p0-safety-route-baseline.md` contains route list, dirty-file summary, protected-path status, and stale-server hypothesis.
- No source file is changed in P0.
- No protected path is changed or staged.

**QA Scenarios**:
```text
Scenario: Source route parity baseline
  Run: python snippet or pytest route parity test against create_app()
  Expected: /strategy_code, /strategy_diff, and /status exist in source app.
  Evidence: p0-safety-route-baseline.md

Scenario: Existing live server mismatch
  Run: fetch 8770 OpenAPI only if server is already running.
  Expected: If route missing live but present in source, mark stale server; do not edit code for this alone.
  Evidence: p0-safety-route-baseline.md
```

### P1 - Additive Strategy Route Contract Hardening
**Goal**: Make strategy-code and diff routes self-describing without breaking current callers.

**Likely files**:
- `ai_strategy_loop/dashboard/app.py`
- `tests/unit/test_dashboard_profit_codeview.py`
- `tests/unit/test_dashboard_strategy_diff.py`
- `tests/unit/test_dashboard_route_parity.py`

**Actions**:
- Add tests first for:
  - missing run;
  - missing generation;
  - generation exists but code is empty;
  - gen0 previous diff;
  - DB lookup exception or code-read failure if practical through monkeypatch.
- Preserve HTTP 200 for dashboard invalid/empty cases.
- Add the route status fields defined above.
- Keep existing keys and route parameters:
  - `/strategy_code?run=<run>&gen=<gen>`
  - `/strategy_diff?run_id=<run>&gen_no=<gen>&base_gen=<optional>`

**Acceptance Criteria**:
- Existing tests still pass without frontend changes.
- New tests prove 404 is not returned from source routes.
- Missing/stale/empty cases are visible as payload state, not swallowed silently.

**QA Scenarios**:
```text
Scenario: /strategy_code missing generation
  Expected: HTTP 200, buy_code="", sell_code="", code_status="missing_generation" or equivalent reason.

Scenario: /strategy_diff gen0
  Expected: HTTP 200, diff_status="no_previous_generation", base_gen=null, no exception.
```

### P2 - Active Strategy Identity Contract
**Goal**: Give the frontend a deterministic active-strategy identity without placing full code into `/status`.

**Likely files**:
- `ai_strategy_loop/dashboard/frontend/app.jsx`
- `ai_strategy_loop/dashboard/frontend/panels.jsx`
- `ai_strategy_loop/dashboard/frontend/code-viewer.jsx`
- `tests/unit/test_dashboard_strategy_prompt_frontend.py`
- Optional backend/state files only if identity cannot be inferred safely:
  - `ai_strategy_loop/controller/contract.py`
  - `ai_strategy_loop/controller/state.py`
  - `ai_strategy_loop/dashboard/app.py`

**Actions**:
- Prefer a frontend resolver that uses existing state fields:
  - `winner`
  - `best`
  - `generations`
  - `current_run.generation`
- If this is too brittle, add an additive `/status.latest.active_strategy` identity object with names/gen/status only.
- Do not fetch full code from `/status`.
- Do not rename `CodeViewer` or `StrategyInspectorTabs`.

**Acceptance Criteria**:
- Resolver returns one of:
  - `winner`
  - `best`
  - `latest_generation`
  - `streaming_partial`
  - `no_strategy`
- Running-generation partial code is labeled `streaming_partial`.
- Completed/error/preflight-timeout states show latest finalized generation or explicit `no_strategy`.

**QA Scenarios**:
```text
Scenario: Complete run has winner
  Expected: Active source is winner and code fetch uses winner gen_no.

Scenario: Running generation has only partial code
  Expected: Active source is streaming_partial; full-code fetch is disabled or clearly unavailable.
```

### P3 - Main-Page Active Strategy Panel
**Goal**: Show the user what strategy is currently being used/researched without needing to open a modal first.

**Likely files**:
- `ai_strategy_loop/dashboard/frontend/app.jsx`
- `ai_strategy_loop/dashboard/frontend/panels.jsx`
- `ai_strategy_loop/dashboard/frontend/code-viewer.jsx`
- `ai_strategy_loop/dashboard/frontend/strategy-inspector.jsx`
- `tests/unit/test_dashboard_strategy_prompt_frontend.py`

**Actions**:
- Add or extend a compact main-page panel near the current run/strategy area.
- Always show:
  - source label (`winner`, `best`, `latest_generation`, `streaming_partial`, `no_strategy`);
  - run ID;
  - generation number;
  - buy name;
  - sell name;
  - code status;
  - diff status.
- Show buy/sell code in a height-bounded, collapsed-by-default preview.
- Provide buttons/controls to open the existing full CodeViewer modal and StrategyInspector tabs.
- Do not render huge code blocks unbounded.
- Avoid exact Korean text assertions in tests; use stable component markers/classes or English/ASCII labels if needed.

**Acceptance Criteria**:
- The main page contains an always-visible active strategy section.
- The user can inspect buy/sell names and see whether code is loaded, empty, stale, or streaming partial.
- The full existing modal path still works.
- UI remains usable on desktop and mobile widths.

**QA Scenarios**:
```text
Scenario: Active finalized generation
  Expected: Panel shows buy/sell names, a bounded code preview, and opens CodeViewer.

Scenario: Empty code payload
  Expected: Panel shows explicit empty/unavailable state, not a blank area or JS exception.
```

### P4 - Previous Diff And AI Context Linkage
**Goal**: Make previous-generation comparison visible from the main page while reusing existing inspector logic.

**Likely files**:
- `ai_strategy_loop/dashboard/frontend/strategy-inspector.jsx`
- `ai_strategy_loop/dashboard/frontend/code-viewer.jsx`
- `ai_strategy_loop/dashboard/frontend/app.jsx`
- `tests/unit/test_dashboard_strategy_prompt_frontend.py`
- `tests/unit/test_dashboard_strategy_diff.py`

**Actions**:
- Use `/strategy_diff` as the canonical diff source.
- For gen0, show `no_previous_generation`; do not compare to previous run unless that is explicitly added later.
- Add a compact diff status/summary on the Active Strategy panel:
  - changed buy lines count if route provides it or can be derived cheaply;
  - changed sell lines count if route provides it or can be derived cheaply;
  - otherwise show route status and link to full diff tab.
- Reuse `StrategyInspectorTabs` for the full diff/prompt/context details.

**Acceptance Criteria**:
- Gen0 does not error.
- Missing base generation does not error.
- A normal gen1+ case shows previous diff availability from the main page.
- Existing modal tabs still show `Previous Diff`, `Prompt Timeline`, `AI Context`, and `Current Code`.

**QA Scenarios**:
```text
Scenario: gen0 active strategy
  Expected: diff_status=no_previous_generation and no frontend error.

Scenario: gen1 active strategy
  Expected: diff fetch succeeds and panel exposes previous-diff availability.
```

### P5 - Seed Timeout Diagnostic Ladder
**Goal**: Determine whether the known seed timeout is caused by workload size before retrying long training.

**Likely files**:
- Evidence/config files only under `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/`
- `cli/warm_session.py` only if a focused test proves reset/timeout recovery is wrong.
- `tests/unit/test_loop_robustness.py` and a new/updated focused timeout diagnostic test only if source changes are needed.

**Actions**:
- Write the three diagnostic configs listed in "Timeout Diagnostic Ladder".
- Run only one diagnostic at a time.
- Use owned processes only.
- Capture:
  - config hash;
  - command;
  - run ID;
  - start/end timestamps;
  - elapsed seconds;
  - timeout setting;
  - status;
  - CSV path yes/no;
  - first blocker reason.
- Stop at the first failed gate.

**Acceptance Criteria**:
- `p5-timeout-diagnostic-ladder.md` contains all attempted diagnostics and first failure/pass gate.
- No 2023-2025 training starts before all three diagnostics pass.
- No protected path is edited/staged.

**QA Scenarios**:
```text
Scenario: 5m diagnostic passes
  Expected: CSV exists or explicit non-timeout terminal status; proceed to 10m.

Scenario: 5m diagnostic times out
  Expected: Stop, write BLOCKED_WITH_TIMEOUT_EVIDENCE_NO_OOS, do not run 10m/Jan/full training.
```

### P6 - Training Retry Gate
**Goal**: Produce a clear go/no-go page after diagnostics.

**Actions**:
- If full January preflight retry passes:
  - write `p6-training-retry-gate.md` with verdict `ready_for_training_retry`;
  - recommend the next command for 2023-2025 bounded training;
  - do not run OOS in this page.
- If any diagnostic fails:
  - write `p6-training-retry-gate.md` with verdict `blocked`;
  - name the failing run ID and first blocker;
  - recommend the next plan/implementation target.

**Acceptance Criteria**:
- The gate document contains exact dates, timeframe, window, timeout, elapsed, and CSV status.
- The document explicitly states whether `2023-2025` training is allowed as the next page.
- The document explicitly states OOS remains blocked.

**QA Scenarios**:
```text
Scenario: Diagnostics pass
  Expected: Next command is a training retry plan/start-work, not OOS.

Scenario: Diagnostics fail
  Expected: Next command targets timeout/root-cause work, not training.
```

### P7 - Decision Card And Page Progress
**Goal**: Close the page with a truthful progress table and next command.

**Actions**:
- Write `p7-decision-card.md`.
- Include:
  - terminal verdict;
  - active-strategy panel status;
  - route status;
  - diagnostic ladder status;
  - training retry gate;
  - OOS/export/final approval forbidden-action checklist;
  - whole-page progress table;
  - next recommended command.

**Acceptance Criteria**:
- Decision card separates dashboard/UI success from performance proof.
- It states clearly that human-level/seed-superior proof still requires 2023-2025 training and fixed OOS after a frozen candidate.
- It gives exactly one recommended next command.

**QA Scenarios**:
```text
Scenario: Ready for training
  Expected: Next command is $ulw-plan or $start-work for bounded 2023-2025 training, still no OOS.

Scenario: Still blocked
  Expected: Next command targets timeout root-cause or smaller diagnostic instrumentation.
```

## Final Verification Wave

- [x] Final Verification Wave

Run these after implementation and evidence writing:

```powershell
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_dashboard_strategy_prompt_frontend.py tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_profit_codeview.py tests/unit/test_dashboard_route_parity.py -q
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_dashboard_engine_progress_contract.py tests/unit/test_dashboard_phase_mapping.py tests/unit/test_process_timing.py -q
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_loop_robustness.py tests/unit/test_dashboard_backtest_detail.py tests/unit/test_dashboard_chart_explanations.py -q
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json
```

## Out Of Scope
- 2022/2026 OOS execution.
- Human-level or seed-superior performance claim.
- Hard-gate threshold relaxation.
- Official engine internals.
- Production promotion/export.
- Live broker/V3K actions.
- Broad dashboard redesign beyond active strategy visibility and route/error clarity.

## Next Command After This Plan
```text
$start-work tick-p7-timeout-unblock-live-strategy-visibility-20260605
```
