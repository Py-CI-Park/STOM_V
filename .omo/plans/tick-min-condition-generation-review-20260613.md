# Tick/Min 조건식 생성 기능 검토 및 후속 개발 준비 계획

## TL;DR
> **Summary**: tick/min 데이터를 이용한 조건식 생성 기능은 설정·프롬프트·변수 스코프·템플릿 렌더·프리셋 생성까지는 작동 근거가 있으나, 실제 profitable 후보를 안정적으로 생성했다는 증거는 아직 부족하다. 이 계획은 소스 업데이트 없이 증거를 재검토하고 달성률·부족분·후속 개발 순서를 결정 가능한 보고서로 산출한다.
> **Deliverables**:
> - `.omo/evidence/tick-min-condition-generation-review-20260613/review-report.md`
> - `.omo/evidence/tick-min-condition-generation-review-20260613/completion-score-matrix.json`
> - `.omo/evidence/tick-min-condition-generation-review-20260613/gap-backlog.md`
> - `.omo/evidence/tick-min-condition-generation-review-20260613/verification.txt`
> **Effort**: Medium
> **Parallel**: YES - 3 waves
> **Critical Path**: Task 1 -> Task 4 -> Task 8 -> Final Verification

## Context
### Original Request
사용자는 `$ulw-plan`을 명시했고, 위 핸드오프 문서와 현재 개발/테스트 내용을 바탕으로 다음을 원했다:
- tick/min 데이터를 이용한 조건식 생성 기능이 잘 작동하여 실제로 생성되는지 검토
- 달성률과 완성도 평가
- 현재 부족한 것과 전체 시간을 모두 고려한 조건식을 만들기 위해 부족한 것 상세 검토
- 업데이트/구현 없이 검토부터 진행하여 앞으로 할 개발 준비

### Interview Summary
추가 질문 없이 진행한다. 이유는 범위와 금지가 충분히 명확하고, 선호 결정보다 저장소 사실관계가 중요한 검토 작업이기 때문이다.

### Metis Review (gaps addressed)
별도 `metis` subagent 도구가 현재 세션에 노출되지 않아 동일 기준으로 직접 갭 분석을 수행했다.
- 문서 명령과 실제 CLI 계약 불일치: 로드맵은 `--out-prefix`, 실제 `tmap_sweep`는 `--run-id`와 `--manifest-out`.
- 단위 테스트 통과와 실전 생성 성공을 혼동할 위험: 68개 테스트는 렌더/프리셋/스코프/가드 검증이지 수익 후보 생성 증거가 아니다.
- min 풀세션은 백테스트 윈도우가 열렸지만 LLM 프롬프트가 09:00~15:00 시간대별 탐색을 직접 지도하는 근거가 약하다.
- `wf_t2c3_20260613`은 aggregate가 없어 부분 증거로만 처리해야 한다.
- 기존 min 스모크는 엔진 체인 검증에는 유효하나 게이트 실패라 전략 성과 증거로 쓰면 안 된다.

### High Accuracy Review
`momus` subagent 도구가 현재 세션에 노출되지 않아 동일 기준으로 직접 고정밀 검토했다. 결과는 **OKAY after fixes**.
- 보정 1: Definition of Done의 pytest 명령을 PowerShell 문법으로 수정했다.
- 보정 2: TL;DR에 있던 `verification.txt` 산출물이 Task 8과 F1에서 실제 생성·검증되도록 연결했다.
- 잔여 결정 필요 사항: 없음.

## Work Objectives
### Core Objective
소스 수정 없이 현재 tick/min 조건식 생성 체계의 작동 범위, 완성도, 부족분, 후속 개발 우선순위를 증거 기반으로 정리한다.

### Deliverables
- 검토 보고서: 현재 작동하는 것, 작동이 미확인인 것, 실패/리스크, 달성률, 후속 작업
- 달성률 매트릭스: 기능 영역별 0~100점 점수와 근거
- 후속 개발 백로그: source 수정 없이 다음 구현자가 바로 실행 가능한 작업 순서
- 검증 로그: 실행한 테스트/읽은 증거/소스 무수정 상태

