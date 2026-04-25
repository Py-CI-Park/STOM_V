# Wide v1 v5 Promote And WFO Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only when the user explicitly requests parallel subagents. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wide v1 v5 풀런에서 실제 row-set 기준으로 선택된 대표 후보를 영구 매수 전략으로 승격하고, 독립 WFO 검증으로 MVP 종료 가능 여부를 판정한다.

**Architecture:** `discovery research`는 후보 생성과 실제 row-set 선택까지만 담당한다. 이번 단계는 v5 런타임 JSON과 후보 CSV를 증거로 고정하고, 선택 대표 후보 `cand017`을 기존 베이스 매수 전략에 필터 결합해 DB 전략으로 재생성한 뒤 `wfo` 서브커맨드로 검증한다. 검증 결과는 promotion preset 기준으로 평가하고, 통과 시 MVP freeze 단계로, 실패 시 WFO 실패 분석 단계로 분기한다.

**Tech Stack:** Python, PowerShell, SQLite strategy DB, STOM CLI `stom_backtest.py`, `cli.strategy_loader`, `cli.strategy_generator`, `cli.wfo`, `cli.ai_controller.AIBacktestController.evaluate_walk_forward_result`, Markdown reports.

---

## Current Evidence

- 현재 브랜치: `feature/wide-v1-v5-promote-wfo-validation-plan`
- 기준 브랜치: `STOM_Version_2U_C`
- v5 풀런 merge commit: `08f25c5a Wide v1 v5 풀런 결과를 병합한다`
- v5 풀런 runtime: `backtest/temp/wide_v1_v5_observable_full_20260425.json`
- v5 풀런 결과 문서:
  - `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_observable_full_rerun.md`
  - `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_observable_full_actual_rowset_selection.md`
- v5 결과 요약:
  - `elapsed_seconds=2680.031`
  - `executed candidates=17`
  - `requested_count=10`
  - `selected_count=10`
  - `actual_group_count=11`
  - `duplicate_actual_rowset_count=6`
  - `skipped_duplicate_actual_count=7`
  - `row_set_identity_status=all_distinct`
- 대표 1순위 후보:
  - `strategy_name=WideV1IterationV5ObservableFull_20260425__cand017`
  - `expression=66.999 <= 시가총액 < 2_580 and 등락율 > 4.83`
  - `candidate_csv=backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand017_20260425125216.csv`
  - `trade_count=27601`
  - `duration_seconds=142.672`
  - `selected_as_best=True`
  - `actual_rowset_selected=True`
- 중요한 제약:
  - v5 풀런은 `--cleanup-best-candidate`를 사용했다.
  - 따라서 `WideV1IterationV5ObservableFull_20260425__cand017` 같은 임시 후보 전략이 DB에 남아 있다고 가정하면 안 된다.
  - 이번 단계는 후보를 새로 탐색하는 단계가 아니라, 선택된 후보의 조건식을 기존 베이스 전략에 결합해 영구 전략으로 재생성하는 단계다.

## Target Flow

```text
v5 full runtime JSON
        |
        v
selected actual row-set representatives
        |
        v
primary representative cand017 fixed
        |
        v
recreate permanent buy strategy from base strategy + cand017 filter
        |
        v
runtime-preflight
        |
        v
WFO dry-run window schedule
        |
        v
WFO execution
        |
        v
promotion evaluation
        |
        +--> pass: MVP freeze/release documentation branch
        |
        +--> fail: WFO failure analysis branch
```

## Files

- Create: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_manifest.json`
  - v5 선택 대표 후보 10개의 전략명, 조건식, CSV, 실제 row-set 순위, 거래 수, 후보별 소요 시간을 고정 기록한다.
- Create: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_manifest.md`
  - 사람이 읽는 promote 후보 명세서다.
- Create: `utility/ai_agent/WideV1Final_B_20260425.py`
  - DB에 저장할 최종 매수 전략 코드 스냅샷이다.
- Create: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_windows.json`
  - WFO dry-run window schedule 증거다.
- Create: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_report.json`
  - 실제 WFO 실행 결과다.
