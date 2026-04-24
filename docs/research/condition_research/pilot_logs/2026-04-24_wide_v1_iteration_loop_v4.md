# Wide v1 Iteration Loop v4 Pilot

## Purpose

Run `best_feature_mix_v4` with `candidate_count=10` and prepare actual row-set diversity verification.

## Inputs

```text
runtime_path=backtest\temp\wide_v1_iteration_v4_20260424.json
input_csv=C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv
score_reference_csv=C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv
mode=best_feature_mix_v4
candidate_count=10
candidate_timeout=900
cleanup_best_candidate=True
```

## Runtime Result

```text
status=ok
phase=candidates_evaluated
best_candidate=WideV1IterationV4_20260424__cand002
candidate_result_count=10
```

## Iteration v4 Candidate Pool

```text
status=ok
mode=best_feature_mix_v4
candidate_count=17
primary_feature=B_�ð��Ѿ�
trade_amount_feature=B_���ϰŷ����
type_counts={'v4_relax_trade_amount': 2, 'v4_repair_trade_amount': 1, 'v4_replace_secondary': 7, 'v4_tighten_secondary': 7, 'v4_control_keep_best': 1}
```

## Proxy Row-Set Selection

```text
phase=rowset_diverse_candidates_selected
pool_count=17
eligible_count=17
selected_count=10
proxy_group_count=10
skipped_duplicate_proxy_count=0
selected_proxy_groups=['0335bae70c7f7d18', '34618d58cbb77b83', 'acf892e14bc2e13e', '80cdcba9bfff4ba2', '66019bb42dde7bab', '667c552ef1c53ff6', 'dda7599c4f2ac0bd', 'f50108b17a8d27b0', 'aeb6579665bebe1e', 'f4833e0845011439']
```

## Quota Summary

- v4_relax_trade_amount: target=2, selected=2, shortfall=0
- v4_repair_trade_amount: target=2, selected=1, shortfall=1
- v4_replace_secondary: target=2, selected=5, shortfall=0
- v4_tighten_secondary: target=2, selected=2, shortfall=0

## Executed Family Distribution

```text
{'v4_replace_secondary': 5, 'v4_relax_trade_amount': 2, 'v4_repair_trade_amount': 1, 'v4_tighten_secondary': 2}
```

## Candidate Ranking

- rank=1 strategy=WideV1IterationV4_20260424__cand002 type=v4_replace_secondary adjusted_score=29708.648251307368 trade_count=29572.0 retention=0.7223782885897843 csv=backtest/csv\stock_bt_WideV1IterationV4_20260424__cand002_20260424165951.csv
- rank=2 strategy=WideV1IterationV4_20260424__cand006 type=v4_relax_trade_amount adjusted_score=28729.328168197055 trade_count=29792.0 retention=0.7277524000293133 csv=backtest/csv\stock_bt_WideV1IterationV4_20260424__cand006_20260424170855.csv
- rank=3 strategy=WideV1IterationV4_20260424__cand009 type=v4_replace_secondary adjusted_score=18364.16974700487 trade_count=34091.0 retention=0.8327674231135648 csv=backtest/csv\stock_bt_WideV1IterationV4_20260424__cand009_20260424171544.csv
- rank=4 strategy=WideV1IterationV4_20260424__cand001 type=v4_repair_trade_amount adjusted_score=16048.129682275494 trade_count=35286.0 retention=0.8619586193419156 csv=backtest/csv\stock_bt_WideV1IterationV4_20260424__cand001_20260424165741.csv
- rank=5 strategy=WideV1IterationV4_20260424__cand003 type=v4_replace_secondary adjusted_score=15781.69541531546 trade_count=35073.0 retention=0.8567555023572807 csv=backtest/csv\stock_bt_WideV1IterationV4_20260424__cand003_20260424170208.csv
- rank=6 strategy=WideV1IterationV4_20260424__cand008 type=v4_replace_secondary adjusted_score=14540.4899413001 trade_count=35700.0 retention=0.8720717199599385 csv=backtest/csv\stock_bt_WideV1IterationV4_20260424__cand008_20260424171329.csv
- rank=7 strategy=WideV1IterationV4_20260424__cand007 type=v4_relax_trade_amount adjusted_score=14205.563285735752 trade_count=35898.0 retention=0.8769084202555145 csv=backtest/csv\stock_bt_WideV1IterationV4_20260424__cand007_20260424171112.csv
- rank=8 strategy=WideV1IterationV4_20260424__cand010 type=v4_replace_secondary adjusted_score=13751.461309552804 trade_count=35942.0 retention=0.8779832425434204 csv=backtest/csv\stock_bt_WideV1IterationV4_20260424__cand010_20260424171800.csv
- rank=9 strategy=WideV1IterationV4_20260424__cand004 type=v4_tighten_secondary adjusted_score=13497.662902097409 trade_count=36096.0 retention=0.8817451205510907 csv=backtest/csv\stock_bt_WideV1IterationV4_20260424__cand004_20260424170427.csv
- rank=10 strategy=WideV1IterationV4_20260424__cand005 type=v4_tighten_secondary adjusted_score=13497.662902097409 trade_count=36096.0 retention=0.8817451205510907 csv=backtest/csv\stock_bt_WideV1IterationV4_20260424__cand005_20260424170645.csv

## Cleanup Summary

```text
attempted_count=10
deleted_count=10
kept_count=0
failed_count=0
```
