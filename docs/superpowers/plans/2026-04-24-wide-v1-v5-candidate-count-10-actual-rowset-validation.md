# Wide v1 v5 Candidate Count 10 Actual Row-Set Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run `best_feature_mix_v5` with `candidate_count=10`, verify whether actual candidate CSV row-set representatives are sufficiently distinct, and record the next decision.

**Architecture:** Keep v4 inputs fixed so the only meaningful change is v5's actual row-set representative selection after oversampled execution. Use the existing `stom_backtest.py discovery research` entrypoint, existing v5 runtime decision script, and markdown pilot logs/PR reports. Runtime artifacts under `backtest/` are verification evidence and must not be staged.

**Tech Stack:** Python 3.11, PowerShell, `stom_backtest.py`, `cli.research_v3_decision.read_runtime_json`, `scripts/analyze_wide_v1_v5_actual_rowset_selection.py`, pytest, git.

---

## File Structure

- Create runtime artifact, do not stage: `backtest\temp\wide_v1_iteration_v5_20260424.json`
- Create candidate CSV artifacts, do not stage: `backtest\csv\stock_bt_WideV1IterationV5_20260424__cand*.csv`
- Create/update pilot log: `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_iteration_loop_v5.md`
- Create/update v5 decision report: `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v5_actual_rowset_selection.md`
- Create PR report: `docs\pr\2026-04-24_wide_v1_v5_candidate_count_10_actual_rowset_validation_pr.md`
- Existing code paths to use without modification:
  - `stom_backtest.py`
  - `cli\research_loop.py`
  - `cli\research_iteration_v5.py`
  - `scripts\analyze_wide_v1_v5_actual_rowset_selection.py`
  - `cli\research_v3_decision.py`

Execution branch:

```powershell
git branch --show-current
```

Expected:

```text
feature/wide-v1-v5-candidate-count-10-runtime-validation
```

Do not use `git add -A`. Stage only the markdown documents created by this plan.

---

## Task 1: Preflight and Input Lock

**Files:**
- Read: `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_iteration_loop_v4.md`
- Read: fixed input CSV: `C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv`
- Read: fixed score reference CSV: `C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv`
- Create directory if missing: `backtest\temp`
- Create directory if missing: `docs\research\condition_research\pilot_logs`

- [ ] **Step 1: Confirm branch and tracked cleanliness**

Run:

```powershell
git branch --show-current
git status --short --untracked-files=no
```

Expected:

```text
feature/wide-v1-v5-candidate-count-10-runtime-validation
```

`git status --short --untracked-files=no` must not list modified tracked files. Existing untracked `backtest\graph\*.png` files can remain ignored by this plan.

- [ ] **Step 2: Create output directories**

Run:

```powershell
New-Item -ItemType Directory -Force backtest\temp | Out-Null
New-Item -ItemType Directory -Force docs\research\condition_research\pilot_logs | Out-Null
```

Expected:

```text
No error.
```

- [ ] **Step 3: Define fixed runtime variables**

Run:

```powershell
$RuntimePath = 'backtest\temp\wide_v1_iteration_v5_20260424.json'
$PreflightPath = 'docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v5_preflight.json'
$InputCsv = 'C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv'
$ScoreReferenceCsv = 'C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv'
Test-Path $InputCsv
Test-Path $ScoreReferenceCsv
```

Expected:

```text
True
True
```

- [ ] **Step 4: Remove stale v5 runtime capture**

Run:

```powershell
Remove-Item -LiteralPath $RuntimePath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $PreflightPath -Force -ErrorAction SilentlyContinue
```

Expected:

```text
No error.
```

- [ ] **Step 5: Run runtime preflight**

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
  | Tee-Object -FilePath $PreflightPath
```

Expected:

```text
"status": "ok"
"failed_checks": []
"validation_errors": []
```

- [ ] **Step 6: Stop if preflight fails**

Run this parser:

```powershell
@'
from pathlib import Path
from cli.research_v3_decision import read_runtime_json