### Definition of Done (verifiable conditions with commands)
- PowerShell에서 `$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/unit/test_warm_session_window.py tests/unit/test_variable_scope.py tests/unit/test_time_window.py tests/unit/test_time_cap_bucket_generation.py tests/unit/test_late_tick_and_min_templates.py tests/unit/test_research_presets.py -q -p no:cacheprovider` 가 통과한다.
- `review-report.md`가 tick LLM 생성, tick TMAP 스윕, min LLM 생성, min TMAP 스윕, 백테스트 윈도우, 변수 스코프, 테스트 커버리지, 실제 성과 증거를 각각 분리 평가한다.
- `completion-score-matrix.json`이 영역별 점수와 근거 파일을 포함한다.
- `gap-backlog.md`가 “검토 후 바로 개발할 작업”을 우선순위와 acceptance criteria로 정리한다.
- `verification.txt`가 실행한 검증 명령, 결과, 소스 무수정 확인, High Accuracy Review 보정 사항을 요약한다.
- `git status --short`에서 소스/테스트/운영 문서 신규 변경이 없어야 한다. 허용 변경은 `.omo/evidence/tick-min-condition-generation-review-20260613/**`뿐이다.

### Must Have
- `docs/AGENT_HANDOFF.md`, `docs/update_log/2026-06-13_dawn_handoff.md`, `docs/update_log/2026-06-13_late_tick_min_discovery_roadmap.md`, `docs/research/condition_research/2026-06-13_entry_extension_and_min_roadmap.md` 근거 반영.
- 현재 변경 중인 파일은 사용자 변경으로 간주하고 읽기만 한다.
- 단위 테스트 통과와 실DB/수익 검증을 분리한다.
- tick 데이터 한계는 09:00~09:30, min 데이터 검토 범위는 09:00~15:00 기준으로 분리한다.
- V3K 승인 게이트, 운영 DB 쓰기, 전략 실배포는 전부 범위 밖으로 둔다.

### Must NOT Have (guardrails, scope boundaries)
- 소스 코드, 테스트 파일, `docs/update_log`, `_database`, `ai_strategy_loop/state` 파일 수정 금지.
- `research_presets.py` 실행으로 config JSON을 `ai_strategy_loop/state`에 쓰지 않는다.
- `tmap_sweep` 장기 실행, LLM 호출, 운영 전략 DB 쓰기 금지. 이 계획은 검토 계획이다.
- `git add -A`, destructive git 명령, 전체 Python 프로세스 강제 종료 금지.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after + pytest + evidence audit. 이 요청은 검토/계획이므로 TDD 구현은 하지 않는다.
- QA policy: Every task has agent-executed scenarios.
- Evidence: `.omo/evidence/tick-min-condition-generation-review-20260613/task-{N}-*.txt|json|md`

## Execution Strategy
### Parallel Execution Waves
Wave 1: Task 1, Task 2, Task 3
Wave 2: Task 4, Task 5, Task 6
Wave 3: Task 7, Task 8

### Dependency Matrix (full, all tasks)
| Task | Depends On | Blocks |
|---|---|---|
| 1. Evidence Inventory | None | 4, 8 |
| 2. Pipeline Contract Audit | None | 4, 5, 6 |
| 3. Test Coverage Audit | None | 4, 8 |
| 4. Completion Score Matrix | 1, 2, 3 | 8 |
| 5. Tick Late Readiness Review | 2 | 8 |
| 6. Min Full-Session Readiness Review | 2 | 8 |
| 7. CLI/Runbook Consistency Review | 1, 2 | 8 |
| 8. Final Review Report and Backlog | 4, 5, 6, 7 | Final Verification |

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: References + Acceptance Criteria + QA Scenarios.

