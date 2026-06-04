# TICK 조건식 연구 대시보드 고도화 계획

## TL;DR
> **Summary**: 기존 AI strategy loop 대시보드를 조건식 연구 워크벤치로 확장한다. 변수 상관/조합 분석, 전략 코드·diff·프롬프트 추적, run 비교, 그래프 가독성, 진행/엔진 상태, wiki형 연구 기록을 한 흐름으로 묶되 이전 OOS 결과(`REJECT_CANDIDATE`)는 승격 근거로 쓰지 않는다.
> **Deliverables**:
> - 변수 상관/조합 분석 백엔드와 dashboard heatmap/panel
> - 매수/매도 전략 코드 보기와 이전 세대 diff, 프롬프트 로그 보기
> - run 비교 콘솔 확장: 기간/연도, min/tick, 시간창, 수익금/수익률, elapsed/cost
> - 그래프 UX 개선: 누적수익곡선 색상, 시간대별/동시보유, score/payoff 설명
> - 진행률/예상시간/남은시간/소요시간, 엔진 상태/로그/config 표시
> - 연구 wiki/read-only docs browser와 연구기법 registry
> - 테스트, API smoke, dashboard manual QA evidence
> **Effort**: XL
> **Parallel**: YES - 5 waves
> **Critical Path**: P0 baseline -> backend contracts -> frontend panels -> wiki/research registry -> final QA

## Context
### Original Request
- 사용자는 조건식을 사람이 차트·호가·시장 경험으로 오래 수정해 만드는 과정을 AI와 컴퓨팅 파워로 대체/가속하려는 목표를 명시했다.
- 요청 범위는 변수별 상관도/히트맵/변수 조합 연구, 조건식 코드·diff·프롬프트 가시화, 지수 비교, 그래프/점수/payoff 설명, 진행률/엔진 로그/config, wiki형 연구 문서, run 비교 콘솔 확장, 연구기법 이력 기록이다.
- 이전 `$start-work tick-oos-validation-20260603` 결과는 유지한다: P4 `fails_seed`, P5 `Final Verdict: REJECT_CANDIDATE`.

### Interview Summary
- 추가 질문 없이 진행한다. 사용자는 `$ulw-plan`을 명시했고, 요구가 Architecture급이므로 기본값을 적용해 단일 OMO 실행 계획으로 만든다.
- 기본값: 첫 구현에서는 Naver 지수 네트워크 의존을 넣지 않는다. 로컬/엔진 지수 데이터가 확인되면 read-only 비교를 구현하고, 없으면 UI에 `index_unavailable`을 표시한다.
- 테스트 전략: tests-after + agent-executed API/GUI QA. 기존 테스트 인프라가 충분하다.

### Metis Review (gaps addressed)
- Metis 에이전트는 두 차례 대기와 후속 지시에도 결과를 반환하지 않아 inconclusive로 처리했다.
- 자체 반영 리스크:
  - 변수 간 Pearson/Spearman 상관 모듈은 아직 production path에 없다. 새 모듈은 분석 전용/read-only로 추가한다.
  - prompt DB는 존재하지만 `prompt_logging_enabled`가 켜져야 기록된다. UI는 "기록 없음"을 blocker로 정직하게 보여야 한다.
  - wiki/docs browser는 임의 파일 접근 위험이 있으므로 whitelist directory만 읽는다.
  - 지수 비교는 로컬 지수 데이터 경로 확인 전까지 optional/disabled 상태로 설계한다.
  - dashboard 재배치는 기능 추가보다 regression 위험이 크므로, 기존 컴포넌트 확장 후 마지막에 layout 정리한다.

## Work Objectives
### Core Objective
조건식 연구자가 현재 run, 세대별 전략, 변수/세그먼트 분석, 프롬프트, 그래프, 비교, 문서화까지 한 화면 흐름에서 검토하고 AI에게 상태를 설명할 수 있는 연구 대시보드/프로세스를 구축한다.

### Deliverables
- `ai_strategy_loop/fitness/correlation.py`
- `ai_strategy_loop/dashboard/app.py` read-only endpoints 확장
- `ai_strategy_loop/dashboard/frontend/analysis.jsx`, `chart.jsx`, `code-viewer.jsx`, `table.jsx`, `engine.jsx`, `panels.jsx`, `app.jsx` 확장
- `docs/research/condition_research/wiki/` 초기 연구 문서
- 신규/확장 테스트: dashboard correlation, prompts, strategy diff, run compare, wiki, chart/table regressions
- `.omo/evidence/tick-research-dashboard-upgrade-20260603/` QA/API/browser evidence

### Definition of Done
- 변수 상관/조합 분석 API가 per-trade CSV 기반으로 Pearson/Spearman, outcome correlation, top feature pairs, heatmap payload를 반환한다.
- dashboard에서 edge/feature/correlation 분석, 전략 코드/diff, prompt log, run comparison, wiki docs를 볼 수 있다.
- score/graded/payoff/period/year/min/tick/engine config/progress/logs가 사용자에게 설명 가능하게 표시된다.
- `current generation backtest detail` 클릭과 매수/매도 코드 미표시 문제가 regression test로 잠긴다.
- 지수 비교는 로컬 데이터가 있으면 표시하고, 없으면 정확한 unavailable reason을 표시한다.
- final verification commands pass:
  - `git diff --check`
  - `python scripts/verify_nonrelease_sync.py`
  - `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json`
  - focused pytest suite

### Must Have
- 기존 dashboard API 패턴과 frontend vanilla React JSX 패턴을 따른다.
- 신규 분석은 하드게이트/engine/winner/export에 관여하지 않는 read-only 분석으로만 구현한다.
- prompt viewer는 `prompts` table에 기록된 것만 보여주며, 기록이 없으면 "prompt_logging_enabled 필요"를 표시한다.
- 전략 code/diff는 loop strategy DB read-only 조회만 사용한다.
- 모든 기간/연도, timeframe(min/tick), universe time window, run id, gen no를 항상 표시한다.
- wiki/docs browser는 repo 내부 whitelist 경로만 읽는다.

