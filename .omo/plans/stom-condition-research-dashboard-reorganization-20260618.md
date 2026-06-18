# STOM 조건식 연구 대시보드 재정리 및 업그레이드 계획

## TL;DR
> **Summary**: `STOM_Version_2U_C-ai-strategy-loop` 이후 누적된 조건식 연구, OOS, 대시보드, PR 흐름을 다시 설명 가능한 구조로 정리하고, 앞으로의 연구가 evidence lineage, naming, official OOS, dashboard visibility를 통해 스스로 개선되도록 만드는 단일 실행 계획이다.
> **Deliverables**:
> - 브랜치/PR/커밋 파생 관계 지도와 wave별 재구성 전략.
> - 조건식 연구 canonical registry, naming taxonomy, evidence lineage 규칙.
> - 연구 진행 관리 프로세스와 다음 공식 OOS 실행 기준.
> - 대시보드 전체 전수검사 리포트: 중복 기능, 기능별 분류, 비효율, 시각 기능, 에러, 테스트 갭.
> - 대시보드 개선 backlog: 후보 별칭, evidence type badge, latest update_log indexing, GUI parity 확인, branch attribution visibility.
> **Effort**: XL
> **Parallel**: YES - 5 waves
> **Critical Path**: Safety/Inventory -> Canonical Research Registry -> Dashboard Audit -> Naming/Lineage Guards -> UI/API Improvements -> Full Verification

## Context

### Original Request

사용자는 최근 2개 커밋까지 포함해 지금까지의 작업을 체계적으로 정리하고, `STOM_Version_2U_C-ai-strategy-loop` 이후 파생된 연구/대시보드 개발을 다시 브랜치/PR 단위로 설명 가능한 구조로 만들고 싶다고 요청했다. 또한 지금까지의 조건식 연구를 정리하고, 앞으로 연구를 진행하며 연구 내용 관리 자체가 연구 성능을 개선하는 프로세스를 연구하고, 대시보드 전체를 전수 검사해 중복 기능, 기능별 분류, 비효율성, 조건식 연구 네이밍 규칙, 시각 기능, 에러를 누락 없이 점검하는 계획을 페이지별로 상세히 원했다.

### Current Ground Truth

