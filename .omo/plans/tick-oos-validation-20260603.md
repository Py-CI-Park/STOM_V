# TICK 토글 ON 다년 연구 run + 2022/2026 OOS 검증 계획

## TL;DR
> **Summary**: TICK T0~T4 인프라를 실제로 켜서 2023~2025 탐색/훈련 run을 수행하고, 2022/2026 OOS에서 seed Tick_902 및 인간 reference 조건식 지표와 비교해 "인간 근사/초월" 주장을 정직하게 판정한다.
> **Deliverables**:
> - `.omo/evidence/tick-oos-validation-20260603/` 실행 config, API 응답, 로그, 요약 JSON/Markdown
> - P1 short reproduction run 결과
> - P2 2023~2025 toggles-ON TICK 연구 run 결과
> - P3 T1/T4 분석 및 segment feedback 적용 증거
> - P4 2022/2026 OOS seed/human-reference 비교표
> - P5 PBO/DSR/slippage/promotion-card 판정 보고서
> **Effort**: Large
> **Parallel**: YES - 3 waves
> **Critical Path**: P0 safety snapshot -> P1 reproduction -> P2 multiyear run -> P3 feedback -> P4 OOS comparison -> P5 decision report -> Final verification

## Context
### Original Request
- 사용자는 `docs/AGENT_HANDOFF.md`, `docs/update_log/2026-06-03_tick_program_complete_handoff.md`, `.omo/evidence/condition-research-rereview-20260603.md`를 정본으로 삼아 TICK 토글 ON 다년 연구 run과 2022/2026 OOS 검증 계획을 만들라고 요청했다.
- 필수 조건: 엔진/하드게이트/`backtest/graph/` 무수정, 신규 토글 기본 OFF, 보호 경로를 소스 변경으로 취급하지 않음, `final_approval`/`export_winner` 금지.

### Interview Summary
- 질문 없이 진행한다. 요청 범위와 성공 기준은 레포 문서에서 명확하다.
- 이 계획은 구현 계획이 아니라 실행/검증 계획이다. 소스 코드는 수정하지 않고, OMO evidence와 runtime run 결과만 남긴다.
- 실행은 `$start-work tick-oos-validation-20260603`로 시작한다.

### Metis Review (gaps addressed)
- Metis 검토는 두 차례 요청했으나 제한 시간 내 실질 결과를 반환하지 않았다. 따라서 아래 리스크를 보수적으로 계획에 직접 반영했다.
- High Accuracy Review(Momus)는 두 차례 요청했으나 제한 시간 내 실질 결과를 반환하지 않았다. Momus 승인으로 계산하지 않고, `start-work` 실행성 관점의 자체 보완을 반영했다.
- Runtime loop는 `ai_strategy_loop/state/*.db`와 snapshot을 갱신할 수 있으므로, 이를 운영 DB/보호 경로 소스 편집으로 취급하지 않고 generated runtime evidence로만 기록한다.
- 1개월 smoke 결과는 승격 근거가 될 수 없으며, 2022/2026 OOS 전에는 "인간 초월" 또는 "수익 조건식 완성"이라고 쓰지 않는다.
- `--config-json` 사용 시 `--max-gen` CLI 인자는 무시되므로 실행용 config JSON 안의 `max_generations` 값을 명시적으로 고친다.
- `final_approval`/`export_winner`는 대시보드와 컨트롤러에 존재하지만 이번 계획에서는 호출 금지 대상이다.
- OOS run은 탐색/훈련이 아니라 평가 전용이다. `seed_buy`/`seed_sell`에 평가 대상 pair를 넣고 `max_generations=1`로 고정해 OOS에서 재생성·재선택하지 않는다.

## Work Objectives
### Core Objective
TICK 09:00~09:30 조건식 자율진화 루프가 인간 reference 조건식에 근접하거나 우월한 조건식을 자동 개발하는지, 2023~2025 탐색/훈련과 2022/2026 OOS 분리검증으로 판정한다.

### Deliverables
- `.omo/evidence/tick-oos-validation-20260603/safety-snapshot.txt`
- `.omo/evidence/tick-oos-validation-20260603/p1-smoke-config.json`
- `.omo/evidence/tick-oos-validation-20260603/p1-smoke-log.txt`
- `.omo/evidence/tick-oos-validation-20260603/p2-train-config.json`
- `.omo/evidence/tick-oos-validation-20260603/p2-train-log.txt`
- `.omo/evidence/tick-oos-validation-20260603/p3-analysis.json`
- `.omo/evidence/tick-oos-validation-20260603/p4-oos-comparison.json`
- `.omo/evidence/tick-oos-validation-20260603/p5-decision-card.md`
- `.omo/evidence/tick-oos-validation-20260603/final-verification.txt`

