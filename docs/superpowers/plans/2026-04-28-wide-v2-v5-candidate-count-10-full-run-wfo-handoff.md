# Wide v2 v5 Candidate Count 10 Full Run and WFO Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run Wide v2 v5 with `candidate_count=10`, select the best WFO handoff candidate from real backtest results, and decide the next MVP step.

**Architecture:** Do not change optimizer code in this plan. Execute the existing `stom_backtest.py discovery optimize-wide-v2` CLI with full candidate count, inspect structured JSON/Markdown outputs, write a Korean evidence review, and route to WFO/OOS validation or a focused recovery plan. Use `max_rounds=1` by default because the 2-round smoke already validated loop continuation and next-seed recovery, while the remaining MVP need is full candidate-set WFO handoff selection within a practical runtime budget.

**Tech Stack:** Python 3.11, PowerShell, existing STOM CLI, `cli.research_optimizer`, optimizer JSON/Markdown reports, pytest, git.

---

## Scope Check

This is an execution-validation plan, not a new feature implementation plan.

Included:

- Preflight verification for the current optimizer/report/CLI code.
- Direct `candidate_count=10` full candidate-set run.
- `max_rounds=1` WFO handoff candidate selection path.
- Structured inspection of summary JSON, leaderboard JSON, Markdown report, candidate diversity, and WFO handoff fields.
- Korean full-run review document.
- Commit of curated Markdown evidence only.
- Next superpowers command decision.

Excluded:

- No WFO/OOS execution inside this plan.
- No live-trading approval.
- No v6/v7 design unless this full run fails a gate.
- No optimizer, candidate-generation, GUI, or backtest-engine code changes.
- No broad `cli/` refactor.
- No commit of raw runtime artifacts under `backtest/`.

Protected paths:

- Do not stage `utility/strategy.db`.
- Do not stage `backtest/graph/`.
- Do not stage `backtest/temp/`.
- Do not stage `backtest/csv/`.
- Use explicit `git add` paths only.

## Current Evidence

The immediate predecessor smoke was:

```text
run_id=WideV2V5NextSeedRecoverySmoke_20260428
candidate_count=2
max_rounds=2
status=ok
stop_reason=max_rounds_reached
completed_round_count=2
leaderboard_count=8
elapsed=about 00:56:02
next_seed_selection_status=compatible_fallback
```

Interpretation:

```text
2-round loop continuation: verified
next-seed fallback after invalid round best: verified
full candidate-count WFO handoff selection: not yet verified
WFO/OOS validation: not yet run
```

Fast MVP route:

```text
candidate_count=10 max_rounds=1 full candidate-set run
-> select final_best_candidate and wfo_candidate
-> write evidence review
-> if healthy, plan WFO/OOS validation
-> if unhealthy, design only the failing recovery lane
```

## File Structure

- Read: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_next_seed_recovery_smoke_review.md`
  - Evidence that `candidate_count=2`, `max_rounds=2` no longer stops at `invalid_seed_expression`.
- Generated, do not stage: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428.json`
  - Optimizer runtime output for the full candidate-set run.
- Generated, do not stage: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428_summary.json`
  - Structured final summary used for decision-making.
- Generated, do not stage: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428_leaderboard.json`
  - Full leaderboard used for candidate diversity and WFO handoff review.
- Generated, do not stage: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428_console.txt`
  - Console evidence for runtime diagnostics.
- Generated, do not stage: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428_run_meta.json`
  - Start/end/elapsed/exit-code metadata.
- Commit if generated: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_candidate_count_10_full_run_summary.md`
  - Optimizer Markdown report.
- Create and commit: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_candidate_count_10_full_run_review.md`
  - Korean review of full run result, WFO handoff candidate, and next command.

---

### Task 1: Preflight Verification

**Files:**
- Read only: `cli/research_optimizer.py`
- Read only: `cli/research_optimizer_report.py`
- Read only: `cli/subcommands.py`
- Read only: `tests/unit/test_research_optimizer.py`
- Read only: `tests/unit/test_research_optimizer_report.py`
- Read only: `tests/unit/test_subcommands.py`

- [ ] **Step 1: Confirm current branch and protected untracked state**

Run:

```powershell
git status --short --branch
```

Expected acceptable state:

```text
## feature/wide-v2-smoke-full-run-validation-exec
?? backtest/graph/
```