### Must NOT Have
- No edits to backtest engines, hard gates, `backtest/graph/`, live broker runtime, production strategy DB wiring.
- No `final_approval` WebSocket action and no `export_winner(...)`.
- No V3K gate advancement, USER_ACK, KHOPENAPI connect/login, live order wiring.
- No protected path writes or cleanup: `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`.
- No network dependency for index comparison in first implementation.
- No claim that the previous AI candidate is human-level/superior.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after with pytest, plus targeted frontend static tests and dashboard API smoke.
- QA policy: Every task has agent-executed scenarios with concrete curl/TestClient/file artifacts.
- Evidence root: `.omo/evidence/tick-research-dashboard-upgrade-20260603/`
- Baseline focused tests before edits:
  - `python -m pytest tests/unit/test_dashboard_backtest_detail.py tests/unit/test_dashboard_equity_curves.py tests/unit/test_dashboard_profit_codeview.py tests/unit/test_dashboard_run_state.py tests/unit/test_prompt_logging.py tests/unit/test_edge_ratio.py tests/unit/test_feature_importance.py tests/unit/test_adaptive_timing.py tests/unit/test_dashboard_hall_of_fame.py -q`
- Final focused tests add new tests from this plan.

## Execution Strategy
### Parallel Execution Waves
Wave 1: Baseline, API/data contract design, frontend layout inventory.
Wave 2: Backend read-only endpoints: correlation, prompts/diff, run compare, wiki/index.
Wave 3: Frontend panels: analysis lab, strategy/prompt viewer, run compare, charts/engine.
Wave 4: Research registry/wiki content and AI state explanation pack.
Wave 5: End-to-end QA, browser/manual dashboard checks, final verification.

### Dependency Matrix
| Task | Depends On | Blocks |
| --- | --- | --- |
| 1 Baseline | none | all |
| 2 Correlation backend | 1 | 7 |
| 3 Prompt/code/diff backend | 1 | 8 |
| 4 Run compare/progress metadata backend | 1 | 9, 10 |
| 5 Wiki/index backend | 1 | 11, 12 |
| 6 Research registry docs | 1 | 11, 12 |
| 7 Analysis lab frontend | 2 | 13 |
| 8 Strategy/prompt frontend | 3 | 13 |
| 9 Run compare frontend | 4 | 13 |
| 10 Graph/engine/table UX | 4 | 13 |
| 11 Wiki frontend | 5, 6 | 13 |
| 12 AI state explanation pack | 3, 4, 5, 6 | 13 |
| 13 Integrated dashboard QA | 7, 8, 9, 10, 11, 12 | F1-F4 |

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: References + Acceptance Criteria + QA Scenarios.

- [x] 1. P0 baseline snapshot and dashboard contract freeze

  **What to do**: Create `.omo/evidence/tick-research-dashboard-upgrade-20260603/`. Capture branch, HEAD, dirty state, protected-path state, dashboard health, current run list, and previous OOS verdict artifacts. Run baseline focused tests before edits. Record that `tick-oos-validation-20260603` verdict remains `REJECT_CANDIDATE`.
  **Must NOT do**: Do not clean dirty files. Do not edit runtime DBs manually. Do not stop pre-existing dashboard processes.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 2-13 | Blocked By: none

  **References**:
  - Root rules: `AGENTS.md` - branch role, protected paths, verifier commands.
  - Previous verdict: `.omo/evidence/tick-oos-validation-20260603/p5-decision-card.md` - `Final Verdict: REJECT_CANDIDATE`.
  - Dashboard health: `ai_strategy_loop/dashboard/app.py:1043` - `/health`.
  - Baseline API: `ai_strategy_loop/dashboard/app.py:1086` - `/runs`; `:1095` - `/run_state`.

  **Acceptance Criteria**:
  - [ ] `safety-snapshot.txt` contains branch, HEAD, dirty state, protected-path status, dashboard health, and previous verdict.
  - [ ] `baseline-tests.txt` contains baseline focused pytest output.
  - [ ] No protected-path git status output is introduced by the task.

  **QA Scenarios**:
  ```text
  Scenario: Baseline contract capture
    Tool: powershell + curl.exe
    Steps:
      git status --short --branch
      git rev-parse HEAD
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      curl.exe -sS http://127.0.0.1:8770/health
      curl.exe -sS http://127.0.0.1:8770/runs
    Expected: Evidence files exist; protected-path status is empty or explicitly pre-existing.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/safety-snapshot.txt

  Scenario: Baseline tests
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      python -m pytest tests/unit/test_dashboard_backtest_detail.py tests/unit/test_dashboard_equity_curves.py tests/unit/test_dashboard_profit_codeview.py tests/unit/test_dashboard_run_state.py tests/unit/test_prompt_logging.py tests/unit/test_edge_ratio.py tests/unit/test_feature_importance.py tests/unit/test_adaptive_timing.py tests/unit/test_dashboard_hall_of_fame.py -q
    Expected: Tests pass or exact pre-existing failures are recorded before implementation.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/baseline-tests.txt
  ```

  **Commit**: NO | Message: n/a | Files: `.omo/evidence/tick-research-dashboard-upgrade-20260603/*`