- Create: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_wfo_decision.md`
  - promotion 통과/실패 판정 보고서다.
- Create: `docs/pr/2026-04-25_wide_v1_v5_promote_wfo_validation_pr.md`
  - 이전 PR 형식에 맞춘 한글 Markdown PR 보고서다.
- Runtime DB update: `utility/strategy.db`
  - `stockbuy` 테이블에 `WideV1Final_B_20260425`를 저장한다.
  - DB 파일은 변경 여부를 확인하되, 바이너리/운영 DB 정책에 맞춰 커밋 대상에서 제외한다.
- Protected runtime data:
  - `backtest/graph/`는 건드리지 않는다.
  - `backtest/temp/`와 신규 백테스트 CSV는 증거 확인용이며 커밋하지 않는다.

## Constants

Use these values consistently in every command:

```text
RUNTIME_PATH=backtest\temp\wide_v1_v5_observable_full_20260425.json
FINAL_BUY=WideV1Final_B_20260425
PRIMARY_CANDIDATE=WideV1IterationV5ObservableFull_20260425__cand017
BASE_BUY=WideV1IterationV2_20260423__cand005
SELL=ResearchTest_Tick_S_090000_092800_Wide_20260419
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
PROMOTION_PRESET=balanced
```

## Promotion Criteria

Primary decision uses the existing balanced preset from `cli/promotion.py`:

```text
min_rounds=2
min_success_rate=0.60
min_mean_oos_metric=0.00
min_avg_trade_count=50.0
```

Secondary report also prints conservative comparison:

```text
min_rounds=3
min_success_rate=0.80
min_mean_oos_metric=0.10
min_avg_trade_count=100.0
```

Decision rule:

- Balanced pass: `PROCEED_TO_MVP_FREEZE`
- Balanced fail with some trading rounds: `PROCEED_TO_WFO_FAILURE_ANALYSIS`
- All WFO rounds no-trade: `PROCEED_TO_AUTO_RELAX_OR_CONDITION_REPAIR_PLAN`

---

### Task 1: Validate Branch And Evidence Inputs

**Files:**
- Read: `backtest/temp/wide_v1_v5_observable_full_20260425.json`
- Read: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_observable_full_actual_rowset_selection.md`

- [ ] **Step 1: Confirm branch and clean tracked state**

Run:

```powershell
git status --short --branch --untracked-files=no
```

Expected:

```text
## feature/wide-v1-v5-promote-wfo-validation-plan
```

If tracked changes are present, inspect them with:

```powershell
git diff --stat
git diff -- docs\superpowers\plans\2026-04-25-wide-v1-v5-promote-wfo-validation.md
```

Proceed only after confirming they are part of this plan or unrelated user changes that must not be touched.

- [ ] **Step 2: Confirm runtime JSON exists and contains selected actual row-set representatives**

Run:

```powershell
@'
import json
from pathlib import Path

runtime_path = Path(r"backtest\temp\wide_v1_v5_observable_full_20260425.json")
data = json.loads(runtime_path.read_text(encoding="utf-8"))
selection = data["actual_rowset_selection"]
print("status=", data.get("status"))
print("phase=", data.get("phase"))
print("selection_status=", selection.get("status"))
print("selected_count=", selection.get("selected_count"))
print("first_selected=", selection.get("selected_strategy_names", [None])[0])
'@ | python -
```

Expected output:

```text
status= ok
phase= candidates_evaluated
selection_status= ok
selected_count= 10
first_selected= WideV1IterationV5ObservableFull_20260425__cand017
```

- [ ] **Step 3: Confirm the primary candidate CSV exists**

Run:

```powershell
Test-Path "backtest\csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand017_20260425125216.csv"
```

Expected:

```text
True
```

- [ ] **Step 4: Confirm base buy and sell strategies are loadable**

Run:

```powershell
@'
from cli.paths import DB_STRATEGY
from cli.strategy_loader import load_strategy_from_db

checks = [
    ("WideV1IterationV2_20260423__cand005", "buy"),
    ("ResearchTest_Tick_S_090000_092800_Wide_20260419", "sell"),
]
for name, strategy_type in checks:
    result = load_strategy_from_db(DB_STRATEGY, name, strategy_type)
    print(strategy_type, name, result.get("status"), len(result.get("code", "")))
'@ | python -
```

Expected:

```text
buy WideV1IterationV2_20260423__cand005 ok 1 이상의 코드 길이
sell ResearchTest_Tick_S_090000_092800_Wide_20260419 ok 1 이상의 코드 길이
```

The integer does not need to match a fixed value; it must be greater than zero.

### Task 2: Create Promote Manifest

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_manifest.json`
- Create: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_manifest.md`

- [ ] **Step 1: Generate machine-readable and human-readable manifest**

Run:

```powershell
@'
import json
from pathlib import Path

runtime_path = Path(r"backtest\temp\wide_v1_v5_observable_full_20260425.json")
json_path = Path(r"docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_promote_manifest.json")
md_path = Path(r"docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_promote_manifest.md")

data = json.loads(runtime_path.read_text(encoding="utf-8"))
selection = data["actual_rowset_selection"]
selected_names = selection["selected_strategy_names"]
candidates = {item["strategy_name"]: item for item in data["candidates"]}
durations = {
    item["strategy_name"]: item
    for item in (data.get("runtime_timing") or {}).get("candidate_durations", [])
}

manifest_candidates = []
for order, name in enumerate(selected_names, start=1):
    candidate = candidates[name]
    timing = durations.get(name, {})
    manifest_candidates.append({
        "order": order,
        "strategy_name": name,
        "expression": candidate["expression"],
        "candidate_csv": candidate.get("candidate_csv") or timing.get("candidate_csv"),
        "rank": candidate.get("rank"),
        "rank_score": candidate.get("rank_score"),
        "selected_as_best": candidate.get("selected_as_best", False),
        "actual_rowset_selected": candidate.get("actual_rowset_selected", False),
        "trade_count": timing.get("trade_count"),
        "trade_count_retention": timing.get("trade_count_retention"),
        "duration_seconds": timing.get("duration_seconds"),
        "cleanup": candidate.get("cleanup"),
    })

primary = manifest_candidates[0]
manifest = {
    "status": "ok",
    "source_runtime": str(runtime_path),
    "final_buy_strategy": "WideV1Final_B_20260425",
    "base_buy_strategy": "WideV1IterationV2_20260423__cand005",
    "sell_strategy": "ResearchTest_Tick_S_090000_092800_Wide_20260419",
    "primary_candidate": primary,
    "actual_rowset_selection": {
        "requested_count": selection.get("requested_count"),
        "selected_count": selection.get("selected_count"),
        "actual_group_count": selection.get("actual_group_count"),
        "duplicate_actual_rowset_count": selection.get("duplicate_actual_rowset_count"),
        "skipped_duplicate_actual_count": selection.get("skipped_duplicate_actual_count"),
        "row_set_identity_status": data.get("iteration_v5", {}).get("row_set_identity_status"),
    },
    "candidates": manifest_candidates,
}

json_path.parent.mkdir(parents=True, exist_ok=True)
json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

lines = [
    "# Wide v1 v5 promote manifest",
    "",
    "## Decision",
    "",
    "- decision=PRIMARY_CAND017_FOR_WFO",
    "- final_buy_strategy=WideV1Final_B_20260425",
    "- base_buy_strategy=WideV1IterationV2_20260423__cand005",
    "- sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419",
    f"- source_runtime={runtime_path}",
    "",
    "## Actual row-set selection",
    "",
    f"- requested_count={selection.get('requested_count')}",
    f"- selected_count={selection.get('selected_count')}",
    f"- actual_group_count={selection.get('actual_group_count')}",
    f"- duplicate_actual_rowset_count={selection.get('duplicate_actual_rowset_count')}",
    f"- skipped_duplicate_actual_count={selection.get('skipped_duplicate_actual_count')}",
    "",
    "## Selected representatives",
    "",
    "| order | strategy | expression | csv | trades | seconds |",
    "| ---: | --- | --- | --- | ---: | ---: |",
]
for item in manifest_candidates:
    lines.append(
        f"| {item['order']} | `{item['strategy_name']}` | `{item['expression']}` | "
        f"`{item['candidate_csv']}` | {item.get('trade_count')} | {item.get('duration_seconds')} |"
    )

md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json_path)
print(md_path)
'@ | python -
```

Expected output:

```text
docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_promote_manifest.json
docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_promote_manifest.md
```

- [ ] **Step 2: Inspect the manifest primary candidate**

Run:

```powershell
@'
import json
from pathlib import Path

manifest = json.loads(Path(r"docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_promote_manifest.json").read_text(encoding="utf-8"))
primary = manifest["primary_candidate"]
print(primary["strategy_name"])
print(primary["expression"])
print(primary["candidate_csv"])
print(primary["selected_as_best"], primary["actual_rowset_selected"])
'@ | python -
```

Expected:

```text
WideV1IterationV5ObservableFull_20260425__cand017
66.999 <= 시가총액 < 2_580 and 등락율 > 4.83
backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand017_20260425125216.csv
True True
```

