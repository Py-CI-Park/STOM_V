# 조건식 자기개선 프로세스 상세 검토 보고서 작성 계획

## TL;DR
> **Summary**: 현재 STOM AI 조건식 루프가 "나쁜 조건식 -> 좋은 조건식"으로 스스로 개선되기 위해 무엇이 이미 있고 무엇이 부족한지, 수치 점수와 개선 로드맵으로 정리하는 보고서를 작성한다. 구현은 하지 않고, 현재 코드/연구/테스트 근거를 문서와 evidence로만 남긴다.
> **Deliverables**:
> - `docs/update_log/2026-06-15_condition_self_improvement_process_report.md`
> - `.omo/evidence/condition-self-improvement-process-report-20260615/source_inventory.md`
> - `.omo/evidence/condition-self-improvement-process-report-20260615/process_map.md`
> - `.omo/evidence/condition-self-improvement-process-report-20260615/gap_score_matrix.json`
> - `.omo/evidence/condition-self-improvement-process-report-20260615/improvement_backlog.md`
> - `.omo/evidence/condition-self-improvement-process-report-20260615/verification.md`
> **Effort**: Medium
> **Parallel**: YES - 3 waves
> **Critical Path**: Task 1 -> Task 2 -> Tasks 3-7 -> Task 8 -> Final Verification

## Context
### Original Request
- 사용자는 DB, 백테스트 검증 시스템, 매수/매도 규칙을 기반으로 데이터 퀀트 방식으로 좋은 조건식을 찾는 전체 목적을 확인했다.
- 이번 요청은 `$ulw-plan`: "더 상세하게 어떻게 개선하고 업데이트하면 좋을지도 연구해서 보고서로 작성".
- 따라서 이 계획은 구현이 아니라, 현 코드/연구/테스트를 다시 검토해 보고서와 향후 개발 준비물을 작성하는 실행 계획이다.

### Interview Summary
- 별도 질문은 필요하지 않다. 사용자의 성공 기준은 명확하다: 현재 tick/min 조건식 생성 및 검증 루프가 나쁜 조건식에서 좋은 조건식으로 스스로 개선될 수 있는지, 부족분을 수치화하고, 개선 방법까지 제시해야 한다.
- 테스트 전략은 tests-after로 둔다. 이번 작업은 문서/evidence 작성이지만, 보고서가 인용하는 현재 테스트가 실제 존재하고 실행 가능한지 확인한다.

### Metis Review (gaps addressed)
- Codex 현재 도구 목록에는 `spawn_agent(agent_type="metis")`가 없어 별도 Metis subagent는 호출하지 못했다. 대신 같은 체크리스트로 직접 gap review를 수행해 아래 가드를 계획에 반영한다.
- **Gap 1: self-score 과신 위험**. 점수는 진단 보조로만 쓰고, 성공 판정은 `.omo/evidence/tmap-walkforward/p1_ab_preregistration.md:14`의 OOS PROMISING count 기준으로 제한한다.
- **Gap 2: in-sample feedback 누수 위험**. `ai_strategy_loop/autopsy/analyze.py:136`의 train-only guard와 기존 연구 문서의 P0 gate 우선 원칙을 보고서에 명시한다.
- **Gap 3: 구현 범위 침범 위험**. 이번 계획은 source code, DB, backtest runtime을 수정하지 않는다. 보고서가 제안하는 개선은 backlog/acceptance criteria로만 남긴다.
- **Gap 4: seed가 중요하다는 사용자 가설**. seed breadth를 별도 평가축과 개선 backlog로 분리한다. `ai_strategy_loop/config.py:444`의 classification/time-cap generation toggles와 기존 A/B 결과를 근거로 삼는다.

## Work Objectives
### Core Objective
- 현재 AI 조건식 발굴 루프를 "생성 -> 백테스트 -> 원인분석 -> feedback -> mutation/seed coverage -> 재검증 -> OOS/WF 승격"의 폐루프로 재정의하고, 현재 완성도와 부족분을 수치화한 보고서를 작성한다.