- [x] 1. Evidence Inventory and Baseline Snapshot

  **What to do**: Create `.omo/evidence/tick-min-condition-generation-review-20260613/task-1-evidence-inventory.md`. List every evidence source used, classify each as `design doc`, `unit test`, `runtime log`, `partial run`, or `roadmap`. Record whether each source proves infrastructure, generation, backtest execution, profitability, or OOS robustness.
  **Must NOT do**: Do not edit source/docs. Do not treat untracked evidence as complete unless aggregate/final markers exist.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 4, 8 | Blocked By: None

  **References**:
  - Pattern: `docs/AGENT_HANDOFF.md:43` - T0~T4 completion and known limitation that full toggle-on multiyear/OOS was not yet done.
  - Pattern: `docs/update_log/2026-06-13_dawn_handoff.md:8` - THETA champion and V6 remaining decision.
  - Pattern: `.omo/evidence/tmap-walkforward/llm_context_failure_lessons.md:1` - rejected LLM/min/tick families and failure lessons.
  - Pattern: `.omo/evidence/tmap-walkforward/r1_ablation_findings.md:1` - R1/R5/R4 conclusions and THETA/R2R3_B status.
  - Pattern: `.omo/evidence/tmap-walkforward/wf_t2c3_20260613/w0_manifest.json:1` - partial w0 evidence only, not aggregate WF completion.

  **Acceptance Criteria**:
  - [ ] Evidence inventory exists and contains at least 12 entries.
  - [ ] Each entry has `path`, `type`, `proves`, `does_not_prove`, and `confidence`.
  - [ ] `wf_t2c3_20260613` is explicitly marked partial because `aggregate.json` is absent.
  - [ ] Existing negative min smoke logs are marked as engine-chain evidence, not strategy-success evidence.

  **QA Scenarios**:
  ```text
  Scenario: Inventory distinguishes evidence strength
    Tool: powershell
    Steps: Select lines in task-1-evidence-inventory.md containing "min_e2e_smoke", "m2_smoke", "wf_t2c3", and "THETA".
    Expected: Each line classifies the artifact and states what it does not prove.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-1-inventory-check.txt

  Scenario: Missing aggregate is handled honestly
    Tool: powershell
    Steps: Test-Path .omo/evidence/tmap-walkforward/wf_t2c3_20260613/aggregate.json
    Expected: False, and task-1 evidence marks the run as partial.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-1-partial-wf-check.txt
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/tick-min-condition-generation-review-20260613/task-1-evidence-inventory.md`

- [x] 2. Tick/Min Generation Pipeline Contract Audit

  **What to do**: Trace the current contract from `LoopConfig` to prompt construction, generator pre-save guards, `_generate_pair`, warm backtest config, templates, and presets. Produce `.omo/evidence/tick-min-condition-generation-review-20260613/task-2-pipeline-contract.md` with separate sections for tick LLM generation, tick TMAP generation, min LLM generation, and min TMAP generation.
  **Must NOT do**: Do not run LLM generation, do not call `tmap_sweep`, and do not write config JSON into `ai_strategy_loop/state`.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 4, 5, 6, 7, 8 | Blocked By: None

  **References**:
  - Pattern: `ai_strategy_loop/config.py:94` - `bt_timeframe` contract.
  - Pattern: `ai_strategy_loop/config.py:135` - `full_session_enabled` default OFF and min-only purpose.
  - Pattern: `ai_strategy_loop/config.py:458` - `time_cap_bucket_generation_enabled` and `time_cap_bucket_end_time`.
  - Pattern: `ai_strategy_loop/brain/prompt.py:456` - time-cap prompt injection point.
  - Pattern: `ai_strategy_loop/brain/prompt.py:486` - current `encourage_time_dispersion` wording still says 09:00~09:20.
  - Pattern: `ai_strategy_loop/brain/generator.py:392` - time-cap complexity guard.
  - Pattern: `ai_strategy_loop/controller/loop.py:374` - warm backtest config construction.
  - Pattern: `ai_strategy_loop/controller/loop.py:675` - `_generate_pair` passes generation toggles to `generate_strategy`.
  - Pattern: `ai_strategy_loop/scripts/research_presets.py:99` - tick late preset.
  - Pattern: `ai_strategy_loop/scripts/research_presets.py:130` - min full preset.

  **Acceptance Criteria**:
  - [ ] The report contains a four-row contract table: tick LLM, tick TMAP, min LLM, min TMAP.
  - [ ] Each row lists entry command, config fields, prompt/template path, validation guard, and backtest path.
  - [ ] The report explicitly states that min full-session data loading is wired, while min full-session LLM prompt guidance is not yet as direct as the tick time-cap guidance.
  - [ ] The report identifies that `encourage_time_dispersion` remains 09:00~09:20-oriented and should not be considered a full-session min guide.

  **QA Scenarios**:
  ```text
  Scenario: Pipeline table covers all four paths
    Tool: powershell
    Steps: Count occurrences of "tick LLM", "tick TMAP", "min LLM", "min TMAP" in task-2-pipeline-contract.md.
    Expected: Each phrase appears at least once in a table or section heading.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-2-path-coverage.txt

  Scenario: No execution was performed
    Tool: powershell
    Steps: git status --short
    Expected: No new ai_strategy_loop/state config files from this audit.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-2-no-state-write.txt
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/tick-min-condition-generation-review-20260613/task-2-pipeline-contract.md`

