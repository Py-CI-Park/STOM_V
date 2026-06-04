# STOM Condition Research Re-Review and Re-Research Plan

## TL;DR
> **Summary**: Re-audit the prior passed autoresearch report, refresh local STOM 2U_C evidence, refresh external quant/AI validation references, and produce a new Korean-centered read-only research report with a concrete improvement roadmap for profitable human-approved condition expressions.
> **Deliverables**:
> - New report: `.omo/evidence/condition-research-rereview-20260603.md`
> - Evidence ledger: `.omo/evidence/condition-research-rereview-evidence.md`
> - Claim-gap matrix: `.omo/evidence/condition-research-claim-gap-matrix.csv`
> - Safety verification log: `.omo/evidence/condition-research-rereview-verification.txt`
> **Effort**: Medium
> **Parallel**: YES - 4 waves
> **Critical Path**: Task 1 -> Tasks 2/3/4/5 -> Task 6 -> Task 7 -> Final Verification

## Context
### Original Request
The user asked: `$ulw-plan ?? ?? ?? ? ??`.

### Interview Summary
No extra user decision is required. Defaults applied to Metis ambiguities:
- Write a new Korean-centered re-review/research report.
- Do not overwrite the prior `.omx/goals/autoresearch/condition-evolution-profit-research-20260602/research-report.md`.
- Keep the work read-only with respect to source code, DBs, live runtime, V3K gates, and protected result paths.
- Use `.omo/evidence/` for generated research outputs and validation evidence.
- Treat prior report counts such as `equity_points=0` / `prompts=4` as historical until Task 4 confirms current read-only DB counts.
- Use Korean body text with English terms/links where needed.

### Metis Review (gaps addressed)
Metis found decision risks and the plan resolves them with defaults and explicit guardrails: the prior report must be treated as historical, current runtime-state counts must be rechecked before any conclusion, external references must be revalidated rather than assumed refreshed, dashboard `final_approval`/`export_winner` and DB write paths are forbidden, V3K assets remain offline/advisory only, UTF-8-aware reads should be used for Korean logs, and full unit tests are baseline evidence rather than a clean pass gate because unrelated failures already exist.

## Work Objectives
### Core Objective
Produce a decision-ready second-pass research report that verifies what remains true from the prior report, identifies what is missing or stale, and gives an evidence-backed roadmap for improving STOM condition-expression research toward profitable human-approved strategies.

### Deliverables
- `.omo/evidence/condition-research-rereview-20260603.md`: final Korean-centered report.
- `.omo/evidence/condition-research-rereview-evidence.md`: source/evidence ledger with local paths and external links.
- `.omo/evidence/condition-research-claim-gap-matrix.csv`: claim-by-claim matrix from prior report.
- `.omo/evidence/condition-research-rereview-verification.txt`: command outputs and QA notes.

### Definition of Done
- Prior report claims are mapped to confirmed/stale/unsupported/needs-more-evidence status.
- Local code/docs/state evidence is refreshed from the current worktree.
- External quant/AI validation references are rechecked with current URLs.
- Final report is Korean-centered and includes citations/links, local file references, and evidence-vs-inference labels.
- No source files are edited.
- Protected paths remain untouched.
- `git diff --check` and `python scripts/verify_nonrelease_sync.py` pass.

### Must Have
- Preserve STOM_Version_2U_C rules from `AGENTS.md`.
- Keep V3K gate execution at `3/6`; do not advance gates.
- Use `verify_nonrelease_sync.py`, not `verify_release_sync.py`.
- Explain how to improve human condition-expression creation without doing implementation.
- Include a concrete next-work backlog ranked P0/P1/P2.

### Must NOT Have
- No source-code edits.
- No live broker actions, KHOPENAPI connect/login, USER_ACK creation, DB cutover, live order/exit wiring, dashboard `final_approval`, or `export_winner` invocation.
- No writes to `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`, or `_v3k_sidecar/v3k_gui_settings.json`.
- No claim that a condition is profitable without multi-horizon and overfitting-risk evidence.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after for plan/research artifacts only; no source-code test implementation.
- QA policy: Every task has agent-executed scenarios.
- Evidence: `.omo/evidence/task-{N}-{slug}.txt` or `.md`.
- Full `pytest tests/unit/ -q` is not a success gate because the current worktree already has unrelated backtest/UI contract failures. Record current failures only if rerun is needed for context.
- Use UTF-8-aware reads where possible, e.g. set `PYTHONUTF8=1` or read files with Python `encoding='utf-8'`, because some Korean shell output renders garbled.