- Current branch: `lazycodex/tick-sparse-positive-generation-improvement-20260604`.
- Current worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`.
- Important correction: `wt-dev` is not currently checked out on `STOM_Version_2U_C-ai-strategy-loop`; that branch is the local AI evolution dashboard anchor.
- Latest commits:
  - `067ef1841` 공식 OOS 후속 연구 기록 추가.
  - `81fbcfe03` 조건식 연구 현황 재검토 문서화.
- Branch ancestry:
  - `STOM_Version_2U_C -> STOM_Version_2U_C-ai-strategy-loop`: +125 commits.
  - `STOM_Version_2U_C-ai-strategy-loop -> origin/lazycodex/tick-sparse-positive-generation-improvement-20260604`: +319 commits, first-parent 186 commits, merge commits 59.
  - `origin/lazycodex/tick-sparse-positive-generation-improvement-20260604 -> wt-dev HEAD`: +36 local commits at planning time.
- Direct anchor gap: `STOM_Version_2U_C-ai-strategy-loop..HEAD` is +355 commits and `HEAD..STOM_Version_2U_C-ai-strategy-loop` is 0 commits.
- Remote branch check: `origin/STOM_Version_2U_C-ai-strategy-loop` is not currently present in `git ls-remote`; it must be pushed before it can be used as a GitHub PR base.
- Current `wt-dev` has many uncommitted and untracked research/dashboard artifacts. Execution must not reset, stash, clean, or overwrite them.
- Restart target model: after dirty-state classification and required commits, push the local anchor branch and the current source branch, open a PR with `base: STOM_Version_2U_C-ai-strategy-loop` and `compare: lazycodex/tick-sparse-positive-generation-improvement-20260604`, merge it, then create the next development branch from the updated `STOM_Version_2U_C-ai-strategy-loop`.
- `wt-webbt` is clean on `feature/webbt-followup-gates-20260618` at `19d82beb`, has no upstream, and remains reserved for future file-disjoint dashboard PR work that is later reflected back into `wt-dev`.

### Research Findings

- `docs/update_log/2026-06-18_condition_research_current_state_rereview.md:5` says the process improved substantially, but cold AI generation remains weak and seed/validated-candidate mutation plus official OOS is the realistic route.
- `docs/update_log/2026-06-18_condition_research_current_state_rereview.md:7` scores: overall process 72, AI generation 67, OOS/portfolio 76, promotion readiness 56.
- `docs/update_log/2026-06-18_condition_research_current_state_rereview.md:60` identifies next official OOS candidates, with the robust candidate first.
- `docs/update_log/2026-06-18_condition_research_current_state_rereview.md:71` lists gaps: cold generation, promotion readiness, time-bucket generalization, branch attribution, human-case corpus, evidence lineage, dashboard docs exposure, unit failures.
- `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md:25` names the priority robust OOS candidate: `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full`.
- `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md:33` says candidate names are too hard and need aliases/dashboard labels.
- `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md:34` says latest update_log auto exposure in dashboard is not implemented.
- `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md:35` says weekday/hourly GUI parity in the evolution dashboard needs confirmation.
- `ai_strategy_loop/dashboard/research_api.py:147` exposes `/research_records`.
- `ai_strategy_loop/dashboard/research_api.py:157` exposes `/evolution_gui_parity`.
- `ai_strategy_loop/dashboard/frontend/app.jsx:326` mounts `ResearchRecordsPanel`.
- `ai_strategy_loop/dashboard/frontend/app.jsx:334` mounts `EvolutionGuiParityPanel`.
- `docs/web_dashboard_expansion/CODEX_DEV_HANDOFF.md:24` requires file-disjoint dashboard development and protecting `wt-dev` research files.
- `docs/web_dashboard_expansion/CODEX_DEV_HANDOFF.md:124` defines dashboard PR gates.
- `docs/web_dashboard_expansion/PROG_P7_FIELD_DIFF.md:33` records the HoF merge decision as DEFER because the two panels have genuinely different fields and functions.

### Metis Review (gaps addressed)

The Codex harness in this session does not expose the `spawn_agent`/Metis tool required by the `ulw-plan` skill. This plan therefore includes a manual Metis-equivalent gap review:

| Gap | Resolution in this plan |
|---|---|
| Scope is too broad and could mix research execution, dashboard development, and branch cleanup | Split into waves: safety/inventory, research governance, dashboard audit, implementation backlog, final verification. |
| `wt-dev` has many dirty files, so direct PR/merge work can lose data | First tasks snapshot dirty state and produce split plan before any staging/commit. |
| Replaying 355 commits into the old anchor can become unreadable | Default to a documented catch-up PR into `STOM_Version_2U_C-ai-strategy-loop` only after dirty-state classification; if review size is too broad, fall back to wave-based replay branches. Never force-move, rebase, or reset the anchor. |
| Research evidence can drift from summaries | Add canonical registry and summary/jsonl drift guard tasks before further promotion claims. |
| Dashboard duplicate detection can accidentally delete useful divergent functions | Require field-diff classification: duplicate, divergent-by-design, overlap-with-shared-helper, or obsolete. |
| Visual audit can become subjective | Require Playwright/browser artifacts, route screenshots, console errors, and binary pass/fail criteria. |
| Backtest contract failures can distract from research dashboard work | Treat `backtest.py`/UI/runner 7 failures as separate stabilization plan unless explicitly scheduled. |

## Work Objectives

### Core Objective

Build a disciplined restart plan for STOM condition research and dashboard development so every future condition experiment has a canonical name, evidence lineage, dashboard visibility, official OOS status, and promotion decision path.

### Deliverables

- `.omo/evidence/stom-reorg-20260618/branch-map.md`
- `.omo/evidence/stom-reorg-20260618/dirty-worktree-inventory.md`
- `.omo/evidence/stom-reorg-20260618/research-registry.json`
- `.omo/evidence/stom-reorg-20260618/research-registry.md`
- `.omo/evidence/stom-reorg-20260618/naming-taxonomy.md`
- `.omo/evidence/stom-reorg-20260618/evidence-lineage-rules.md`
- `.omo/evidence/stom-reorg-20260618/dashboard-inventory.md`
- `.omo/evidence/stom-reorg-20260618/dashboard-duplicate-audit.md`
- `.omo/evidence/stom-reorg-20260618/dashboard-visual-error-audit.md`
- `.omo/evidence/stom-reorg-20260618/research-management-process.md`
- `.omo/evidence/stom-reorg-20260618/pr-restart-strategy.md`
- `docs/update_log/YYYY-MM-DD_stom_research_dashboard_reorg_execution.md`
- Optional later implementation commits for aliases, update_log indexing, evidence labels, dashboard visual fixes, and audit scripts.

### Definition of Done

- Branch ancestry, anchor catch-up PR strategy, and replay fallback strategy are recorded with exact commit hashes and PR wave boundaries.
- All current research evidence and key untracked artifacts are inventoried before any modification.
- Every candidate class has a naming rule: machine name, display alias, evidence type, OOS status, promotion status.
- Dashboard pages/panels are classified by function, owner file, data source, endpoint, overlap/duplicate status, and error/QA status.
- Research management process defines what must be written before, during, and after every experiment.
- Dashboard audit produces actionable backlog items with severity and owner.
- Final verification commands run and outputs are saved.
- No protected runtime path is modified as a side effect.

### Must Have

- Preserve STOM 2U_C nonrelease and V3K gate rules.
- Treat `STOM_Version_2U_C-ai-strategy-loop` as a protected anchor until the explicit catch-up PR step; update it only by reviewed PR merge, never by force-push, reset, or direct history rewrite.
- Stage files explicitly in later execution; never use `git add -A`.
- Separate `wt-dev` research work from `wt-webbt` dashboard PR work.
- Distinguish official OOS, CSV reanalysis, portfolio rule simulation, design note, and deferred/blocked work.
- Dashboard tests must include static checks, bundle build, harness, API tests, and real browser/manual QA artifacts when UI changes.

- Before editing `docs/`, `ai_strategy_loop/`, `scripts/`, or `tests/`, read the directory-local `AGENTS.md` and record applicable constraints in the safety snapshot or task evidence.
- `Commit: YES` markers mean "commit during an explicitly approved execution run"; review/planning mode must not stage, commit, push, or merge.

### Must NOT Have

- Do not reset, clean, stash, or restore current `wt-dev` dirty research artifacts.
- Do not modify `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports`, `v3k_settings*.json`, or `_v3k_sidecar/v3k_gui_settings.json`.
- Do not invoke final approval/export winner or write live strategy DBs.
- Do not run KHOPENAPI login, live order, live exit wiring, or V3K gate 4~6.
- Do not merge HoF panels just because names overlap; `PROG_P7_FIELD_DIFF.md` says they are divergent by design.
- Do not fix `backtest.py` contract failures inside this research dashboard plan.

## Verification Strategy

> VERIFICATION IS AGENT-EXECUTED - all verification evidence is command/browser/tool-backed. Human review can approve direction, but remote pushes, PR merge, official OOS execution, and any commit require the explicit execution gate stated in this plan.

- Test decision: TDD for new API/UI/audit scripts; tests-after allowed only for documentation inventories.
- Existing test infrastructure: `pytest`, `node build-app.mjs`, `track-z-harness.mjs`, `check-missing-imports.mjs`, `verify_nonrelease_sync.py`.
- Browser QA: start dashboard on a temporary non-8770 port and use `curl` plus browser/screenshot automation where available.
- Evidence root: `.omo/evidence/stom-reorg-20260618/`.
- Full unit baseline: known unrelated 7 failures are tolerated only if the exact failure set remains unchanged.

## Execution Strategy

### Parallel Execution Waves

Wave 1: Safety, branch/replay map, dirty worktree inventory, research source inventory.  
Wave 2: Canonical research registry, naming taxonomy, evidence lineage, research management process.  
Wave 3: Dashboard IA inventory, duplicate/function audit, error/visual audit, test coverage map.  
Wave 4: Implementation backlog for aliases, latest update_log indexing, evidence labels, GUI parity confirmation, branch attribution visibility.  
Wave 5: Final verification, split commit/PR plan, handoff.

### Dependency Matrix

| Task | Depends on | Blocks |
|---|---|---|
| 1 | none | 2, 3, 4 |
| 2 | 1 | 5, 6 |
| 3 | 1 | 4, 5, 16 |
| 4 | 1, 3 | 5, 6 |
| 5 | 2, 4 | 7, 8, 12 |
| 6 | 4 | 7, 8 |
| 7 | 5, 6 | 12, 13 |
| 8 | 5, 6 | 12, 13 |
| 9 | 1 | 10, 11 |
| 10 | 9 | 12 |
| 11 | 9 | 12 |
| 12 | 7, 8, 10, 11 | 13, 14, 15 |
| 13 | 12 | 16 |
| 14 | 12 | 16 |
| 15 | 12 | 16 |
| 16 | 3, 13, 14, 15 | F1-F4 |

## TODOs

- [x] 1. Page 1 - Safety Snapshot and Nonrelease Guard

  **What to do**: Capture branch, HEAD, upstream, dirty status, protected path status, active `.omo/.gjc` workflow state (`.omo/boulder.json`, `.omo/start-work/ledger.jsonl`, `.gjc/` if present), recent commits, and active worktree list before any organization or implementation work. Save all outputs under `.omo/evidence/stom-reorg-20260618/`.

  **Must NOT do**: Do not clean, reset, stash, restore, or stage anything.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 2, 3, 4 | Blocked By: none

  **References**:
  - `AGENTS.md` - protected paths and commit/review rules.
  - `docs/web_dashboard_expansion/CODEX_DEV_HANDOFF.md:24` - file-disjoint worktree model.
  - `docs/web_dashboard_expansion/CODEX_DEV_HANDOFF.md:94` - absolute no-go actions.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/stom-reorg-20260618/safety-snapshot.txt` contains `git status --short --branch`, `git worktree list`, latest 12 commits, upstream ahead/behind, and protected-path status.
  - [ ] Protected path status command is captured and reviewed.
  - [ ] The snapshot states whether current `wt-dev` is dirty and explicitly says no cleanup was performed.

  **QA Scenarios**:
  ```
  Scenario: clean evidence capture
    Tool: powershell
    Steps: Run git status/worktree/log/protected-path commands and redirect to safety-snapshot.txt.
    Expected: Evidence file exists and includes current branch `lazycodex/tick-sparse-positive-generation-improvement-20260604`.
    Evidence: .omo/evidence/stom-reorg-20260618/safety-snapshot.txt

  Scenario: protected path guard
    Tool: powershell
    Steps: Run `git status --short -- _database/ _database_v3k_shadow/ _log/ backup/ ":(glob)**/*.db" backtest/graph/ .omx/reports/ ":(glob)v3k_settings*.json" _v3k_sidecar/v3k_gui_settings.json`.
    Expected: Output is empty or explicitly classified without modification.
    Evidence: .omo/evidence/stom-reorg-20260618/protected-path-status.txt
  ```

  **Commit**: NO | Message: n/a | Files: evidence only