- [x] 2. Backend variable correlation and combination analysis API

  **What to do**: Add read-only analysis module `ai_strategy_loop/fitness/correlation.py` and dashboard endpoint `/variable_correlation`. Use per-trade CSVs resolved by run id, same source resolution pattern as `/edge_ratio` and `/feature_importance`. Return Pearson/Spearman feature-to-outcome correlations, feature-to-feature matrix for numeric `B_*` columns, top pairs by absolute correlation, and insufficient-data payloads. Keep it analysis-only; no score/gate/generation influence.
  **Must NOT do**: Do not use `S_*`, `R_*`, or result/leakage columns as generated buy-condition inputs. Do not modify hard gate or engines. Do not run a backtest from this endpoint.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 7 | Blocked By: 1

  **References**:
  - Existing edge endpoint: `ai_strategy_loop/dashboard/app.py:880` and `:1171` - CSV pooling/read-only API pattern.
  - Existing feature endpoint: `ai_strategy_loop/dashboard/app.py:945` and `:1185` - `B_*` feature analysis endpoint pattern.
  - Feature module: `ai_strategy_loop/fitness/feature_importance.py:105` and `:241` - pure analysis from CSVs.
  - Analyzer helpers: `cli/analyzer.py:67`, `:247`, `:285`, `:346` - feature columns, quantile candidates, t-test, result CSV analysis.
  - Tests to mirror: `tests/unit/test_feature_importance.py:199`, `tests/unit/test_edge_ratio.py:190`.

  **Acceptance Criteria**:
  - [ ] `compute_variable_correlation(df)` returns deterministic JSON-safe output for numeric `B_*` features and outcome column `수익률`.
  - [ ] `variable_correlation_from_csvs(paths, method="pearson|spearman")` skips missing files and returns `{"insufficient": true}` for empty pools.
  - [ ] `/variable_correlation?run_id=...&method=spearman` returns HTTP 200 without DB mutation.
  - [ ] Unit tests cover exact values, low-sample guard, missing columns, Spearman/Pearson switch, and endpoint route.

  **QA Scenarios**:
  ```text
  Scenario: Correlation endpoint happy path
    Tool: pytest + curl.exe
    Steps:
      python -m pytest tests/unit/test_variable_correlation.py -q
      curl.exe -sS "http://127.0.0.1:8770/variable_correlation?run_id=tick_oos_p4_seed_2022_20260603&method=spearman"
    Expected: JSON has method, pooled_trades, outcome_correlations, feature_matrix, top_pairs.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/task-2-correlation-api.json

  Scenario: Insufficient data
    Tool: pytest
    Steps:
      Unit test calls variable_correlation_from_csvs([]).
    Expected: `{"insufficient": true, "pooled_trades": 0}`.
    Evidence: tests/unit/test_variable_correlation.py
  ```

  **Commit**: YES | Message: `feat: 조건식 변수 상관 분석 API 추가` | Files: `ai_strategy_loop/fitness/correlation.py`, `ai_strategy_loop/dashboard/app.py`, `tests/unit/test_variable_correlation.py`

- [x] 3. Backend prompt, strategy diff, and current-code inspection APIs

  **What to do**: Add read-only endpoints `/prompts`, `/strategy_diff`, and strengthen `/strategy_code` behavior. `/prompts?run_id=...&gen_no=...` reads `LoopState.get_prompts()` and returns prompt metadata plus user/system text heads with hashes. `/strategy_diff?run_id=...&gen_no=...&base_gen=previous` returns buy/sell names, code, previous code, and unified diff lines. Preserve existing `/strategy_code` contract.
  **Must NOT do**: Do not expose secrets, auth tokens, or arbitrary files. Do not write prompt records from the dashboard. Do not call LLMs.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8, 12 | Blocked By: 1

  **References**:
  - Prompt schema: `ai_strategy_loop/controller/state.py:124`, `:404`, `:458`.
  - Prompt logging requirement: `ai_strategy_loop/controller/loop.py:564`, `:1184`.
  - Strategy code payload: `ai_strategy_loop/dashboard/app.py:597`, `:1125`.
  - Code viewer frontend: `ai_strategy_loop/dashboard/frontend/code-viewer.jsx:87`.
  - Existing code tests: `tests/unit/test_dashboard_profit_codeview.py:277`, `:340`.
  - Prompt tests: `tests/unit/test_prompt_logging.py:135`.

  **Acceptance Criteria**:
  - [ ] `/prompts` returns prompt records for a seeded test DB and clear `{"prompts": [], "reason": "prompt_logging_not_enabled_or_no_records"}` when empty.
  - [ ] `/strategy_diff` returns `buy_diff` and `sell_diff` arrays for seeded gen N vs gen N-1.
  - [ ] Existing `/strategy_code` tests still pass.
  - [ ] Frontend can rely on fields: `run_id`, `gen_no`, `buy_name`, `sell_name`, `base_gen`, `buy_diff`, `sell_diff`, `prompts`.

  **QA Scenarios**:
  ```text
  Scenario: Strategy diff seeded route
    Tool: pytest
    Steps:
      Seed loop_runs.db and loop_strategies.db with gen0/gen1 buy/sell code.
      Call `/strategy_diff?run_id=runX&gen_no=1`.
    Expected: HTTP 200; diff includes changed condition lines for both buy and sell.
    Evidence: tests/unit/test_dashboard_strategy_diff.py

  Scenario: Prompt records absent
    Tool: curl.exe
    Steps:
      curl.exe -sS "http://127.0.0.1:8770/prompts?run_id=tick_oos_p2_train_2023_2025_20260603"
    Expected: HTTP 200; empty prompt list with explicit no-record reason, not a silent success.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/task-3-prompts-empty.json
  ```

  **Commit**: YES | Message: `feat: 전략 diff와 프롬프트 조회 API 추가` | Files: `ai_strategy_loop/dashboard/app.py`, `tests/unit/test_dashboard_strategy_diff.py`, `tests/unit/test_dashboard_prompts.py`

- [x] 4. Backend run comparison, engine metadata, and progress payload enrichment

  **What to do**: Extend `/runs`, `/runs/compare`, `/run_state`, and `/generation_durations` payloads with period string, start/end year, timeframe, universe time window, final profit, return pct, trade count, daily trades, max holdings, elapsed seconds, generation duration, cost/count formatted to one decimal when available, and active config summary. Keep old fields intact.
  **Must NOT do**: Do not change run selection or scoring. Do not require a running dashboard process for unit tests.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 9, 10, 12 | Blocked By: 1

  **References**:
  - Runs payload: `ai_strategy_loop/dashboard/app.py:169`, `:1086`.
  - Generation durations: `ai_strategy_loop/dashboard/app.py:193`, `:1106`.
  - Run compare endpoint: `ai_strategy_loop/dashboard/app.py:1116`.
  - Lineage compare: `ai_strategy_loop/controller/lineage.py:223`.
  - State conversion active config/latest: `ai_strategy_loop/controller/state.py:783`, `:891`.
  - Existing period/HOF helpers: `tests/unit/test_dashboard_hall_of_fame.py:212`, `:244`.

  **Acceptance Criteria**:
  - [ ] `/runs` rows include sortable `final_profit`, `total_profit_pct`, `period`, `timeframe`, `years`, `elapsed_sec`.
  - [ ] `/runs/compare` includes per-run and per-generation metric rows suitable for frontend table rendering.
  - [ ] `/run_state.active_config` visibly includes `bt_timeframe`, `bt_full_start`, `bt_full_end`, `bt_universe_start_time`, `bt_universe_end_time`.
  - [ ] Existing `/runs` consumers remain compatible.

  **QA Scenarios**:
  ```text
  Scenario: Enriched runs payload
    Tool: pytest
    Steps:
      Seed runs/generations with config_json containing bt_full_start/end and bt_timeframe.
      Call `/runs`.
    Expected: Row has period `2023-01-01 ~ 2025-12-31`, timeframe `tick`, final_profit, return pct.
    Evidence: tests/unit/test_dashboard_runs_enriched.py

  Scenario: Run compare includes timing and profit
    Tool: curl.exe
    Steps:
      curl.exe -sS "http://127.0.0.1:8770/runs/compare?ids=tick_oos_p4_seed_2022_20260603,tick_oos_p4_ai_2022_20260603"
    Expected: HTTP 200; rows include run ids, profit, return pct, period/timeframe fields.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/task-4-runs-compare.json
  ```

  **Commit**: YES | Message: `feat: run 비교와 진행 메타데이터 확장` | Files: `ai_strategy_loop/dashboard/app.py`, `ai_strategy_loop/controller/lineage.py`, `tests/unit/test_dashboard_runs_enriched.py`

