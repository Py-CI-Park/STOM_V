# Condition Research End-to-End Master Roadmap 20260606

## TL;DR
> **Summary**: Create and maintain a single master roadmap for STOM condition discovery, covering generation, backtest, analysis, feedback, validation, wiki, and dashboard visibility. This plan also defines the required progress-reporting format for all future work.
> **Goal**: Move toward human-level or human-surpassing condition research without overclaiming. Research can use loose or disabled OOS to discover ideas, but any human-level claim remains blocked until strict frozen validation passes.
> **Deliverables**:
> - Master roadmap status table and page-progress table.
> - Change-control rule requiring explicit user consent for roadmap decision changes.
> - Reporting template for every future development update.
> - Integrated backlog for dashboard pages, generation lanes, analysis, feedback, validation, and wiki.
> **Critical Path**: M0/M1 governance -> current P2 bounded preflight -> dashboard visibility fixes -> analysis persistence -> recent-weighted research -> strict promotion validation.

## Context

The user wants the AI and compute process to replace much of the human condition-research labor:

```text
human idea / chart / order-book / condition edit
-> condition expression
-> backtest
-> result analysis
-> variable/time/market-cap insight
-> condition revision
-> repeated discovery
-> good candidate documentation
-> frozen validation before any claim
```

Current canonical inputs:

- `docs/AGENT_HANDOFF.md`
- `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`
- `.omo/plans/tick-human-like-research-criteria-dashboard-20260605.md`
- Supporting: `.omo/plans/condition-research-rereview-20260603.md`
- Supporting: `docs/update_log/2026-06-03_tick_program_complete_handoff.md`

Current evidence summary:

- TICK T0-T4 closed-loop infrastructure exists: wide tick generation, time/return analysis, BackFinder-derived seeds, time-window measurement, and loser-segment feedback.
- A real toggle-ON multi-year candidate did not pass fixed 2022/2026 OOS. This is an honest rejection, not proof that the research direction is useless.
- The active detailed plan `.omo/plans/tick-human-like-research-criteria-dashboard-20260605.md` reframed research around loose human-like discovery criteria.
- Active detailed progress: P0 complete, P1 complete, P2 partial, P3-P7 pending.
- Human-level or seed-superior claim is not proven.

## Metis Review Addressed

Metis found no hard contradiction, but identified gaps that this plan resolves:

- Define "page" as both `.omo/plans` execution plans and dashboard UI pages/panels.
- Define roadmap change control: progress/status/evidence updates are routine; changes to stage scope, order, guardrails, or acceptance criteria require explicit user consent.
- Define a fixed progress-report template and metric set.
- Keep analysis persistence in local research state, never in production DB/protected paths.
- Treat existing backend routes as insufficient until UI/browser behavior and evidence are verified.
- Keep P2 partial until bounded `09:00..09:20` CSV+metrics exists.
- Mark strict promotion validation as blocked until frozen candidate, fixed OOS, slippage, PBO/DSR, and no-reselection evidence exist.

## Definitions

### OOS

OOS means Out Of Sample. It is an unseen exam period that was not used to select, tune, or reselect the strategy.

OOS does not mean every year must be profitable. A strategy can be worth studying if the full-period curve is upward, recent behavior is strong, and drawdown/trade count are acceptable.

### Research vs Claim

| Tier | Purpose | OOS Mode | Result Meaning |
|---|---|---|---|
| `research_continue` | Find ideas worth further study | `disabled` or `advisory` allowed | Research-only, no human-level claim |
| `promotion_claim` | Claim seed/human-level superiority | `promotion_only` fixed OOS | Claim possible only if all strict gates pass |

### Gen

`gen` means generation in the evolving strategy loop. It is related to evolutionary search, but the dashboard must explain the exact local process as "AI condition generation attempt number N" unless a specific genetic algorithm operator is being shown.

## Guardrails

Must preserve:

- No official backtest engine edits.
- No hard-gate edits to promotion/scoring contracts.
- No `backtest/graph` edits.
- New toggles default OFF.
- No production strategy export, no `final_approval`, no `export_winner`.
- No live broker, KHOPENAPI, order wiring, or V3K gate advancement.
- No blanket `taskkill /F /IM python.exe`; use PID-scoped reuse/shutdown only.
- No writes to `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`, or `_v3k_sidecar/v3k_gui_settings.json`.
- OOS-disabled or OOS-advisory research results cannot be called human-level proof.

