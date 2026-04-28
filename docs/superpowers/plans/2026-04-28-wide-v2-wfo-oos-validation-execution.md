# Wide v2 WFO/OOS Validation Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only if a later report-review task is split after WFO execution. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate the Wide v2 v5 winner `cand007` with an explicit WFO/OOS run and decide whether MVP freeze can start or condition-generation improvement must continue.

**Architecture:** Keep `discovery research` and `optimize-wide-v2` as candidate-generation paths only. Recreate the WFO handoff candidate as a permanent buy strategy by combining the current base strategy `WideV1Final_B_20260425` with the selected v5 expression, then run the existing `stom_backtest.py wfo` command as an independent out-of-sample validation step. Commit only curated Markdown/JSON evidence under `docs/`; do not commit raw backtest outputs or `utility/strategy.db`.

**Tech Stack:** Python 3.11, PowerShell, SQLite strategy DB, STOM CLI `stom_backtest.py`, `cli.strategy_loader`, `cli.strategy_generator`, `cli.wfo`, `cli.ai_controller.AIBacktestController.evaluate_walk_forward_result`, `cli.promotion`, pytest, git.

---

## Scope Check

Included:

- Validate current tracked state before WFO work.
- Fix the exact WFO/OOS target from the verified Wide v2 v5 run.
- Recreate `WideV2Final_B_20260428` as a permanent buy strategy for validation.
- Run strategy reload and runtime preflight.
- Run WFO dry-run window schedule.
- Run WFO/OOS validation through `stom_backtest.py wfo`.
- Evaluate WFO result with existing `balanced` and `conservative` promotion presets.
- Write Korean validation and PR-ready evidence reports.
- Commit only curated evidence and the strategy code snapshot.
- Route the next MVP step.

Excluded:

- No new v6/v7 design in this plan.
- No changes to candidate-generation logic.
- No broad CLI refactor.
- No WFO execution inside `discovery research`.
- No live-trading approval.
- No staging of raw runtime artifacts under `backtest/`.
- No staging of `utility/strategy.db`.

Protected paths:

- Do not stage `backtest/graph/`.
- Do not stage `backtest/temp/`.
- Do not stage `backtest/csv/`.
- Do not stage `utility/strategy.db`.
- Use explicit `git add` paths only.

## Current Evidence

Immediate predecessor validation:

```text
branch=feature/wide-v2-smoke-full-run-validation-exec
run_id=WideV2V5DirectV4ShortfallRecovery_20260428
candidate_count=10
max_rounds=1
elapsed=02:05:01.5510118
exit_code=0
status=ok
stop_reason=max_rounds_reached
leaderboard_count=20
actual_selected_count=10
row_set_identity_status=all_distinct
```

WFO handoff candidate:

```text
source_run=WideV2V5DirectV4ShortfallRecovery_20260428
source_candidate=WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007
source_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 3.535
source_adjusted_score=112.06250936127728
base_buy_strategy=WideV1Final_B_20260425
seed_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 4.83
sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
```

Interpretation:

```text
Wide v2 v5 candidate-generation recovery: verified
actual row-set diversity: verified
WFO/OOS validation: not yet run
live-trading approval: not allowed from current evidence
```

## Target Flow

```text
Wide v2 v5 full-run evidence
        |
        v
fix cand007 expression as WFO/OOS target
        |
        v
read strategy guidance and base strategy
        |
        v
create WideV2Final_B_20260428 snapshot + DB entry
        |
        v
runtime-preflight
        |
        v
WFO dry-run window schedule
        |
        v
WFO/OOS execution
        |
        v
balanced/conservative preset evaluation
        |
        +--> pass: MVP freeze / PR merge preparation
        |
        +--> fail with trades: WFO failure analysis and condition refinement
        |
        +--> all no-trade: condition relax or candidate-pool repair
```

## File Structure

- Read: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_direct_v4_shortfall_recovery_review.md`
  - Human-readable proof that candidate generation, direct_v4 shortfall recovery, and WFO handoff selection are healthy.
- Read: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_direct_v4_shortfall_recovery_summary.md`
  - Optimizer Markdown summary containing the WFO handoff fields.
- Read: `utility/ai_agent/strategy.txt`
  - Branch-local strategy-generation guidance required by `AGENTS.md`.
- Read: `utility/ai_agent/rules.txt`
  - Branch-local STOM syntax/rule guidance required by `AGENTS.md`.
- Create: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.json`
  - Machine-readable target manifest for WFO/OOS validation.
- Create: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.md`
  - Korean-readable target manifest.
- Create: `utility/ai_agent/WideV2Final_B_20260428.py`
  - Permanent buy strategy code snapshot generated from `WideV1Final_B_20260425` plus the cand007 filter expression.
- Runtime DB update, do not stage: `utility/strategy.db`
  - `stockbuy` entry for `WideV2Final_B_20260428`.
- Generated, do not stage: `backtest/temp/wide_v2_wfo_oos_preflight_20260428.json`
  - Runtime preflight output.