### Definition of Done
- P1 short reproduction run completes or fails with captured root-cause evidence.
- P2 2023~2025 toggles-ON TICK run completes or is explicitly marked blocked by resource/runtime evidence.
- P3 dashboard/API analysis captures edge, feature, and losing-segment feedback evidence.
- P4 2022/2026 OOS compares best AI candidate against seed Tick_902 and human reference metric corridor.
- P5 decision card says exactly one of `PROMOTE_CANDIDATE`, `REJECT_CANDIDATE`, or `NEEDS_MORE_EVIDENCE`, with concrete reasons.
- Final commands pass or record known/pre-existing failures:
  - `git diff --check`
  - `python scripts/verify_nonrelease_sync.py`
  - `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json`

### Must Have
- Use `ai_strategy_loop/state/run_tickwide_config.json` as the P1 base pattern.
- For P2 use `bt_timeframe="tick"`, `bt_universe_start_time=90000`, `bt_universe_end_time=93000`, `bt_full_start=20230101`, `bt_full_end=20251231`.
- Enable these research toggles in execution config: `classification_generation_enabled`, `require_filter_gates`, `encourage_time_dispersion`, `few_shot_enabled`, `few_shot_source="seed_db"`, `segment_feedback_enabled`.
- Keep `segment_feedback_enabled` default OFF in source; only execution config may turn it ON.
- OOS years are exactly 2022 and 2026. If 2026 available data is partial, record exact start/end dates from config and result.
- Use explicit run ids:
  - `tick_oos_p1_smoke_20260603`
  - `tick_oos_p2_train_2023_2025_20260603`
  - `tick_oos_p4_seed_2022_20260603`
  - `tick_oos_p4_seed_2026_20260603`
  - `tick_oos_p4_ai_2022_20260603`
  - `tick_oos_p4_ai_2026_20260603`
- For OOS evaluation configs, set `max_generations=1`, `bt_refine_from_best=false`, and use the preselected pair as `seed_buy`/`seed_sell`.

### Must NOT Have
- No edits to `backtest/`, `backtest/graph/`, hard-gate scoring, engine files, live broker code, or production strategy DB wiring.
- No `final_approval` WebSocket message.
- No `export_winner(...)` call.
- No V3K gate advancement, USER_ACK creation, KHOPENAPI login/connect, DB cutover, live order/exit wiring.
- No blanket `taskkill`. If a server must be stopped, stop only the PID spawned by this execution and record the receipt.
- No claim that a candidate is human-level/superior unless P4 and P5 explicitly support it.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after + runtime QA. This plan executes research runs and evidence collection, not source implementation.
- QA policy: Every task has agent-executed scenarios with concrete command/API artifacts.
- Evidence root: `.omo/evidence/tick-oos-validation-20260603/`
- Runtime state policy: `ai_strategy_loop/state/*.db` and snapshots may change only through the official loop/dashboard runtime. They are generated runtime evidence, not source edits or disposable scratch. Do not delete or manually rewrite them.
- Ledger policy: for every top-level TODO and final verification checkbox, append one JSONL entry to `.omo/start-work/ledger.jsonl` with `event`, `plan`, `task`, `session_id`, `commands`, `artifact`, `adversarial_classes`, and `cleanup`.
- Adversarial QA policy: each task must record these classes as either probed or not-applicable with one-line reason: malformed input, prompt injection, cancel/resume, stale state, dirty worktree, hung or long commands, flaky tests, misleading success output, repeated interruptions.
- Cleanup policy: any spawned dashboard/server/process, temporary config, or browser session must be recorded at spawn time and either cleaned up with receipt or explicitly marked pre-existing/not-owned.

## Execution Strategy
### Parallel Execution Waves
Wave 1: Task 1 safety snapshot and Task 2 focused verifier/API baseline can run after reading the plan.
Wave 2: Task 3 P1 smoke must complete before Task 4 P2 training. Task 5 analysis depends on at least one completed run.
Wave 3: Task 6 OOS comparison depends on Task 4 selected candidate. Task 7 decision report depends on Task 6.
Final Wave: F1-F4 after all tasks.

### Dependency Matrix
| Task | Depends On | Blocks |
| --- | --- | --- |
| 1 Safety Snapshot | none | 3, 4, 6 |
| 2 Verifier/API Baseline | none | 3, 5 |
| 3 P1 Short Reproduction | 1, 2 | 4 |
| 4 P2 Multiyear Train Run | 3 | 5, 6 |
| 5 P3 T1/T4 Analysis | 3, 4 | 6, 7 |
| 6 P4 OOS Comparison | 4, 5 | 7 |
| 7 P5 Decision Report | 6 | F1-F4 |

## TODOs
> Implementation + Test = ONE task. Nested checkboxes below are acceptance criteria only; `$start-work` should advance only column-0 checkboxes.
> Common completion rule for every top-level task: before marking the checkbox done, append `.omo/start-work/ledger.jsonl`; record the applicable adversarial QA classes; record cleanup receipt for every spawned process/temp artifact or mark it pre-existing/not-owned.