### Deliverables
- 최종 보고서: `docs/update_log/2026-06-15_condition_self_improvement_process_report.md`
- 근거 인벤토리: 코드/문서/테스트/결과 파일별 확인 내용과 line reference.
- 프로세스 맵: DB/seed/generator/backtest/autopsy/feedback/gate/dashboard 흐름.
- 점수 매트릭스: 현재 완성도 %, 부족 %, 근거, 개선 방법, 우선순위.
- 개발 backlog: P0-P5 순서, 각 단계 acceptance criteria, 금지사항, 검증 명령.

### Definition of Done
- [ ] 보고서에 목적, 현재 구조, 테스트 결과, 완성도 %, 부족분 %, 개선 방법이 모두 포함된다.
- [ ] 보고서가 최소 12개 이상의 실제 파일/라인 근거를 인용한다.
- [ ] `gap_score_matrix.json`이 JSON parse 가능하고 모든 평가축에 `score_pct`, `gap_pct`, `evidence`, `improvement`가 있다.
- [ ] 보고서가 buy-side와 sell-side 개선을 분리해서 설명한다.
- [ ] 보고서가 seed breadth 개선을 별도 장으로 다룬다.
- [ ] 보고서가 OOS/WF를 유일한 성공 판정 기준으로 명시한다.
- [ ] source code, runtime DB, protected path는 수정하지 않는다.

### Must Have
- 한국어 보고서.
- 테이블 중심 구성.
- 현재 수치 근거 포함: n=8 A/B smoke-pass 0.375 vs 0.0, OOS 0; 40회 다밴드 PROMISING 0; P0b known-good +2.17M PASS / 새 후보 -3M REFUSE; 현재 기준점은 OOS 통과 후보 0.
- "seed가 가장 중요한가?"에 답해야 한다: 중요하지만 단독으로 충분하지 않고, seed coverage + feedback policy + OOS gate + mutation/action ledger가 같이 있어야 한다고 정리한다.

### Must NOT Have
- No source implementation.
- No edits under `ai_strategy_loop/`, `backtest/`, `cli/`, `tests/`, `utility/ai_agent/`.
- No writes to `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`, `_v3k_sidecar/`.
- No V3K gate state changes, USER_ACK, live broker/KHOPENAPI, live order/exit wiring.
- No long LLM generation/backtest run. Only read existing results and optionally run focused unit tests.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after, focused only on tests cited by the report.
- QA policy: Every task writes evidence under `.omo/evidence/condition-self-improvement-process-report-20260615/`.
- Evidence: markdown/JSON files only; no runtime DB writes.

## Execution Strategy
### Parallel Execution Waves
- Wave 1: Task 1 and Task 2 establish source inventory and process map.
- Wave 2: Tasks 3, 4, 5, 6, 7 can run in parallel after Wave 1.
- Wave 3: Task 8 assembles the final report and Task 9 verifies consistency.

### Dependency Matrix
| Task | Blocks | Blocked By |
|---|---|---|
| 1. Source inventory | 2, 3, 4, 5, 6, 7, 8 | None |
| 2. Process map | 3, 4, 5, 6, 7, 8 | 1 |
| 3. Scoring matrix | 8 | 1, 2 |
| 4. Seed coverage review | 8 | 1, 2 |
| 5. Buy/sell diagnosis review | 8 | 1, 2 |
| 6. Feedback/gate/DB review | 8 | 1, 2 |
| 7. Improvement backlog | 8 | 1, 2 |
| 8. Final report | 9 | 3, 4, 5, 6, 7 |
| 9. Verification | Final Verification | 8 |

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: References + Acceptance Criteria + QA Scenarios.