- Create: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_windows.json`
  - WFO dry-run window schedule.
- Create: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_report.json`
  - WFO/OOS result from `stom_backtest.py wfo`.
- Create: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_decision.md`
  - Korean decision report for MVP freeze or recovery branch.
- Create: `docs/pr/2026-04-28_wide_v2_wfo_oos_validation_pr.md`
  - Korean PR-ready report for this validation stage.

## Constants

Use these values consistently:

```text
FINAL_BUY=WideV2Final_B_20260428
BASE_BUY=WideV1Final_B_20260425
SELL=ResearchTest_Tick_S_090000_092800_Wide_20260419
SOURCE_RUN=WideV2V5DirectV4ShortfallRecovery_20260428
SOURCE_CANDIDATE=WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007
SOURCE_EXPRESSION=66.999 <= 시가총액 < 2_580 and 등락율 > 3.535
START=20250101
END=20251231
TIMEFRAME=tick
BETTING=20
AVG_TIME=30
START_TIME=90000
END_TIME=92800
ENGINES=32
TRAIN_WINDOW_DAYS=120
TEST_WINDOW_DAYS=30
STEP_DAYS=30
PURGE_DAYS=1
EMBARGO_DAYS=1
OBJECTIVE=tpi
METHOD=grid
MAX_ITER=1
TIMEOUT=1200
PROMOTION_PRESET=balanced
```

## Decision Criteria

Primary decision uses `cli.promotion.resolve_promotion_criteria("balanced")`:

```text
min_rounds=2
min_success_rate=0.60
min_mean_oos_metric=0.00
min_avg_trade_count=50.0
```

Secondary comparison uses `conservative`:

```text
min_rounds=3
min_success_rate=0.80
min_mean_oos_metric=0.10
min_avg_trade_count=100.0
```

Decision mapping:

```text
balanced pass
-> PROCEED_TO_MVP_FREEZE
-> $writing-plans Wide v2 MVP freeze 및 PR 병합 보고서 작성

balanced fail and at least one trading WFO round exists
-> PROCEED_TO_WFO_FAILURE_ANALYSIS
-> $brainstorming Wide v2 WFO/OOS failure analysis 및 조건식 개선 루프 보강 설계

all WFO rounds no-trade
-> PROCEED_TO_CONDITION_RELAX_OR_CANDIDATE_REPAIR
-> $brainstorming Wide v2 WFO/OOS no-trade recovery 및 조건식 완화 설계

preflight or WFO command failure
-> HOLD_WFO_RUNTIME_FAILURE
-> $brainstorming Wide v2 WFO/OOS runtime failure recovery 설계
```

---

### Task 1: Validate Branch And Input Evidence

**Files:**
- Read: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_direct_v4_shortfall_recovery_review.md`
- Read: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_direct_v4_shortfall_recovery_summary.md`

- [ ] **Step 1: Confirm branch and tracked state**

Run:

```powershell
git status --short --branch
```

Expected acceptable state:

```text
## feature/wide-v2-smoke-full-run-validation-exec
?? backtest/graph/
```

If tracked changes appear, inspect them with:

```powershell
git diff --stat
git diff --name-only
```

Proceed only when tracked changes are either part of this plan or unrelated user changes that will remain untouched.

- [ ] **Step 2: Confirm WFO handoff evidence exists**

Run:

```powershell
Select-String `
  -Path docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_direct_v4_shortfall_recovery_review.md `
  -Pattern 'final_best_candidate:', 'final_best_expression:', 'wfo_candidate:', 'row_set_identity_status'
```

Expected output includes:

```text
final_best_candidate: `WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007`
final_best_expression: `66.999 <= 시가총액 < 2_580 and 등락율 > 3.535`
wfo_candidate: `WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007`
row_set_identity_status: `all_distinct`
```

- [ ] **Step 3: Confirm WFO CLI is available**

Run:

```powershell
python .\stom_backtest.py wfo --help
```

Expected output contains:

```text
--train-window-days
--test-window-days
--buy
--sell
--step-days
--purge-days
--embargo-days
--objective
--method
--max-iter
--dry-run
```

If the command fails to import, stop this execution and route to:

```text
$brainstorming Wide v2 WFO/OOS CLI import failure recovery 설계
```

- [ ] **Step 4: Confirm base buy and sell strategies are loadable**

Run:

```powershell
@'
from cli.paths import DB_STRATEGY
from cli.strategy_loader import load_strategy_from_db

checks = [
    ("WideV1Final_B_20260425", "buy"),
    ("ResearchTest_Tick_S_090000_092800_Wide_20260419", "sell"),
]
for name, strategy_type in checks:
    result = load_strategy_from_db(DB_STRATEGY, name, strategy_type)
    print(strategy_type, name, result.get("status"), len(result.get("code", "")) > 0)
'@ | python -
```

Expected:

```text
buy WideV1Final_B_20260425 ok True
sell ResearchTest_Tick_S_090000_092800_Wide_20260419 ok True
```

### Task 2: Create WFO/OOS Manifest

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.json`
- Create: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.md`

- [ ] **Step 1: Generate manifest files**

Run:

```powershell
@'
import json
from pathlib import Path

