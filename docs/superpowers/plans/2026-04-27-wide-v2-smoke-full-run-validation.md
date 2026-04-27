# Wide v2 Smoke and Full Run Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify the merged Wide v2 optimizer with a small smoke run first, then run `candidate_count=10` validation only when runtime and output gates are acceptable.

**Architecture:** Do not change optimizer code in this step. Execute the existing `stom_backtest.py discovery optimize-wide-v2` CLI, inspect JSON/report artifacts, and decide whether the next branch should be WFO validation or optimizer recovery/design refinement.

**Tech Stack:** Python 3.11, PowerShell, argparse CLI, existing STOM `cli.research_optimizer`, existing runtime JSON/report writers, pytest.

---

## Scope Check

This plan is an execution validation plan, not a new feature implementation. The Wide v2 optimizer was already merged in PR #26. This step proves whether the merged CLI can run on real STOM backtest data and whether the generated candidates are diverse and useful enough to hand off to WFO later.

Included:

- CLI parser and optimizer import smoke verification.
- `candidate_count=2`, `max_rounds=2` smoke execution.
- Smoke artifact inspection for status, stop reason, final best candidate, leaderboard, and report path.
- Runtime budget estimation before a larger run.
- `candidate_count=10` validation run, with a guarded `max_rounds=3` path only when smoke timing makes that realistic.
- Result review and next-command decision.

Excluded:

- Code changes to candidate generation, scoring, WFO, or GUI.
- Direct WFO execution.
- Live trading or strategy approval.
- Committing generated `backtest/temp`, `backtest/csv`, or `backtest/graph` artifacts.
- Editing `utility/strategy.db`.

## File Structure

- Create during this planning branch: `docs/superpowers/plans/2026-04-27-wide-v2-smoke-full-run-validation.md`
  - Owns the execution plan and gates.
- Generated during later execution, not committed by default: `backtest/temp/wide_v2_smoke_20260427*.json`
  - Runtime JSON, summary JSON, leaderboard JSON, and per-round JSON for the smoke run.
- Generated during later execution, not committed by default: `backtest/temp/wide_v2_candidate_count_10_20260427*.json`
  - Runtime JSON, summary JSON, leaderboard JSON, and per-round JSON for the larger validation run.
- Generated during later execution and reviewed for possible commit: `docs/research/condition_research/pilot_logs/2026-04-27_wide_v2_smoke_summary.md`
  - Optimizer Markdown report for the smoke run.
- Generated during later execution and reviewed for possible commit: `docs/research/condition_research/pilot_logs/2026-04-27_wide_v2_candidate_count_10_summary.md`
  - Optimizer Markdown report for the larger validation run.
- Create during later execution if analysis is needed: `docs/research/condition_research/pilot_logs/2026-04-27_wide_v2_smoke_full_run_validation_review.md`
  - Human-readable Korean review of the smoke/full run result, runtime, candidate diversity, final best candidate, and next step.
- Create during later execution PR: `docs/pr/2026-04-27_wide_v2_smoke_full_run_validation_pr.md`
  - Korean PR report for the execution-result branch if report artifacts are committed.

Protected paths:

- Do not stage `utility/strategy.db`.
- Do not stage `backtest/graph/`.
- Do not stage `backtest/temp/`.
- Do not stage `backtest/csv/`.
- Use explicit `git add` paths only.

---

### Task 1: Baseline Sanity Check

**Files:**
- Read only: `cli/subcommands.py`
- Read only: `cli/research_optimizer.py`
- Read only: `cli/research_optimizer_state.py`
- Read only: `tests/unit/test_subcommands.py`
- Read only: `tests/unit/test_research_optimizer.py`

- [ ] **Step 1: Confirm the branch and protected untracked artifact state**

Run:

```powershell
git status --short --branch
```

Expected:

```text
## STOM_Version_2U_C...origin/STOM_Version_2U_C
?? backtest/graph/
```

If running from a feature branch created for execution, the branch name may differ. `backtest/graph/` may remain untracked and must not be staged.

- [ ] **Step 2: Confirm the optimizer command is discoverable**

Run:

```powershell
python .\stom_backtest.py discovery optimize-wide-v2 --help
```

Expected:

```text
usage:
...
--candidate-count
--max-rounds
--runtime-output
--leaderboard-output
--summary-output
--report-path
```

If this fails with parser/import errors, stop the run and create a recovery branch instead of starting a real backtest.

- [ ] **Step 3: Run the focused optimizer unit tests before real runtime**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_optimizer_state.py `
  tests/unit/test_research_optimizer.py `
  tests/unit/test_research_optimizer_report.py `
  tests/unit/test_subcommands.py `
  -q
```

Expected:

```text
113 passed
```

If the count changes because new tests were added later, the expected condition is that all selected tests pass with zero failures.

---

### Task 2: Smoke Run With `candidate_count=2`

**Files:**
- Generated: `backtest/temp/wide_v2_smoke_20260427.json`
- Generated: `backtest/temp/wide_v2_smoke_20260427_summary.json`
- Generated: `backtest/temp/wide_v2_smoke_20260427_leaderboard.json`
- Generated: `backtest/temp/wide_v2_smoke_20260427_round001.json`
- Generated: `backtest/temp/wide_v2_smoke_20260427_round002.json`
- Generated: `docs/research/condition_research/pilot_logs/2026-04-27_wide_v2_smoke_summary.md`

- [ ] **Step 1: Start the smoke run and record wall-clock time**

Run:

```powershell
$smokeStart = Get-Date
python .\stom_backtest.py discovery optimize-wide-v2 `
  --name WideV2Smoke_20260427 `
  --base-buy-strategy WideV1Final_B_20260425 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --seed-candidate WideV1Final_B_20260425 `
  --seed-expression "66.999 <= ?쒓?珥앹븸 < 2_580 and ?깅씫??> 4.83" `
  --iteration-v2-trade-amount-feature "B_?깅씫??" `
  --start 20250101 `
  --end 20251231 `
  --candidate-count 2 `
  --max-rounds 2 `
  --candidate-timeout 900 `
  --runtime-output backtest\temp\wide_v2_smoke_20260427.json `
  --leaderboard-output backtest\temp\wide_v2_smoke_20260427_leaderboard.json `
  --summary-output backtest\temp\wide_v2_smoke_20260427_summary.json `
  --report-path docs\research\condition_research\pilot_logs\2026-04-27_wide_v2_smoke_summary.md
$smokeEnd = Get-Date
$smokeElapsed = $smokeEnd - $smokeStart
$smokeElapsed
```

Expected:

```text
Days              : 0
Hours             : 0
Minutes           : the elapsed minute value printed by PowerShell
...
```

The run can return `status=ok` or a structured `status=error`. An unhandled Python traceback is a blocker and should become a recovery branch.

- [ ] **Step 2: Inspect the smoke summary JSON**

Run:

```powershell
$smoke = Get-Content backtest\temp\wide_v2_smoke_20260427_summary.json -Raw | ConvertFrom-Json
$smoke | Select-Object status, run_id, stop_reason, completed_round_count, failed_round, failure_phase, failure_message
$smoke.final_best_candidate | Select-Object round_index, candidate_index, strategy_name, adjusted_score, promotion_score
$smoke.wfo_candidate | Select-Object strategy_name, source_round, source_candidate, next_command
```

Expected pass condition:

```text
status                 ok
completed_round_count  1 or 2
failure_phase          empty
final_best_candidate   present when at least one valid candidate was ranked
wfo_candidate          present when final_best_candidate is present
```

Expected structured-stop conditions that are acceptable for diagnosis:

```text
stop_reason = duplicate_rowset_only
stop_reason = insufficient_candidates
stop_reason = no_improvement
```

Unexpected conditions:

```text
status = error with missing failure_phase
failure_phase = optimizer_summary_output_write_failure
failure_phase = optimizer_leaderboard_output_write_failure
failure_phase = optimizer_report_output_write_failure
```

Output write failures are code or filesystem issues and should be fixed before a larger run.

- [ ] **Step 3: Inspect leaderboard size and candidate diversity**

Run:

```powershell
$leaderboard = Get-Content backtest\temp\wide_v2_smoke_20260427_leaderboard.json -Raw | ConvertFrom-Json
$leaderboard.Count
$leaderboard | Select-Object round_index, candidate_index, strategy_name, status, candidate_type, promotion_passed, adjusted_score, trade_count_retention
$leaderboard | Group-Object expression | Select-Object Count, Name
```