### Task 3: Promote Primary Candidate To A Permanent Strategy

**Files:**
- Create: `utility/ai_agent/WideV1Final_B_20260425.py`
- Runtime DB update: `utility/strategy.db`

- [ ] **Step 1: Read branch-local strategy guidance**

Run:

```powershell
Get-Content utility\ai_agent\strategy.txt -TotalCount 80
Get-Content utility\ai_agent\rules.txt -TotalCount 80
```

Expected:

```text
두 파일의 전략 작성 지침이 비어 있지 않게 출력된다.
```

This step satisfies the strategy generation rule in `AGENTS.md`. Do not edit these guidance files.

- [ ] **Step 2: Recreate final buy strategy code and save it to DB**

Run:

```powershell
@'
import json
from pathlib import Path

from cli.paths import DB_STRATEGY
from cli.strategy_generator import generate_buy_filter_strategy, save_strategy_to_db
from cli.strategy_loader import load_strategy_from_db

manifest_path = Path(r"docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_promote_manifest.json")
snapshot_path = Path(r"utility\ai_agent\WideV1Final_B_20260425.py")

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
final_name = manifest["final_buy_strategy"]
base_name = manifest["base_buy_strategy"]
expression = manifest["primary_candidate"]["expression"]

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
    "name": "WideV1Final_B_20260425",
    "action": "created"
  },
  "snapshot": "utility\\ai_agent\\WideV1Final_B_20260425.py",
  "expression": "66.999 <= 시가총액 < 2_580 and 등락율 > 4.83"
}
```

If `action` is `"updated"`, continue only after confirming the existing `WideV1Final_B_20260425` was created by this same task attempt.

- [ ] **Step 3: Verify DB reload of final strategy**

Run:

```powershell
@'
from cli.paths import DB_STRATEGY
from cli.strategy_loader import load_strategy_from_db

result = load_strategy_from_db(DB_STRATEGY, "WideV1Final_B_20260425", "buy")
print(result.get("status"))
print("66.999 <= 시가총액 < 2_580 and 등락율 > 4.83" in result.get("code", ""))
print("self.Buy()" in result.get("code", ""))
'@ | python -
```

Expected:

```text
ok
True
True
```

### Task 4: Runtime Preflight

**Files:**
- Runtime output: `backtest/temp/wide_v1_v5_promote_preflight_20260425.json`

- [ ] **Step 1: Run preflight for the promoted strategy**

Run:

```powershell
$preflight = python .\stom_backtest.py runtime-preflight --buy WideV1Final_B_20260425 --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 --start 20250101 --end 20251231 --timeframe tick --betting 20 --avg-time 30 --start-time 90000 --end-time 92800 --engines 32 --timeout 900
$preflight | Set-Content -Path backtest\temp\wide_v1_v5_promote_preflight_20260425.json -Encoding UTF8
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

Expected:

```text
PowerShell 프롬프트가 오류 없이 반환된다.
```

- [ ] **Step 2: Inspect preflight status**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path(r"backtest\temp\wide_v1_v5_promote_preflight_20260425.json")
data = json.loads(path.read_text(encoding="utf-8"))
print(data.get("status"))
print(data.get("phase"))
print(data.get("message"))
'@ | python -
```

Expected:

```text
ok
두 번째 줄에는 preflight phase가 출력된다.
세 번째 줄에는 preflight message가 출력된다.
```

If the command returns a strategy syntax or missing-variable error, stop WFO execution and create `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_preflight_failure.md` with the error text, then proceed to final report with decision `PROMOTE_BLOCKED_BY_PREFLIGHT`.

### Task 5: WFO Dry-Run Schedule

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_windows.json`

- [ ] **Step 1: Generate WFO windows without running backtests**

Run:

```powershell
python .\stom_backtest.py wfo --start 20250101 --end 20251231 --train-window-days 120 --test-window-days 30 --step-days 30 --purge-days 1 --embargo-days 1 --dry-run -o docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_wfo_windows.json
```

Expected:

```text
PowerShell 프롬프트가 오류 없이 반환된다.
```

- [ ] **Step 2: Verify window count is enough for balanced and conservative criteria**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path(r"docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_wfo_windows.json")
data = json.loads(path.read_text(encoding="utf-8"))
print(data["status"])
print(data["round_count"])
print(data["windows"][0])
print(data["windows"][-1])
'@ | python -
```

Expected:

```text
dry-run
3 이상의 round_count가 출력된다.
첫 번째 window dict가 출력된다.
마지막 window dict가 출력된다.
```

If `round_count < 3`, change only the WFO window parameters in this order:

```text
train_window_days=90
test_window_days=30
step_days=30
purge_days=1
embargo_days=1
```

Then rerun Step 1 and Step 2.

### Task 6: Execute WFO Validation

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_report.json`

- [ ] **Step 1: Run WFO for the promoted final strategy**

Run:

```powershell
python .\stom_backtest.py wfo --buy WideV1Final_B_20260425 --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 --start 20250101 --end 20251231 --train-window-days 120 --test-window-days 30 --step-days 30 --purge-days 1 --embargo-days 1 --objective tpi --method grid --max-iter 1 --engines 32 --timeframe tick --betting 20 --avg-time 30 --start-time 90000 --end-time 92800 --timeout 900 --format json -o docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_wfo_report.json
```

Expected:

```text
PowerShell 프롬프트가 오류 없이 반환된다.
```

Runtime expectation:

- This is heavier than one candidate backtest because each WFO round runs train optimization plus out-of-sample test.
- With `MAX_ITER=1`, no parameter grid expansion is performed beyond fixed config.
- If the dry-run window count is 8, practical upper bound is roughly `8 * one backtest runtime + overhead`.
- If elapsed time exceeds 2 hours, interrupt once, keep partial logs, and write a runtime failure report before retrying with `train_window_days=150`, `test_window_days=45`, `step_days=45`.

- [ ] **Step 2: Inspect WFO summary**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path(r"docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_wfo_report.json")
data = json.loads(path.read_text(encoding="utf-8"))
summary = data.get("summary", {})
print(data.get("status"))
print("round_count=", summary.get("round_count"))
print("success_rate=", summary.get("success_rate"))
print("mean_oos_metric=", summary.get("mean_oos_metric"))
print("mean_trade_count=", summary.get("mean_trade_count"))
print("zero_trade_rounds=", summary.get("zero_trade_rounds"))
'@ | python -
```

Expected:

```text
ok
round_count= 3 이상의 정수
success_rate= 0.0 이상 1.0 이하 실수
mean_oos_metric= 실수 또는 None
mean_trade_count= 실수 또는 None
zero_trade_rounds= 0 이상의 정수
```

### Task 7: Evaluate Promotion Decision

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_wfo_decision.md`

- [ ] **Step 1: Evaluate WFO result with balanced and conservative criteria**

Run:

```powershell
@'
import json
from pathlib import Path

from cli.ai_controller import AIBacktestController
from cli.promotion import resolve_promotion_criteria

wfo_path = Path(r"docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_wfo_report.json")
manifest_path = Path(r"docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_promote_manifest.json")
decision_path = Path(r"docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_promote_wfo_decision.md")

wfo = json.loads(wfo_path.read_text(encoding="utf-8"))
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
controller = AIBacktestController()

evaluations = {}
for preset in ("balanced", "conservative"):
    criteria = resolve_promotion_criteria(preset)
    evaluations[preset] = controller.evaluate_walk_forward_result(
        wfo,
        min_rounds=criteria["min_rounds"],
        min_success_rate=criteria["min_success_rate"],
        min_mean_oos_metric=criteria["min_mean_oos_metric"],
        min_avg_trade_count=criteria["min_avg_trade_count"],
    )
    evaluations[preset]["criteria"] = criteria

balanced = evaluations["balanced"]
summary = wfo.get("summary", {})
round_count = int(summary.get("round_count", 0) or 0)
zero_trade_rounds = int(summary.get("zero_trade_rounds", 0) or 0)

if balanced.get("passed"):
    decision = "PROCEED_TO_MVP_FREEZE"
    next_command = "$writing-plans Wide v1 MVP freeze 및 운영 재현 문서 작성"
elif round_count > 0 and zero_trade_rounds >= round_count:
    decision = "PROCEED_TO_AUTO_RELAX_OR_CONDITION_REPAIR_PLAN"
    next_command = "$brainstorming Wide v1 v5 WFO no-trade recovery 설계"
else:
    decision = "PROCEED_TO_WFO_FAILURE_ANALYSIS"
    next_command = "$brainstorming Wide v1 v5 WFO failure analysis 설계"