Allowed writes for this roadmap work:

- `.omo/plans/*`
- `.omo/evidence/*`
- Dated docs under `docs/research/` or `docs/update_log/` when explicitly part of execution.
- Local research-only state paths only when a later implementation task defines the exact path and verifies protected-path status.

## Change Control

Routine updates that do not require extra user consent:

- Marking a step complete/partial/blocked.
- Adding evidence links.
- Adding observed metrics from a run.
- Recommending the next command.

Master roadmap changes that require explicit user consent:

- Changing stage order.
- Adding/removing a major stage.
- Weakening or strengthening claim criteria.
- Changing protected-path, live-trading, export, or OOS guardrails.
- Reclassifying a research-only result as a promotion/human-level result.

Required consent phrase:

```text
마스터 로드맵 변경 승인: <변경 요약>
```

Without that phrase, executors may draft a proposed change but must not modify the approved roadmap decision sections.

## Required Future Report Format

Every future development report must include these sections:

### 1. Master Roadmap Progress

| Stage | Status | Progress | Current Evidence | Blocker / Next Unlock |
|---|---|---:|---|---|
| M0 Baseline | partial | 70% | handoff/docs exist | fresh execution snapshot needed |
| M1 Governance | partial | 30% | this plan defines rules | execute/start-work to create status artifacts |
| M2 Dashboard Visibility | partial | 45% | dashboard exists; routes/UI need QA | repair 404/stale panels |
| M3 Generation Families | partial | 35% | T0-T4 plus P2 partial | bounded CSV+metrics |
| M4 Bounded Backtest Preflight | pending | 20% | timeout root cause known | run capped preflight |
| M5 Quant Analysis | partial | 30% | T1/correlation work exists | persisted analysis schema/UI |
| M6 Feedback/Wiki Loop | partial | 30% | T4 exists | prompt/history/wiki integration |
| M7 Recent-Weighted Research | pending | 10% | criteria layer exists | stable preflight and visibility |
| M8 Strict Promotion Validation | blocked | 15% | last candidate rejected | frozen candidate plus PBO/DSR/slippage |
| M9 Wiki/Knowledge Base | partial | 20% | docs exist; wiki 404 reported | dashboard wiki/API repair |
| M10 Human Comparison | partial | 25% | screenshots/docs exist | numeric extraction and verdict card |
| M11 Operating Loop | pending | 5% | concept only | user-selected after M7/M8 evidence |

### 2. Current Page Detailed Progress

For the current active page plan:

| Page / Plan | Step | Status | Evidence | Next |
|---|---|---|---|---|
| `tick-human-like-research-criteria-dashboard-20260605` | P0 safety/dashboard baseline | complete | prior evidence | maintain |
| same | P1 OOS/criteria | complete | unit/evidence from prior work | maintain |
| same | P2 time x market-cap buy | partial | plumbing/tests pass | bounded CSV+metrics |
| same | P3 sell generation | pending | none yet | study existing sell forms |
| same | P4 live code/diff/prompt/history | pending | 404 reported | repair and browser QA |
| same | P5 CSV analysis persistence/UI | pending | correlation ideas exist | schema/API/UI |
| same | P6 glossary/tooltips | pending | criteria text exists | dashboard explanations |
| same | P7 bounded research run | pending | blocked by P2/P4/P5 | capped run |
| same | Final | pending | none | verification/handoff |

For dashboard UI pages/panels:

| Dashboard Page / Panel | Current Known State | Required Next State |
|---|---|---|
| Engine status/progress/logs | insufficient progress/log/settings visibility | show progress, ETA, elapsed, CPU, tick/min, config, logs |
| Strategy inspector | `strategy_diff` HTTP 404 reported | graceful code/diff for active buy/sell and stale states |
| Fitness/equity chart | prior strategy curve unclear | clearer color/legend, period labels, score explanation |
| Hall of Fame | total profit sort and horizontal scroll missing | add profit sort and horizontal scan usability |
| Phase detail | "waiting for live data" unclear | explain feature purpose and show stale/empty state |
| Research Wiki | query HTTP 404 reported | markdown/wiki entries with evidence links |
| AI Context Pack | HTTP 404 reported | show prompt, state, config, last result, copyable context |
| Run Compare console | lacks enough metrics | profit, return, MDD, trades, time, years, OOS mode |
| Analysis/heatmaps | partial ideas/modules | variable/time/market-cap heatmaps and histograms |