preflight_path = Path("docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v5_preflight.json")
preflight = read_runtime_json(preflight_path)
print(f"status={preflight.get('status')}")
print(f"failed_checks={preflight.get('failed_checks')}")
print(f"validation_errors={preflight.get('validation_errors')}")
'@ | python -
```

Expected:

```text
status=ok
failed_checks=[]
validation_errors=[]
```

If any value differs, do not run Task 2. Create `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v5_actual_rowset_selection.md` with the decision `HOLD_V5_RUNTIME_FAILURE`, commit the failure report, and stop.

- [ ] **Step 7: Commit preflight-only docs if failure happened**

Only run this step if Step 6 failed.

```powershell
git add docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v5_actual_rowset_selection.md
git commit -m "Wide v1 v5 실행 전 프리플라이트 실패를 기록한다" -m "v5 candidate_count=10 실제 실행 전에 runtime-preflight가 실패해 실행을 중단하고 복구 설계로 넘긴다." -m "Confidence: high" -m "Scope-risk: narrow" -m "Tested: python .\stom_backtest.py runtime-preflight" -m "Not-tested: v5 후보 실행은 preflight 실패로 수행하지 않았다"
```

Expected:

```text
[feature/wide-v1-v5-candidate-count-10-runtime-validation <hash>] Wide v1 v5 실행 전 프리플라이트 실패를 기록한다
```

---

## Task 2: Execute `best_feature_mix_v5` Candidate Count 10

**Files:**
- Read: `$InputCsv`
- Read: `$ScoreReferenceCsv`
- Create runtime artifact, do not stage: `backtest\temp\wide_v1_iteration_v5_20260424.json`
- Create candidate CSV artifacts, do not stage: `backtest\csv\stock_bt_WideV1IterationV5_20260424__cand*.csv`

- [ ] **Step 1: Run v5 candidate execution**

Run:

```powershell
python .\stom_backtest.py discovery research WideV1IterationV5_20260424 `
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
  --iteration-v2-mode best_feature_mix_v5 `
  --iteration-v2-best-candidate WideV1IterationV2_20260423__cand005 `
  --iteration-v2-best-expression '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4' `
  --iteration-v2-primary-feature 'B_시가총액' `
  --iteration-v2-secondary-features 'B_체결강도,B_등락율,B_당일거래대금' `
  | Tee-Object -FilePath $RuntimePath
```

Expected:

```text
The command eventually prints a JSON object.
The JSON contains "status": "ok" and "phase": "candidates_evaluated".
The runtime file exists at backtest\temp\wide_v1_iteration_v5_20260424.json.
```

Notes:

```text
This command can run for tens of minutes.
Tee-Object may write UTF-16 on Windows PowerShell; read_runtime_json supports utf-8-sig, utf-16, and utf-16-le.
Keep --cleanup-best-candidate enabled because v5 is still a research run before promote/WFO.
Do not stage backtest\temp, backtest\csv, or backtest\graph outputs.
```

- [ ] **Step 2: Parse v5 runtime status**

Run:

```powershell
@'
from pathlib import Path
from cli.research_v3_decision import read_runtime_json