- [x] 2. Page 2 - Branch and PR Restart Map

  **What to do**: Build a restart map from `STOM_Version_2U_C-ai-strategy-loop` to current parent and `wt-dev` HEAD. Record that `STOM_Version_2U_C-ai-strategy-loop` is a local anchor at `84acb6cb`, current `wt-dev` HEAD is on `lazycodex/tick-sparse-positive-generation-improvement-20260604` at `067ef184`, and the direct anchor-to-HEAD gap is +355 commits. Group first-parent merge commits into functional waves: Phase14, Program A/B, Track Z, Research/OOS, Dashboard records, Current local commits. Produce a PR restart strategy with the default path:
  1. finish dirty-state classification;
  2. commit only selected current `wt-dev` changes;
  3. push `STOM_Version_2U_C-ai-strategy-loop` because `origin/STOM_Version_2U_C-ai-strategy-loop` is absent;
  4. push `lazycodex/tick-sparse-positive-generation-improvement-20260604`;
  5. open PR with `base: STOM_Version_2U_C-ai-strategy-loop` and `compare: lazycodex/tick-sparse-positive-generation-improvement-20260604`;
  6. merge the PR;
  7. create the next development branch from the updated `STOM_Version_2U_C-ai-strategy-loop`.
  Also define the fallback if the +355 commit PR is too broad: split by wave into `integration/ai-loop-replay-YYYYMMDD-*` branches while preserving the same final base branch.

  **Must NOT do**: Do not create or push branches in this task. This is mapping only.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 5, 6 | Blocked By: 1

  **References**:
  - `STOM_Version_2U_C-ai-strategy-loop` commit `84acb6cbb047` - initial AI evolution dashboard anchor.
  - `origin/lazycodex/tick-sparse-positive-generation-improvement-20260604` commit `19d82bebe55f` - parent after PR #96.
  - `lazycodex/tick-sparse-positive-generation-improvement-20260604` commit `067ef1841f9f` - current `wt-dev` HEAD at planning update.
  - `docs/web_dashboard_expansion/CODEX_DEV_HANDOFF.md:188` - merge commit history preservation.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/stom-reorg-20260618/branch-map.md` includes exact ahead/behind counts.
  - [ ] `.omo/evidence/stom-reorg-20260618/pr-restart-strategy.md` includes the exact base/compare PR route and the required preconditions.
  - [ ] `.omo/evidence/stom-reorg-20260618/pr-restart-strategy.md` describes when to use one catch-up PR versus wave replay branches.
  - [ ] The strategy explicitly states that `STOM_Version_2U_C-ai-strategy-loop` is updated only by reviewed PR merge, not by force move, reset, rebase, or direct overwrite.

  **QA Scenarios**:
  ```
  Scenario: graph count reproduction
    Tool: powershell
    Steps: Run `git rev-list --left-right --count HEAD...STOM_Version_2U_C-ai-strategy-loop`, `git rev-list --count STOM_Version_2U_C-ai-strategy-loop..HEAD`, and matching parent comparisons.
    Expected: Counts are recorded and match the strategy table.
    Evidence: .omo/evidence/stom-reorg-20260618/branch-map.md

  Scenario: no branch mutation
    Tool: powershell
    Steps: Run `git branch --show-current` before and after task.
    Expected: Branch remains unchanged.
    Evidence: .omo/evidence/stom-reorg-20260618/branch-map.md

  Scenario: remote base readiness
    Tool: powershell
    Steps: Run `git ls-remote --heads origin STOM_Version_2U_C-ai-strategy-loop lazycodex/tick-sparse-positive-generation-improvement-20260604`.
    Expected: Strategy records that the anchor remote is absent until pushed and the source remote currently points to `19d82beb`.
    Evidence: .omo/evidence/stom-reorg-20260618/pr-restart-strategy.md
  ```

  **Commit**: NO | Message: n/a | Files: evidence only

- [x] 3. Page 3 - Dirty Worktree Split Inventory

  **What to do**: Classify every current modified/untracked file into buckets: research source change, dashboard API/UI change, generated bundle, evidence artifact, plan/draft, docs/update_log, test, `.omo/.gjc` workflow state, protected/runtime, unknown. Produce explicit future staging groups and Korean commit title suggestions.

  **Must NOT do**: Do not stage or commit. Do not delete unknown files.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 4, 16 | Blocked By: 1

  **References**:
  - `AGENTS.md` - explicit staging rule and protected path list.
  - `docs/web_dashboard_expansion/CODEX_DEV_HANDOFF.md:25` - research workstream must not be touched during dashboard sync.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/stom-reorg-20260618/dirty-worktree-inventory.md` lists all current dirty files by bucket.
  - [ ] Each bucket has proposed action: keep, stage later, ignore, investigate, or protected-do-not-touch.
  - [ ] Generated bundle files are tied to source files that caused them.

  **QA Scenarios**:
  ```
  Scenario: inventory completeness
    Tool: powershell
    Steps: Compare `git status --short` line count to inventory row count.
    Expected: Every dirty line is represented or grouped by glob with explicit count.
    Evidence: .omo/evidence/stom-reorg-20260618/dirty-worktree-inventory.md

  Scenario: protected runtime classification
    Tool: powershell
    Steps: Search inventory for `_database`, `.db`, `backtest/graph`, `.omx`.
    Expected: Any match is marked protected-do-not-touch.
    Evidence: .omo/evidence/stom-reorg-20260618/dirty-worktree-inventory.md
  ```

  **Commit**: NO | Message: n/a | Files: evidence only