- [x] 5. Safe wiki/docs and optional index comparison backend

  **What to do**: Add read-only docs endpoints `/research_docs` and `/research_doc?id=...` with whitelist roots `docs/research/condition_research`, `docs/reference/STOM_Good_Results`, selected update logs, and generated wiki folder `docs/research/condition_research/wiki`. Add `/index_compare` that first checks local engine/index data availability; if no supported local source is discovered, returns `{"available": false, "reason": "local_index_source_not_found"}`. Do not add Naver network fetching in this implementation.
  **Must NOT do**: Do not serve arbitrary paths. Do not write docs from dashboard. Do not add network dependency.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 11, 12 | Blocked By: 1

  **References**:
  - Docs guidance: `docs/AGENTS.md:11` and `:24`.
  - Reference screenshots: `ai_strategy_loop/dashboard/app.py:1075`; `ai_strategy_loop/dashboard/frontend/chart.jsx:1523`.
  - Human reference tests: `tests/unit/test_dashboard_hall_of_fame.py:303`.
  - Backtest data/index hints: `backtest/backengine_base.py:371`, `:710`.
  - Existing reference docs: `docs/reference/STOM_Good_Results/backtest_analysis_report.md`.

  **Acceptance Criteria**:
  - [ ] `/research_docs` lists only whitelisted markdown docs with ids, titles, category, updated time.
  - [ ] `/research_doc?id=...` returns markdown text only for whitelisted ids and rejects traversal.
  - [ ] `/index_compare?run_id=...` returns either local comparison payload or unavailable reason; no network call.
  - [ ] Tests cover path traversal rejection and missing index source.

  **QA Scenarios**:
  ```text
  Scenario: Wiki docs list/read
    Tool: pytest + curl.exe
    Steps:
      python -m pytest tests/unit/test_dashboard_research_docs.py -q
      curl.exe -sS http://127.0.0.1:8770/research_docs
    Expected: Docs list contains reference/good-result docs and no paths outside whitelist.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/task-5-docs.json

  Scenario: Index unavailable is honest
    Tool: pytest
    Steps:
      Test `/index_compare` with no local source.
    Expected: HTTP 200 with `available=false`, no exception, no network call.
    Evidence: tests/unit/test_dashboard_index_compare.py
  ```

  **Commit**: YES | Message: `feat: 연구 문서와 지수 비교 조회 API 추가` | Files: `ai_strategy_loop/dashboard/app.py`, `tests/unit/test_dashboard_research_docs.py`, `tests/unit/test_dashboard_index_compare.py`

- [x] 6. Research method registry and initial wiki content

  **What to do**: Create wiki markdown docs under `docs/research/condition_research/wiki/` documenting current research methods: hillclimb/refine, GA, band compiler/seed_902 band, Optuna band optimizer design, edge ratio, feature importance, adaptive timing, segment feedback, prompt logging, PBO/DSR gap, tick OOS failure lesson. Include good-strategy reference policy and "screenshots are reference, not live proof".
  **Must NOT do**: Do not claim rejected candidates are good strategies. Do not copy protected DB content. Do not create production strategy rows.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 11, 12 | Blocked By: 1

  **References**:
  - Handoff methods map: `docs/AGENT_HANDOFF.md:79`, `:80`, `:92`.
  - Analysis audit: `docs/update_log/2026-06-02_analysis_capability_audit.md`.
  - Band design: `docs/update_log/2026-06-02_band_generator_design.md:26`, `:40`.
  - Dashboard batch context: `docs/update_log/2026-06-02_dashboard_batch_resume_context.md:25`, `:27`.
  - Tick handoff: `docs/update_log/2026-06-03_tick_program_complete_handoff.md:64`, `:67`.
  - Latest OOS verdict: `.omo/evidence/tick-oos-validation-20260603/p5-decision-card.md`.

  **Acceptance Criteria**:
  - [ ] Wiki docs exist with sections for methods, metrics, pitfalls, current rejected candidate lesson, next experiments.
  - [ ] Docs define `graded`, `hard gate`, `payoff_ratio`, `edge_ratio`, `feature_importance`, `PBO/DSR advisory blocker`.
  - [ ] Docs are discoverable by `/research_docs` from Task 5.

  **QA Scenarios**:
  ```text
  Scenario: Wiki docs sanity
    Tool: powershell
    Steps:
      rg -n "REJECT_CANDIDATE|payoff_ratio|edge_ratio|feature_importance|PBO|DSR|segment feedback" docs/research/condition_research/wiki
    Expected: Required terms appear; no "PROMOTE_CANDIDATE" claim appears.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/task-6-wiki-rg.txt

  Scenario: Dashboard docs endpoint sees wiki
    Tool: curl.exe
    Steps:
      curl.exe -sS http://127.0.0.1:8770/research_docs
    Expected: Wiki docs are listed with safe ids.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/task-6-docs-api.json
  ```

  **Commit**: YES | Message: `docs: 조건식 연구 wiki 초기화` | Files: `docs/research/condition_research/wiki/*.md`

