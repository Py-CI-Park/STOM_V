# Wide v1 Retention-Aware Candidate Count 5 Pilot

## 목적

Wide v1 CLI baseline GUI compare가 `PASS`된 뒤 Retention-Aware 후보 5개 자동 백테스트를 재개하고, 후보별 실행 결과와 ranking/cleanup 상태를 확인한다.

## 전체 플로우

```text
[Wide v1 CLI baseline PASS]
        |
        v
[runtime-preflight]
        |
        v
[discovery research --run-candidates --candidate-count 5]
        |
        v
[candidate ranking / cleanup 확인]
        |
        v
[PASS_FOR_EXECUTION]
        |
        v
[다음: 후보 결과 분석 및 반복 개선 루프 v2 설계]
```

## runtime DB path 검증

```text
setting_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\setting.db
strategy_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\strategy.db
backtest_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\backtest.db
stock_back_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_tick_back.db
stock_back_db_usable=True
```

`STOM_V.wt-dev`라는 폴더명 자체에 의존하는 것이 아니라, 현재 운용 `_database` 경로를 명시적으로 가리키는 방식으로 실행했다. 운용 폴더명이 바뀌면 `STOM_CLI_DATABASE_DIR`만 새 `_database` 경로로 바꾸면 된다.

## 실행 조건

```text
baseline_csv=backtest/csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv
base_buy_strategy=ResearchTest_Tick_B_090000_092800_Wide_20260419
base_sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
start=20250101
end=20251231
timeframe=tick
avg_time=30
betting=20
start_time=090000
end_time=092800
engines=32
candidate_count=5
candidate_timeout=900
min_estimated_retention=0.4
candidate_pool_multiplier=3
retention_fallback=enabled
retention_penalty=enabled
```

## 결과 요약

```text
status=ok
phase=candidates_evaluated
candidate_count_observed=5
retention_selection.status=ok
retention_selection.phase=retention_candidates_selected
retention_selection.pool_count=15
retention_selection.passed_count=15
retention_selection.fallback_count=0
retention_selection.selected_count=5
best_candidate=WideV1RetentionCand5_20260422__cand003
```

## 후보별 결과

```text
rank=1
strategy_name=WideV1RetentionCand5_20260422__cand003
expression=66.999 <= 시가총액 < 2_580
estimated_retention=0.9003346605760071
retention_filter_passed=True
retention_fallback_used=False
candidate_status=success
trade_count=36918
trade_count_retention=0.9018247551115128
promotion_passed=True
promotion_score=10943.034141541459
retention_penalty=1.0
adjusted_score=10943.034141541459
csv_path=backtest/csv\stock_bt_WideV1RetentionCand5_20260422__cand003_20260422213825.csv
cleanup=best_candidate_kept

rank=2
strategy_name=WideV1RetentionCand5_20260422__cand004
expression=0.009 <= 체결강도 < 55.94
estimated_retention=0.90004152722476
retention_filter_passed=True
retention_fallback_used=False
candidate_status=success
trade_count=37990
trade_count_retention=0.9280113344895815
promotion_passed=True
promotion_score=9079.558772203623
retention_penalty=1.0
adjusted_score=9079.558772203623
csv_path=backtest/csv\stock_bt_WideV1RetentionCand5_20260422__cand004_20260422214123.csv
cleanup=loser_candidate_deleted

rank=3
strategy_name=WideV1RetentionCand5_20260422__cand002
expression=15.894 <= 등락율 < 25
estimated_retention=0.9007255050443365
retention_filter_passed=True
retention_fallback_used=False
candidate_status=success
trade_count=37582
trade_count_retention=0.9180448005471823
promotion_passed=True
promotion_score=8220.553561775416
retention_penalty=1.0
adjusted_score=8220.553561775416
csv_path=backtest/csv\stock_bt_WideV1RetentionCand5_20260422__cand002_20260422213529.csv
cleanup=loser_candidate_deleted

rank=4
strategy_name=WideV1RetentionCand5_20260422__cand005
expression=1_800 <= 당일거래대금 < 3_586
estimated_retention=0.90004152722476
retention_filter_passed=True
retention_fallback_used=False
candidate_status=success
trade_count=39179
trade_count_retention=0.9570559640423089
promotion_passed=True
promotion_score=4736.37085278282
retention_penalty=1.0
adjusted_score=4736.37085278282
csv_path=backtest/csv\stock_bt_WideV1RetentionCand5_20260422__cand005_20260422214417.csv
cleanup=loser_candidate_deleted

rank=5
strategy_name=WideV1RetentionCand5_20260422__cand001
expression=90029.999 <= 시분초 < 90_055
estimated_retention=0.9012629161882894
retention_filter_passed=True
retention_fallback_used=False
candidate_status=success
trade_count=40478
trade_count_retention=0.9887876493148008
promotion_passed=True
promotion_score=1415.192693028745
retention_penalty=1.0
adjusted_score=1415.192693028745
csv_path=backtest/csv\stock_bt_WideV1RetentionCand5_20260422__cand001_20260422213230.csv
cleanup=loser_candidate_deleted
```

## cleanup 결과

```text
attempted_count=4
deleted_count=4
kept_count=1
failed_count=0
kept_strategy=WideV1RetentionCand5_20260422__cand003
kept_reason=best_candidate_kept
remaining_candidate_rows=['WideV1RetentionCand5_20260422__cand003']
```

`cleanup_best_candidate=False`가 기본이므로 best candidate 1개가 남는 것은 정상 정책이다. loser 후보 4개는 삭제됐다.

## 판정

```text
decision=PASS_FOR_EXECUTION
reason=candidate_count=5 executed and ranking data is present.
next_command=$brainstorming Wide v1 후보 결과 분석 및 반복 개선 루프 v2 설계
```

## 해석

- 후보 5개 모두 full-year tick 백테스트가 완료됐다.
- 후보 5개 모두 `estimated_retention >= 0.4`를 만족했고 fallback은 사용되지 않았다.
- 후보 5개 모두 실제 `trade_count_retention >= 0.9`로 retention gate를 충분히 만족했다.
- best candidate는 `cand003`이며, 기준 대비 거래 수를 `40937 -> 36918`로 줄이면서 promotion score와 adjusted score가 가장 높았다.

## 남은 리스크

- best candidate는 최종 채택이 아니다.
- 이번 단계는 WFO/promote 검증이 아니다.
- row-level CSV parity와 후보별 상세 오차 원인 분석은 별도 단계로 남을 수 있다.
- 후보 표현식의 한글 컬럼명이 일부 CLI JSON에서 mojibake로 보이므로, 다음 리포트 단계에서 원본 CSV/조건식 컬럼명 표시 품질을 점검할 필요가 있다.
- runtime JSON/CSV/graph 산출물은 Git에 포함하지 않는다.