json_path = Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_manifest.json")
md_path = Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_manifest.md")

manifest = {
    "status": "ok",
    "stage": "wide_v2_wfo_oos_validation",
    "final_buy_strategy": "WideV2Final_B_20260428",
    "base_buy_strategy": "WideV1Final_B_20260425",
    "sell_strategy": "ResearchTest_Tick_S_090000_092800_Wide_20260419",
    "source_run": "WideV2V5DirectV4ShortfallRecovery_20260428",
    "source_candidate": "WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007",
    "source_expression": "66.999 <= 시가총액 < 2_580 and 등락율 > 3.535",
    "source_adjusted_score": 112.06250936127728,
    "source_review": "docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_direct_v4_shortfall_recovery_review.md",
    "wfo_config": {
        "start": 20250101,
        "end": 20251231,
        "timeframe": "tick",
        "betting": "20",
        "avg_time": 30,
        "start_time": 90000,
        "end_time": 92800,
        "engines": 32,
        "train_window_days": 120,
        "test_window_days": 30,
        "step_days": 30,
        "purge_days": 1,
        "embargo_days": 1,
        "objective": "tpi",
        "method": "grid",
        "max_iter": 1,
        "timeout": 1200,
        "promotion_preset": "balanced"
    },
    "interpretation": "This is an OOS validation target, not a live-trading approval."
}

json_path.parent.mkdir(parents=True, exist_ok=True)
json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

lines = [
    "# Wide v2 WFO/OOS 검증 manifest",
    "",
    "## 검증 대상",
    "",
    f"- final_buy_strategy={manifest['final_buy_strategy']}",
    f"- base_buy_strategy={manifest['base_buy_strategy']}",
    f"- sell_strategy={manifest['sell_strategy']}",
    f"- source_run={manifest['source_run']}",
    f"- source_candidate={manifest['source_candidate']}",
    f"- source_expression={manifest['source_expression']}",
    f"- source_adjusted_score={manifest['source_adjusted_score']}",
    "",
    "## WFO 설정",
    "",
]
for key, value in manifest["wfo_config"].items():
    lines.append(f"- {key}={value}")
lines.extend([
    "",
    "## 해석",
    "",
    "- 이 manifest는 Wide v2 v5 winner를 WFO/OOS 검증 대상으로 고정한다.",
    "- WFO 통과 전에는 운영 승인 또는 실거래 승인으로 해석하지 않는다.",
])

md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json_path)
print(md_path)
'@ | python -
```

Expected:

```text
docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_manifest.json
docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_manifest.md
```

- [ ] **Step 2: Inspect manifest target**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_manifest.json")
data = json.loads(path.read_text(encoding="utf-8"))
print(data["final_buy_strategy"])
print(data["base_buy_strategy"])
print(data["source_candidate"])
print(data["source_expression"])
print(data["wfo_config"]["train_window_days"], data["wfo_config"]["test_window_days"])
'@ | python -
```

Expected:

```text
WideV2Final_B_20260428
WideV1Final_B_20260425
WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007
66.999 <= 시가총액 < 2_580 and 등락율 > 3.535
120 30
```

### Task 3: Recreate Permanent Wide v2 Validation Strategy

**Files:**
- Read: `utility/ai_agent/strategy.txt`
- Read: `utility/ai_agent/rules.txt`
- Create: `utility/ai_agent/WideV2Final_B_20260428.py`
- Runtime DB update, do not stage: `utility/strategy.db`

- [ ] **Step 1: Read branch-local strategy guidance**

Run:

```powershell
Get-Content utility\ai_agent\strategy.txt -TotalCount 80 -Encoding UTF8
Get-Content utility\ai_agent\rules.txt -TotalCount 80 -Encoding UTF8
```

Expected:

```text
Both commands print non-empty strategy guidance.
```

- [ ] **Step 2: Generate the final buy strategy snapshot and save it to DB**

Run:

```powershell
@'
import json
from pathlib import Path

from cli.paths import DB_STRATEGY
from cli.strategy_generator import generate_buy_filter_strategy, save_strategy_to_db
from cli.strategy_loader import load_strategy_from_db

manifest_path = Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_manifest.json")
snapshot_path = Path(r"utility\ai_agent\WideV2Final_B_20260428.py")

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
final_name = manifest["final_buy_strategy"]
base_name = manifest["base_buy_strategy"]
expression = manifest["source_expression"]

base_loaded = load_strategy_from_db(DB_STRATEGY, base_name, "buy")
if base_loaded.get("status") != "ok":
    raise SystemExit(f"base strategy load failed: {base_loaded}")

generated = generate_buy_filter_strategy(final_name, base_loaded["code"], [expression])
if generated.get("status") != "ok":
    raise SystemExit(f"strategy generation failed: {generated}")

snapshot_path.parent.mkdir(parents=True, exist_ok=True)
snapshot_path.write_text(generated["code"], encoding="utf-8")

saved = save_strategy_to_db(DB_STRATEGY, final_name, generated["code"], "buy")
print(json.dumps({
    "generated": generated.get("status"),
    "saved": saved,
    "snapshot": str(snapshot_path),
    "expression": expression,
}, ensure_ascii=False, indent=2))
'@ | python -
```