- [x] 1. P0 안전 스냅샷과 실행 격리 선언

  **What to do**: Create `.omo/evidence/tick-oos-validation-20260603/`. Capture branch, HEAD, dirty state, protected-path state, currently listening dashboard PID if any, current `.omo/boulder.json`, and whether `ai_strategy_loop/state/loop_runs.db` exists. Record that generated runtime DB writes are expected only from official loop execution and must not be staged or manually edited.
  **Must NOT do**: Do not clean dirty files. Do not delete DBs/snapshots. Do not stop existing Python processes. Do not stage or commit.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 3, 4, 6 | Blocked By: none

  **References**:
  - Governance: `AGENTS.md` - branch role, protected paths, V3K gate state, verifier commands.
  - Handoff: `docs/AGENT_HANDOFF.md:26` - hard invariants; `docs/AGENT_HANDOFF.md:88` - next TICK/OOS work.
  - Runtime boundary: `ai_strategy_loop/AGENTS.md` - state files are generated and loop is research/control-plane code.
  - Existing OMO state: `.omo/boulder.json` - previous work is completed, so this plan needs a new work id.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/tick-oos-validation-20260603/safety-snapshot.txt` contains outputs of `git status --short --branch`, `git rev-parse HEAD`, `git branch --show-current`, and protected-path status.
  - [ ] Snapshot records whether `http://127.0.0.1:8770/health` responds and, if live, the PID/command line for port `8770`.
  - [ ] Snapshot records that `final_approval`, `export_winner`, V3K gate advancement, and blanket `taskkill` are forbidden.

  **QA Scenarios**:
  ```text
  Scenario: Happy path safety snapshot
    Tool: powershell
    Steps:
      New-Item -ItemType Directory -Force .omo/evidence/tick-oos-validation-20260603
      git status --short --branch | Tee-Object .omo/evidence/tick-oos-validation-20260603/safety-snapshot.txt
      git rev-parse HEAD | Tee-Object -Append .omo/evidence/tick-oos-validation-20260603/safety-snapshot.txt
      git branch --show-current | Tee-Object -Append .omo/evidence/tick-oos-validation-20260603/safety-snapshot.txt
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json | Tee-Object -Append .omo/evidence/tick-oos-validation-20260603/safety-snapshot.txt
    Expected: Evidence file exists; protected-path status has no new source-controlled modifications caused by this task.
    Evidence: .omo/evidence/tick-oos-validation-20260603/safety-snapshot.txt

  Scenario: Dirty worktree classification
    Tool: powershell
    Steps:
      If dirty files exist, list them under "pre-existing dirty/untracked state" in safety-snapshot.txt.
    Expected: No dirty file is removed or reverted; task continues unless protected-path tracked modifications are newly introduced by the executor.
    Evidence: .omo/evidence/tick-oos-validation-20260603/safety-snapshot.txt
  ```

  **Commit**: NO | Message: n/a | Files: `.omo/evidence/tick-oos-validation-20260603/safety-snapshot.txt`

