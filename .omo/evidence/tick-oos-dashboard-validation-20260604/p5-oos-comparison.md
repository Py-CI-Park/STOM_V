# P5 Fixed OOS Comparison

## Candidate Lock
- P3 selected gen: `4` from `tick_oos_dash_p3_train_2023_2025_20260604`
- AI buy/sell: `AILOOP_tick_oos_dash_p3_train_2023_2025_20260604_g4_buy` / `AILOOP_tick_oos_dash_p3_train_2023_2025_20260604_g4_sell`
- P3 warning: gate_passed=False, training_profit=-67,190
- Candidate was not reselected after OOS.

## Rows
| row | period | window | gate | profit | pct | MDD | trades | daily_avg | payoff | reason |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| seed_2022 | 20220101~20221231 | 90000~92800 | True | 2,223,554 | 44.36 | 13.02 | 58 | 0.3 | 1.2548258225172206 | `ok` |
| seed_2026 | 20260101~20260228 | 90000~92800 | False | -191,109 | -3.82 | 15.63 | 10 | 0.3 | 1.259748427672956 | `total_profit -1.911e+05 <= 0` |
| ai_2022 | 20220101~20221231 | 90000~93000 | False | -531,523 | -10.63 | 16.77 | 99 | 0.5 | 1.3211008370217803 | `total_profit -5.315e+05 <= 0` |
| ai_2026 | 20260101~20260228 | 90000~93000 | True | 126,238 | 2.52 | 2.52 | 2 | 0.1 | 999.0 | `ok` |

## Superiority Rule
- ai_positive_both_oos_years: False
- combined_ai_profit_gte_seed: False
- combined_ai_max_mdd_lte_seed: False
- candidate_identity_matches_p3: True
- no_oos_reselection: True
- combined_seed_profit=2,032,445
- combined_ai_profit=-405,285
- seed_max_mdd=15.63
- ai_max_mdd=16.77
- seed_total_trades=68
- ai_total_trades=101
- rule_passed=False

## Decision
- P5 rule failed. AI is negative in 2022, combined AI profit is below seed, and AI max MDD is above seed max MDD.
- This cannot support human-level, seed-superior, or promotion claims.
