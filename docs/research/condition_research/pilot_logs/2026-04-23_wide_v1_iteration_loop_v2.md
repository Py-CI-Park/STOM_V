# Wide v1 Iteration Loop v2 Pilot

## 목적

`cand003` 중심 v2 후보 생성 규칙이 기존 best candidate보다 더 나은 후보를 만들 수 있는지 확인한다.

## 전체 플로우

```text
[기존 best: WideV1RetentionCand5_20260422__cand003]
        |
        v
[v2 후보 생성: best_feature_mix]
        |
        v
[v2 candidate_count=5 실행]
        |
        v
[기존 cand003 기준과 비교]
        |
        v
[HOLD]
        |
        v
[다음: row-level 후보 차이 분석 설계]
```

## preflight

```text
status=ok
setting_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\setting.db
strategy_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\strategy.db
stock_back_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_tick_back.db
```

## 실행 조건

```text
baseline_csv=C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_WideV1RetentionCand5_20260422__cand003_20260422213825.csv
base_buy_strategy=WideV1RetentionCand5_20260422__cand003
sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
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
iteration_v2_mode=best_feature_mix
iteration_v2_best_candidate=WideV1RetentionCand5_20260422__cand003
iteration_v2_primary_feature=B_시가총액
iteration_v2_secondary_features=B_체결강도,B_등락율,B_당일거래대금,B_시분초
```

## 실행 결과

```text
status=ok
phase=candidates_evaluated
candidate_count_observed=5
best_candidate=WideV1IterationV2_20260423__cand005
best_adjusted_score=1115.0276473855229
baseline_adjusted_score=10943.034141541459
best_trade_count=36642
best_trade_count_retention=0.9925239720461564
promotion_passed=True
cleanup_failed_count=0
decision=HOLD
```

## 후보별 결과

```text
rank=1
strategy_name=WideV1IterationV2_20260423__cand005
expression=시가총액 중심 조건 + 시분초 보조 조건
candidate_status=success
trade_count=36642
trade_count_retention=0.9925239720461564
promotion_passed=True
adjusted_score=1115.0276473855229

rank=2
strategy_name=WideV1IterationV2_20260423__cand004
expression=시가총액 중심 조건 + 당일거래대금 보조 조건
candidate_status=success
trade_count=36754
trade_count_retention=0.9955577225201798
promotion_passed=True
adjusted_score=683.3603687036441

rank=3
strategy_name=WideV1IterationV2_20260423__cand003
expression=시가총액 중심 조건 + 시분초 보조 조건
candidate_status=success
trade_count=36751
trade_count_retention=0.9954764613467685
promotion_passed=True
adjusted_score=604.1326092090056

rank=4
strategy_name=WideV1IterationV2_20260423__cand001
expression=시가총액 중심 조건 + 체결강도 보조 조건
candidate_status=success
trade_count=36799
trade_count_retention=0.99677664012135
promotion_passed=True
adjusted_score=483.7262560108513

rank=5
strategy_name=WideV1IterationV2_20260423__cand002
expression=시가총액 중심 조건 + 시분초 보조 조건
candidate_status=success
trade_count=36889
trade_count_retention=0.9992144753236903
promotion_passed=True
adjusted_score=177.53012717023753
```

## cleanup 결과

```text
attempted_count=4
deleted_count=4
kept_count=1
failed_count=0
kept_strategy=WideV1IterationV2_20260423__cand005
kept_reason=best_candidate_kept
```

## 판정

```text
decision=HOLD
reason=v2 executed but did not improve over cand003 baseline or needs row-level analysis.
next_command=$brainstorming Wide v1 row-level 후보 차이 분석 설계
```

## 해석

- v2 후보 5개 모두 full-year tick 백테스트와 promotion gate를 통과했다.
- cleanup 실패는 없었다.
- 하지만 v2 best adjusted_score는 `1115.0276473855229`로 기존 cand003 기준 `10943.034141541459`보다 낮다.
- 따라서 v2 규칙은 실행 가능하지만, 기존 best를 개선하지 못했다.
- 바로 candidate_count=10으로 확장하지 않는다.
- 다음 단계는 row-level 후보 차이 분석으로, cand003이 강했던 손실 제거 구간과 v2 후보들이 놓친 구간을 비교해야 한다.

## 남은 리스크

- v2 실행 명령의 한글 feature 인자가 runtime JSON에서 mojibake로 보인다.
- v2 후보가 모두 실행은 됐지만 기존 best보다 score가 낮다.
- scalar score만으로는 왜 v2가 개선 실패했는지 충분히 설명하기 어렵다.
- row-level CSV 비교가 필요하다.
- 최종 채택 전에는 promote/WFO 검증이 필요하다.