If additional tracked changes exist, inspect them before running the full backtest. Do not stage protected `backtest/` result paths.

- [ ] **Step 2: Confirm the optimizer command exposes the needed flags**

Run:

```powershell
python .\stom_backtest.py discovery optimize-wide-v2 --help
```

Expected output contains:

```text
--candidate-count
--max-rounds
--candidate-timeout
--runtime-output
--leaderboard-output
--summary-output
--report-path
--iteration-v2-trade-amount-feature
```

If the command fails to import or parse, stop and start:

```text
$brainstorming Wide v2 optimize-wide-v2 CLI import failure recovery 설계
```

- [ ] **Step 3: Run focused unit verification**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_optimizer.py `
  tests/unit/test_research_optimizer_report.py `
  tests/unit/test_subcommands.py `
  -q
```

Expected:

```text
all selected tests pass with zero failures
```

If this fails, do not run the full backtest. Fix the failing test or route to a focused recovery design.

---

### Task 2: Execute Candidate Count 10 Full Candidate-Set Run

**Files:**
- Generate, do not stage: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428.json`
- Generate, do not stage: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428_summary.json`
- Generate, do not stage: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428_leaderboard.json`
- Generate, do not stage: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428_console.txt`
- Generate, do not stage: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428_run_meta.json`
- Generate: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_candidate_count_10_full_run_summary.md`

- [ ] **Step 1: Define run paths and remove only same-run stale files**

Run:

```powershell
$env:PYTHONUTF8 = '1'
$RunId = 'wide_v2_v5_candidate_count_10_full_run_20260428'
$RuntimePath = "backtest\temp\${RunId}.json"
$SummaryPath = "backtest\temp\${RunId}_summary.json"
$LeaderboardPath = "backtest\temp\${RunId}_leaderboard.json"
$ConsolePath = "backtest\temp\${RunId}_console.txt"
$MetaPath = "backtest\temp\${RunId}_run_meta.json"
$ReportPath = 'docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_candidate_count_10_full_run_summary.md'

New-Item -ItemType Directory -Force -Path 'backtest\temp' | Out-Null
New-Item -ItemType Directory -Force -Path 'docs\research\condition_research\pilot_logs' | Out-Null

foreach ($Path in @($RuntimePath, $SummaryPath, $LeaderboardPath, $ConsolePath, $MetaPath, $ReportPath)) {
  if (Test-Path -LiteralPath $Path) {
    Remove-Item -LiteralPath $Path -Force
  }
}
```

Expected:

```text
No PowerShell error.
```

- [ ] **Step 2: Run the full candidate-set optimizer**

Run:

```powershell
$FullStart = Get-Date
python .\stom_backtest.py discovery optimize-wide-v2 `
  --name WideV2V5CandidateCount10FullRun_20260428 `
  --base-buy-strategy WideV1Final_B_20260425 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --seed-candidate WideV1Final_B_20260425 `
  --seed-expression "66.999 <= 시가총액 < 2_580 and 등락율 > 4.83" `
  --iteration-v2-trade-amount-feature "B_등락율" `
  --start 20250101 `
  --end 20251231 `
  --candidate-count 10 `
  --max-rounds 1 `
  --candidate-timeout 900 `
  --runtime-output $RuntimePath `
  --leaderboard-output $LeaderboardPath `
  --summary-output $SummaryPath `
  --report-path $ReportPath *> $ConsolePath