primary = manifest["primary_candidate"]
lines = [
    "# Wide v1 v5 promote WFO decision",
    "",
    "## Decision",
    "",
    f"- decision={decision}",
    f"- next_command={next_command}",
    f"- final_buy_strategy={manifest['final_buy_strategy']}",
    f"- primary_candidate={primary['strategy_name']}",
    f"- primary_expression={primary['expression']}",
    f"- source_csv={primary['candidate_csv']}",
    "",
    "## WFO summary",
    "",
    f"- status={wfo.get('status')}",
    f"- round_count={summary.get('round_count')}",
    f"- success_rate={summary.get('success_rate')}",
    f"- mean_oos_metric={summary.get('mean_oos_metric')}",
    f"- mean_trade_count={summary.get('mean_trade_count')}",
    f"- zero_trade_rounds={summary.get('zero_trade_rounds')}",
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
    "- v5는 후보 생성과 실제 row-set 중복 제거까지 완료한 데이터 분석 단계다.",
    "- 이 문서는 대표 후보를 운영 후보 전략으로 승격할 수 있는지 WFO로 검증한 결과다.",
    "- balanced 통과 시 현재 MVP 개발은 신규 후보 탐색보다 운영 재현성, 문서화, freeze 검증으로 이동한다.",
]

decision_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(decision)
print(next_command)
'@ | python -
```

Expected one of:

```text
PROCEED_TO_MVP_FREEZE
$writing-plans Wide v1 MVP freeze 및 운영 재현 문서 작성
```

```text
PROCEED_TO_WFO_FAILURE_ANALYSIS
$brainstorming Wide v1 v5 WFO failure analysis 설계
```

```text
PROCEED_TO_AUTO_RELAX_OR_CONDITION_REPAIR_PLAN
$brainstorming Wide v1 v5 WFO no-trade recovery 설계
```

- [ ] **Step 2: Read the decision document**

Run:

```powershell
Get-Content docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_promote_wfo_decision.md
```

Expected:

```text
# Wide v1 v5 promote WFO decision
...
```

### Task 8: Write PR Report

**Files:**
- Create: `docs/pr/2026-04-25_wide_v1_v5_promote_wfo_validation_pr.md`

- [ ] **Step 1: Create Korean Markdown PR report**

Run:

```powershell
@'
import json
from pathlib import Path

manifest = json.loads(Path(r"docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_promote_manifest.json").read_text(encoding="utf-8"))
wfo = json.loads(Path(r"docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_wfo_report.json").read_text(encoding="utf-8"))
decision = Path(r"docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_promote_wfo_decision.md").read_text(encoding="utf-8")
summary = wfo.get("summary", {})
primary = manifest["primary_candidate"]

decision_line = next(line for line in decision.splitlines() if line.startswith("- decision="))
next_line = next(line for line in decision.splitlines() if line.startswith("- next_command="))

lines = [
    "# Wide v1 v5 promote 및 WFO 검증 PR 보고서",
    "",
    "## 전체 계획",
    "",
    "1. v5 풀런 runtime JSON에서 실제 row-set 기준 대표 후보 10개를 고정 기록한다.",
    "2. 1순위 대표 후보 cand017의 조건식을 기존 베이스 매수 전략에 결합해 영구 전략 `WideV1Final_B_20260425`로 저장한다.",
    "3. runtime-preflight로 전략 로딩, 문법, 실행 전제 조건을 검증한다.",
    "4. WFO dry-run으로 train/test 창 수와 기간을 먼저 검증한다.",
    "5. 실제 WFO를 실행하고 balanced preset 기준으로 승격 여부를 판정한다.",
    "6. 결과에 따라 MVP freeze 또는 WFO 실패 분석으로 다음 브랜치를 분기한다.",
    "",
    "## 현재 계획 결과",
    "",
    f"- final_buy_strategy={manifest['final_buy_strategy']}",
    f"- base_buy_strategy={manifest['base_buy_strategy']}",
    f"- sell_strategy={manifest['sell_strategy']}",
    f"- primary_candidate={primary['strategy_name']}",
    f"- primary_expression={primary['expression']}",
    f"- primary_candidate_csv={primary['candidate_csv']}",
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
    "- 퀀트 관점: v5까지의 후보 생성은 데이터 분석과 조건식 생성 단계였고, 이번 단계는 신규 조건을 더 만드는 것이 아니라 선택 후보의 OOS 안정성을 확인하는 검증 단계다.",
    "- CLI 관점: `discovery research`에 WFO를 다시 붙이지 않고 별도 `wfo` 단계로 분리한 현재 구조가 맞다. 연구 루프는 빠른 후보 생성, WFO는 느린 최종 검증으로 역할이 분리된다.",
    "- 전체 프로젝트 관점: cand017 임시 전략은 cleanup으로 삭제될 수 있으므로, 런타임 JSON의 조건식을 베이스 전략에 재결합해 영구 전략명으로 저장한 뒤 검증하는 방식이 관리 가능하다.",
    "",
    "## 변경 파일",
    "",
    "- `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_manifest.json`",
    "- `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_manifest.md`",
    "- `utility/ai_agent/WideV1Final_B_20260425.py`",
    "- `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_windows.json`",
    "- `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_report.json`",
    "- `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_wfo_decision.md`",
    "",
    "## 검증",
    "",
    "- `runtime-preflight` 실행",
    "- `stom_backtest.py wfo --dry-run` 실행",
    "- `stom_backtest.py wfo` 실행",
    "- `python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q` 실행",
    "- `cmd /c \"git diff --check --ignore-cr-at-eol 2>&1\"` 실행",
    "",
    "## 남은 위험",
    "",
    "- WFO는 기간 분할 검증이므로 실거래 슬리피지, 호가 체결 우선순위, 장중 시스템 장애 위험을 완전히 대체하지 않는다.",
    "- `utility/strategy.db`는 런타임 DB라서 코드 리뷰에서 diff로 확인하기 어렵다. 최종 전략 코드는 `utility/ai_agent/WideV1Final_B_20260425.py` 스냅샷으로 함께 추적한다.",
]

