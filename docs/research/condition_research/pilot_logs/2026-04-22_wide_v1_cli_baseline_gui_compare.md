# Wide v1 CLI Baseline GUI Compare Pilot

## 목적

Wide v1 ResearchTest tick 조건식을 CLI full-year로 실행하고, 사용자가 GUI/STOM에서 직접 확보한 기준 결과와 비교해 후보 자동 백테스트 진입 가능 여부를 판단한다.

## 전체 플로우

```text
[PR #17 merge 완료]
        |
        v
[runtime-preflight]
        |
        v
[full-year CLI baseline]
        |
        v
[GUI 기준 결과와 비교]
        |
        v
[PASS]
        |
        v
[다음: candidate_count=5 실행 재개 설계]
```

## 실행 중 확인한 추가 보정

처음 full-year CLI 실행은 feature worktree의 빈 `_database/setting.db`를 읽으면서 실패했다.

```text
failure=utility.setting.py가 ./_database/setting.db를 직접 참조
error=no such table: main
root_cause=utility.setting_base는 CLI DB override를 따르지만 legacy utility.setting은 아직 하드코딩 경로를 사용
fix=utility.setting도 STOM_CLI_DATABASE_DIR 및 STOM_CLI_DB_* override를 따르도록 보강
```

또한 GUI 기준 조건에는 종목당 배팅금액 20,000,000원이 포함되어 있었다. CLI 기본값 `--betting 1`로 실행하면 거래 수가 달라지므로, 최종 비교 실행은 `--betting 20`을 명시했다.

```text
first_cli_trade_count_with_betting_1=42892
final_cli_trade_count_with_betting_20=40937
gui_trade_count=40937
```

## 실행 조건

```text
buy=ResearchTest_Tick_B_090000_092800_Wide_20260419
sell=ResearchTest_Tick_S_090000_092800_Wide_20260419
start=20250101
end=20251231
timeframe=tick
avg_time=30
betting=20
start_time=090000
end_time=092800
engines=32
timeout=900
runtime_db=C:\System_Trading\STOM\STOM_V.wt-dev\_database
```

## preflight 결과

```text
status=ok
failed_checks=[]
validation_errors=[]
timeframe_match=ok
buy_status=ok
sell_status=ok
stock_back_db_usable=True
stock_back_db_integrity=table_probe_only
```

## CLI baseline 결과

```text
status=success
message=None
checkpoint_status=success
last_checkpoint=csv_detected
elapsed_seconds=162.782
csv_path=backtest/csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv
csv_exists=True
back_count=1638
trade_count=40937
```

주요 checkpoint:

```text
engine_data_load_completed.back_count=1638
back_count_ready.back_count=1638
backtest_process_started=present
backtest_process_finished=present
csv_detected=present
```

## GUI 기준

```text
gui_csv=C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv
back_count=1638
trade_count=40937
win_rate=30.02
avg_profit_pct=-0.68
total_profit_pct=-695.09
total_profit_krw=-5564960005
mdd_pct=693.76
tpi=0.60
max_hold_count=40
avg_hold_time=228.19
```

## 비교 결과

```text
back_count: cli=1638 gui=1638 diff=0.0 diff_ratio=0.0
trade_count: cli=40937 gui=40937 diff=0.0 diff_ratio=0.0
win_rate: cli=30.02 gui=30.02 diff=0.0 diff_ratio=0.0
avg_profit_pct: cli=-0.68 gui=-0.68 diff=0.0 diff_ratio=0.0
total_profit_pct: cli=-695.09 gui=-695.09 diff=0.0 diff_ratio=0.0
total_profit_krw: cli=-5564960005 gui=-5564960005 diff=0.0 diff_ratio=0.0
mdd_pct: cli=693.8 gui=693.76 diff=0.03999999999996362 diff_ratio=5.7656826568213246e-05
tpi: cli=0.6 gui=0.6 diff=0.0 diff_ratio=0.0
max_hold_count: cli=40 gui=40 diff=0.0 diff_ratio=0.0
avg_hold_time: cli=228.19 gui=228.19 diff=0.0 diff_ratio=0.0
```

## 판정

```text
decision=PASS
reason=CLI full-year baseline matched GUI trade_count and back_count exactly.
next_command=$brainstorming Wide v1 Retention-Aware candidate_count=5 실행 재개 설계
```

## 남은 리스크

- 이번 gate는 scalar metric 비교다. row-level CSV parity는 필요 시 별도 설계로 분리한다.
- `mdd_pct`는 GUI 기준 693.76과 CLI 693.80으로 0.04p 차이가 있다. hard gate는 아니지만 후보 실행 전후 리포트에 계속 기록한다.
- 최종 실전 채택 전에는 `discovery promote` 또는 WFO 검증이 필요하다.
- runtime JSON, CSV, graph 산출물은 Git에 포함하지 않는다.