- [x] 7. Frontend Research Lab for correlation, feature importance, and edge heatmaps

  **What to do**: Extend `analysis.jsx` with a Research Lab panel containing tabs for Edge, Feature Importance, Correlation, and Variable Combinations. Reuse existing heatmap/bar components where possible. Add method selector `pearson|spearman`, segment axis selector, min sample display, and explicit insufficient-data state.
  **Must NOT do**: Do not create nested cards or marketing layout. Do not hide insufficient data. Do not use viewport-scaled fonts.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 13 | Blocked By: 2

  **References**:
  - Existing analysis UI: `ai_strategy_loop/dashboard/frontend/analysis.jsx:78`, `:264`, `:384`, `:524`.
  - App wiring: `ai_strategy_loop/dashboard/frontend/app.jsx:224`.
  - Existing frontend tests: `tests/unit/test_feature_importance.py` plus static patterns in `test_dashboard_backtest_detail.py:343`.

  **Acceptance Criteria**:
  - [ ] Research Lab calls `/variable_correlation` for selected run and method.
  - [ ] Heatmap cells show variable names, correlation value, sample count, and color scale.
  - [ ] Existing EdgeRatioPanel and FeatureImportancePanel behavior remains available.
  - [ ] Static frontend tests verify labels, endpoint string, method selector, empty state.

  **QA Scenarios**:
  ```text
  Scenario: Research Lab static contract
    Tool: pytest
    Steps:
      python -m pytest tests/unit/test_dashboard_research_lab_frontend.py -q
    Expected: Component exposes correlation tab, fetches `/variable_correlation`, renders insufficient state.
    Evidence: tests/unit/test_dashboard_research_lab_frontend.py

  Scenario: Live API panel smoke
    Tool: curl.exe
    Steps:
      curl.exe -sS "http://127.0.0.1:8770/variable_correlation?run_id=tick_oos_p4_seed_2022_20260603&method=spearman"
    Expected: JSON response is compatible with frontend payload shape.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/task-7-correlation-smoke.json
  ```

  **Commit**: YES | Message: `feat: 변수 상관 연구 패널 추가` | Files: `ai_strategy_loop/dashboard/frontend/analysis.jsx`, `ai_strategy_loop/dashboard/frontend/styles.css`, `tests/unit/test_dashboard_research_lab_frontend.py`

- [x] 8. Frontend strategy code, previous diff, and prompt timeline viewer

  **What to do**: Extend `code-viewer.jsx` or add adjacent modal/panel to show buy/sell code, previous generation diff, prompt records, injected features, model/token counts, and no-record explanation. Fix missing buy/sell code display by ensuring CodeViewer fetch fallback is visible for selected run/gen. Add "copy AI context" safe text block referencing current run/gen only.
  **Must NOT do**: Do not display secrets. Do not make prompt viewer trigger LLM calls. Do not call approval/export controls.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 13 | Blocked By: 3

  **References**:
  - Code viewer fetch: `ai_strategy_loop/dashboard/frontend/code-viewer.jsx:87`, `:107`, `:120`.
  - Table action: `ai_strategy_loop/dashboard/frontend/table.jsx:167`, `:173`.
  - Phase prompt context: `ai_strategy_loop/dashboard/frontend/phase-detail.jsx:183`.
  - Backend endpoints from Task 3.
  - Existing code tests: `tests/unit/test_dashboard_profit_codeview.py:340`.

  **Acceptance Criteria**:
  - [ ] For any generation row, CodeViewer displays buy and sell tabs or explicit unavailable reason.
  - [ ] Diff tab compares selected gen against previous gen by default, with override for gen0 showing no base.
  - [ ] Prompt tab displays prompt_count and prompt rows or no-record reason.
  - [ ] Current generation detail click still works after adding prompt/diff controls.

  **QA Scenarios**:
  ```text
  Scenario: Code/diff/prompt UI contract
    Tool: pytest
    Steps:
      python -m pytest tests/unit/test_dashboard_strategy_prompt_frontend.py -q
    Expected: Frontend references `/strategy_code`, `/strategy_diff`, `/prompts`, buy/sell/diff/prompt tabs.
    Evidence: tests/unit/test_dashboard_strategy_prompt_frontend.py

  Scenario: Current gen click regression
    Tool: pytest
    Steps:
      Test GenerationsTable click handler passes selected gen to BacktestDetailChart and CodeViewer.
    Expected: Selected gen no is propagated; detail panel fetch URL uses that gen.
    Evidence: tests/unit/test_dashboard_current_gen_detail.py
  ```

  **Commit**: YES | Message: `feat: 전략 코드 diff와 프롬프트 타임라인 표시` | Files: `ai_strategy_loop/dashboard/frontend/code-viewer.jsx`, `ai_strategy_loop/dashboard/frontend/table.jsx`, `ai_strategy_loop/dashboard/frontend/app.jsx`, `tests/unit/test_dashboard_strategy_prompt_frontend.py`