- [x] 1. 근거 인벤토리 작성

  **What to do**: 현재 조건식 생성/검증/feedback/대시보드/연구 문서를 읽고, 보고서에서 인용할 근거를 `source_inventory.md`에 정리한다. 각 항목은 `file:line`, 확인 내용, 보고서에서 쓰일 의미를 포함한다.

  **Must NOT do**: 파일 내용을 추측하지 않는다. 깨진 인코딩 출력은 최종 인용문으로 쓰지 말고 의미만 요약한다.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 2-8 | Blocked By: None

  **References**:
  - Pattern: `ai_strategy_loop/scripts/tmap_multiband_discovery.py:87` - stateful ledger feedback builder.
  - Pattern: `ai_strategy_loop/scripts/tmap_multiband_discovery.py:212` - smoke q1/q2, full train, OOS escalation.
  - Pattern: `ai_strategy_loop/scripts/gen_template_hypothesis.py:73` - feedback text prompt injection.
  - Pattern: `ai_strategy_loop/brain/segment_feedback.py:84` - losing segment avoid line generation.
  - Pattern: `ai_strategy_loop/autopsy/analyze.py:25` - B_* entry diagnosis columns.
  - Pattern: `ai_strategy_loop/autopsy/analyze.py:295` - exit autopsy using MFE/MAE/hold/sell rules.
  - Pattern: `backtest/backengine_base.py:546` - buy/sell/result snapshots including MFE/MAE.
  - Pattern: `ai_strategy_loop/config.py:340` - exit-edge feedback toggle.
  - Pattern: `ai_strategy_loop/config.py:355` - segment feedback toggle.
  - Pattern: `ai_strategy_loop/config.py:444` - classification/time-cap generation toggles.
  - Pattern: `ai_strategy_loop/config.py:500` - quantile/counterfactual feedback toggles.
  - Pattern: `ai_strategy_loop/dashboard/analysis_snapshot.py:244` - dashboard analysis reports.
  - Evidence: `.omo/evidence/tmap-walkforward/ab_result_n8.json` - pilot A/B metrics.
  - Evidence: `.omo/evidence/tmap-walkforward/p1_ab_preregistration.md:14` - OOS success criterion.
  - Evidence: `docs/update_log/2026-06-15_multiband_overnight_results.md:8` - 40 iteration result.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/condition-self-improvement-process-report-20260615/source_inventory.md` exists.
  - [ ] Inventory has at least 12 rows with `Source`, `Finding`, `Meaning`, `Report Section`.
  - [ ] Every cited source path exists.

  **QA Scenarios**:
  ```text
  Scenario: inventory paths resolve
    Tool: powershell
    Steps: For every backticked path in source_inventory.md, run Test-Path.
    Expected: All local paths return True.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md

  Scenario: missing source guard
    Tool: powershell
    Steps: Search source_inventory.md for "TODO", "TBD", "unknown".
    Expected: No placeholder remains.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/condition-self-improvement-process-report-20260615/source_inventory.md`

- [x] 2. 전체 프로세스 맵 작성

  **What to do**: 현재/목표 흐름을 한 문서에 그린다. 필수 노드: DB/history, seed/template, generator prompt, syntax/schema gate, backtest q1/q2/full/OOS, trade CSV, entry autopsy, exit autopsy, segment feedback, quantile/counterfactual feedback, refine gate, dashboard/report, promotion/archive. 각 노드에 "현재 있음/부분 있음/없음"을 표시한다.

  **Must NOT do**: Mermaid나 이미지 생성은 필수로 하지 않는다. 텍스트 표로 충분하다.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 3-8 | Blocked By: 1

  **References**:
  - Pattern: `ai_strategy_loop/scripts/tmap_multiband_discovery.py:301` - `--stateful` flag.
  - Pattern: `ai_strategy_loop/scripts/tmap_multiband_discovery.py:323` - track rotation and per-iteration feedback.
  - Pattern: `ai_strategy_loop/dashboard/analysis_snapshot.py:207` - generation context and CSV paths.
  - Pattern: `ai_strategy_loop/dashboard/analysis_snapshot.py:262` - analysis snapshot endpoint.
  - Evidence: `docs/update_log/2026-06-15_session_handoff_pipeline_execution.md:13` - P0/P1/P2/P3-P5 status.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/condition-self-improvement-process-report-20260615/process_map.md` exists.
  - [ ] It contains two tables: `Current Flow` and `Target Self-Improvement Flow`.
  - [ ] It identifies at least 5 partial/missing bridges.

  **QA Scenarios**:
  ```text
  Scenario: process map completeness
    Tool: powershell
    Steps: Select-String process_map.md for "DB", "seed", "generator", "backtest", "autopsy", "feedback", "OOS", "dashboard".
    Expected: All terms are present.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md

  Scenario: no implementation drift
    Tool: git
    Steps: git status --short -- ai_strategy_loop backtest cli tests
    Expected: No new changes caused by this report task beyond pre-existing dirty state.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/condition-self-improvement-process-report-20260615/process_map.md`