Expected pass condition:

```text
leaderboard.Count >= 1
at least one row has status ok
expressions are visible and not all blank
```

If all candidates collapse into the same actual row set, the larger run should not proceed until the result is reviewed.

- [ ] **Step 4: Inspect the generated Markdown report**

Run:

```powershell
Get-Content docs\research\condition_research\pilot_logs\2026-04-27_wide_v2_smoke_summary.md -TotalCount 120
```

Expected report sections:

```text
# Wide v2 optimizer summary
## Run configuration
## Initial baseline
## Round count
## Round summary
## Round best candidates
## Global leaderboard
## Stop reason
## Final best candidate
## WFO handoff
```

The report must state that WFO was not run inside the optimizer loop.

---

### Task 3: Runtime Budget Gate Before `candidate_count=10`

**Files:**
- Read: `backtest/temp/wide_v2_smoke_20260427_summary.json`
- Read: `backtest/temp/wide_v2_smoke_20260427_leaderboard.json`

- [ ] **Step 1: Estimate larger-run time from smoke elapsed time**

Run:

```powershell
$smokeCandidateSlots = 2 * [Math]::Max(1, [int]$smoke.completed_round_count)
$minutesPerSlot = [Math]::Max(1, $smokeElapsed.TotalMinutes / $smokeCandidateSlots)
$estimatedFullRoundMinutes = $minutesPerSlot * 10
$estimatedThreeRoundMinutes = $minutesPerSlot * 10 * 3
[PSCustomObject]@{
  SmokeMinutes = [Math]::Round($smokeElapsed.TotalMinutes, 1)
  MinutesPerCandidateSlot = [Math]::Round($minutesPerSlot, 1)
  EstimatedCandidateCount10OneRoundMinutes = [Math]::Round($estimatedFullRoundMinutes, 1)
  EstimatedCandidateCount10ThreeRoundMinutes = [Math]::Round($estimatedThreeRoundMinutes, 1)
}
```

Expected decision:

```text
If EstimatedCandidateCount10ThreeRoundMinutes <= 120, run candidate_count=10 with max_rounds=3.
If EstimatedCandidateCount10ThreeRoundMinutes > 120 and EstimatedCandidateCount10OneRoundMinutes <= 120, run candidate_count=10 with max_rounds=1 first.
If EstimatedCandidateCount10OneRoundMinutes > 120, do not run the larger validation in this branch; create a runtime-reduction plan.
```

This keeps the next validation aligned with the user's time concern while still testing the full candidate count.

- [ ] **Step 2: Confirm the smoke result is worth scaling**

Run:

```powershell
[PSCustomObject]@{
  Status = $smoke.status
  StopReason = $smoke.stop_reason
  CompletedRounds = $smoke.completed_round_count
  FinalBest = $smoke.final_best_candidate.strategy_name
  WfoCandidate = $smoke.wfo_candidate.strategy_name
  LeaderboardCount = $leaderboard.Count
}
```

Proceed only when:

```text
Status = ok
LeaderboardCount >= 1
StopReason is not duplicate_rowset_only
FinalBest is present
```

If `StopReason=duplicate_rowset_only`, the next step is candidate diversity redesign, not a larger run.

---

### Task 4: Candidate Count 10 Validation Run

**Files:**
- Generated: `backtest/temp/wide_v2_candidate_count_10_20260427.json`
- Generated: `backtest/temp/wide_v2_candidate_count_10_20260427_summary.json`
- Generated: `backtest/temp/wide_v2_candidate_count_10_20260427_leaderboard.json`
- Generated: `backtest/temp/wide_v2_candidate_count_10_20260427_round001.json`
- Generated: `backtest/temp/wide_v2_candidate_count_10_20260427_round002.json` when `max_rounds >= 2`
- Generated: `backtest/temp/wide_v2_candidate_count_10_20260427_round003.json` when `max_rounds >= 3`
- Generated: `docs/research/condition_research/pilot_logs/2026-04-27_wide_v2_candidate_count_10_summary.md`

- [ ] **Step 1: Choose the full-run round count from Task 3**

Use this value:

```powershell
if ($estimatedThreeRoundMinutes -le 120) {
  $fullMaxRounds = 3
} else {
  $fullMaxRounds = 1
}
$fullMaxRounds
```

Expected:

```text
3 when smoke timing supports a complete optimizer validation
1 when only the full candidate set can be verified within the current time budget
```

- [ ] **Step 2: Run the candidate_count=10 validation**

Run:

```powershell
$fullStart = Get-Date
python .\stom_backtest.py discovery optimize-wide-v2 `
  --name WideV2CandidateCount10_20260427 `
  --base-buy-strategy WideV1Final_B_20260425 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --seed-candidate WideV1Final_B_20260425 `
  --seed-expression "66.999 <= ?쒓?珥앹븸 < 2_580 and ?깅씫??> 4.83" `
  --iteration-v2-trade-amount-feature "B_?깅씫??" `
  --start 20250101 `
  --end 20251231 `
  --candidate-count 10 `
  --max-rounds $fullMaxRounds `
  --candidate-timeout 900 `
  --runtime-output backtest\temp\wide_v2_candidate_count_10_20260427.json `
  --leaderboard-output backtest\temp\wide_v2_candidate_count_10_20260427_leaderboard.json `
  --summary-output backtest\temp\wide_v2_candidate_count_10_20260427_summary.json `
  --report-path docs\research\condition_research\pilot_logs\2026-04-27_wide_v2_candidate_count_10_summary.md
$fullEnd = Get-Date
$fullElapsed = $fullEnd - $fullStart
$fullElapsed
```

Expected:

```text
The command exits without an unhandled traceback.
The summary JSON and leaderboard JSON exist.
The Markdown report exists.
```

- [ ] **Step 3: Inspect candidate_count=10 result**

Run:

```powershell
$full = Get-Content backtest\temp\wide_v2_candidate_count_10_20260427_summary.json -Raw | ConvertFrom-Json
$fullLeaderboard = Get-Content backtest\temp\wide_v2_candidate_count_10_20260427_leaderboard.json -Raw | ConvertFrom-Json
$full | Select-Object status, run_id, stop_reason, completed_round_count, failed_round, failure_phase, failure_message
$full.final_best_candidate | Select-Object round_index, candidate_index, strategy_name, adjusted_score, promotion_score
$full.wfo_candidate | Select-Object strategy_name, source_round, source_candidate, next_command
$fullLeaderboard.Count
$fullLeaderboard | Select-Object -First 15 round_index, candidate_index, strategy_name, status, candidate_type, promotion_passed, adjusted_score, trade_count_retention
```

Expected pass condition:

```text
status = ok
completed_round_count >= 1
leaderboard count >= 1
final_best_candidate is present
wfo_candidate is present
failure_phase is blank
```

- [ ] **Step 4: Inspect expression diversity**

Run:

```powershell
$fullLeaderboard | Group-Object expression | Sort-Object Count -Descending | Select-Object Count, Name
$fullLeaderboard | Group-Object candidate_type | Sort-Object Count -Descending | Select-Object Count, Name
```

Expected:

```text
More than one expression group is preferred.
If only one expression group exists, record the result as candidate diversity failure.
Candidate type distribution must be visible for later generator tuning.
```

---

### Task 5: Result Review Document

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-27_wide_v2_smoke_full_run_validation_review.md`
- Read: `docs/research/condition_research/pilot_logs/2026-04-27_wide_v2_smoke_summary.md`
- Read: `docs/research/condition_research/pilot_logs/2026-04-27_wide_v2_candidate_count_10_summary.md`

- [ ] **Step 1: Create the Korean validation review document**

Create `docs/research/condition_research/pilot_logs/2026-04-27_wide_v2_smoke_full_run_validation_review.md` with this structure:

```markdown
# Wide v2 smoke/full run 검증 리뷰

## 목적

Wide v2 자동 개선 루프가 실제 백테스트 실행에서 후보 생성, 후보 백테스트, leaderboard 기록, final best 선정, WFO handoff 후보 기록까지 수행되는지 확인한다.

## 실행 요약

| 구분 | candidate_count | max_rounds | 완료 round | 소요 시간 | status | stop_reason |
| --- | ---: | ---: | ---: | --- | --- | --- |
| smoke | 2 | 2 | Task 2에서 확인한 `smoke.completed_round_count` 값 | Task 2에서 측정한 `$smokeElapsed` 값 | Task 2에서 확인한 `smoke.status` 값 | Task 2에서 확인한 `smoke.stop_reason` 값 |
| candidate_count=10 | 10 | Task 4에서 사용한 `$fullMaxRounds` 값 | Task 4에서 확인한 `full.completed_round_count` 값 | Task 4에서 측정한 `$fullElapsed` 값 | Task 4에서 확인한 `full.status` 값 | Task 4에서 확인한 `full.stop_reason` 값 |

## Smoke 판정

- final_best_candidate: Task 2에서 확인한 `smoke.final_best_candidate.strategy_name` 값
- wfo_candidate: Task 2에서 확인한 `smoke.wfo_candidate.strategy_name` 값
- leaderboard_count: Task 2에서 확인한 `$leaderboard.Count` 값
- 판정: Task 3 gate를 통과하면 `pass`, 통과하지 못하면 `recovery-needed`

## Candidate Count 10 판정

- final_best_candidate: Task 4에서 확인한 `full.final_best_candidate.strategy_name` 값
- wfo_candidate: Task 4에서 확인한 `full.wfo_candidate.strategy_name` 값
- leaderboard_count: Task 4에서 확인한 `$fullLeaderboard.Count` 값
- expression_group_count: Task 4에서 확인한 expression group 개수
- candidate_type_distribution: Task 4에서 확인한 candidate type group 결과
- 판정: Task 4 pass condition을 통과하면 `pass`, 통과하지 못하면 `recovery-needed`

## 퀀트 관점 검토

- 조건식 개선 루프의 목적은 단일 후보를 승인하는 것이 아니라, 백테스트 결과를 기준으로 더 나은 후보를 반복 생성하고 WFO 검증 대상으로 넘기는 것이다.
- final_best_candidate는 실전 채택이 아니며, 다음 단계에서 WFO 또는 OOS 검증을 통과해야 한다.
- 후보 다양성이 낮으면 수익률보다 먼저 생성 규칙을 수정해야 한다.

## CLI 개발 관점 검토

- CLI는 구조화된 JSON과 Markdown report를 남겨야 한다.
- 실패는 traceback보다 `status`, `stop_reason`, `failure_phase`, `failure_message`로 확인 가능해야 한다.
- `backtest/temp`, `backtest/csv`, `backtest/graph`는 실행 산출물이므로 커밋하지 않는다.

## 다음 단계

Task 5 Step 2 decision table에서 선택한 superpowers 명령
```

Before committing, replace every "Task N에서 확인한 ..." sentence with the concrete inspected value so the final review document reads as evidence, not as instructions.

- [ ] **Step 2: Choose the next command**

Use this decision table:

```text
If candidate_count=10 passes and wfo_candidate exists:
  $writing-plans Wide v2 final_best_candidate WFO 검증 계획 작성

If candidate_count=10 stops with duplicate_rowset_only:
  $brainstorming Wide v2 후보 다양성 개선 및 row-set 중복 완화 설계

If runtime exceeds the budget before candidate_count=10 completes:
  $brainstorming Wide v2 실행시간 단축 및 후보 백테스트 병목 개선 설계

If CLI/report output fails:
  $brainstorming Wide v2 runtime output failure recovery 설계
```

Expected recommended command when the run is healthy:

```text
$writing-plans Wide v2 final_best_candidate WFO 검증 계획 작성
```

---

### Task 6: Verification and PR Packaging

**Files:**
- Create: `docs/pr/2026-04-27_wide_v2_smoke_full_run_validation_pr.md`
- Read: `docs/research/condition_research/pilot_logs/2026-04-27_wide_v2_smoke_full_run_validation_review.md`

- [ ] **Step 1: Run unit verification after result documents are prepared**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 2: Run non-release sync verification**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
all OK
```

- [ ] **Step 3: Check whitespace**

Run:

```powershell
git diff --check --ignore-cr-at-eol HEAD
```

Expected:

```text
no output
```

- [ ] **Step 4: Confirm generated protected artifacts are not staged**

Run:

```powershell
git status --short
```

Expected:

```text
M or A only for docs/research/condition_research/pilot_logs/...review/report documents
M or A only for docs/pr/...PR report
?? backtest/graph/
```

Do not stage `backtest/temp`, `backtest/csv`, `backtest/graph`, or `utility/strategy.db`.

- [ ] **Step 5: Write the Korean PR report**

Create `docs/pr/2026-04-27_wide_v2_smoke_full_run_validation_pr.md` with these sections:

```markdown
# Wide v2 smoke/full run 검증 PR 보고서