- [x] 3. Test Coverage and Test Meaning Audit

  **What to do**: Run the relevant read-only tests with bytecode/cache disabled and write `.omo/evidence/tick-min-condition-generation-review-20260613/task-3-test-coverage.md`. Explain what the tests prove and what they do not prove.
  **Must NOT do**: Do not add tests. Do not run full long backtests.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 4, 8 | Blocked By: None

  **References**:
  - Pattern: `tests/unit/test_time_cap_bucket_generation.py:109` - config default/off and end-time parsing.
  - Pattern: `tests/unit/test_time_cap_bucket_generation.py:168` - 09:20~09:30 bucket prompt injection.
  - Pattern: `tests/unit/test_time_cap_bucket_generation.py:247` - loop `_generate_pair` forwards time-cap config.
  - Pattern: `tests/unit/test_late_tick_and_min_templates.py:11` - tick/min template render and validation tests.
  - Pattern: `tests/unit/test_research_presets.py:13` - preset contract tests.
  - Pattern: `tests/unit/test_warm_session_window.py:1` - min full-session warm config tests.
  - Pattern: `tests/unit/test_variable_scope.py:1` - timeframe variable scope tests.

  **Acceptance Criteria**:
  - [ ] Test command output is saved to `task-3-pytest.txt`.
  - [ ] Coverage audit states that 68 targeted tests prove config/prompt/template/scope/window contracts.
  - [ ] Coverage audit states that these tests do not prove LLM quality, profitable candidate generation, OOS robustness, or dashboard verdict completion.
  - [ ] Coverage audit lists missing future tests without implementing them.

  **QA Scenarios**:
  ```text
  Scenario: Targeted tests pass
    Tool: powershell
    Steps: $env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/unit/test_warm_session_window.py tests/unit/test_variable_scope.py tests/unit/test_time_window.py tests/unit/test_time_cap_bucket_generation.py tests/unit/test_late_tick_and_min_templates.py tests/unit/test_research_presets.py -q -p no:cacheprovider
    Expected: 68 passed.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-3-pytest.txt

  Scenario: Audit does not overclaim
    Tool: powershell
    Steps: Search task-3-test-coverage.md for "does not prove".
    Expected: At least four explicit non-proof statements.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-3-nonproof-check.txt
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/tick-min-condition-generation-review-20260613/task-3-test-coverage.md`, `.omo/evidence/tick-min-condition-generation-review-20260613/task-3-pytest.txt`