Expected:

```json
{
  "generated": "ok",
  "saved": {
    "status": "ok",
    "name": "WideV2Final_B_20260428",
    "action": "created"
  },
  "snapshot": "utility\\ai_agent\\WideV2Final_B_20260428.py",
  "expression": "66.999 <= 시가총액 < 2_580 and 등락율 > 3.535"
}
```

If `"action": "updated"` appears, continue only after confirming the existing DB row was created by this same WFO/OOS validation attempt.

- [ ] **Step 3: Verify DB reload of final strategy**

Run:

```powershell
@'
from cli.paths import DB_STRATEGY
from cli.strategy_loader import load_strategy_from_db

result = load_strategy_from_db(DB_STRATEGY, "WideV2Final_B_20260428", "buy")
code = result.get("code", "")
print(result.get("status"))
print("66.999 <= 시가총액 < 2_580 and 등락율 > 3.535" in code)
print("self.Buy()" in code)
print(len(code) > 0)
'@ | python -
```

Expected:

```text
ok
True
True
True
```

### Task 4: Runtime Preflight

**Files:**
- Generate, do not stage: `backtest/temp/wide_v2_wfo_oos_preflight_20260428.json`

- [ ] **Step 1: Run preflight for the promoted Wide v2 validation strategy**

Run:

```powershell
$env:PYTHONUTF8 = '1'
$PreflightPath = 'backtest\temp\wide_v2_wfo_oos_preflight_20260428.json'
New-Item -ItemType Directory -Force -Path 'backtest\temp' | Out-Null
$preflight = python .\stom_backtest.py runtime-preflight `
  --buy WideV2Final_B_20260428 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --betting 20 `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 1200
$preflight | Set-Content -Path $PreflightPath -Encoding UTF8
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

Expected:

```text
PowerShell returns without error.
```

- [ ] **Step 2: Inspect preflight status**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path(r"backtest\temp\wide_v2_wfo_oos_preflight_20260428.json")
data = json.loads(path.read_text(encoding="utf-8"))
print(data.get("status"))
print(bool(data.get("phase") or data.get("checks")))
print(bool(data.get("message") or data.get("summary") or data.get("checks")))
'@ | python -
```

Expected:

```text
ok
True
True
```

If the preflight status is not `ok`, create `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_preflight_failure.md` with the error fields and route to:

```text
$brainstorming Wide v2 WFO/OOS preflight failure recovery 설계
```

### Task 5: WFO Dry-Run Window Schedule

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_windows.json`

- [ ] **Step 1: Generate WFO windows without running backtests**

Run:

```powershell
python .\stom_backtest.py wfo `
  --start 20250101 `
  --end 20251231 `
  --train-window-days 120 `
  --test-window-days 30 `
  --step-days 30 `
  --purge-days 1 `
  --embargo-days 1 `
  --dry-run `
  -o docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_windows.json
```

Expected:

```text
PowerShell returns without error.
```

- [ ] **Step 2: Verify window count and range**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_windows.json")
data = json.loads(path.read_text(encoding="utf-8"))
print(data["status"])
print(data["round_count"] >= 3)
print(bool(data["windows"]))
print(data["windows"][0]["round"] == 1)
'@ | python -
```

Expected:

```text
dry-run
True
True
True
```

If `round_count < 3`, rerun Step 1 with:

```text
train_window_days=90
test_window_days=30
step_days=30
purge_days=1
embargo_days=1
```

Record the changed window configuration in the final decision report.

### Task 6: Execute WFO/OOS Validation

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_report.json`
- Generate, do not stage: `backtest/temp/wide_v2_wfo_oos_console_20260428.txt`
- Generate, do not stage: `backtest/temp/wide_v2_wfo_oos_run_meta_20260428.json`

- [ ] **Step 1: Run WFO/OOS validation**

Run:

```powershell
$env:PYTHONUTF8 = '1'
$WfoStart = Get-Date
$WfoReportPath = 'docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_report.json'
$WfoConsolePath = 'backtest\temp\wide_v2_wfo_oos_console_20260428.txt'
$WfoMetaPath = 'backtest\temp\wide_v2_wfo_oos_run_meta_20260428.json'
python .\stom_backtest.py wfo `
  --buy WideV2Final_B_20260428 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --train-window-days 120 `
  --test-window-days 30 `
  --step-days 30 `
  --purge-days 1 `
  --embargo-days 1 `
  --objective tpi `
  --method grid `
  --max-iter 1 `
  --engines 32 `
  --timeframe tick `
  --betting 20 `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --timeout 1200 `
  --format json `
  -o $WfoReportPath *> $WfoConsolePath
$WfoExit = $LASTEXITCODE
$WfoEnd = Get-Date
$WfoElapsed = $WfoEnd - $WfoStart
[PSCustomObject]@{
  run_id = 'wide_v2_wfo_oos_validation_20260428'
  started_at = $WfoStart.ToString('o')
  ended_at = $WfoEnd.ToString('o')
  elapsed = $WfoElapsed.ToString()
  exit_code = $WfoExit
  report_path = $WfoReportPath
  console_path = $WfoConsolePath
  final_buy_strategy = 'WideV2Final_B_20260428'
  sell_strategy = 'ResearchTest_Tick_S_090000_092800_Wide_20260419'
} | ConvertTo-Json | Set-Content -Encoding UTF8 $WfoMetaPath
$WfoElapsed
$WfoExit
if ($WfoExit -ne 0) { exit $WfoExit }
```