### 3. Current Performance Status

Always separate:

- Infrastructure result: what tooling now works.
- Research candidate result: best current loose research candidate metrics.
- Strict promotion result: whether fixed OOS/slippage/PBO/DSR/no-reselection support a claim.

Minimum metrics:

- period and years covered
- OOS mode
- total profit
- total return
- MDD
- trade count
- max/current holdings interpretation
- win-day ratio
- payoff
- recent-weighted score
- 2024, 2025, available 2026 split
- fixed 2022/2026 OOS if used
- seed/human-reference comparison status

### 4. Next Command

Always include:

- Recommended command.
- Why this command is next.
- What it should prove or unlock.
- What must not be claimed yet.

## End-to-End Master Process

```text
M0 canonical safety baseline
-> M1 master roadmap and consent governance
-> M2 always-on dashboard/process visibility
-> M3 condition generation families
-> M4 bounded backtest preflight
-> M5 quantitative result analysis
-> M6 feedback into prompts/conditions/wiki
-> M7 recent-weighted exploratory research
-> M8 frozen strict promotion validation
-> M9 wiki and condition knowledge base
-> M10 human-reference comparison report
-> M11 operating loop / walk-forward / regime experts
```

## Work Objectives

### Core Objective

Create a decision-complete master roadmap that lets future agents continue condition discovery in a disciplined way: visible dashboard, auditable evidence, loose discovery criteria, strict claim criteria, and user-approved roadmap changes only.

### Deliverables

- `.omo/plans/condition-research-end-to-end-master-roadmap-20260606.md`
- `.omo/evidence/condition-research-end-to-end-master-roadmap-20260606/roadmap-status.md`
- `.omo/evidence/condition-research-end-to-end-master-roadmap-20260606/page-progress.md`
- `.omo/evidence/condition-research-end-to-end-master-roadmap-20260606/report-template.md`
- Optional dated docs only if execution reaches final handoff.

### Definition of Done

- Master roadmap has an up-to-date stage progress table.
- Active page plan progress is integrated.
- Dashboard page/panel backlog is integrated.
- Reporting template is written and reusable.
- Consent protocol is explicit.
- Next command is clear.
- No source code is edited by this planning work.
- Protected-path status is recorded.

## Verification Strategy

- Tests-after for documentation and command correctness only.
- No runtime backtest is required to complete this roadmap plan.
- Later implementation tasks must run their own unit/UI/backtest checks.
- Use `PYTHONUTF8=1` for Korean text verification when needed.
- Browser/dashboard checks must be real UI checks when a dashboard page is claimed complete.
- Evidence goes under `.omo/evidence/condition-research-end-to-end-master-roadmap-20260606/`.

## Dependency Matrix

| Task | Depends On | Blocks |
|---|---|---|
| 1. Safety and canonical inventory | none | 2,3 |
| 2. Master roadmap status artifact | 1 | 3,10 |
| 3. Page progress registry | 1,2 | 4,5,6,7,10 |
| 4. Dashboard visibility backlog | 3 | 7,8 |
| 5. Generation lane map | 3 | 8 |
| 6. Bounded preflight gate map | 3,5 | 8 |
| 7. Analysis/wiki/feedback map | 3,4,6 | 8,10 |
| 8. Recent research and promotion gates | 4,5,6,7 | 9 |
| 9. Human comparison verdict framework | 8 | 10 |
| 10. Final roadmap handoff | 2,3,7,9 | final |

## TODOs

- [ ] 1. Capture Safety And Canonical Inventory

  **Do**:
  - Record branch, HEAD, dirty status, protected-path status, and active dashboard URL if running.
  - Confirm canonical refs exist.
  - Record current dirty worktree as pre-existing; do not revert or stage unrelated changes.

  **References**:
  - `AGENTS.md`
  - `docs/AGENT_HANDOFF.md`
  - `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`
  - `.omo/plans/tick-human-like-research-criteria-dashboard-20260605.md`

  **Acceptance**:
  - Evidence file records branch/HEAD/status.
  - Protected-path check is recorded.
  - No source files are changed.

  **QA Scenarios**:
  ```text
  Scenario: clean inventory
    Steps: Run git status, branch, HEAD, protected-path status.
    Expected: Evidence file classifies dirty files as pre-existing or roadmap artifacts.

  Scenario: protected path dirty
    Steps: If protected paths appear, stop and report blocker.
    Expected: No protected path is written.
  ```

  **Commit**: NO unless user explicitly asks. If committed later, use Korean title/body.