- [x] 4. Completion Score Matrix

  **What to do**: Create `.omo/evidence/tick-min-condition-generation-review-20260613/completion-score-matrix.json` and a short markdown explanation. Score each area from 0 to 100 with evidence and missing proof. Use conservative scoring.
  **Must NOT do**: Do not score strategy profitability based only on unit tests.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 1, 2, 3

  **References**:
  - Pattern: `docs/AGENT_HANDOFF.md:59` - explicit limitation that toggle-on multiyear/OOS was not done at that point.
  - Pattern: `docs/update_log/2026-06-13_dawn_handoff.md:8` - THETA evidence and V6 remaining.
  - Pattern: `ai_strategy_loop/scripts/research_presets.py:99` - tick late preset readiness.
  - Pattern: `ai_strategy_loop/scripts/research_presets.py:130` - min full preset readiness.
  - Pattern: `.omo/evidence/tmap-walkforward/min_e2e_smoke_log.txt:1` - min chain smoke negative result.
  - Pattern: `.omo/evidence/tmap-walkforward/t2_corner_log.txt:1` - THETA/tick-side positive batch evidence.

  **Acceptance Criteria**:
  - [ ] Matrix contains at least these dimensions: config wiring, prompt generation, template generation, variable scope safety, warm backtest data window, targeted unit tests, real tick sweep evidence, real min sweep evidence, OOS/WF robustness, full-day time coverage.
  - [ ] Each score has `score`, `status`, `evidence`, `missing`, and `next_action`.
  - [ ] Overall completion is expressed as an evidence-weighted estimate, not a claim of production readiness.
  - [ ] The matrix includes provisional current estimates: infrastructure high, profitable generation low-to-mid, full-day min condition generation not complete.

  **QA Scenarios**:
  ```text
  Scenario: JSON parses
    Tool: powershell
    Steps: python -c "import json, pathlib; json.loads(pathlib.Path('.omo/evidence/tick-min-condition-generation-review-20260613/completion-score-matrix.json').read_text(encoding='utf-8')); print('ok')"
    Expected: ok
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-4-json-parse.txt

  Scenario: Scores are conservative
    Tool: powershell
    Steps: Search matrix for "OOS/WF robustness" and "full-day time coverage".
    Expected: Neither dimension is scored as complete unless backed by completed aggregate evidence.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-4-score-honesty.txt
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/tick-min-condition-generation-review-20260613/completion-score-matrix.json`

- [x] 5. Tick 09:20~09:25 Readiness Review

  **What to do**: Produce `.omo/evidence/tick-min-condition-generation-review-20260613/task-5-tick-late-readiness.md`. Assess whether tick late generation can create candidates, what has been validated, what remains for 09:20~09:25, and how T1/T2/T3/T4 from the roadmap should be ordered.
  **Must NOT do**: Do not execute TMAP sweeps. Do not freeze or promote a candidate.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 2

  **References**:
  - Pattern: `ai_strategy_loop/tmap/templates/tick_late_0920_0925_continuation.json:5` - late-tick template intent.
  - Pattern: `ai_strategy_loop/tmap/templates/tick_late_0920_0925_continuation.json:9` - default 09:20 entry start.
  - Pattern: `ai_strategy_loop/tmap/templates/tick_late_0920_0925_continuation.json:10` - default 09:25 entry end.
  - Pattern: `ai_strategy_loop/brain/time_cap_bucket.py:83` - prompt says 09:20~09:25 should be single branch in extended mode.
  - Pattern: `docs/research/condition_research/2026-06-13_entry_extension_and_min_roadmap.md:9` - evidence that naive extension after 09:07 degrades.
  - Pattern: `.omo/evidence/tmap-walkforward/wf_t2c3_20260613/w0_manifest.json:1` - partial T2C3 w0 fit.

  **Acceptance Criteria**:
  - [ ] Tick review states readiness separately for LLM generation and TMAP template generation.
  - [ ] It explicitly says 09:20~09:25 candidate creation is syntactically/contractually ready but profitable discovery is not proven.
  - [ ] It lists the next evidence needed: 2-quarter smoke, full train sweep, 2022/2026 OOS, 4-window WF aggregate.
  - [ ] It flags `wf_t2c3_20260613` as partial until more windows/aggregate exist.

  **QA Scenarios**:
  ```text
  Scenario: Tick review does not confuse THETA with late-tick discovery
    Tool: powershell
    Steps: Search task-5-tick-late-readiness.md for "THETA" and "09:20~09:25".
    Expected: THETA is described as current champion/baseline, not proof that late-tick new discovery is complete.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-5-theta-separation.txt

  Scenario: Required future evidence is listed
    Tool: powershell
    Steps: Search task-5-tick-late-readiness.md for "OOS", "WF", and "2-quarter".
    Expected: All three appear in the next-evidence section.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-5-evidence-requirements.txt
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/tick-min-condition-generation-review-20260613/task-5-tick-late-readiness.md`