Expected:

```text
exit_code 0
docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_report.json exists
```

Runtime expectation:

```text
WFO is slower than a single candidate backtest because each window runs train optimization plus OOS test.
With MAX_ITER=1 and fixed param_space, the practical upper bound should stay within roughly 2 hours.
If the process exceeds 2 hours, stop once and write a runtime failure report from the console and metadata files before choosing a wider-window rerun.
```

- [ ] **Step 2: Inspect WFO summary**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_report.json")
data = json.loads(path.read_text(encoding="utf-8"))
summary = data.get("summary", {})
print(data.get("status"))
round_count = summary.get("round_count")
success_rate = summary.get("success_rate")
zero_trade_rounds = summary.get("zero_trade_rounds")
print("round_count_at_least_3=", isinstance(round_count, int) and round_count >= 3)
print("success_rate_in_range=", isinstance(success_rate, (int, float)) and 0.0 <= float(success_rate) <= 1.0)
print("has_oos_metric_key=", "mean_oos_metric" in summary)
print("has_mean_trade_count_key=", "mean_trade_count" in summary)
print("zero_trade_rounds_valid=", isinstance(zero_trade_rounds, int) and zero_trade_rounds >= 0)
'@ | python -
```

Expected:

```text
ok
round_count_at_least_3= True
success_rate_in_range= True
has_oos_metric_key= True
has_mean_trade_count_key= True
zero_trade_rounds_valid= True
```

If the JSON cannot be parsed with UTF-8, inspect the console file and route to:

```text
$brainstorming Wide v2 WFO/OOS report serialization recovery 설계
```

### Task 7: Evaluate WFO/OOS Decision

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_decision.md`

- [ ] **Step 1: Evaluate WFO result with balanced and conservative presets**

Run:

```powershell
@'
import json
from pathlib import Path

from cli.ai_controller import AIBacktestController
from cli.promotion import resolve_promotion_criteria

manifest_path = Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_manifest.json")
wfo_path = Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_report.json")
meta_path = Path(r"backtest\temp\wide_v2_wfo_oos_run_meta_20260428.json")
decision_path = Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_decision.md")

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
wfo = json.loads(wfo_path.read_text(encoding="utf-8"))
meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
controller = AIBacktestController()

evaluations = {}
for preset in ("balanced", "conservative"):
    criteria = resolve_promotion_criteria(preset)
    evaluation = controller.evaluate_walk_forward_result(
        wfo,
        min_rounds=criteria["min_rounds"],
        min_success_rate=criteria["min_success_rate"],
        min_mean_oos_metric=criteria["min_mean_oos_metric"],
        min_avg_trade_count=criteria["min_avg_trade_count"],
    )
    evaluation["criteria"] = criteria
    evaluations[preset] = evaluation

summary = wfo.get("summary", {})
round_count = int(summary.get("round_count", 0) or 0)
zero_trade_rounds = int(summary.get("zero_trade_rounds", 0) or 0)
trade_count_rounds = int(summary.get("trade_count_rounds", 0) or 0)

if evaluations["balanced"].get("passed"):
    decision = "PROCEED_TO_MVP_FREEZE"
    next_command = "$writing-plans Wide v2 MVP freeze 및 PR 병합 보고서 작성"
elif round_count > 0 and zero_trade_rounds >= round_count:
    decision = "PROCEED_TO_CONDITION_RELAX_OR_CANDIDATE_REPAIR"
    next_command = "$brainstorming Wide v2 WFO/OOS no-trade recovery 및 조건식 완화 설계"
elif trade_count_rounds > 0:
    decision = "PROCEED_TO_WFO_FAILURE_ANALYSIS"
    next_command = "$brainstorming Wide v2 WFO/OOS failure analysis 및 조건식 개선 루프 보강 설계"
else:
    decision = "HOLD_WFO_RUNTIME_FAILURE"
    next_command = "$brainstorming Wide v2 WFO/OOS runtime failure recovery 설계"

lines = [
    "# Wide v2 WFO/OOS 검증 판정",
    "",
    "## Decision",
    "",
    f"- decision={decision}",
    f"- next_command={next_command}",
    f"- final_buy_strategy={manifest['final_buy_strategy']}",
    f"- base_buy_strategy={manifest['base_buy_strategy']}",
    f"- sell_strategy={manifest['sell_strategy']}",
    f"- source_run={manifest['source_run']}",
    f"- source_candidate={manifest['source_candidate']}",
    f"- source_expression={manifest['source_expression']}",
    "",
    "## Runtime",
    "",
    f"- elapsed={meta.get('elapsed')}",
    f"- exit_code={meta.get('exit_code')}",
    "",
    "## WFO summary",
    "",
    f"- status={wfo.get('status')}",
    f"- round_count={summary.get('round_count')}",
    f"- success_count={summary.get('success_count')}",
    f"- success_rate={summary.get('success_rate')}",
    f"- metric={summary.get('metric')}",
    f"- mean_oos_metric={summary.get('mean_oos_metric')}",
    f"- best_oos_metric={summary.get('best_oos_metric')}",
    f"- trade_count_rounds={summary.get('trade_count_rounds')}",
    f"- zero_trade_rounds={summary.get('zero_trade_rounds')}",
    f"- mean_trade_count={summary.get('mean_trade_count')}",
    "",
    "## Balanced evaluation",
    "",
    f"- passed={evaluations['balanced'].get('passed')}",
    f"- reasons={evaluations['balanced'].get('reasons')}",
    f"- criteria={evaluations['balanced'].get('criteria')}",
    "",
    "## Conservative comparison",
    "",
    f"- passed={evaluations['conservative'].get('passed')}",
    f"- reasons={evaluations['conservative'].get('reasons')}",
    f"- criteria={evaluations['conservative'].get('criteria')}",
    "",
    "## Interpretation",
    "",
    "- Wide v2 v5는 조건식 자동 개선 루프의 후보 생성과 후보 선별 단계다.",
    "- 이번 WFO/OOS는 final candidate의 기간 분할 안정성을 확인하는 검증 단계다.",
    "- balanced 통과 전에는 실거래 승인으로 해석하지 않는다.",
    "- balanced 통과 시 MVP 종료 준비는 신규 조건식 생성보다 재현성, 문서화, PR merge point 생성으로 이동한다.",
]

decision_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(decision)
print(next_command)
'@ | python -
```