## 목적

Wide v2 optimizer가 실제 실행에서 후보 백테스트 반복, leaderboard 기록, final best 선정, WFO handoff 후보 생성을 수행하는지 검증한다.

## 전체 방향성

조건식 자동 개선 시스템의 현재 방향은 다음과 같다.

백테스트 실행 -> 결과 기록 -> 후보 성능/다양성 분석 -> 개선 후보 생성 -> 반복 백테스트 -> final best 선정 -> WFO/OOS 검증 -> 운영 후보 판단

## 이번 PR 범위

- smoke 실행 결과
- candidate_count=10 실행 결과
- final_best_candidate 정리
- WFO handoff 가능 여부 판단
- 다음 superpowers 명령 제안

## 제외 범위

- WFO 직접 실행
- 실전 채택
- 새 조건식 생성 알고리즘 변경
- `backtest/temp`, `backtest/csv`, `backtest/graph`, `utility/strategy.db` 커밋

## 검증 결과

Task 6 Step 1의 실제 pytest 결과

Task 6 Step 2의 실제 non-release sync 결과

Task 6 Step 3의 실제 diff check 결과

## 결론

Task 5의 smoke/full run 판정 결과

## 다음 단계

Task 5 Step 2 decision table에서 선택한 superpowers 명령
```

Before committing, replace every "Task N..." sentence with concrete evidence from the run and verification outputs.

- [ ] **Step 6: Commit with explicit staging**

Run:

```powershell
git add `
  docs\research\condition_research\pilot_logs\2026-04-27_wide_v2_smoke_summary.md `
  docs\research\condition_research\pilot_logs\2026-04-27_wide_v2_candidate_count_10_summary.md `
  docs\research\condition_research\pilot_logs\2026-04-27_wide_v2_smoke_full_run_validation_review.md `
  docs\pr\2026-04-27_wide_v2_smoke_full_run_validation_pr.md

git commit -m "Wide v2 실행 검증 결과를 기록한다" -m @"
Wide v2 optimizer가 실제 백테스트 실행에서 smoke와 candidate_count=10 검증을 통과하는지 확인하고, final best 후보와 WFO handoff 판단을 문서화한다.

Constraint: 실행 산출물 중 backtest/temp, backtest/csv, backtest/graph는 커밋하지 않는다
Constraint: final_best_candidate는 실전 승인 후보가 아니라 WFO/OOS 검증 대상이다
Rejected: smoke 없이 candidate_count=10부터 실행 | runtime 실패와 출력 실패를 분리하기 어렵다
Confidence: medium
Scope-risk: narrow
Directive: WFO 단계로 넘어가기 전 candidate diversity와 structured failure metadata를 반드시 확인한다
Tested: python -m pytest tests/unit/ -q
Tested: python scripts/verify_nonrelease_sync.py
Tested: git diff --check --ignore-cr-at-eol HEAD
Not-tested: WFO 검증과 실전 운용 성능
"@
```

Expected:

```text
[feature/wide-v2-smoke-full-run-validation ...] Wide v2 실행 검증 결과를 기록한다
```

---

## Self-Review

- Spec coverage: smoke run, `candidate_count=10` run, runtime budget gate, artifact inspection, result review, PR packaging, and next-command decision are all covered.
- Placeholder scan: The plan uses explicit commands and required document structures. Runtime-dependent report values are described by the exact task output that supplies them, and the execution task requires replacing those descriptions with concrete evidence before commit.
- Type consistency: CLI flags match `discovery optimize-wide-v2`: `--candidate-count`, `--max-rounds`, `--runtime-output`, `--leaderboard-output`, `--summary-output`, `--report-path`, `--iteration-v2-trade-amount-feature`.
- Scope check: The plan does not change candidate generation, WFO, GUI, serial-key behavior, or protected runtime/result paths.