- [x] 3. 완성도/부족분 점수 매트릭스 작성

  **What to do**: 10개 평가축으로 현재 완성도와 부족분을 수치화한다. 권장 평가축: 목적 정렬, 데이터 캡처, 백테스트 게이트, seed breadth, generation diversity, buy-side diagnosis, sell-side diagnosis, feedback policy, DB lineage/evidence, dashboard/runbook, OOS proof, end-to-end autonomy. 각 축은 0-100%, gap=100-score, 근거, 개선 방법, 우선순위를 포함한다.

  **Must NOT do**: 점수를 성공 판정으로 쓰지 않는다. OOS/WF 통과 후보 수와 score를 혼동하지 않는다.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 1, 2

  **References**:
  - Evidence: `.omo/evidence/tmap-walkforward/ab_result_n8.json` - proxy rate improvement but OOS 0.
  - Evidence: `docs/update_log/2026-06-15_multiband_overnight_results.md:4` - PROMISING 0.
  - Evidence: `docs/update_log/2026-06-15_condition_discovery_process_research_report.md:310` - OOS-first roadmap and prior score target.
  - Pattern: `ai_strategy_loop/config.py:514` - prompt logging default-OFF, lineage gap.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/condition-self-improvement-process-report-20260615/gap_score_matrix.json` exists.
  - [ ] JSON parses with `python -m json.tool`.
  - [ ] Every row has `axis`, `score_pct`, `gap_pct`, `evidence`, `improvement`, `priority`.
  - [ ] Average score and average gap are included.

  **QA Scenarios**:
  ```text
  Scenario: JSON matrix parses
    Tool: powershell
    Steps: python -m json.tool .omo/evidence/condition-self-improvement-process-report-20260615/gap_score_matrix.json > $null
    Expected: Exit code 0.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md

  Scenario: score math is valid
    Tool: powershell
    Steps: Parse JSON and verify every gap_pct equals 100 - score_pct.
    Expected: All rows pass.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/condition-self-improvement-process-report-20260615/gap_score_matrix.json`

- [x] 4. Seed breadth 개선안 작성

  **What to do**: 사용자의 "시드가 가장 중요한가" 질문에 직접 답하는 장을 만든다. 현재 seed/branch가 좁을 때 생기는 문제, 이미 있는 broad-generation 토글, 필요한 coverage ledger, tick/min 분리, anchor/explore 비율, 시총/등락률/시간대 grid를 구체화한다.

  **Must NOT do**: 새 seed JSON/template을 생성하지 않는다.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 1, 2

  **References**:
  - Pattern: `ai_strategy_loop/config.py:444` - classification_generation_enabled rationale.
  - Pattern: `ai_strategy_loop/config.py:456` - time_cap_bucket_generation_enabled and bucket end time.
  - Evidence: `docs/update_log/2026-06-15_multiband_overnight_results.md:45` - multiband idea is structurally valid but new alpha scarce.
  - Evidence: `.omo/evidence/tmap-walkforward/p1_ab_preregistration.md:6` - random vs stateful arms.

  **Acceptance Criteria**:
  - [ ] `improvement_backlog.md` contains a `Seed Coverage` section.
  - [ ] It defines at least 6 seed coverage dimensions: timeframe, time bucket, market-cap bucket, change bucket, entry family, exit family.
  - [ ] It proposes a deterministic exploration allocation, e.g. anchor 30%, broad grid 50%, mutation 20%, or explains a different fixed allocation.

  **QA Scenarios**:
  ```text
  Scenario: seed coverage section exists
    Tool: powershell
    Steps: Select-String improvement_backlog.md for "Seed Coverage", "time bucket", "market-cap", "anchor", "mutation".
    Expected: All terms are present.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md

  Scenario: no generated strategy side effect
    Tool: git
    Steps: git status --short -- utility/ai_agent ai_strategy_loop/tmap/templates
    Expected: No new template/strategy files caused by this report task.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/condition-self-improvement-process-report-20260615/improvement_backlog.md`

- [x] 5. Buy-side / Sell-side 진단 개선안 작성

  **What to do**: 매수 조건식과 매도 조건식을 별도 학습 대상으로 분리한다. 매수는 B_* snapshot, time/cap/change segment, feature importance, quantile/counterfactual filters로 진단한다. 매도는 MFE/MAE, giveback, hold time, sell-rule distribution, exit regret로 진단한다. 각 진단 결과가 다음 조건식에 어떤 feedback action으로 바뀌어야 하는지 표로 정리한다.

  **Must NOT do**: buy와 sell 개선을 하나의 "수익률이 낮다" 문제로 뭉뚱그리지 않는다.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 1, 2

  **References**:
  - Pattern: `ai_strategy_loop/autopsy/analyze.py:25` - B_* variables for entry diagnosis.
  - Pattern: `ai_strategy_loop/autopsy/analyze.py:56` - MFE/MAE/hold/sell-rule columns for exit diagnosis.
  - Pattern: `ai_strategy_loop/autopsy/analyze.py:371` - exit metrics calculations.
  - Pattern: `backtest/backengine_base.py:557` - `R_매수후최고수익률`, `R_MFE`, `R_MAE`.
  - Pattern: `ai_strategy_loop/config.py:340` - exit-edge feedback prompt policy.

  **Acceptance Criteria**:
  - [ ] `improvement_backlog.md` contains `Buy-Side Diagnosis` and `Sell-Side Diagnosis` sections.
  - [ ] Each section has at least 5 failure classes and a corresponding improvement action.
  - [ ] The sell-side section includes exit regret/giveback as a first-class item.

  **QA Scenarios**:
  ```text
  Scenario: buy/sell split is explicit
    Tool: powershell
    Steps: Select-String improvement_backlog.md for "Buy-Side Diagnosis", "Sell-Side Diagnosis", "MFE", "MAE", "B_*".
    Expected: All terms are present.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md

  Scenario: failure class table complete
    Tool: powershell
    Steps: Count rows under buy/sell failure class tables.
    Expected: At least 5 rows per side.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/condition-self-improvement-process-report-20260615/improvement_backlog.md`

- [x] 6. Feedback, gate, DB/evidence lineage 개선안 작성

  **What to do**: 현재 prompt-context feedback을 typed feedback action ledger로 업그레이드하는 방안을 작성한다. 필수 action: reject, avoid_segment, tighten_threshold, relax_threshold, mutate_seed, revise_exit, preserve_anchor, promote_candidate. 각 action은 근거 metric, 적용 범위, leakage guard, 재검증 gate를 가져야 한다. DB/evidence 측면에서는 source DB를 직접 수정하지 않고 loop/event lineage schema 초안을 제안한다.

  **Must NOT do**: 실제 DB migration이나 SQLite write를 수행하지 않는다.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 1, 2

  **References**:
  - Pattern: `ai_strategy_loop/scripts/tmap_multiband_discovery.py:98` - current avoid/prefer categories.
  - Pattern: `ai_strategy_loop/scripts/gen_template_hypothesis.py:449` - feedback file loading.
  - Pattern: `ai_strategy_loop/dashboard/analysis_snapshot.py:145` - analysis snapshot tables.
  - Pattern: `ai_strategy_loop/dashboard/analysis_snapshot.py:207` - generation metrics from LoopState.
  - Pattern: `ai_strategy_loop/config.py:514` - prompt logging toggle and lineage rationale.
  - Evidence: `.omo/evidence/tmap-walkforward/p1_ab_preregistration.md:28` - C3 stop rule.

  **Acceptance Criteria**:
  - [ ] `improvement_backlog.md` contains `Typed Feedback Ledger` and `Gate Policy` sections.
  - [ ] It includes a schema table for feedback action records without changing any DB.
  - [ ] It states that OOS/WF promotion is the only success signal and all in-sample feedback is advisory until revalidated.

  **QA Scenarios**:
  ```text
  Scenario: typed action coverage
    Tool: powershell
    Steps: Select-String improvement_backlog.md for "reject", "avoid_segment", "tighten_threshold", "revise_exit", "promote_candidate".
    Expected: All action names are present.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md

  Scenario: protected DB untouched
    Tool: git
    Steps: git status --short -- _database _database_v3k_shadow ai_strategy_loop/state *.db
    Expected: No new DB/protected path modification caused by this report task.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/condition-self-improvement-process-report-20260615/improvement_backlog.md`

- [x] 7. 단계별 업데이트 로드맵 작성

  **What to do**: 개발자가 바로 실행할 수 있는 P0-P5 backlog를 작성한다. 각 단계는 "왜 먼저인지", "수정 대상", "성공 조건", "중단 조건", "예상 개선되는 점수축"을 포함한다. 권장 순서: P0 metric/gate freeze, P1 lineage/report reliability, P2 seed coverage ledger, P3 buy/sell typed feedback, P4 mutation/grid/coarse-to-fine, P5 dashboard/runbook/automation.

  **Must NOT do**: 사용자의 승인 없이 live trading, V3K, source implementation까지 넘어가지 않는다.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 1, 2

  **References**:
  - Evidence: `docs/update_log/2026-06-15_session_handoff_pipeline_execution.md:16` - P0b real backtest gate result.
  - Evidence: `docs/update_log/2026-06-15_session_handoff_pipeline_execution.md:24` - pilot A/B outcome.
  - Evidence: `docs/update_log/2026-06-15_condition_discovery_process_research_report.md:312` - prior P0-P5 roadmap.
  - Evidence: `docs/update_log/2026-06-15_multiband_overnight_results.md:59` - next-stage recommendations.

  **Acceptance Criteria**:
  - [ ] `improvement_backlog.md` contains a `P0-P5 Update Roadmap` table.
  - [ ] Every phase has `Objective`, `Files/Areas`, `Acceptance`, `Stop Condition`, `Score Impact`.
  - [ ] P0 and P1 must be validation/reporting gates, not new generation features.

  **QA Scenarios**:
  ```text
  Scenario: roadmap phases complete
    Tool: powershell
    Steps: Select-String improvement_backlog.md for "P0", "P1", "P2", "P3", "P4", "P5".
    Expected: All phases are present.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md

  Scenario: no premature feature-first roadmap
    Tool: powershell
    Steps: Inspect P0/P1 rows.
    Expected: P0/P1 are gate/lineage/report reliability; feature expansion begins after validation guardrails.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/condition-self-improvement-process-report-20260615/improvement_backlog.md`

- [x] 8. 최종 보고서 작성

  **What to do**: `docs/update_log/2026-06-15_condition_self_improvement_process_report.md`를 작성한다. 구조는 다음 순서로 고정한다: 1) 한 줄 결론, 2) 목적/프로세스 이해, 3) 현재 개발/연구/테스트 근거, 4) 전체 점수표, 5) 부족분 Top 10과 개선 방법, 6) seed breadth 평가, 7) buy/sell 진단 폐루프, 8) DB/evidence/gate 업데이트, 9) P0-P5 로드맵, 10) 다음 start-work 권장 범위.

  **Must NOT do**: 보고서를 "좋아 보인다" 식의 정성 평가로 끝내지 않는다. 모든 핵심 판단은 수치/근거/파일 reference와 연결한다.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: 9 | Blocked By: 3, 4, 5, 6, 7

  **References**:
  - Evidence: `.omo/evidence/condition-self-improvement-process-report-20260615/source_inventory.md`
  - Evidence: `.omo/evidence/condition-self-improvement-process-report-20260615/process_map.md`
  - Evidence: `.omo/evidence/condition-self-improvement-process-report-20260615/gap_score_matrix.json`
  - Evidence: `.omo/evidence/condition-self-improvement-process-report-20260615/improvement_backlog.md`
  - Style: `docs/update_log/2026-06-15_condition_discovery_process_research_report.md` - table-heavy Korean research report style.
  - Style: `docs/AGENTS.md` - update log rules.

  **Acceptance Criteria**:
  - [ ] Final report exists at `docs/update_log/2026-06-15_condition_self_improvement_process_report.md`.
  - [ ] It has at least 8 tables.
  - [ ] It includes an overall score and gap percentage.
  - [ ] It includes explicit "지금 부족한 것" and "어떻게 업데이트하면 좋은가" sections.
  - [ ] It names the recommended next `$start-work` scope.

  **QA Scenarios**:
  ```text
  Scenario: report structure present
    Tool: powershell
    Steps: Select-String final report for "한 줄 결론", "점수표", "Seed", "Buy", "Sell", "P0-P5", "$start-work".
    Expected: All sections are present.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md

  Scenario: table count
    Tool: powershell
    Steps: Count markdown table separator lines matching "^\\|[-: ]+\\|".
    Expected: At least 8 table separators.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md
  ```

  **Commit**: NO | Message: N/A | Files: `docs/update_log/2026-06-15_condition_self_improvement_process_report.md`

- [x] 9. 보고서 검증 및 상태 정리

  **What to do**: JSON parse, source path existence, focused tests, diff scope, protected path status를 확인하고 `verification.md`에 결과를 남긴다. 테스트는 보고서가 실제로 인용하는 unit test만 대상으로 한다.

  **Must NOT do**: 전체 장시간 backtest나 LLM generation을 실행하지 않는다.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: Final Verification | Blocked By: 8

  **References**:
  - Test: `tests/unit/test_discovery_stateful.py` - stateful feedback behavior.
  - Test: `tests/unit/test_template_hypothesis.py` - prompt/feedback generation behavior.
  - Test: `tests/unit/test_refine_gate.py` and `tests/unit/test_refine_gate_wire.py` - refine gate behavior.
  - Command policy: root `AGENTS.md` command list.

  **Acceptance Criteria**:
  - [ ] `python -m json.tool .omo/evidence/condition-self-improvement-process-report-20260615/gap_score_matrix.json` exits 0.
  - [ ] Focused pytest command result is recorded. Recommended: `python -m pytest tests/unit/test_discovery_stateful.py tests/unit/test_template_hypothesis.py tests/unit/test_refine_gate.py tests/unit/test_refine_gate_wire.py -q -p no:cacheprovider`.
  - [ ] `git diff --check` result is recorded.
  - [ ] `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json` result is recorded.
  - [ ] Verification notes distinguish pre-existing dirty files from files created by this report task.

  **QA Scenarios**:
  ```text
  Scenario: focused tests verify cited behavior
    Tool: powershell
    Steps: Run python -m pytest tests/unit/test_discovery_stateful.py tests/unit/test_template_hypothesis.py tests/unit/test_refine_gate.py tests/unit/test_refine_gate_wire.py -q -p no:cacheprovider
    Expected: Pass, or failure captured with exact failing test names and why the report still can/cannot rely on them.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md

  Scenario: protected paths unchanged
    Tool: powershell
    Steps: Run git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
    Expected: No protected writes from this report task.
    Evidence: .omo/evidence/condition-self-improvement-process-report-20260615/verification.md
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/condition-self-improvement-process-report-20260615/verification.md`

## Final Verification Wave
> ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. Plan Compliance Audit
  - Verify all deliverables exist and no source code files were edited by this work.
  - Verify every report claim about current state has a source in `source_inventory.md` or existing evidence docs.

- [x] F2. Evidence Quality Review
  - Verify `gap_score_matrix.json` is parseable and score/gap math is correct.
  - Verify no OOS success is claimed when `.omo/evidence/tmap-walkforward/ab_result_n8.json` and `multiband_overnight_results.md` show OOS/PROMISING 0.

- [x] F3. Real QA
  - Run focused pytest command from Task 9.
  - Run `git diff --check`.
  - Run protected path status command.

- [x] F4. Scope Fidelity Check
  - Verify no runtime DB writes, no live/V3K gate changes, no strategy/template generation, no long backtests.
  - Verify final report names next work as a separate `$start-work` candidate rather than implementing it.

## Commit Strategy
- Do not commit automatically.
- If the user later asks for a commit, stage only:
  - `docs/update_log/2026-06-15_condition_self_improvement_process_report.md`
  - `.omo/evidence/condition-self-improvement-process-report-20260615/*`
- Commit message must use Korean title and Korean markdown body per root instructions.

## Success Criteria
- The user can read one report and understand:
  - why the full process exists,
  - what current code already supports,
  - why current AI is not yet fully self-improving,
  - which percentage is missing,
  - how each missing part should be improved,
  - and which `$start-work` plan should execute next.