- [ ] 2. Create Master Roadmap Status Artifact

  **Do**:
  - Write a status artifact with M0-M11 stages, progress, evidence, blockers, and next unlock.
  - Include the change-control consent rule.
  - Distinguish routine status updates from roadmap decision changes.

  **References**:
  - This plan.
  - `docs/AGENT_HANDOFF.md`
  - `.omo/plans/tick-human-like-research-criteria-dashboard-20260605.md`

  **Acceptance**:
  - `roadmap-status.md` exists.
  - M0-M11 rows exist.
  - Consent phrase is included.
  - Human-level claim remains blocked.

  **QA Scenarios**:
  ```text
  Scenario: status table completeness
    Steps: Inspect roadmap-status.md.
    Expected: All M0-M11 stages have status, progress, evidence, and blocker/next unlock.

  Scenario: change-control clarity
    Steps: Inspect consent section.
    Expected: Stage/order/criteria/guardrail changes require explicit consent; routine progress does not.
  ```

  **Commit**: NO unless user explicitly asks.

- [ ] 3. Integrate Current Page And Dashboard Page Progress

  **Do**:
  - Create `page-progress.md`.
  - Include the active `.omo/plans/tick-human-like-research-criteria-dashboard-20260605.md` P0-P7 status.
  - Include dashboard UI pages/panels: engine status, strategy inspector, fitness/equity chart, hall of fame, phase detail, research wiki, AI context pack, run compare, analysis heatmaps.
  - Preserve P2 as partial until bounded CSV+metrics exists.

  **References**:
  - `.omo/plans/tick-human-like-research-criteria-dashboard-20260605.md`
  - `ai_strategy_loop/dashboard/frontend/`
  - `ai_strategy_loop/dashboard/app.py`

  **Acceptance**:
  - Page progress table exists.
  - Backend route existence is not treated as UI completion.
  - Reported 404 items are listed as required repairs.

  **QA Scenarios**:
  ```text
  Scenario: active page status
    Steps: Compare page-progress.md with the active plan.
    Expected: P0/P1 complete, P2 partial, P3-P7 pending.

  Scenario: dashboard panel status
    Steps: Inspect dashboard rows.
    Expected: 404/stale/unclear panels have required next state.
  ```

  **Commit**: NO unless user explicitly asks.

- [ ] 4. Define Dashboard Always-On And Observability Backlog

  **Do**:
  - Define how future executors should start/reuse dashboard at `http://127.0.0.1:8770/ui/`.
  - If port conflict occurs, use a new port and report it; do not blanket-kill Python.
  - Require visible backtest progress, ETA, elapsed time, engine settings, CPU count, tick/min mode, logs, config, and period/year labels.
  - Include fixes for total profit sort, Hall of Fame horizontal scroll, strategy diff 404, wiki 404, AI context 404, unclear phase-detail "live data waiting", and score/glossary explanations.

  **References**:
  - `ai_strategy_loop/dashboard/app.py`
  - `ai_strategy_loop/dashboard/frontend/`
  - `tests/unit/test_dashboard_*`

  **Acceptance**:
  - Backlog says what must be visible on the dashboard before long runs.
  - Dashboard health and browser/UI verification are required before claiming complete.
  - Korean copy/rendering must be checked.

  **QA Scenarios**:
  ```text
  Scenario: dashboard reuse
    Steps: Check health endpoint or UI status.
    Expected: Existing server reused if correct; PID-scoped action only if needed.

  Scenario: UI completion
    Steps: Browser smoke or Playwright screenshot for changed page.
    Expected: No blank UI, no 404 panels, no overlapping text.
  ```

  **Commit**: NO in this roadmap task; later implementation commits should be small and Korean.