- [x] 6. Min 09:00~15:00 Full-Session Readiness Review

  **What to do**: Produce `.omo/evidence/tick-min-condition-generation-review-20260613/task-6-min-fullsession-readiness.md`. Assess data-window wiring, min variable safety, template readiness, LLM guidance gap, primitive-map gap, OOS limitations, and time-band coverage.
  **Must NOT do**: Do not run min sweeps or write min configs into state.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 2

  **References**:
  - Pattern: `ai_strategy_loop/controller/loop.py:380` - min full session end-time branch.
  - Pattern: `tests/unit/test_warm_session_window.py:25` - min full session opens end time.
  - Pattern: `ai_strategy_loop/tmap/templates/min_session_0900_1500_rotation.json:5` - min full-session template intent.
  - Pattern: `ai_strategy_loop/tmap/templates/min_session_0900_1500_rotation.json:9` - time-band entry starts.
  - Pattern: `ai_strategy_loop/tmap/templates/min_session_0900_1500_rotation.json:10` - entry ends capped at 15:00.
  - Pattern: `ai_strategy_loop/tmap/templates/min_session_0900_1500_rotation.json:36` - forced exit at 15:00.
  - Pattern: `docs/research/condition_research/2026-06-12_min_timeframe_validation_protocol.md:1` - min protocol and OOS limitation.
  - Pattern: `docs/research/condition_research/2026-06-13_entry_extension_and_min_roadmap.md:30` - M1 primitive map is the recommended missing step.
  - Pattern: `.omo/evidence/tmap-walkforward/min_e2e_smoke_log.txt:1` - engine chain works but result is negative.

  **Acceptance Criteria**:
  - [ ] Min review states that full-session backtest data access is mostly wired and tested.
  - [ ] Min review states that “full-day condition generation” is not complete until M1 primitive maps and time-band-specific generation feedback exist.
  - [ ] It distinguishes `09:00~15:00 template exists` from `profitable 09:00~15:00 condition discovered`.
  - [ ] It explains why min OOS is structurally limited to 2026-01~02 with only 11 months of data.

  **QA Scenarios**:
  ```text
  Scenario: Min review has all time bands
    Tool: powershell
    Steps: Search task-6-min-fullsession-readiness.md for "09:00~10:00", "10:00~11:30", "11:30~13:00", "13:00~14:50", "14:50~15:00".
    Expected: All bands are represented.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-6-timeband-check.txt

  Scenario: Min review preserves data limitation
    Tool: powershell
    Steps: Search task-6-min-fullsession-readiness.md for "11개월" and "2026-01~02".
    Expected: Both appear in the OOS limitation section.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-6-oos-limitation-check.txt
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/tick-min-condition-generation-review-20260613/task-6-min-fullsession-readiness.md`