- [x] 9. Frontend run comparison console enrichment

  **What to do**: Extend `RunComparePanel` to show period, year range, timeframe, universe time, profit, return %, trades, daily trades, MDD, payoff, max holdings, elapsed/duration, and cost/count one decimal. Add sorting by total profit and toggles to compare seed vs AI runs.
  **Must NOT do**: Do not aggregate OOS/training into a promotion claim. Do not hide negative rows.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 13 | Blocked By: 4

  **References**:
  - Run compare frontend: `ai_strategy_loop/dashboard/frontend/panels.jsx:705`.
  - Runs API: `ai_strategy_loop/dashboard/app.py:1116`.
  - Hall of fame sorting patterns: `ai_strategy_loop/dashboard/frontend/chart.jsx:1276`, `:1314`, `:1326`.
  - Existing HOF tests for total profit/period: `tests/unit/test_dashboard_hall_of_fame.py:380`.

  **Acceptance Criteria**:
  - [ ] Run comparison table includes `총수익금`, `수익률`, `기간`, `연도`, `min/tick`, `시간창`, `소요시간`, `비용/요청수`.
  - [ ] Sorting by total profit works and negative rows remain visible.
  - [ ] Static tests confirm column labels and sort state.

  **QA Scenarios**:
  ```text
  Scenario: Run compare display contract
    Tool: pytest
    Steps:
      python -m pytest tests/unit/test_dashboard_run_compare_frontend.py -q
    Expected: Required Korean labels and enriched fields are rendered.
    Evidence: tests/unit/test_dashboard_run_compare_frontend.py

  Scenario: Seed vs AI comparison smoke
    Tool: curl.exe
    Steps:
      curl.exe -sS "http://127.0.0.1:8770/runs/compare?ids=tick_oos_p4_seed_2022_20260603,tick_oos_p4_ai_2022_20260603"
    Expected: Both runs present with profit and period metadata.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/task-9-compare-smoke.json
  ```

  **Commit**: YES | Message: `feat: run 비교 콘솔 메타데이터 확장` | Files: `ai_strategy_loop/dashboard/frontend/panels.jsx`, `ai_strategy_loop/dashboard/frontend/styles.css`, `tests/unit/test_dashboard_run_compare_frontend.py`

- [x] 10. Graph, engine, progress, and generations table UX fixes

  **What to do**: Improve chart/table UX without changing data semantics. Add clear legends and explanations for `graded`, `hard gate`, `payoff_ratio`, `calmar`, `uptrend_r2`, `edge_ratio`. Improve equity curve color separation and line opacity. Ensure BacktestDetailChart shows period/timeframe/gen/run id, time-of-day/day labels, cumulative curve, drawdown, holdings, and honest `peak_holdings=0` reason when no buy/sell overlap data exists. Extend EnginePanel with overall progress, ETA, elapsed, remaining, engine config, min/tick, run period, recent logs.
  **Must NOT do**: Do not invent metrics. Do not mask zero holdings; show whether it is true zero or insufficient buy-time data.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 13 | Blocked By: 4

  **References**:
  - Fitness chart: `ai_strategy_loop/dashboard/frontend/chart.jsx:4`.
  - Profit chart: `ai_strategy_loop/dashboard/frontend/chart.jsx:276`.
  - Equity overlay: `ai_strategy_loop/dashboard/frontend/chart.jsx:440`.
  - Backtest detail chart: `ai_strategy_loop/dashboard/frontend/chart.jsx:892`.
  - Engine panel: `ai_strategy_loop/dashboard/frontend/engine.jsx:12`, `:126`.
  - Table columns/actions: `ai_strategy_loop/dashboard/frontend/table.jsx:10`, `:97`, `:167`.
  - Score meanings: `ai_strategy_loop/fitness/score.py:251`, `:473`, `:888`.
  - Holdings tests: `tests/unit/test_dashboard_backtest_detail.py:178`, `:367`.

  **Acceptance Criteria**:
  - [ ] Charts include visible legends and metric explanations; no text overlap at desktop width.
  - [ ] Equity curves use distinct color palette for at least 12 winners and subdued non-winners.
  - [ ] Generations table supports sorting by total profit and preserves code/detail buttons.
  - [ ] EnginePanel shows ETA/elapsed/remaining and config summary when available; otherwise shows explicit unavailable state.

  **QA Scenarios**:
  ```text
  Scenario: Chart/table static UX checks
    Tool: pytest
    Steps:
      python -m pytest tests/unit/test_dashboard_chart_explanations.py tests/unit/test_dashboard_table_sorting.py -q
    Expected: Required labels, legends, sort keys, and insufficient-data states are present.
    Evidence: tests/unit/test_dashboard_chart_explanations.py

  Scenario: Dashboard real QA
    Tool: curl.exe
    Steps:
      curl.exe -sS http://127.0.0.1:8770/ui/
      curl.exe -sS "http://127.0.0.1:8770/backtest_detail?run_id=tick_oos_p4_ai_2026_20260603&gen_no=0"
    Expected: UI loads; backtest detail payload supports holdings/no-data explanation.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/task-10-dashboard-qa.txt
  ```

  **Commit**: YES | Message: `feat: 그래프와 엔진 진행 상태 가독성 개선` | Files: `ai_strategy_loop/dashboard/frontend/chart.jsx`, `ai_strategy_loop/dashboard/frontend/engine.jsx`, `ai_strategy_loop/dashboard/frontend/table.jsx`, `ai_strategy_loop/dashboard/frontend/styles.css`, `tests/unit/test_dashboard_chart_explanations.py`, `tests/unit/test_dashboard_table_sorting.py`

- [x] 11. Frontend wiki/research documentation browser

  **What to do**: Add dashboard wiki panel that lists `/research_docs`, reads selected markdown via `/research_doc`, and links relevant docs from current run context. Include categories: Good Results, Methods, Failed Candidates, Metrics, Next Experiments. Use plain markdown rendering with minimal safe formatting or preformatted text; do not add a new frontend framework.
  **Must NOT do**: Do not render raw HTML from markdown. Do not allow arbitrary path ids.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 13 | Blocked By: 5, 6

  **References**:
  - Reference gallery pattern: `ai_strategy_loop/dashboard/frontend/chart.jsx:1523`.
  - Dashboard composition: `ai_strategy_loop/dashboard/frontend/app.jsx:193`, `:224`.
  - Docs endpoints from Task 5.
  - Docs AGENTS: `docs/AGENTS.md:11`, `:36`.

  **Acceptance Criteria**:
  - [ ] Wiki panel lists docs grouped by category and can open selected doc text.
  - [ ] It shows "reference only, not live proof" for screenshots/good results.
  - [ ] Static tests verify endpoint use and safe rendering policy.

  **QA Scenarios**:
  ```text
  Scenario: Wiki panel static contract
    Tool: pytest
    Steps:
      python -m pytest tests/unit/test_dashboard_wiki_frontend.py -q
    Expected: Component fetches `/research_docs` and `/research_doc`, renders category labels, no raw HTML renderer.
    Evidence: tests/unit/test_dashboard_wiki_frontend.py

  Scenario: Docs browser smoke
    Tool: curl.exe
    Steps:
      curl.exe -sS http://127.0.0.1:8770/research_docs
    Expected: Whitelisted docs appear; no traversal ids.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/task-11-docs-smoke.json
  ```

  **Commit**: YES | Message: `feat: 연구 wiki 패널 추가` | Files: `ai_strategy_loop/dashboard/frontend/panels.jsx`, `ai_strategy_loop/dashboard/frontend/app.jsx`, `ai_strategy_loop/dashboard/frontend/styles.css`, `tests/unit/test_dashboard_wiki_frontend.py`