- [x] 4. Page 4 - Research Source Inventory and Current-State Baseline

  **What to do**: Inventory all current research documents and evidence roots that define the latest state: current-state rereview, post-Q4 handoff, dashboard records OOS followup, OOS 2023-2025 combo experiment, Q4 defense, post-Q4 bulk research, condition generation breadth, self-improvement score. Extract canonical facts: scores, candidates, OOS status, promotion status, next action.

  **Must NOT do**: Do not recompute results. Do not infer performance numbers not present in evidence.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 5, 6 | Blocked By: 1, 3

  **References**:
  - `docs/update_log/2026-06-18_condition_research_current_state_rereview.md:7` - current scores.
  - `docs/update_log/2026-06-18_condition_research_current_state_rereview.md:60` - official OOS candidates.
  - `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md:22` - next research candidates.
  - `docs/research/condition_research/README.md` - research folder role.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/stom-reorg-20260618/research-source-inventory.md` lists each source file, role, key facts, and whether it is canonical or historical.
  - [ ] Conflicting facts are marked as conflict, not silently resolved.
  - [ ] The inventory states the current default research direction: seed bank + official OOS + branch attribution, not cold mass generation.

  **QA Scenarios**:
  ```
  Scenario: key fact extraction
    Tool: powershell
    Steps: Search inventory for `72`, `67`, `76`, `56`, `r8_exclude_cap_lt_1500`.
    Expected: All are present with source references.
    Evidence: .omo/evidence/stom-reorg-20260618/research-source-inventory.md

  Scenario: conflict handling
    Tool: powershell
    Steps: Search inventory for `conflict` or `drift`.
    Expected: Any summary/jsonl mismatch or uncertain source is explicitly marked.
    Evidence: .omo/evidence/stom-reorg-20260618/research-source-inventory.md
  ```

  **Commit**: NO | Message: n/a | Files: evidence only

- [x] 5. Page 5 - Canonical Research Registry Design

  **What to do**: Define a canonical registry schema for condition research campaigns and candidates. It must unify machine name, display alias, candidate family, evidence type, train/OOS period, result metrics, gate status, promotion status, source files, related dashboard record, and next action. Then generate the first registry from current evidence.

  **Must NOT do**: Do not replace raw evidence. Registry is an index over evidence, not the source of truth.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 7, 8, 12 | Blocked By: 2, 4

  **References**:
  - `ai_strategy_loop/dashboard/research_records.py:195` - current research record listing.
  - `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md:33` - names are too hard and need aliases.
  - `.omo/evidence/tmap-walkforward/post-q4-3h-official-oos-recommendations-20260618.json` - next official OOS recommendation source.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/stom-reorg-20260618/research-registry.json` exists and validates with `python -m json.tool`.
  - [ ] `.omo/evidence/stom-reorg-20260618/research-registry.md` contains a human-readable table.
  - [ ] Every candidate has `machine_name`, `display_alias`, `evidence_type`, `oos_status`, `promotion_status`, and `next_action`.
  - [ ] The robust candidate has a short alias such as `저시총 제외 방어 조합`.

  **QA Scenarios**:
  ```
  Scenario: registry validation
    Tool: powershell
    Steps: Run `python -m json.tool .omo/evidence/stom-reorg-20260618/research-registry.json`.
    Expected: Exit 0.
    Evidence: .omo/evidence/stom-reorg-20260618/research-registry.json

  Scenario: alias coverage
    Tool: powershell
    Steps: Search registry markdown for `r8_exclude_cap_lt_1500` and `저시총 제외`.
    Expected: Machine name and display alias both exist.
    Evidence: .omo/evidence/stom-reorg-20260618/research-registry.md
  ```

  **Commit**: YES | Message: `docs(연구): 조건식 연구 정본 레지스트리 초안 추가` | Files: registry evidence + update_log summary