Expected one of:

```text
PROCEED_TO_MVP_FREEZE
$writing-plans Wide v2 MVP freeze 및 PR 병합 보고서 작성
```

```text
PROCEED_TO_WFO_FAILURE_ANALYSIS
$brainstorming Wide v2 WFO/OOS failure analysis 및 조건식 개선 루프 보강 설계
```

```text
PROCEED_TO_CONDITION_RELAX_OR_CANDIDATE_REPAIR
$brainstorming Wide v2 WFO/OOS no-trade recovery 및 조건식 완화 설계
```

```text
HOLD_WFO_RUNTIME_FAILURE
$brainstorming Wide v2 WFO/OOS runtime failure recovery 설계
```

- [ ] **Step 2: Inspect the decision document**

Run:

```powershell
Get-Content docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_decision.md -Encoding UTF8
```

Expected:

```text
# Wide v2 WFO/OOS 검증 판정
...
- decision=one of the four labels printed in Step 1
- next_command=the matching command printed in Step 1
```

### Task 8: Write Korean PR-Ready Report

**Files:**
- Create: `docs/pr/2026-04-28_wide_v2_wfo_oos_validation_pr.md`

- [ ] **Step 1: Generate Korean PR-ready report**

Run:

```powershell
@'
import json
from pathlib import Path

manifest = json.loads(Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_manifest.json").read_text(encoding="utf-8"))
wfo = json.loads(Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_report.json").read_text(encoding="utf-8"))
decision_text = Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_decision.md").read_text(encoding="utf-8")
summary = wfo.get("summary", {})

decision_line = next(line for line in decision_text.splitlines() if line.startswith("- decision="))
next_line = next(line for line in decision_text.splitlines() if line.startswith("- next_command="))

lines = [
    "# Wide v2 WFO/OOS 검증 PR 보고서",
    "",
    "## 전체 계획",
    "",
    "1. Wide v2 v5 full-run에서 선정된 cand007을 WFO/OOS 검증 대상으로 고정한다.",
    "2. 임시 후보 전략명이 DB에 남아 있다는 가정을 제거하고, 조건식을 `WideV1Final_B_20260425`에 재결합해 `WideV2Final_B_20260428`로 저장한다.",
    "3. runtime-preflight로 전략 로딩과 실행 전제를 확인한다.",
    "4. WFO dry-run으로 train/test window 수와 기간을 확인한다.",
    "5. 실제 WFO/OOS를 실행하고 balanced preset으로 MVP freeze 가능 여부를 판정한다.",
    "6. 결과에 따라 MVP freeze 또는 조건식 개선 루프 보강으로 분기한다.",
    "",
    "## 현재 계획 결과",
    "",
    f"- final_buy_strategy={manifest['final_buy_strategy']}",
    f"- base_buy_strategy={manifest['base_buy_strategy']}",
    f"- sell_strategy={manifest['sell_strategy']}",
    f"- source_candidate={manifest['source_candidate']}",
    f"- source_expression={manifest['source_expression']}",
    f"- wfo_status={wfo.get('status')}",
    f"- round_count={summary.get('round_count')}",
    f"- success_rate={summary.get('success_rate')}",
    f"- mean_oos_metric={summary.get('mean_oos_metric')}",
    f"- mean_trade_count={summary.get('mean_trade_count')}",
    f"- zero_trade_rounds={summary.get('zero_trade_rounds')}",
    decision_line,
    next_line,
    "",
    "## 검토 의견",
    "",
    "- 퀀트 관점: cand007은 `candidate_count=10` full-run에서 점수와 실제 row-set 기준으로 선택된 검증 대상이다. WFO/OOS 결과가 없으면 좋은 조건식 후보일 뿐 최종 조건식이 아니다.",
    "- CLI 관점: 연구 루프와 WFO를 분리한 구조가 맞다. 연구 루프는 후보를 빠르게 만들고, WFO는 느리지만 최종 후보만 검증한다.",
    "- 프로젝트 관점: raw backtest 산출물은 보호 경로에 남기고, 판단에 필요한 manifest, report, decision, PR 문서만 커밋한다.",
    "",
    "## 변경 파일",
    "",
    "- `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.json`",
    "- `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.md`",
    "- `utility/ai_agent/WideV2Final_B_20260428.py`",
    "- `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_windows.json`",
    "- `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_report.json`",
    "- `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_decision.md`",
    "",
    "## 검증",
    "",
    "- `python .\\stom_backtest.py runtime-preflight ...`",
    "- `python .\\stom_backtest.py wfo --dry-run ...`",
    "- `python .\\stom_backtest.py wfo ...`",
    "- `python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q`",
    "- `python scripts/verify_nonrelease_sync.py`",
    "- `git diff --check --ignore-cr-at-eol HEAD`",
    "",
    "## 남은 위험",
    "",
    "- WFO/OOS는 기간 분할 검증이며, 실거래 체결 품질과 장애 대응을 완전히 대체하지 않는다.",
    "- `utility/strategy.db`는 런타임 DB라 커밋하지 않는다. 전략 코드는 `utility/ai_agent/WideV2Final_B_20260428.py`로 추적한다.",
]

path = Path(r"docs\pr\2026-04-28_wide_v2_wfo_oos_validation_pr.md")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(path)
'@ | python -
```