- [ ] 5. Define Condition Generation Lane Map

  **Do**:
  - Map buy generation lanes:
    - 5-minute buckets from `09:00..09:20` first.
    - Optional extension to `09:30` only after bounded evidence.
    - Dynamic market-cap bands from DB/segment evidence.
    - Variable range and histogram-informed filters.
    - BackFinder/band/few-shot lanes.
  - Map sell generation lanes:
    - Existing STOM sell forms.
    - Profit-taking, stop-loss, trailing give-back, upper-tail/lower-tail, trend break, hold-time exits.
  - Include trade-count and simultaneous-hold diagnostics, especially cases where holdings show `0/1` or seed holdings look suspicious.

  **References**:
  - `utility/ai_agent/strategy.txt`
  - `utility/ai_agent/rules.txt`
  - `ai_strategy_loop/brain/time_cap_bucket.py`
  - `ai_strategy_loop/brain/prompt.py`
  - `ai_strategy_loop/brain/generator.py`
  - Existing strategy DB forms, read-only only.

  **Acceptance**:
  - Each lane has input evidence, generation rules, pre-save checks, and unlock criteria.
  - Time/cap boundaries remain configurable.
  - Branches are kept small enough to avoid known timeout patterns.

  **QA Scenarios**:
  ```text
  Scenario: generation lane table
    Steps: Inspect generation lane map.
    Expected: Buy, sell, time, market-cap, variable-range, and BackFinder lanes are all listed.

  Scenario: timeout guard
    Steps: Inspect branch-size/preflight requirements.
    Expected: No lane can expand to 09:30 or full multi-year run without bounded evidence.
  ```

  **Commit**: NO in this roadmap task.

- [ ] 6. Define Bounded Backtest Preflight Gate

  **Do**:
  - Define the exact unlock sequence before long runs:
    - short period
    - `09:00..09:20`
    - capped generation count
    - capped wall time
    - explicit engine settings
    - CSV output
    - metrics card
  - Require progress display matching GUI expectations.
  - Require process logs and config capture.
  - Do not run 2023-2026 full research before bounded CSV+metrics and dashboard visibility are stable.

  **References**:
  - `.omo/plans/tick-human-like-research-criteria-dashboard-20260605.md`
  - `ai_strategy_loop/controller/loop.py`
  - `ai_strategy_loop/controller/progress_contract.py` if present
  - `cli/runner.py`

  **Acceptance**:
  - Preflight gate states exact minimum evidence.
  - Failure/timeout handling is defined.
  - OOS disabled/advisory labels are shown if used.

  **QA Scenarios**:
  ```text
  Scenario: bounded run ready
    Steps: Inspect preflight checklist.
    Expected: command/config, period, caps, CSV path, metrics, and logs are specified before execution.

  Scenario: timeout
    Steps: Inspect timeout policy.
    Expected: Timeout becomes evidence and next diagnosis, not a silent hang or blanket kill.
  ```

  **Commit**: NO in this roadmap task.

- [ ] 7. Define Quant Analysis, Feedback, And Wiki Loop

  **Do**:
  - Define local research-only analysis persistence for:
    - variable correlations
    - compound feature interactions
    - time x market-cap x return matrices
    - histograms
    - MFE/MAE
    - payoff
    - win/loss and win-day ratio
    - total profit and return
  - Define how analysis feeds the next generation prompt.
  - Define wiki entries for good conditions, failed attempts, prompt decisions, human-reference screenshots, and image-derived notes.
  - Mark screenshots as reference only unless converted into audited numeric evidence.

  **References**:
  - `docs/research/2026-06-04_condition_research_rereview_human_reference_graphs.md`
  - `ai_strategy_loop/fitness/correlation.py`
  - `ai_strategy_loop/fitness/correlation_profile.py` if present
  - `ai_strategy_loop/dashboard/frontend/research-lab.jsx`

  **Acceptance**:
  - Persistence target is research-only and not `_database/`.
  - Dashboard and docs share evidence IDs.
  - Wiki/query/API failure states are handled gracefully.

  **QA Scenarios**:
  ```text
  Scenario: analysis schema
    Steps: Inspect proposed schema or artifact table.
    Expected: All requested metrics have a storage/display owner.

  Scenario: feedback traceability
    Steps: Pick one variable insight.
    Expected: It can be traced to a prompt change, strategy diff, and result card.
  ```

  **Commit**: NO in this roadmap task.