runtime_path = Path("backtest/temp/wide_v1_iteration_v5_20260424.json")
runtime = read_runtime_json(runtime_path)
iteration_v4 = runtime.get("iteration_v4") or {}
iteration_v5 = runtime.get("iteration_v5") or {}
selection = runtime.get("actual_rowset_selection") or {}
candidates = runtime.get("candidates") or []
best = runtime.get("best_candidate") or {}
print(f"status={runtime.get('status')}")
print(f"phase={runtime.get('phase')}")
print(f"candidate_result_count={len(candidates)}")
print(f"best_candidate={best.get('strategy_name')}")
print(f"iteration_v4_candidate_count={iteration_v4.get('candidate_count')}")
print(f"iteration_v5_status={iteration_v5.get('status')}")
print(f"iteration_v5_requested_count={iteration_v5.get('requested_count')}")
print(f"iteration_v5_planned_execution_count={iteration_v5.get('planned_execution_count')}")
print(f"iteration_v5_execution_count={iteration_v5.get('execution_count')}")
print(f"actual_selection_status={selection.get('status')}")
print(f"row_set_identity_status={selection.get('row_set_identity_status')}")
print(f"selected_count={selection.get('selected_count')}")
print(f"requested_count={selection.get('requested_count')}")
print(f"duplicate_actual_rowset_count={selection.get('duplicate_actual_rowset_count')}")
'@ | python -
```

Expected successful path:

```text
status=ok
phase=candidates_evaluated
candidate_result_count=17
iteration_v5_requested_count=10
iteration_v5_planned_execution_count=17
iteration_v5_execution_count=17
actual_selection_status=ok
row_set_identity_status=all_distinct
selected_count=10
requested_count=10
```

Accepted non-success paths:

```text
status=error
```

or

```text
actual_selection_status=shortfall
row_set_identity_status=partially_distinct
selected_count=<integer less than 10>
requested_count=10
```

If `status=error`, skip Task 3 and run Task 4 to create the v5 decision report. If status is ok, continue to Task 3.

---

## Task 3: Write v5 Runtime Pilot Log

**Files:**
- Read: `backtest\temp\wide_v1_iteration_v5_20260424.json`
- Create: `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_iteration_loop_v5.md`

- [ ] **Step 1: Generate v5 pilot markdown**

Run:

```powershell
@'
from __future__ import annotations

from collections import Counter
from pathlib import Path
from cli.research_v3_decision import read_runtime_json

runtime_path = Path("backtest/temp/wide_v1_iteration_v5_20260424.json")
output_path = Path("docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_iteration_loop_v5.md")
runtime = read_runtime_json(runtime_path)
config = runtime.get("config") or {}
plan = runtime.get("iteration_plan") or {}
iteration_v4 = runtime.get("iteration_v4") or {}
iteration_v5 = runtime.get("iteration_v5") or {}
retention_selection = runtime.get("retention_selection") or {}
actual_selection = runtime.get("actual_rowset_selection") or {}
cleanup_summary = runtime.get("cleanup_summary") or {}
best_candidate = runtime.get("best_candidate") or {}
candidates = runtime.get("candidates") or []
candidate_specs = runtime.get("candidate_specs") or []
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
    family = source.get("v4_candidate_type") or candidate.get("v4_candidate_type") or "unknown"
    if candidate.get("status") == "ok":
        family_counts[str(family)] += 1
    score = candidate.get("rank_score") or {}
    rank_lines.append(
        "- "
        f"rank={candidate.get('rank')} "
        f"strategy={candidate.get('strategy_name')} "
        f"type={family} "
        f"actual_rowset_selected={candidate.get('actual_rowset_selected')} "
        f"selected_as_best={candidate.get('selected_as_best')} "
        f"adjusted_score={score.get('adjusted_score')} "
        f"trade_count={score.get('trade_count')} "
        f"retention={score.get('trade_count_retention')} "
        f"csv={candidate.get('candidate_csv') or candidate.get('csv_path')}"
    )

selected_names = actual_selection.get("selected_strategy_names") or []
duplicate_groups = actual_selection.get("duplicate_groups") or []
duplicate_lines = []
for group in duplicate_groups:
    duplicate_lines.append(
        "- "
        f"group_id={group.get('group_id')} "
        f"representative={group.get('representative')} "
        f"members={group.get('members')}"
    )
if not duplicate_lines:
    duplicate_lines.append("- none")