- [x] 7. CLI and Runbook Consistency Review

  **What to do**: Produce `.omo/evidence/tick-min-condition-generation-review-20260613/task-7-cli-runbook-review.md`. Compare documented commands with actual CLI help and code. Identify exact command corrections for future development, but do not modify docs.
  **Must NOT do**: Do not update `docs/update_log/2026-06-13_late_tick_min_discovery_roadmap.md` yet.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 8 | Blocked By: 1, 2

  **References**:
  - Pattern: `docs/update_log/2026-06-13_late_tick_min_discovery_roadmap.md:66` - documented tick command uses `--out-prefix`.
  - Pattern: `docs/update_log/2026-06-13_late_tick_min_discovery_roadmap.md:82` - documented min command uses `--out-prefix`.
  - Pattern: `ai_strategy_loop/scripts/tmap_sweep.py:49` - actual `--template` argument.
  - Pattern: `ai_strategy_loop/scripts/tmap_sweep.py:51` - actual required `--run-id` argument.
  - Pattern: `ai_strategy_loop/scripts/tmap_sweep.py:54` - actual `--manifest-out` argument.
  - Pattern: `ai_strategy_loop/scripts/research_presets.py:164` - preset CLI.

  **Acceptance Criteria**:
  - [ ] Review includes the exact mismatch: `--out-prefix` is not accepted by current `tmap_sweep`.
  - [ ] Review proposes corrected future commands for tick and min with `--run-id` and `--manifest-out`.
  - [ ] Review states whether corrected commands should use generated config files or existing `.omo/evidence` configs.
  - [ ] Review avoids editing the roadmap in this phase.

  **QA Scenarios**:
  ```text
  Scenario: CLI mismatch is reproduced by help output
    Tool: powershell
    Steps: $env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'; python -m ai_strategy_loop.scripts.tmap_sweep --help
    Expected: Help includes --run-id and --manifest-out, does not include --out-prefix.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-7-tmap-help.txt

  Scenario: Runbook review gives corrected commands
    Tool: powershell
    Steps: Search task-7-cli-runbook-review.md for "--run-id", "--manifest-out", and "--out-prefix".
    Expected: The first two are in corrected command examples; the last is in the mismatch section only.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-7-command-check.txt
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/tick-min-condition-generation-review-20260613/task-7-cli-runbook-review.md`

- [x] 8. Final Review Report and Development Backlog

  **What to do**: Assemble `.omo/evidence/tick-min-condition-generation-review-20260613/review-report.md`, `.omo/evidence/tick-min-condition-generation-review-20260613/gap-backlog.md`, and `.omo/evidence/tick-min-condition-generation-review-20260613/verification.txt`. The report must include a current-state verdict, completion score table, evidence map, missing pieces, and exact next development sequence.
  **Must NOT do**: Do not implement backlog items. Do not promote or freeze strategies.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: Final Verification | Blocked By: 4, 5, 6, 7

  **References**:
  - Pattern: all Task 1-7 outputs.
  - Pattern: `docs/research/condition_research/2026-06-13_entry_extension_and_min_roadmap.md:18` - T-track order.
  - Pattern: `docs/research/condition_research/2026-06-13_entry_extension_and_min_roadmap.md:30` - M-track primitive map order.
  - Pattern: `docs/research/condition_research/2026-06-12_min_timeframe_validation_protocol.md:3` - min train/OOS protocol.
  - Pattern: `docs/update_log/2026-06-13_dawn_handoff.md:34` - next-stage priorities.

  **Acceptance Criteria**:
  - [ ] Report includes a clear answer to “조건식 생성 기능이 잘 작동하여 생성을 하는가?” with four statuses: config/prompt works, template generation works, actual profitable generation not proven, OOS robustness pending.
  - [ ] Report includes current completion estimate by area and one overall estimate.
  - [ ] Backlog ranks at least 8 future development tasks with `priority`, `why`, `files likely touched`, `tests to add/run`, and `acceptance`.
  - [ ] Backlog starts with review-safe prerequisites before implementation: command contract fix, evidence baseline, M1 primitive map, tick late smoke, then LLM context injection.
  - [ ] Report explicitly says no source updates were performed.
  - [ ] `verification.txt` records the final targeted pytest result, source no-update check, and High Accuracy Review adjustments.

  **QA Scenarios**:
  ```text
  Scenario: Final report answers the user's question directly
    Tool: powershell
    Steps: Search review-report.md for "현재 판정", "달성률", "부족한 것", "전체 시간".
    Expected: All four headings exist.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-8-report-heading-check.txt

  Scenario: Backlog is executable
    Tool: powershell
    Steps: Search gap-backlog.md for "priority", "files likely touched", "tests to add/run", and "acceptance".
    Expected: Each backlog item includes these fields.
    Evidence: .omo/evidence/tick-min-condition-generation-review-20260613/task-8-backlog-structure-check.txt
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/tick-min-condition-generation-review-20260613/review-report.md`, `.omo/evidence/tick-min-condition-generation-review-20260613/gap-backlog.md`, `.omo/evidence/tick-min-condition-generation-review-20260613/verification.txt`