- [x] 2. Baseline verifier, focused tests, and dashboard read-only API smoke

  **What to do**: Run focused tests for the analysis surfaces and branch safety verifiers before any new run. Check dashboard health and read-only endpoints if the service is live; if not live, start `python -m ai_strategy_loop` and record the spawned PID for cleanup. Leave pre-existing dashboard processes running.
  **Must NOT do**: Do not invoke WebSocket `final_approval`. Do not click export/approve UI controls. Do not kill pre-existing dashboard PID.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 3, 5 | Blocked By: none

  **References**:
  - Test map: `tests/AGENTS.md` - focused tests first, broader unit sweep only for branch propagation.
  - Script map: `scripts/AGENTS.md` - use `verify_nonrelease_sync.py`, not release sync.
  - Dashboard API: `ai_strategy_loop/dashboard/app.py:1095`, `:1141`, `:1161`, `:1171`, `:1185` - `/run_state`, `/backtest_detail`, `/adaptive_timing`, `/edge_ratio`, `/feature_importance`.
  - Prohibited export boundary: `ai_strategy_loop/dashboard/app.py:1269` and `ai_strategy_loop/controller/export.py` - `final_approval` calls `export_winner`.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/tick-oos-validation-20260603/baseline-verification.txt` contains focused pytest results, `git diff --check`, and `python scripts/verify_nonrelease_sync.py`.
  - [ ] `.omo/evidence/tick-oos-validation-20260603/dashboard-api-smoke.json` contains `/health`, `/runs`, and at least one read-only analysis endpoint response or records why the dashboard is unavailable.
  - [ ] If a dashboard process is spawned by this task, `.omo/evidence/tick-oos-validation-20260603/dashboard-pid.txt` records the PID and cleanup obligation.

  **QA Scenarios**:
  ```text
  Scenario: Focused automated baseline
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      python -m pytest tests/unit/test_segment_feedback.py tests/unit/test_edge_ratio.py tests/unit/test_feature_importance.py tests/unit/test_change_segment.py tests/unit/test_dashboard_backtest_detail.py tests/unit/test_dashboard_run_state.py tests/unit/test_dashboard_equity_curves.py tests/unit/test_dashboard_runs_lock.py tests/unit/test_adaptive_timing.py -q
      git diff --check
      python scripts/verify_nonrelease_sync.py
    Expected: Commands pass, or failures are recorded as pre-existing with exact failing test names before proceeding.
    Evidence: .omo/evidence/tick-oos-validation-20260603/baseline-verification.txt

  Scenario: Read-only dashboard smoke
    Tool: curl.exe
    Steps:
      curl.exe -sS http://127.0.0.1:8770/health
      curl.exe -sS http://127.0.0.1:8770/runs
      curl.exe -sS "http://127.0.0.1:8770/edge_ratio?run_id=tickwide_t0b&fine_time=true"
    Expected: `/health` returns status ok if service is live; read-only endpoint responses are captured without export/final approval.
    Evidence: .omo/evidence/tick-oos-validation-20260603/dashboard-api-smoke.json
  ```

  **Commit**: NO | Message: n/a | Files: `.omo/evidence/tick-oos-validation-20260603/baseline-verification.txt`, `.omo/evidence/tick-oos-validation-20260603/dashboard-api-smoke.json`

- [x] 3. P1 짧은 재현 run: TICK wide 토글 ON smoke

  **What to do**: Create `.omo/evidence/tick-oos-validation-20260603/p1-smoke-config.json` by copying `ai_strategy_loop/state/run_tickwide_config.json` and explicitly setting `segment_feedback_enabled=true`, `segment_feedback_min_count=8`, `max_generations=2`, `bt_full_start=20250408`, `bt_full_end=20250430`, `bt_timeframe="tick"`, `bt_universe_start_time=90000`, `bt_universe_end_time=93000`. Run the loop with run id `tick_oos_p1_smoke_20260603`. Capture stdout/stderr log and dashboard API result.
  **Must NOT do**: Do not rely on `--max-gen` to override config; with `--config-json`, `max_generations` must be inside the JSON. Do not call final approval even if a winner appears.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 4 | Blocked By: 1, 2

  **References**:
  - Baseline config: `ai_strategy_loop/state/run_tickwide_config.json:4` - tick warm mode and 09:00~09:30.
  - Config fields: `ai_strategy_loop/config.py:126` - `bt_full_start/end`; `ai_strategy_loop/config.py:368` - `segment_feedback_enabled` default false.
  - CLI behavior: `ai_strategy_loop/controller/loop.py:2278` - `--config-json` accepts file path; `ai_strategy_loop/controller/loop.py:2307` - `run_loop` uses config object.
  - State resume contract: `ai_strategy_loop/controller/state.py:254` - same `run_id` resumes existing run.

  **Acceptance Criteria**:
  - [ ] `p1-smoke-config.json` exists and contains `segment_feedback_enabled: true`, `max_generations: 2`, `bt_full_start: 20250408`, `bt_full_end: 20250430`.
  - [ ] `p1-smoke-log.txt` contains `[LOOP] === SUMMARY ===` or an explicit runtime failure with stack trace and resource observations.
  - [ ] Dashboard `/run_state?run_id=tick_oos_p1_smoke_20260603` and `/backtest_detail?run_id=tick_oos_p1_smoke_20260603&gen_no=1` responses are captured.

  **QA Scenarios**:
  ```text
  Scenario: P1 smoke run
    Tool: powershell
    Steps:
      $env:STOM_ALLOW_MINIMAL_SETTING='1'
      $env:PYTHONUTF8='1'
      python -m ai_strategy_loop.controller.loop --config-json .omo/evidence/tick-oos-validation-20260603/p1-smoke-config.json --run-id tick_oos_p1_smoke_20260603
    Expected: Process exits 0 with summary, or failure is captured with enough evidence to diagnose without retrying blindly.
    Evidence: .omo/evidence/tick-oos-validation-20260603/p1-smoke-log.txt

  Scenario: P1 read-only API verification
    Tool: curl.exe
    Steps:
      curl.exe -sS "http://127.0.0.1:8770/run_state?run_id=tick_oos_p1_smoke_20260603"
      curl.exe -sS "http://127.0.0.1:8770/backtest_detail?run_id=tick_oos_p1_smoke_20260603&gen_no=1"
      curl.exe -sS "http://127.0.0.1:8770/edge_ratio?run_id=tick_oos_p1_smoke_20260603&fine_time=true"
    Expected: JSON responses contain the run id or a documented insufficient-data response; no export action occurs.
    Evidence: .omo/evidence/tick-oos-validation-20260603/p1-api.json
  ```

  **Commit**: NO | Message: n/a | Files: `.omo/evidence/tick-oos-validation-20260603/p1-smoke-config.json`, `.omo/evidence/tick-oos-validation-20260603/p1-smoke-log.txt`, `.omo/evidence/tick-oos-validation-20260603/p1-api.json`

- [x] 4. P2 2023~2025 toggles-ON 다년 탐색/훈련 run

  **What to do**: Create `.omo/evidence/tick-oos-validation-20260603/p2-train-config.json` from P1 config and set `bt_full_start=20230101`, `bt_full_end=20251231`, `max_generations=6`, `segment_feedback_enabled=true`, `segment_feedback_min_count=8`, `bt_timeout=900`, `bt_warm_run_timeout=300`. Run id must be `tick_oos_p2_train_2023_2025_20260603`. Monitor memory/timeout manually via process exit, log timestamps, and dashboard state. If OOM/hang occurs, stop only the spawned loop process after recording PID and stack/log evidence, then mark Task 4 blocked with resource evidence rather than weakening guardrails.
  **Must NOT do**: Do not modify backtest engines, hard gates, or score formula to make the run pass. Do not reduce OOS years. Do not delete prior runtime state.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 5, 6 | Blocked By: 3

  **References**:
  - Next-work instruction: `docs/AGENT_HANDOFF.md:89` - toggles ON multiyear TICK run + OOS.
  - Detailed handoff: `docs/update_log/2026-06-03_tick_program_complete_handoff.md:73` - run_tickwide pattern with segment feedback ON.
  - Existing multiyear profile: `ai_strategy_loop/state/run_multiyear_config.json:7` - tick and 2023~2025 date window.
  - Loop warm dates: `ai_strategy_loop/controller/loop.py:390` - backtest config uses `bt_full_start/end`.

  **Acceptance Criteria**:
  - [ ] `p2-train-config.json` contains 2023~2025 dates, tick 09:00~09:30, and all required toggles ON.
  - [ ] `p2-train-log.txt` records command, start/end timestamps, exit code, summary, and any resource failure.
  - [ ] `p2-selected-candidate.json` identifies the predeclared selected candidate: highest score among completed P2 generations, with `best_gen`, `buy_name`, `sell_name`, `score`, `profit`, `max_drawdown`, `trade_count`, and `csv_path` if present.

  **QA Scenarios**:
  ```text
  Scenario: P2 multiyear train run
    Tool: powershell
    Steps:
      $env:STOM_ALLOW_MINIMAL_SETTING='1'
      $env:PYTHONUTF8='1'
      python -m ai_strategy_loop.controller.loop --config-json .omo/evidence/tick-oos-validation-20260603/p2-train-config.json --run-id tick_oos_p2_train_2023_2025_20260603
    Expected: Completed summary is captured. If blocked by runtime resource limits, evidence contains PID, elapsed time, last log lines, and exact failure.
    Evidence: .omo/evidence/tick-oos-validation-20260603/p2-train-log.txt

  Scenario: Misleading success guard
    Tool: curl.exe + powershell
    Steps:
      curl.exe -sS "http://127.0.0.1:8770/run_state?run_id=tick_oos_p2_train_2023_2025_20260603"
      Parse generations and confirm at least one completed generation exists before selecting a candidate.
    Expected: A candidate is not selected from an empty or failed run.
    Evidence: .omo/evidence/tick-oos-validation-20260603/p2-selected-candidate.json
  ```

  **Commit**: NO | Message: n/a | Files: `.omo/evidence/tick-oos-validation-20260603/p2-train-config.json`, `.omo/evidence/tick-oos-validation-20260603/p2-train-log.txt`, `.omo/evidence/tick-oos-validation-20260603/p2-selected-candidate.json`

- [x] 5. P3 T1/T4 분석과 패배 세그먼트 환류 증거 수집

  **What to do**: Use read-only dashboard endpoints on P1 and P2 runs to collect `edge_ratio`, `feature_importance`, `backtest_detail`, and `adaptive_timing` evidence. Confirm whether segment feedback actually produced avoid guidance in prompts or logs. Produce `p3-analysis.json` and `p3-feedback-summary.md` with losing segments, useful feature axes, and whether a follow-up generation should avoid specific time/market-cap/change cells.
  **Must NOT do**: Do not rewrite prompts or source. Do not manually inject segment feedback into code. Do not run extra generations unless Task 4 completed and the plan evidence says the first P2 pass is insufficient due to missing segment feedback.

  **Parallelization**: Can Parallel: YES after Task 4 | Wave 3 | Blocks: 6, 7 | Blocked By: 3, 4

  **References**:
  - T1/T4 modules: `docs/update_log/2026-06-03_tick_program_complete_handoff.md:64` - `segment_feedback.py`, `analysis.jsx`, `edge_ratio.py`, `feature_importance.py`.
  - Dashboard endpoints: `docs/update_log/2026-06-03_tick_program_complete_handoff.md:67` - `/edge_ratio`, `/feature_importance`, `/backtest_detail`.
  - Segment feedback default: `tests/unit/test_segment_feedback.py:209` - `LoopConfig.segment_feedback_enabled` default false.
  - Prompt wiring: `ai_strategy_loop/brain/prompt.py:248` - segment feedback is only filled when enabled.

  **Acceptance Criteria**:
  - [ ] `p3-analysis.json` contains endpoint responses for P1 and P2 or documents unavailable runs.
  - [ ] `p3-feedback-summary.md` lists top losing segments by total profit and count, top useful B_* features, and whether feedback was used in generation.
  - [ ] If segment feedback was not active despite config, report `NEEDS_MORE_EVIDENCE` blocker and do not fabricate T4 closure.

  **QA Scenarios**:
  ```text
  Scenario: Segment/feature analysis capture
    Tool: curl.exe
    Steps:
      curl.exe -sS "http://127.0.0.1:8770/edge_ratio?run_id=tick_oos_p2_train_2023_2025_20260603&fine_time=true"
      curl.exe -sS "http://127.0.0.1:8770/feature_importance?run_id=tick_oos_p2_train_2023_2025_20260603&axis=change&fine_time=true"
      curl.exe -sS "http://127.0.0.1:8770/adaptive_timing?run_id=tick_oos_p2_train_2023_2025_20260603&lookback=2"
    Expected: Responses are valid JSON or documented insufficient-data JSON; no endpoint mutates production DB or exports a strategy.
    Evidence: .omo/evidence/tick-oos-validation-20260603/p3-analysis.json

  Scenario: Prompt-feedback evidence
    Tool: powershell
    Steps:
      Search `p2-train-log.txt` and loop prompt records for `avoid`, `segment`, `feedback`, or Korean segment-feedback markers tied to `tick_oos_p2_train_2023_2025_20260603`.
    Expected: Report either concrete prompt feedback evidence or a clear blocker; no manual prompt editing.
    Evidence: .omo/evidence/tick-oos-validation-20260603/p3-feedback-summary.md
  ```

  **Commit**: NO | Message: n/a | Files: `.omo/evidence/tick-oos-validation-20260603/p3-analysis.json`, `.omo/evidence/tick-oos-validation-20260603/p3-feedback-summary.md`

- [x] 6. P4 2022/2026 OOS seed Tick_902 직접 비교

  **What to do**: Generate OOS configs for seed and selected AI candidate. Seed configs must use existing seed profile patterns from `run_ens_seed_2022full_config.json` and `run_ens_seed_2026full_config.json`. AI configs must use the exact selected P2 buy/sell names from `p2-selected-candidate.json`, tick timeframe, 09:00~09:30 window, `max_generations=1`, `bt_refine_from_best=false`, and OOS dates `20220101~20221231` plus the available 2026 window from the seed config. Run four OOS evaluation runs if required state does not already exist; otherwise capture existing matching run evidence. Produce `p4-oos-comparison.json` and `p4-oos-comparison.md`.
  **Must NOT do**: Do not select a new candidate after seeing OOS. Do not tune on 2022 or 2026. Do not combine OOS years into training. Do not call export/final approval.

  **Parallelization**: Can Parallel: PARTIAL | Wave 3 | Blocks: 7 | Blocked By: 4, 5

  **References**:
  - OOS requirement: `docs/AGENT_HANDOFF.md:21` and `docs/AGENT_HANDOFF.md:89` - 2022/2026 OOS split.
  - Seed robustness: `docs/AGENT_HANDOFF.md:13` and `docs/AGENT_HANDOFF.md:67` - Tick_902 is multiyear robust gold.
  - Seed OOS profiles: `ai_strategy_loop/state/run_ens_seed_2022full_config.json:5`, `ai_strategy_loop/state/run_ens_seed_2026full_config.json:5`.
  - Bias warning: `docs/AGENT_HANDOFF.md:72` - BackFinder seed has lookahead/survivorship risk; OOS required.

  **Acceptance Criteria**:
  - [ ] `p4-oos-comparison.json` contains metrics for seed 2022, seed 2026, AI 2022, AI 2026.
  - [ ] Each OOS config uses `max_generations=1`, `bt_refine_from_best=false`, and predeclared `seed_buy`/`seed_sell`; no OOS generation/refinement is performed.
  - [ ] Each row includes `run_id`, `period`, `final_profit`, `max_drawdown`, `trade_count`, `daily_trade_avg` if available, `peak_holdings` if available, `edge_ratio` if available, and `source_config`.
  - [ ] `p4-oos-comparison.md` classifies the AI candidate as `beats_seed`, `near_seed`, `fails_seed`, or `insufficient_data` under predeclared rules.
  - [ ] Predeclared superiority rule: AI can be called seed-superior only if both 2022 and 2026 OOS have positive final profit, combined OOS final profit is >= seed combined final profit, combined OOS max drawdown is <= seed combined max drawdown, and trade/holding profile is inside or explicitly justified relative to the human reference corridor.

  **QA Scenarios**:
  ```text
  Scenario: OOS run execution/capture
    Tool: powershell
    Steps:
      Run or capture seed 2022, seed 2026, AI 2022, AI 2026 with fixed predeclared configs and run ids.
      For each run, call `/run_state`, `/backtest_detail`, `/edge_ratio`, and `/feature_importance` where data exists.
    Expected: Four OOS rows are present, or missing rows have exact blocker reasons. Candidate selection does not change after OOS.
    Evidence: .omo/evidence/tick-oos-validation-20260603/p4-oos-comparison.json

  Scenario: OOS tuning leak guard
    Tool: powershell
    Steps:
      Compare `p2-selected-candidate.json` before and after OOS task; verify same buy/sell names and generation.
    Expected: No OOS-informed candidate reselection occurs.
    Evidence: .omo/evidence/tick-oos-validation-20260603/p4-oos-comparison.md
  ```

  **Commit**: NO | Message: n/a | Files: `.omo/evidence/tick-oos-validation-20260603/p4-oos-comparison.json`, `.omo/evidence/tick-oos-validation-20260603/p4-oos-comparison.md`

- [x] 7. P5 PBO/DSR/slippage/promotion-card 최종 판정 보고서

  **What to do**: Produce `p5-decision-card.md` that converts P1-P4 evidence into a final verdict. Include overfit risk, PBO/DSR or equivalent advisory warning, slippage/execution stress, seed comparison, human reference corridor, and exact forbidden actions not taken. The card must end with exactly one verdict: `PROMOTE_CANDIDATE`, `REJECT_CANDIDATE`, or `NEEDS_MORE_EVIDENCE`.
  **Must NOT do**: Do not promote to production. Do not call export. Do not soften an OOS failure by citing only training or smoke results.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: F1-F4 | Blocked By: 6

  **References**:
  - Rereview conclusion: `.omo/evidence/condition-research-rereview-20260603.md:18` - human-level/superior claim impossible before OOS.
  - Needs-more-evidence list: `.omo/evidence/condition-research-rereview-20260603.md:130` - OOS, PBO/DSR, slippage, promotion card.
  - Overfit/slippage caution: `.omo/evidence/condition-research-rereview-20260603.md:99` - many-candidate best-picking needs PBO/DSR; tick scalping needs slippage stress.
  - Report writers: `cli/research_report.py:465` and `cli/research_report.py:576` - Markdown/JSON report rendering patterns if a helper is useful.

  **Acceptance Criteria**:
  - [ ] `p5-decision-card.md` has sections: Executive Verdict, Candidate Identity, Training Evidence, OOS Evidence, Seed Comparison, Human Reference Corridor, Overfit Risk, Slippage/Execution Stress, Forbidden Actions Check, Final Verdict.
  - [ ] Overfit risk is not left blank. If PBO/DSR is not implemented by existing tooling, card must mark it as `advisory_blocker` rather than pretending it passed.
  - [ ] Slippage stress applies at least three advisory haircuts to OOS profit, for example 0.1%, 0.2%, and 0.3% per round-trip if trade-level costs are unavailable; if trade-level fields are available, use them and document the method.
  - [ ] `PROMOTE_CANDIDATE` is allowed only if P4 superiority rule passes and slippage-stressed OOS remains positive in both 2022 and 2026. Otherwise verdict is `REJECT_CANDIDATE` or `NEEDS_MORE_EVIDENCE`.

  **QA Scenarios**:
  ```text
  Scenario: Decision card consistency
    Tool: powershell
    Steps:
      Read p2-selected-candidate.json, p3-analysis.json, p4-oos-comparison.json, and generate p5-decision-card.md.
      Verify the final verdict line appears exactly once and matches the predeclared rules.
    Expected: No contradiction between metrics and verdict.
    Evidence: .omo/evidence/tick-oos-validation-20260603/p5-decision-card.md

  Scenario: Misleading success output guard
    Tool: powershell
    Steps:
      Search p5-decision-card.md for "human", "초월", "능가", "PROMOTE_CANDIDATE"; verify any such claim cites P4 and slippage-stressed OOS.
    Expected: Training-only or smoke-only success language is absent.
    Evidence: .omo/evidence/tick-oos-validation-20260603/p5-decision-card.md
  ```

  **Commit**: NO | Message: n/a | Files: `.omo/evidence/tick-oos-validation-20260603/p5-decision-card.md`

## Final Verification Wave (MANDATORY - after ALL implementation tasks)
> ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
- [x] F1. Plan Compliance Audit

  **What to do**: Re-read this plan and every artifact under `.omo/evidence/tick-oos-validation-20260603/`. Confirm each top-level TODO has a corresponding evidence artifact and that no task used forbidden paths/actions.
  **Must NOT do**: Do not mark complete if any top-level task is unchecked or evidence is missing.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/tick-oos-validation-20260603/final-plan-compliance.txt` lists each task 1-7 and its evidence artifact.
  - [ ] The file states whether `final_approval`, `export_winner`, V3K gate advancement, and blanket `taskkill` were absent.

  **QA Scenarios**:
  ```text
  Scenario: Compliance audit
    Tool: powershell
    Steps:
      List `.omo/evidence/tick-oos-validation-20260603/`.
      Search logs/artifacts for `final_approval`, `export_winner`, `USER_ACK`, `KHOPENAPI`, and `taskkill`.
    Expected: Forbidden actions absent except as text in guardrails/audit statements.
    Evidence: .omo/evidence/tick-oos-validation-20260603/final-plan-compliance.txt
  ```

