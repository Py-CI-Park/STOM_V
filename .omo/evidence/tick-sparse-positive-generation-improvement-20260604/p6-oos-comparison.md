# P6 Fixed OOS Comparison

## Candidate
- P5 selected gen: `4`
- Buy: `AILOOP_tick_spgen_p5_train_2023_2025_20260604_g4_buy`
- Sell: `AILOOP_tick_spgen_p5_train_2023_2025_20260604_g4_sell`
- Training profit/MDD/trades: `1,155,715` / `9.12` / `124`

## OOS Rows
- `seed_2022`: profit `2,223,554`, MDD `13.02`, trades `58`, gate `True`, reason `ok`
- `seed_2026`: profit `-191,109`, MDD `15.63`, trades `10`, gate `False`, reason `total_profit -1.911e+05 <= 0`
- `ai_2022`: profit `-222,400`, MDD `9.0`, trades `24`, gate `False`, reason `total_profit -2.224e+05 <= 0`
- `ai_2026`: profit `356,664`, MDD `1.36`, trades `7`, gate `True`, reason `ok`

## Predeclared Checks
- `ai_positive_both_oos_years`: `false`
- `combined_ai_profit_gte_seed`: `false`
- `combined_ai_max_mdd_lte_seed`: `true`
- `each_ai_oos_year_trade_count_gte_20`: `false`
- `combined_ai_oos_trade_count_gte_50`: `false`
- `candidate_identity_matches_p5`: `true`
- `no_oos_reselection`: `true`

- Combined seed profit: `2,032,445`
- Combined AI profit: `134,264`
- Seed max MDD: `15.63`
- AI max MDD: `9.0`
- Seed total trades: `68`
- AI total trades: `31`

## P6 Verdict
- OOS pass rule passed: `false`
- Promotion evidence: `false` because AI 2022 OOS profit is negative and AI combined profit/trade sufficiency fail.