- [x] 6. Page 6 - Research Naming Taxonomy and Visual Label Rules

  **What to do**: Design naming rules for research campaigns, condition candidates, portfolio rules, official OOS runs, CSV reanalysis, shadow comparisons, and blocked/deferred work. Define dashboard visual labels and colors for evidence types and promotion states.

  **Must NOT do**: Do not rename existing files in this task. Provide migration map first.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 7, 8 | Blocked By: 4

  **References**:
  - `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md:36` - evidence type labels need clarity.
  - `ai_strategy_loop/dashboard/frontend/research-records-panel.jsx:34` - ResearchRecordsPanel display entry point.
  - `docs/web_dashboard_expansion/PROG_P7_FIELD_DIFF.md:39` - preserve divergent visual systems when merging would lose fields.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/stom-reorg-20260618/naming-taxonomy.md` defines at least 8 categories: seed, mutation, OOS, shadow, portfolio, defense rule, docs-only, blocked.
  - [ ] Each category has machine-name pattern, Korean display alias pattern, badge text, badge color, promotion meaning.
  - [ ] The taxonomy includes examples for `r8_4`, `exit2 balance`, `r2full MDD`, robust low-cap exclusion, November exclusion shadow.

  **QA Scenarios**:
  ```
  Scenario: naming category completeness
    Tool: powershell
    Steps: Search taxonomy for required category names.
    Expected: All required categories appear.
    Evidence: .omo/evidence/stom-reorg-20260618/naming-taxonomy.md

  Scenario: no destructive migration
    Tool: powershell
    Steps: Run `git status --short` after task.
    Expected: No renamed evidence files; only new taxonomy documents.
    Evidence: .omo/evidence/stom-reorg-20260618/naming-taxonomy.md
  ```

  **Commit**: YES | Message: `docs(연구): 조건식 연구 네이밍 규칙 정의` | Files: taxonomy evidence + docs summary

- [x] 7. Page 7 - Evidence Lineage and Drift Guard Process

  **What to do**: Define how every future research run records pre-registration, raw jsonl, summary, logs, official OOS result, dashboard card, update_log, and promotion decision. Specify drift checks between raw jsonl and summary JSON.

  **Must NOT do**: Do not delete old summaries. Mark stale/drifted files and generate repair tasks.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 12, 13 | Blocked By: 5, 6

  **References**:
  - `docs/update_log/2026-06-17_condition_generation_breadth_evaluation.md` - prior summary drift and branch attribution concerns.
  - `docs/update_log/2026-06-18_condition_research_current_state_rereview.md:81` - evidence lineage remains a gap.
  - `ai_strategy_loop/dashboard/research_records.py:141` - current jsonl candidate parsing.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/stom-reorg-20260618/evidence-lineage-rules.md` defines mandatory files for each campaign.
  - [ ] Rules distinguish raw evidence, derived summary, dashboard index, and narrative report.
  - [ ] Rules include a command-level drift check design and failure action.

  **QA Scenarios**:
  ```
  Scenario: lineage file checklist
    Tool: powershell
    Steps: Search rules for `jsonl`, `summary.json`, `log.txt`, `update_log`, `promotion`.
    Expected: All mandatory evidence classes are present.
    Evidence: .omo/evidence/stom-reorg-20260618/evidence-lineage-rules.md

  Scenario: drift response
    Tool: powershell
    Steps: Search rules for `drift` and `repair`.
    Expected: Rules define what to do when summary and jsonl disagree.
    Evidence: .omo/evidence/stom-reorg-20260618/evidence-lineage-rules.md
  ```

  **Commit**: YES | Message: `docs(연구): 증거 계보와 요약 드리프트 규칙 추가` | Files: lineage evidence + docs summary

- [x] 8. Page 8 - Research Management Operating Process

  **What to do**: Create the recurring process for future research: plan, preregister, run, record, classify evidence, update registry, expose dashboard, decide next action. The process must make research management itself improve research quality by forcing branch attribution, OOS separation, and candidate naming.

  **Must NOT do**: Do not run new OOS in this task.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 12, 13 | Blocked By: 5, 6

  **References**:
  - `docs/update_log/2026-06-18_condition_research_current_state_rereview.md:112` - direction: seed bank + official OOS + branch attribution.
  - `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md:57` - next work moves to official backtest.

  **Acceptance Criteria**:
  - [ ] `.omo/evidence/stom-reorg-20260618/research-management-process.md` defines page templates for preregistration, run log, result card, OOS decision, dashboard card, and next-action queue.
  - [ ] The process includes explicit stop conditions: overfit risk, official OOS fail, MDD cap fail, summary drift, insufficient trades.
  - [ ] The process defines how research output becomes a dashboard card and how dashboard gaps feed the next research task.

  **QA Scenarios**:
  ```
  Scenario: process completeness
    Tool: powershell
    Steps: Search process doc for `preregistration`, `official OOS`, `dashboard`, `next-action`, `stop`.
    Expected: All lifecycle stages exist.
    Evidence: .omo/evidence/stom-reorg-20260618/research-management-process.md

  Scenario: research management feedback loop
    Tool: powershell
    Steps: Search process doc for `branch attribution`, `seed bank`, `registry`.
    Expected: Management loop explicitly improves candidate selection.
    Evidence: .omo/evidence/stom-reorg-20260618/research-management-process.md
  ```

  **Commit**: YES | Message: `docs(연구): 조건식 연구 운영 프로세스 정립` | Files: process evidence + docs summary

- [x] 9. Page 9 - Dashboard Information Architecture Inventory

  **What to do**: Inventory all dashboard tabs, panels, routes, endpoints, data sources, static bundle files, and tests. Classify by function: evolution control, generation results, research records, backtest workbench, simulation, research lab, research pro, verdict, process flow, docs/wiki.

  **Must NOT do**: Do not change UI or remove panels.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 10, 11 | Blocked By: 1

  **References**:
  - `ai_strategy_loop/dashboard/frontend/app.jsx:442` - `STOM_TABS`.
  - `ai_strategy_loop/dashboard/research_api.py:130` - research docs endpoint.
  - `ai_strategy_loop/dashboard/research_api.py:147` - research records endpoint.
  - `ai_strategy_loop/dashboard/frontend/app.jsx:326` - research records panel mount.

  **Acceptance Criteria**:
  - [x] `.omo/evidence/stom-reorg-20260618/dashboard-inventory.md` lists every tab and major panel.
  - [x] Each row includes owner file, endpoint/data source, test file if known, and status.
  - [x] Research Records and Evolution GUI parity panels are explicitly included.

  **QA Scenarios**:
  ```
  Scenario: tab coverage
    Tool: powershell
    Steps: Compare `STOM_TABS` in app.jsx with inventory rows.
    Expected: Every tab key has inventory coverage.
    Evidence: .omo/evidence/stom-reorg-20260618/dashboard-inventory.md

  Scenario: endpoint coverage
    Tool: powershell
    Steps: Search research_api/app route decorators and compare to inventory.
    Expected: New `/research_records` and `/evolution_gui_parity` are covered.
    Evidence: .omo/evidence/stom-reorg-20260618/dashboard-inventory.md
  ```

  **Commit**: YES | Message: `docs(대시보드): 전체 정보구조 인벤토리 작성` | Files: dashboard inventory