path = Path(r"docs\pr\2026-04-25_wide_v1_v5_promote_wfo_validation_pr.md")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(path)
'@ | python -
```

Expected:

```text
docs\pr\2026-04-25_wide_v1_v5_promote_wfo_validation_pr.md
```

### Task 9: Verification

**Files:**
- Read: all files created in this plan

- [ ] **Step 1: Run focused unit tests**

Run:

```powershell
python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q
```

Expected:

```text
pytest exits 0 and prints a passed summary.
```

- [ ] **Step 2: Run research/CLI regression tests that protect the current split**

Run:

```powershell
python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q
```

Expected:

```text
pytest exits 0 and prints a passed summary.
```

- [ ] **Step 3: Run whitespace check**

Run:

```powershell
cmd /c "git diff --check --ignore-cr-at-eol 2>&1"
```

Expected:

```text
명령 출력이 없다.
```

- [ ] **Step 4: Review untracked/protected outputs before staging**

Run:

```powershell
git status --short
```

Expected includes created docs and `utility/ai_agent/WideV1Final_B_20260425.py`.

Do not stage:

```text
backtest/graph/
backtest/temp/
backtest/csv/
utility/strategy.db
```

### Task 10: Commit And Merge Point

**Files:**
- Stage only created report/snapshot files from this plan.

- [ ] **Step 1: Stage explicit files only**

Run:

```powershell
git add docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_manifest.json
git add docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_manifest.md
git add utility/ai_agent/WideV1Final_B_20260425.py
git add docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_windows.json
git add docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_report.json
git add docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_wfo_decision.md
git add docs/pr/2026-04-25_wide_v1_v5_promote_wfo_validation_pr.md
```

- [ ] **Step 2: Confirm staged files**

Run:

```powershell
git diff --cached --stat
```

Expected staged files are exactly the seven files listed in Step 1.

- [ ] **Step 3: Commit with Lore protocol**

Run:

```powershell
git commit -m "Wide v1 v5 승격 WFO 검증 결과를 기록한다" -m "v5 실제 row-set 대표 후보를 영구 전략 후보로 승격하고 WFO 검증 결과를 문서화한다. 연구 루프는 후보 생성과 중복 제거에 유지하고, WFO는 별도 최종 검증 단계로 분리한다." -m "Constraint: v5 임시 후보 전략은 cleanup으로 DB에서 삭제될 수 있어 runtime JSON의 조건식을 베이스 전략에 재결합해야 한다
Constraint: discovery research에는 WFO payload를 다시 추가하지 않는다
Rejected: discovery research 안에서 WFO를 직접 실행 | 후보 생성 루프가 다시 장시간 블로킹된다
Confidence: medium
Scope-risk: moderate
Directive: 최종 승격 여부는 WFO decision 문서의 next_command를 기준으로 분기한다
Tested: runtime-preflight, wfo dry-run, wfo execution, focused pytest, git diff check
Not-tested: live trading execution"
```

- [ ] **Step 4: Merge to `STOM_Version_2U_C`**

Run:

```powershell
git switch STOM_Version_2U_C
git merge --no-ff feature/wide-v1-v5-promote-wfo-validation-plan -m "Wide v1 v5 승격 WFO 검증을 병합한다" -m "v5 실제 row-set 대표 후보의 최종 검증 결과를 기준 브랜치에 통합한다." -m "Constraint: merge point를 남겨 후속 MVP freeze 또는 WFO 실패 분석 분기를 추적 가능하게 한다
Confidence: medium
Scope-risk: moderate
Directive: 후속 브랜치는 WFO decision의 next_command에 맞춰 새로 생성한다
Tested: feature branch verification completed
Not-tested: post-merge full upstream propagation"
```

- [ ] **Step 5: Re-run post-merge verification**

Run:

```powershell
python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q
cmd /c "git diff --check --ignore-cr-at-eol 2>&1"
```

Expected:

```text
pytest exits 0 and prints a passed summary.
diff check prints no output.
```

### Task 11: Create Next Branch

**Files:**
- Read: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_wfo_decision.md`