- [x] F2. Code Quality Review

  **What to do**: Run final verifier commands and focused tests. Because the plan should not edit source, the expected source diff should be limited to `.omo/` plan/evidence changes unless runtime ignored files changed.
  **Must NOT do**: Do not run formatters or code generators. Do not weaken tests.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/tick-oos-validation-20260603/final-verification.txt` contains `git diff --check`, `python scripts/verify_nonrelease_sync.py`, protected-path status, and focused pytest output.
  - [ ] If `pytest tests/unit/ -q` is run, known existing failures are separated from new failures.

  **QA Scenarios**:
  ```text
  Scenario: Final automated verification
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      git diff --check
      python scripts/verify_nonrelease_sync.py
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      python -m pytest tests/unit/test_segment_feedback.py tests/unit/test_edge_ratio.py tests/unit/test_feature_importance.py tests/unit/test_change_segment.py tests/unit/test_dashboard_backtest_detail.py tests/unit/test_dashboard_run_state.py tests/unit/test_dashboard_equity_curves.py tests/unit/test_dashboard_runs_lock.py tests/unit/test_adaptive_timing.py -q
    Expected: Commands pass or exact unrelated/pre-existing failures are recorded. Protected source-controlled paths remain untouched.
    Evidence: .omo/evidence/tick-oos-validation-20260603/final-verification.txt
  ```

- [x] F3. Real Manual QA

  **What to do**: Use the real dashboard/browser or curl channel to inspect the final P2/P4 runs. Capture a screenshot if browser automation is available; otherwise capture `/ui/`, `/runs`, `/run_state`, `/edge_ratio`, and `/feature_importance` responses. This is mandatory because run evidence is user-visible through the dashboard.
  **Must NOT do**: Do not click approval/export controls.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/tick-oos-validation-20260603/final-dashboard-qa.txt` contains the exact UI/API checks performed.
  - [ ] If screenshot is captured, it is stored as `.omo/evidence/tick-oos-validation-20260603/final-dashboard.png`.

  **QA Scenarios**:
  ```text
  Scenario: Real dashboard QA
    Tool: curl.exe or Playwright
    Steps:
      curl.exe -sS http://127.0.0.1:8770/ui/
      curl.exe -sS http://127.0.0.1:8770/runs
      curl.exe -sS "http://127.0.0.1:8770/run_state?run_id=tick_oos_p2_train_2023_2025_20260603"
      curl.exe -sS "http://127.0.0.1:8770/edge_ratio?run_id=tick_oos_p2_train_2023_2025_20260603&fine_time=true"
    Expected: UI/API are reachable or exact service unavailable reason is recorded; no export is invoked.
    Evidence: .omo/evidence/tick-oos-validation-20260603/final-dashboard-qa.txt
  ```