Expected:

```text
docs\pr\2026-04-28_wide_v2_wfo_oos_validation_pr.md
```

### Task 9: Verification

**Files:**
- Read: all files created in this plan.

- [ ] **Step 1: Run focused WFO and strategy tests**

Run:

```powershell
python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q
```

Expected:

```text
pytest exits 0 and prints a passed summary.
```

- [ ] **Step 2: Run optimizer/report regression tests**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q
```

Expected:

```text
pytest exits 0 and prints a passed summary.
```

- [ ] **Step 3: Run non-release sync guard**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

- [ ] **Step 4: Run whitespace check**

Run:

```powershell
git diff --check --ignore-cr-at-eol HEAD
```

Expected:

```text
No output.
```

- [ ] **Step 5: Confirm protected artifacts are not staged**

Run:

```powershell
git status --short
```

Expected before staging includes only curated docs/snapshot plus protected untracked data:

```text
?? backtest/graph/
?? docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.json
?? docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.md
?? utility/ai_agent/WideV2Final_B_20260428.py
?? docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_windows.json
?? docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_report.json
?? docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_decision.md
?? docs/pr/2026-04-28_wide_v2_wfo_oos_validation_pr.md
```

Do not stage:

```text
backtest/graph/
backtest/temp/
backtest/csv/
utility/strategy.db
```

### Task 10: Commit Validation Evidence

**Files:**
- Stage only the curated evidence and snapshot files listed below.

- [ ] **Step 1: Stage explicit files only**

Run:

```powershell
git add docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_manifest.json
git add docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_manifest.md
git add utility\ai_agent\WideV2Final_B_20260428.py
git add docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_windows.json
git add docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_report.json
git add docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_decision.md
git add docs\pr\2026-04-28_wide_v2_wfo_oos_validation_pr.md
```

- [ ] **Step 2: Confirm staged files**

Run:

```powershell
git diff --cached --name-only
```

Expected exactly:

```text
docs/pr/2026-04-28_wide_v2_wfo_oos_validation_pr.md
docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_decision.md
docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.json
docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.md
docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_report.json
docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_windows.json
utility/ai_agent/WideV2Final_B_20260428.py
```

- [ ] **Step 3: Commit with Lore protocol**

Run:

```powershell
git commit -m "Wide v2 WFO/OOS 검증 결과를 기록한다" -m "Wide v2 v5 winner cand007을 영구 검증 전략으로 재생성하고 WFO/OOS 결과와 MVP 분기 판정을 문서화한다. 후보 생성 루프는 유지하고, 느린 기간 분할 검증은 별도 WFO 단계로 분리한다." -m "Constraint: utility/strategy.db와 raw backtest 산출물은 커밋하지 않는다
Constraint: WFO/OOS 통과 전에는 final candidate를 실거래 승인으로 표현하지 않는다
Rejected: optimize-wide-v2 내부에 WFO를 다시 연결 | 후보 생성 루프가 장시간 검증 단계와 결합된다
Confidence: medium
Scope-risk: moderate
Directive: 후속 단계는 WFO decision 문서의 next_command 기준으로 새 브랜치에서 진행한다
Tested: runtime-preflight, wfo dry-run, wfo execution, focused pytest, nonrelease sync guard, diff check
Not-tested: live trading execution"
```

Expected:

```text
git exits 0 and prints a commit summary for "Wide v2 WFO/OOS 검증 결과를 기록한다".
```

### Task 11: Next Branch Routing

**Files:**
- Read: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_decision.md`