## Execution Strategy
### Parallel Execution Waves
Wave 1: Task 1 safety snapshot.
Wave 2: Tasks 2, 3, 4, 5 in parallel after Task 1.
Wave 3: Task 6 synthesizes all research.
Wave 4: Task 7 validates and freezes report.

### Dependency Matrix
| Task | Depends On | Blocks |
|---|---|---|
| 1 | none | 2,3,4,5 |
| 2 | 1 | 6 |
| 3 | 1 | 6 |
| 4 | 1 | 6 |
| 5 | 1 | 6 |
| 6 | 2,3,4,5 | 7 |
| 7 | 6 | Final Verification |

## TODOs
> Implementation + Test = ONE task. Every task includes references, acceptance criteria, QA scenarios, and commit policy.

- [x] 1. Create safety snapshot and research workspace

  **What to do**: Create `.omo/evidence/` if absent. Record current branch, `git status --short --branch`, protected-path status, and the root/subdirectory AGENTS constraints relevant to this work. Create an evidence ledger skeleton.
  **Must NOT do**: Do not stage, commit, or edit source files. Do not inspect or write protected DB/result paths beyond `git status` checks.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 2,3,4,5 | Blocked By: none

  **References**:
  - Governance: `AGENTS.md` - branch role, V3K gates, protected paths, verification commands.
  - Local knowledge: `docs/AGENTS.md`, `scripts/AGENTS.md`, `ai_strategy_loop/AGENTS.md`.
  - Prior artifact: `.omx/goals/autoresearch/condition-evolution-profit-research-20260602/research-report.md`.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/condition-research-rereview-evidence.md` exists and lists branch, commit, status summary, protected path check, and scope guardrails.
  - [ ] `.omo/evidence/task-1-safety-snapshot.txt` contains outputs from `git status --short --branch` and protected-path status command.

  **QA Scenarios**:
  ```text
  Scenario: Safety snapshot happy path
    Tool: powershell
    Steps: Run `git status --short --branch`; run `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json`; append both outputs to `.omo/evidence/task-1-safety-snapshot.txt`.
    Expected: Evidence file exists; protected-path command shows no new modifications from this research task.
    Evidence: .omo/evidence/task-1-safety-snapshot.txt

  Scenario: Protected path dirty edge case
    Tool: powershell
    Steps: If protected-path status is non-empty, record each path under `Blocked / pre-existing protected changes` in the evidence ledger and do not proceed to write any protected path.
    Expected: No protected path is modified by the agent; dirty state is classified as pre-existing or blocker.
    Evidence: .omo/evidence/task-1-safety-snapshot.txt
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/*`

- [x] 2. Audit the prior research report claim-by-claim

  **What to do**: Read the prior report, mission, completion, ledger, and rubric. Extract every material claim into a CSV matrix with columns: claim_id, claim_text, prior_evidence, current_status, confidence, needs_refresh, followup_action.
  **Must NOT do**: Do not rewrite the prior report. Do not silently drop weak claims.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 6 | Blocked By: 1

  **References**:
  - Prior report: `.omx/goals/autoresearch/condition-evolution-profit-research-20260602/research-report.md`.
  - Freshness logs: `docs/update_log/2026-06-02*`, `docs/update_log/2026-06-03*`, especially AI strategy loop handoff/resume notes if present.
  - Mission/completion: `.omx/goals/autoresearch/condition-evolution-profit-research-20260602/mission.json`, `completion.json`, `ledger.jsonl`, `rubric.md`.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/condition-research-claim-gap-matrix.csv` exists.
  - [ ] Matrix includes at least these themes: overfitting defense, multi-horizon validation, evidence persistence, dashboard decision card, exit/MDD, V3K analyzer boundaries, ML leakage controls.
  - [ ] Each claim has a status: confirmed, stale, unsupported, or needs-more-evidence.

  **QA Scenarios**:
  ```text
  Scenario: Claim extraction happy path
    Tool: powershell/python
    Steps: Parse headings and bullets from prior report; manually consolidate material claims into CSV; count rows.
    Expected: CSV row count >= 20 and includes all required themes.
    Evidence: .omo/evidence/task-2-claim-audit.txt

  Scenario: Weak-evidence claim edge case
    Tool: manual read + powershell
    Steps: For any claim without a local path or external URL, mark `current_status=needs-more-evidence` and add a followup action.
    Expected: No unsupported claim is marked confirmed.
    Evidence: .omo/evidence/condition-research-claim-gap-matrix.csv
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/*`

- [x] 3. Refresh local code, dashboard, backtest, CLI, and V3K evidence

  **What to do**: Re-inspect the current worktree for the features discussed in the prior report. Cover `ai_strategy_loop`, `backtest`, `cli`, `research`, `strategy`, `docs/reference/STOM_Good_Results`, current `docs/update_log/2026-06-02*` / `2026-06-03*` notes, and relevant tests. Summarize whether each feature still exists and what changed or needs deeper verification.
  **Must NOT do**: Do not modify code, run backtests that create result data, or write runtime DBs.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 6 | Blocked By: 1

  **References**:
  - AI loop: `ai_strategy_loop/config.py`, `ai_strategy_loop/fitness/score.py`, `ai_strategy_loop/brain/prompt.py`, `ai_strategy_loop/brain/generator.py`, `ai_strategy_loop/controller/state.py`, `ai_strategy_loop/dashboard/app.py`, `ai_strategy_loop/dashboard/frontend/`.
  - Backtest: `backtest/backtest.py`, `backtest/backengine_base.py`, `backtest/rolling_walk_forward_test.py`, `backtest/optimiz.py`.
  - CLI research: `cli/research_loop.py`, `cli/condition_generator.py`, `cli/ml_factor_model.py`, `cli/research_optimizer.py`, `cli/research_v3_decision.py`.
  - V3K analyzers: `research/analyzer/`, `research/deeplearning/`, `strategy/v3k_analyzer_adapter.py`.
  - Good results: `docs/reference/STOM_Good_Results/`.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/task-3-local-refresh.md` lists all inspected local surfaces with file paths.
  - [ ] Each prior local feature claim is classified as present, changed, absent, or not-inspected-with-reason.
  - [ ] The report identifies any pre-existing dirty code files separately from research findings.

  **QA Scenarios**:
  ```text
  Scenario: Local feature inventory happy path
    Tool: powershell
    Steps: Use read-only `Get-Content`, `Select-String`, Python UTF-8 file reads, and `git status` to inspect listed files and summarize evidence.
    Expected: Evidence file contains at least one concrete path for each of the seven local scopes.
    Evidence: .omo/evidence/task-3-local-refresh.md

  Scenario: Missing or changed file edge case
    Tool: powershell
    Steps: If a referenced file is missing or materially changed, record `not found` or `changed from prior assumption` with path and effect.
    Expected: Missing/changed files are not ignored; final report avoids stale claims.
    Evidence: .omo/evidence/task-3-local-refresh.md
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/*`

- [x] 4. Refresh runtime-state and observability evidence without mutating DBs

  **What to do**: Read current `ai_strategy_loop/state` metadata and SQLite counts in read-only mode. Re-check the prior observations around `equity_points`, `prompts`, generations, runs, and strategy DB counts. Metis flagged that current counts may now be `equity_points=1943` and `prompts=184`; verify this independently before using it. Capture whether observability gaps still exist or have been partially closed.
  **Must NOT do**: Do not write to `.db` files. Do not run migrations. Do not mark runtime runs complete. Do not call dashboard `final_approval` or `export_winner`.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 6 | Blocked By: 1

  **References**:
  - State contract: `ai_strategy_loop/controller/state.py`.
  - Export boundary to avoid: `ai_strategy_loop/controller/export.py`, `ai_strategy_loop/dashboard/app.py` `final_approval` route if present.
  - Runtime state dir: `ai_strategy_loop/state/`.
  - Prior report DB claims: `.omx/goals/autoresearch/condition-evolution-profit-research-20260602/research-report.md` section `Runtime DB findings`.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/task-4-state-observability.md` records read-only counts for available state DB tables or documents why DB inspection was skipped.
  - [ ] Final report states whether `equity_points=0` and `prompts=4` remain true, changed, or unverified.
  - [ ] No DB file appears modified in `git status --short -- *.db ai_strategy_loop/state` due to this task.

  **QA Scenarios**:
  ```text
  Scenario: Read-only SQLite inventory
    Tool: python
    Steps: Open SQLite DBs using URI `mode=ro`; query table names and row counts; write only to `.omo/evidence/task-4-state-observability.md`; then run `git status --short -- *.db ai_strategy_loop/state`.
    Expected: Counts are captured and DB file mtimes/git status do not change.
    Evidence: .omo/evidence/task-4-state-observability.md

  Scenario: DB missing or locked edge case
    Tool: python
    Steps: If DB is missing/locked, record exact error and classify observability evidence as unavailable rather than guessing.
    Expected: No fabricated counts; final report labels the gap.
    Evidence: .omo/evidence/task-4-state-observability.md
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/*`

- [x] 5. Refresh external quant, AI, and validation references

  **What to do**: Re-check external sources and collect current links for overfitting defense, deflated metrics, time-series validation, purged/embargo CV, triple-barrier/meta-labeling, multi-objective/Pareto optimization, and slippage/execution realism. Treat any planning-time links as candidates until opened/verified during execution. Prefer primary or official sources.
  **Must NOT do**: Do not rely on random blog claims when primary/official sources are available. Do not quote long copyrighted passages.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 6 | Blocked By: 1

  **References**:
  - PBO/backtest overfitting: https://scholarworks.wmich.edu/math_pubs/42/
  - Deflated Sharpe: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
  - TimeSeriesSplit: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
  - Optuna multi-objective/Pareto: https://optuna.readthedocs.io/en/v3.4.1/tutorial/20_recipes/002_multi_objective.html
  - Prior external source list: prior research report section `External references used`.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/task-5-external-references.md` lists each source, URL, date accessed, and how it changes or confirms the prior report.
  - [ ] Final report includes citations/links for all external recommendations.
  - [ ] Any non-primary source is explicitly labeled as secondary.

  **QA Scenarios**:
  ```text
  Scenario: External reference refresh happy path
    Tool: web/browser or read-only web search
    Steps: Open or verify current URLs for the required reference families; record access date and key applicability in evidence file.
    Expected: At least six reference families are covered and no dead link is used unlabelled.
    Evidence: .omo/evidence/task-5-external-references.md

  Scenario: Source unavailable edge case
    Tool: web/browser
    Steps: If a prior URL is dead, find a primary replacement or mark the recommendation as needing source refresh.
    Expected: Final report does not cite unavailable sources as confirmed.
    Evidence: .omo/evidence/task-5-external-references.md
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/*`

- [x] 6. Write the second-pass Korean-centered research report

  **What to do**: Synthesize Tasks 2-5 into `.omo/evidence/condition-research-rereview-20260603.md`. The report must be in Korean-centered prose with clear local paths and external links. Include executive summary, confirmed findings, changed/stale findings, P0/P1/P2 roadmap, human condition-expression workflow, and a no-code/no-live-safety record.
  **Must NOT do**: Do not overwrite the prior report. Do not claim a feature is implemented if only recommended. Do not make financial guarantees.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: 7 | Blocked By: 2,3,4,5

  **References**:
  - Claim matrix: `.omo/evidence/condition-research-claim-gap-matrix.csv`.
  - Local refresh: `.omo/evidence/task-3-local-refresh.md`.
  - State evidence: `.omo/evidence/task-4-state-observability.md`.
  - External references: `.omo/evidence/task-5-external-references.md`.
  - Prior report: `.omx/goals/autoresearch/condition-evolution-profit-research-20260602/research-report.md`.
  - Freshness logs: `docs/update_log/2026-06-02*`, `docs/update_log/2026-06-03*`, especially AI strategy loop handoff/resume notes if present.

  **Acceptance Criteria**:
  - [ ] Report exists at `.omo/evidence/condition-research-rereview-20260603.md`.
  - [ ] Report includes sections: prior-report audit, current local evidence, external research refresh, gap matrix summary, roadmap, safe operating playbook, verification record.
  - [ ] Every recommendation is labeled as evidence-backed, inference, or future experiment.
  - [ ] Report explicitly states that no code/source/runtime DB/live wiring changes were made.

  **QA Scenarios**:
  ```text
  Scenario: Report completeness happy path
    Tool: powershell
    Steps: Check report file exists; grep for required section headings and at least one local path plus one external URL per major section.
    Expected: All required sections present and references are concrete.
    Evidence: .omo/evidence/task-6-report-completeness.txt

  Scenario: Overclaiming edge case
    Tool: manual read + grep
    Steps: Search report for absolute profit guarantees or implementation-complete claims; rewrite any such language as risk/probability/inference language.
    Expected: No financial guarantees; no false implementation claims.
    Evidence: .omo/evidence/task-6-report-completeness.txt
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/*`

- [x] 7. Validate safety, consistency, and final evidence package

  **What to do**: Run final verification commands, inspect generated files, ensure only `.omo/evidence/` artifacts were written by the re-research execution, verify dashboard export/final approval was not invoked, and produce a final verification log.
  **Must NOT do**: Do not stage or commit. Do not attempt to fix unrelated existing code/test failures.

  **Parallelization**: Can Parallel: NO | Wave 4 | Blocks: Final Verification | Blocked By: 6

  **References**:
  - Root commands: `AGENTS.md` section `COMMANDS`.
  - Current known test caveat: full unit suite currently has unrelated backtest/UI contract failures.
  - Protected-path guard: `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json`.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/condition-research-rereview-verification.txt` contains outputs from `git diff --check`, `python scripts/verify_nonrelease_sync.py`, protected-path status, and generated-file listing.
  - [ ] Protected-path status is empty or classified as pre-existing unrelated state.
  - [ ] Final report path and evidence files are listed in the verification log.

  **QA Scenarios**:
  ```text
  Scenario: Verification happy path
    Tool: powershell
    Steps: Run `git diff --check`; run `python scripts/verify_nonrelease_sync.py`; run protected-path status command; list `.omo/evidence/condition-research*` files.
    Expected: diff check and nonrelease verifier pass; protected paths untouched by this task.
    Evidence: .omo/evidence/condition-research-rereview-verification.txt

  Scenario: Existing unrelated failure edge case
    Tool: powershell
    Steps: If full tests are considered, do not require `pytest tests/unit/ -q` as pass gate; record known existing failures separately if rerun.
    Expected: Research deliverable can complete despite unrelated pre-existing code-test failures, as long as safety commands pass.
    Evidence: .omo/evidence/condition-research-rereview-verification.txt
  ```

  **Commit**: NO | Message: N/A | Files: `.omo/evidence/*`

## Final Verification Wave
> ALL must APPROVE. Present consolidated results to user and get explicit okay before completing any subsequent execution goal.

- [x] F1. Plan Compliance Audit
  - Confirm all deliverables are under `.omo/evidence/` and no source code was edited.
  - Evidence: `.omo/evidence/final-plan-compliance.txt`.

- [x] F2. Research Quality Review
  - Verify every major recommendation has local evidence, external citation, or explicit inference label.
  - Evidence: `.omo/evidence/final-research-quality.txt`.

- [x] F3. Safety / Scope Fidelity Check
  - Verify V3K gates did not advance and protected path status remains clean.
  - Evidence: `.omo/evidence/final-scope-fidelity.txt`.

- [x] F4. User-Facing Summary
  - Produce a Korean summary with report path, top findings, validation commands, and remaining risks.
  - Evidence: `.omo/evidence/final-user-summary.md`.

## Commit Strategy
No commit by default. If the user later asks to commit research artifacts, stage only the explicitly requested `.omo/evidence/` files and use a Korean Lore-style commit message. Never use `git add -A`.

## Success Criteria
- The re-review report gives a sharper, evidence-backed answer than the prior report.
- The report distinguishes confirmed facts from stale claims and future experiments.
- The final roadmap tells an executor exactly what to implement later if the user chooses execution.
- No source/runtime/protected path is modified.