- [x] F4. Scope Fidelity Check

  **What to do**: Compare final git status and evidence against the original guardrails. Ensure the final response to the user states the honest verdict: infrastructure/run evidence, OOS result, and whether human-level/superior claim is proven.
  **Must NOT do**: Do not hide inconclusive OOS or resource blockers.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/tick-oos-validation-20260603/final-scope-fidelity.txt` records final `git status --short --branch`, protected-path status, and final verdict from `p5-decision-card.md`.
  - [ ] The final user summary says one of: `candidate promoted by evidence`, `candidate rejected by evidence`, or `needs more evidence`, matching P5.

  **QA Scenarios**:
  ```text
  Scenario: Scope fidelity final check
    Tool: powershell
    Steps:
      git status --short --branch
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      Read final verdict from p5-decision-card.md.
    Expected: No source/protected-path drift caused by execution; final message matches the decision card.
    Evidence: .omo/evidence/tick-oos-validation-20260603/final-scope-fidelity.txt
  ```

## Commit Strategy
- Commit: NO by default. This plan produces OMO evidence and runtime state; it does not change source code.
- If the user later requests a commit, stage files explicitly. Do not use `git add -A`. Commit title/body must be Korean.

## Success Criteria
- The executor can run `$start-work tick-oos-validation-20260603` and complete every top-level checkbox without making strategy-promotion decisions manually.
- The final answer distinguishes infrastructure maturity from proven human-level performance.
- Protected branch invariants remain intact.