- [ ] **Step 1: Read final routing**

Run:

```powershell
Select-String `
  -Path docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_decision.md `
  -Pattern 'decision=', 'next_command='
```

Expected one of:

```text
decision=PROCEED_TO_MVP_FREEZE
next_command=$writing-plans Wide v2 MVP freeze 및 PR 병합 보고서 작성
```

```text
decision=PROCEED_TO_WFO_FAILURE_ANALYSIS
next_command=$brainstorming Wide v2 WFO/OOS failure analysis 및 조건식 개선 루프 보강 설계
```

```text
decision=PROCEED_TO_CONDITION_RELAX_OR_CANDIDATE_REPAIR
next_command=$brainstorming Wide v2 WFO/OOS no-trade recovery 및 조건식 완화 설계
```

```text
decision=HOLD_WFO_RUNTIME_FAILURE
next_command=$brainstorming Wide v2 WFO/OOS runtime failure recovery 설계
```

- [ ] **Step 2: Create the next branch from the decision**

If decision is `PROCEED_TO_MVP_FREEZE`, run:

```powershell
git switch -c feature/wide-v2-mvp-freeze-pr-report
```

If decision is `PROCEED_TO_WFO_FAILURE_ANALYSIS`, run:

```powershell
git switch -c feature/wide-v2-wfo-oos-failure-analysis
```

If decision is `PROCEED_TO_CONDITION_RELAX_OR_CANDIDATE_REPAIR`, run:

```powershell
git switch -c feature/wide-v2-wfo-oos-no-trade-recovery
```

If decision is `HOLD_WFO_RUNTIME_FAILURE`, run:

```powershell
git switch -c feature/wide-v2-wfo-oos-runtime-recovery
```

Expected:

```text
Switched to the branch name selected from the decision table.
```

Do not merge to `STOM_Version_2U_C` inside this plan unless the WFO/OOS result is complete, tests pass, and the user explicitly wants this validation stage merged. The normal merge point should be created after the implementation evidence is verified and the PR report is ready.

---

## Self-Review

Spec coverage:

- Wide v2 WFO/OOS execution target: covered by Current Evidence, Constants, Task 2, and Task 3.
- Existing Superpowers process: plan is saved under `docs/superpowers/plans/` and requires `superpowers:executing-plans`.
- CLI/quant correctness: research loop remains candidate-generation only; WFO is separate OOS validation.
- Strategy-generation branch rule: Task 3 explicitly reads `utility/ai_agent/strategy.txt` and `utility/ai_agent/rules.txt`.
- PR-ready Korean report: Task 8.
- Protected artifact policy: Scope Check, File Structure, Task 9, and Task 10.
- Next MVP routing: Decision Criteria and Task 11.

Red-flag scan:

- Every command uses exact file paths and concrete strategy names.
- No code step depends on an undefined helper.
- No raw `backtest/` artifact is staged.
- `utility/strategy.db` is updated at runtime but intentionally not staged.

Type and field consistency:

- WFO summary keys match `cli.wfo.run_walk_forward`: `round_count`, `success_count`, `success_rate`, `metric`, `mean_oos_metric`, `best_oos_metric`, `trade_count_rounds`, `zero_trade_rounds`, `mean_trade_count`.
- Promotion criteria keys match `cli.promotion.resolve_promotion_criteria`: `min_rounds`, `min_success_rate`, `min_mean_oos_metric`, `min_avg_trade_count`.
- Strategy loader/generator calls match existing APIs: `load_strategy_from_db(DB_STRATEGY, name, strategy_type)`, `generate_buy_filter_strategy(name, base_code, [expression])`, `save_strategy_to_db(DB_STRATEGY, name, code, "buy")`.

## Execution Recommendation

Recommended next command:

```text
$executing-plans docs/superpowers/plans/2026-04-28-wide-v2-wfo-oos-validation-execution.md
```

Reason:

- This plan is sequential: manifest -> strategy recreation -> preflight -> dry-run -> WFO/OOS -> decision -> report.
- WFO/OOS execution is the blocking artifact, so parallel subagents add little value before the WFO report exists.
- After Task 7, a reviewer subagent can inspect the Korean report if the user wants an additional review before merge.
