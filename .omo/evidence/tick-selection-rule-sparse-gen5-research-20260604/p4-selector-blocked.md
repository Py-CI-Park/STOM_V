# P4 Selector Blocked

## Verdict
- selected: False
- blocked: True
- blocker: no candidate qualified for sparse_positive_v1
- selector_version: sparse_positive_v1
- run_id: tick_sel_sparse_p4_train_2023_2025_20260604
- oos_excluded: True

## Run Summary
- Official loop exit: 0
- Generations: 6
- Winner: null
- Best generation by existing graded score: gen4, but it is training-negative and gate-failed.
- Wall clock: about 2704.2 seconds, from loop summary.

## Generation Rows
| gen | status | score | gate | reason | trades | daily_avg | mdd | profit | pct | payoff | max_hold |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | error | 0.0 | 0 | backtest failed/timeout: warm backtest non-success: status=error message=���׽�Ʈ �ð� �ʰ� (300��) csv=no | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 1 | ok | 0.016672959200214055 | 0 | mdd 167.6 > mdd_cap 35 | 4212 | 5.8 | 167.56 | -35206257.0 | -175.78 | 1.2712289213228511 | 4.0 |
| 2 | ok | 0.16319728759236568 | 0 | mdd 43.76 > mdd_cap 35 | 688 | 0.9 | 43.76 | -1945943.0 | -19.51 | 1.3270414441556224 | 2.0 |
| 3 | error | 0.0 | 0 | backtest failed/timeout: warm backtest non-success: status=error message=backtest completed without metrics csv=no | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 4 | ok | 0.16904957025100648 | 0 | mdd 39.05 > mdd_cap 35 | 687 | 0.9 | 39.05 | -2153502.0 | -21.61 | 1.253967211931151 | 2.0 |
| 5 | ok | 0.15753391372194106 | 0 | daily_avg_trades 0.2 < min_daily_trades 0.3 | 111 | 0.2 | 13.4 | -353764.0 | -7.08 | 1.74679186756128 | 0.0 |

## Selector Interpretation
sparse_positive_v1 found no eligible candidate.

Key rejection facts:
- gen1: profit negative, MDD 167.56, trades 4212.
- gen2: profit negative, MDD 43.76, trades 688.
- gen4: profit negative, MDD 39.05, trades 687.
- gen5: daily-frequency gate failure, but profit is negative (-353,764) and MDD is 13.4, so it is not sparse-positive under P1 thresholds.

## Next-Step Effect
P5 fixed OOS must be skipped/blocked. No OOS rows should be fabricated because no P4 candidate was frozen.