text = f"""# Wide v1 Iteration Loop v5 Pilot

## Purpose

Run `best_feature_mix_v5` with `candidate_count=10` and verify whether actual candidate CSV row-set representative selection produces 10 distinct final representatives.

## Inputs

```text
runtime_path={runtime_path}
input_csv={runtime.get('baseline_csv')}
score_reference_csv={plan.get('score_reference_csv')}
mode={config.get('iteration_v2_mode')}
candidate_count={plan.get('candidate_count')}
candidate_timeout={plan.get('candidate_timeout')}
cleanup_best_candidate={plan.get('cleanup_best_candidate')}
```

## Runtime Result

```text
status={runtime.get('status')}
phase={runtime.get('phase')}
best_candidate={best_candidate.get('strategy_name')}
candidate_result_count={len(candidates)}
```

## v4 Source Candidate Pool

```text
status={iteration_v4.get('status')}
mode={iteration_v4.get('mode')}
candidate_count={iteration_v4.get('candidate_count')}
type_counts={iteration_v4.get('type_counts')}
```

## v5 Oversampled Execution

```text
status={iteration_v5.get('status')}
mode={iteration_v5.get('mode')}
requested_count={iteration_v5.get('requested_count')}
eligible_count={iteration_v5.get('eligible_count')}
planned_execution_count={iteration_v5.get('planned_execution_count')}
execution_count={iteration_v5.get('execution_count')}
actual_selected_count={iteration_v5.get('actual_selected_count')}
row_set_identity_status={iteration_v5.get('row_set_identity_status')}
```

## Proxy Row-Set Selection Before Execution

```text
phase={retention_selection.get('phase')}
pool_count={retention_selection.get('pool_count')}
eligible_count={retention_selection.get('eligible_count')}
selected_count={retention_selection.get('selected_count')}
proxy_group_count={retention_selection.get('proxy_group_count')}
skipped_duplicate_proxy_count={retention_selection.get('skipped_duplicate_proxy_count')}
```

## Actual Row-Set Representative Selection

```text
status={actual_selection.get('status')}
row_set_identity_status={actual_selection.get('row_set_identity_status')}
requested_count={actual_selection.get('requested_count')}
executed_count={actual_selection.get('executed_count')}
actual_group_count={actual_selection.get('actual_group_count')}
selected_count={actual_selection.get('selected_count')}
duplicate_actual_rowset_count={actual_selection.get('duplicate_actual_rowset_count')}
skipped_duplicate_actual_count={actual_selection.get('skipped_duplicate_actual_count')}
selected_strategy_names={selected_names}
```

## Duplicate Actual Row-Set Groups

{chr(10).join(duplicate_lines)}

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
print(f"actual_selection_status={actual_selection.get('status')}")
print(f"row_set_identity_status={actual_selection.get('row_set_identity_status')}")
'@ | python -
```

Expected successful path:

```text
wrote=docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_iteration_loop_v5.md
status=ok
phase=candidates_evaluated
actual_selection_status=ok
row_set_identity_status=all_distinct
```

Accepted hold path:

```text
actual_selection_status=shortfall
```

- [ ] **Step 2: Inspect v5 pilot log decision lines**

Run:

```powershell
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_iteration_loop_v5.md -Pattern 'status=|phase=|planned_execution_count|actual_selected_count|row_set_identity_status|duplicate_actual_rowset_count|selected_strategy_names'
```

Expected:

```text
The output includes status, phase, planned_execution_count, row_set_identity_status, duplicate_actual_rowset_count, and selected_strategy_names.
```

---

## Task 4: Analyze v5 Actual Row-Set Decision

**Files:**
- Read: `backtest\temp\wide_v1_iteration_v5_20260424.json`
- Create: `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v5_actual_rowset_selection.md`

- [ ] **Step 1: Run v5 decision script**

Run:

```powershell
python scripts\analyze_wide_v1_v5_actual_rowset_selection.py `
  --runtime-path backtest\temp\wide_v1_iteration_v5_20260424.json `
  --output docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v5_actual_rowset_selection.md
```

Expected successful path:

```text
decision=PROCEED_TO_PROMOTE_WFO_PLAN
next_command=$writing-plans Wide v1 v5 promote 및 WFO 검증 계획 작성
row_set_identity_status=all_distinct
selected_count=10
requested_count=10
wrote=docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v5_actual_rowset_selection.md
```

Accepted hold paths:

```text
decision=HOLD_V5_RUNTIME_FAILURE
next_command=$brainstorming Wide v1 v5 runtime failure recovery 설계
```

or

```text
decision=HOLD_V5_ACTUAL_ROW_SET_SHORTFALL
next_command=$brainstorming Wide v1 v6 actual row-set generation expansion 설계
```

- [ ] **Step 2: Inspect v5 decision report**

Run:

```powershell
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v5_actual_rowset_selection.md -Pattern 'decision=|next_command=|row_set_identity_status=|requested_count=|selected_count=|duplicate_actual_rowset_count='
```

Expected:

```text
The output includes decision, next_command, row_set_identity_status, requested_count, selected_count, and duplicate_actual_rowset_count.
```

---

## Task 5: Write v5 Runtime Validation PR Report

**Files:**
- Read: `backtest\temp\wide_v1_iteration_v5_20260424.json`
- Read: `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_iteration_loop_v5.md`
- Read: `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v5_actual_rowset_selection.md`
- Create: `docs\pr\2026-04-24_wide_v1_v5_candidate_count_10_actual_rowset_validation_pr.md`

- [ ] **Step 1: Generate PR report**

Run:

```powershell
@'
from __future__ import annotations

from pathlib import Path
from cli.research_v3_decision import read_runtime_json

runtime_path = Path("backtest/temp/wide_v1_iteration_v5_20260424.json")
runtime = read_runtime_json(runtime_path)
iteration_v5 = runtime.get("iteration_v5") or {}
selection = runtime.get("actual_rowset_selection") or {}
best = runtime.get("best_candidate") or {}
candidates = runtime.get("candidates") or []
decision_report = Path("docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v5_actual_rowset_selection.md").read_text(encoding="utf-8")
decision_line = next((line for line in decision_report.splitlines() if line.startswith("- decision=")), "")
next_command_line = next((line for line in decision_report.splitlines() if line.startswith("- next_command=")), "")

output_path = Path("docs/pr/2026-04-24_wide_v1_v5_candidate_count_10_actual_rowset_validation_pr.md")
report = f"""# Wide v1 v5 candidate_count=10 actual row-set validation PR 보고서