$FullExit = $LASTEXITCODE
$FullEnd = Get-Date
$FullElapsed = $FullEnd - $FullStart
[PSCustomObject]@{
  run_id = 'WideV2V5CandidateCount10FullRun_20260428'
  started_at = $FullStart.ToString('o')
  ended_at = $FullEnd.ToString('o')
  elapsed = $FullElapsed.ToString()
  exit_code = $FullExit
  runtime_path = $RuntimePath
  summary_path = $SummaryPath
  leaderboard_path = $LeaderboardPath
  console_path = $ConsolePath
  report_path = $ReportPath
  candidate_count = 10
  max_rounds = 1
} | ConvertTo-Json | Set-Content -Encoding UTF8 $MetaPath
$FullElapsed
$FullExit
```

Expected:

```text
The command returns exit_code 0.
The summary JSON exists.
The leaderboard JSON exists.
The Markdown report exists.
```

If exit code is non-zero but summary JSON exists, continue to Task 3 and classify the structured failure. If no summary JSON exists, inspect the console file and start:

```text
$brainstorming Wide v2 v5 candidate_count=10 runtime failure recovery 설계
```

- [ ] **Step 3: Confirm required output files exist**

Run:

```powershell
[PSCustomObject]@{
  RuntimeExists = Test-Path -LiteralPath $RuntimePath
  SummaryExists = Test-Path -LiteralPath $SummaryPath
  LeaderboardExists = Test-Path -LiteralPath $LeaderboardPath
  ConsoleExists = Test-Path -LiteralPath $ConsolePath
  MetaExists = Test-Path -LiteralPath $MetaPath
  ReportExists = Test-Path -LiteralPath $ReportPath
} | Format-List
```

Expected:

```text
SummaryExists     : True
LeaderboardExists : True
ReportExists      : True
```

---

### Task 3: Inspect Full-Run Result and WFO Handoff Candidate

**Files:**
- Read: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428_summary.json`
- Read: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428_leaderboard.json`
- Read: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428_run_meta.json`
- Read: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_candidate_count_10_full_run_summary.md`

- [ ] **Step 1: Print the summary decision facts**

Run:

```powershell
$Summary = Get-Content $SummaryPath -Raw -Encoding UTF8 | ConvertFrom-Json
$Leaderboard = Get-Content $LeaderboardPath -Raw -Encoding UTF8 | ConvertFrom-Json
$Meta = Get-Content $MetaPath -Raw -Encoding UTF8 | ConvertFrom-Json
[PSCustomObject]@{
  status = $Summary.status
  stop_reason = $Summary.stop_reason
  completed_round_count = $Summary.completed_round_count
  failed_round = $Summary.failed_round
  failure_phase = $Summary.failure_phase
  failure_message = $Summary.failure_message
  final_best_strategy_name = $Summary.final_best_candidate.strategy_name
  final_best_expression = $Summary.final_best_candidate.expression
  final_best_adjusted_score = $Summary.final_best_candidate.adjusted_score
  wfo_strategy_name = $Summary.wfo_candidate.strategy_name
  wfo_expression = $Summary.wfo_candidate.expression
  next_seed_selection_status = $Summary.next_seed_selection_status
  leaderboard_count = @($Leaderboard).Count
  elapsed = $Meta.elapsed
  exit_code = $Meta.exit_code
} | Format-List
```

Expected healthy path:

```text
status = ok
stop_reason = max_rounds_reached
completed_round_count = 1
failure_phase is blank
final_best_strategy_name is not blank
wfo_strategy_name is not blank
leaderboard_count >= 10
```

If `leaderboard_count < 10`, continue to Task 4 but classify the decision as `HOLD_CANDIDATE_COUNT_10_SHORTFALL`.

- [ ] **Step 2: Print top candidates**

Run:

```powershell
$Leaderboard |
  Sort-Object @{Expression = { [double]($_.adjusted_score) }; Descending = $true } |
  Select-Object -First 15 `
    round_index,
    candidate_index,
    strategy_name,
    candidate_type,
    promotion_passed,
    adjusted_score,
    promotion_score,
    trade_count,
    trade_count_retention,
    actual_rowset_selected |
  Format-Table -AutoSize
```

Expected:

```text
At least one candidate has promotion_passed=True.
The top row matches final_best_strategy_name or explains why final_best was selected differently.
```

- [ ] **Step 3: Inspect expression and candidate-family diversity**

Run:

```powershell
$ExpressionGroups = $Leaderboard |
  Group-Object expression |
  Sort-Object Count -Descending |
  Select-Object Count, Name

$CandidateTypeGroups = $Leaderboard |
  Group-Object candidate_type |
  Sort-Object Count -Descending |
  Select-Object Count, Name

$ExpressionGroups | Format-Table -AutoSize
$CandidateTypeGroups | Format-Table -AutoSize
```

Expected healthy path:

```text
ExpressionGroups contains more than one group.
CandidateTypeGroups is visible for later generator tuning.
```

If all candidates collapse to one expression or one actual row-set, route to candidate diversity recovery after documenting the result.

- [ ] **Step 4: Confirm the Markdown report has WFO and next-seed sections**

Run:

```powershell
$ReportText = Get-Content $ReportPath -Raw -Encoding UTF8
[PSCustomObject]@{
  HasSummaryTitle = $ReportText.Contains('# Wide v2 optimizer summary')
  HasLeaderboard = $ReportText.Contains('## Global leaderboard top candidates')
  HasNextSeedSelection = $ReportText.Contains('## Next seed selection')
  HasWfoHandoff = $ReportText.Contains('## WFO handoff')
  HasWfoWarning = $ReportText.Contains('The final candidate is a WFO candidate, not a live-trading approval.')
} | Format-List
```

Expected:

```text
All values are True.
```

For `max_rounds=1`, `next_seed_selection_status` can be blank because no next round was needed. The section still must exist for report consistency.

---

### Task 4: Write Korean Full-Run Review

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_candidate_count_10_full_run_review.md`
- Read: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428_summary.json`
- Read: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428_leaderboard.json`
- Read: `backtest/temp/wide_v2_v5_candidate_count_10_full_run_20260428_run_meta.json`

- [ ] **Step 1: Generate the review from structured outputs**

Run:

```powershell
$ReviewPath = 'docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_candidate_count_10_full_run_review.md'
$TopCandidate = @($Leaderboard |
  Sort-Object @{Expression = { [double]($_.adjusted_score) }; Descending = $true} |
  Select-Object -First 1)[0]
$ExpressionGroupCount = @($ExpressionGroups).Count
$CandidateTypeSummary = ($CandidateTypeGroups | ForEach-Object { "$($_.Name)=$($_.Count)" }) -join ', '
$Decision = 'PROCEED_TO_WFO_HANDOFF_PLAN'
$NextCommand = '$writing-plans Wide v2 final_best_candidate WFO/OOS 검증 계획 작성'

if ($Summary.status -ne 'ok' -or $Summary.failure_phase) {
  $Decision = 'HOLD_FULL_RUN_RUNTIME_OR_STRUCTURED_FAILURE'
  $NextCommand = '$brainstorming Wide v2 v5 candidate_count=10 runtime or structured failure recovery 설계'
} elseif (-not $Summary.wfo_candidate -or -not $Summary.wfo_candidate.strategy_name) {
  $Decision = 'HOLD_WFO_HANDOFF_MISSING'
  $NextCommand = '$brainstorming Wide v2 WFO handoff candidate missing recovery 설계'
} elseif (@($Leaderboard).Count -lt 10) {
  $Decision = 'HOLD_CANDIDATE_COUNT_10_SHORTFALL'
  $NextCommand = '$brainstorming Wide v2 v5 candidate_count=10 shortfall recovery 설계'
} elseif ($ExpressionGroupCount -lt 2) {
  $Decision = 'HOLD_EXPRESSION_DIVERSITY_COLLAPSE'
  $NextCommand = '$brainstorming Wide v2 v5 expression diversity collapse recovery 설계'
}

$Review = @"
# Wide v2 v5 candidate_count=10 full run 검토

## 실행 목적

Wide v2 v5 자동 개선 루프에서 full candidate count인 `candidate_count=10`을 실제 2025년 백테스트 데이터로 실행하고, WFO/OOS 검증으로 넘길 final best 후보를 선정할 수 있는지 확인했다.

이번 실행은 WFO/OOS가 아니다. 실행 목적은 후보 생성과 ranking, global best 선정, WFO handoff metadata 기록까지 검증하는 것이다.

## 실행 조건

- run_id: WideV2V5CandidateCount10FullRun_20260428
- candidate_count: 10
- max_rounds: 1
- start/end: 20250101-20251231
- seed_candidate: WideV1Final_B_20260425
- seed_expression: 66.999 <= 시가총액 < 2_580 and 등락율 > 4.83
- sell_strategy: ResearchTest_Tick_S_090000_092800_Wide_20260419
- elapsed: $($Meta.elapsed)
- exit_code: $($Meta.exit_code)

## 결과 요약

- status: $($Summary.status)
- stop_reason: $($Summary.stop_reason)
- completed_round_count: $($Summary.completed_round_count)
- failed_round: $($Summary.failed_round)
- failure_phase: $($Summary.failure_phase)
- failure_message: $($Summary.failure_message)
- leaderboard_count: $(@($Leaderboard).Count)
- expression_group_count: $ExpressionGroupCount
- candidate_type_distribution: $CandidateTypeSummary

