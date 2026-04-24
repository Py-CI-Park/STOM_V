# Wide v1 v4 Candidate Count 10 Execution and Actual Row-Set Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute `best_feature_mix_v4` with `candidate_count=10`, verify the produced candidates with actual candidate CSV row-set analysis, and record whether the program should proceed to promote/WFO planning or hold for another diversity design pass.

**Architecture:** Use the existing `discovery research` CLI as the runtime entrypoint, not a new code path. Keep v4 execution temporary by deleting all generated candidate strategies after evaluation, persist only runtime JSON and markdown analysis artifacts, then make the next decision from observed `iteration_v4`, `retention_selection`, `candidate_specs`, and actual row-set grouping.

**Tech Stack:** Python 3.11, PowerShell, existing `stom_backtest.py` CLI, `cli.research_v3_decision.read_runtime_json`, `scripts/analyze_wide_v1_v4_rowset_diversity.py`, pytest, Ruff, basedpyright, existing STOM `_database` and `backtest/csv` outputs.

---

## Expert Direction Check

Quant trader view:

```text
The next action is not promote or WFO.
The next action is one controlled v4 candidate run plus actual row-set verification.
Reason: v4 currently improves selection by proxy row-set diversity, but only actual candidate CSV row sets can prove that the selected candidates are execution-distinct.
```

CLI developer view:

```text
Use the existing `python .\stom_backtest.py discovery research ...` entrypoint.
Use `runtime-preflight` first.
Capture stdout to a runtime JSON file with Tee-Object.
Do not add new CLI options for this run.
Do not keep temporary candidate strategies in `strategy.db`.
```

Whole-program view:

```text
Respect the current branch role: STOM_Version_2U_C in STOM_V.wt-dev.
Do not touch serial-key code.
Do not stage protected `backtest/graph/*.png` outputs.
Do not promote, run WFO, or mutate release branches in this plan.
```

---

## Fixed Inputs

Use these exact inputs for the v4 runtime:

```text
worktree=C:\System_Trading\STOM\STOM_V.wt-dev
runtime_name=WideV1IterationV4_20260424
runtime_path=backtest\temp\wide_v1_iteration_v4_20260424.json
runtime_root=.
input_csv=C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv
score_reference_csv=C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv
base_buy_strategy=WideV1IterationV2_20260423__cand005
sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
period=20250101~20251231
time=090000~092800
avg_time=30
betting=20
engines=32
candidate_count=10
candidate_timeout=900
mode=best_feature_mix_v4
best_expression=66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4
primary_feature=B_시가총액
secondary_features=B_체결강도,B_등락율,B_당일거래대금
```

The input CSV and score reference CSV already existed during plan creation, and `runtime-preflight` returned `status=ok` for the buy/sell strategies in this worktree.

---

## File Structure

- Read-only runtime inputs:
  - `C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv`
  - `C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv`
  - `_database\strategy.db`
  - `_database\stock_tick_back.db`

- Runtime artifacts to create or overwrite:
  - `backtest\temp\wide_v1_iteration_v4_20260424.json`
  - `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_iteration_loop_v4.md`
  - `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_rowset_diversity.md`
  - `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_execution_decision.md`
  - `docs\pr\2026-04-24_wide_v1_v4_candidate_count_10_actual_rowset_analysis_pr.md`

- Existing code paths to use without modification:
  - `stom_backtest.py`
  - `cli\subcommands.py`
  - `cli\research_loop.py`
  - `cli\research_iteration_v4.py`
  - `scripts\analyze_wide_v1_v4_rowset_diversity.py`
  - `cli\research_v3_decision.py`
  - `cli\research_v3_tiebreak.py`

---

## Task 1: Preflight and Runtime Directory Preparation

**Files:**
- Read: `cli\paths.py`
- Read: `_database\strategy.db`
- Read: `_database\stock_tick_back.db`
- Create directory if missing: `backtest\temp`
- Create directory if missing: `docs\research\condition_research\pilot_logs`

- [ ] **Step 1: Create output directories**

Run:

```powershell
New-Item -ItemType Directory -Force backtest\temp | Out-Null
New-Item -ItemType Directory -Force docs\research\condition_research\pilot_logs | Out-Null
```

Expected:

```text
No error.
```

- [ ] **Step 2: Verify fixed input CSV paths**

Run:

```powershell
Test-Path 'C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv'
Test-Path 'C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv'
```

Expected:

```text
True
True
```

- [ ] **Step 3: Run runtime preflight**

Run:

```powershell
python .\stom_backtest.py runtime-preflight `
  --buy WideV1IterationV2_20260423__cand005 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --betting 20 `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900 `
  | Tee-Object -FilePath docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_preflight.json
```

Expected:

```text
"status": "ok"
"failed_checks": []
"validation_errors": []
buy.status=ok
sell.status=ok
```

- [ ] **Step 4: Stop if preflight fails**

If preflight returns any failed check, do not run v4. Run this command to create `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_execution_decision.md` from the captured preflight JSON, then skip Tasks 2-4 and continue at Task 5 final docs.

```powershell
@'
from __future__ import annotations

import json
from pathlib import Path

preflight_path = Path("docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v4_preflight.json")
preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
failed_checks = preflight.get("failed_checks") or []
validation_errors = preflight.get("validation_errors") or []
status = preflight.get("status")

output_path = Path("docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v4_execution_decision.md")
output_path.write_text(
    f"""# Wide v1 v4 execution decision

## Decision

```text
decision=HOLD_PREFLIGHT_FAILURE
next_command=$brainstorming Wide v1 v4 runtime preflight failure recovery 설계
```

## Failed Preflight

```text
status={status}
failed_checks={failed_checks}
validation_errors={validation_errors}
```
""",
    encoding="utf-8",
)
print(f"decision=HOLD_PREFLIGHT_FAILURE")
print(f"next_command=$brainstorming Wide v1 v4 runtime preflight failure recovery 설계")
print(f"wrote={output_path}")
'@ | python -
```

Expected:

```text
decision=HOLD_PREFLIGHT_FAILURE
next_command=$brainstorming Wide v1 v4 runtime preflight failure recovery 설계
wrote=docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_execution_decision.md
```

---

## Task 2: Execute `best_feature_mix_v4` Candidate Count 10

**Files:**
- Read: fixed input CSV and score reference CSV
- Read/write runtime: `backtest\temp\wide_v1_iteration_v4_20260424.json`
- Runtime output: `backtest\csv\stock_bt_WideV1IterationV4_20260424__cand*.csv`
- Do not stage: `backtest\csv\*.csv`, `backtest\graph\*.png`, `backtest\temp\wide_v1_iteration_v4_20260424.json`

- [ ] **Step 1: Define runtime variables**

Run:

```powershell
$RuntimePath = 'backtest\temp\wide_v1_iteration_v4_20260424.json'
$InputCsv = 'C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv'
$ScoreReferenceCsv = 'C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv'
Remove-Item -LiteralPath $RuntimePath -Force -ErrorAction SilentlyContinue
```

Expected:

```text
No error.
```

- [ ] **Step 2: Run v4 candidate execution**

Run:

```powershell
python .\stom_backtest.py discovery research WideV1IterationV4_20260424 `
  --input $InputCsv `
  --score-reference-csv $ScoreReferenceCsv `
  --base-buy-strategy WideV1IterationV2_20260423__cand005 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --betting 20 `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --top-n 10 `
  --run-candidates `
  --candidate-count 10 `
  --candidate-timeout 900 `
  --candidate-pool-multiplier 3 `
  --cleanup-best-candidate `
  --iteration-v2-mode best_feature_mix_v4 `
  --iteration-v2-best-candidate WideV1IterationV2_20260423__cand005 `
  --iteration-v2-best-expression '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4' `
  --iteration-v2-primary-feature 'B_시가총액' `
  --iteration-v2-secondary-features 'B_체결강도,B_등락율,B_당일거래대금' `
  | Tee-Object -FilePath $RuntimePath
```

Expected:

```text
Runtime JSON is written to backtest\temp\wide_v1_iteration_v4_20260424.json.
The command eventually prints a JSON object.
The desired terminal state is "status": "ok" and "phase": "candidates_evaluated".
```

Notes:

```text
The command may run for tens of minutes.
Tee-Object may write UTF-16 on Windows PowerShell; downstream readers in this repo support utf-8-sig, utf-16, and utf-16-le.
`--cleanup-best-candidate` is intentional: v4 remains a research run until actual row-set diversity is verified.
```

- [ ] **Step 3: Parse runtime status**

Run:

```powershell
@'
from pathlib import Path
from cli.research_v3_decision import read_runtime_json

runtime_path = Path("backtest/temp/wide_v1_iteration_v4_20260424.json")
runtime = read_runtime_json(runtime_path)
iteration_v4 = runtime.get("iteration_v4") or {}
retention_selection = runtime.get("retention_selection") or {}
cleanup_summary = runtime.get("cleanup_summary") or {}
candidates = runtime.get("candidates") or []
print(f"status={runtime.get('status')}")
print(f"phase={runtime.get('phase')}")
print(f"iteration_v4_status={iteration_v4.get('status')}")
print(f"iteration_v4_candidate_count={iteration_v4.get('candidate_count')}")
print(f"selected_count={retention_selection.get('selected_count')}")
print(f"proxy_group_count={retention_selection.get('proxy_group_count')}")
print(f"skipped_duplicate_proxy_count={retention_selection.get('skipped_duplicate_proxy_count')}")
print(f"candidate_result_count={len(candidates)}")
print(f"cleanup_deleted_count={cleanup_summary.get('deleted_count')}")
print(f"cleanup_kept_count={cleanup_summary.get('kept_count')}")
'@ | python -
```

Expected success gate:

```text
status=ok
phase=candidates_evaluated
iteration_v4_status=ok
selected_count=10
candidate_result_count=10
cleanup_kept_count=0
```

- [ ] **Step 4: Stop if v4 execution fails**

If `status` is not `ok` or `phase` is not `candidates_evaluated`, do not analyze row sets. Run this command to create `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_execution_decision.md` from the runtime JSON, then skip Tasks 3-4 and continue at Task 5 final docs.

```powershell
@'
from __future__ import annotations

from pathlib import Path
from cli.research_v3_decision import read_runtime_json

runtime_path = Path("backtest/temp/wide_v1_iteration_v4_20260424.json")
runtime = read_runtime_json(runtime_path)
output_path = Path("docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v4_execution_decision.md")
output_path.write_text(
    f"""# Wide v1 v4 execution decision

## Decision

```text
decision=HOLD_V4_RUNTIME_FAILURE
next_command=$brainstorming Wide v1 v4 runtime failure recovery 설계
```

## Runtime Summary

```text
status={runtime.get('status')}
phase={runtime.get('phase')}
message={runtime.get('message')}
runtime_path={runtime_path}
```
""",
    encoding="utf-8",
)
print("decision=HOLD_V4_RUNTIME_FAILURE")
print("next_command=$brainstorming Wide v1 v4 runtime failure recovery 설계")
print(f"wrote={output_path}")
'@ | python -
```

Expected:

```text
decision=HOLD_V4_RUNTIME_FAILURE
next_command=$brainstorming Wide v1 v4 runtime failure recovery 설계
wrote=docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_execution_decision.md
```

---

## Task 3: Generate v4 Runtime Pilot Log

**Files:**
- Read: `backtest\temp\wide_v1_iteration_v4_20260424.json`
- Create: `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_iteration_loop_v4.md`

- [ ] **Step 1: Generate runtime pilot log from JSON**

Run:

```powershell
@'
from __future__ import annotations

from collections import Counter
from pathlib import Path
from cli.research_v3_decision import read_runtime_json

runtime_path = Path("backtest/temp/wide_v1_iteration_v4_20260424.json")
output_path = Path("docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_iteration_loop_v4.md")
runtime = read_runtime_json(runtime_path)
iteration_v4 = runtime.get("iteration_v4") or {}
retention_selection = runtime.get("retention_selection") or {}
candidate_specs = runtime.get("candidate_specs") or []
candidates = runtime.get("candidates") or []
cleanup_summary = runtime.get("cleanup_summary") or {}
best_candidate = runtime.get("best_candidate") or {}

spec_by_name = {
    spec.get("strategy_name"): spec
    for spec in candidate_specs
    if isinstance(spec, dict)
}
family_counts = Counter()
rank_lines = []
for candidate in sorted(candidates, key=lambda item: int(item.get("rank") or 999999)):
    spec = spec_by_name.get(candidate.get("strategy_name")) or {}
    source = spec.get("source_candidate") or {}
    family = source.get("v4_candidate_type") or "unknown"
    family_counts[str(family)] += 1
    rank_score = candidate.get("rank_score") or {}
    rank_lines.append(
        "- rank={rank} strategy={strategy} type={family} adjusted_score={score} "
        "trade_count={trade_count} retention={retention} csv={csv}".format(
            rank=candidate.get("rank"),
            strategy=candidate.get("strategy_name"),
            family=family,
            score=rank_score.get("adjusted_score"),
            trade_count=rank_score.get("trade_count"),
            retention=rank_score.get("trade_count_retention"),
            csv=candidate.get("candidate_csv"),
        )
    )

quota_summary = retention_selection.get("quota_summary") or {}
quota_lines = [
    f"- {family}: target={item.get('target')}, selected={item.get('selected')}, shortfall={item.get('shortfall')}"
    for family, item in sorted(quota_summary.items())
    if isinstance(item, dict)
]

text = f"""# Wide v1 Iteration Loop v4 Pilot

## Purpose

Run `best_feature_mix_v4` with `candidate_count=10` and prepare actual row-set diversity verification.

## Inputs

```text
runtime_path={runtime_path}
input_csv={runtime.get('baseline_csv')}
score_reference_csv={(runtime.get('iteration_plan') or {}).get('score_reference_csv')}
mode={(runtime.get('config') or {}).get('iteration_v2_mode')}
candidate_count={(runtime.get('iteration_plan') or {}).get('candidate_count')}
candidate_timeout={(runtime.get('iteration_plan') or {}).get('candidate_timeout')}
cleanup_best_candidate={(runtime.get('iteration_plan') or {}).get('cleanup_best_candidate')}
```

## Runtime Result

```text
status={runtime.get('status')}
phase={runtime.get('phase')}
best_candidate={best_candidate.get('strategy_name')}
candidate_result_count={len(candidates)}
```

## Iteration v4 Candidate Pool

```text
status={iteration_v4.get('status')}
mode={iteration_v4.get('mode')}
candidate_count={iteration_v4.get('candidate_count')}
primary_feature={iteration_v4.get('primary_feature')}
trade_amount_feature={iteration_v4.get('trade_amount_feature')}
type_counts={iteration_v4.get('type_counts')}
```

## Proxy Row-Set Selection

```text
phase={retention_selection.get('phase')}
pool_count={retention_selection.get('pool_count')}
eligible_count={retention_selection.get('eligible_count')}
selected_count={retention_selection.get('selected_count')}
proxy_group_count={retention_selection.get('proxy_group_count')}
skipped_duplicate_proxy_count={retention_selection.get('skipped_duplicate_proxy_count')}
selected_proxy_groups={retention_selection.get('selected_proxy_groups')}
```

## Quota Summary

{chr(10).join(quota_lines)}

## Executed Family Distribution

```text
{dict(family_counts)}
```

## Candidate Ranking

{chr(10).join(rank_lines)}

## Cleanup Summary

```text
attempted_count={cleanup_summary.get('attempted_count')}
deleted_count={cleanup_summary.get('deleted_count')}
kept_count={cleanup_summary.get('kept_count')}
failed_count={cleanup_summary.get('failed_count')}
```
"""

output_path.write_text(text, encoding="utf-8")
print(f"wrote={output_path}")
print(f"status={runtime.get('status')}")
print(f"phase={runtime.get('phase')}")
print(f"executed_family_distribution={dict(family_counts)}")
'@ | python -
```

Expected:

```text
wrote=docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_iteration_loop_v4.md
status=ok
phase=candidates_evaluated
```

- [ ] **Step 2: Inspect key pilot log lines**

Run:

```powershell
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_iteration_loop_v4.md -Pattern 'status=|phase=|proxy_group_count|skipped_duplicate_proxy_count|Executed Family Distribution|best_candidate='
```

Expected:

```text
status=ok
phase=candidates_evaluated
The output includes proxy_group_count and skipped_duplicate_proxy_count.
```

---

## Task 4: Analyze Actual Row-Set Diversity

**Files:**
- Read: `backtest\temp\wide_v1_iteration_v4_20260424.json`
- Read: generated candidate CSV files referenced by runtime JSON
- Create: `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_rowset_diversity.md`
- Create: `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_execution_decision.md`

- [ ] **Step 1: Run actual row-set diversity wrapper**

Run:

```powershell
python scripts\analyze_wide_v1_v4_rowset_diversity.py `
  --runtime-path backtest\temp\wide_v1_iteration_v4_20260424.json `
  --runtime-root . `
  --output docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_rowset_diversity.md `
  --top-n 10
```

Expected:

```text
decision=accepted values are HOLD_V4_ROW_SET_REVIEW, PROCEED_TO_PROMOTE_WFO_PLAN, HOLD_V4_FAMILY_CONCENTRATION_REVIEW, or HOLD_V4_UNKNOWN_DECISION_STATE
next_command=accepted value is one command derived from the decision
row_set_identity_status=accepted values are all_identical, partially_distinct, all_distinct, not_evaluated, or error
group_count=accepted value is a non-negative integer
wrote=docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_rowset_diversity.md
```

- [ ] **Step 2: Generate execution decision from actual row-set status and v4 family spread**

Run:

```powershell
@'
from __future__ import annotations

from collections import Counter
from pathlib import Path
from cli.research_v3_decision import read_runtime_json
from cli.research_v3_tiebreak import build_v3_tie_break_analysis

runtime_path = Path("backtest/temp/wide_v1_iteration_v4_20260424.json")
runtime = read_runtime_json(runtime_path)
analysis = build_v3_tie_break_analysis(
    runtime_path=runtime_path,
    runtime_root=Path("."),
    top_n=10,
)
row_set_gate = analysis.get("row_set_gate") or {}
candidate_specs = runtime.get("candidate_specs") or []
candidates = runtime.get("candidates") or []
spec_by_name = {
    spec.get("strategy_name"): spec
    for spec in candidate_specs
    if isinstance(spec, dict)
}
executed_family_counts = Counter()
for candidate in candidates:
    spec = spec_by_name.get(candidate.get("strategy_name")) or {}
    source = spec.get("source_candidate") or {}
    family = source.get("v4_candidate_type") or "unknown"
    if candidate.get("status") == "ok":
        executed_family_counts[str(family)] += 1

row_status = row_set_gate.get("status")
group_count = int(row_set_gate.get("group_count") or 0)
family_count = len([family for family in executed_family_counts if family != "unknown"])

if row_status in {"error", "all_identical", "partially_distinct", "not_evaluated"}:
    decision = "HOLD_V4_ROW_SET_REVIEW"
    next_command = "$brainstorming Wide v1 v5 actual row-set diversity selection 보강 설계"
elif row_status == "all_distinct" and family_count >= 2:
    decision = "PROCEED_TO_PROMOTE_WFO_PLAN"
    next_command = "$writing-plans Wide v1 v4 promote 및 WFO 검증 계획 작성"
elif row_status == "all_distinct":
    decision = "HOLD_V4_FAMILY_CONCENTRATION_REVIEW"
    next_command = "$brainstorming Wide v1 v4 family concentration selection 보강 설계"
else:
    decision = "HOLD_V4_UNKNOWN_DECISION_STATE"
    next_command = "$brainstorming Wide v1 v4 execution decision state 정리"

output_path = Path("docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v4_execution_decision.md")
output_path.write_text(
    f"""# Wide v1 v4 execution decision

## Decision

```text
decision={decision}
next_command={next_command}
```

## Runtime

```text
runtime_path={runtime_path}
status={runtime.get('status')}
phase={runtime.get('phase')}
best_candidate={(runtime.get('best_candidate') or {}).get('strategy_name')}
```

## Actual Row-Set Gate

```text
row_set_identity_status={row_status}
group_count={group_count}
candidate_count={row_set_gate.get('candidate_count')}
```

## Executed v4 Family Distribution

```text
{dict(executed_family_counts)}
```

## Rule

```text
all_distinct and at least two known executed v4 families -> proceed to promote/WFO planning
all_identical, partially_distinct, not_evaluated, or error -> hold and redesign actual row-set diversity
all_distinct but one known executed family -> hold family concentration review
```
""",
    encoding="utf-8",
)
print(f"decision={decision}")
print(f"next_command={next_command}")
print(f"row_set_identity_status={row_status}")
print(f"group_count={group_count}")
print(f"executed_family_distribution={dict(executed_family_counts)}")
print(f"wrote={output_path}")
'@ | python -
```

Expected:

```text
decision=accepted values are HOLD_V4_ROW_SET_REVIEW, PROCEED_TO_PROMOTE_WFO_PLAN, HOLD_V4_FAMILY_CONCENTRATION_REVIEW, or HOLD_V4_UNKNOWN_DECISION_STATE
next_command=accepted value is one command derived from the decision
row_set_identity_status=accepted values are all_identical, partially_distinct, all_distinct, not_evaluated, or error
group_count=accepted value is a non-negative integer
wrote=docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_execution_decision.md
```

- [ ] **Step 3: Inspect decision file**

Run:

```powershell
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_execution_decision.md -Pattern 'decision=|next_command=|row_set_identity_status|group_count|Executed v4 Family Distribution'
```

Expected:

```text
The output contains one decision, one next_command, row_set_identity_status, and group_count.
```

---

## Task 5: PR Report and Final Verification

**Files:**
- Create: `docs\pr\2026-04-24_wide_v1_v4_candidate_count_10_actual_rowset_analysis_pr.md`
- Runtime temp: `backtest\temp\wide_v1_v4_verification.txt`
- Stage only markdown docs from this plan.
- Do not stage `backtest\csv`, `backtest\graph`, or `backtest\temp`.

- [ ] **Step 1: Run focused verification**

Run:

```powershell
$VerificationLog = 'backtest\temp\wide_v1_v4_verification.txt'
"# Wide v1 v4 verification" | Set-Content -Path $VerificationLog -Encoding utf8

"`n## pytest" | Tee-Object -FilePath $VerificationLog -Append
python -m pytest tests/unit/test_research_iteration_v4.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_research_v3_tiebreak.py -q 2>&1 | Tee-Object -FilePath $VerificationLog -Append
if ($LASTEXITCODE -ne 0) { throw "pytest failed" }

"`n## ruff" | Tee-Object -FilePath $VerificationLog -Append
python -m ruff check cli/research_iteration_v4.py cli/research_loop.py cli/research_report.py scripts/analyze_wide_v1_v4_rowset_diversity.py tests/unit/test_research_iteration_v4.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_research_v3_tiebreak.py 2>&1 | Tee-Object -FilePath $VerificationLog -Append
if ($LASTEXITCODE -ne 0) { throw "ruff failed" }

"`n## basedpyright" | Tee-Object -FilePath $VerificationLog -Append
basedpyright cli\research_iteration_v4.py scripts\analyze_wide_v1_v4_rowset_diversity.py tests\unit\test_research_iteration_v4.py 2>&1 | Tee-Object -FilePath $VerificationLog -Append
if ($LASTEXITCODE -ne 0) { throw "basedpyright failed" }

"`n## verify_nonrelease_sync" | Tee-Object -FilePath $VerificationLog -Append
python scripts\verify_nonrelease_sync.py 2>&1 | Tee-Object -FilePath $VerificationLog -Append
if ($LASTEXITCODE -ne 0) { throw "verify_nonrelease_sync failed" }

"`n## git diff --check" | Tee-Object -FilePath $VerificationLog -Append
git diff --check 2>&1 | Tee-Object -FilePath $VerificationLog -Append
if ($LASTEXITCODE -ne 0) { throw "git diff --check failed" }
```

Expected:

```text
All commands exit 0.
backtest\temp\wide_v1_v4_verification.txt contains the observed outputs.
```

- [ ] **Step 2: Generate PR report from observed artifacts**

Run:

```powershell
@'
from __future__ import annotations

from pathlib import Path
import re

runtime_log_path = Path("docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_iteration_loop_v4.md")
rowset_log_path = Path("docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v4_rowset_diversity.md")
decision_path = Path("docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v4_execution_decision.md")
verification_path = Path("backtest/temp/wide_v1_v4_verification.txt")
output_path = Path("docs/pr/2026-04-24_wide_v1_v4_candidate_count_10_actual_rowset_analysis_pr.md")

runtime_log = runtime_log_path.read_text(encoding="utf-8")
rowset_log = rowset_log_path.read_text(encoding="utf-8")
decision_log = decision_path.read_text(encoding="utf-8")
verification_log = verification_path.read_text(encoding="utf-8")

next_command_match = re.search(r"next_command=(.+)", decision_log)
next_command = next_command_match.group(1).strip() if next_command_match else "$brainstorming Wide v1 v4 execution decision state 정리"

report = f"""# Wide v1 v4 candidate_count=10 actual row-set analysis PR 보고서

## 1. 목적

`best_feature_mix_v4`를 candidate_count=10으로 실제 실행하고, proxy row-set selection이 actual candidate CSV row-set diversity로 이어졌는지 확인한다.

## 2. 실행 입력

```text
runtime_name=WideV1IterationV4_20260424
runtime_path=backtest\\temp\\wide_v1_iteration_v4_20260424.json
input_csv=C:\\System_Trading\\STOM\\STOM_V.wt-wide-v2\\backtest\\csv\\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv
score_reference_csv=C:\\System_Trading\\STOM\\STOM_V.wt-wide-cli-compare\\backtest\\csv\\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv
candidate_count=10
mode=best_feature_mix_v4
cleanup_best_candidate=True
```

## 3. runtime 결과

Source: `{runtime_log_path}`

{runtime_log}

## 4. actual row-set 결과

Source: `{rowset_log_path}`

{rowset_log}

## 5. 최종 판단

Source: `{decision_path}`

{decision_log}

## 6. 검증 결과

Source: `{verification_path}`

```text
{verification_log}
```

## 7. 남은 리스크

```text
- This PR records one v4 runtime only.
- Promote/WFO is still blocked unless the decision file says PROCEED_TO_PROMOTE_WFO_PLAN.
- Generated backtest CSV/graph/temp artifacts are runtime evidence, not source changes.
```

## 8. 다음 단계

```text
{next_command}
```
"""

output_path.write_text(report, encoding="utf-8")
print(f"wrote={output_path}")
print(f"next_command={next_command}")
'@ | python -
```

Expected:

```text
wrote=docs\pr\2026-04-24_wide_v1_v4_candidate_count_10_actual_rowset_analysis_pr.md
next_command=the exact next_command value from docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_execution_decision.md
```

- [ ] **Step 3: Verify the PR report contains no placeholders**

Run:

```powershell
$patterns = @(
  ('TB' + 'D'),
  ('TO' + 'DO'),
  ('Copy the ' + 'observed'),
  ('Record only ' + 'commands'),
  ('replace ' + 'with')
)
Select-String -Path docs\pr\2026-04-24_wide_v1_v4_candidate_count_10_actual_rowset_analysis_pr.md -Pattern $patterns
```

Expected:

```text
No matches.
```

- [ ] **Step 4: Stage only documentation outputs**

Run:

```powershell
git add docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_iteration_loop_v4.md `
        docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_rowset_diversity.md `
        docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_execution_decision.md `
        docs\pr\2026-04-24_wide_v1_v4_candidate_count_10_actual_rowset_analysis_pr.md
git diff --cached --check
git diff --cached --stat
```

Expected:

```text
Only the four markdown files are staged.
git diff --cached --check prints no errors.
```

- [ ] **Step 5: Commit observed v4 execution analysis**

Run:

```powershell
git commit -m "Wide v1 v4 실제 실행과 행집합 분석 결과를 기록한다" -m "## 배경

best_feature_mix_v4 후보 생성이 proxy row-set diversity를 실제 실행 row-set 다양성으로 연결하는지 확인하기 위해 candidate_count=10 runtime 결과를 문서화한다.

## 변경

- v4 runtime pilot log를 추가했다.
- actual row-set diversity 분석 보고서를 추가했다.
- 실행 결정 보고서를 추가했다.
- PR 보고서에 검증 결과와 다음 명령을 기록했다.

Constraint: backtest CSV/graph/temp runtime artifact는 git에 staging하지 않음
Confidence: medium
Scope-risk: narrow
Directive: decision이 PROCEED_TO_PROMOTE_WFO_PLAN이 아니면 promote/WFO 계획을 세우지 말 것
Tested: python -m pytest tests/unit/test_research_iteration_v4.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_research_v3_tiebreak.py -q
Tested: python -m ruff check v4 touched files
Tested: basedpyright cli\research_iteration_v4.py scripts\analyze_wide_v1_v4_rowset_diversity.py tests\unit\test_research_iteration_v4.py
Tested: python scripts\verify_nonrelease_sync.py
Tested: git diff --cached --check
Not-tested: promote/WFO execution"
```

The detailed observed verification output is already embedded in the generated PR report.

---

## Final Verification

- [ ] **Step 1: Check worktree**

Run:

```powershell
git status --short --branch --untracked-files=all
```

Expected:

```text
No tracked changes remain.
Untracked backtest runtime outputs may remain.
Pre-existing protected backtest/graph/*.png files may remain untracked.
```

- [ ] **Step 2: Read next command**

Run:

```powershell
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_execution_decision.md -Pattern 'next_command='
```

Expected:

```text
Exactly one next_command is present.
```

## Self-Review Checklist

Spec coverage:

```text
candidate_count=10 v4 execution: Task 2
preflight before runtime: Task 1
no promote/WFO during this plan: Tasks 2, 4, and 5
temporary strategy cleanup: Task 2 uses --cleanup-best-candidate
runtime pilot log: Task 3
actual row-set diversity analysis: Task 4
decision gate and next command: Task 4
PR report and verification: Task 5
explicit staging exclusions for backtest outputs: Task 5
```

Placeholder scan:

```text
The plan uses scripts to generate observed runtime and PR report content.
The executor verifies the generated PR report has no placeholder markers before staging.
```

Type consistency:

```text
Main runtime mode: best_feature_mix_v4
Runtime JSON: backtest\temp\wide_v1_iteration_v4_20260424.json
Runtime name: WideV1IterationV4_20260424
Actual row-set script: scripts\analyze_wide_v1_v4_rowset_diversity.py
Decision doc: docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v4_execution_decision.md
```