## 1. 목적

이번 PR은 `best_feature_mix_v5`를 실제 `candidate_count=10` 조건으로 실행하고, v5의 actual row-set representative selection이 promote/WFO로 넘어갈 수 있을 만큼 충분히 서로 다른 후보를 만들었는지 검증한다.

## 2. 전체 방향

```text
v4 actual row-set partially_distinct 확인
  -> v5 actual row-set representative selection 구현
  -> 이번 PR: v5 candidate_count=10 실제 실행
  -> actual row-set 대표 10개 확보 여부 판단
  -> 성공이면 promote/WFO 계획
  -> 부족하면 v6 후보 생성 확장 설계
  -> runtime 실패면 failure recovery 설계
```

## 3. 실행 입력

```text
runtime_path={runtime_path}
runtime_status={runtime.get('status')}
runtime_phase={runtime.get('phase')}
candidate_result_count={len(candidates)}
best_candidate={best.get('strategy_name')}
```

## 4. v5 실행 요약

```text
iteration_v5_status={iteration_v5.get('status')}
requested_count={iteration_v5.get('requested_count')}
eligible_count={iteration_v5.get('eligible_count')}
planned_execution_count={iteration_v5.get('planned_execution_count')}
execution_count={iteration_v5.get('execution_count')}
actual_selected_count={iteration_v5.get('actual_selected_count')}
row_set_identity_status={iteration_v5.get('row_set_identity_status')}
```

## 5. actual row-set 선택 결과

```text
selection_status={selection.get('status')}
row_set_identity_status={selection.get('row_set_identity_status')}
requested_count={selection.get('requested_count')}
selected_count={selection.get('selected_count')}
executed_count={selection.get('executed_count')}
actual_group_count={selection.get('actual_group_count')}
duplicate_actual_rowset_count={selection.get('duplicate_actual_rowset_count')}
skipped_duplicate_actual_count={selection.get('skipped_duplicate_actual_count')}
selected_strategy_names={selection.get('selected_strategy_names')}
```

## 6. 최종 결정

```text
{decision_line.removeprefix('- ')}
{next_command_line.removeprefix('- ')}
```

## 7. 전문가 관점 검토