## Final best 후보

- strategy_name: $($Summary.final_best_candidate.strategy_name)
- expression: $($Summary.final_best_candidate.expression)
- adjusted_score: $($Summary.final_best_candidate.adjusted_score)
- promotion_score: $($Summary.final_best_candidate.promotion_score)

## WFO handoff 후보

- strategy_name: $($Summary.wfo_candidate.strategy_name)
- expression: $($Summary.wfo_candidate.expression)
- source_round: $($Summary.wfo_candidate.source_round)
- source_candidate: $($Summary.wfo_candidate.source_candidate)
- next_command: $($Summary.wfo_candidate.next_command)

## Top leaderboard 후보

- strategy_name: $($TopCandidate.strategy_name)
- expression: $($TopCandidate.expression)
- adjusted_score: $($TopCandidate.adjusted_score)
- trade_count: $($TopCandidate.trade_count)
- trade_count_retention: $($TopCandidate.trade_count_retention)
- candidate_type: $($TopCandidate.candidate_type)

## 퀀트 관점 판정

`candidate_count=10` 실행은 조건식 자동 개선 루프의 후보 탐색 폭을 확인하는 단계다. final best 후보가 존재하더라도 이는 실전 채택 후보가 아니라 WFO/OOS 검증 대상으로만 해석한다.

건강한 결과의 기준은 `status=ok`, `completed_round_count >= 1`, `leaderboard_count >= 10`, WFO handoff 후보 존재, 그리고 후보 표현식 다양성 유지다.

## CLI 관점 판정

CLI는 summary JSON, leaderboard JSON, Markdown report를 생성해야 한다. 실패 시 traceback만 남기는 것이 아니라 `status`, `stop_reason`, `failure_phase`, `failure_message`로 원인이 남아야 한다.

이번 실행의 raw artifact는 `backtest/temp`, `backtest/csv`, `backtest/graph`에 남기고 커밋하지 않는다. 커밋 대상은 이 검토 문서와 optimizer Markdown summary뿐이다.

## 결정

- decision: $Decision
- next_command: $NextCommand

## 남은 MVP 단계

```text
1. candidate_count=10 full run 결과 확정
2. final_best_candidate WFO/OOS 검증
3. WFO/OOS 결과를 기준으로 MVP freeze 또는 조건식 생성 보강 분기
4. PR 보고서 작성 및 merge point 생성
```
"@

$Review | Set-Content -Encoding UTF8 $ReviewPath
Get-Content $ReviewPath -TotalCount 180 -Encoding UTF8
```

Expected:

```text
The review file exists.
The review includes decision and next_command.
The review includes final_best_candidate and wfo_candidate values.
```

- [ ] **Step 2: Confirm decision routing**

Run:

```powershell
Select-String -Path $ReviewPath -Pattern 'decision:', 'next_command:', 'strategy_name:', 'leaderboard_count:'
```

Expected healthy next command:

```text
$writing-plans Wide v2 final_best_candidate WFO/OOS 검증 계획 작성
```

If the generated decision is a `HOLD_*` decision, do not start WFO planning. Start the matching brainstorming command from the review.

---

### Task 5: Verification and Evidence Commit

**Files:**
- Stage only: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_candidate_count_10_full_run_summary.md`
- Stage only: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_candidate_count_10_full_run_review.md`

- [ ] **Step 1: Run full unit verification**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected:

```text
all tests pass with zero failures
```

- [ ] **Step 2: Run non-release sync guard**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

- [ ] **Step 3: Run whitespace check**

Run:

```powershell
git diff --check --ignore-cr-at-eol HEAD
```

Expected:

```text
no output
```

- [ ] **Step 4: Confirm protected artifacts are not staged**

Run:

```powershell
git status --short
```

Expected:

```text
?? backtest/graph/
```

The command may also show the two generated docs as untracked before staging. It must not show staged files under `backtest/temp`, `backtest/csv`, `backtest/graph`, or `utility/strategy.db`.

- [ ] **Step 5: Stage curated Markdown evidence only**

Run:

```powershell
git add `
  docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_candidate_count_10_full_run_summary.md `
  docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_candidate_count_10_full_run_review.md