- [x] 10. Page 10 - Dashboard Duplicate and Overlap Audit

  **What to do**: Audit duplicate-looking dashboard features and classify them as: true duplicate, divergent-by-design, shared-helper candidate, obsolete, or needs user decision. Include HoF, Research Records vs Research Wiki, Research Lab vs Research Pro, backtest GUI parity vs evolution GUI parity, process flow docs vs dashboard process tab.

  **Must NOT do**: Do not merge or delete components during audit.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 12 | Blocked By: 9

  **References**:
  - `docs/web_dashboard_expansion/PROG_P7_FIELD_DIFF.md:33` - HoF merge deferred.
  - `docs/web_dashboard_expansion/PROG_P7_FIELD_DIFF.md:35` - HoF divergence decision.
  - `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md:30` - dashboard middle cleanup notes.

  **Acceptance Criteria**:
  - [x] `.omo/evidence/stom-reorg-20260618/dashboard-duplicate-audit.md` contains at least 15 feature pairs/groups.
  - [x] Every group has classification, evidence, risk, and recommended action.
  - [x] HoF is marked divergent-by-design, not true duplicate.

  **QA Scenarios**:
  ```
  Scenario: duplicate classification
    Tool: powershell
    Steps: Search duplicate audit for `true duplicate`, `divergent-by-design`, `shared-helper candidate`, `obsolete`.
    Expected: Each classification appears at least once or is marked zero with reason.
    Evidence: .omo/evidence/stom-reorg-20260618/dashboard-duplicate-audit.md

  Scenario: HoF guard
    Tool: powershell
    Steps: Search duplicate audit for `HallOfFamePanel` and `_RpHallOfFame`.
    Expected: Classification is divergent-by-design with reference to P7 field diff.
    Evidence: .omo/evidence/stom-reorg-20260618/dashboard-duplicate-audit.md
  ```

  **Commit**: YES | Message: `docs(대시보드): 중복 기능 전수 감사 기록` | Files: duplicate audit

- [x] 11. Page 11 - Dashboard Visual, Error, and Inefficiency Audit

  **What to do**: Run static and runtime audit for dashboard visual errors, console errors, missing imports, oversized files, unclear labels, confusing names, inefficient polling/fetching, and inaccessible/low-contrast UI. Use existing harness and add a manual browser/curl artifact.

  **Must NOT do**: Do not fix issues in this task unless the plan explicitly creates a follow-up task.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 12 | Blocked By: 9

  **References**:
  - `docs/web_dashboard_expansion/CODEX_DEV_HANDOFF.md:124` - required dashboard gates.
  - `docs/web_dashboard_expansion/CODEX_DEV_HANDOFF.md:170` - missing import static checker.
  - `tests/unit/dashboard/test_track_z_pr1_harness.py:205` - per-tab render sweep.

  **Acceptance Criteria**:
  - [x] `node build-app.mjs`, `node track-z-harness.mjs`, and `node check-missing-imports.mjs` outputs are captured.
  - [x] `.omo/evidence/stom-reorg-20260618/dashboard-visual-error-audit.md` lists each tab with visual/error status and screenshots or HTML artifacts.
  - [x] File line-count audit confirms whether any frontend file exceeds 800 lines.
  - [x] Any console/page errors are severity-ranked.

  **QA Scenarios**:
  ```
  Scenario: static frontend gates
    Tool: powershell
    Steps: Run build-app, track-z-harness, check-missing-imports from dashboard/webui-build.
    Expected: Exit 0 and `allPass: true`.
    Evidence: .omo/evidence/stom-reorg-20260618/dashboard-static-gates.txt

  Scenario: live endpoint smoke
    Tool: curl
    Steps: Start uvicorn on a temporary port; call `/ui/`, `/research_records`, `/evolution_gui_parity?run_id=&gen_no=-1`.
    Expected: HTTP 200 and graceful empty/error payload, no server crash.
    Evidence: .omo/evidence/stom-reorg-20260618/dashboard-curl-smoke.txt
  ```

  **Commit**: YES | Message: `docs(대시보드): 시각 오류와 비효율 전수 감사 기록` | Files: audit evidence + docs summary

- [x] 12. Page 12 - Dashboard Improvement Backlog and First Implementation Slice

  **What to do**: Convert audit findings into a prioritized implementation backlog. The first safe slice should include only low-risk dashboard clarity improvements: candidate alias table, evidence type labels, promotion status badges, latest update_log index visibility, and GUI parity visibility confirmation. If implementation begins, use TDD and keep it in a separate feature branch or clearly separated commit.

  **Must NOT do**: Do not implement high-risk DB/backend changes before tests. Do not touch official backtest engine.

  **Parallelization**: Can Parallel: NO | Wave 4 | Blocks: 13, 14, 15 | Blocked By: 7, 8, 10, 11

  **References**:
  - `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md:42` - robust official OOS still needed.
  - `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md:43` - candidate names need aliases.
  - `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md:44` - latest update_log auto indexing gap.
  - `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md:45` - GUI parity confirmation gap.

  **Acceptance Criteria**:
  - [x] `.omo/evidence/stom-reorg-20260618/dashboard-improvement-backlog.md` ranks improvements by severity, risk, and research value.
  - [x] First implementation slice has a file list, tests, manual QA command, and rollback plan.
  - [x] Items requiring user decision are separated from items safe to implement.

  **QA Scenarios**:
  ```
  Scenario: backlog prioritization
    Tool: powershell
    Steps: Search backlog for `P0`, `P1`, `P2`, `risk`, `rollback`.
    Expected: Every item has priority and rollback/risk.
    Evidence: .omo/evidence/stom-reorg-20260618/dashboard-improvement-backlog.md

  Scenario: implementation slice safety
    Tool: powershell
    Steps: Search first slice for `tests`, `manual QA`, `files`.
    Expected: First slice is executable without judgment calls.
    Evidence: .omo/evidence/stom-reorg-20260618/dashboard-improvement-backlog.md
  ```

  **Commit**: YES | Message: `docs(대시보드): 개선 백로그와 첫 실행 단위 정의` | Files: backlog evidence