- [ ] **Step 1: Determine next branch from decision**

Run:

```powershell
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_promote_wfo_decision.md -Pattern "decision=|next_command="
```

Expected one of:

```text
decision=PROCEED_TO_MVP_FREEZE
next_command=$writing-plans Wide v1 MVP freeze 및 운영 재현 문서 작성
```

```text
decision=PROCEED_TO_WFO_FAILURE_ANALYSIS
next_command=$brainstorming Wide v1 v5 WFO failure analysis 설계
```

```text
decision=PROCEED_TO_AUTO_RELAX_OR_CONDITION_REPAIR_PLAN
next_command=$brainstorming Wide v1 v5 WFO no-trade recovery 설계
```

- [ ] **Step 2: Create the next branch**

If decision is `PROCEED_TO_MVP_FREEZE`, run:

```powershell
git switch -c feature/wide-v1-mvp-freeze-release-report
```

If decision is `PROCEED_TO_WFO_FAILURE_ANALYSIS`, run:

```powershell
git switch -c feature/wide-v1-v5-wfo-failure-analysis
```

If decision is `PROCEED_TO_AUTO_RELAX_OR_CONDITION_REPAIR_PLAN`, run:

```powershell
git switch -c feature/wide-v1-v5-wfo-no-trade-recovery
```

Expected:

```text
Switched to a new branch 'feature/wide-v1-mvp-freeze-release-report'
또는
Switched to a new branch 'feature/wide-v1-v5-wfo-failure-analysis'
또는
Switched to a new branch 'feature/wide-v1-v5-wfo-no-trade-recovery'
```

---

## Self-Review

Spec coverage:

- `Wide v1 v5 promote`: covered by Task 2 and Task 3.
- `WFO 검증`: covered by Task 5, Task 6, and Task 7.
- 실제 row-set 대표 후보 사용: covered by Task 1 and Task 2.
- cleanup으로 DB 후보가 삭제된 상황: covered by Task 3.
- 한글 PR 보고서: covered by Task 8.
- merge point 생성: covered by Task 10.
- 다음 단계 안내: covered by Task 11.

Red-flag scan:

- The plan contains concrete paths, exact commands, expected outputs, and decision branches.
- Code-changing commands include full inline Python content.
- No task depends on an undefined helper script.

Type and field consistency:

- Runtime fields are consistently read from `actual_rowset_selection`, `candidates`, and `runtime_timing.candidate_durations`.
- Final strategy name is consistently `WideV1Final_B_20260425`.
- Primary candidate is consistently `WideV1IterationV5ObservableFull_20260425__cand017`.
- WFO summary keys match `cli.wfo.run_walk_forward`: `round_count`, `success_rate`, `mean_oos_metric`, `mean_trade_count`, `zero_trade_rounds`.

## Execution Recommendation

Recommended execution mode: Inline Execution using `executing-plans`.

Reason:

- Most tasks are sequential and depend on the previous artifact: manifest -> strategy DB save -> preflight -> dry-run -> WFO -> decision.
- Subagents would add coordination overhead because the WFO result is the blocking artifact for all later work.
- If the user explicitly asks for subagents, only Task 8 PR report review can run in parallel after Task 7 completes.