- [ ] 8. Define Recent-Weighted Research And Strict Promotion Gates

  **Do**:
  - Define loose recent-weighted research sequence:
    - prioritize 2024, 2025, and available 2026.
    - allow losing years if full-period curve is upward and recovery/drawdown/trade count are acceptable.
    - compare against seed and human references only as research guidance.
  - Define strict promotion sequence:
    - freeze candidate ID, config, code, prompt, and selected period.
    - no reselection after OOS.
    - fixed 2022/2026 OOS where available.
    - slippage status.
    - PBO/DSR advisory or implemented status.
    - promotion card.

  **References**:
  - `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`
  - `ai_strategy_loop/fitness/research_criteria.py` if present
  - `ai_strategy_loop/fitness/promotion_diagnostics.py` if present

  **Acceptance**:
  - Research pass cannot become claim pass automatically.
  - Strict claim remains blocked until all promotion evidence exists.
  - OOS disabled mode is allowed only for discovery and labeled clearly.

  **QA Scenarios**:
  ```text
  Scenario: loose research pass
    Steps: Evaluate a hypothetical upward full-period result with one losing year.
    Expected: research_continue can pass, promotion_claim remains false.

  Scenario: strict promotion block
    Steps: Remove slippage/PBO/DSR/no-reselection evidence.
    Expected: promotion_claim is blocked.
  ```

  **Commit**: NO in this roadmap task.

- [ ] 9. Define Human Reference Comparison Framework

  **Do**:
  - Compare AI candidates to:
    - seed `Tick_902` or current live/reference seed.
    - human good-result screenshots and documented metrics.
    - adaptive regime/portfolio variants if later created.
  - Separate qualitative screenshot similarity from numeric proof.
  - Include image-to-text/number extraction as a future research support task, not proof by itself.

  **References**:
  - `docs/reference/STOM_Good_Results/`
  - `docs/research/2026-06-04_condition_research_rereview_human_reference_graphs.md`
  - `docs/AGENT_HANDOFF.md`

  **Acceptance**:
  - Report has separate rows for seed, human reference, AI research candidate, and strict candidate.
  - Human-level verdict has one of: not tested, research promising, strict rejected, strict pass.
  - No screenshot-only human-level claim.

  **QA Scenarios**:
  ```text
  Scenario: screenshot reference
    Steps: Inspect verdict card.
    Expected: screenshot graph is labeled reference-only unless numeric extraction is audited.

  Scenario: seed comparison
    Steps: Inspect metrics table.
    Expected: seed comparison uses same period/mode labels or clearly marks mismatch.
  ```

  **Commit**: NO in this roadmap task.

- [ ] 10. Finalize Roadmap Handoff And Next Command Protocol

  **Do**:
  - Write final summary with:
    - master roadmap progress table
    - current page progress table
    - current performance status
    - next recommended command
    - reason
    - what is still not proven
  - Recommend exactly one next `$start-work` command unless high-accuracy review is more appropriate.
  - Keep master roadmap modification policy visible.

  **References**:
  - This plan.
  - `.omo/evidence/condition-research-end-to-end-master-roadmap-20260606/*`

  **Acceptance**:
  - Future agents can continue from one command.
  - User can see current status without rereading all history.
  - No source/runtime/protected edits are part of this roadmap-only task.

  **QA Scenarios**:
  ```text
  Scenario: final report completeness
    Steps: Inspect final response and evidence files.
    Expected: It includes master progress, page progress, results, next command, reason, and guardrails.

  Scenario: next command clarity
    Steps: Inspect recommended command.
    Expected: It is executable and tied to the next unlock.
  ```

  **Commit**: NO unless user explicitly asks.

## Recommended Next Commands

Option A, execute the roadmap artifacts and reporting discipline:

```text
$start-work condition-research-end-to-end-master-roadmap-20260606
```

Option B, audit this master roadmap before execution:

```text
high accuracy review
```

After Option A completes, the likely next implementation command should remain the active detailed plan unless evidence changes:

```text
$start-work tick-human-like-research-criteria-dashboard-20260605
```

Reason: P2 bounded `09:00..09:20` CSV+metrics is the next practical unlock before expanding to sell generation, dashboard full visibility, analysis persistence, or 2024-2026 broad research.