- [x] 13. Page 13 - Official OOS Queue and Promotion Workflow

  **What to do**: Define and then execute only if explicitly selected: the official OOS queue starting with `저시총 제외 방어 조합`. If execution is allowed in the implementation run, preregister the run, execute official OOS, record raw and summary evidence, update registry, and produce promotion/defer decision card.

  **Must NOT do**: Do not treat CSV reanalysis as official OOS. Do not promote to live or strategy DB.

  **Parallelization**: Can Parallel: NO | Wave 4 | Blocks: 16 | Blocked By: 12

  **References**:
  - `docs/update_log/2026-06-18_condition_research_current_state_rereview.md:69` - robust official OOS is next, not mass generation.
  - `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md:25` - first candidate.
  - `.omo/plans/post-20260618-official-oos-dashboard-cleanup.md` - existing next official OOS plan.

  **Acceptance Criteria**:
  - [x] `.omo/evidence/stom-reorg-20260618/official-oos-queue.md` lists candidate order, inputs, expected commands, stop criteria, and evidence outputs.
  - [x] If OOS is executed later, registry and dashboard records are updated in the same change set.
  - [x] Promotion status remains `candidate`, `oos_passed`, `deferred`, or `rejected`; never `live`.

  **QA Scenarios**:
  ```
  Scenario: queue clarity
    Tool: powershell
    Steps: Search OOS queue for `저시총 제외 방어 조합`, `official`, `stop`.
    Expected: First candidate and stop criteria are present.
    Evidence: .omo/evidence/stom-reorg-20260618/official-oos-queue.md

  Scenario: promotion boundary
    Tool: powershell
    Steps: Search queue for `live` and `strategy.db`.
    Expected: Any occurrence is in a Must NOT / forbidden context.
    Evidence: .omo/evidence/stom-reorg-20260618/official-oos-queue.md
  ```

  **Commit**: YES | Message: `docs(연구): 공식 OOS 큐와 승격 절차 정의` | Files: OOS queue evidence

- [x] 14. Page 14 - Branch Attribution and AND/OR Contribution Plan

  **What to do**: Design the analysis needed to measure whether AND/OR/if-elif branches actually contribute to profit, MDD reduction, and OOS stability. Define how candidates expose branch_id, how backtest CSV rows are attributed, and how dashboard displays branch contribution.

  **Must NOT do**: Do not change generator syntax or official engine in this planning task.

  **Parallelization**: Can Parallel: YES | Wave 4 | Blocks: 16 | Blocked By: 12

  **References**:
  - `docs/update_log/2026-06-18_condition_research_current_state_rereview.md:78` - branch attribution gap.
  - `docs/update_log/2026-06-17_condition_generation_breadth_evaluation.md` - AND/OR diversity evaluation and branch gap.
  - `ai_strategy_loop/tmap/templates/` - generated template corpus to analyze.

  **Acceptance Criteria**:
  - [x] `.omo/evidence/stom-reorg-20260618/branch-attribution-plan.md` defines data model, instrumentation choices, dashboard view, tests, and non-goals.
  - [x] It distinguishes literal OR, if/elif branches, cap/time buckets, and sell branches.
  - [x] It states how branch contribution affects future seed bank and generation prompts.

  **QA Scenarios**:
  ```
  Scenario: attribution dimensions
    Tool: powershell
    Steps: Search branch plan for `literal OR`, `if/elif`, `time`, `cap`, `sell`.
    Expected: All dimensions are addressed.
    Evidence: .omo/evidence/stom-reorg-20260618/branch-attribution-plan.md

  Scenario: dashboard feedback loop
    Tool: powershell
    Steps: Search branch plan for `dashboard` and `seed bank`.
    Expected: Plan says how branch metrics feed future research.
    Evidence: .omo/evidence/stom-reorg-20260618/branch-attribution-plan.md
  ```

  **Commit**: YES | Message: `docs(연구): AND OR 분기 기여도 분석 계획 추가` | Files: branch attribution plan

- [x] 15. Page 15 - Full Dashboard QA Execution Plan

  **What to do**: Define a repeatable QA matrix for all dashboard pages: evolution, backtest, simulation, lab, pro, verdict, process, standalone lab/pro/verdict, API endpoints. Include viewport sizes, dark/light themes, console errors, stale localStorage, empty/missing backend, and long-candidate-name overflow.

  **Must NOT do**: Do not rely only on tests; real page QA artifacts are mandatory.

  **Parallelization**: Can Parallel: YES | Wave 4 | Blocks: 16 | Blocked By: 12

  **References**:
  - `docs/web_dashboard_expansion/CODEX_DEV_HANDOFF.md:131` - 7 tabs + 3 standalone pages harness.
  - `docs/web_dashboard_expansion/HANDOFF_2026-06-15.md:61` - manual visual QA scope.
  - `ai_strategy_loop/dashboard/frontend/research-records-panel.jsx:105` - dense table where long names may overflow.

  **Acceptance Criteria**:
  - [x] `.omo/evidence/stom-reorg-20260618/dashboard-qa-matrix.md` lists every route/tab, viewport, theme, and expected artifact.
  - [x] Long candidate name and missing API cases are included.
  - [x] Cleanup receipts are defined for server/browser processes.

  **QA Scenarios**:
  ```
  Scenario: QA matrix completeness
    Tool: powershell
    Steps: Search QA matrix for `evolution`, `backtest`, `simulation`, `lab`, `pro`, `verdict`, `process`.
    Expected: All route/tab names exist.
    Evidence: .omo/evidence/stom-reorg-20260618/dashboard-qa-matrix.md

  Scenario: adversarial UI cases
    Tool: powershell
    Steps: Search QA matrix for `long candidate`, `missing API`, `localStorage`, `light`, `dark`.
    Expected: All adversarial cases exist.
    Evidence: .omo/evidence/stom-reorg-20260618/dashboard-qa-matrix.md
  ```

  **Commit**: YES | Message: `docs(대시보드): 전체 QA 매트릭스 정의` | Files: QA matrix

