# P3 Prior-Run Selector Replay

## Status
- diagnostic_only: true
- run_id: tick_oos_dash_p3_train_2023_2025_20260604
- selector_version: sparse_positive_v1
- selected: True
- selected_gen: 5
- selected_bucket: sparse_positive
- selected_buy: AILOOP_tick_oos_dash_p3_train_2023_2025_20260604_g5_buy
- selected_sell: AILOOP_tick_oos_dash_p3_train_2023_2025_20260604_g5_sell

## Interpretation
This replay applies the predeclared sparse_positive_v1 selector to the prior 2023~2025 training rows only. It is a mechanics check and not efficacy evidence, because the prior P5 OOS failure is already known.

## Required observations
- Prior gen4 is rejected because it has negative training profit. Rejection reasons: profit <= 0, mdd > 10.0, trade_count > 250
- Prior gen5 qualifies as sparse_positive because it is profitable, low MDD, has 99 trades, and its gate failure is only daily_avg_trades 0.1 < min_daily_trades 0.3.
- Artifact has oos_excluded=true and diagnostic_only=true.

## Guardrail
Do not cite this replay as promotion, human-level, seed-superior, or OOS performance evidence. A fresh selector-frozen P4 run is still required before P5 OOS.
