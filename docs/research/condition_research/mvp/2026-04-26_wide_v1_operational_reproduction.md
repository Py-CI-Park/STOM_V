# Wide v1 operational reproduction

## Purpose

이 문서는 `WideV1Final_B_20260425` MVP 후보를 다른 세션에서 재현하기 위한 최소 명령어 세트다.

## Constants

```text
FINAL_BUY=WideV1Final_B_20260425
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
```

## Step 1: Restore final buy strategy into strategy DB

```powershell
@'
from pathlib import Path
from cli.paths import DB_STRATEGY
from cli.strategy_generator import save_strategy_to_db

strategy_name = "WideV1Final_B_20260425"
code = Path(r"utility\ai_agent\WideV1Final_B_20260425.py").read_text(encoding="utf-8")
result = save_strategy_to_db(DB_STRATEGY, strategy_name, code, "buy")
print(result)
'@ | python -
```

Expected:

```text
status=ok with action created or updated
```

## Step 2: Verify strategy loads from DB

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

## Step 3: Runtime preflight

```powershell
$preflight = python .\stom_backtest.py runtime-preflight --buy WideV1Final_B_20260425 --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 --start 20250101 --end 20251231 --timeframe tick --betting 20 --avg-time 30 --start-time 90000 --end-time 92800 --engines 32 --timeout 900
$preflight | Set-Content -Path backtest\temp\wide_v1_mvp_freeze_preflight_20260426.json -Encoding UTF8
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

Expected:

```text
PowerShell exits 0 and the JSON file contains status=ok.
```

## Step 4: WFO window dry-run

```powershell
python .\stom_backtest.py wfo --start 20250101 --end 20251231 --train-window-days 120 --test-window-days 30 --step-days 30 --purge-days 1 --embargo-days 1 --dry-run -o backtest\temp\wide_v1_mvp_freeze_wfo_windows_20260426.json
```

Expected:

```text
round_count=8
```

## Step 5: Optional full WFO reproduction

```powershell
python .\stom_backtest.py wfo --buy WideV1Final_B_20260425 --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 --start 20250101 --end 20251231 --train-window-days 120 --test-window-days 30 --step-days 30 --purge-days 1 --embargo-days 1 --objective tpi --method grid --max-iter 1 --engines 32 --timeframe tick --betting 20 --avg-time 30 --start-time 90000 --end-time 92800 --timeout 900 --format json -o backtest\temp\wide_v1_mvp_freeze_wfo_report_20260426.json
```

Expected based on the frozen run:

```text
status=ok
round_count=8
success_rate=1.0
mean_oos_metric=0.5762499999999999
mean_trade_count=2131.75
zero_trade_rounds=0
```

## Step 6: Unit and regression verification

```powershell
python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q
python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q
cmd /c "git diff --check --ignore-cr-at-eol 2>&1"
```

Expected from the frozen branch:

```text
113 passed
167 passed
diff check prints no whitespace errors
```

## Operational caution

- 이 재현 절차는 백테스트와 WFO 검증 재현 절차다.
- 실거래 전에는 소액 파일럿, 슬리피지, 호가 체결, API 장애 대응을 별도 검증해야 한다.
- `utility/strategy.db`는 런타임 DB이므로 Git diff 대신 `utility/ai_agent/WideV1Final_B_20260425.py` 스냅샷을 기준 artifact로 사용한다.