git status --short
```

Expected staged files:

```text
A  docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_candidate_count_10_full_run_summary.md
A  docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_candidate_count_10_full_run_review.md
```

- [ ] **Step 6: Commit the full-run evidence**

Run:

```powershell
git commit -m "Wide v2 v5 후보 10개 full run 결과를 기록한다" -m @"
candidate_count=10 실행 결과를 기준으로 Wide v2 v5의 final best 후보와 WFO handoff 후보를 문서화한다.

이번 커밋은 raw backtest 산출물이 아니라 사람이 검토 가능한 Markdown evidence만 남긴다. WFO/OOS는 아직 실행하지 않았고, final best는 실전 채택 후보가 아니라 다음 검증 대상이다.

Constraint: backtest/temp, backtest/csv, backtest/graph 산출물은 커밋하지 않는다
Rejected: full run 결과 없이 WFO 계획으로 이동 | WFO 대상 후보가 실제 candidate_count=10에서 선정됐는지 확인해야 한다
Confidence: medium
Scope-risk: narrow
Directive: WFO/OOS 검증 전에는 final_best_candidate를 운영 후보로 표현하지 말 것
Tested: python -m pytest tests/unit/ -q
Tested: python scripts/verify_nonrelease_sync.py
Tested: git diff --check --ignore-cr-at-eol HEAD
Not-tested: WFO/OOS validation and live trading
"@
```

Expected:

```text
[feature/wide-v2-smoke-full-run-validation-exec <hash>] Wide v2 v5 후보 10개 full run 결과를 기록한다
```

---

### Task 6: Final Decision and Next Superpowers Command

**Files:**
- Read: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_candidate_count_10_full_run_review.md`

- [ ] **Step 1: Read the final decision**

Run:

```powershell
Select-String `
  -Path docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_candidate_count_10_full_run_review.md `
  -Pattern 'decision:', 'next_command:'
```

Expected healthy path:

```text
decision: PROCEED_TO_WFO_HANDOFF_PLAN
next_command: $writing-plans Wide v2 final_best_candidate WFO/OOS 검증 계획 작성
```

- [ ] **Step 2: Route to the next stage**

Use this decision table:

```text
PROCEED_TO_WFO_HANDOFF_PLAN
-> $writing-plans Wide v2 final_best_candidate WFO/OOS 검증 계획 작성

HOLD_FULL_RUN_RUNTIME_OR_STRUCTURED_FAILURE
-> $brainstorming Wide v2 v5 candidate_count=10 runtime or structured failure recovery 설계

HOLD_WFO_HANDOFF_MISSING
-> $brainstorming Wide v2 WFO handoff candidate missing recovery 설계

HOLD_CANDIDATE_COUNT_10_SHORTFALL
-> $brainstorming Wide v2 v5 candidate_count=10 shortfall recovery 설계

HOLD_EXPRESSION_DIVERSITY_COLLAPSE
-> $brainstorming Wide v2 v5 expression diversity collapse recovery 설계
```

- [ ] **Step 3: Report remaining MVP stages to the user**

Use this concise status:

```text
현재 완료: candidate_count=10 full run evidence commit
다음 단계: WFO/OOS 검증 계획
남은 단계: WFO/OOS 실행 -> MVP freeze 또는 후보 생성 보강 -> PR/merge
```

If the decision is a `HOLD_*` state, replace "WFO/OOS 검증 계획" with the recovery command from Step 2.

---

## Self-Review

- Spec coverage: This plan covers the exact next recommended stage: `candidate_count=10` full run, WFO handoff candidate selection, report review, verification, evidence commit, and next-stage routing.
- Scope control: The plan does not implement code, does not run WFO/OOS, does not add v6/v7, and does not commit protected runtime artifacts.
- Runtime control: The plan uses `max_rounds=1` because `candidate_count=2`, `max_rounds=2` smoke already verified loop continuation and next-seed recovery, while full `candidate_count=10`, `max_rounds=2` is likely to exceed the practical MVP runtime budget.
- Placeholder scan: The plan uses concrete paths, concrete commands, concrete decision labels, and scripts that generate actual review values from JSON outputs.
- Type consistency: CLI flags match `stom_backtest.py discovery optimize-wide-v2 --help`, including `--candidate-count`, `--max-rounds`, `--candidate-timeout`, `--runtime-output`, `--leaderboard-output`, `--summary-output`, and `--report-path`.