- [x] 16. Page 16 - Split Commit, PR, and Handoff Strategy

  **What to do**: Convert all outputs into a staged execution order and PR/commit strategy. Define which work stays in `wt-dev`, which dashboard-only work moves to `wt-webbt`, which evidence is committed, and which untracked files remain local until reviewed. Include the explicit anchor catch-up sequence: commit selected `wt-dev` changes, push `STOM_Version_2U_C-ai-strategy-loop`, push `lazycodex/tick-sparse-positive-generation-improvement-20260604`, open PR `base: STOM_Version_2U_C-ai-strategy-loop` / `compare: lazycodex/tick-sparse-positive-generation-improvement-20260604`, merge, then create the next branch from the updated anchor. Produce Korean commit messages and PR descriptions.

  **Must NOT do**: Do not stage or commit unless the user explicitly starts execution. This task outputs the strategy.

  **Parallelization**: Can Parallel: NO | Wave 5 | Blocks: F1-F4 | Blocked By: 3, 13, 14, 15

  **References**:
  - `AGENTS.md` - Korean commit title/body and explicit staging.
  - `docs/web_dashboard_expansion/CODEX_DEV_HANDOFF.md:188` - merge commit and history preservation.
  - `docs/web_dashboard_expansion/CODEX_DEV_HANDOFF.md:221` - dashboard gate commands.

  **Acceptance Criteria**:
  - [x] `.omo/evidence/stom-reorg-20260618/split-commit-pr-strategy.md` defines at least 6 commit/PR groups.
  - [x] Each group has exact files/globs, commit title in Korean, verification commands, and target branch/worktree.
  - [x] Strategy explicitly separates `wt-dev` research commits from `wt-webbt` dashboard PRs.
  - [x] Strategy states that `wt-webbt` remains a clean auxiliary dashboard worktree and is not the canonical restart branch.
  - [x] Strategy includes the catch-up PR base/compare pair and the post-merge branch creation rule.

  **QA Scenarios**:
  ```
  Scenario: explicit staging guard
    Tool: powershell
    Steps: Search strategy for `git add -A`.
    Expected: No use of `git add -A`; only explicit file staging examples.
    Evidence: .omo/evidence/stom-reorg-20260618/split-commit-pr-strategy.md

  Scenario: worktree separation
    Tool: powershell
    Steps: Search strategy for `wt-dev` and `wt-webbt`.
    Expected: Both are present with separate responsibilities.
    Evidence: .omo/evidence/stom-reorg-20260618/split-commit-pr-strategy.md
  ```

  **Commit**: YES | Message: `docs(운영): 연구와 대시보드 PR 분리 전략 정리` | Files: split strategy

## Final Verification Wave

- [x] F1. Plan Compliance Audit

  Confirm every task has references, acceptance criteria, QA scenarios, and commit guidance. Confirm all plan outputs live under `.omo/evidence/stom-reorg-20260618/` or dated docs.

- [x] F2. Automated Verification

  Run:

  ```powershell
  python -m json.tool .omo/evidence/stom-reorg-20260618/research-registry.json
  git diff --check
  git status --short -- _database/ _database_v3k_shadow/ _log/ backup/ ":(glob)**/*.db" backtest/graph/ .omx/reports/ ":(glob)v3k_settings*.json" _v3k_sidecar/v3k_gui_settings.json
  python scripts/verify_nonrelease_sync.py
  cd ai_strategy_loop/dashboard/webui-build
  node build-app.mjs
  node track-z-harness.mjs
  node check-missing-imports.mjs
  cd C:\System_Trading\STOM\STOM_V.wt-dev
  python -m pytest tests/unit/dashboard/test_research_records.py tests/unit/dashboard/test_evolution_gui_parity.py tests/unit/dashboard/test_research_records_frontend.py -q
  python -m pytest tests/unit/dashboard/test_no_duplicate_globals.py tests/unit/dashboard/test_no_missing_cross_module_imports.py -q
  ```

  If full unit is run, record the known baseline failure set separately and require no new failures.

- [x] F3. Real Manual QA

  Start a temporary dashboard server:

  ```powershell
  python -m uvicorn ai_strategy_loop.dashboard.app:app --host 127.0.0.1 --port 8793
  curl.exe -i http://127.0.0.1:8793/ui/
  curl.exe -i http://127.0.0.1:8793/research_records
  curl.exe -i "http://127.0.0.1:8793/evolution_gui_parity?run_id=&gen_no=-1"
  curl.exe -i http://127.0.0.1:8793/research_docs
  ```

  Capture browser screenshots or HTML dumps for evolution, backtest, simulation, lab, pro, verdict, and process.

- [x] F4. Scope Fidelity Check

  Confirm:
  - No protected runtime paths modified.
  - No `backtest.py` changes included.
  - No live strategy promotion/export/final approval invoked.
  - `STOM_Version_2U_C-ai-strategy-loop` not mutated.
  - Dashboard-only work remains separable from research evidence work.
  - Protected-path status command is captured with recursive DB pathspec and `_v3k_sidecar/v3k_gui_settings.json`.

## Commit Strategy

Suggested commit/PR groups after execution:

1. `docs(운영): AI 연구 브랜치 파생 관계 지도화`
   - Files: branch map, replay strategy, safety snapshot docs.
2. `docs(연구): 조건식 연구 정본 레지스트리와 네이밍 규칙 추가`
   - Files: research registry, naming taxonomy, current-state summary.
3. `docs(연구): 증거 계보와 연구 운영 프로세스 정립`
   - Files: lineage rules, management process.
4. `docs(대시보드): 정보구조와 중복 기능 전수 감사`
   - Files: dashboard inventory, duplicate audit.
5. `docs(대시보드): 시각 오류와 QA 매트릭스 정리`
   - Files: visual/error audit, QA matrix.
6. `feat/dashboard` or `fix/dashboard` later PR in `wt-webbt`
   - Files: aliases, evidence badges, latest update_log indexing, UI labels, tests, rebuilt bundle.

Never stage with `git add -A`; stage explicit files per group.

## Success Criteria

- The user can answer “what changed since `STOM_Version_2U_C-ai-strategy-loop`?” from one branch map.
- The user can answer “what is the next official research action?” from the registry and OOS queue.
- The user can answer “what is this long condition name?” from display aliases and dashboard labels.
- The user can answer “is this official OOS or just CSV reanalysis?” from evidence badges.
- Future agents can run research without losing context because every run has preregistration, raw evidence, summary, dashboard card, and next action.
- Dashboard improvements proceed from a complete IA/duplicate/visual/error audit rather than ad hoc fixes.
- The plan remains compatible with 2U_C nonrelease and V3K protected gate constraints.