- [x] 12. AI state explanation and prompt-pack workflow

  **What to do**: Add backend `/ai_context_pack?run_id=...&gen_no=...` and frontend button/panel that summarizes current research state for AI: run identity, selected gen, config, period, timeframe, latest logs, best/winner, P3/P4/P5 verdict refs if available, strategy names, prompt count, top edge/feature/correlation findings, and explicit forbidden actions. The output is copyable text/JSON only; it does not call an external AI.
  **Must NOT do**: Do not include secrets, tokens, arbitrary file contents, production DB paths, or prompt injection execution. Do not send network requests.

  **Parallelization**: Can Parallel: YES | Wave 4 | Blocks: 13 | Blocked By: 3, 4, 5, 6

  **References**:
  - Active config/latest state: `ai_strategy_loop/controller/state.py:765`, `:891`.
  - Prompt records: `ai_strategy_loop/controller/state.py:458`.
  - Analysis endpoints: `ai_strategy_loop/dashboard/app.py:1171`, `:1185`.
  - User goal memory: this plan context and `.omo/evidence/tick-oos-validation-20260603/p5-decision-card.md`.

  **Acceptance Criteria**:
  - [ ] `/ai_context_pack` returns deterministic text and JSON fields for a run, including period/timeframe/verdict/forbidden actions.
  - [ ] Frontend shows "AI에게 현재 상태 설명" panel/button and copy area.
  - [ ] Tests verify secrets are not included and missing prompt/correlation data is clearly marked.

  **QA Scenarios**:
  ```text
  Scenario: AI context pack endpoint
    Tool: pytest + curl.exe
    Steps:
      python -m pytest tests/unit/test_dashboard_ai_context_pack.py -q
      curl.exe -sS "http://127.0.0.1:8770/ai_context_pack?run_id=tick_oos_p4_ai_2026_20260603&gen_no=0"
    Expected: JSON includes summary_text, run_id, gen_no, timeframe, period, final verdict note, forbidden actions.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/task-12-ai-context.json

  Scenario: No secret leak
    Tool: pytest
    Steps:
      Test context pack text excludes token/auth/password/env secret patterns.
    Expected: Pack contains no secret-like keys.
    Evidence: tests/unit/test_dashboard_ai_context_pack.py
  ```

  **Commit**: YES | Message: `feat: AI 상태 설명 컨텍스트 팩 추가` | Files: `ai_strategy_loop/dashboard/app.py`, `ai_strategy_loop/dashboard/frontend/panels.jsx`, `tests/unit/test_dashboard_ai_context_pack.py`

- [x] 13. Integrated dashboard layout and end-to-end QA

  **What to do**: Reorganize dashboard sections only after Tasks 7-12 pass. Use a restrained operational layout: Run Monitor, Research Lab, Strategy/Prompt, Compare, Wiki. Keep first viewport focused on live run status and current research state, not a landing page. Verify no overlapping text, no broken buttons, and no approval/export action invoked.
  **Must NOT do**: Do not introduce new frontend framework or decorative hero/marketing layout. Do not click approval/export.

  **Parallelization**: Can Parallel: NO | Wave 5 | Blocks: F1-F4 | Blocked By: 7-12

  **References**:
  - App composition: `ai_strategy_loop/dashboard/frontend/app.jsx:113`, `:193`, `:277`.
  - Existing components: `analysis.jsx`, `chart.jsx`, `code-viewer.jsx`, `engine.jsx`, `panels.jsx`, `table.jsx`.
  - Dashboard tests map: `tests/unit/test_dashboard_*`.

  **Acceptance Criteria**:
  - [ ] `/ui/` loads with all major panels reachable.
  - [ ] Read-only API smoke covers `/runs`, `/run_state`, `/variable_correlation`, `/strategy_diff`, `/prompts`, `/research_docs`, `/ai_context_pack`.
  - [ ] Focused pytest suite passes.
  - [ ] Browser or curl QA records no final approval/export action.

  **QA Scenarios**:
  ```text
  Scenario: Integrated API smoke
    Tool: curl.exe
    Steps:
      curl.exe -sS http://127.0.0.1:8770/ui/
      curl.exe -sS http://127.0.0.1:8770/runs
      curl.exe -sS "http://127.0.0.1:8770/variable_correlation?run_id=tick_oos_p4_seed_2022_20260603"
      curl.exe -sS "http://127.0.0.1:8770/strategy_diff?run_id=tick_oos_p4_ai_2022_20260603&gen_no=0"
      curl.exe -sS "http://127.0.0.1:8770/research_docs"
      curl.exe -sS "http://127.0.0.1:8770/ai_context_pack?run_id=tick_oos_p4_ai_2022_20260603&gen_no=0"
    Expected: HTTP 200 for all; no approval/export endpoint invoked.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/task-13-api-smoke.json

  Scenario: Focused regression suite
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      python -m pytest tests/unit/test_dashboard_backtest_detail.py tests/unit/test_dashboard_equity_curves.py tests/unit/test_dashboard_profit_codeview.py tests/unit/test_dashboard_run_state.py tests/unit/test_prompt_logging.py tests/unit/test_edge_ratio.py tests/unit/test_feature_importance.py tests/unit/test_adaptive_timing.py tests/unit/test_dashboard_hall_of_fame.py tests/unit/test_variable_correlation.py tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_research_docs.py tests/unit/test_dashboard_ai_context_pack.py tests/unit/test_dashboard_research_lab_frontend.py tests/unit/test_dashboard_strategy_prompt_frontend.py tests/unit/test_dashboard_run_compare_frontend.py tests/unit/test_dashboard_chart_explanations.py tests/unit/test_dashboard_wiki_frontend.py -q
    Expected: Suite passes, or exact unrelated/pre-existing failures are documented.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/task-13-focused-tests.txt
  ```

  **Commit**: YES | Message: `feat: 조건식 연구 대시보드 통합 개선` | Files: `ai_strategy_loop/dashboard/frontend/app.jsx`, `ai_strategy_loop/dashboard/frontend/styles.css`, `.omo/evidence/tick-research-dashboard-upgrade-20260603/*`

