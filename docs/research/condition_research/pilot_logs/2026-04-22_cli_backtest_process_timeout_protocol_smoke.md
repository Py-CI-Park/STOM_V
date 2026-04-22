# CLI BackTest Process Timeout Protocol Smoke

## 목적

BackTest process가 `backtest_process_started` 이후 timeout되던 원인을 확인하고, CLI가 BackTest/Total protocol checkpoint를 관측할 수 있는지 검증했다.

## 실행 조건

```text
buy=ResearchTest_Tick_B_090000_092800_Wide_20260419
sell=ResearchTest_Tick_S_090000_092800_Wide_20260419
period=20250102~20250103
time=090000~092800
timeframe=tick
avg_time=30
runtime_db=C:\System_Trading\STOM\STOM_V.wt-dev\_database
```

## 중간 실패 증거

초기 smoke에서 `BackTest`는 `backtest_child_waiting_mq_first`까지 진행한 뒤 engine worker가 전략 실행 중 중단됐다.

```text
first_failure=KeyError: '시장미시구조분석'
second_failure=KeyError: '시장리스크분석'
failure_location=backtest/backengine_kiwoom_tick.py Strategy()
interpretation=CLI DICT_SET이 tick engine이 요구하는 시장 분석 설정 키를 보장하지 않아 engine이 중단되고 Total 완료 신호가 오지 않았다.
```

수정:

```text
시장미시구조분석=False
시장리스크분석=False
scope=CLI headless DICT_SET sync and child env payload
```

## smoke 4 결과

```text
status=success
checkpoint_status=success
last_checkpoint=csv_detected
elapsed_seconds=45.594
csv_path=backtest/csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422170357.csv
trade_count=194
win_rate=34.54
avg_profit_pct=-0.56
total_profit_pct=-3.63
total_profit_krw=-1081812
mdd_pct=3.88
tpi=0.70
protocol_diag_log_count=91
protocol_diag_last=BackTest.backtest_child_completed
```

## smoke 32 결과

```text
status=success
checkpoint_status=success
last_checkpoint=csv_detected
elapsed_seconds=60.125
csv_path=backtest/csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422170552.csv
trade_count=194
win_rate=34.54
avg_profit_pct=-0.56
total_profit_pct=-3.63
total_profit_krw=-1081812
mdd_pct=3.93
tpi=0.70
protocol_diag_log_count=91
protocol_diag_last=BackTest.backtest_child_completed
```

## 판정

```text
decision=PASS_FOR_CLI_SMOKE_AND_PROTOCOL_PATH
reason=4/32 engine smoke 모두 metrics와 CSV를 생성했고, protocol checkpoint 로그가 BackTest completion까지 남았다. 기존 timeout은 단순 runtime 문제가 아니라 CLI DICT_SET 누락 키로 engine worker가 중단되며 완료 신호가 막힌 결과였다.
```

## 남은 해석

```text
success_json에는 backtest_process_diagnostics가 포함되지 않는다.
error/timeout JSON에는 output diagnostic field로 보존되도록 보강했다.
success run의 protocol checkpoint는 stderr log에 남는다.
```

## 다음 단계

```text
$brainstorming Wide v1 CLI Baseline Backtest Gate 및 GUI 결과 비교 설계
```

단, PR 전에는 현재 브랜치 변경 사항을 먼저 보고서화하고 merge할 수 있다.