## Final Verification Wave (MANDATORY - after ALL implementation tasks)
> ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
- [x] F1. Plan Compliance Audit
  - Verify every task produced its stated evidence file.
  - Verify all acceptance criteria are checked in the task evidence.
  - Command: `Test-Path .omo/evidence/tick-min-condition-generation-review-20260613/review-report.md; Test-Path .omo/evidence/tick-min-condition-generation-review-20260613/completion-score-matrix.json; Test-Path .omo/evidence/tick-min-condition-generation-review-20260613/gap-backlog.md; Test-Path .omo/evidence/tick-min-condition-generation-review-20260613/verification.txt`
  - Evidence: `.omo/evidence/tick-min-condition-generation-review-20260613/f1-plan-compliance.txt`
- [x] F2. Source No-Update Review
  - Verify no source/test/docs files were changed by execution of this review plan.
  - Command: `git status --short`
  - Expected: Only pre-existing user changes plus `.omo/evidence/tick-min-condition-generation-review-20260613/**`; no new source/test/docs changes from the review.
  - Evidence: `.omo/evidence/tick-min-condition-generation-review-20260613/f2-source-no-update.txt`
- [x] F3. Real Command QA
  - Re-run the targeted 68-test command with bytecode/cache disabled.
  - Command: `$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/unit/test_warm_session_window.py tests/unit/test_variable_scope.py tests/unit/test_time_window.py tests/unit/test_time_cap_bucket_generation.py tests/unit/test_late_tick_and_min_templates.py tests/unit/test_research_presets.py -q -p no:cacheprovider`
  - Expected: 68 passed.
  - Evidence: `.omo/evidence/tick-min-condition-generation-review-20260613/f3-targeted-tests.txt`
- [x] F4. Scope Fidelity Check
  - Verify report does not claim source updates, live deployment, V3K gate progress, or profitable min/tick discovery without evidence.
  - Command: Search report for forbidden overclaim phrases: `V3K complete`, `실배포 완료`, `min 수익 후보 확정`, `09:20~09:25 수익 후보 확정`.
  - Expected: No such completion claims unless framed as “not proven/pending”.
  - Evidence: `.omo/evidence/tick-min-condition-generation-review-20260613/f4-scope-fidelity.txt`

## Commit Strategy
No commit. Review-only plan. If a later worker executes this plan, only `.omo/evidence/tick-min-condition-generation-review-20260613/**` artifacts may be produced unless the user explicitly authorizes source updates.

## Success Criteria
- 현재 기능 상태를 “작동함/부분 작동/미검증/부족”으로 구분해 설명한다.
- 달성률은 과장 없이 영역별 점수와 증거로 제시한다.
- 전체 시간을 모두 고려한 조건식 생성을 위해 부족한 개발 항목이 우선순위화된다.
- 후속 구현자가 다음 단계에서 무엇을 만들고 어떤 테스트로 잠글지 판단할 필요가 없다.