## Final Verification Wave (MANDATORY - after ALL implementation tasks)
> ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
- [x] F1. Plan Compliance Audit

  **What to do**: Re-read this plan and all evidence under `.omo/evidence/tick-research-dashboard-upgrade-20260603/`. Confirm every top-level task has evidence and required acceptance criteria are met.
  **Must NOT do**: Do not mark complete if any TODO remains unchecked or evidence is missing.

  **Acceptance Criteria**:
  - [ ] `final-plan-compliance.txt` maps tasks 1-13 plus F1-F4 to evidence files.
  - [ ] It states whether forbidden actions were absent.

  **QA Scenarios**:
  ```text
  Scenario: Compliance audit
    Tool: powershell
    Steps:
      rg -n "^- \\[ \\]" .omo/plans/tick-research-dashboard-upgrade-20260603.md
      Get-ChildItem .omo/evidence/tick-research-dashboard-upgrade-20260603
      rg -n "final_approval|export_winner|USER_ACK|KHOPENAPI|taskkill" .omo/evidence/tick-research-dashboard-upgrade-20260603
    Expected: Only current final-wave unchecked items before completion; forbidden terms only appear in guardrail/audit text.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/final-plan-compliance.txt
  ```

- [x] F2. Code Quality Review

  **What to do**: Run final code and branch safety verification.
  **Must NOT do**: Do not run formatters or generators that rewrite files.

  **Acceptance Criteria**:
  - [ ] `final-verification.txt` contains `git diff --check`, `python scripts/verify_nonrelease_sync.py`, protected path status, and focused pytest output.
  - [ ] Protected path status is empty or explicitly pre-existing and unrelated.

  **QA Scenarios**:
  ```text
  Scenario: Final verification
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      git diff --check
      python scripts/verify_nonrelease_sync.py
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      python -m pytest tests/unit/test_dashboard_backtest_detail.py tests/unit/test_dashboard_equity_curves.py tests/unit/test_dashboard_profit_codeview.py tests/unit/test_dashboard_run_state.py tests/unit/test_prompt_logging.py tests/unit/test_edge_ratio.py tests/unit/test_feature_importance.py tests/unit/test_adaptive_timing.py tests/unit/test_dashboard_hall_of_fame.py tests/unit/test_variable_correlation.py tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_research_docs.py tests/unit/test_dashboard_ai_context_pack.py tests/unit/test_dashboard_research_lab_frontend.py tests/unit/test_dashboard_strategy_prompt_frontend.py tests/unit/test_dashboard_run_compare_frontend.py tests/unit/test_dashboard_chart_explanations.py tests/unit/test_dashboard_wiki_frontend.py -q
    Expected: Commands pass or exact unrelated/pre-existing failures are recorded.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/final-verification.txt
  ```

- [x] F3. Real Manual QA

  **What to do**: Exercise the real dashboard at `http://127.0.0.1:8770/ui/` and read-only API endpoints. If dashboard is not running, start `python -m ai_strategy_loop`, record PID, and stop only that PID after QA.
  **Must NOT do**: Do not click approval/export. Do not stop pre-existing dashboard PID.

  **Acceptance Criteria**:
  - [ ] `final-dashboard-qa.txt` records exact UI/API checks.
  - [ ] If a server is spawned by this task, cleanup receipt records only the spawned PID.

  **QA Scenarios**:
  ```text
  Scenario: Dashboard QA
    Tool: curl.exe or browser screenshot
    Steps:
      curl.exe -sS http://127.0.0.1:8770/ui/
      curl.exe -sS http://127.0.0.1:8770/runs
      curl.exe -sS "http://127.0.0.1:8770/variable_correlation?run_id=tick_oos_p4_seed_2022_20260603"
      curl.exe -sS "http://127.0.0.1:8770/prompts?run_id=tick_oos_p2_train_2023_2025_20260603"
      curl.exe -sS "http://127.0.0.1:8770/strategy_diff?run_id=tick_oos_p4_ai_2022_20260603&gen_no=0"
      curl.exe -sS "http://127.0.0.1:8770/research_docs"
      curl.exe -sS "http://127.0.0.1:8770/ai_context_pack?run_id=tick_oos_p4_ai_2022_20260603&gen_no=0"
    Expected: HTTP 200/readable payloads; no export/final approval endpoint invoked.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/final-dashboard-qa.txt
  ```

- [x] F4. Scope Fidelity Check

  **What to do**: Record final git status, protected-path status, and scope assertions. Ensure final user summary says this is a dashboard/process improvement, not a strategy promotion.
  **Must NOT do**: Do not hide dirty worktree state. Do not make human-level/superior claims.

  **Acceptance Criteria**:
  - [ ] `final-scope-fidelity.txt` includes final `git status --short --branch`, protected-path status, and statement that previous candidate remains rejected.
  - [ ] Final response includes the plan path and recommended `$start-work` command.

  **QA Scenarios**:
  ```text
  Scenario: Scope fidelity
    Tool: powershell
    Steps:
      git status --short --branch
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      rg -n "PROMOTE_CANDIDATE|human-level|초월|능가" .omo/evidence/tick-research-dashboard-upgrade-20260603
    Expected: Protected paths untouched; any promotion/superiority terms appear only as prohibited/guardrail context.
    Evidence: .omo/evidence/tick-research-dashboard-upgrade-20260603/final-scope-fidelity.txt
  ```

## Commit Strategy
- Commit: NO by default during `$start-work`; user can request commit after QA.
- If committing later, stage files explicitly and use Korean commit title/body.

## Success Criteria
- The dashboard becomes a condition-research workbench, not just a run monitor.
- A user can inspect current/previous strategy code, prompt history, score/payoff meanings, variable/segment/correlation heatmaps, run comparisons, and research wiki without leaving the dashboard.
- The system remains honest: previous candidate stays rejected; analysis visibility improves without changing engines/hard gates/export boundaries.