퀀트 관점에서 v5 실행 검증은 promote/WFO 직전의 필수 gate다. 조건식이 새로워 보여도 실제 거래 목록이 같으면 독립 후보가 아니므로, actual row-set 대표 후보 수가 요청 수를 만족해야 한다.

CLI 개발 관점에서는 이번 실행이 기존 `stom_backtest.py discovery research` 경로를 그대로 사용하므로 메인 GUI/실거래 경로와 분리된다. runtime JSON, pilot log, decision report를 남겨 재현 가능성을 확보한다.

전체 프로그램 관점에서는 `backtest` 산출물은 stage하지 않고, 문서화된 판단만 커밋한다. strategy DB promotion과 WFO는 이 PR에서 실행하지 않는다.

## 8. 검증

```text
python scripts\\analyze_wide_v1_v5_actual_rowset_selection.py --runtime-path backtest\\temp\\wide_v1_iteration_v5_20260424.json --output docs\\research\\condition_research\\pilot_logs\\2026-04-24_wide_v1_v5_actual_rowset_selection.md
```

```text
python -m pytest tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q
```

```text
git diff --check --ignore-cr-at-eol
```

## 9. 다음 단계

결정 보고서의 `next_command`를 따른다. 성공 기준은 아래와 같다.

```text
actual_rowset_selection.status=ok
row_set_identity_status=all_distinct
selected_count >= requested_count
```
"""

output_path.write_text(report, encoding="utf-8")
print(f"wrote={output_path}")
print(decision_line)
print(next_command_line)
'@ | python -
```

Expected:

```text
wrote=docs\pr\2026-04-24_wide_v1_v5_candidate_count_10_actual_rowset_validation_pr.md
- decision=<decision from Task 4>
- next_command=<next command from Task 4>
```

- [ ] **Step 2: Inspect PR report**

Run:

```powershell
Select-String -Path docs\pr\2026-04-24_wide_v1_v5_candidate_count_10_actual_rowset_validation_pr.md -Pattern 'decision=|next_command=|selection_status=|row_set_identity_status=|selected_count='
```

Expected:

```text
The output includes decision, next_command, selection_status, row_set_identity_status, and selected_count.
```

---

## Task 6: Verification and Commit

**Files:**
- Stage only:
  - `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_iteration_loop_v5.md`
  - `docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v5_actual_rowset_selection.md`
  - `docs\pr\2026-04-24_wide_v1_v5_candidate_count_10_actual_rowset_validation_pr.md`
- Do not stage:
  - `backtest\temp\wide_v1_iteration_v5_20260424.json`
  - `backtest\csv\stock_bt_WideV1IterationV5_20260424__cand*.csv`
  - `backtest\graph\*.png`

- [ ] **Step 1: Run focused v5 unit tests**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q
```

Expected:

```text
7 passed
```

- [ ] **Step 2: Run whitespace check**

Run:

```powershell
cmd /c "git diff --check --ignore-cr-at-eol 2>&1"
```

Expected:

```text
No output.
```

- [ ] **Step 3: Confirm only intended docs are staged**

Run:

```powershell
git status --short --untracked-files=all
```

Expected:

```text
Untracked backtest artifacts may appear.
The three markdown report files are untracked or modified before staging.
No cli/*.py file is modified.
```

- [ ] **Step 4: Stage documentation only**

Run:

```powershell
git add docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_iteration_loop_v5.md
git add docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v5_actual_rowset_selection.md
git add docs/pr/2026-04-24_wide_v1_v5_candidate_count_10_actual_rowset_validation_pr.md
git status --short --untracked-files=no
```

Expected:

```text
A  docs/pr/2026-04-24_wide_v1_v5_candidate_count_10_actual_rowset_validation_pr.md
A  docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_iteration_loop_v5.md
A  docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v5_actual_rowset_selection.md
```

If any `backtest\` path appears as staged, unstage it with:

```powershell
git restore --staged backtest
```

- [ ] **Step 5: Commit v5 runtime validation report**

Run:

```powershell
git commit -m "Wide v1 v5 실제 실행 검증 결과를 기록한다" -m "best_feature_mix_v5 candidate_count=10 runtime을 실행하고 actual row-set representative selection 결과와 다음 판단 명령을 문서화한다." -m "Constraint: backtest runtime/csv/graph 산출물은 stage하지 않는다" -m "Confidence: high" -m "Scope-risk: narrow" -m "Directive: 결정 보고서의 next_command를 다음 superpower 단계로 사용한다" -m "Tested: python -m pytest tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q" -m "Tested: python scripts\analyze_wide_v1_v5_actual_rowset_selection.py --runtime-path backtest\temp\wide_v1_iteration_v5_20260424.json --output docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v5_actual_rowset_selection.md" -m "Tested: git diff --check --ignore-cr-at-eol"
```

Expected:

```text
[feature/wide-v1-v5-candidate-count-10-runtime-validation <hash>] Wide v1 v5 실제 실행 검증 결과를 기록한다
```

---

## Task 7: Merge Handoff

**Files:**
- Read: git history and status only

- [ ] **Step 1: Verify branch status after commit**

Run:

```powershell
git status --short --branch --untracked-files=all
git log --oneline --decorate --graph --max-count=8
```

Expected:

```text
Current branch is feature/wide-v1-v5-candidate-count-10-runtime-validation.
The latest commit is "Wide v1 v5 실제 실행 검증 결과를 기록한다".
Only untracked backtest artifacts may remain.
```

- [ ] **Step 2: Merge back to `STOM_Version_2U_C` with a merge point**

Run:

```powershell
git switch STOM_Version_2U_C
git merge --no-ff --no-commit feature/wide-v1-v5-candidate-count-10-runtime-validation
git commit -m "Wide v1 v5 실제 실행 검증 결과를 병합한다" -m "v5 candidate_count=10 실제 실행 결과와 actual row-set representative selection 결정을 2U_C 기준 이력에 merge point로 통합한다." -m "Constraint: backtest 산출물은 병합하지 않고 문서화된 판단만 통합한다" -m "Confidence: high" -m "Scope-risk: narrow" -m "Directive: 다음 단계는 병합된 decision report의 next_command를 따른다" -m "Tested: git merge --no-ff --no-commit feature/wide-v1-v5-candidate-count-10-runtime-validation"
```

Expected:

```text
[STOM_Version_2U_C <merge-hash>] Wide v1 v5 실제 실행 검증 결과를 병합한다
```

- [ ] **Step 3: Create the next branch from the merge result**

If Task 4 decision is `PROCEED_TO_PROMOTE_WFO_PLAN`, run:

```powershell
git switch -c feature/wide-v1-v5-promote-wfo-validation-plan
```

Expected next command:

```text
$writing-plans Wide v1 v5 promote 및 WFO 검증 계획 작성
```

If Task 4 decision is `HOLD_V5_ACTUAL_ROW_SET_SHORTFALL`, run:

```powershell
git switch -c feature/wide-v1-v6-actual-rowset-generation-expansion-design
```

Expected next command:

```text
$brainstorming Wide v1 v6 actual row-set generation expansion 설계
```

If Task 4 decision is `HOLD_V5_RUNTIME_FAILURE`, run:

```powershell
git switch -c feature/wide-v1-v5-runtime-failure-recovery
```

Expected next command:

```text
$brainstorming Wide v1 v5 runtime failure recovery 설계
```

---

## Self-Review Checklist

- Spec coverage: The plan covers branch guard, preflight, v5 execution, runtime summary, actual row-set decision, PR report, verification, commit, merge point, and next branch creation.
- Placeholder scan: The plan has no undefined future implementation placeholders.
- Type consistency: Runtime keys match current v5 implementation: `iteration_v5`, `actual_rowset_selection`, `selected_strategy_names`, `row_set_identity_status`, `planned_execution_count`, and `actual_selected_count`.
- Scope control: No code refactor or CLI behavior change is included. This is an execution and documentation plan only.
- Safety: Backtest artifacts are explicitly excluded from staging, and every git operation uses explicit paths or named branches.
